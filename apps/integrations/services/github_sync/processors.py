"""Processors for syncing individual PR-related entities from GitHub.

Each processor handles syncing a specific entity type (reviews, commits, files, etc.)
from GitHub to the database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from github import Github

from apps.integrations.services.github_sync.client import get_pull_request_reviews

if TYPE_CHECKING:
    from apps.metrics.models import PullRequest


def sync_pr_reviews(
    pr: PullRequest,
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync reviews for a single pull request.

    Args:
        pr: PullRequest instance to sync reviews for
        pr_number: GitHub PR number
        access_token: Decrypted GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of reviews successfully synced
    """
    from apps.metrics.models import PRReview
    from apps.metrics.processors import (
        _calculate_time_diff_hours,
        _get_team_member_by_github_id,
        _parse_github_timestamp,
    )

    reviews_synced = 0

    try:
        reviews_data = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Track earliest review time for this PR
        earliest_review_at = None

        for review_data in reviews_data:
            try:
                # Create or update review record
                PRReview.objects.update_or_create(
                    team=team,
                    github_review_id=review_data["id"],
                    defaults={
                        "pull_request": pr,
                        "reviewer": _get_team_member_by_github_id(team, str(review_data["user"]["id"])),
                        "state": review_data["state"].lower(),
                        "submitted_at": _parse_github_timestamp(review_data["submitted_at"]),
                    },
                )
                reviews_synced += 1

                # Track earliest review time
                submitted_at = _parse_github_timestamp(review_data["submitted_at"])
                if submitted_at and (earliest_review_at is None or submitted_at < earliest_review_at):
                    earliest_review_at = submitted_at

            except Exception as e:
                # Log error but continue processing other reviews
                error_msg = f"Failed to sync review {review_data.get('id', 'unknown')} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

        # Update PR metrics if we found an earlier review
        if earliest_review_at and (pr.first_review_at is None or earliest_review_at < pr.first_review_at):
            pr.first_review_at = earliest_review_at
            pr.review_time_hours = _calculate_time_diff_hours(pr.pr_created_at, earliest_review_at)
            pr.save()

    except Exception as e:
        # Log error but continue processing other PRs
        error_msg = f"Failed to fetch reviews for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return reviews_synced


