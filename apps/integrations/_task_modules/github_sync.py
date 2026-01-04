"""GitHub sync Celery tasks.

This module contains tasks for synchronizing GitHub data:
- Repository sync (incremental and full history)
- Member sync (organization members)
- Webhook creation
- Onboarding sync (quick and full history)
"""

import logging
import time

from celery import shared_task
from celery.exceptions import Retry

from apps.integrations.models import GitHubIntegration, TrackedRepository
from apps.integrations.services import github_webhooks
from apps.integrations.services.github_sync import get_repository_pull_requests, sync_repository_incremental
from apps.integrations.services.member_sync import sync_github_members
from apps.utils.errors import sanitize_error

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


def _sync_with_graphql_or_rest(tracked_repo, days_back: int, skip_recent: int = 0) -> dict:
    """Sync repository using GraphQL or REST API based on feature flags.

    Uses GraphQL API if enabled for initial_sync operation, falling back to REST
    if GraphQL fails and fallback is enabled.

    Supports two-phase onboarding:
    - Phase 1: days_back=30, skip_recent=0 (sync recent 30 days)
    - Phase 2: days_back=90, skip_recent=30 (sync days 31-90, older data)

    Args:
        tracked_repo: TrackedRepository instance to sync
        days_back: Number of days of history to sync
        skip_recent: Skip PRs from the most recent N days (default 0)

    Returns:
        Dict with sync results (prs_synced, reviews_synced, etc.)
    """
    from asgiref.sync import async_to_sync
    from django.conf import settings

    github_config = getattr(settings, "GITHUB_API_CONFIG", {})
    use_graphql = github_config.get("USE_GRAPHQL", False)
    graphql_ops = github_config.get("GRAPHQL_OPERATIONS", {})
    initial_sync_enabled = graphql_ops.get("initial_sync", True)
    use_search_api = graphql_ops.get("use_search_api", False)  # New flag for Search API
    fallback_to_rest = github_config.get("FALLBACK_TO_REST", True)

    if use_graphql and initial_sync_enabled:
        logger.info(f"Using GraphQL API for sync: {tracked_repo.full_name}")
        try:
            # Use Search API if enabled (more accurate progress tracking)
            if use_search_api:
                from apps.integrations.services.github_graphql_sync import sync_repository_history_by_search

                logger.info(f"Using Search API for accurate progress: {tracked_repo.full_name}")
                # Run async function in sync context using async_to_sync (NOT asyncio.run!)
                result = async_to_sync(sync_repository_history_by_search)(
                    tracked_repo, days_back=days_back, skip_recent=skip_recent
                )
            else:
                from apps.integrations.services.github_graphql_sync import sync_repository_history_graphql

                # Run async function in sync context using async_to_sync (NOT asyncio.run!)
                result = async_to_sync(sync_repository_history_graphql)(
                    tracked_repo, days_back=days_back, skip_recent=skip_recent
                )

            # Check if GraphQL sync had errors
            if result.get("errors") and fallback_to_rest:
                logger.warning(
                    f"GraphQL sync had errors for {tracked_repo.full_name}: {result['errors']}, falling back to REST"
                )
                raise Exception(f"GraphQL sync errors: {result['errors']}")

            return result
        except Exception as e:
            if fallback_to_rest:
                logger.warning(f"GraphQL sync failed for {tracked_repo.full_name}: {e}, falling back to REST")
            else:
                raise

    # Use REST API (default or fallback)
    logger.info(f"Using REST API for sync: {tracked_repo.full_name}")
    from apps.integrations.services.github_sync import sync_repository_history

    return sync_repository_history(tracked_repo, days_back=days_back)


def _sync_incremental_with_graphql_or_rest(tracked_repo) -> dict:
    """Sync repository incrementally using GraphQL or REST API based on feature flags.

    Uses GraphQL API if enabled for incremental_sync operation, falling back to REST
    if GraphQL fails and fallback is enabled.

    Args:
        tracked_repo: TrackedRepository instance to sync

    Returns:
        Dict with sync results (prs_synced, reviews_synced, etc.)
    """
    from asgiref.sync import async_to_sync
    from django.conf import settings

    github_config = getattr(settings, "GITHUB_API_CONFIG", {})
    use_graphql = github_config.get("USE_GRAPHQL", False)
    graphql_ops = github_config.get("GRAPHQL_OPERATIONS", {})
    incremental_sync_enabled = graphql_ops.get("incremental_sync", True)
    fallback_to_rest = github_config.get("FALLBACK_TO_REST", True)

    if use_graphql and incremental_sync_enabled:
        logger.info(f"Using GraphQL API for incremental sync: {tracked_repo.full_name}")
        try:
            from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

            # Run async function in sync context using async_to_sync (NOT asyncio.run!)
            result = async_to_sync(sync_repository_incremental_graphql)(tracked_repo)

            # Check if GraphQL sync had errors
            if result.get("errors") and fallback_to_rest:
                logger.warning(
                    f"GraphQL incremental sync had errors for {tracked_repo.full_name}: {result['errors']}, "
                    "falling back to REST"
                )
                raise Exception(f"GraphQL sync errors: {result['errors']}")

            return result
        except Exception as e:
            if fallback_to_rest:
                logger.warning(
                    f"GraphQL incremental sync failed for {tracked_repo.full_name}: {e}, falling back to REST"
                )
            else:
                raise

    # Use REST API (default or fallback)
    logger.info(f"Using REST API for incremental sync: {tracked_repo.full_name}")
    return sync_repository_incremental(tracked_repo)


