"""Celery tasks for integrations."""

import logging
import time

from celery import shared_task
from celery.exceptions import Retry
from github import GithubException

from apps.integrations.models import (
    GitHubIntegration,
    JiraIntegration,
    SlackIntegration,
    TrackedJiraProject,
    TrackedRepository,
)
from apps.integrations.services import github_comments, github_pr_description, github_sync, github_webhooks
from apps.integrations.services.copilot_metrics import (
    CopilotMetricsError,
    fetch_copilot_metrics,
    map_copilot_to_ai_usage,
    parse_metrics_response,
)
from apps.integrations.services.github_sync import get_repository_pull_requests, sync_repository_incremental
from apps.integrations.services.groq_batch import GroqBatchProcessor
from apps.integrations.services.jira_sync import sync_project_issues
from apps.integrations.services.jira_user_matching import sync_jira_users
from apps.integrations.services.member_sync import sync_github_members
from apps.integrations.services.slack_client import get_slack_client, send_channel_message, send_dm
from apps.integrations.services.slack_leaderboard import (
    build_leaderboard_blocks,
    compute_weekly_leaderboard,
    should_post_leaderboard,
)
from apps.integrations.services.slack_surveys import (
    build_author_survey_blocks,
    build_reveal_correct_blocks,
    build_reveal_wrong_blocks,
    build_reviewer_survey_blocks,
)
from apps.integrations.services.slack_user_matching import sync_slack_users
from apps.metrics.models import PRReview, PRSurveyReview, PullRequest
from apps.metrics.services.aggregation_service import aggregate_team_weekly_metrics
from apps.metrics.services.survey_service import create_pr_survey, create_reviewer_survey, get_reviewer_accuracy_stats
from apps.teams.models import Team
from apps.utils.errors import sanitize_error

logger = logging.getLogger(__name__)


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


