"""GitHub API client functions for fetching data from GitHub repositories."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from django.utils import timezone
from github import Github, GithubException

from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.integrations.services.github_sync.converters import convert_pr_to_dict

if TYPE_CHECKING:
    from apps.integrations.types import PRDict


def get_repository_pull_requests(
    access_token: str,
    repo_full_name: str,
    state: str = "all",
    per_page: int = 100,
    days_back: int | None = None,
) -> Generator[PRDict, None, None]:
    """Fetch pull requests from a GitHub repository.

    Args:
        access_token: GitHub OAuth access token
        repo_full_name: Repository in "owner/repo" format
        state: PR state filter ("all", "open", "closed")
        per_page: Results per page (max 100, ignored - PyGithub handles pagination)
        days_back: If set, only return PRs updated within this many days.
                  PRs are sorted by updated_at desc and iteration stops when
                  hitting old PRs, preventing loading all PRs into memory.

    Yields:
        PR dictionaries with all required attributes (generator for memory efficiency)

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create GitHub client
        github = Github(access_token)

        # Get repository
        repo = github.get_repo(repo_full_name)

        # Get pull requests sorted by updated_at desc for efficient date filtering
        prs = repo.get_pulls(state=state, sort="updated", direction="desc")

        # Calculate cutoff date if days_back is specified
        cutoff_date = None
        if days_back is not None:
            cutoff_date = timezone.now() - timedelta(days=days_back)

        # Yield PRs one at a time (generator pattern for memory efficiency)
        for pr in prs:
            # Stop iteration when hitting PRs older than cutoff
            # PyGithub stubs mark updated_at as Optional but PRs always have it
            if cutoff_date is not None and pr.updated_at and pr.updated_at < cutoff_date:
                break
            yield convert_pr_to_dict(pr)

    except GithubException as e:
        raise GitHubOAuthError(f"GitHub API error: {e.status}") from e


def get_updated_pull_requests(
    access_token: str,
    repo_full_name: str,
    since: datetime,
) -> list[dict]:
    """Fetch pull requests updated since a given datetime.

    GitHub's Pull Requests API doesn't have a 'since' parameter, so we use
    the Issues API which does have 'since' and filter to only return issues
    that are pull requests.

    Args:
        access_token: GitHub OAuth access token
        repo_full_name: Repository in "owner/repo" format
        since: Only return PRs updated at or after this datetime

    Returns:
        List of PR dictionaries with all required attributes (same format as get_repository_pull_requests)

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create GitHub client
        github = Github(access_token)

        # Get repository
        repo = github.get_repo(repo_full_name)

        # Get issues updated since datetime (includes PRs)
        # PyGithub returns PaginatedList that handles pagination automatically
        issues = repo.get_issues(since=since, state="all")

        # Filter to only issues that are pull requests and fetch full PR details
        pr_list = []
        for issue in issues:
            # Check if issue is a pull request (has pull_request attribute)
            if issue.pull_request is None:
                continue

            # Fetch full PR details (Issues API doesn't include merged status, etc.)
            pr = repo.get_pull(issue.number)

            # Convert PR to dict with all required attributes (same format as get_repository_pull_requests)
            pr_list.append(convert_pr_to_dict(pr))

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
