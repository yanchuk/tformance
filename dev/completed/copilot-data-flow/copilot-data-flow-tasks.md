# Copilot Data Flow - Tasks

**Last Updated: 2026-01-11**
**Status: COMPLETE - All phases and UI implemented**

## Legend
- [ ] Not started
- [~] In progress
- [x] Completed

---

## Phase A: Foundation (CRITICAL PATH)

### A.1: Add copilot_status field to Team model

**TDD Status:** ✅ GREEN complete

- [x] RED: Write failing test for copilot_status field
- [x] GREEN: Implement copilot_status field in Team model
- [x] REFACTOR: Clean up if needed

**Test file:** `apps/teams/tests/test_copilot_status.py`
**Implementation file:** `apps/teams/models.py`

```python
# Add after PIPELINE_STATUS_CHOICES (around line 49)
COPILOT_STATUS_CHOICES = [
    ("disabled", "Not Connected"),
    ("connected", "Connected"),
    ("insufficient_licenses", "Awaiting Data"),
    ("token_revoked", "Reconnection Required"),
]

# Add fields after background_llm_progress (around line 82)
copilot_status = models.CharField(
    max_length=30,
    choices=COPILOT_STATUS_CHOICES,
    default="disabled",
    help_text="Current Copilot integration status",
)
copilot_last_sync_at = models.DateTimeField(
    null=True,
    blank=True,
    help_text="Last successful Copilot data sync",
)
copilot_consecutive_failures = models.PositiveIntegerField(
    default=0,
    help_text="Count of consecutive sync failures (reset on success)",
)

# Add property after dashboard_accessible property (around line 145)
@property
def copilot_enabled(self) -> bool:
    """Backward-compatible property for checking Copilot connectivity."""
    return self.copilot_status == "connected"
```

### A.2: Create migration

- [x] Run `makemigrations teams --name add_copilot_status`
- [x] Review migration file
- [x] Run `migrate`

```bash
.venv/bin/python manage.py makemigrations teams --name add_copilot_status
.venv/bin/python manage.py migrate
```

### A.3: Run tests (TDD GREEN)

- [x] Run copilot status tests
- [x] All 12 tests pass

```bash
.venv/bin/pytest apps/teams/tests/test_copilot_status.py -v
```

**Expected result:** 12 tests pass

---

## Phase B: Celery Beat Schedule ✅

### B.1: Add schedule to settings.py

- [x] Add sync-copilot-metrics-daily entry
- [x] Set to 4:45 AM UTC

**File:** `tformance/settings.py`
**Location:** Line 694-698

```python
"sync-copilot-metrics-daily": {
    "task": "apps.integrations.tasks.sync_all_copilot_metrics",
    "schedule": schedules.crontab(minute=45, hour=4),  # 4:45 AM UTC (after GitHub, before LLM)
    "options": {"expire_seconds": 60 * 60 * 2},  # 2 hour expiry
},
```

### B.2: Verify schedule

- [x] Schedule added successfully
- [x] Task path verified

```bash
# Start beat for 10 seconds to verify
timeout 10 .venv/bin/celery -A tformance beat --loglevel=info || true
```

---

## Phase C: Sync Task Enhancement ✅

### C.1: Update sync_all_copilot_metrics

- [x] Team model already imported
- [x] Filter by copilot_status="connected"
- [x] Add monitoring (teams_dispatched, teams_skipped, duration_seconds)

**File:** `apps/integrations/_task_modules/copilot.py` (lines 284-344)

### C.2: Write tests for filtering

- [x] Test only connected teams are synced
- [x] Test disabled teams are skipped
- [x] Test monitoring output
- [x] All 11 sync tests pass

**File:** `apps/integrations/tests/test_copilot_sync.py`

### C.3: Update sync_copilot_metrics_task for status updates ✅

- [x] On 403 error, set status to insufficient_licenses
- [x] On 401 error, set status to token_revoked and mark credential as revoked
- [x] On success, reset consecutive_failures and update last_sync_at