def _sync_with_graphql_or_rest(tracked_repo, days_back: int) -> dict:
    """Sync repository using GraphQL or REST API based on feature flags.

    Uses GraphQL API if enabled for initial_sync operation, falling back to REST
    if GraphQL fails and fallback is enabled.

    Args:
        tracked_repo: TrackedRepository instance to sync
        days_back: Number of days of history to sync

    Returns:
        Dict with sync results (prs_synced, reviews_synced, etc.)
    """
    from asgiref.sync import async_to_sync
    from django.conf import settings

    github_config = getattr(settings, "GITHUB_API_CONFIG", {})
    use_graphql = github_config.get("USE_GRAPHQL", False)
    graphql_ops = github_config.get("GRAPHQL_OPERATIONS", {})
    initial_sync_enabled = graphql_ops.get("initial_sync", True)
    fallback_to_rest = github_config.get("FALLBACK_TO_REST", True)

    if use_graphql and initial_sync_enabled:
        logger.info(f"Using GraphQL API for sync: {tracked_repo.full_name}")
        try:
            from apps.integrations.services.github_graphql_sync import sync_repository_history_graphql

            # Run async function in sync context using async_to_sync
            # NOTE: Using async_to_sync instead of asyncio.run() is critical!
            # asyncio.run() creates a new event loop which breaks @sync_to_async
            # decorators' thread handling, causing DB operations to silently fail.
            sync_graphql = async_to_sync(sync_repository_history_graphql)
            result = sync_graphql(tracked_repo, days_back=days_back)

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

            # Run async function in sync context using async_to_sync
            # NOTE: async_to_sync properly manages event loop + thread context for Django DB
            sync_graphql = async_to_sync(sync_repository_incremental_graphql)
            result = sync_graphql(tracked_repo)

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
            # Use async_to_sync for proper Django DB thread context management
            sync_members = async_to_sync(sync_github_members_graphql)
            result = sync_members(integration, org_name=org_slug)

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=300, time_limit=360)
def sync_jira_project_task(self, project_id: int) -> dict:
    """Sync a single tracked Jira project.

    A-006: Added soft_time_limit=300s, time_limit=360s to prevent Jira API hangs.

    Args:
        self: Celery task instance (bound task)
        project_id: ID of the TrackedJiraProject to sync

    Returns:
        Dict with sync results (issues_created, issues_updated, errors) or error/skip status
    """
    # Get TrackedJiraProject by id
    try:
        tracked_project = TrackedJiraProject.objects.get(id=project_id)  # noqa: TEAM001 - ID from Celery task queue
    except TrackedJiraProject.DoesNotExist:
        logger.warning(f"TrackedJiraProject with id {project_id} not found")
        return {"error": f"TrackedJiraProject with id {project_id} not found"}

    # Check if project is active
    if not tracked_project.is_active:
        logger.info(f"Skipping inactive Jira project: {tracked_project.jira_project_key}")
        return {"skipped": True, "reason": "Project is not active"}

    # Set status to syncing
    tracked_project.sync_status = TrackedJiraProject.SYNC_STATUS_SYNCING
    tracked_project.save(update_fields=["sync_status"])

    # Sync the project
    logger.info(f"Starting sync for Jira project: {tracked_project.jira_project_key}")
    try:
        result = sync_project_issues(tracked_project)
        logger.info(f"Successfully synced Jira project: {tracked_project.jira_project_key}")

        # Set status to complete and clear error
        tracked_project.sync_status = TrackedJiraProject.SYNC_STATUS_COMPLETE
        tracked_project.last_sync_error = None
        tracked_project.save(update_fields=["sync_status", "last_sync_error"])

        return result
    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff
            logger.warning(f"Sync failed for {tracked_project.jira_project_key}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted - log to Sentry and return error
            from sentry_sdk import capture_exception

            logger.error(f"Sync failed permanently for {tracked_project.jira_project_key}: {exc}")
            capture_exception(exc)

            # Set status to error and save error message
            tracked_project.sync_status = TrackedJiraProject.SYNC_STATUS_ERROR
            tracked_project.last_sync_error = sanitize_error(exc)
            tracked_project.save(update_fields=["sync_status", "last_sync_error"])

            return {"error": sanitize_error(exc)}


@shared_task
def sync_all_jira_projects_task() -> dict:
    """Dispatch sync tasks for all active tracked Jira projects.

    Returns:
        Dict with counts: projects_dispatched, projects_skipped
    """
    logger.info("Starting sync for all Jira projects")

    # Query all tracked Jira projects
    active_projects = TrackedJiraProject.objects.filter(is_active=True)  # noqa: TEAM001 - System job iterating all projects
    projects_skipped = TrackedJiraProject.objects.filter(is_active=False).count()  # noqa: TEAM001 - System job

    projects_dispatched = 0

    # Dispatch sync task for each active project
    for project in active_projects:
        try:
            sync_jira_project_task.delay(project.id)
            projects_dispatched += 1
        except Exception as e:
            # Log dispatch errors and continue with remaining projects
            logger.error(f"Failed to dispatch sync task for Jira project {project.jira_project_key}: {e}")
            continue

    logger.info(f"Finished dispatching Jira sync tasks. Dispatched: {projects_dispatched}, Skipped: {projects_skipped}")

    return {
        "projects_dispatched": projects_dispatched,
        "projects_skipped": projects_skipped,
    }


@shared_task
def sync_jira_users_task(team_id: int) -> dict:
    """Sync Jira users to TeamMembers for a team.

    Args:
        team_id: ID of the Team to sync users for

    Returns:
        Dict with sync results or error status
    """
    # Get Team by id
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": f"Team with id {team_id} not found"}

    # Get Jira integration for team
    try:
        jira_integration = JiraIntegration.objects.get(team=team)
        credential = jira_integration.credential
    except JiraIntegration.DoesNotExist:
        logger.warning(f"No Jira integration found for team {team.name}")
        return {"error": f"No Jira integration found for team {team.name}"}

    # Sync users
    logger.info(f"Starting Jira user sync for team: {team.name}")
    try:
        result = sync_jira_users(team, credential)
        logger.info(f"Successfully synced Jira users for team: {team.name}")
        return result
    except Exception as exc:
        logger.error(f"Failed to sync Jira users for team {team.name}: {exc}")
        return {"error": sanitize_error(exc)}


@shared_task
def send_pr_surveys_task(pull_request_id: int) -> dict:
    """Send surveys for a merged PR.

    1. Get PR and check if merged
    2. Get SlackIntegration for team (check surveys_enabled)
    3. Create PRSurvey using survey_service
    4. Send author DM (if author has slack_user_id)
    5. Send reviewer DMs (for each reviewer with slack_user_id)

    Args:
        pull_request_id: ID of the PullRequest to send surveys for

    Returns:
        Dict with keys: author_sent (bool), reviewers_sent (int), errors (list)
    """
    # Get PR by ID with related author for efficiency
    try:
        pr = PullRequest.objects.select_related("author", "team").get(id=pull_request_id)  # noqa: TEAM001 - ID from Celery task
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pull_request_id} not found")
        return {"error": f"PullRequest with id {pull_request_id} not found"}

    # Check if PR is merged
    if pr.state != "merged":
        logger.info(f"Skipping survey for non-merged PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "PR is not merged"}

    # Get SlackIntegration for team
    try:
        slack_integration = SlackIntegration.objects.get(team=pr.team)
    except SlackIntegration.DoesNotExist:
        logger.info(f"No Slack integration found for team {pr.team.name}")
        return {"skipped": True, "reason": "No Slack integration"}

    # Check if surveys are enabled
    if not slack_integration.surveys_enabled:
        logger.info(f"Surveys disabled for team {pr.team.name}")
        return {"skipped": True, "reason": "Surveys disabled"}

    # Get existing survey or create new one
    from apps.metrics.models import PRSurvey

    existing_survey = PRSurvey.objects.filter(pull_request=pr).first()  # noqa: TEAM001 - filtering by team-scoped PR
    if existing_survey:
        survey = existing_survey
        logger.info(f"Using existing survey {survey.id} for PR {pr.github_pr_id}")
    else:
        survey = create_pr_survey(pr)
        logger.info(f"Created survey {survey.id} for PR {pr.github_pr_id}")

    # Get Slack client
    client = get_slack_client(slack_integration.credential)

    # Track results
    author_sent = False
    author_skipped = False
    reviewers_sent = 0
    reviewers_skipped = 0
    errors = []

    # Send author DM if author has slack_user_id
    if pr.author and pr.author.slack_user_id:
        # Check if author already responded via GitHub (author_ai_assisted is set to a boolean value)
        if survey.has_author_responded():
            logger.info(f"Skipping author {pr.author.display_name} - already responded via GitHub")
            author_skipped = True
        else:
            try:
                blocks = build_author_survey_blocks(pr, survey)
                send_dm(client, pr.author.slack_user_id, blocks, text="PR Survey")
                author_sent = True
                logger.info(f"Sent author survey to {pr.author.display_name}")
            except Exception as e:
                error_msg = f"Failed to send author DM: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

    # Get unique reviewers from PR reviews
    reviewers = (
        PRReview.objects.filter(pull_request=pr)  # noqa: TEAM001 - filtering by team-scoped PR
        .select_related("reviewer")
        .exclude(reviewer__isnull=True)
        .values_list("reviewer", flat=True)
        .distinct()
    )
    # Convert IDs back to TeamMember objects
    from apps.metrics.models import TeamMember

    reviewers = TeamMember.objects.filter(id__in=reviewers)  # noqa: TEAM001 - IDs from team-scoped queryset

    # Optimize: Fetch all responded reviewer IDs in a single query to avoid N+1
    responded_reviewer_ids = set(
        PRSurveyReview.objects.filter(survey_id=survey.id, responded_at__isnull=False).values_list(  # noqa: TEAM001 - filtering by team-scoped survey
            "reviewer_id", flat=True
        )
    )

    # Send reviewer DMs
    for reviewer in reviewers:
        if not reviewer.slack_user_id:
            logger.info(f"Skipping reviewer {reviewer.display_name} - no slack_user_id")
            continue

        # Check if reviewer already responded via GitHub
        if reviewer.id in responded_reviewer_ids:
            logger.info(f"Skipping reviewer {reviewer.display_name} - already responded via GitHub")
            reviewers_skipped += 1
            continue

        try:
            # Create reviewer survey entry if it doesn't exist (idempotency check)
            if not PRSurveyReview.objects.filter(survey_id=survey.id, reviewer_id=reviewer.id).exists():  # noqa: TEAM001 - filtering by team-scoped survey
                create_reviewer_survey(survey, reviewer)

            # Build and send reviewer survey blocks
            blocks = build_reviewer_survey_blocks(pr, survey, reviewer)
            send_dm(client, reviewer.slack_user_id, blocks, text="PR Review Survey")
            reviewers_sent += 1
            logger.info(f"Sent reviewer survey to {reviewer.display_name}")
        except Exception as e:
            error_msg = f"Failed to send reviewer DM to {reviewer.display_name}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        "author_sent": author_sent,
        "author_skipped": author_skipped,
        "reviewers_sent": reviewers_sent,
        "reviewers_skipped": reviewers_skipped,
        "errors": errors,
    }


