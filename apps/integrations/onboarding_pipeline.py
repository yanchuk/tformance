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
from apps.utils.sync_logger import get_sync_logger

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
    from django.utils import timezone

    from apps.teams.models import Team

    try:
        team = Team.objects.get(id=team_id)
        previous_phase = team.onboarding_pipeline_status
        team.update_pipeline_status(status, error=error)
        logger.info(f"Pipeline status updated: team={team_id}, status={status}")

        # Log phase change
        sync_log = get_sync_logger(__name__)
        sync_log.info(
            "sync.pipeline.phase_changed",
            extra={
                "team_id": team_id,
                "phase": status,
                "previous_phase": previous_phase,
            },
        )

        # Log completion event for terminal states
        if status in ("phase1_complete", "complete"):
            duration_seconds = 0
            if team.onboarding_pipeline_started_at:
                duration_seconds = (timezone.now() - team.onboarding_pipeline_started_at).total_seconds()
            sync_log.info(
                "sync.pipeline.completed",
                extra={
                    "team_id": team_id,
                    "duration_seconds": duration_seconds,
                },
            )

        print(f"!!! PIPELINE_STATUS_UPDATED: team={team_id}, status={status} - Chain should continue")
        logger.warning(f"!!! PIPELINE_STATUS_UPDATED: team={team_id}, status={status} - Chain should continue")
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
    error_type = type(exc).__name__ if exc else "UnknownError"

    if team_id is None:
        logger.error(f"Pipeline failure handler called without team_id: {error_message}")
        return {"status": "error", "error": "No team_id provided"}

    try:
        team = Team.objects.get(id=team_id)
        failed_phase = team.onboarding_pipeline_status
        team.update_pipeline_status("failed", error=error_message)
        logger.error(f"Pipeline failed for team {team_id}: {error_message}")

        # Log failure event
        sync_log = get_sync_logger(__name__)
        sync_log.error(
            "sync.pipeline.failed",
            extra={
                "team_id": team_id,
                "error_type": error_type,
                "error_message": error_message,
                "failed_phase": failed_phase,
            },
        )

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
        queue_llm_analysis_batch_task,
        sync_historical_data_task,
    )
    from apps.metrics.tasks import compute_team_insights, generate_team_llm_insights

    # Build Phase 2 pipeline
    pipeline = chain(
        # Stage 0: Sync members first (may have new contributors in older PRs)
        sync_github_members_pipeline_task.si(team_id),
        # Stage 1: Sync historical data (days 31-90)
        update_pipeline_status.si(team_id, "background_syncing"),
        sync_historical_data_task.si(team_id, repo_ids, days_back=90, skip_recent=30),
        # Stage 2: LLM analysis for remaining PRs (uses Groq Batch API for 50% cost savings)
        update_pipeline_status.si(team_id, "background_llm"),
        queue_llm_analysis_batch_task.si(team_id, batch_size=500),  # Process all remaining
        # Stage 3: Re-aggregate metrics with full data
        aggregate_team_weekly_metrics_task.si(team_id),
        # Stage 4: Re-compute insights with full data
        compute_team_insights.si(team_id),
        # Stage 5: Generate 90-day LLM insight (now have full 90 days of data)
        generate_team_llm_insights.si(team_id, days_list=[90]),
        # Stage 6: Final completion
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
        queue_llm_analysis_batch_task,
        sync_historical_data_task,
    )
    from apps.metrics.tasks import compute_team_insights, generate_team_llm_insights

    logger.info(f"Running Phase 2 pipeline: team={team_id}, repos={repo_ids}")

    pipeline = chain(
        # Stage 0: Sync members first (may have new contributors in older PRs)
        sync_github_members_pipeline_task.si(team_id),
        # Stage 1: Sync historical data (days 31-90)
        update_pipeline_status.si(team_id, "background_syncing"),
        sync_historical_data_task.si(team_id, repo_ids, days_back=90, skip_recent=30),
        # Stage 2: LLM analysis for remaining PRs (uses Groq Batch API for 50% cost savings)
        update_pipeline_status.si(team_id, "background_llm"),
        queue_llm_analysis_batch_task.si(team_id, batch_size=500),
        # Stage 3: Re-aggregate metrics
        aggregate_team_weekly_metrics_task.si(team_id),
        # Stage 4: Re-compute insights
        compute_team_insights.si(team_id),
        # Stage 5: Generate 90-day LLM insight (now have full 90 days of data)
        generate_team_llm_insights.si(team_id, days_list=[90]),
        # Stage 6: Final completion
        update_pipeline_status.si(team_id, "complete"),
    )

    # Phase 2 failures don't block dashboard - use graceful error handler
    pipeline = pipeline.on_error(handle_phase2_failure.s(team_id=team_id))

    return pipeline.apply_async()


