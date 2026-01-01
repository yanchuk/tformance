# Two-Phase Onboarding - TDD Task Checklist

**Last Updated**: 2026-01-01
**Status**: Planning
**Branch**: `feature/two-phase-onboarding`

## Phase 1: Model Changes ✅

### 1.1 Team Model Status Choices
- [x] **RED**: Write test for new `phase1_complete` status
- [x] **RED**: Write test for `background_syncing` status
- [x] **RED**: Write test for `background_llm` status
- [x] **GREEN**: Add new choices to `PIPELINE_STATUS_CHOICES`
- [x] **REFACTOR**: Update `pipeline_in_progress` property

### 1.2 Team Model Progress Fields
- [x] **RED**: Write test for `background_sync_progress` field
- [x] **RED**: Write test for `background_llm_progress` field
- [x] **GREEN**: Add fields to Team model
- [x] **GREEN**: Create and apply migration (0006_add_two_phase_onboarding_fields)
- [x] **REFACTOR**: Add `update_background_progress()` method

## Phase 2: Sync Task Modifications ✅

### 2.1 Days-Back Parameter
- [x] **RED**: Write test for `days_back=30` limiting sync
- [x] **RED**: Write test for `skip_recent=30` excluding recent days
- [x] **GREEN**: Add parameters to `sync_historical_data_task`
- [x] **GREEN**: Implement date filtering in GraphQL query
- [x] **REFACTOR**: Extract date range logic to helper

### 2.2 Progress Tracking
- [ ] **RED**: Write test for progress updates during sync
- [ ] **GREEN**: Add progress callback to sync task
- [ ] **REFACTOR**: DRY up progress update code

## Phase 3: LLM Analysis Modifications ✅

### 3.1 Remove Limit
- [x] **RED**: Write test for `limit=None` processing all PRs
- [x] **GREEN**: Handle `limit=None` case in `run_llm_analysis_batch`
- [x] **REFACTOR**: Clarify limit behavior in docstring

### 3.2 Progress Tracking
- [ ] **RED**: Write test for LLM progress updates
- [ ] **GREEN**: Add progress updates during batch processing
- [ ] **REFACTOR**: Batch progress updates (every 10 PRs)

## Phase 4: Pipeline Orchestration ✅

### 4.1 Phase 1 Pipeline
- [x] **RED**: Write test for Phase 1 completing in order
- [x] **RED**: Write test for Phase 1 using 30-day sync
- [x] **RED**: Write test for Phase 1 processing ALL synced PRs
- [x] **GREEN**: Implement `start_phase1_pipeline()` function
- [x] **GREEN**: Update `start_onboarding_pipeline()` to call Phase 1
- [x] **REFACTOR**: Extract common status update logic

### 4.2 Phase 2 Dispatch
- [x] **RED**: Write test for Phase 2 dispatching after Phase 1
- [x] **RED**: Write test for Phase 2 using 31-90 day range
- [x] **GREEN**: Implement `dispatch_phase2_pipeline()` task
- [x] **GREEN**: Implement `run_phase2_pipeline()` task
- [ ] **REFACTOR**: Add idempotency check (deferred)

### 4.3 Error Handling
- [ ] **RED**: Write test for Phase 1 failure blocking dashboard
- [ ] **RED**: Write test for Phase 2 failure not affecting dashboard
- [ ] **GREEN**: Implement separate error handlers for each phase
- [ ] **REFACTOR**: Log clear error messages

## Phase 5: UI Components ✅

### 5.1 Progress Banner
- [x] **RED**: Write test for banner showing during background_syncing
- [x] **RED**: Write test for banner showing during background_llm
- [x] **RED**: Write test for banner hidden when complete
- [x] **GREEN**: Create progress banner partial template
- [x] **GREEN**: Include banner in dashboard template
- [x] **REFACTOR**: Add HTMX polling for live progress

### 5.2 Dashboard Access
- [ ] **RED**: Write test for dashboard accessible after phase1_complete
- [ ] **RED**: Write test for dashboard blocked during phase1
- [ ] **GREEN**: Update dashboard view permission check
- [ ] **REFACTOR**: Clear loading state handling

## Phase 6: Integration Tests

### 6.1 Full Flow Tests
- [ ] Write integration test for complete two-phase flow
- [ ] Write integration test for Phase 2 retry after failure
- [ ] Write integration test for concurrent pipeline prevention

### 6.2 E2E Tests
- [ ] Write E2E test for dashboard access timing
- [ ] Write E2E test for progress banner display
- [ ] Write E2E test for banner dismissal

## Phase 7: Feature Flag & Rollout

### 7.1 Feature Flag
- [ ] Create `two_phase_onboarding` waffle flag
- [ ] Add flag check in `start_onboarding_pipeline`
- [ ] Document rollout plan

### 7.2 Monitoring
- [ ] Add metrics for Phase 1 completion time
- [ ] Add metrics for Phase 2 completion time
- [ ] Add alert for Phase 2 failure rate

---

## Quick Start Commands

```bash
# Run tests for this feature
make test ARGS='apps.integrations.tests.test_onboarding_pipeline'
make test ARGS='apps.metrics.tests.test_tasks'

# Check migrations
make migrations

# Run specific TDD cycle
pytest apps/integrations/tests/test_two_phase_onboarding.py -v

# E2E tests
make e2e ARGS='tests/e2e/onboarding-pipeline.spec.ts'
```