@shared_task
def send_reveal_task(survey_review_id: int) -> dict:
    """Send reveal message to a reviewer.

    1. Get PRSurveyReview
    2. Check if reveal should be sent (author responded, reveals_enabled)
    3. Calculate accuracy stats
    4. Send reveal message

    Args:
        survey_review_id: ID of the PRSurveyReview to send reveal for

    Returns:
        Dict with keys: sent (bool), error (str | None)
    """
    # Get PRSurveyReview
    try:
        survey_review = PRSurveyReview.objects.select_related("survey", "reviewer", "survey__team").get(  # noqa: TEAM001 - ID from Celery task
            id=survey_review_id
        )
    except PRSurveyReview.DoesNotExist:
        logger.warning(f"PRSurveyReview with id {survey_review_id} not found")
        return {"sent": False, "error": f"PRSurveyReview with id {survey_review_id} not found"}

    survey = survey_review.survey
    reviewer = survey_review.reviewer

    # Check if author has responded
    if survey.author_ai_assisted is None:
        logger.info(f"Skipping reveal for survey {survey.id} - author has not responded")
        return {"sent": False, "error": "Author has not responded yet"}

    # Check if reviewer is valid
    if not reviewer:
        logger.warning(f"Skipping reveal for survey_review {survey_review_id} - no reviewer")
        return {"sent": False, "error": "No reviewer found"}

    # Check if reviewer has slack_user_id
    if not reviewer.slack_user_id:
        logger.info(f"Skipping reveal for reviewer {reviewer.display_name} - no slack_user_id")
        return {"sent": False, "error": "Reviewer has no slack_user_id"}

    # Get SlackIntegration and check reveals_enabled
    try:
        slack_integration = SlackIntegration.objects.get(team=survey.team)
    except SlackIntegration.DoesNotExist:
        logger.info(f"No Slack integration found for team {survey.team.name}")
        return {"sent": False, "error": "No Slack integration"}

    if not slack_integration.reveals_enabled:
        logger.info(f"Reveals disabled for team {survey.team.name}")
        return {"sent": False, "error": "Reveals disabled"}

    # Calculate accuracy stats
    accuracy_stats = get_reviewer_accuracy_stats(reviewer)

    # Get Slack client
    client = get_slack_client(slack_integration.credential)

    # Build reveal blocks based on correctness
    was_ai_assisted = survey.author_ai_assisted
    guess_correct = survey_review.ai_guess == was_ai_assisted

    if guess_correct:
        blocks = build_reveal_correct_blocks(reviewer, was_ai_assisted, accuracy_stats)
    else:
        blocks = build_reveal_wrong_blocks(reviewer, was_ai_assisted, accuracy_stats)

    # Send reveal message
    try:
        send_dm(client, reviewer.slack_user_id, blocks, text="Survey Reveal")
        logger.info(f"Sent reveal to {reviewer.display_name} for survey {survey.id}")
        return {"sent": True, "error": None}
    except Exception as e:
        error_msg = f"Failed to send reveal DM: {e}"
        logger.error(error_msg)
        return {"sent": False, "error": error_msg}


