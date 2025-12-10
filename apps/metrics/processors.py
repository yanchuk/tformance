"""
GitHub webhook event processors.

Functions to process GitHub webhook payloads and create/update database records.
"""

from datetime import datetime
from decimal import Decimal

from apps.metrics.models import PRReview, PullRequest, TeamMember


def _parse_github_timestamp(timestamp_str: str | None) -> datetime | None:
    """
    Parse GitHub ISO8601 timestamp string to datetime.

    Args:
        timestamp_str: ISO8601 timestamp string from GitHub (e.g., "2025-01-01T10:00:00Z")

    Returns:
        datetime object if parsing succeeds, None if timestamp_str is None
    """
    if not timestamp_str:
        return None
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


def _determine_pr_state(github_state: str, is_merged: bool) -> str:
    """
    Determine PR state from GitHub state and merged flag.

    Args:
        github_state: GitHub state ("open" or "closed")
        is_merged: Whether the PR was merged

    Returns:
        One of: "merged", "closed", or "open"
    """
    if github_state == "closed" and is_merged:
        return "merged"
    elif github_state == "closed":
        return "closed"
    else:
        return "open"


def _calculate_cycle_time_hours(pr_created_at: datetime | None, merged_at: datetime | None) -> Decimal | None:
    """
    Calculate cycle time in hours between PR creation and merge.

    Args:
        pr_created_at: When the PR was created
        merged_at: When the PR was merged

    Returns:
        Decimal representing hours, rounded to 2 decimal places, or None if either timestamp is missing
    """
    if not merged_at or not pr_created_at:
        return None

    time_diff = merged_at - pr_created_at
    return Decimal(str(round(time_diff.total_seconds() / 3600, 2)))


def _calculate_time_diff_hours(start_time: datetime | None, end_time: datetime | None) -> Decimal | None:
    """
    Calculate time difference in hours between two timestamps.

    Args:
        start_time: Start timestamp
        end_time: End timestamp

    Returns:
        Decimal representing hours, rounded to 2 decimal places, or None if either timestamp is missing
    """
    if not start_time or not end_time:
        return None

    time_diff = end_time - start_time
    return Decimal(str(round(time_diff.total_seconds() / 3600, 2)))


def _get_team_member_by_github_id(team, github_user_id: str) -> TeamMember | None:
    """
    Look up a TeamMember by their GitHub user ID.

    Args:
        team: Team instance to search within
        github_user_id: GitHub user ID as a string

    Returns:
        TeamMember instance if found, None otherwise
    """
    try:
        return TeamMember.objects.get(team=team, github_id=github_user_id)
    except TeamMember.DoesNotExist:
        return None


def handle_pull_request_event(team, payload: dict) -> PullRequest | None:
    """
    Process pull_request webhook event and create/update PullRequest record.

    Args:
        team: Team instance this PR belongs to
        payload: GitHub webhook payload dictionary

    Returns:
        PullRequest instance if successful, None if author not found
    """
    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    # Extract basic PR information
    github_pr_id = pr_data.get("id")
    github_repo = repo_data.get("full_name")
    title = pr_data.get("title", "")

    # Determine state based on GitHub state and merged flag
    github_state = pr_data.get("state", "open")
    is_merged = pr_data.get("merged", False)
    state = _determine_pr_state(github_state, is_merged)

    # Look up author by github_id
    user_data = pr_data.get("user", {})
    github_user_id = str(user_data.get("id"))
    author = _get_team_member_by_github_id(team, github_user_id)

    # Parse timestamps
    pr_created_at = _parse_github_timestamp(pr_data.get("created_at"))
    merged_at = _parse_github_timestamp(pr_data.get("merged_at"))

    # Calculate cycle time if merged
    cycle_time_hours = _calculate_cycle_time_hours(pr_created_at, merged_at)

    # Extract code changes
    additions = pr_data.get("additions", 0)
    deletions = pr_data.get("deletions", 0)

    # Detect flags
    is_revert = "revert" in title.lower()
    is_hotfix = "hotfix" in title.lower()

    # Create or update the PR record
    pr, created = PullRequest.objects.update_or_create(
        team=team,
        github_pr_id=github_pr_id,
        github_repo=github_repo,
        defaults={
            "title": title,
            "author": author,
            "state": state,
            "pr_created_at": pr_created_at,
            "merged_at": merged_at,
            "cycle_time_hours": cycle_time_hours,
            "additions": additions,
            "deletions": deletions,
            "is_revert": is_revert,
            "is_hotfix": is_hotfix,
        },
    )

    return pr


def handle_pull_request_review_event(team, payload: dict) -> PRReview | None:
    """
    Process pull_request_review webhook event and create PRReview record.

    Args:
        team: Team instance this review belongs to
        payload: GitHub webhook payload dictionary

    Returns:
        PRReview instance if successful, None if PR not found
    """
    review_data = payload.get("review", {})
    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    # Extract review information
    github_review_id = review_data.get("id")
    review_state = review_data.get("state", "")
    submitted_at = _parse_github_timestamp(review_data.get("submitted_at"))

    # Look up the PR
    github_pr_id = pr_data.get("id")
    github_repo = repo_data.get("full_name")

    try:
        pull_request = PullRequest.objects.get(
            team=team,
            github_pr_id=github_pr_id,
            github_repo=github_repo,
        )
    except PullRequest.DoesNotExist:
        return None

    # Look up reviewer by github_id
    user_data = review_data.get("user", {})
    github_user_id = str(user_data.get("id"))
    reviewer = _get_team_member_by_github_id(team, github_user_id)

    # Create or update the review record
    review, created = PRReview.objects.update_or_create(
        team=team,
        github_review_id=github_review_id,
        defaults={
            "pull_request": pull_request,
            "reviewer": reviewer,
            "state": review_state,
            "submitted_at": submitted_at,
        },
    )

    # Update PR's first_review_at and review_time_hours if this is the first review
    if pull_request.first_review_at is None and submitted_at is not None:
        pull_request.first_review_at = submitted_at
        # Calculate review_time_hours
        pull_request.review_time_hours = _calculate_time_diff_hours(pull_request.pr_created_at, submitted_at)
        pull_request.save()

    return review
