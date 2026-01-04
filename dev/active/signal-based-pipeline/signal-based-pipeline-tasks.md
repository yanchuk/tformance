# Signal-Based Pipeline - Tasks

**Last Updated: 2026-01-04**

## Phase 1: Foundation (TDD RED)

### 1.1 Status Tracking in Team Model
- [ ] **Add `_original_status` tracking to Team.__init__** [S]
  - Store original status on model instantiation
  - Acceptance: `team._original_status` contains status at load time

### 1.2 Write Failing Tests for Signal Dispatch
- [ ] **Test: signal fires on status change** [M]
  - File: `apps/integrations/tests/test_pipeline_signals.py`
  - Test `on_pipeline_status_change` is called when status changes
  - Acceptance: Test fails (signal not implemented yet)

- [ ] **Test: correct task dispatched for each status** [M]
  - Test each status → task mapping
  - Acceptance: Tests fail (state machine not implemented)

- [ ] **Test: no dispatch on non-status saves** [S]
  - Updating other Team fields doesn't trigger dispatch
  - Acceptance: Test fails

- [ ] **Test: no dispatch when status unchanged** [S]
  - Saving with same status doesn't dispatch
  - Acceptance: Test fails

## Phase 2: Signal Handler (TDD GREEN)

### 2.1 Create Pipeline State Machine
- [ ] **Create `apps/integrations/pipeline_signals.py`** [M]
  - Define `PIPELINE_STATE_MACHINE` dict
  - Map status → (task, kwargs_function)
  - Acceptance: Module importable, config complete

### 2.2 Implement Signal Handler
- [ ] **Implement `on_pipeline_status_change` signal** [M]
  - Detect status change via `_original_status`
  - Look up next task in state machine
  - Dispatch with countdown=1
  - Handle errors gracefully
  - Acceptance: All RED tests pass

### 2.3 Register Signal
- [ ] **Import signals in `apps/integrations/apps.py`** [S]
  - Add `import apps.integrations.pipeline_signals` in `ready()`
  - Acceptance: Signal handler active on app startup

### 2.4 Run Tests
- [ ] **All signal dispatch tests pass** [S]
  - Run `pytest apps/integrations/tests/test_pipeline_signals.py`
  - Acceptance: 100% pass

## Phase 3: Task Modifications (TDD GREEN continued)

### 3.1 Modify Phase 1 Tasks
- [ ] **Update `sync_github_members_pipeline_task`** [S]
  - On completion: call `team.update_pipeline_status("syncing")`
  - Acceptance: Task updates status, signal fires

- [ ] **Update `sync_historical_data_task`** [S]
  - On completion: call `team.update_pipeline_status("llm_processing")`
  - Acceptance: Task updates status, signal fires

- [ ] **Update `queue_llm_analysis_batch_task`** [S]
  - On completion: call `team.update_pipeline_status("computing_metrics")`
  - Acceptance: Task updates status, signal fires

- [ ] **Update `aggregate_team_weekly_metrics_task`** [S]
  - On completion: call `team.update_pipeline_status("computing_insights")`
  - Acceptance: Task updates status, signal fires

- [ ] **Update `compute_team_insights`** [M]
  - On completion: dispatch `generate_team_llm_insights` directly
  - Then call `team.update_pipeline_status("phase1_complete")`
  - Acceptance: Both insights generated, status updated

### 3.2 Modify Phase 2 Tasks
- [ ] **Update Phase 2 task completions** [M]
  - `sync_historical_data_task` (phase2): → `background_llm`
  - `queue_llm_analysis_batch_task` (phase2): → re-aggregate then `complete`
  - Acceptance: Phase 2 flows via signals

## Phase 4: Refactor Pipeline Entry Points (TDD REFACTOR)

### 4.1 Simplify `start_phase1_pipeline`
- [ ] **Remove chain, use status update** [M]
  - Just set status to `syncing_members`
  - Signal handles the rest
  - Acceptance: Existing tests still pass

### 4.2 Simplify `dispatch_phase2_pipeline`
- [ ] **Remove chain, just update status** [S]
  - Set status to `background_syncing`
  - Signal handles the rest
  - Acceptance: Phase 2 starts via signal

### 4.3 Phase 1 Complete Auto-Dispatch
- [ ] **Add Phase 2 auto-dispatch on `phase1_complete`** [M]
  - In signal handler, detect `phase1_complete`
  - Dispatch Phase 2 start task
  - Acceptance: Phase 2 starts automatically

### 4.4 Update Recovery System
- [ ] **Simplify `recover_stuck_pipeline`** [S]
  - Just update status to appropriate value
  - Signal handles dispatch
  - Acceptance: Recovery triggers pipeline continuation

## Phase 5: Integration Testing

### 5.1 End-to-End Tests
- [ ] **Test full Phase 1 flow via signals** [L]
  - Start pipeline, verify each status transition
  - Verify each task dispatched
  - Acceptance: Pipeline completes without chains

- [ ] **Test Phase 2 auto-start** [M]
  - Verify Phase 2 starts after Phase 1
  - Acceptance: `phase1_complete` → `background_syncing`

- [ ] **Test worker restart resilience** [M]
  - Simulate stuck state, trigger recovery
  - Acceptance: Pipeline resumes correctly

### 5.2 Existing Test Verification
- [ ] **All existing pipeline tests pass** [S]
  - Run full test suite
  - Acceptance: No regressions

## Phase 6: Cleanup

### 6.1 Remove Dead Code
- [ ] **Remove chain-building code** [S]
  - Clean up unused chain construction
  - Acceptance: Code is simpler

### 6.2 Update Documentation
- [ ] **Update CLAUDE.md if needed** [S]
  - Document signal-based pipeline architecture
  - Acceptance: Documentation accurate

---

## Effort Legend
- **S** = Small (~30 min)
- **M** = Medium (~1-2 hours)
- **L** = Large (~2-4 hours)
- **XL** = Extra Large (4+ hours)

## Progress Tracking

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Foundation (RED) | Not Started | 0/5 |
| Phase 2: Signal Handler (GREEN) | Not Started | 0/4 |
| Phase 3: Task Modifications | Not Started | 0/7 |
| Phase 4: Refactor Pipeline | Not Started | 0/4 |
| Phase 5: Integration Testing | Not Started | 0/4 |
| Phase 6: Cleanup | Not Started | 0/2 |

**Total Tasks: 26**
**Completed: 0**