@shared_task
def sync_slack_users_task(team_id: int) -> dict:
    """Sync Slack users to TeamMembers for a team.

    Args:
        team_id: ID of the Team to sync users for

    Returns:
        Dict with sync results: matched_count, unmatched_count, unmatched_users
    """
    # Get Team by id
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": f"Team with id {team_id} not found"}

    # Get Slack integration for team
    try:
        slack_integration = SlackIntegration.objects.get(team=team)
        credential = slack_integration.credential
    except SlackIntegration.DoesNotExist:
        logger.warning(f"No Slack integration found for team {team.name}")
        return {"error": f"No Slack integration found for team {team.name}"}

    # Sync users
    logger.info(f"Starting Slack user sync for team: {team.name}")
    try:
        result = sync_slack_users(team, credential)
        logger.info(f"Successfully synced Slack users for team: {team.name}")
        return result
    except Exception as exc:
        logger.error(f"Failed to sync Slack users for team {team.name}: {exc}")
        return {"error": sanitize_error(exc)}


@shared_task
def post_weekly_leaderboards_task() -> dict:
    """Check all teams and post leaderboards where appropriate.

    Returns: {teams_checked: int, leaderboards_posted: int, errors: list}
    """
    from datetime import date, timedelta

    logger.info("Starting weekly leaderboard check")

    teams_checked = 0
    leaderboards_posted = 0
    errors = []

    # Get all SlackIntegrations
    integrations = SlackIntegration.objects.select_related("team", "credential").all()  # noqa: TEAM001 - System job iterating all integrations

    for integration in integrations:
        teams_checked += 1

        # Check if we should post now
        if not should_post_leaderboard(integration):
            logger.debug(f"Skipping leaderboard for team {integration.team.name} - not scheduled for now")
            continue

        # Check if channel is configured
        if not integration.leaderboard_channel_id:
            logger.warning(f"Skipping leaderboard for team {integration.team.name} - no channel configured")
            errors.append(f"{integration.team.name}: No leaderboard channel configured")
            continue

        try:
            # Calculate week start (last Monday)
            today = date.today()
            week_start = today - timedelta(days=today.weekday() + 7)  # Previous Monday

            # Compute leaderboard data
            leaderboard_data = compute_weekly_leaderboard(integration.team, week_start)

            # Build date range string
            week_end = week_start + timedelta(days=6)
            date_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"

            # Build blocks
            blocks = build_leaderboard_blocks(leaderboard_data, date_range)

            # Get Slack client and send message
            client = get_slack_client(integration.credential)
            send_channel_message(
                client, integration.leaderboard_channel_id, blocks, text=f"Weekly Leaderboard - {date_range}"
            )

            leaderboards_posted += 1
            logger.info(f"Posted leaderboard for team {integration.team.name}")

        except Exception as e:
            error_msg = f"{integration.team.name}: {str(e)}"
            logger.error(f"Failed to post leaderboard for team {integration.team.name}: {e}")
            errors.append(error_msg)

    logger.info(
        f"Leaderboard check complete. Checked: {teams_checked}, Posted: {leaderboards_posted}, Errors: {len(errors)}"
    )

    return {
        "teams_checked": teams_checked,
        "leaderboards_posted": leaderboards_posted,
        "errors": errors,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=180, time_limit=240)
