"""Utility classes and functions for GitHub GraphQL sync.

Contains SyncResult/MemberSyncResult classes, datetime parsing,
state mapping functions, and async database helpers.
"""

import logging
from typing import Any

from asgiref.sync import sync_to_async
from dateutil import parser as date_parser
from django.utils import timezone

from apps.integrations.models import TrackedRepository
from apps.metrics.models import TeamMember

logger = logging.getLogger(__name__)


def _get_sync_logger():
    """Get sync logger lazily to allow mocking in tests."""
    from apps.utils.sync_logger import get_sync_logger

    return get_sync_logger(__name__)


class SyncResult:
    """Track sync progress and errors."""

    def __init__(self) -> None:
        self.prs_synced = 0
        self.reviews_synced = 0
        self.commits_synced = 0
        self.files_synced = 0
        self.comments_synced = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for return value."""
        return {
            "prs_synced": self.prs_synced,
            "reviews_synced": self.reviews_synced,
            "commits_synced": self.commits_synced,
            "files_synced": self.files_synced,
            "comments_synced": self.comments_synced,
            "errors": self.errors,
        }


class MemberSyncResult:
    """Track member sync progress and errors."""

    def __init__(self) -> None:
        self.members_synced = 0
        self.members_created = 0
        self.members_updated = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for return value."""
        return {
            "members_synced": self.members_synced,
            "members_created": self.members_created,
            "members_updated": self.members_updated,
            "errors": self.errors,
        }


def _parse_datetime(dt_string: str | None):
    """Parse ISO datetime string to timezone-aware datetime."""
    if not dt_string:
        return None
    return date_parser.isoparse(dt_string)


def _map_pr_state(graphql_state: str) -> str:
    """Map GraphQL PR state to model state (lowercase)."""
    state_mapping = {
        "OPEN": "open",
        "MERGED": "merged",
        "CLOSED": "closed",
    }
    return state_mapping.get(graphql_state, graphql_state.lower())


def _map_review_state(graphql_state: str) -> str:
    """Map GraphQL review state to model state (lowercase)."""
    state_mapping = {
        "APPROVED": "approved",
        "CHANGES_REQUESTED": "changes_requested",
        "COMMENTED": "commented",
        "DISMISSED": "commented",  # Map dismissed to commented
        "PENDING": "commented",
    }
    return state_mapping.get(graphql_state, graphql_state.lower())


def _map_file_status(graphql_change_type: str) -> str:
    """Map GraphQL file changeType to model status (lowercase).

    GraphQL uses UPPERCASE changeType enum values: ADDED, CHANGED, COPIED, DELETED, MODIFIED, RENAMED
    """
    status_mapping = {
        "ADDED": "added",
        "CHANGED": "modified",
        "COPIED": "added",
        "DELETED": "removed",
        "MODIFIED": "modified",
        "REMOVED": "removed",
        "RENAMED": "renamed",
        # Handle lowercase too (for backwards compatibility)
        "added": "added",
        "modified": "modified",
        "removed": "removed",
        "renamed": "renamed",
    }
    return status_mapping.get(graphql_change_type, "modified")


def _get_team_member(team, github_login: str | None) -> TeamMember | None:
    """Get TeamMember by GitHub login, or None if not found."""
    if not github_login:
        return None
    try:
        return TeamMember.objects.get(team=team, github_username=github_login)
    except TeamMember.DoesNotExist:
        return None


# =============================================================================
# Async Database Helpers
# =============================================================================


@sync_to_async
def _update_sync_status(tracked_repo_id: int, status: str) -> None:
    """Update sync status (async-safe)."""
    TrackedRepository.objects.filter(id=tracked_repo_id).update(sync_status=status)  # noqa: TEAM001


@sync_to_async
def _update_sync_complete(tracked_repo_id: int) -> None:
    """Update sync status to complete with timestamp (async-safe)."""
    TrackedRepository.objects.filter(id=tracked_repo_id).update(  # noqa: TEAM001
        sync_status="complete",
        last_sync_at=timezone.now(),
    )


@sync_to_async
def _update_sync_progress(tracked_repo_id: int, completed: int, total: int) -> None:
    """Update sync progress fields (async-safe).

    Args:
        tracked_repo_id: ID of the TrackedRepository
        completed: Number of PRs synced so far
        total: Total number of PRs to sync
    """
    progress = int((completed / total) * 100) if total > 0 else 0
    TrackedRepository.objects.filter(id=tracked_repo_id).update(  # noqa: TEAM001
        sync_progress=progress,
        sync_prs_completed=completed,
        sync_prs_total=total,
    )


@sync_to_async
def _get_access_token(tracked_repo_id: int) -> str | None:
    """Get access token for a tracked repository (async-safe).

    This wraps ORM access to avoid SynchronousOnlyOperation errors
    when called from async context.
    """
    try:
        tracked_repo = TrackedRepository.objects.select_related("integration__credential").get(id=tracked_repo_id)  # noqa: TEAM001 - ID from Celery task
        return tracked_repo.integration.credential.access_token
    except (TrackedRepository.DoesNotExist, AttributeError):
        return None


@sync_to_async
def _set_prs_total(tracked_repo_id: int, total: int) -> None:
    """Set sync_prs_total on TrackedRepository (async-safe)."""
    TrackedRepository.objects.filter(id=tracked_repo_id).update(sync_prs_total=total)  # noqa: TEAM001


@sync_to_async
def _increment_prs_processed(tracked_repo_id: int) -> None:
    """Increment sync_prs_completed on TrackedRepository (async-safe).

    Uses F() expression for atomic increment.
    """
    from django.db.models import F

    TrackedRepository.objects.filter(id=tracked_repo_id).update(  # noqa: TEAM001
        sync_prs_completed=F("sync_prs_completed") + 1
    )


@sync_to_async
def _get_integration_access_token(integration_id: int) -> str | None:
    """Get access token for a GitHub integration (async-safe)."""
    from apps.integrations.models import GitHubIntegration

    try:
        integration = GitHubIntegration.objects.select_related("credential").get(id=integration_id)  # noqa: TEAM001 - ID from Celery task
        return integration.credential.access_token
    except (GitHubIntegration.DoesNotExist, AttributeError):
        return None