def _sync_members_with_graphql_or_rest(integration, org_slug: str) -> dict:
    """Sync organization members using GraphQL or REST API based on feature flags.

    Args:
        integration: GitHubIntegration instance with team and credential
        org_slug: GitHub organization slug

    Returns:
        dict: Sync results with created, updated, unchanged counts
    """
    from asgiref.sync import async_to_sync
    from django.conf import settings

    github_config = getattr(settings, "GITHUB_API_CONFIG", {})
    use_graphql = github_config.get("USE_GRAPHQL", False)
    graphql_ops = github_config.get("GRAPHQL_OPERATIONS", {})
    member_sync_enabled = graphql_ops.get("member_sync", False)
    fallback_to_rest = github_config.get("FALLBACK_TO_REST", True)

    if use_graphql and member_sync_enabled:
        try:
            from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

            logger.info(f"Using GraphQL for member sync: {org_slug}")
            # Run async function in sync context using async_to_sync (NOT asyncio.run!)
            result = async_to_sync(sync_github_members_graphql)(integration, org_name=org_slug)

            # If GraphQL has errors and fallback is enabled, fall back to REST
            if result.get("errors") and fallback_to_rest:
                logger.warning(f"GraphQL member sync had errors, falling back to REST: {result['errors']}")
                raise Exception(f"GraphQL errors: {result['errors']}")

            # Map GraphQL result keys to REST-style result keys for compatibility
            return {
                "created": result.get("members_created", 0),
                "updated": result.get("members_updated", 0),
                "unchanged": 0,  # GraphQL doesn't track unchanged separately
                "failed": 0 if not result.get("errors") else len(result.get("errors", [])),
            }
        except Exception as e:
            if fallback_to_rest:
                logger.warning(f"GraphQL member sync failed for {org_slug}, falling back to REST: {e}")
            else:
                raise

    # Use REST API (default or fallback)
    logger.info(f"Using REST for member sync: {org_slug}")
    return sync_github_members(
        team=integration.team,
        access_token=integration.credential.access_token,
        org_slug=org_slug,
    )


def _filter_prs_by_days(prs_data: list[dict], days_back: int = 7) -> list[dict]:
    """Filter PRs to only those created within the specified number of days.

    Args:
        prs_data: List of PR dictionaries with 'created_at' field
        days_back: Number of days to look back (default 7)

    Returns:
        Filtered list of PR dictionaries
    """
    from datetime import timedelta

    from dateutil.parser import parse as parse_date
    from django.utils import timezone

    cutoff_date = timezone.now() - timedelta(days=days_back)
    filtered = []

    for pr in prs_data:
        created_at_str = pr.get("created_at")
        if created_at_str:
            try:
                created_at = parse_date(created_at_str)
                # Make timezone-aware if needed
                if created_at.tzinfo is None:
                    from django.utils.timezone import make_aware

                    created_at = make_aware(created_at)
                if created_at >= cutoff_date:
                    filtered.append(pr)
            except (ValueError, TypeError):
                # If we can't parse the date, include it to be safe
                filtered.append(pr)
        else:
            # No date, include it
            filtered.append(pr)

    return filtered


# =============================================================================
# Repository Sync Tasks
# =============================================================================


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300, time_limit=360)
def sync_repository_task(self, repo_id: int) -> dict:
    """Sync a single tracked repository.

    A-006: Added soft_time_limit=300s, time_limit=360s to prevent API hangs.

    Args:
        self: Celery task instance (bound task)
        repo_id: ID of the TrackedRepository to sync

    Returns:
        Dict with sync results (prs_synced, reviews_synced, errors) or error/skip status
    """
    # Get TrackedRepository by id
    try:
        tracked_repo = TrackedRepository.objects.get(id=repo_id)  # noqa: TEAM001 - ID from Celery task queue
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
        result = _sync_incremental_with_graphql_or_rest(tracked_repo)
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
            # Log sync.task.retry before retrying
            from apps.utils.sync_logger import get_sync_logger

            sync_logger = get_sync_logger(__name__)
            sync_logger.warning(
                "sync.task.retry",
                extra={
                    "retry_count": self.request.retries + 1,
                    "countdown": countdown,
                    "error": str(exc),
                },
            )
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
            tracked_repo.last_sync_error = sanitize_error(exc)
            tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

            return {"error": sanitize_error(exc)}


