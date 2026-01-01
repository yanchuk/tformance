"""Onboarding pipeline task orchestration using Celery chains.

This module provides a reliable, sequential pipeline for processing
new user onboarding data:

1. Sync historical PR data from GitHub
2. Run LLM analysis for AI detection
3. Aggregate weekly metrics
4. Compute insights
5. Send completion email

Uses Celery chains for guaranteed sequential execution with error handling.
"""

import logging

from celery import chain, shared_task
from celery.result import AsyncResult

from apps.utils.errors import sanitize_error

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def update_pipeline_status(self, team_id: int, status: str, error: str | None = None) -> dict:
    """
    Update the pipeline status for a team.

    This is a lightweight task that updates the Team model's pipeline tracking fields.
    Used as a checkpoint between pipeline stages.

    Args:
        team_id: The team's ID
        status: New status (syncing, llm_processing, computing_metrics, etc.)
        error: Optional error message (only used if status is 'failed')

    Returns:
        dict with status and team_id
    """
    from apps.teams.models import Team

    try:
        team = Team.objects.get(id=team_id)
        team.update_pipeline_status(status, error=error)
        logger.info(f"Pipeline status updated: team={team_id}, status={status}")
        return {"status": "ok", "team_id": team_id, "pipeline_status": status}
    except Team.DoesNotExist:
        logger.error(f"Team not found: {team_id}")
        return {"status": "error", "error": f"Team {team_id} not found"}


@shared_task(bind=True)
def handle_pipeline_failure(
    self,
    request,
    exc,
    traceback,
    team_id: int | None = None,
) -> dict:
    """
    Handle Phase 1 pipeline failure by updating team status to 'failed'.

    This blocks dashboard access until the issue is resolved.
    Used for Phase 1 failures where the user hasn't seen the dashboard yet.

    Args:
        request: The failed task's request (from Celery)
        exc: The exception that was raised
        traceback: The exception traceback
        team_id: The team ID (passed as kwarg)

    Returns:
        dict with error details
    """
    from apps.teams.models import Team

    error_message = sanitize_error(exc) if exc else "Unknown error"

    if team_id is None:
        logger.error(f"Pipeline failure handler called without team_id: {error_message}")
        return {"status": "error", "error": "No team_id provided"}

    try:
        team = Team.objects.get(id=team_id)
        team.update_pipeline_status("failed", error=error_message)
        logger.error(f"Pipeline failed for team {team_id}: {error_message}")
        return {"status": "failed", "team_id": team_id, "error": error_message}
    except Team.DoesNotExist:
        logger.error(f"Team not found during failure handling: {team_id}")
        return {"status": "error", "error": f"Team {team_id} not found"}


@shared_task(bind=True)
def handle_phase2_failure(
    self,
    request,
    exc,
    traceback,
    team_id: int | None = None,
) -> dict:
    """
    Handle Phase 2 pipeline failure gracefully without blocking dashboard.

    Phase 2 failures should NOT affect dashboard access since the user
    already completed Phase 1 and has 30 days of data available.

    This handler:
    1. Logs the error for debugging
    2. Reverts status to 'phase1_complete' (dashboard stays accessible)
    3. Does NOT set status to 'failed'

    The nightly batch will retry processing later.

    Args:
        request: The failed task's request (from Celery)
        exc: The exception that was raised
        traceback: The exception traceback
        team_id: The team ID (passed as kwarg)

    Returns:
        dict with phase2_failed status
    """
    from apps.teams.models import Team

    error_message = sanitize_error(exc) if exc else "Unknown error"

    if team_id is None:
        logger.error(f"Phase 2 failure handler called without team_id: {error_message}")
        return {"status": "error", "error": "No team_id provided"}

    try:
        team = Team.objects.get(id=team_id)
        # Revert to phase1_complete - keeps dashboard accessible
        team.update_pipeline_status("phase1_complete")
        logger.warning(f"Phase 2 failed for team {team_id} (dashboard stays accessible): {error_message}")
        return {"status": "phase2_failed", "team_id": team_id, "error": error_message}
    except Team.DoesNotExist:
        logger.error(f"Team not found during Phase 2 failure handling: {team_id}")
        return {"status": "error", "error": f"Team {team_id} not found"}


