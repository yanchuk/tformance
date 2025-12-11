"""Celery tasks for integrations."""

import logging

from celery import shared_task
from celery.exceptions import Retry

from apps.integrations.models import TrackedRepository
from apps.integrations.services.github_sync import sync_repository_incremental

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_repository_task(self, repo_id: int) -> dict:
    """Sync a single tracked repository.

    Args:
        self: Celery task instance (bound task)
        repo_id: ID of the TrackedRepository to sync

    Returns:
        Dict with sync results (prs_synced, reviews_synced, errors) or error/skip status
    """
    # Get TrackedRepository by id
    try:
        tracked_repo = TrackedRepository.objects.get(id=repo_id)
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository with id {repo_id} not found")
        return {"error": f"TrackedRepository with id {repo_id} not found"}

    # Check if repo is active
    if not tracked_repo.is_active:
        logger.info(f"Skipping inactive repository: {tracked_repo.full_name}")
        return {"skipped": True, "reason": "Repository is not active"}

    # Set status to syncing
    tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_SYNCING
    tracked_repo.save(update_fields=["sync_status"])

    # Sync the repository
    logger.info(f"Starting sync for repository: {tracked_repo.full_name}")
    try:
        result = sync_repository_incremental(tracked_repo)
        logger.info(f"Successfully synced repository: {tracked_repo.full_name}")

        # Set status to complete and clear error
        tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_COMPLETE
        tracked_repo.last_sync_error = None
        tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

        return result
    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff
            logger.warning(f"Sync failed for {tracked_repo.full_name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted or retry failed - log to Sentry and return error
            from sentry_sdk import capture_exception

            logger.error(f"Sync failed permanently for {tracked_repo.full_name}: {exc}")
            capture_exception(exc)

            # Set status to error and save error message
            tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_ERROR
            tracked_repo.last_sync_error = str(exc)
            tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

            return {"error": str(exc)}


@shared_task
def sync_all_repositories_task() -> dict:
    """Dispatch sync tasks for all active tracked repositories.

    Returns:
        Dict with counts: repos_dispatched, repos_skipped
    """
    logger.info("Starting sync for all repositories")

    # Query all tracked repositories with optimized counts
    active_repos = TrackedRepository.objects.filter(is_active=True)
    repos_skipped = TrackedRepository.objects.filter(is_active=False).count()

    repos_dispatched = 0

    # Dispatch sync task for each active repo
    for repo in active_repos:
        try:
            sync_repository_task.delay(repo.id)
            repos_dispatched += 1
        except Exception as e:
            # Log dispatch errors and continue with remaining repos
            logger.error(f"Failed to dispatch sync task for repository {repo.full_name}: {e}")
            continue

    logger.info(f"Finished dispatching sync tasks. Dispatched: {repos_dispatched}, Skipped: {repos_skipped}")

    return {
        "repos_dispatched": repos_dispatched,
        "repos_skipped": repos_skipped,
    }
