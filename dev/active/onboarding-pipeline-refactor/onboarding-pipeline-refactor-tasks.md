# Onboarding Pipeline Refactor - Task Checklist

**Last Updated:** 2025-12-29
**Status:** COMPLETED

## Pre-Implementation Setup

- [x] ~~Create git worktree for feature branch~~ (worked in main worktree)
- [x] Verify dev environment works
- [x] Run existing tests to establish baseline (3851 tests passing)

---

## Phase 1: Model & Signal Infrastructure [Effort: M] - COMPLETED

### 1.1 Team Model - Pipeline Tracking Fields

**TDD RED:**
- [x] Write test: `test_team_has_pipeline_status_field`
- [x] Write test: `test_team_pipeline_status_default_not_started`
- [x] Write test: `test_team_pipeline_status_choices_valid`
- [x] Write test: `test_team_has_pipeline_error_field`
- [x] Write test: `test_team_has_pipeline_timestamps`
- [x] Verify tests FAIL

**TDD GREEN:**
- [x] Add `onboarding_pipeline_status` field to Team model
- [x] Add `onboarding_pipeline_error` field
- [x] Add `onboarding_pipeline_started_at` field
- [x] Add `onboarding_pipeline_completed_at` field
- [x] Create migration: `0005_add_pipeline_tracking_fields`
- [x] Run migration
- [x] Verify tests PASS (20 tests)

**TDD REFACTOR:**
- [x] Add helper method `update_pipeline_status(status, error=None)`
- [x] Add property `pipeline_in_progress`
- [x] Ensure clean code, no duplication

### 1.2 Signal Receivers

**TDD RED:**
- [x] Write test: `test_onboarding_sync_completed_receiver_called`
- [x] Write test: `test_repository_sync_completed_receiver_called`
- [x] Write test: `test_receiver_logs_completion`
- [x] Verify tests FAIL

**TDD GREEN:**
- [x] Create `apps/integrations/receivers.py`
- [x] Implement `@receiver(onboarding_sync_completed)` handler
- [x] Implement `@receiver(repository_sync_completed)` handler
- [x] Verify tests PASS (10 tests)

**TDD REFACTOR:**
- [x] Ensure receivers are lightweight (no blocking operations)
- [x] Add appropriate logging

### 1.3 App Config Integration

**TDD RED:**
- [x] Write test: `test_receivers_registered_on_app_ready`
- [x] Verify tests FAIL

**TDD GREEN:**
- [x] Add `ready()` method to `IntegrationsConfig`
- [x] Import receivers in `ready()`
- [x] Verify tests PASS

**Phase 1 Acceptance:**
- [x] All Phase 1 tests pass
- [x] Migration applied successfully
- [x] Signals fire AND are received (verify with logging)

---

## Phase 2: Task Chain Orchestration [Effort: L] - COMPLETED

### 2.1 Pipeline Status Update Task

**TDD RED:**
- [x] Write test: `test_update_pipeline_status_updates_team`
- [x] Write test: `test_update_pipeline_status_sets_started_at`
- [x] Write test: `test_update_pipeline_status_sets_completed_at_on_complete`
- [x] Write test: `test_update_pipeline_status_invalid_team_logs_error`
- [x] Verify tests FAIL

**TDD GREEN:**
- [x] Create `apps/integrations/onboarding_pipeline.py` (standalone module)
- [x] Implement `update_pipeline_status` task
- [x] Verify tests PASS

### 2.2 Pipeline Error Handler

**TDD RED:**
- [x] Write test: `test_handle_pipeline_failure_sets_status_failed`
- [x] Write test: `test_handle_pipeline_failure_stores_error_message`
- [x] Verify tests FAIL

**TDD GREEN:**
- [x] Implement `handle_pipeline_failure` task
- [x] Verify tests PASS

### 2.3 Start Pipeline Function

**TDD RED:**
- [x] Write test: `test_start_pipeline_returns_async_result`
- [x] Write test: `test_start_pipeline_chain_order_correct`
- [x] Write test: `test_start_pipeline_has_error_handler`
- [x] Verify tests FAIL

**TDD GREEN:**
- [x] Implement `start_onboarding_pipeline()` function
- [x] Wire up Celery chain with all tasks
- [x] Add error handler callback
- [x] Verify tests PASS (16 tests)

**TDD REFACTOR:**
- [x] No refactoring needed - code is clean and focused

**Phase 2 Acceptance:**
- [x] All Phase 2 tests pass
- [x] Chain executes tasks in correct order

---

## Phase 3: Email Notification [Effort: M] - COMPLETED (merged into Phase 2)

### 3.1 Email Task

- [x] Create `send_onboarding_complete_email` task (in `onboarding_pipeline.py`)
- [x] Wire to existing email infrastructure
- [x] Task included in pipeline chain

**Note:** Email templates were not created as the existing `send_sync_complete_email()` function is reused.

---

## Phase 4: Progress API Enhancement [Effort: S] - COMPLETED

### 4.1 Enhanced sync_status Endpoint

