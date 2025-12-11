"""GitHub sync service for fetching data from GitHub repositories."""

from github import Github, GithubException

from apps.integrations.services.github_oauth import GitHubOAuthError

__all__ = ["GitHubOAuthError", "get_repository_pull_requests", "get_pull_request_reviews", "sync_repository_history"]


def get_repository_pull_requests(
    access_token: str,
    repo_full_name: str,
    state: str = "all",
    per_page: int = 100,
) -> list[dict]:
    """Fetch pull requests from a GitHub repository.

    Args:
        access_token: GitHub OAuth access token
        repo_full_name: Repository in "owner/repo" format
        state: PR state filter ("all", "open", "closed")
        per_page: Results per page (max 100, ignored - PyGithub handles pagination)

    Returns:
        List of PR dictionaries with all required attributes

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create GitHub client
        github = Github(access_token)

        # Get repository
        repo = github.get_repo(repo_full_name)

        # Get pull requests - PyGithub returns PaginatedList that handles pagination automatically
        prs = repo.get_pulls(state=state)

        # Convert each PR to dict with all required attributes
        pr_list = []
        for pr in prs:
            pr_dict = {
                "id": pr.id,
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "merged": pr.merged,
                "merged_at": pr.merged_at.isoformat().replace("+00:00", "Z") if pr.merged_at else None,
                "created_at": pr.created_at.isoformat().replace("+00:00", "Z"),
                "updated_at": pr.updated_at.isoformat().replace("+00:00", "Z"),
                "additions": pr.additions,
                "deletions": pr.deletions,
                "commits": pr.commits,
                "changed_files": pr.changed_files,
                "user": {
                    "id": pr.user.id,
                    "login": pr.user.login,
                },
                "base": {
                    "ref": pr.base.ref,
                },
                "head": {
                    "ref": pr.head.ref,
                    "sha": pr.head.sha,
                },
                "html_url": pr.html_url,
            }
            pr_list.append(pr_dict)

        return pr_list

    except GithubException as e:
        raise GitHubOAuthError(f"GitHub API error: {e.status}") from e


def get_pull_request_reviews(
    access_token: str,
    repo_full_name: str,
    pr_number: int,
) -> list[dict]:
    """Fetch reviews for a specific pull request.

    Args:
        access_token: GitHub OAuth access token
        repo_full_name: Repository in "owner/repo" format
        pr_number: Pull request number

    Returns:
        List of review dictionaries with all required attributes

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create GitHub client
        github = Github(access_token)

        # Get repository and pull request
        repo = github.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)

        # Get reviews - PyGithub returns PaginatedList that handles pagination automatically
        reviews = pr.get_reviews()

        # Convert each review to dict with all required attributes
        review_list = []
        for review in reviews:
            review_dict = {
                "id": review.id,
                "user": {
                    "id": review.user.id,
                    "login": review.user.login,
                },
                "body": review.body,
                "state": review.state,
                "submitted_at": review.submitted_at.isoformat().replace("+00:00", "Z"),
            }
            review_list.append(review_dict)

        return review_list

    except GithubException as e:
        raise GitHubOAuthError(f"GitHub API error: {e.status}") from e


def _sync_pr_reviews(
    pr: "PullRequest",  # noqa: F821
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


def sync_repository_history(
    tracked_repo: "TrackedRepository",  # noqa: F821
    days_back: int = 90,
) -> dict:
    """Sync historical PR data from a tracked repository.

    Args:
        tracked_repo: TrackedRepository instance to sync
        days_back: Number of days of history to sync (default 90, not yet implemented)

    Returns:
        Dict with keys: prs_synced, reviews_synced, errors
    """
    from django.utils import timezone

    from apps.integrations.services.encryption import decrypt
    from apps.metrics.models import PullRequest
    from apps.metrics.processors import _map_github_pr_to_fields

    # Decrypt the access token
    access_token = decrypt(tracked_repo.integration.credential.access_token)

    # Fetch PRs from GitHub
    prs_data = get_repository_pull_requests(access_token, tracked_repo.full_name)

    # Process each PR with error handling
    prs_synced = 0
    reviews_synced = 0
    errors = []

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
            reviews_synced += _sync_pr_reviews(
                pr=pr,
                pr_number=pr_number,
                access_token=access_token,
                repo_full_name=tracked_repo.full_name,
                team=tracked_repo.team,
                errors=errors,
            )

        except Exception as e:
            # Log the error but continue processing other PRs
            pr_number = pr_data.get("number", "unknown")
            error_msg = f"Failed to sync PR #{pr_number}: {str(e)}"
            errors.append(error_msg)
            continue

    # Update last_sync_at
    tracked_repo.last_sync_at = timezone.now()
    tracked_repo.save()

    return {
        "prs_synced": prs_synced,
        "reviews_synced": reviews_synced,
        "errors": errors,
    }