def start_phase1_pipeline(team_id: int, repo_ids: list[int]) -> dict:
    """
    Start Phase 1 (Quick Start) of the two-phase onboarding pipeline.

    Uses signal-based state machine for resilient execution:
    - Updates status to 'syncing_members'
    - Django signal dispatches `sync_github_members_pipeline_task`
    - Each task updates status on completion, triggering the next task
    - Pipeline is self-healing: status field is source of truth

    Phase 1 sequence (signal-driven):
    0. syncing_members → sync_github_members_pipeline_task
    1. syncing → sync_historical_data_task (30 days)
    2. llm_processing → queue_llm_analysis_batch_task
    3. computing_metrics → aggregate_team_weekly_metrics_task
    4. computing_insights → compute_team_insights → generate_team_llm_insights
    5. phase1_complete → (signal triggers Phase 2)

    Args:
        team_id: The team's ID
        repo_ids: List of TrackedRepository IDs to sync (no longer used, kept for API compat)

    Returns:
        dict with pipeline start status
    """
    from apps.teams.models import Team

    logger.info(f"Starting Phase 1 pipeline (signal-based): team={team_id}")

    # Log pipeline started event
    sync_log = get_sync_logger(__name__)
    sync_log.info(
        "sync.pipeline.started",
        extra={
            "team_id": team_id,
            "repos_count": len(repo_ids) if repo_ids else 0,
            "phase": "phase1",
            "execution_mode": "signal_based",
        },
    )

    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.error(f"Team not found: {team_id}")
        return {"status": "error", "error": f"Team {team_id} not found"}

    # Start the pipeline by updating status to syncing_members
    # The signal handler will dispatch sync_github_members_pipeline_task
    team.update_pipeline_status("syncing_members")

    logger.info(f"Phase 1 pipeline started for team {team_id} - signal will dispatch first task")

    return {
        "status": "started",
        "team_id": team_id,
        "execution_mode": "signal_based",
        "initial_status": "syncing_members",
    }


def start_onboarding_pipeline(team_id: int, repo_ids: list[int]) -> dict:
    """
    Start the onboarding pipeline using Two-Phase Quick Start.

    Delegates to start_phase1_pipeline for faster time-to-dashboard.
    Phase 2 runs automatically in the background after Phase 1.

    Two-Phase Onboarding (signal-based):
    - Phase 1: 30 days sync → ALL PRs LLM → dashboard ready (~5 min)
    - Phase 2: 31-90 days sync → remaining LLM → complete (background)

    Signal-driven execution:
    - Each status change triggers the next task via Django signals
    - Self-healing: if worker restarts, pipeline resumes from current status
    - Observable: status field is always the source of truth

    Args:
        team_id: The team's ID
        repo_ids: List of TrackedRepository IDs to sync

    Returns:
        dict with pipeline start status
    """
    return start_phase1_pipeline(team_id, repo_ids)


# =============================================================================
# GitHub Member Sync Task for Pipeline
# =============================================================================


