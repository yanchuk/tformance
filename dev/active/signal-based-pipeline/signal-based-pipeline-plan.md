# Signal-Based Pipeline State Machine

**Last Updated: 2026-01-04**

## Executive Summary

Replace fragile Celery chain-based onboarding pipeline with a signal-driven state machine. When `Team.onboarding_pipeline_status` changes, a Django signal automatically dispatches the next task. This eliminates chain fragility where worker restarts lose remaining tasks.

## Problem Statement

### Current Issue
The onboarding pipeline uses Celery chains:
```python
chain(task_A, task_B, task_C, task_D).apply_async()
```

**Failure mode**: If a worker restarts after task_A completes but before task_B starts, tasks B/C/D are lost. The chain state is in memory, not persisted.

**Observed symptoms**:
- Pipeline stuck at `computing_insights` for Team 164 and 165
- `compute_team_insights` and `generate_team_llm_insights` never ran
- Phase 2 never started because Phase 1 didn't complete
- Manual intervention required to complete pipelines

### Root Cause
Celery chains rely on the worker maintaining chain state in memory. Any interruption (worker restart, broker disconnect, timeout) breaks the chain silently with no automatic recovery.

## Proposed Solution

### Signal-Based State Machine

Replace chains with independent tasks triggered by status changes:

```python
# When Team.onboarding_pipeline_status changes
@receiver(post_save, sender=Team)
def dispatch_next_pipeline_task(sender, instance, **kwargs):
    old_status = getattr(instance, '_original_status', None)
    new_status = instance.onboarding_pipeline_status

    if old_status != new_status:
        next_task = PIPELINE_STATE_MACHINE.get(new_status)
        if next_task:
            next_task.delay(instance.id)
```

**Benefits**:
1. **Self-healing**: Any status update automatically triggers next step
2. **Idempotent**: Tasks can be safely re-run
3. **Observable**: Status field is source of truth
4. **Recoverable**: Recovery = update status, signal fires automatically

## Architecture

### State Machine Definition

```
not_started → (start_pipeline) → syncing_members
syncing_members → (sync complete) → syncing
syncing → (sync complete) → llm_processing
llm_processing → (LLM complete) → computing_metrics
computing_metrics → (metrics done) → computing_insights
computing_insights → (insights done) → phase1_complete

phase1_complete → (auto-dispatch) → background_syncing
background_syncing → (sync complete) → background_llm
background_llm → (LLM complete) → complete
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `Team.update_pipeline_status()` | Updates status field, triggers save |
| `post_save` signal handler | Detects status change, dispatches next task |
| Individual tasks | Do work, then call `update_pipeline_status()` |
| State machine config | Maps status → next_task |

## Implementation Plan

### Phase 1: Foundation (TDD RED)

1. **Add FieldTracker to Team model** (or use `__init__` tracking)
2. **Create pipeline state machine configuration**
3. **Write failing tests for signal-based dispatch**

### Phase 2: Signal Handler (TDD GREEN)

1. **Implement signal handler** in `apps/integrations/pipeline_signals.py`
2. **Wire up in `apps/integrations/apps.py`**
3. **Modify tasks to use `update_pipeline_status()` instead of chain continuation**

### Phase 3: Refactor Pipeline (TDD REFACTOR)

1. **Remove chain-based dispatching** from `start_phase1_pipeline()`
2. **Simplify `dispatch_phase2_pipeline()`** - just update status
3. **Update recovery system** to leverage signals

## Technical Design

### File Changes

| File | Change |
|------|--------|
| `apps/teams/models.py` | Add `_original_status` tracking in `__init__` |
| `apps/integrations/pipeline_signals.py` | NEW: State machine + signal handler |
| `apps/integrations/apps.py` | Import signals to register handler |
| `apps/integrations/onboarding_pipeline.py` | Remove chains, simplify to status updates |
| `apps/integrations/tasks.py` | Tasks call `update_pipeline_status()` on completion |

### State Machine Configuration

```python
# apps/integrations/pipeline_signals.py

from apps.integrations.tasks import (
    sync_github_members_pipeline_task,
    sync_historical_data_task,
    queue_llm_analysis_batch_task,
    aggregate_team_weekly_metrics_task,
)
from apps.metrics.tasks import compute_team_insights, generate_team_llm_insights

# Status → (next_task, task_kwargs_func)
PHASE1_STATE_MACHINE = {
    "syncing_members": (sync_github_members_pipeline_task, lambda t: {}),
    "syncing": (sync_historical_data_task, lambda t: {"repo_ids": get_repo_ids(t), "days_back": 30}),
    "llm_processing": (queue_llm_analysis_batch_task, lambda t: {"batch_size": 500}),
    "computing_metrics": (aggregate_team_weekly_metrics_task, lambda t: {}),
    "computing_insights": (compute_team_insights, lambda t: {}),
}

# Insights completion triggers LLM insights then phase1_complete
# This needs special handling - see detailed design
```

### Signal Handler Implementation

```python
@receiver(post_save, sender=Team)
def on_pipeline_status_change(sender, instance, update_fields, **kwargs):
    """Dispatch next pipeline task when status changes."""
    # Only fire if status was actually updated
    if update_fields and "onboarding_pipeline_status" not in update_fields:
        return

    # Get the task to run based on current status
    task_config = PIPELINE_STATE_MACHINE.get(instance.onboarding_pipeline_status)
    if not task_config:
        return

    task_func, kwargs_func = task_config
    kwargs = kwargs_func(instance)

    # Dispatch with countdown to allow current transaction to commit
    task_func.apply_async(args=[instance.id], kwargs=kwargs, countdown=1)
```

### Task Modification Pattern

Before (chain-based):
```python
# Task A completes, chain automatically calls Task B
```

After (signal-based):
```python
def task_a(team_id):
    # Do work...
    team = Team.objects.get(id=team_id)
    team.update_pipeline_status("next_status")  # Signal fires, dispatches Task B
```

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Double-dispatch on rapid saves | Use countdown, check if task already queued |
| Signal handler exceptions break saves | Catch exceptions, log errors, don't block save |
| Status update in failed task | Task failure handlers update to appropriate status |
| Migration complexity | Gradual rollout, keep chain fallback initially |

## Success Metrics

1. **Zero stuck pipelines** - No manual intervention needed
2. **Reduced time-to-dashboard** - Pipeline completes reliably
3. **Observable progress** - Status field accurately reflects state
4. **Test coverage** - 100% coverage on state machine transitions

## Dependencies

- Django signals (built-in)
- Celery task dispatch
- Team model status tracking

## Timeline Estimate

| Phase | Effort | Description |
|-------|--------|-------------|
| RED tests | M | Write failing tests for signal dispatch |
| GREEN implementation | M | Implement signal handler + state machine |
| REFACTOR pipeline | L | Remove chains, update all tasks |
| Integration testing | M | Test full pipeline flows |

**Total: ~4-6 hours**
