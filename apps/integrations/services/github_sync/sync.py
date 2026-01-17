"""Sync orchestration for GitHub repository data.

This module coordinates the overall sync process, calling processors and metrics
calculators in the correct order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone
from github import Github

from apps.integrations.services.github_rate_limit import should_pause_for_rate_limit
from apps.integrations.services.github_sync.auth import get_access_token
from apps.integrations.services.github_sync.client import (
    get_repository_pull_requests,
    get_updated_pull_requests,
)
from apps.integrations.services.github_sync.metrics import calculate_pr_iteration_metrics
from apps.integrations.services.github_sync.processors import (
    sync_pr_check_runs,
    sync_pr_commits,
    sync_pr_files,
    sync_pr_issue_comments,
    sync_pr_review_comments,
    sync_pr_reviews,
    sync_repository_deployments,
)

if TYPE_CHECKING:
    from apps.integrations.models import TrackedRepository


def _process_prs(
    prs_data,
    tracked_repo: TrackedRepository,
    access_token: str,
) -> dict:
    """Process PR data and sync to database.

    Args:
        prs_data: Iterable of PR dictionaries from GitHub API (list or generator)
        tracked_repo: TrackedRepository instance to sync
        access_token: Decrypted GitHub access token

    Returns:
        Dict with sync stats for PRs, reviews, commits, check_runs, files, comments, rate_limited
    """
    from apps.metrics.models import PullRequest
    from apps.metrics.processors import _map_github_pr_to_fields

    # Create Github client for rate limit checks
    github = Github(access_token)

    prs_synced = 0
    reviews_synced = 0
    commits_synced = 0
    check_runs_synced = 0
    files_synced = 0
    comments_synced = 0
    errors = []
    rate_limited = False

    for pr_data in prs_data:
        try:
            # Extract identifying information
            github_pr_id = pr_data["id"]
            pr_number = pr_data["number"]

            # Map GitHub data to model fields
            pr_fields = _map_github_pr_to_fields(tracked_repo.team, pr_data)

            # Create or update the PR record
            pr, created = PullRequest.objects.update_or_create(
                team=tracked_repo.team,
                github_pr_id=github_pr_id,
                github_repo=tracked_repo.full_name,
                defaults=pr_fields,
            )
            prs_synced += 1

            # Sync reviews for this PR
            reviews_synced += sync_pr_reviews(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Sync commits for this PR
            commits_synced += sync_pr_commits(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Sync check runs for this PR
            check_runs_synced += sync_pr_check_runs(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Sync files for this PR
            files_synced += sync_pr_files(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Sync comments for this PR (both issue and review comments)
            comments_synced += sync_pr_issue_comments(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )
            comments_synced += sync_pr_review_comments(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

            # Calculate iteration metrics after all data is synced
            calculate_pr_iteration_metrics(pr)

            # Check rate limit after processing this PR
            rate_limit = github.get_rate_limit()
            core = rate_limit.core
            tracked_repo.rate_limit_remaining = core.remaining
            tracked_repo.rate_limit_reset_at = core.reset
            tracked_repo.save()

            # Stop processing if rate limited
            if should_pause_for_rate_limit(core.remaining):
                rate_limited = True
                break

        except Exception as e:
            # Log the error but continue processing other PRs
            pr_number = pr_data.get("number", "unknown")
            error_msg = f"Failed to sync PR #{pr_number}: {str(e)}"
            errors.append(error_msg)
            continue

    return {
        "prs_synced": prs_synced,
        "reviews_synced": reviews_synced,
        "commits_synced": commits_synced,
        "check_runs_synced": check_runs_synced,
        "files_synced": files_synced,
        "comments_synced": comments_synced,
        "errors": errors,
        "rate_limited": rate_limited,
    }


def sync_repository_history(
    tracked_repo: TrackedRepository,
    days_back: int = 90,
) -> dict:
    """Sync historical PR data from a tracked repository.

    Args:
        tracked_repo: TrackedRepository instance to sync
        days_back: Number of days of history to sync (default 90)

    Returns:
        Dict with sync stats for PRs, reviews, commits, check_runs, files, comments, deployments
    """
    # Get access token (prefers App installation over OAuth)
    access_token = get_access_token(tracked_repo)

    # Fetch PRs from GitHub with days_back filter (generator for memory efficiency)
    prs_data = get_repository_pull_requests(access_token, tracked_repo.full_name, days_back=days_back)

    # Process PRs and sync all related data (iterates generator one PR at a time)
    result = _process_prs(prs_data, tracked_repo, access_token)

    # Sync deployments for this repository
    result["deployments_synced"] = sync_repository_deployments(
        repo_full_name=tracked_repo.full_name,
        access_token=access_token,
        team=tracked_repo.team,
        errors=result["errors"],
    )

    # Update last_sync_at
    tracked_repo.last_sync_at = timezone.now()
    tracked_repo.save()

    return result


def sync_repository_incremental(tracked_repo: TrackedRepository) -> dict:
    """
    Perform incremental sync for a repository.

    Args:
        tracked_repo: TrackedRepository model instance

    Returns:
        Dict with sync stats for PRs, reviews, commits, check_runs, files, comments, deployments
    """
    # If last_sync_at is None, fall back to full sync
    if tracked_repo.last_sync_at is None:
        return sync_repository_history(tracked_repo)

    # Get access token (prefers App installation over OAuth)
    access_token = get_access_token(tracked_repo)

    # Fetch updated PRs from GitHub since last sync
    prs_data = get_updated_pull_requests(access_token, tracked_repo.full_name, tracked_repo.last_sync_at)

    # Process PRs and sync all related data
    result = _process_prs(prs_data, tracked_repo, access_token)

    # Sync deployments for this repository
    result["deployments_synced"] = sync_repository_deployments(
        repo_full_name=tracked_repo.full_name,
        access_token=access_token,
        team=tracked_repo.team,
        errors=result["errors"],
    )

    # Update last_sync_at
    tracked_repo.last_sync_at = timezone.now()
    tracked_repo.save()

    return result