**File:** `apps/integrations/_task_modules/copilot.py` (lines 199-243)

---

## Phase D: Pipeline Integration ✅

### D.1: Add syncing_copilot status

- [x] Add to PIPELINE_STATUS_CHOICES in Team model
- [x] Update pipeline_in_progress property

### D.2: Update state machine

- [x] Add syncing_copilot to PHASE1_STATE_MACHINE

**File:** `apps/integrations/pipeline_signals.py` (line 50-53)

### D.3: Create sync_copilot_pipeline_task

- [x] Check if team.copilot_status == "connected"
- [x] If connected: run sync, update status to llm_processing
- [x] If not connected: skip directly to llm_processing
- [x] If sync fails: log warning, continue to llm_processing (graceful degradation)

**File:** `apps/integrations/_task_modules/copilot.py` (lines 241-281)

### D.4: Write tests for pipeline task

- [x] Test task skips when copilot_status != "connected"
- [x] Test task syncs when copilot_status == "connected"
- [x] Test task continues on sync error (pipeline doesn't break)

**File:** `apps/integrations/tests/test_copilot_sync.py` (TestSyncCopilotPipelineTask class)

---

## Phase E: LLM Insight Integration ✅

### E.1: Update gather_insight_data to check copilot_enabled

- [x] Added team.copilot_enabled check before including Copilot metrics
- [x] Still checks CopilotSeatSnapshot for 5+ seats requirement

**File:** `apps/metrics/services/insight_llm.py` (lines 462-483)

### E.2: Verify Celery Beat timing

- [x] Copilot sync: 4:45 AM UTC
- [x] LLM analysis: 5:00 AM UTC
- [x] Timing ensures Copilot data is fresh before LLM runs

---

## Quick Commands

```bash
# Run all tests for this feature
.venv/bin/pytest apps/teams/tests/test_copilot_status.py -v

# Create migration
.venv/bin/python manage.py makemigrations teams --name add_copilot_status

# Apply migration
.venv/bin/python manage.py migrate

# Test sync task manually
.venv/bin/python -c "
from apps.integrations.tasks import sync_all_copilot_metrics
result = sync_all_copilot_metrics()
print(result)
"

# Check schedule
.venv/bin/celery -A tformance inspect scheduled
```

---

## Session Progress

### Session 1 (2026-01-11)

**Completed:**
- [x] Created dev docs structure
- [x] TDD RED phase: Wrote 12 failing tests for copilot_status

### Session 2 (2026-01-11)

**Completed:**
- [x] TDD GREEN phase: Implemented copilot_status field on Team model
- [x] Created migration `0010_add_copilot_status.py`
- [x] Applied migration successfully
- [x] All 12 copilot_status tests pass
- [x] Added Celery Beat schedule at 4:45 AM UTC
- [x] Updated sync_all_copilot_metrics to filter by copilot_status="connected"
- [x] Added monitoring (teams_dispatched, teams_skipped, duration_seconds)
- [x] Updated tests - all 23 tests pass (12 status + 11 sync)

### Session 3 (2026-01-11)

**Completed:**
- [x] Phase D: Added syncing_copilot to PHASE1_STATE_MACHINE
- [x] Created sync_copilot_pipeline_task with conditional skip logic
- [x] Updated pipeline_in_progress property to include syncing_copilot
- [x] Phase C.3: Updated sync_copilot_metrics_task for error handling:
  - 403 error → set copilot_status="insufficient_licenses"
  - 401 error → set copilot_status="token_revoked", mark credential revoked
  - Success → reset consecutive_failures, update last_sync_at
- [x] Phase E: Updated gather_insight_data to check team.copilot_enabled
- [x] All 29 Copilot tests pass (12 status + 17 sync/pipeline)

**Completed in copilot-ui-integration:**
- [x] US-1: Copilot onboarding step (UI for connecting during onboarding)
- [x] US-3: Post-activation settings page (UI for connecting after onboarding)
- [x] Sync progress template update (show Copilot step in stepper)

**All Copilot Data Flow work is complete!**