def sync_copilot_metrics_task(self, team_id: int) -> dict:
    """Sync Copilot metrics for a team.

    A-006: Added soft_time_limit=180s, time_limit=240s to prevent GitHub API hangs.

    Args:
        self: Celery task instance (bound task)
        team_id: ID of the Team to sync Copilot metrics for

    Returns:
        Dict with sync results (metrics_synced) or error/skip status
    """
    from apps.metrics.models import AIUsageDaily, TeamMember

    # Get Team by id
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": f"Team with id {team_id} not found"}

    # Get GitHubIntegration for team
    try:
        github_integration = GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        logger.info(f"No GitHub integration found for team {team.name}")
        return {"skipped": True, "reason": "No GitHub integration"}

    # Get access token and org_slug
    access_token = github_integration.credential.access_token
    org_slug = github_integration.organization_slug

    if not org_slug:
        logger.info(f"No organization selected for team {team.name}")
        return {"skipped": True, "reason": "No organization selected"}

    # Fetch Copilot metrics
    logger.info(f"Starting Copilot metrics sync for team: {team.name} (org: {org_slug})")
    try:
        raw_metrics = fetch_copilot_metrics(access_token, org_slug, since=None, until=None)
        parsed_metrics = parse_metrics_response(raw_metrics)

        metrics_synced = 0

        # Batch fetch all TeamMembers for per-user data (fix N+1 query)
        all_usernames = set()
        for day_data in parsed_metrics:
            if "per_user_data" in day_data:
                for user_data in day_data["per_user_data"]:
                    username = user_data.get("github_username")
                    if username:
                        all_usernames.add(username)

        # Single query to fetch all team members by username
        members_by_username = {
            m.github_username: m for m in TeamMember.objects.filter(team=team, github_username__in=all_usernames)
        }

        # Process each day's metrics
        for day_data in parsed_metrics:
            # Check if there's per-user data
            if "per_user_data" in day_data:
                # Create records for each user
                for user_data in day_data["per_user_data"]:
                    github_username = user_data.get("github_username")
                    if not github_username:
                        continue

                    # Find matching TeamMember from pre-fetched dict (O(1) lookup)
                    member = members_by_username.get(github_username)
                    if not member:
                        logger.warning(
                            f"No TeamMember found with github_username={github_username} for team {team.name}"
                        )
                        continue

                    # Map user data to AIUsageDaily fields
                    mapped_data = map_copilot_to_ai_usage(user_data, github_username=github_username)

                    # Store in AIUsageDaily
                    AIUsageDaily.objects.update_or_create(
                        team=team,
                        member=member,
                        date=mapped_data["date"],
                        source=mapped_data["source"],
                        defaults={
                            "suggestions_shown": mapped_data["suggestions_shown"],
                            "suggestions_accepted": mapped_data["suggestions_accepted"],
                            "acceptance_rate": mapped_data.get("acceptance_rate"),
                        },
                    )
                    metrics_synced += 1
            else:
                # Org-level data - store with first available team member
                members = TeamMember.objects.filter(team=team).first()
                if not members:
                    logger.warning(f"No team members found for team {team.name}")
                    continue

                # Map org data to AIUsageDaily fields
                mapped_data = map_copilot_to_ai_usage(day_data)

                # Store in AIUsageDaily
                AIUsageDaily.objects.update_or_create(
                    team=team,
                    member=members,
                    date=mapped_data["date"],
                    source=mapped_data["source"],
                    defaults={
                        "suggestions_shown": mapped_data["suggestions_shown"],
                        "suggestions_accepted": mapped_data["suggestions_accepted"],
                        "acceptance_rate": mapped_data.get("acceptance_rate"),
                    },
                )
                metrics_synced += 1

        logger.info(f"Successfully synced {metrics_synced} Copilot metrics for team {team.name}")
        return {"metrics_synced": metrics_synced}

    except CopilotMetricsError as exc:
        # Check if it's a 403 error (Copilot not available)
        if "403" in str(exc):
            logger.info(f"Copilot not available for team {team.name}: {exc}")
            return {"error": sanitize_error(exc), "copilot_available": False}
        # For other CopilotMetricsError, treat as transient and retry
        countdown = self.default_retry_delay * (2**self.request.retries)
        try:
            logger.warning(f"Copilot sync failed for {team.name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            raise
        except Exception:
            from sentry_sdk import capture_exception

            logger.error(f"Copilot sync failed permanently for {team.name}: {exc}")
            capture_exception(exc)
            return {"error": sanitize_error(exc)}

    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff
            logger.warning(f"Copilot sync failed for {team.name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted - log to Sentry and return error
            from sentry_sdk import capture_exception

            logger.error(f"Copilot sync failed permanently for {team.name}: {exc}")
            capture_exception(exc)
            return {"error": sanitize_error(exc)}


@shared_task
def sync_all_copilot_metrics() -> dict:
    """Dispatch Copilot sync tasks for all teams with GitHub integration.

    Returns:
        Dict with count of dispatched tasks: teams_dispatched
    """
    logger.info("Starting Copilot metrics sync for all teams")

    # Query all teams with GitHub integrations
    integrations = GitHubIntegration.objects.exclude(organization_slug__isnull=True).exclude(  # noqa: TEAM001 - System job iterating all integrations
        organization_slug=""
    )

    teams_dispatched = 0

    # Dispatch sync task for each team
    for integration in integrations:
        try:
            sync_copilot_metrics_task.delay(integration.team_id)
            teams_dispatched += 1
        except Exception as e:
            # Log dispatch errors and continue with remaining teams
            logger.error(f"Failed to dispatch Copilot sync task for team {integration.team_id}: {e}")
            continue

    logger.info(f"Finished dispatching Copilot sync tasks. Dispatched: {teams_dispatched}")

    return {
        "teams_dispatched": teams_dispatched,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=60, time_limit=90)
def post_survey_comment_task(self, pull_request_id: int) -> dict:
    """Post survey comment to merged PR.

    A-006: Added soft_time_limit=60s, time_limit=90s to prevent GitHub API hangs.

    Creates a PRSurvey and posts survey invitation comment to GitHub.
    Retries up to 3 times with exponential backoff on transient errors.

    Args:
        self: Celery task instance (bound task)
        pull_request_id: ID of the PullRequest to create survey for

    Returns:
        dict with survey_id and comment_id on success
        or dict with skipped/error status and reason
    """
    # Get PR by ID
    try:
        pr = PullRequest.objects.get(id=pull_request_id)  # noqa: TEAM001 - ID from Celery task
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pull_request_id} not found")
        return {"error": "PR not found"}

    # Skip non-merged PRs
    if pr.state != "merged":
        logger.info(f"Skipping survey comment for non-merged PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "PR not merged"}

    # Skip if survey already exists (idempotent)
    from apps.metrics.models import PRSurvey

    if PRSurvey.objects.filter(pull_request=pr).exists():  # noqa: TEAM001 - filtering by team-scoped PR
        logger.info(f"Skipping survey comment - survey already exists for PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "Survey already exists"}

    # Check for GitHub integration
    try:
        github_integration = GitHubIntegration.objects.get(team=pr.team)
    except GitHubIntegration.DoesNotExist:
        logger.info(f"Skipping survey comment - no GitHub integration for team {pr.team.name}")
        return {"skipped": True, "reason": "No GitHub integration"}

    # Create survey (this sets token and expiry)
    survey = create_pr_survey(pr)
    logger.info(f"Starting to post survey comment for PR {pr.github_pr_id} (survey {survey.id})")

    # Post comment to GitHub with retry logic
    try:
        comment_id = github_comments.post_survey_comment(pr, survey, github_integration.credential.access_token)

        # Store comment ID on survey (in case post_survey_comment didn't persist it)
        survey.github_comment_id = comment_id
        survey.save(update_fields=["github_comment_id"])

        logger.info(f"Successfully posted survey comment {comment_id} for PR {pr.github_pr_id}")
        return {"survey_id": survey.id, "comment_id": comment_id}
    except GithubException as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff for transient errors
            logger.warning(f"Failed to post survey comment for PR {pr.github_pr_id}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted - log to Sentry and return error
            from sentry_sdk import capture_exception

            error_msg = f"GitHub API error: {exc}"
            logger.error(f"Failed permanently to post survey comment for PR {pr.github_pr_id}: {error_msg}")
            capture_exception(exc)

            return {"error": error_msg, "survey_id": survey.id}


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=60, time_limit=90)
def update_pr_description_survey_task(self, pull_request_id: int) -> dict:
    """Update PR description with survey voting links.

    A-006: Added soft_time_limit=60s, time_limit=90s to prevent GitHub API hangs.

    Creates a PRSurvey and updates the PR description with survey links.
    This is the preferred approach (vs comments) as it's more visible.
    Retries up to 3 times with exponential backoff on transient errors.

    Args:
        self: Celery task instance (bound task)
        pull_request_id: ID of the PullRequest to create survey for

    Returns:
        dict with survey_id on success
        or dict with skipped/error status and reason
    """
    from django.conf import settings

    # Get PR by ID
    try:
        pr = PullRequest.objects.get(id=pull_request_id)  # noqa: TEAM001 - ID from Celery task
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pull_request_id} not found")
        return {"error": "PR not found"}

    # Skip non-merged PRs
    if pr.state != "merged":
        logger.info(f"Skipping PR description update for non-merged PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "PR not merged"}

    # Skip if survey already exists (idempotent)
    from apps.metrics.models import PRSurvey

    if PRSurvey.objects.filter(pull_request=pr).exists():  # noqa: TEAM001 - filtering by team-scoped PR
        logger.info(f"Skipping PR description update - survey already exists for PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "Survey already exists"}

    # Check for GitHub integration
    try:
        github_integration = GitHubIntegration.objects.get(team=pr.team)
    except GitHubIntegration.DoesNotExist:
        logger.info(f"Skipping PR description update - no GitHub integration for team {pr.team.name}")
        return {"skipped": True, "reason": "No GitHub integration"}

    # Create survey (this includes AI auto-detection)
    survey = create_pr_survey(pr)
    logger.info(f"Created survey {survey.id} for PR {pr.github_pr_id}, AI detected: {survey.author_ai_assisted}")

    # Get base URL from settings
    base_url = getattr(settings, "SITE_URL", "https://app.tformance.com")

    # Update PR description with survey links
    try:
        github_pr_description.update_pr_description_with_survey(
            survey=survey,
            access_token=github_integration.credential.access_token,
            base_url=base_url,
        )

        logger.info(f"Successfully updated PR description with survey for PR {pr.github_pr_id}")

        # Schedule Slack fallback survey (runs after 1 hour delay)
        schedule_slack_survey_fallback_task.delay(pull_request_id)
        logger.info(f"Scheduled Slack fallback survey for PR {pr.github_pr_id}")

        return {"survey_id": survey.id, "success": True, "slack_fallback_scheduled": True}
    except GithubException as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff for transient errors
            logger.warning(f"Failed to update PR description for PR {pr.github_pr_id}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted - log to Sentry and return error
            from sentry_sdk import capture_exception

            error_msg = f"GitHub API error: {exc}"
            logger.error(f"Failed permanently to update PR description for PR {pr.github_pr_id}: {error_msg}")
            capture_exception(exc)

            return {"error": error_msg, "survey_id": survey.id}


@shared_task
def schedule_slack_survey_fallback_task(pull_request_id: int) -> dict:
    """Schedule Slack surveys as fallback for users who haven't responded via GitHub.

    This task schedules send_pr_surveys_task with a 1-hour countdown, giving users
    time to respond via GitHub one-click voting before receiving Slack messages.

    Args:
        pull_request_id: ID of the PullRequest to send surveys for

    Returns:
        Dict with keys: scheduled (bool), task_id (str), countdown (int)
    """
    # Schedule send_pr_surveys_task with 1-hour countdown
    countdown = 3600  # 1 hour in seconds

    async_result = send_pr_surveys_task.apply_async(
        (pull_request_id,),
        countdown=countdown,
    )

    logger.info(f"Scheduled Slack survey fallback for PR {pull_request_id} in {countdown} seconds")

    return {
        "scheduled": True,
        "task_id": async_result.id,
        "countdown": countdown,
    }


@shared_task
def aggregate_team_weekly_metrics_task(team_id: int):
    """Aggregate weekly metrics for a single team.

    Args:
        team_id: ID of the Team to aggregate metrics for

    Returns:
        int: Count of WeeklyMetrics records created/updated, or None/0 if error
    """
    from datetime import date, timedelta

    # Get Team by id
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return None

    # Calculate previous week's Monday
    today = date.today()
    days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
    this_monday = today - timedelta(days=days_since_monday)
    previous_monday = this_monday - timedelta(days=7)

    # Call aggregation service
    logger.info(f"Starting weekly metrics aggregation for team {team.name} (week starting {previous_monday})")
    try:
        weekly_metrics = aggregate_team_weekly_metrics(team, previous_monday)
        count = len(weekly_metrics)
        logger.info(f"Successfully aggregated {count} weekly metrics for team {team.name}")
        return count
    except Exception as exc:
        from sentry_sdk import capture_exception

        logger.error(f"Failed to aggregate weekly metrics for team {team.name}: {exc}")
        capture_exception(exc)
        return 0


@shared_task
def aggregate_all_teams_weekly_metrics_task():
    """Aggregate weekly metrics for all teams with GitHub integration.

    Returns:
        int: Count of teams processed
    """
    logger.info("Starting weekly metrics aggregation for all teams")

    # Find all teams with GitHubIntegration
    integrations = GitHubIntegration.objects.select_related("team").all()  # noqa: TEAM001 - System job iterating all integrations

    teams_processed = 0

    # Dispatch aggregate_team_weekly_metrics_task for each team
    for integration in integrations:
        try:
            aggregate_team_weekly_metrics_task.delay(integration.team.id)
            teams_processed += 1
        except Exception as e:
            logger.error(f"Failed to dispatch weekly metrics aggregation for team {integration.team.id}: {e}")
            continue

    logger.info(f"Finished dispatching weekly metrics aggregation tasks. Processed: {teams_processed}")

    return teams_processed


def _fetch_pr_core_data_with_graphql_or_rest(pr, tracked_repo, access_token, errors: list) -> dict:
    """Fetch PR commits, files, and reviews using GraphQL or REST.

    Uses GraphQL API if enabled for pr_complete_data operation, falling back to REST
    if GraphQL fails and fallback is enabled. Check runs and comments always use REST.

    Args:
        pr: PullRequest model instance
        tracked_repo: TrackedRepository model instance
        access_token: GitHub access token
        errors: List to append errors to

    Returns:
        dict with commits_synced, files_synced, reviews_synced counts
    """
    from asgiref.sync import async_to_sync
    from django.conf import settings

    github_config = getattr(settings, "GITHUB_API_CONFIG", {})
    use_graphql = github_config.get("USE_GRAPHQL", False)
    graphql_ops = github_config.get("GRAPHQL_OPERATIONS", {})
    pr_complete_enabled = graphql_ops.get("pr_complete_data", True)
    fallback_to_rest = github_config.get("FALLBACK_TO_REST", True)

    if use_graphql and pr_complete_enabled:
        logger.info(f"Using GraphQL API for PR complete data: {pr.github_repo}#{pr.github_pr_id}")
        try:
            from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql

            # Run async function in sync context using async_to_sync
            # NOTE: Using async_to_sync instead of asyncio.run() is critical!
            # asyncio.run() creates a new event loop which breaks @sync_to_async
            # decorators' thread handling, causing DB operations to silently fail
            # in Celery workers. async_to_sync properly manages the event loop
            # and thread context for Django's database connections.
            sync_fetch = async_to_sync(fetch_pr_complete_data_graphql)
            result = sync_fetch(pr, tracked_repo)

            # Check if GraphQL sync had errors
            if result.get("errors") and fallback_to_rest:
                logger.warning(
                    f"GraphQL PR data fetch had errors for {pr.github_repo}#{pr.github_pr_id}: {result['errors']}, "
                    "falling back to REST"
                )
                raise Exception(f"GraphQL errors: {result['errors']}")

            return {
                "commits_synced": result.get("commits_synced", 0),
                "files_synced": result.get("files_synced", 0),
                "reviews_synced": result.get("reviews_synced", 0),
            }
        except Exception as e:
            if fallback_to_rest:
                logger.warning(
                    f"GraphQL PR data fetch failed for {pr.github_repo}#{pr.github_pr_id}: {e}, falling back to REST"
                )
            else:
                raise

    # Use REST API (default or fallback)
    logger.info(f"Using REST API for PR complete data: {pr.github_repo}#{pr.github_pr_id}")
    commits_synced = github_sync.sync_pr_commits(pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors)
    files_synced = github_sync.sync_pr_files(pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors)
    # Note: REST doesn't have a separate reviews sync here - reviews are typically synced during PR sync

    return {
        "commits_synced": commits_synced,
        "files_synced": files_synced,
        "reviews_synced": 0,  # REST path doesn't sync reviews in this task
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=180, time_limit=240)
def fetch_pr_complete_data_task(self, pr_id: int) -> dict:
    """Fetch complete PR data (commits, files, check runs, comments) after merge.

    A-006: Added soft_time_limit=180s, time_limit=240s to prevent GitHub API hangs.

    Args:
        self: Celery task instance (bound task)
        pr_id: ID of the PullRequest to fetch data for

    Returns:
        Dict with sync counts and errors list
    """
    # Get PullRequest by id
    try:
        pr = PullRequest.objects.get(id=pr_id)  # noqa: TEAM001 - ID from Celery task queue
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pr_id} not found")
        return {"error": f"PullRequest with id {pr_id} not found"}

    # Find TrackedRepository matching team, repo, and is_active=True
    try:
        tracked_repo = TrackedRepository.objects.get(
            team=pr.team,
            full_name=pr.github_repo,
            is_active=True,
        )
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository not found for team={pr.team.id}, repo={pr.github_repo}, is_active=True")
        return {"error": f"TrackedRepository not found for team={pr.team.name}, repo={pr.github_repo}, is_active=True"}

    # Get access token from integration credential
    access_token = tracked_repo.integration.credential.access_token

    # Initialize errors list
    errors = []

    # Sync all PR data
    logger.info(f"Starting complete data fetch for PR {pr.github_pr_id}")

    # Fetch commits, files (and reviews if using GraphQL) - uses GraphQL or REST based on config
    core_data = _fetch_pr_core_data_with_graphql_or_rest(pr, tracked_repo, access_token, errors)
    commits_synced = core_data["commits_synced"]
    files_synced = core_data["files_synced"]

    # These always use REST (not supported by our GraphQL queries yet)
    check_runs_synced = github_sync.sync_pr_check_runs(
        pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors
    )

    issue_comments_synced = github_sync.sync_pr_issue_comments(
        pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors
    )

    review_comments_synced = github_sync.sync_pr_review_comments(
        pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors
    )

    # Calculate iteration metrics after all data is synced
    github_sync.calculate_pr_iteration_metrics(pr)

    logger.info(f"Completed data fetch for PR {pr.github_pr_id}")

    return {
        "commits_synced": commits_synced,
        "files_synced": files_synced,
        "check_runs_synced": check_runs_synced,
        "issue_comments_synced": issue_comments_synced,
        "review_comments_synced": review_comments_synced,
        "errors": errors,
    }


@shared_task
def refresh_repo_languages_task(repo_id: int) -> dict:
    """Refresh language breakdown for a single repository.

    Args:
        repo_id: ID of the TrackedRepository to refresh

    Returns:
        Dict with language count and primary language
    """
    from apps.integrations.services.github_repo_languages import update_repo_languages

    try:
        repo = TrackedRepository.objects.get(id=repo_id)  # noqa: TEAM001 - ID from Celery task queue
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository with id {repo_id} not found")
        return {"error": f"TrackedRepository with id {repo_id} not found"}

    if not repo.is_active:
        return {"skipped": True, "reason": "Repository is not active"}

    try:
        languages = update_repo_languages(repo)
        return {
            "repo": repo.full_name,
            "languages_count": len(languages),
            "primary_language": repo.primary_language,
        }
    except Exception as e:
        logger.exception(f"Failed to refresh languages for {repo.full_name}")
        return {"error": str(e)}


@shared_task
def refresh_all_repo_languages_task() -> dict:
    """Refresh language breakdown for all active repositories.

    Scheduled monthly to keep language data current.

    Returns:
        Dict with count of repos updated and errors
    """
    from datetime import timedelta

    from django.db.models import Q
    from django.utils import timezone

    from apps.integrations.services.github_repo_languages import update_repo_languages

    # Find repos that need refresh (never updated or updated > 30 days ago)
    threshold = timezone.now() - timedelta(days=30)
    repos = TrackedRepository.objects.filter(  # noqa: TEAM001 - Background task for all teams
        is_active=True,
    ).filter(Q(languages_updated_at__isnull=True) | Q(languages_updated_at__lt=threshold))

    updated = 0
    errors = []

    for repo in repos:
        try:
            update_repo_languages(repo)
            updated += 1
        except Exception as e:
            logger.warning(f"Failed to update languages for {repo.full_name}: {e}")
            errors.append({"repo": repo.full_name, "error": str(e)})

    logger.info(f"Refreshed languages for {updated} repos, {len(errors)} errors")

    return {
        "repos_updated": updated,
        "errors_count": len(errors),
        "errors": errors[:10],  # First 10 errors only
    }


# ============================================================================
# Historical Sync for Onboarding
# ============================================================================


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


@shared_task(bind=True, soft_time_limit=600, time_limit=660)
def queue_llm_analysis_batch_task(self, team_id: int, batch_size: int = 50) -> dict:
    """Process PRs missing LLM analysis in batches.

    A-006: Added soft_time_limit=600s (10 min), time_limit=660s (11 min) for LLM batch processing.

    Args:
        self: Celery task instance (bound task)
        team_id: The team to process PRs for
        batch_size: Number of PRs to process per batch (default 50)

    Returns:
        Dict with prs_processed count or error status
    """
    # Verify team exists
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": "Team not found", "prs_processed": 0}

    # Find PRs missing llm_summary for this team
    prs_to_process = list(
        PullRequest.objects.filter(
            team=team,
            llm_summary__isnull=True,
        )
        .select_related("author")
        .prefetch_related("files", "commits", "reviews__reviewer", "comments__author")[:batch_size]
    )

    if not prs_to_process:
        logger.info(f"No PRs need LLM processing for team {team.name}")
        return {"prs_processed": 0, "message": "No PRs need processing"}

    logger.info(f"Starting LLM batch analysis for {len(prs_to_process)} PRs for team {team.name}")

    # Process with LLM using GroqBatchProcessor
    processor = GroqBatchProcessor()
    results, stats = processor.submit_batch_with_fallback(prs_to_process)

    # Update PRs with results
    prs_updated = 0
    for result in results:
        if result.error:
            logger.warning(f"LLM analysis failed for PR {result.pr_id}: {result.error}")
            continue

        try:
            pr = PullRequest.objects.get(id=result.pr_id)  # noqa: TEAM001 - ID from LLM batch result
            pr.llm_summary = result.llm_summary
            pr.llm_summary_version = result.prompt_version
            pr.save(update_fields=["llm_summary", "llm_summary_version"])
            prs_updated += 1
        except PullRequest.DoesNotExist:
            logger.warning(f"PR {result.pr_id} not found when updating LLM results")

    logger.info(f"Successfully updated {prs_updated} PRs with LLM analysis for team {team.name}")

    return {"prs_processed": prs_updated}


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

    return {
        "status": "complete",
        "repos_synced": repos_synced,
        "failed_repos": failed_repos,
        "total_prs": total_prs,
    }
