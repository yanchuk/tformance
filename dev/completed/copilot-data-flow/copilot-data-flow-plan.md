# Copilot Data Flow Implementation Plan

**Last Updated: 2026-01-11**
**Status: IN PROGRESS - Phase A-C Complete, Phase D-F In Progress**

## Executive Summary

Implement the Copilot data flow features to enable:
1. **Team-level Copilot status tracking** with `copilot_status` field ✅
2. **Nightly automated sync** via Celery Beat at 4:45 AM UTC ✅
3. **Pipeline integration** for syncing Copilot data during onboarding 🟡
4. **Graceful handling** of edge cases (insufficient licenses, token revocation) 🟡
5. **LLM insight regeneration** with Copilot data after nightly sync ❌

---

## User Story Coverage

| US | Title | Status | Priority |
|----|-------|--------|----------|
| US-1 | Copilot Onboarding Step | ❌ Not Started | P1 - Future |
| US-2 | Pipeline Integration (syncing_copilot) | 🟡 In Progress | P0 - Current |
| US-3 | Post-Activation (Settings UI) | ❌ Not Started | P1 - Future |
| US-4 | Nightly Sync | ✅ Complete | P0 |
| US-5 | Nightly LLM Insight Regeneration | ❌ Not Started | P0 - Current |
| US-6 | Insufficient Licenses UX | 🟡 Partial (fields only) | P1 |
| US-7 | Email Timing | ⏸️ Pre-existing | N/A |
| US-8 | Org Admin Permission Check | ❌ Not Started | P2 |
| US-9 | License Count Changes | 🟡 Partial (fields only) | P1 |
| US-10 | Cross-Team Isolation | ⏸️ Pre-existing | N/A |

---

## Current State (What's Done)

### Phase A: Foundation ✅

| Component | Status | Notes |
|-----------|--------|-------|
| `copilot_status` field on Team | ✅ | 4 choices: disabled, connected, insufficient_licenses, token_revoked |
| `copilot_last_sync_at` field | ✅ | DateTimeField, nullable |
| `copilot_consecutive_failures` field | ✅ | PositiveIntegerField, default 0 |
| `copilot_enabled` property | ✅ | Returns `copilot_status == "connected"` |
| Migration `0010_add_copilot_status` | ✅ | Applied |
| TDD tests (12 tests) | ✅ | All passing |

### Phase B: Celery Beat ✅

| Component | Status | Notes |
|-----------|--------|-------|
| `sync-copilot-metrics-daily` schedule | ✅ | 4:45 AM UTC |
| Task path verified | ✅ | `apps.integrations.tasks.sync_all_copilot_metrics` |

### Phase C: Sync Task Enhancement ✅

| Component | Status | Notes |
|-----------|--------|-------|
| Filter by `copilot_status="connected"` | ✅ | Only syncs connected teams |
| Monitoring (dispatched, skipped, duration) | ✅ | Logged and returned in result dict |
| Tests updated (11 tests) | ✅ | All passing |

### Phase D: Pipeline Integration 🟡

| Component | Status | Notes |
|-----------|--------|-------|
| `syncing_copilot` in PIPELINE_STATUS_CHOICES | ✅ | Added after `syncing` |
| `syncing_copilot` in PHASE1_STATE_MACHINE | ❌ | Needs task entry |
| Pipeline task with conditional skip | ❌ | If copilot_status != "connected", skip to next |
| `pipeline_in_progress` property update | ❌ | Add syncing_copilot |
| Sync progress template | ❌ | Show Copilot step |

---

## Implementation Plan (Remaining)

### Phase D: Pipeline Integration (Current)

**Goal**: Integrate Copilot sync into onboarding pipeline so new teams get Copilot data before LLM insights.

#### D.1: Add syncing_copilot to PHASE1_STATE_MACHINE

**File**: `apps/integrations/pipeline_signals.py`

```python
PHASE1_STATE_MACHINE = {
    "syncing_members": {...},
    "syncing": {...},
    "syncing_copilot": {  # NEW
        "task_path": "apps.integrations._task_modules.copilot.sync_copilot_pipeline_task",
        "kwargs_builder": lambda team: {},
    },
    "llm_processing": {...},
    # ...
}
```

#### D.2: Create sync_copilot_pipeline_task

**File**: `apps/integrations/_task_modules/copilot.py`

This task:
1. Checks if `team.copilot_status == "connected"`
2. If yes: runs sync, updates status to `llm_processing`
3. If no: skips directly to `llm_processing`

