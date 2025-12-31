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
    Handle pipeline failure by updating team status.

    This task is attached to the chain via on_error() and is called
    when any task in the pipeline fails.

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


def start_onboarding_pipeline(team_id: int, repo_ids: list[int]) -> AsyncResult:
    """
    Start the complete onboarding pipeline using a Celery chain.

    This orchestrates the entire onboarding data processing flow:
    1. Update status to 'syncing'
    2. Sync historical PR data
    3. Update status to 'llm_processing'
    4. Run LLM analysis
    5. Update status to 'computing_metrics'
    6. Aggregate weekly metrics
    7. Update status to 'computing_insights'
    8. Compute insights
    9. Update status to 'complete'
    10. Send completion email

    Args:
        team_id: The team's ID
        repo_ids: List of TrackedRepository IDs to sync

    Returns:
        AsyncResult from the chain execution
    """
    # Import tasks from their modules
    from apps.integrations.tasks import (
        aggregate_team_weekly_metrics_task,
        sync_historical_data_task,
    )
    from apps.metrics.tasks import compute_team_insights, run_llm_analysis_batch

    logger.info(f"Starting onboarding pipeline: team={team_id}, repos={repo_ids}")

    # Build the pipeline chain
    # Using .si() for immutable signatures (ignores previous task's return value)
    pipeline = chain(
        # Stage 1: Sync historical data
        update_pipeline_status.si(team_id, "syncing"),
        sync_historical_data_task.si(team_id, repo_ids),
        # Stage 2: LLM analysis
        update_pipeline_status.si(team_id, "llm_processing"),
        run_llm_analysis_batch.si(team_id, limit=100),  # Process more for onboarding
        # Stage 3: Metrics aggregation
        update_pipeline_status.si(team_id, "computing_metrics"),
        aggregate_team_weekly_metrics_task.si(team_id),
        # Stage 4: Insights computation
        update_pipeline_status.si(team_id, "computing_insights"),
        compute_team_insights.si(team_id),
        # Stage 5: Completion
        update_pipeline_status.si(team_id, "complete"),
        send_onboarding_complete_email.si(team_id),
    )

    # Attach error handler
    pipeline = pipeline.on_error(handle_pipeline_failure.s(team_id=team_id))

    # Execute the pipeline
    return pipeline.apply_async()
