"""Signal receivers for integrations app.

These receivers handle lightweight, non-blocking operations in response to
onboarding and sync events. Heavy processing is handled via Celery task chains.
"""

import logging

from django.dispatch import receiver

from apps.integrations.signals import (
    onboarding_sync_completed,
    onboarding_sync_started,
    repository_sync_completed,
)

logger = logging.getLogger(__name__)


def track_event(event_name: str, **kwargs) -> None:
    """
    Track an analytics event.

    This is a simple wrapper that can be replaced with PostHog, Segment, etc.
    """
    try:
        from apps.web.analytics import track_event as posthog_track

        posthog_track(event_name=event_name, **kwargs)
    except Exception as e:
        logger.warning(f"Failed to track analytics event {event_name}: {e}")


@receiver(onboarding_sync_started)
def handle_onboarding_sync_started(sender, team_id: int, repo_ids: list[int], **kwargs) -> None:
    """
    Handle the start of onboarding sync.

    Logs the event for monitoring and debugging.
    """
    logger.info(f"Onboarding sync started for team {team_id} with {len(repo_ids)} repos: {repo_ids}")


@receiver(onboarding_sync_completed)
def handle_onboarding_sync_completed(
    sender,
    team_id: int,
    repos_synced: int = 0,
    failed_repos: int = 0,
    total_prs: int = 0,
    **kwargs,
) -> None:
    """
    Handle completion of onboarding sync.

    - Logs completion for monitoring
    - Sends analytics event for tracking
    """
    logger.info(
        f"Onboarding sync completed for team {team_id}: "
        f"repos_synced={repos_synced}, failed_repos={failed_repos}, total_prs={total_prs}"
    )

    # Track analytics event
    track_event(
        event_name="onboarding_sync_completed",
        team_id=team_id,
        repos_synced=repos_synced,
        failed_repos=failed_repos,
        total_prs=total_prs,
    )


@receiver(repository_sync_completed)
def handle_repository_sync_completed(
    sender,
    team_id: int,
    repo_id: int,
    prs_synced: int = 0,
    **kwargs,
) -> None:
    """
    Handle completion of individual repository sync.

    Logs the event for per-repo monitoring.
    """
    logger.info(f"Repository sync completed: team={team_id}, repo_id={repo_id}, prs_synced={prs_synced}")