@shared_task(bind=True, soft_time_limit=180, time_limit=240)
def sync_github_members_pipeline_task(self, team_id: int) -> dict:
    """
    Sync GitHub organization members as part of the onboarding pipeline.

    This task runs synchronously within the pipeline chain to ensure members
    are synced before PR data is fetched (A-025 fix).

    Handles both integration types:
    - GitHubIntegration (OAuth flow)
    - GitHubAppInstallation (App flow)

    Args:
        team_id: The team's ID

    Returns:
        Dict with sync results or skip reason
    """
    from apps.integrations.models import GitHubAppInstallation, GitHubIntegration
    from apps.integrations.tasks import sync_github_app_members_task, sync_github_members_task
    from apps.teams.models import Team

    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.error(f"Team not found for member sync: {team_id}")
        return {"error": f"Team {team_id} not found"}

    logger.info(f"Starting member sync in pipeline for team {team.name}")

    result = None

    # Try OAuth integration first
    try:
        integration = GitHubIntegration.objects.get(team=team)
        # Run synchronously (not .delay()) to ensure completion before next stage
        result = sync_github_members_task(integration.id)
        logger.info(f"Member sync complete via OAuth for team {team.name}: {result}")
    except GitHubIntegration.DoesNotExist:
        pass

    # Try GitHub App installation if OAuth not found
    if result is None:
        try:
            installation = GitHubAppInstallation.objects.get(team=team)
            # Run synchronously (not .delay()) to ensure completion before next stage
            result = sync_github_app_members_task(installation.id)
            logger.info(f"Member sync complete via App for team {team.name}: {result}")
        except GitHubAppInstallation.DoesNotExist:
            pass

    if result is None:
        logger.warning(f"No GitHub integration found for team {team.slug}, skipping member sync")
        result = {"skipped": True, "reason": "No GitHub integration found"}

    # Signal-based pipeline: update status to trigger next task
    # Reload team to get fresh state
    team.refresh_from_db()
    team.update_pipeline_status("syncing")

    return result


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


# =============================================================================
# Pipeline Recovery System
# =============================================================================
# Celery chains don't survive worker restarts - when a worker dies mid-chain,
# pending tasks in the chain are lost. This recovery system detects stuck
# pipelines and resumes them from the appropriate step.


STUCK_THRESHOLD_MINUTES = 15  # Consider pipeline stuck after 15 minutes of no progress


def get_pipeline_resume_step(status: str) -> str | None:
    """
    Get the next pipeline step to resume from based on current status.

    The pipeline can get stuck after a status update but before the next task
    starts (e.g., worker restart). This function returns what task should run next.

    Args:
        status: Current pipeline status

    Returns:
        The next step to execute, or None if no recovery needed
    """
    # Map status -> what should run next
    resume_map = {
        # Phase 1 statuses
        "syncing_members": "sync_members",  # Resume member sync
        "syncing": "sync_prs",  # Resume PR sync (may be partially done)
        "llm_processing": "llm_analysis",  # Resume LLM analysis
        "computing_metrics": "aggregate_metrics",  # Resume aggregation
        "computing_insights": "compute_insights",  # Resume insights
        # Phase 2 statuses
        "background_syncing": "phase2_sync",  # Resume Phase 2 sync
        "background_llm": "phase2_llm",  # Resume Phase 2 LLM
    }
    return resume_map.get(status)


