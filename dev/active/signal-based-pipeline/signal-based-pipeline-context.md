# Signal-Based Pipeline - Context

**Last Updated: 2026-01-04**

## Key Files

### Core Implementation Files

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `apps/teams/models.py` | Team model with `onboarding_pipeline_status` | L37-71 (status field), L175-210 (`update_pipeline_status()`) |
| `apps/integrations/onboarding_pipeline.py` | Current chain-based pipeline | L339-409 (`start_phase1_pipeline`), L240-290 (`dispatch_phase2_pipeline`) |
| `apps/teams/signals.py` | Existing Team signals | Pattern to follow |
| `apps/integrations/signals.py` | Custom sync signals | Custom signal pattern |
| `apps/integrations/apps.py` | App config for signal registration | Signal import location |

### Task Files

| File | Purpose |
|------|---------|
| `apps/integrations/tasks.py` | sync_historical_data_task, sync_github_members_task |
| `apps/integrations/_task_modules/metrics.py` | queue_llm_analysis_batch_task, aggregate_team_weekly_metrics_task |
| `apps/metrics/tasks.py` | compute_team_insights, generate_team_llm_insights |

### Test Files

| File | Purpose |
|------|---------|
| `apps/integrations/tests/test_onboarding_pipeline.py` | Existing pipeline tests (20 tests) |
| `apps/integrations/tests/test_two_phase_sync.py` | Two-phase sync tests (8 tests) |

## Key Decisions Made

### 1. Signal vs Polling Approach
**Decision**: Use Django `post_save` signal on Team model
**Rationale**:
- Immediate dispatch (no polling delay)
- Built-in Django mechanism (no new dependencies)
- Clean separation of concerns

### 2. Status Tracking Method
**Decision**: Track original status in `__init__` (not django-model-utils FieldTracker)
**Rationale**:
- Avoids new dependency
- Simple implementation
- Pattern already used in codebase elsewhere

### 3. Task Dispatch Timing
**Decision**: Use `countdown=1` on task dispatch
**Rationale**:
- Allows current DB transaction to commit
- Prevents race conditions
- Task sees committed status

### 4. Error Handling Strategy
**Decision**: Signal handler catches exceptions, logs, doesn't block save
**Rationale**:
- Status update must succeed even if dispatch fails
- Recovery mechanism can pick up missed dispatches
- Preserves observability (status is truth)

## Pipeline Status Flow

```
Phase 1 (Quick Start - 30 days):
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ not_started     │───▶│syncing_members│───▶│    syncing      │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                                    │
                                                    ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ phase1_complete │◀───│computing_insights│◀───│  llm_processing │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       ▲
        │                       │
        │              ┌──────────────────┐
        │              │ computing_metrics │
        │              └──────────────────┘
        ▼
Phase 2 (Background - days 31-90):
┌───────────────────┐    ┌────────────────┐    ┌─────────────────┐
│background_syncing │───▶│ background_llm │───▶│    complete     │
└───────────────────┘    └────────────────┘    └─────────────────┘
```

## Special Cases

### 1. LLM Insights Generation (Two-Step)
The `computing_insights` status needs to trigger:
1. `compute_team_insights` (rule-based) → returns immediately
2. `generate_team_llm_insights` (LLM-based) → async

**Solution**: Chain these two in a mini-chain OR have `compute_team_insights` call the LLM task directly on completion.

### 2. Phase 1 → Phase 2 Transition
When status becomes `phase1_complete`:
1. User can access dashboard (immediate)
2. Phase 2 should start automatically (background)

**Solution**: Signal handler detects `phase1_complete` and dispatches Phase 2 start task.

### 3. Recovery Integration
Existing `check_and_recover_stuck_pipelines` task should still work:
- If pipeline is stuck, just update status to re-trigger signal
- Simpler recovery logic

## Dependencies

### Runtime Dependencies
- Django signals (built-in)
- Celery (existing)
- Redis broker (existing)

### No New Dependencies Required
- NOT using django-model-utils (FieldTracker)
- NOT using django-fsm (state machine library)
- Using simple Python dict for state machine config

## Environment Notes

- Celery worker must be running: `make celery` (uses `--pool=solo` on macOS)
- Redis must be running for broker
- Tests use Django TestCase with Celery task synchronous execution

## Related Issues

- Team 164: Pipeline stuck at `computing_insights` (fixed manually)
- Team 165: Pipeline stuck at `computing_insights` (fixed manually)
- Both required manual task execution to complete
