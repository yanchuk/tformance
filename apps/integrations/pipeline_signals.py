"""Signal-based pipeline state machine for onboarding.

This module provides a resilient alternative to Celery chains by using
Django signals to dispatch the next task when pipeline status changes.

Architecture:
- When Team.onboarding_pipeline_status changes, the post_save signal fires
- Signal handler looks up the next task in the state machine
- Task is dispatched with countdown=1 to allow transaction commit
- Each task updates status on completion, which triggers the next task

Benefits over Celery chains:
- Self-healing: Any status update automatically triggers next step
- Resilient: Worker restarts don't lose pending tasks
- Observable: Status field is the source of truth
- Recoverable: Recovery = update status, signal fires automatically
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def get_repo_ids(team):
    """Get TrackedRepository IDs for a team."""
    from apps.integrations.models import TrackedRepository

    return list(TrackedRepository.objects.filter(team=team).values_list("id", flat=True))


# =============================================================================
# State Machine Configuration
# =============================================================================
# Maps status → (task_function, kwargs_builder)
# kwargs_builder is a callable that takes (team) and returns task kwargs

# Phase 1 state machine - triggered by status changes
PHASE1_STATE_MACHINE = {
    "syncing_members": {
        "task_path": "apps.integrations.onboarding_pipeline.sync_github_members_pipeline_task",
        "kwargs_builder": lambda team: {},
    },
    "syncing": {
        "task_path": "apps.integrations.tasks.sync_historical_data_task",
        "kwargs_builder": lambda team: {"repo_ids": get_repo_ids(team), "days_back": 30},
    },
    "syncing_copilot": {
        "task_path": "apps.integrations._task_modules.copilot.sync_copilot_pipeline_task",
        "kwargs_builder": lambda team: {},
    },
    "llm_processing": {
        "task_path": "apps.integrations._task_modules.metrics.queue_llm_analysis_batch_task",
        "kwargs_builder": lambda team: {"batch_size": 500},
    },
    "computing_metrics": {
        "task_path": "apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task",
        "kwargs_builder": lambda team: {},
    },
    "computing_insights": {
        "task_path": "apps.metrics.tasks.compute_team_insights",
        "kwargs_builder": lambda team: {},
    },
}

# Phase 2 state machine
PHASE2_STATE_MACHINE = {
    "background_syncing": {
        "task_path": "apps.integrations.tasks.sync_historical_data_task",
        "kwargs_builder": lambda team: {"repo_ids": get_repo_ids(team), "days_back": 90, "skip_recent": 30},
    },
    "background_llm": {
        "task_path": "apps.integrations._task_modules.metrics.queue_llm_analysis_batch_task",
        "kwargs_builder": lambda team: {"batch_size": 500},
    },
    "background_metrics": {
        "task_path": "apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task",
        "kwargs_builder": lambda team: {},
    },
    "background_insights": {
        "task_path": "apps.metrics.tasks.compute_team_insights",
        "kwargs_builder": lambda team: {},
    },
}

# Combined state machine
PIPELINE_STATE_MACHINE = {**PHASE1_STATE_MACHINE, **PHASE2_STATE_MACHINE}

# Terminal states that don't dispatch further tasks
TERMINAL_STATES = {"complete", "failed", "not_started"}

# Special state that triggers Phase 2
PHASE1_COMPLETE_STATE = "phase1_complete"


def get_task_by_path(task_path: str):
    """Import and return a Celery task by its module path."""
    from importlib import import_module

    module_path, task_name = task_path.rsplit(".", 1)
    module = import_module(module_path)
    return getattr(module, task_name)


def dispatch_pipeline_task(team_id: int, status: str) -> bool:
    """Dispatch the appropriate task for the given pipeline status.

    Args:
        team_id: Team ID
        status: Current pipeline status

    Returns:
        True if task was dispatched, False otherwise
    """
    from apps.teams.models import Team

    # Don't dispatch for terminal states
    if status in TERMINAL_STATES:
        logger.debug(f"Pipeline dispatch: status '{status}' is terminal, no dispatch")
        return False

    # Check state machine for this status
    task_config = PIPELINE_STATE_MACHINE.get(status)
    if not task_config:
        logger.debug(f"Pipeline dispatch: no task configured for status '{status}'")
        return False

    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.error(f"Pipeline dispatch: team {team_id} not found")
        return False

    # Get task and kwargs
    task_path = task_config["task_path"]
    kwargs_builder = task_config["kwargs_builder"]

    try:
        task = get_task_by_path(task_path)
        kwargs = kwargs_builder(team)

        # Dispatch with countdown=1 to allow DB transaction to commit
        task.apply_async(args=[team_id], kwargs=kwargs, countdown=1)

        logger.info(f"Pipeline dispatch: dispatched {task_path} for team {team_id} (status: {status})")
        return True

    except Exception as e:
        logger.exception(f"Pipeline dispatch: failed to dispatch task for team {team_id}: {e}")
        return False


def dispatch_phase2_start(team_id: int) -> bool:
    """Dispatch the start of Phase 2 pipeline.

    Called when status changes to 'phase1_complete'.

    Args:
        team_id: Team ID

    Returns:
        True if Phase 2 was dispatched, False otherwise
    """
    from apps.teams.models import Team

    try:
        if not Team.objects.filter(id=team_id).exists():
            logger.error(f"Pipeline: team {team_id} not found for Phase 2 start")
            return False

        # Update status to background_syncing - signal will dispatch the sync task
        # Use delay to allow current transaction to commit
        from apps.integrations.onboarding_pipeline import update_pipeline_status

        update_pipeline_status.apply_async(args=[team_id, "background_syncing"], countdown=2)

        logger.info(f"Pipeline: dispatched Phase 2 start for team {team_id}")
        return True
    except Exception as e:
        logger.exception(f"Pipeline: failed to dispatch Phase 2 for team {team_id}: {e}")
        return False


def dispatch_llm_insights_and_complete(team_id: int) -> bool:
    """Dispatch LLM insights generation after rule-based insights complete.

    Called after compute_team_insights completes. This dispatches the
    LLM insights task and then updates status to phase1_complete.

    Args:
        team_id: Team ID

    Returns:
        True if dispatched successfully
    """
    from apps.metrics.tasks import generate_team_llm_insights

    try:
        # Dispatch LLM insights with callback to update status
        generate_team_llm_insights.apply_async(
            args=[team_id],
            kwargs={"days_list": [7, 30]},
            countdown=1,
        )
        logger.info(f"Pipeline: dispatched LLM insights for team {team_id}")
        return True
    except Exception as e:
        logger.exception(f"Pipeline: failed to dispatch LLM insights for team {team_id}: {e}")
        return False


# =============================================================================
# Signal Handler
# =============================================================================


@receiver(post_save, sender="teams.Team")
def on_pipeline_status_change(sender, instance, update_fields, **kwargs):
    """Dispatch next pipeline task when status changes.

    This signal handler detects when onboarding_pipeline_status changes
    and dispatches the appropriate next task based on the state machine.

    Uses transaction.on_commit() to defer task dispatch until after the
    database transaction commits, ensuring the view responds quickly.

    Args:
        sender: Team model class
        instance: Team instance
        update_fields: Fields that were updated (if save used update_fields)
        **kwargs: Additional signal kwargs
    """
    from django.db import transaction

    # Skip if this save didn't include the status field
    if update_fields and "onboarding_pipeline_status" not in update_fields:
        return

    new_status = instance.onboarding_pipeline_status
    old_status = getattr(instance, "_original_pipeline_status", None)

    # Skip if status didn't actually change
    if old_status == new_status:
        return

    logger.debug(f"Pipeline status changed: team={instance.id}, {old_status} → {new_status}")

    # Update the tracked original status for future saves
    instance._original_pipeline_status = new_status

    # Capture values for the closure (instance may change)
    team_id = instance.id

    def dispatch_after_commit():
        """Dispatch task after transaction commits to avoid blocking the response."""
        try:
            # Special handling for phase1_complete - trigger Phase 2
            if new_status == PHASE1_COMPLETE_STATE:
                dispatch_phase2_start(team_id)
                return

            # Dispatch task for this status
            dispatch_pipeline_task(team_id, new_status)

        except Exception as e:
            # Never let signal handler break the save
            logger.exception(f"Pipeline signal handler error for team {team_id}: {e}")

    # Defer task dispatch until after transaction commits
    # This ensures the view responds immediately
    transaction.on_commit(dispatch_after_commit)


# =============================================================================
# Lazy imports to avoid circular dependencies
# =============================================================================

# Import tasks lazily when needed to avoid circular imports at module load
sync_github_members_pipeline_task = None
sync_historical_data_task = None
queue_llm_analysis_batch_task = None
aggregate_team_weekly_metrics_task = None
compute_team_insights = None