@shared_task(bind=True)
def recover_stuck_pipeline(self, team_id: int) -> dict:
    """
    Recover a single stuck pipeline by resuming from the appropriate step.

    This task is safe to call multiple times - it checks current status
    and only takes action if the pipeline is actually stuck.

    Args:
        team_id: The team's ID

    Returns:
        dict with recovery action taken
    """
    from apps.integrations.models import TrackedRepository
    from apps.integrations.tasks import (
        aggregate_team_weekly_metrics_task,
        queue_llm_analysis_batch_task,
        sync_historical_data_task,
    )
    from apps.metrics.tasks import compute_team_insights, generate_team_llm_insights
    from apps.teams.models import Team

    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.error(f"Recovery: Team not found: {team_id}")
        return {"status": "error", "error": f"Team {team_id} not found"}

    status = team.onboarding_pipeline_status
    resume_step = get_pipeline_resume_step(status)

    if not resume_step:
        logger.debug(f"Recovery: Team {team_id} status '{status}' doesn't need recovery")
        return {"status": "skipped", "reason": f"Status '{status}' not recoverable"}

    repo_ids = list(TrackedRepository.objects.filter(team=team).values_list("id", flat=True))
    logger.warning(f"Recovery: Resuming team {team_id} pipeline from '{status}' (step: {resume_step})")

    sync_log = get_sync_logger(__name__)
    sync_log.warning(
        "sync.pipeline.recovery",
        extra={
            "team_id": team_id,
            "stuck_status": status,
            "resume_step": resume_step,
        },
    )

    # Resume based on the step needed
    if resume_step == "sync_members":
        # Resume from member sync
        sync_github_members_pipeline_task.delay(team_id)
        # After member sync completes, we need to continue the pipeline
        # The simplest approach: dispatch the remaining Phase 1 chain
        chain(
            update_pipeline_status.si(team_id, "syncing"),
            sync_historical_data_task.si(team_id, repo_ids, days_back=30),
            update_pipeline_status.si(team_id, "llm_processing"),
            queue_llm_analysis_batch_task.si(team_id, batch_size=500),
            update_pipeline_status.si(team_id, "computing_metrics"),
            aggregate_team_weekly_metrics_task.si(team_id),
            update_pipeline_status.si(team_id, "computing_insights"),
            compute_team_insights.si(team_id),
            generate_team_llm_insights.si(team_id, days_list=[7, 30]),
            update_pipeline_status.si(team_id, "phase1_complete"),
            dispatch_phase2_pipeline.si(team_id, repo_ids),
        ).on_error(handle_pipeline_failure.s(team_id=team_id)).apply_async(countdown=5)

    elif resume_step == "sync_prs":
        # Resume from PR sync - may be partially done, sync_historical_data_task handles this
        chain(
            sync_historical_data_task.si(team_id, repo_ids, days_back=30),
            update_pipeline_status.si(team_id, "llm_processing"),
            queue_llm_analysis_batch_task.si(team_id, batch_size=500),
            update_pipeline_status.si(team_id, "computing_metrics"),
            aggregate_team_weekly_metrics_task.si(team_id),
            update_pipeline_status.si(team_id, "computing_insights"),
            compute_team_insights.si(team_id),
            generate_team_llm_insights.si(team_id, days_list=[7, 30]),
            update_pipeline_status.si(team_id, "phase1_complete"),
            dispatch_phase2_pipeline.si(team_id, repo_ids),
        ).on_error(handle_pipeline_failure.s(team_id=team_id)).apply_async()

    elif resume_step == "llm_analysis":
        # Resume from LLM analysis - queue_llm_analysis_batch_task handles partial completion
        chain(
            queue_llm_analysis_batch_task.si(team_id, batch_size=500),
            update_pipeline_status.si(team_id, "computing_metrics"),
            aggregate_team_weekly_metrics_task.si(team_id),
            update_pipeline_status.si(team_id, "computing_insights"),
            compute_team_insights.si(team_id),
            generate_team_llm_insights.si(team_id, days_list=[7, 30]),
            update_pipeline_status.si(team_id, "phase1_complete"),
            dispatch_phase2_pipeline.si(team_id, repo_ids),
        ).on_error(handle_pipeline_failure.s(team_id=team_id)).apply_async()

    elif resume_step == "aggregate_metrics":
        # Resume from metrics aggregation
        chain(
            aggregate_team_weekly_metrics_task.si(team_id),
            update_pipeline_status.si(team_id, "computing_insights"),
            compute_team_insights.si(team_id),
            generate_team_llm_insights.si(team_id, days_list=[7, 30]),
            update_pipeline_status.si(team_id, "phase1_complete"),
            dispatch_phase2_pipeline.si(team_id, repo_ids),
        ).on_error(handle_pipeline_failure.s(team_id=team_id)).apply_async()

    elif resume_step == "compute_insights":
        # Resume from insights computation
        chain(
            compute_team_insights.si(team_id),
            generate_team_llm_insights.si(team_id, days_list=[7, 30]),
            update_pipeline_status.si(team_id, "phase1_complete"),
            dispatch_phase2_pipeline.si(team_id, repo_ids),
        ).on_error(handle_pipeline_failure.s(team_id=team_id)).apply_async()

    elif resume_step == "phase2_sync":
        # Resume Phase 2 from sync (days 31-90) - includes member sync for new contributors
        chain(
            sync_github_members_pipeline_task.si(team_id),
            sync_historical_data_task.si(team_id, repo_ids, days_back=90, skip_recent=30),
            update_pipeline_status.si(team_id, "background_llm"),
            queue_llm_analysis_batch_task.si(team_id, batch_size=500),
            aggregate_team_weekly_metrics_task.si(team_id),
            compute_team_insights.si(team_id),
            generate_team_llm_insights.si(team_id, days_list=[90]),
            update_pipeline_status.si(team_id, "complete"),
            send_onboarding_complete_email.si(team_id),
        ).on_error(handle_phase2_failure.s(team_id=team_id)).apply_async()

    elif resume_step == "phase2_llm":
        # Resume Phase 2 from LLM analysis
        chain(
            queue_llm_analysis_batch_task.si(team_id, batch_size=500),
            aggregate_team_weekly_metrics_task.si(team_id),
            compute_team_insights.si(team_id),
            generate_team_llm_insights.si(team_id, days_list=[90]),
            update_pipeline_status.si(team_id, "complete"),
            send_onboarding_complete_email.si(team_id),
        ).on_error(handle_phase2_failure.s(team_id=team_id)).apply_async()

    return {"status": "recovered", "team_id": team_id, "from_status": status, "resume_step": resume_step}