@shared_task(bind=True)
def send_onboarding_complete_email(self, team_id: int) -> dict:
    """
    Send completion email at the end of the pipeline.

    Gathers statistics and sends a rich email to the team admin.

    Args:
        team_id: The team's ID

    Returns:
        dict with email status
    """
    from apps.metrics.models import PullRequest
    from apps.onboarding.services.notifications import send_sync_complete_email
    from apps.teams.models import Team

    try:
        team = Team.objects.get(id=team_id)

        # Get statistics
        total_prs = PullRequest.objects.filter(team=team).count()

        # Get admin user
        admin_membership = team.membership_set.filter(role="admin").first()
        if not admin_membership:
            logger.warning(f"No admin found for team {team_id}")
            return {"status": "skipped", "reason": "no_admin"}

        user = admin_membership.user

        # Send email
        send_sync_complete_email(
            team=team,
            user=user,
            prs_synced=total_prs,
            repos_synced=team.tracked_repos.count() if hasattr(team, "tracked_repos") else 0,
        )

        logger.info(f"Sent onboarding complete email to {user.email} for team {team_id}")
        return {"status": "sent", "team_id": team_id, "recipient": user.email}

    except Team.DoesNotExist:
        logger.error(f"Team not found for email: {team_id}")
        return {"status": "error", "error": f"Team {team_id} not found"}
    except Exception as e:
        # Don't fail the pipeline for email errors
        logger.warning(f"Failed to send onboarding email for team {team_id}: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task(bind=True)
def dispatch_phase2_pipeline(self, team_id: int, repo_ids: list[int]) -> dict:
    """
    Dispatch Phase 2 background processing after Phase 1 completes.

    This is a separate task that starts Phase 2 asynchronously,
    allowing Phase 1 to complete and the user to access the dashboard.

    Args:
        team_id: The team's ID
        repo_ids: List of TrackedRepository IDs to sync

    Returns:
        dict with dispatch status
    """
    logger.info(f"Dispatching Phase 2 pipeline: team={team_id}, repos={repo_ids}")

    # Import here to avoid circular imports
    from apps.integrations.tasks import (
        aggregate_team_weekly_metrics_task,
        sync_historical_data_task,
    )
    from apps.metrics.tasks import compute_team_insights, run_llm_analysis_batch

    # Build Phase 2 pipeline
    pipeline = chain(
        # Stage 1: Sync historical data (days 31-90)
        update_pipeline_status.si(team_id, "background_syncing"),
        sync_historical_data_task.si(team_id, repo_ids, days_back=90, skip_recent=30),
        # Stage 2: LLM analysis for remaining PRs
        update_pipeline_status.si(team_id, "background_llm"),
        run_llm_analysis_batch.si(team_id, limit=None),  # Process all remaining
        # Stage 3: Re-aggregate metrics with full data
        aggregate_team_weekly_metrics_task.si(team_id),
        # Stage 4: Re-compute insights with full data
        compute_team_insights.si(team_id),
        # Stage 5: Final completion
        update_pipeline_status.si(team_id, "complete"),
        send_onboarding_complete_email.si(team_id),
    )

    # Phase 2 failures don't block dashboard - use graceful error handler
    pipeline = pipeline.on_error(handle_phase2_failure.s(team_id=team_id))

    # Execute asynchronously
    result = pipeline.apply_async()

    return {"status": "dispatched", "team_id": team_id, "task_id": result.id}


def run_phase2_pipeline(team_id: int, repo_ids: list[int]) -> AsyncResult:
    """
    Run Phase 2 background pipeline directly (for testing).

    This is a synchronous entry point for Phase 2, mainly used in tests.
    In production, use dispatch_phase2_pipeline which runs async.

    Args:
        team_id: The team's ID
        repo_ids: List of TrackedRepository IDs to sync

    Returns:
        AsyncResult from the chain execution
    """
    from apps.integrations.tasks import (
        aggregate_team_weekly_metrics_task,
        sync_historical_data_task,
    )
    from apps.metrics.tasks import compute_team_insights, run_llm_analysis_batch

    logger.info(f"Running Phase 2 pipeline: team={team_id}, repos={repo_ids}")

    pipeline = chain(
        # Stage 1: Sync historical data (days 31-90)
        update_pipeline_status.si(team_id, "background_syncing"),
        sync_historical_data_task.si(team_id, repo_ids, days_back=90, skip_recent=30),
        # Stage 2: LLM analysis for remaining PRs
        update_pipeline_status.si(team_id, "background_llm"),
        run_llm_analysis_batch.si(team_id, limit=None),
        # Stage 3: Re-aggregate metrics
        aggregate_team_weekly_metrics_task.si(team_id),
        # Stage 4: Re-compute insights
        compute_team_insights.si(team_id),
        # Stage 5: Final completion
        update_pipeline_status.si(team_id, "complete"),
    )

    # Phase 2 failures don't block dashboard - use graceful error handler
    pipeline = pipeline.on_error(handle_phase2_failure.s(team_id=team_id))

    return pipeline.apply_async()


def start_phase1_pipeline(team_id: int, repo_ids: list[int]) -> AsyncResult:
    """
    Start Phase 1 (Quick Start) of the two-phase onboarding pipeline.

    Phase 1 provides fast time-to-dashboard (~5 minutes):
    1. Sync last 30 days of PR data (quick)
    2. LLM analyze ALL synced PRs (~150 PRs = ~5 min)
    3. Aggregate metrics
    4. Compute insights
    5. Set status to 'phase1_complete' (dashboard accessible)
    6. Dispatch Phase 2 for background processing

    Args:
        team_id: The team's ID
        repo_ids: List of TrackedRepository IDs to sync

    Returns:
        AsyncResult from the chain execution
    """
    from apps.integrations.tasks import (
        aggregate_team_weekly_metrics_task,
        sync_historical_data_task,
    )
    from apps.metrics.tasks import compute_team_insights, run_llm_analysis_batch

    logger.info(f"Starting Phase 1 pipeline: team={team_id}, repos={repo_ids}")

    # Build Phase 1 pipeline (Quick Start)
    pipeline = chain(
        # Stage 1: Sync last 30 days only (fast)
        update_pipeline_status.si(team_id, "syncing"),
        sync_historical_data_task.si(team_id, repo_ids, days_back=30),
        # Stage 2: LLM analysis for ALL synced PRs
        update_pipeline_status.si(team_id, "llm_processing"),
        run_llm_analysis_batch.si(team_id, limit=None),  # Process ALL for Phase 1
        # Stage 3: Metrics aggregation
        update_pipeline_status.si(team_id, "computing_metrics"),
        aggregate_team_weekly_metrics_task.si(team_id),
        # Stage 4: Insights computation
        update_pipeline_status.si(team_id, "computing_insights"),
        compute_team_insights.si(team_id),
        # Stage 5: Phase 1 Complete (dashboard accessible!)
        update_pipeline_status.si(team_id, "phase1_complete"),
        # Stage 6: Dispatch Phase 2 in background
        dispatch_phase2_pipeline.si(team_id, repo_ids),
    )

    # Attach error handler
    pipeline = pipeline.on_error(handle_pipeline_failure.s(team_id=team_id))

    # Execute the pipeline
    return pipeline.apply_async()


def start_onboarding_pipeline(team_id: int, repo_ids: list[int]) -> AsyncResult:
    """
    Start the onboarding pipeline using Two-Phase Quick Start.

    Delegates to start_phase1_pipeline for faster time-to-dashboard.
    Phase 2 runs automatically in the background after Phase 1.

    Two-Phase Onboarding:
    - Phase 1: 30 days sync → ALL PRs LLM → dashboard ready (~5 min)
    - Phase 2: 31-90 days sync → remaining LLM → complete (background)

    Args:
        team_id: The team's ID
        repo_ids: List of TrackedRepository IDs to sync

    Returns:
        AsyncResult from the Phase 1 chain execution
    """
    return start_phase1_pipeline(team_id, repo_ids)


# =============================================================================
# Jira Onboarding Pipeline
# =============================================================================
# Parallel pipeline for Jira sync during onboarding.
# Runs independently from GitHub pipeline (Jira is optional).


@shared_task(bind=True)
def sync_jira_users_onboarding(self, team_id: int) -> dict:
    """
    Sync Jira users to TeamMembers during onboarding.

    Delegates to the existing sync_jira_users_task which handles:
    - Fetching users from Jira API
    - Matching by email to existing TeamMembers
    - Setting jira_account_id on matched members

    Args:
        team_id: The team's ID

    Returns:
        dict with matched/unmatched counts from sync_jira_users_task
    """
    from apps.integrations.tasks import sync_jira_users_task

    logger.info(f"Jira onboarding: syncing users for team {team_id}")
    return sync_jira_users_task(team_id)


@shared_task(bind=True)
def sync_jira_projects_onboarding(self, team_id: int, project_ids: list[int]) -> dict:
    """
    Sync Jira projects sequentially during onboarding.

    Syncs each project in the list, aggregating results.
    Continues on individual project failure (silent retry pattern).

    Args:
        team_id: The team's ID
        project_ids: List of TrackedJiraProject IDs to sync

    Returns:
        dict with synced/failed counts and total issues_created
    """
    from apps.integrations.models import TrackedJiraProject
    from apps.integrations.services.jira_sync import sync_project_issues

    results = {"synced": 0, "failed": 0, "issues_created": 0}

    if not project_ids:
        logger.info(f"Jira onboarding: no projects to sync for team {team_id}")
        return results

    logger.info(f"Jira onboarding: syncing {len(project_ids)} projects for team {team_id}")

    for project_id in project_ids:
        try:
            project = TrackedJiraProject.objects.get(id=project_id)  # noqa: TEAM001 - ID from Celery task
            result = sync_project_issues(project, full_sync=True)
            results["synced"] += 1
            results["issues_created"] += result.get("issues_created", 0)
            logger.info(f"Jira project {project.jira_project_key} synced: {result}")
        except TrackedJiraProject.DoesNotExist:
            results["failed"] += 1
            logger.error(f"Jira project not found: {project_id}")
        except Exception as e:
            results["failed"] += 1
            logger.error(f"Jira project sync failed: {project_id}: {e}")

    logger.info(f"Jira onboarding complete for team {team_id}: {results}")
    return results


def start_jira_onboarding_pipeline(team_id: int, project_ids: list[int]) -> AsyncResult:
    """
    Start Jira onboarding pipeline (runs parallel to GitHub).

    Pipeline sequence:
    1. Sync Jira users to TeamMembers (email matching)
    2. Sync all selected Jira projects (fetch issues)

    This pipeline runs independently from the GitHub pipeline.
    Jira sync failure does not affect GitHub pipeline or dashboard access.

    Args:
        team_id: The team's ID
        project_ids: List of TrackedJiraProject IDs to sync

    Returns:
        AsyncResult from the chain execution
    """
    logger.info(f"Starting Jira onboarding pipeline: team={team_id}, projects={project_ids}")

    pipeline = chain(
        sync_jira_users_onboarding.si(team_id),
        sync_jira_projects_onboarding.si(team_id, project_ids),
    )

    return pipeline.apply_async()