```python
@shared_task
def sync_copilot_pipeline_task(team_id: int) -> dict:
    """Copilot sync step in onboarding pipeline.

    If team has Copilot connected, syncs metrics.
    If not, skips to next pipeline step.
    """
    team = Team.objects.get(id=team_id)

    if team.copilot_status != "connected":
        # Skip Copilot sync, proceed to LLM processing
        team.update_pipeline_status("llm_processing")
        return {"status": "skipped", "reason": "copilot_not_connected"}

    # Run sync
    result = sync_copilot_metrics_task(team_id)

    # Proceed to LLM processing
    team.update_pipeline_status("llm_processing")
    return result
```

#### D.3: Update pipeline_in_progress property

**File**: `apps/teams/models.py`

```python
@property
def pipeline_in_progress(self) -> bool:
    return self.onboarding_pipeline_status in [
        "syncing_members",
        "syncing",
        "syncing_copilot",  # NEW
        "llm_processing",
        # ...
    ]
```

### Phase E: Error Status Handling (US-4, US-9)

**Goal**: Update `copilot_status` based on sync errors.

#### E.1: Update sync_copilot_metrics_task

**File**: `apps/integrations/_task_modules/copilot.py`

```python
except CopilotMetricsError as e:
    if "403" in str(e):
        # Insufficient licenses
        team.copilot_status = "insufficient_licenses"
        team.copilot_consecutive_failures += 1
        team.save(update_fields=["copilot_status", "copilot_consecutive_failures"])
        return {"status": "skipped", "reason": "insufficient_licenses"}

    if "401" in str(e):
        # Token revoked
        team.copilot_status = "token_revoked"
        team.save(update_fields=["copilot_status"])
        credential.is_revoked = True
        credential.save(update_fields=["is_revoked"])
        return {"status": "error", "reason": "token_revoked"}
```

#### E.2: Reset on success

```python
# On successful sync
team.copilot_consecutive_failures = 0
team.copilot_last_sync_at = timezone.now()
team.save(update_fields=["copilot_consecutive_failures", "copilot_last_sync_at"])
```

### Phase F: LLM Insight Regeneration (US-5)

**Goal**: After nightly Copilot sync, regenerate LLM insights to include fresh data.

#### F.1: Update run_all_teams_llm_analysis

**File**: `apps/metrics/tasks.py`

The existing nightly LLM task at 5:00 AM already runs after Copilot sync (4:45 AM).
Ensure `gather_insight_data()` includes Copilot metrics when `team.copilot_enabled`.

#### F.2: Verify gather_insight_data includes Copilot

**File**: `apps/metrics/services/insight_llm.py`

```python
def gather_insight_data(team, start_date, end_date):
    # ... existing code ...

    # Include Copilot metrics if team has it enabled
    copilot_metrics = None
    if team.copilot_enabled:
        copilot_metrics = get_copilot_metrics_for_prompt(team, start_date, end_date)

    data["copilot_metrics"] = copilot_metrics
    data["include_copilot"] = copilot_metrics is not None
    return data
```

---

## Files to Modify

| File | Changes | Phase |
|------|---------|-------|
| `apps/teams/models.py` | Add syncing_copilot to pipeline_in_progress | D |
| `apps/integrations/pipeline_signals.py` | Add syncing_copilot to PHASE1_STATE_MACHINE | D |
| `apps/integrations/_task_modules/copilot.py` | Add sync_copilot_pipeline_task, error handling | D, E |
| `apps/metrics/services/insight_llm.py` | Verify Copilot metrics inclusion | F |
| `templates/onboarding/sync_progress.html` | Show Copilot step (optional) | D |

---

## Test Files

| File | Tests | Status |
|------|-------|--------|
| `apps/teams/tests/test_copilot_status.py` | 12 tests for copilot_status field | ✅ |
| `apps/integrations/tests/test_copilot_sync.py` | 11 tests for sync task | ✅ |
| `apps/integrations/tests/test_copilot_pipeline.py` | Pipeline integration tests | ❌ To create |

---

## Verification Commands

```bash
# Run all Copilot tests
.venv/bin/pytest apps/teams/tests/test_copilot_status.py apps/integrations/tests/test_copilot_sync.py -v

# Test pipeline integration (after implementation)
.venv/bin/pytest apps/integrations/tests/test_copilot_pipeline.py -v

# Manual sync test
.venv/bin/python -c "
from apps.integrations.tasks import sync_all_copilot_metrics
result = sync_all_copilot_metrics()
print(result)
"

# Check Celery Beat schedule
.venv/bin/celery -A tformance inspect scheduled
```

---

## Success Metrics

- [ ] All 23+ Copilot tests pass
- [ ] Pipeline correctly syncs Copilot for connected teams
- [ ] Pipeline skips Copilot for non-connected teams
- [ ] 403 errors set status to `insufficient_licenses`
- [ ] 401 errors set status to `token_revoked`
- [ ] LLM insights include Copilot data after nightly sync
