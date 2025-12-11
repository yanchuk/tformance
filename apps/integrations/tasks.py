"""Celery tasks for integrations."""

import logging

from celery import shared_task
from celery.exceptions import Retry

from apps.integrations.models import JiraIntegration, TrackedJiraProject, TrackedRepository
from apps.integrations.services.github_sync import sync_repository_incremental
from apps.integrations.services.jira_sync import sync_project_issues
from apps.integrations.services.jira_user_matching import sync_jira_users
from apps.teams.models import Team

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_jira_project_task(self, project_id: int) -> dict:
    """Sync a single tracked Jira project.

    Args:
        self: Celery task instance (bound task)
        project_id: ID of the TrackedJiraProject to sync

    Returns:
        Dict with sync results (issues_created, issues_updated, errors) or error/skip status
    """
    # Get TrackedJiraProject by id
    try:
        tracked_project = TrackedJiraProject.objects.get(id=project_id)
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
            tracked_project.last_sync_error = str(exc)
            tracked_project.save(update_fields=["sync_status", "last_sync_error"])

            return {"error": str(exc)}


@shared_task
def sync_all_jira_projects_task() -> dict:
    """Dispatch sync tasks for all active tracked Jira projects.

    Returns:
        Dict with counts: projects_dispatched, projects_skipped
    """
    logger.info("Starting sync for all Jira projects")

    # Query all tracked Jira projects
    active_projects = TrackedJiraProject.objects.filter(is_active=True)
    projects_skipped = TrackedJiraProject.objects.filter(is_active=False).count()

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
        return {"error": str(exc)}