def sync_pr_commits(
    pr: PullRequest,
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync commits for a single pull request.

    Args:
        pr: PullRequest instance to sync commits for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of commits successfully synced
    """
    from apps.metrics.models import Commit
    from apps.metrics.processors import _get_team_member_by_github_id, _parse_github_timestamp

    commits_synced = 0

    try:
        # Create GitHub client and get PR
        github = Github(access_token)
        repo = github.get_repo(repo_full_name)
        github_pr = repo.get_pull(pr_number)

        # Iterate over commits
        for commit in github_pr.get_commits():
            try:
                # Extract commit data
                sha = commit.sha
                message = commit.commit.message
                committed_at = _parse_github_timestamp(commit.commit.author.date.isoformat().replace("+00:00", "Z"))
                additions = commit.stats.additions
                deletions = commit.stats.deletions

                # Look up author by github_id (may be None)
                author = None
                if commit.author is not None:
                    author = _get_team_member_by_github_id(team, str(commit.author.id))

                # Create or update commit record
                Commit.objects.update_or_create(
                    team=team,
                    github_sha=sha,
                    defaults={
                        "github_repo": repo_full_name,
                        "author": author,
                        "message": message,
                        "committed_at": committed_at,
                        "additions": additions,
                        "deletions": deletions,
                        "pull_request": pr,
                    },
                )
                commits_synced += 1

            except Exception as e:
                # Log error but continue processing other commits
                error_msg = f"Failed to sync commit {commit.sha[:8]} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error if we can't fetch commits at all
        error_msg = f"Failed to fetch commits for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return commits_synced


def sync_pr_check_runs(
    pr: PullRequest,
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync CI/CD check runs for a pull request.

    Args:
        pr: PullRequest instance to sync check runs for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of check runs successfully synced
    """
    from apps.metrics.models import PRCheckRun

    check_runs_synced = 0

    try:
        # Create GitHub client and get PR
        github = Github(access_token)
        repo = github.get_repo(repo_full_name)
        github_pr = repo.get_pull(pr_number)

        # Get head commit SHA
        head_sha = github_pr.head.sha

        # Get commit object
        commit = repo.get_commit(head_sha)

        # Get check runs for this commit
        check_runs = commit.get_check_runs()

        # Iterate over check runs
        for check_run in check_runs:
            try:
                # Calculate duration if both timestamps present
                duration_seconds = None
                if check_run.started_at and check_run.completed_at:
                    duration = (check_run.completed_at - check_run.started_at).total_seconds()
                    duration_seconds = int(duration)

                # Create or update check run record
                PRCheckRun.objects.update_or_create(
                    team=team,
                    github_check_run_id=check_run.id,
                    defaults={
                        "pull_request": pr,
                        "name": check_run.name,
                        "status": check_run.status,
                        "conclusion": check_run.conclusion,
                        "started_at": check_run.started_at,
                        "completed_at": check_run.completed_at,
                        "duration_seconds": duration_seconds,
                    },
                )
                check_runs_synced += 1

            except Exception as e:
                # Log error but continue processing other check runs
                error_msg = f"Failed to sync check run {check_run.id} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error if we can't fetch check runs at all
        error_msg = f"Failed to fetch check runs for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return check_runs_synced


def sync_pr_files(
    pr: PullRequest,
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync files changed in a PR from GitHub.

    Args:
        pr: PullRequest instance to sync files for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of files successfully synced
    """
    from apps.metrics.models import PRFile

    files_synced = 0

    try:
        # Create GitHub client and get PR
        github = Github(access_token)
        repo = github.get_repo(repo_full_name)
        github_pr = repo.get_pull(pr_number)

        # Fetch files from GitHub API
        files = github_pr.get_files()

        # Iterate over files
        for file in files:
            try:
                # Create or update file record
                PRFile.objects.update_or_create(
                    team=team,
                    pull_request=pr,
                    filename=file.filename,
                    defaults={
                        "status": file.status,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "changes": file.changes,
                        "file_category": PRFile.categorize_file(file.filename),
                    },
                )
                files_synced += 1

            except Exception as e:
                # Log error but continue processing other files
                error_msg = f"Failed to sync file {file.filename} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error if we can't fetch files at all
        error_msg = f"Failed to fetch files for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return files_synced


def _sync_pr_comments(
    pr: PullRequest,
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
    comment_type: str,
    get_comments_method: str,
) -> int:
    """Generic helper to sync PR comments from GitHub.

    Args:
        pr: PullRequest instance to sync comments for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to
        comment_type: Type of comment ("issue" or "review")
        get_comments_method: PyGithub PR method name to call ("get_issue_comments" or "get_review_comments")

    Returns:
        Number of comments successfully synced
    """
    from apps.metrics.models import PRComment
    from apps.metrics.processors import _get_team_member_by_github_id

    comments_synced = 0

    try:
        # Create GitHub client and get PR
        github = Github(access_token)
        repo = github.get_repo(repo_full_name)
        github_pr = repo.get_pull(pr_number)

        # Fetch comments using the specified method
        comments = getattr(github_pr, get_comments_method)()

        # Iterate over comments
        for comment in comments:
            try:
                # Map author to TeamMember
                author = None
                if comment.user:
                    author = _get_team_member_by_github_id(team, str(comment.user.id))

                # Build defaults dict with common fields
                defaults = {
                    "pull_request": pr,
                    "author": author,
                    "body": comment.body,
                    "comment_type": comment_type,
                    "comment_created_at": comment.created_at,
                    "comment_updated_at": comment.updated_at,
                }

                # Add review-specific fields or set them to None for issue comments
                if comment_type == "review":
                    defaults["path"] = comment.path
                    defaults["line"] = comment.line
                    defaults["in_reply_to_id"] = comment.in_reply_to_id
                else:
                    defaults["path"] = None
                    defaults["line"] = None
                    defaults["in_reply_to_id"] = None

                # Create or update comment record
                PRComment.objects.update_or_create(
                    team=team,
                    github_comment_id=comment.id,
                    defaults=defaults,
                )
                comments_synced += 1

            except Exception as e:
                # Log error but continue processing other comments
                error_msg = f"Failed to sync {comment_type} comment {comment.id} for PR #{pr_number}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error if we can't fetch comments at all
        error_msg = f"Failed to fetch {comment_type} comments for PR #{pr_number}: {str(e)}"
        errors.append(error_msg)

    return comments_synced


def sync_pr_issue_comments(
    pr: PullRequest,
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync issue comments (general PR comments) from GitHub.

    Args:
        pr: PullRequest instance to sync comments for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of issue comments successfully synced
    """
    return _sync_pr_comments(
        pr=pr,
        pr_number=pr_number,
        access_token=access_token,
        repo_full_name=repo_full_name,
        team=team,
        errors=errors,
        comment_type="issue",
        get_comments_method="get_issue_comments",
    )


def sync_pr_review_comments(
    pr: PullRequest,
    pr_number: int,
    access_token: str,
    repo_full_name: str,
    team,
    errors: list,
) -> int:
    """Sync review comments (inline code comments) from GitHub.

    Args:
        pr: PullRequest instance to sync comments for
        pr_number: GitHub PR number
        access_token: GitHub access token
        repo_full_name: Repository full name (owner/repo)
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of review comments successfully synced
    """
    return _sync_pr_comments(
        pr=pr,
        pr_number=pr_number,
        access_token=access_token,
        repo_full_name=repo_full_name,
        team=team,
        errors=errors,
        comment_type="review",
        get_comments_method="get_review_comments",
    )


def sync_repository_deployments(
    repo_full_name: str,
    access_token: str,
    team,
    errors: list,
) -> int:
    """Sync deployments from a GitHub repository.

    Args:
        repo_full_name: Repository in "owner/repo" format
        access_token: GitHub OAuth access token
        team: Team instance
        errors: List to append error messages to

    Returns:
        Number of deployments successfully synced
    """
    from apps.metrics.models import Deployment
    from apps.metrics.processors import _get_team_member_by_github_id

    deployments_synced = 0

    try:
        # Create GitHub client
        github = Github(access_token)

        # Get repository
        repo = github.get_repo(repo_full_name)

        # Get deployments
        deployments = repo.get_deployments()

        # Process each deployment
        for deployment in deployments:
            try:
                # Get deployment statuses (first is latest)
                statuses = deployment.get_statuses()
                status_list = list(statuses)

                # Use first status if available, otherwise default to "pending"
                status = status_list[0].state if status_list else "pending"

                # Map creator to TeamMember if present
                creator = None
                if deployment.creator:
                    creator = _get_team_member_by_github_id(team, str(deployment.creator.id))

                # Create or update deployment record
                Deployment.objects.update_or_create(
                    team=team,
                    github_deployment_id=deployment.id,
                    defaults={
                        "github_repo": repo_full_name,
                        "environment": deployment.environment,
                        "status": status,
                        "creator": creator,
                        "deployed_at": deployment.created_at,
                        "sha": deployment.sha or "",  # GitHub deployment SHA
                    },
                )
                deployments_synced += 1

            except Exception as e:
                # Log error but continue processing other deployments
                error_msg = f"Failed to sync deployment {deployment.id} for {repo_full_name}: {str(e)}"
                errors.append(error_msg)
                continue

    except Exception as e:
        # Log error for the entire repository
        error_msg = f"Failed to fetch deployments for {repo_full_name}: {str(e)}"
        errors.append(error_msg)

    return deployments_synced