@shared_task(bind=True, max_retries=3, default_retry_delay=30, soft_time_limit=60, time_limit=90)
def create_repository_webhook_task(self, tracked_repo_id: int, webhook_url: str) -> dict:
    """Create a GitHub webhook for a tracked repository asynchronously.

    A-006: Added soft_time_limit=60s, time_limit=90s to prevent API hangs.

    This task is queued after creating a TrackedRepository to avoid blocking
    the view response. The webhook_id is updated on the TrackedRepository
    once the webhook is successfully created.

    Args:
        self: Celery task instance (bound task)
        tracked_repo_id: ID of the TrackedRepository
        webhook_url: The URL for the webhook endpoint

    Returns:
        Dict with webhook_id on success, or error on failure
    """
    from apps.integrations.services.github_oauth import GitHubOAuthError

    # Get TrackedRepository by id
    try:
        tracked_repo = TrackedRepository.objects.select_related(  # noqa: TEAM001 - ID from Celery task queue
            "integration", "integration__credential"
        ).get(id=tracked_repo_id)
    except TrackedRepository.DoesNotExist:
        logger.error(f"TrackedRepository with id {tracked_repo_id} not found for webhook creation")
        return {"error": f"TrackedRepository with id {tracked_repo_id} not found"}

    # Get access token and webhook secret from integration
    try:
        access_token = tracked_repo.integration.credential.access_token
        webhook_secret = tracked_repo.integration.webhook_secret
    except AttributeError as e:
        logger.error(f"Failed to get credentials for webhook creation: {e}")
        return {"error": "Failed to get integration credentials"}

    # Create the webhook
    try:
        webhook_id = github_webhooks.create_repository_webhook(
            access_token=access_token,
            repo_full_name=tracked_repo.full_name,
            webhook_url=webhook_url,
            secret=webhook_secret,
        )

        # Update TrackedRepository with webhook_id
        tracked_repo.webhook_id = webhook_id
        tracked_repo.save(update_fields=["webhook_id"])

        logger.info(f"Created webhook {webhook_id} for {tracked_repo.full_name}")
        return {"webhook_id": webhook_id, "repo_id": tracked_repo_id}

    except GitHubOAuthError as e:
        logger.error(f"Failed to create webhook for {tracked_repo.full_name}: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error creating webhook for {tracked_repo.full_name}: {e}")
        return {"error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=600, time_limit=660)
def sync_repository_initial_task(self, repo_id: int, days_back: int = 30) -> dict:
    """Sync historical data for a newly tracked repository.

    A-006: Added soft_time_limit=600s (10 min), time_limit=660s (11 min) for initial sync.
    Initial sync is longer than incremental because it fetches historical data.

    Args:
        self: Celery task instance (bound task)
        repo_id: ID of the TrackedRepository to sync
        days_back: Number of days of history to sync (default 30)

    Returns:
        Dict with sync results or error status
    """
    from django.utils import timezone

    # Import here to avoid circular imports
    from apps.integrations._task_modules.metrics import aggregate_team_weekly_metrics_task

    # Get TrackedRepository by id
    try:
        tracked_repo = TrackedRepository.objects.get(id=repo_id)  # noqa: TEAM001 - ID from Celery task queue
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository with id {repo_id} not found")
        return {"error": f"TrackedRepository with id {repo_id} not found"}

    # Set status to syncing and record start time
    tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_SYNCING
    tracked_repo.sync_started_at = timezone.now()
    tracked_repo.save(update_fields=["sync_status", "sync_started_at"])

    # Sync repository history
    logger.info(f"Starting initial sync for repository: {tracked_repo.full_name} (days_back={days_back})")
    try:
        result = _sync_with_graphql_or_rest(tracked_repo, days_back=days_back)
        logger.info(f"Successfully synced repository history: {tracked_repo.full_name}")

        # Set status to complete and clear error
        tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_COMPLETE
        tracked_repo.last_sync_error = None
        tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

        # Dispatch weekly metrics aggregation for the team
        aggregate_team_weekly_metrics_task.delay(tracked_repo.team_id)

        # Send email notification
        from apps.integrations.services.sync_notifications import send_sync_complete_notification

        send_sync_complete_notification(tracked_repo, result)

        return result
    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff
            logger.warning(f"Initial sync failed for {tracked_repo.full_name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted or retry failed - log to Sentry and return error
            from sentry_sdk import capture_exception

            logger.error(f"Initial sync failed permanently for {tracked_repo.full_name}: {exc}")
            capture_exception(exc)

            # Set status to error and save error message
            tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_ERROR
            tracked_repo.last_sync_error = sanitize_error(exc)
            tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

            return {"error": sanitize_error(exc)}


@shared_task
def sync_repository_manual_task(repo_id: int) -> dict:
    """Manually trigger sync for an already-tracked repository.

    Used when user clicks the refresh/sync icon on the repos page.

    Args:
        repo_id: ID of the TrackedRepository to sync

    Returns:
        Dict with sync results or error status
    """
    from django.utils import timezone

    from apps.integrations.services import github_sync

    # Get TrackedRepository by id
    try:
        tracked_repo = TrackedRepository.objects.get(id=repo_id)  # noqa: TEAM001 - ID from Celery task queue
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository with id {repo_id} not found for manual sync")
        return {"error": f"TrackedRepository with id {repo_id} not found"}

    # Set status to syncing and record start time
    tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_SYNCING
    tracked_repo.sync_started_at = timezone.now()
    tracked_repo.save(update_fields=["sync_status", "sync_started_at"])

    # Sync repository history
    logger.info(f"Starting manual sync for repository: {tracked_repo.full_name}")
    try:
        result = github_sync.sync_repository_history(tracked_repo)
        logger.info(f"Successfully completed manual sync for: {tracked_repo.full_name}")

        # Set status to complete and clear error
        tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_COMPLETE
        tracked_repo.last_sync_error = None
        tracked_repo.last_sync_at = timezone.now()
        tracked_repo.save(update_fields=["sync_status", "last_sync_error", "last_sync_at"])

        return result
    except Exception as exc:
        from sentry_sdk import capture_exception

        logger.error(f"Manual sync failed for {tracked_repo.full_name}: {exc}")
        capture_exception(exc)

        # Set status to error and save error message
        tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_ERROR
        tracked_repo.last_sync_error = sanitize_error(exc)
        tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

        return {"error": sanitize_error(exc)}


@shared_task
def sync_all_repositories_task() -> dict:
    """Dispatch sync tasks for all active tracked repositories.

    Returns:
        Dict with counts: repos_dispatched, repos_skipped
    """
    logger.info("Starting sync for all repositories")

    # Query all tracked repositories with optimized counts
    active_repos = TrackedRepository.objects.filter(is_active=True)  # noqa: TEAM001 - System job iterating all repos
    repos_skipped = TrackedRepository.objects.filter(is_active=False).count()  # noqa: TEAM001 - System job

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


# =============================================================================
# Member Sync Tasks
# =============================================================================


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=180, time_limit=240)
def sync_github_members_task(self, integration_id: int) -> dict:
    """Sync GitHub organization members for a team.

    A-006: Added soft_time_limit=180s, time_limit=240s to prevent API hangs.

    Args:
        self: Celery task instance (bound task)
        integration_id: ID of the GitHubIntegration to sync members for

    Returns:
        Dict with sync results (created, updated, unchanged, failed) or error status
    """
    from celery.exceptions import Retry as CeleryRetry
    from django.utils import timezone

    # Get GitHubIntegration by id
    try:
        integration = GitHubIntegration.objects.select_related("team", "credential").get(id=integration_id)  # noqa: TEAM001 - ID from Celery task queue
    except GitHubIntegration.DoesNotExist:
        logger.warning(f"GitHubIntegration with id {integration_id} not found")
        return {"error": f"GitHubIntegration with id {integration_id} not found"}

    # Check if org is selected
    if not integration.organization_slug:
        logger.info(f"Skipping member sync - no org selected for team {integration.team.name}")
        return {"skipped": True, "reason": "No organization selected"}

    # Set status to syncing at start
    integration.member_sync_status = GitHubIntegration.SYNC_STATUS_SYNCING
    integration.member_sync_started_at = timezone.now()
    integration.member_sync_error = ""
    integration.save(update_fields=["member_sync_status", "member_sync_started_at", "member_sync_error"])

    # Sync members
    logger.info(f"Starting GitHub member sync for team: {integration.team.name} (org: {integration.organization_slug})")
    try:
        result = _sync_members_with_graphql_or_rest(integration, integration.organization_slug)
        logger.info(
            f"Successfully synced GitHub members for team {integration.team.name}: "
            f"created={result['created']}, updated={result['updated']}, unchanged={result['unchanged']}"
        )

        # Set status to complete on success
        integration.member_sync_status = GitHubIntegration.SYNC_STATUS_COMPLETE
        integration.member_sync_completed_at = timezone.now()
        integration.member_sync_result = result
        integration.save(update_fields=["member_sync_status", "member_sync_completed_at", "member_sync_result"])

        return result
    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            logger.warning(f"Member sync failed for {integration.team.name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except CeleryRetry:
            raise
        except Exception:
            from sentry_sdk import capture_exception

            logger.error(f"Member sync failed permanently for {integration.team.name}: {exc}")
            capture_exception(exc)

            # Set status to error on failure
            integration.member_sync_status = GitHubIntegration.SYNC_STATUS_ERROR
            integration.member_sync_error = sanitize_error(exc)
            integration.save(update_fields=["member_sync_status", "member_sync_error"])

            return {"error": sanitize_error(exc)}


@shared_task
def sync_all_github_members_task() -> dict:
    """Dispatch member sync tasks for all GitHub integrations with organizations.

    Returns:
        Dict with counts: integrations_dispatched, integrations_skipped
    """
    logger.info("Starting GitHub member sync for all teams")

    # Query all GitHub integrations with an organization selected
    integrations = GitHubIntegration.objects.exclude(organization_slug__isnull=True).exclude(organization_slug="")  # noqa: TEAM001 - System job iterating all integrations

    integrations_dispatched = 0
    integrations_skipped = 0

    for integration in integrations:
        try:
            sync_github_members_task.delay(integration.id)
            integrations_dispatched += 1
        except Exception as e:
            logger.error(f"Failed to dispatch member sync task for team {integration.team_id}: {e}")
            integrations_skipped += 1
            continue

    logger.info(
        f"Finished dispatching GitHub member sync tasks. "
        f"Dispatched: {integrations_dispatched}, Skipped: {integrations_skipped}"
    )

    return {
        "integrations_dispatched": integrations_dispatched,
        "integrations_skipped": integrations_skipped,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=180, time_limit=240)
def sync_github_app_members_task(self, installation_id: int) -> dict:
    """Sync GitHub organization members for a team using GitHub App installation (A-007).

    This is the GitHub App equivalent of sync_github_members_task. It uses
    installation tokens instead of OAuth tokens to sync organization members.

    A-006: Added soft_time_limit=180s, time_limit=240s to prevent API hangs.

    Args:
        self: Celery task instance (bound task)
        installation_id: ID of the GitHubAppInstallation to sync members for

    Returns:
        Dict with sync results (created, updated, unchanged, failed) or error status
    """
    from apps.integrations.models import GitHubAppInstallation
    from apps.integrations.services.github_app import get_installation_token
    from apps.integrations.services.member_sync import sync_github_members

    try:
        installation = GitHubAppInstallation.objects.select_related("team").get(id=installation_id)  # noqa: TEAM001 - ID from Celery task queue
    except GitHubAppInstallation.DoesNotExist:
        logger.warning(f"GitHubAppInstallation with id {installation_id} not found")
        return {"error": f"GitHubAppInstallation with id {installation_id} not found"}

    if not installation.team:
        logger.info(f"Skipping member sync - no team linked for installation {installation_id}")
        return {"skipped": True, "reason": "No team linked"}

    org_slug = installation.account_login
    if not org_slug:
        logger.info(f"Skipping member sync - no org for installation {installation_id}")
        return {"skipped": True, "reason": "No organization"}

    try:
        access_token = get_installation_token(installation.installation_id)
        result = sync_github_members(
            team=installation.team,
            access_token=access_token,
            org_slug=org_slug,
        )
        logger.info(f"GitHub App member sync completed for {org_slug}: {result}")
        return result
    except Exception as e:
        logger.error(f"GitHub App member sync failed for {org_slug}: {e}")
        raise self.retry(exc=e) from e


# =============================================================================
# Onboarding Sync Tasks
# =============================================================================


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=180, time_limit=240)
def sync_quick_data_task(self, repo_id: int) -> dict:
    """Quick sync: 7 days, pattern detection only, for fast initial insights.

    A-006: Added soft_time_limit=180s, time_limit=240s to prevent API hangs.

    After completion, queues sync_full_history_task for background full sync.

    Args:
        self: Celery task instance (bound task)
        repo_id: ID of the TrackedRepository to sync

    Returns:
        Dict with sync results or error/skip status
    """
    from django.utils import timezone

    # Import here to avoid circular imports
    from apps.integrations._task_modules.metrics import aggregate_team_weekly_metrics_task
    from apps.metrics.models import PullRequest
    from apps.metrics.services.ai_detector import detect_ai_in_text

    # Get TrackedRepository by id
    try:
        tracked_repo = TrackedRepository.objects.get(id=repo_id)  # noqa: TEAM001 - ID from Celery task queue
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository with id {repo_id} not found")
        return {"error": f"TrackedRepository with id {repo_id} not found"}

    # Check if repo is active
    if not tracked_repo.is_active:
        logger.info(f"Skipping inactive repository: {tracked_repo.full_name}")
        return {"skipped": True, "reason": "Repository is not active"}

    # Set status to syncing and record start time
    tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_SYNCING
    tracked_repo.sync_started_at = timezone.now()
    tracked_repo.save(update_fields=["sync_status", "sync_started_at"])

    # Sync repository with 7 days window (quick sync)
    logger.info(f"Starting quick sync for repository: {tracked_repo.full_name} (days_back=7)")
    try:
        result = _sync_with_graphql_or_rest(tracked_repo, days_back=7)
        prs_synced = result.get("prs_synced", 0)
        reviews_synced = result.get("reviews_synced", 0)

        logger.info(f"Successfully completed quick sync for repository: {tracked_repo.full_name}")

        # Run pattern detection on recently synced PRs (skip LLM)
        prs_to_detect = PullRequest.objects.filter(
            team=tracked_repo.team,
            github_repo=tracked_repo.full_name,
            is_ai_assisted__isnull=True,  # Only PRs that haven't been processed
        )

        # Process each PR with pattern detection
        prs_detected_count = 0
        for pr in prs_to_detect:
            # Combine title and body for detection
            text_to_analyze = f"{pr.title or ''}\n{pr.body or ''}"
            detection_result = detect_ai_in_text(text_to_analyze)
            pr.is_ai_assisted = detection_result["is_ai_assisted"]
            if detection_result["ai_tools"]:
                pr.ai_tools_detected = detection_result["ai_tools"]
            pr.save(update_fields=["is_ai_assisted", "ai_tools_detected"])
            prs_detected_count += 1

        # If we synced PRs but none needed detection, still verify detection is working
        if prs_synced > 0 and prs_detected_count == 0:
            # Call detect_ai_in_text once to verify the detection pipeline is active
            detect_ai_in_text("")

        # Set status to complete and clear error
        tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_COMPLETE
        tracked_repo.last_sync_error = None
        tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

        # Dispatch metrics aggregation for immediate dashboard data
        aggregate_team_weekly_metrics_task.delay(tracked_repo.team_id)

        # Queue full history sync for background processing
        sync_full_history_task.delay(repo_id)
        logger.info(f"Queued full history sync for repository: {tracked_repo.full_name}")

        return {
            "prs_synced": prs_synced,
            "reviews_synced": reviews_synced,
            "full_sync_queued": True,
        }
    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff
            logger.warning(f"Quick sync failed for {tracked_repo.full_name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted - try direct PR fetch as fallback
            try:
                access_token = tracked_repo.integration.credential.access_token
                all_prs = get_repository_pull_requests(access_token, tracked_repo.full_name)
                filtered_prs = _filter_prs_by_days(all_prs, days_back=7)
                prs_synced = len(filtered_prs)

                # Run pattern detection on PRs in database
                prs_to_detect = PullRequest.objects.filter(
                    team=tracked_repo.team,
                    github_repo=tracked_repo.full_name,
                    is_ai_assisted__isnull=True,
                )
                for pr in prs_to_detect:
                    text_to_analyze = f"{pr.title or ''}\n{pr.body or ''}"
                    detection_result = detect_ai_in_text(text_to_analyze)
                    pr.is_ai_assisted = detection_result["is_ai_assisted"]
                    if detection_result["ai_tools"]:
                        pr.ai_tools_detected = detection_result["ai_tools"]
                    pr.save(update_fields=["is_ai_assisted", "ai_tools_detected"])

                # Set status to complete
                tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_COMPLETE
                tracked_repo.last_sync_error = None
                tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

                # Queue full history sync
                sync_full_history_task.delay(repo_id)

                return {
                    "prs_synced": prs_synced,
                    "reviews_synced": 0,
                    "full_sync_queued": True,
                }
            except Exception:
                # Fallback also failed - log to Sentry and return error
                from sentry_sdk import capture_exception

                logger.error(f"Quick sync failed permanently for {tracked_repo.full_name}: {exc}")
                capture_exception(exc)

                # Set status to error and save error message
                tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_ERROR
                tracked_repo.last_sync_error = sanitize_error(exc)
                tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

                return {"error": sanitize_error(exc)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=900, time_limit=960)
def sync_full_history_task(self, repo_id: int, days_back: int = 90) -> dict:
    """Full historical sync with LLM analysis, runs in background after quick sync.

    A-006: Added soft_time_limit=900s (15 min), time_limit=960s (16 min) for full history sync.
    Longer timeout than initial sync because it fetches 90 days of history.

    Args:
        self: Celery task instance (bound task)
        repo_id: ID of the TrackedRepository to sync
        days_back: Number of days of history to sync (default 90)

    Returns:
        Dict with sync results or error/skip status
    """
    from django.utils import timezone

    # Import here to avoid circular imports
    from apps.integrations._task_modules.metrics import aggregate_team_weekly_metrics_task

    # Get TrackedRepository by id
    try:
        tracked_repo = TrackedRepository.objects.get(id=repo_id)  # noqa: TEAM001 - ID from Celery task queue
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository with id {repo_id} not found")
        return {"error": f"TrackedRepository with id {repo_id} not found"}

    # Check if repo is active
    if not tracked_repo.is_active:
        logger.info(f"Skipping inactive repository: {tracked_repo.full_name}")
        return {"skipped": True, "reason": "Repository is not active"}

    # Set status to syncing
    tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_SYNCING
    tracked_repo.sync_started_at = timezone.now()
    tracked_repo.save(update_fields=["sync_status", "sync_started_at"])

    # Sync repository with full history
    logger.info(f"Starting full history sync for repository: {tracked_repo.full_name} (days_back={days_back})")
    try:
        result = _sync_with_graphql_or_rest(tracked_repo, days_back=days_back)
        logger.info(f"Successfully completed full history sync for repository: {tracked_repo.full_name}")

        # Set status to complete and clear error
        tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_COMPLETE
        tracked_repo.last_sync_error = None
        tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

        # Dispatch weekly metrics aggregation for the team
        aggregate_team_weekly_metrics_task.delay(tracked_repo.team_id)

        return {
            "prs_synced": result.get("prs_synced", 0),
            "reviews_synced": result.get("reviews_synced", 0),
        }
    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff
            logger.warning(f"Full history sync failed for {tracked_repo.full_name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted or retry failed - log to Sentry and return error
            from sentry_sdk import capture_exception

            logger.error(f"Full history sync failed permanently for {tracked_repo.full_name}: {exc}")
            capture_exception(exc)

            # Set status to error and save error message
            tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_ERROR
            tracked_repo.last_sync_error = sanitize_error(exc)
            tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

            return {"error": sanitize_error(exc)}


@shared_task(bind=True, soft_time_limit=1800, time_limit=1860)
def sync_historical_data_task(
    self,
    team_id: int,
    repo_ids: list[int],
    days_back: int = 90,
    skip_recent: int = 0,
) -> dict:
    """
    Sync historical PR data for selected repositories during onboarding.

    A-006: Added soft_time_limit=1800s (30 min), time_limit=1860s (31 min).
    This is the main onboarding sync task and needs a generous timeout for large repos.

    This task fetches historical data for newly connected repositories,
    processes PRs through LLM for AI detection, and reports real-time progress.

    Supports two-phase onboarding:
    - Phase 1: days_back=30, skip_recent=0 (sync recent 30 days)
    - Phase 2: days_back=90, skip_recent=30 (sync days 31-90, older data)

    Args:
        team_id: ID of the team
        repo_ids: List of TrackedRepository IDs to sync
        days_back: How many days of history to sync (default: 90)
        skip_recent: Skip PRs from the most recent N days (default: 0)

    Returns:
        Dict with sync results (status, repos_synced, total_prs)
    """
    from django.utils import timezone

    from apps.integrations.services.historical_sync import prioritize_repositories
    from apps.integrations.services.onboarding_sync import OnboardingSyncService
    from apps.integrations.signals import (
        onboarding_sync_completed,
        onboarding_sync_started,
        repository_sync_completed,
    )
    from apps.teams.models import Team

    # Log task entry
    logger.info(
        f"[SYNC_TASK] Starting sync_historical_data_task: "
        f"team_id={team_id}, repo_ids={repo_ids}, task_id={self.request.id}"
    )

    try:
        team = Team.objects.get(id=team_id)
        logger.info(f"[SYNC_TASK] Found team: {team.name} (id={team_id})")
    except Team.DoesNotExist:
        logger.error(f"[SYNC_TASK] Team with id {team_id} not found")
        return {"status": "error", "error": f"Team {team_id} not found"}

    repos = TrackedRepository.objects.filter(
        id__in=repo_ids,
        team=team,
    )  # noqa: TEAM001 - IDs from Celery task queue

    if not repos.exists():
        return {"status": "complete", "repos_synced": 0, "total_prs": 0}

    # Prioritize repos by recent activity
    sorted_repos = prioritize_repositories(repos)

    total_repos = len(sorted_repos)
    total_prs = 0
    failed_repos = 0

    # Get GitHub token from integration
    try:
        integration = GitHubIntegration.objects.get(team=team)
        logger.info(f"[SYNC_TASK] Found GitHubIntegration for team {team_id}, org={integration.organization_slug}")

        # Access token through encrypted field descriptor
        github_token = integration.credential.access_token
        token_prefix = github_token[:10] if github_token else "None"
        logger.info(
            f"[SYNC_TASK] Token access successful: {token_prefix}... (len={len(github_token) if github_token else 0})"
        )

        if not github_token:
            logger.error(f"[SYNC_TASK] Token is empty for team {team_id}")
            return {"status": "error", "error": "GitHub token is empty"}

    except GitHubIntegration.DoesNotExist:
        logger.error(f"[SYNC_TASK] No GitHub integration found for team {team_id}")
        return {"status": "error", "error": "GitHub integration not configured"}
    except Exception as e:
        logger.error(f"[SYNC_TASK] Failed to get GitHub token for team {team_id}: {type(e).__name__}: {e}")
        return {"status": "error", "error": f"Token access failed: {type(e).__name__}"}

    # Send sync started signal
    onboarding_sync_started.send(
        sender=sync_historical_data_task,
        team_id=team_id,
        repo_ids=repo_ids,
    )

    service = OnboardingSyncService(team=team, github_token=github_token)

    # Import sync_logger inside function so mocks in tests work correctly
    from apps.utils.sync_logger import get_sync_logger

    sync_logger = get_sync_logger(__name__)

    for idx, repo in enumerate(sorted_repos, 1):
        logger.info(f"[SYNC_TASK] Starting sync for repo {idx}/{total_repos}: {repo.full_name} (id={repo.id})")

        # Log sync.repo.started
        sync_logger.info(
            "sync.repo.started",
            extra={
                "team_id": team_id,
                "repo_id": repo.id,
                "full_name": repo.full_name,
            },
        )

        # Update repo status to syncing
        repo.sync_status = "syncing"
        repo.sync_started_at = timezone.now()
        repo.save(update_fields=["sync_status", "sync_started_at"])

        # Report overall progress to celery-progress endpoint (A-020 fix)
        # Guard: only update if we have a task ID (not when called directly in tests)
        if self.request.id:
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": idx,
                    "total": total_repos,
                    "description": f"Syncing {repo.full_name}...",
                },
            )

        repo_sync_start_time = time.time()

        try:
            # Define progress callback for celery_progress
            # Use default argument to capture current repo value (avoids B023 closure issue)
            # Also capture sync_logger, self, idx, total_repos to avoid closure issues
            def progress_callback(
                prs_completed: int,
                prs_total: int,
                message: str,
                current_repo=repo,
                _sync_logger=sync_logger,
                _task=self,
                _repo_idx=idx,
                _total_repos=total_repos,
            ):
                # Update repo progress
                if prs_total > 0:
                    current_repo.sync_progress = int((prs_completed / prs_total) * 100)
                    current_repo.sync_prs_completed = prs_completed
                    current_repo.sync_prs_total = prs_total
                    current_repo.save(update_fields=["sync_progress", "sync_prs_completed", "sync_prs_total"])

                    # Report to celery-progress for main progress bar (A-020 fix)
                    # Guard: only update if we have a task ID (not when called directly in tests)
                    pct = int((prs_completed / prs_total) * 100)
                    if _task.request.id:
                        _task.update_state(
                            state="PROGRESS",
                            meta={
                                "current": prs_completed,
                                "total": prs_total,
                                "description": f"Syncing {current_repo.full_name}: {pct}%",
                            },
                        )

                    # Log sync.repo.progress
                    _sync_logger.info(
                        "sync.repo.progress",
                        extra={
                            "prs_done": prs_completed,
                            "prs_total": prs_total,
                            "pct": pct,
                            "repo_id": current_repo.id,
                        },
                    )

            # Sync the repository with date range parameters
            result = service.sync_repository(
                repo=repo,
                progress_callback=progress_callback,
                days_back=days_back,
                skip_recent=skip_recent,
            )
            prs_synced = result.get("prs_synced", 0)
            total_prs += prs_synced

            # Calculate duration
            repo_sync_duration = time.time() - repo_sync_start_time

            # Mark as completed
            repo.sync_status = "completed"
            repo.last_sync_at = timezone.now()
            repo.last_sync_error = None
            repo.save(update_fields=["sync_status", "last_sync_at", "last_sync_error"])

            # Send repository sync completed signal
            repository_sync_completed.send(
                sender=sync_historical_data_task,
                team_id=team_id,
                repo_id=repo.id,
                prs_synced=prs_synced,
            )

            # Log sync.repo.completed
            sync_logger.info(
                "sync.repo.completed",
                extra={
                    "team_id": team_id,
                    "repo_id": repo.id,
                    "prs_synced": prs_synced,
                    "duration_seconds": repo_sync_duration,
                },
            )

            logger.info(f"[SYNC_TASK] Completed sync for {repo.full_name}: {prs_synced} PRs synced")

        except Exception as e:
            logger.error(f"[SYNC_TASK] Failed to sync {repo.full_name}: {type(e).__name__}: {e}")
            failed_repos += 1

            # Log sync.repo.failed
            sync_logger.error(
                "sync.repo.failed",
                extra={
                    "team_id": team_id,
                    "repo_id": repo.id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            # Mark as failed
            repo.sync_status = "failed"
            repo.last_sync_error = str(e)
            repo.save(update_fields=["sync_status", "last_sync_error"])

    # Send sync completed signal
    repos_synced = total_repos - failed_repos
    onboarding_sync_completed.send(
        sender=sync_historical_data_task,
        team_id=team_id,
        repos_synced=repos_synced,
        failed_repos=failed_repos,
        total_prs=total_prs,
    )

    logger.info(
        f"[SYNC_TASK] Task completed: team_id={team_id}, task_id={self.request.id}, "
        f"repos_synced={repos_synced}, failed_repos={failed_repos}, total_prs={total_prs}"
    )

    # Signal-based pipeline: update status to trigger next task
    # Determine which phase we're in based on skip_recent parameter
    team.refresh_from_db()
    if skip_recent == 0:
        # Phase 1: next is LLM processing
        team.update_pipeline_status("llm_processing")
    else:
        # Phase 2: next is background LLM processing
        team.update_pipeline_status("background_llm")

    return {
        "status": "complete",
        "repos_synced": repos_synced,
        "failed_repos": failed_repos,
        "total_prs": total_prs,
    }