@shared_task(bind=True)
def check_and_recover_stuck_pipelines(self) -> dict:
    """
    Check for and recover stuck pipelines across all teams.

    This task should be scheduled to run every 5-10 minutes via Celery Beat.
    It finds teams that have been in intermediate pipeline states for too long
    and dispatches recovery tasks for them.

    Criteria for "stuck":
    - Pipeline status is in an intermediate state (not terminal)
    - Status hasn't changed for STUCK_THRESHOLD_MINUTES
    - No active Celery tasks for this team's pipeline

    Returns:
        dict with recovery statistics
    """
    from datetime import timedelta

    from django.db.models import Q
    from django.utils import timezone

    from apps.teams.models import Team

    # Intermediate states that could be stuck
    intermediate_statuses = [
        "syncing_members",
        "syncing",
        "llm_processing",
        "computing_metrics",
        "computing_insights",
        "background_syncing",
        "background_llm",
    ]

    cutoff = timezone.now() - timedelta(minutes=STUCK_THRESHOLD_MINUTES)

    # Find teams with intermediate status and old updated_at
    # We use updated_at as a proxy for "when did something last happen"
    stuck_teams = Team.objects.filter(
        Q(onboarding_pipeline_status__in=intermediate_statuses),
        Q(updated_at__lt=cutoff) | Q(onboarding_pipeline_started_at__lt=cutoff),
    ).values_list("id", flat=True)

    stuck_count = len(stuck_teams)

    if stuck_count == 0:
        logger.debug("Pipeline recovery check: no stuck pipelines found")
        return {"checked": True, "stuck_found": 0, "recovered": 0}

    logger.warning(f"Pipeline recovery check: found {stuck_count} stuck pipeline(s)")

    recovered = 0
    for team_id in stuck_teams:
        try:
            recover_stuck_pipeline.delay(team_id)
            recovered += 1
        except Exception as e:
            logger.error(f"Failed to dispatch recovery for team {team_id}: {e}")

    return {"checked": True, "stuck_found": stuck_count, "recovered": recovered}