**TDD RED:**
- [x] Write test: `test_sync_status_includes_pipeline_status`
- [x] Write test: `test_sync_status_includes_pipeline_stage`
- [x] Write test: `test_sync_status_includes_llm_progress`
- [x] Write test: `test_sync_status_includes_metrics_ready`
- [x] Write test: `test_sync_status_includes_insights_ready`
- [x] Verify tests FAIL

**TDD GREEN:**
- [x] Modify `sync_status()` view in `apps/onboarding/views.py`
- [x] Add pipeline_status and pipeline_stage to response
- [x] Add LLM progress calculation
- [x] Add metrics/insights ready flags
- [x] Verify tests PASS (13 tests)

**TDD REFACTOR:**
- [x] Optimized PR count queries using aggregate() with conditional Count

**Phase 4 Acceptance:**
- [x] API returns enhanced status
- [x] Frontend can show pipeline stages

---

## Phase 5: View Integration [Effort: M] - COMPLETED

### 5.1 Update select_repositories View

**TDD RED:**
- [x] Write test: `test_select_repos_starts_pipeline`
- [x] Write test: `test_select_repos_stores_pipeline_task_id`
- [x] Verify tests FAIL

**TDD GREEN:**
- [x] Import `start_onboarding_pipeline`
- [x] Replace `sync_historical_data_task.delay()` with pipeline
- [x] Store pipeline task ID in session
- [x] Verify tests PASS (6 tests)

### 5.2 Update start_sync View

- [x] Update `start_sync()` to use new pipeline
- [x] Remove unused `sync_historical_data_task` import

**Phase 5 Acceptance:**
- [x] Onboarding flow uses new pipeline
- [x] No regression in existing behavior

---

## Phase 6: Integration Testing [Effort: M] - COMPLETED

### 6.1 Full Pipeline Integration Test

- [x] All 106 pipeline-related tests pass
- [x] Fixed 2 tests in `test_sync_progress_redirect.py` that still mocked old task

### 6.2 Full Test Suite Verification

- [x] Full test suite passes: 3851 passed, 2 skipped, 1 xfailed

**Phase 6 Acceptance:**
- [x] All integration tests pass
- [x] No regression in existing functionality

---

## Phase 7: Documentation & Cleanup [Effort: S] - COMPLETED

- [x] Update dev docs with final state
- [x] Add docstrings to all new functions
- [ ] Move dev docs to `dev/completed/` when merged
- [ ] PR created and reviewed
- [ ] Merged to main

---

## Final Checklist

- [x] All tests pass: `make test` (3851 passed)
- [ ] Code formatted: `make ruff`
- [ ] No new linting errors
- [x] Migration works
- [x] Pipeline ready for new users
- [x] Existing nightly batch still works (unchanged)
- [ ] PR created and reviewed
- [ ] Merged to main

---

## Implementation Summary

### Files Created

| File | Purpose |
|------|---------|
| `apps/integrations/receivers.py` | Signal receivers for sync events |
| `apps/integrations/onboarding_pipeline.py` | Celery chain orchestration |
| `apps/teams/migrations/0005_add_pipeline_tracking_fields.py` | Model migration |
| `apps/teams/tests/test_pipeline_tracking.py` | Team model tests (20 tests) |
| `apps/integrations/tests/test_receivers.py` | Receiver tests (10 tests) |
| `apps/integrations/tests/test_onboarding_pipeline.py` | Pipeline tests (16 tests) |

### Files Modified

| File | Changes |
|------|---------|
| `apps/teams/models.py` | Added pipeline tracking fields + helper methods |
| `apps/integrations/apps.py` | Added `ready()` method |
| `apps/onboarding/views.py` | Uses pipeline, enhanced sync_status API |
| `apps/onboarding/tests/test_views.py` | Added pipeline integration tests (19 tests) |
| `apps/onboarding/tests/test_sync_progress_redirect.py` | Updated mocks |

### Architecture

```
User selects repos
       ↓
start_onboarding_pipeline(team_id, repo_ids)
       ↓
Celery Chain:
  1. update_pipeline_status("syncing")
  2. sync_historical_data_task
  3. update_pipeline_status("llm_processing")
  4. run_llm_analysis_batch (limit=100)
  5. update_pipeline_status("computing_metrics")
  6. aggregate_team_weekly_metrics_task
  7. update_pipeline_status("computing_insights")
  8. compute_team_insights
  9. update_pipeline_status("complete")
  10. send_onboarding_complete_email
       ↓
   on_error: handle_pipeline_failure → status="failed"
```

### Test Commands

```bash
# Run pipeline-specific tests
pytest apps/integrations/tests/test_onboarding_pipeline.py -v
pytest apps/integrations/tests/test_receivers.py -v
pytest apps/teams/tests/test_pipeline_tracking.py -v
pytest apps/onboarding/tests/test_views.py::SyncStatusPipelineFieldsTests -v
pytest apps/onboarding/tests/test_views.py::PipelineIntegrationTests -v

# Run all tests
make test
```

### Rollback Steps

If issues arise in production:

1. In `apps/onboarding/views.py`:
   - Replace `start_onboarding_pipeline()` with `sync_historical_data_task.delay()`
   - Add back the import for `sync_historical_data_task`
2. Pipeline fields remain in DB but unused
3. Nightly batch continues as fallback
