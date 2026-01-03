# Sync Logging Optimization - Task Checklist

## Phase 1: Create Sync Logger Module (TDD)

### RED Phase
- [x] **1.1.1** Write test: `test_sync_context_injects_team_id`
- [x] **1.1.2** Write test: `test_sync_context_injects_repo_id`
- [x] **1.1.3** Write test: `test_sync_context_injects_task_id`
- [x] **1.1.4** Write test: `test_timed_operation_logs_duration_ms`
- [x] **1.1.5** Write test: `test_timed_operation_logs_extra_fields`
- [x] **1.1.6** Write test: `test_sync_logger_outputs_json_format`
- [x] **1.1.7** Verify all tests fail

### GREEN Phase
- [x] **1.2.1** Create `apps/utils/sync_logger.py`
- [x] **1.2.2** Implement `SyncContext` class with contextvars
- [x] **1.2.3** Implement `sync_context()` context manager
- [x] **1.2.4** Implement `timed_operation()` context manager
- [x] **1.2.5** Implement `SyncLoggerAdapter` for JSON output
- [x] **1.2.6** Verify all tests pass

### REFACTOR Phase
- [x] **1.3.1** Review code for duplication
- [x] **1.3.2** Ensure docstrings are complete
- [x] **1.3.3** Run full test suite

---

## Phase 2: Instrument Onboarding Pipeline (TDD)

### RED Phase
- [x] **2.1.1** Write test: `test_pipeline_logs_started_event`
- [x] **2.1.2** Write test: `test_pipeline_logs_phase_changed_event`
- [x] **2.1.3** Write test: `test_pipeline_logs_completed_event`
- [x] **2.1.4** Write test: `test_pipeline_logs_failed_event`
- [x] **2.1.5** Verify all tests fail

### GREEN Phase
- [x] **2.2.1** Import sync_logger in `apps/integrations/onboarding_pipeline.py`
- [x] **2.2.2** Add `sync.pipeline.started` logging
- [x] **2.2.3** Add `sync.pipeline.phase_changed` logging
- [x] **2.2.4** Add `sync.pipeline.completed` logging
- [x] **2.2.5** Add `sync.pipeline.failed` logging
- [x] **2.2.6** Verify all tests pass

### REFACTOR Phase
- [x] **2.3.1** Review logging consistency
- [x] **2.3.2** Run full test suite

---

## Phase 3: Instrument Sync Tasks (TDD)

### RED Phase
- [x] **3.1.1** Write test: `test_repo_sync_logs_started_event`
- [x] **3.1.2** Write test: `test_repo_sync_logs_progress_event`
- [x] **3.1.3** Write test: `test_repo_sync_logs_completed_event`
- [x] **3.1.4** Write test: `test_repo_sync_logs_failed_event`
- [x] **3.1.5** Write test: `test_task_retry_logs_event`
- [x] **3.1.6** Verify all tests fail

### GREEN Phase
- [x] **3.2.1** Import sync_logger in `apps/integrations/tasks.py`
- [x] **3.2.2** Add `sync.repo.started` logging to sync tasks
- [x] **3.2.3** Add `sync.repo.progress` logging (every 10 PRs)
- [x] **3.2.4** Add `sync.repo.completed` logging
- [x] **3.2.5** Add `sync.repo.failed` logging
- [x] **3.2.6** Add `sync.task.retry` logging
- [x] **3.2.7** Verify all tests pass

### REFACTOR Phase
- [x] **3.3.1** Ensure consistent field naming
- [x] **3.3.2** Run full test suite

---

## Phase 4: Instrument GraphQL Sync (TDD)

### RED Phase
- [x] **4.1.1** Write test: `test_graphql_query_logs_timing`
- [x] **4.1.2** Write test: `test_graphql_query_logs_points_cost`
- [x] **4.1.3** Write test: `test_rate_limit_check_logs_status`
- [x] **4.1.4** Write test: `test_rate_limit_wait_logs_duration`
- [x] **4.1.5** Write test: `test_pr_processed_logs_details`
- [x] **4.1.6** Verify all tests fail

### GREEN Phase
- [x] **4.2.1** Import sync_logger in `apps/integrations/services/github_graphql.py`
- [x] **4.2.2** Add `sync.api.graphql` logging with timing
- [x] **4.2.3** Import sync_logger in `apps/integrations/services/github_graphql_sync.py`
- [x] **4.2.4** Add `sync.api.rate_limit` logging
- [x] **4.2.5** Add `sync.api.rate_wait` logging
- [x] **4.2.6** Add `sync.pr.processed` logging
- [x] **4.2.7** Add `sync.db.write` logging for batch operations
- [x] **4.2.8** Verify all tests pass

### REFACTOR Phase
- [x] **4.3.1** Review timing measurement consistency
- [x] **4.3.2** Ensure no performance impact from logging
- [x] **4.3.3** Run full test suite

---

## Phase 5: Integration Testing & QA

### Integration Tests
- [x] **5.1.1** Write integration test: full sync generates expected log events
- [x] **5.1.2** Write integration test: log output parses as valid JSON
- [x] **5.1.3** Verify tests pass (29 sync logging tests pass)

### QA Verification
- [x] **5.2.1** Run full unit test suite: 1341 integrations tests pass
- [x] **5.2.2** Run E2E smoke tests: 66 tests pass
- [ ] **5.2.3** Manual QA: Verify alpha-qa-backlog fixes still work
- [ ] **5.2.4** Test with real GitHub org sync
- [ ] **5.2.5** Review log output format and completeness

### Final Steps
- [ ] **5.3.1** Update dev-docs with completion status
- [ ] **5.3.2** Commit and push

---

## Progress Summary

| Phase | Total | Completed | Remaining |
|-------|-------|-----------|-----------|
| Phase 1 (Logger Module) | 16 | 16 | 0 |
| Phase 2 (Pipeline) | 12 | 12 | 0 |
| Phase 3 (Tasks) | 15 | 15 | 0 |
| Phase 4 (GraphQL) | 18 | 18 | 0 |
| Phase 5 (QA) | 10 | 6 | 4 |
| **Total** | **71** | **67** | **4** |

## Implementation Complete

**Files Created:**
- `apps/utils/sync_logger.py` - Structured logging helper with context managers
- `apps/utils/tests/test_sync_logger.py` - Unit tests (10 tests)
- `apps/integrations/tests/test_sync_logging.py` - Integration tests (19 tests)

**Files Modified:**
- `apps/integrations/onboarding_pipeline.py` - Pipeline event logging
- `apps/integrations/tasks.py` - Task/repo event logging
- `apps/integrations/services/github_graphql.py` - API call logging
- `apps/integrations/services/github_graphql_sync.py` - Sync/PR logging

**Log Events Implemented:**
| Event | Level | Purpose |
|-------|-------|---------|
| `sync.pipeline.started` | INFO | Pipeline start |
| `sync.pipeline.phase_changed` | INFO | Phase transition |
| `sync.pipeline.completed` | INFO | Pipeline success |
| `sync.pipeline.failed` | ERROR | Pipeline failure |
| `sync.repo.started` | INFO | Repo sync start |
| `sync.repo.progress` | INFO | Progress update |
| `sync.repo.completed` | INFO | Repo sync end |
| `sync.repo.failed` | ERROR | Repo sync fail |
| `sync.api.graphql` | INFO | GraphQL call |
| `sync.api.rate_limit` | INFO | Rate limit check |
| `sync.api.rate_wait` | INFO | Rate limit wait |
| `sync.pr.processed` | INFO | Per-PR detail |
| `sync.db.write` | INFO | DB batch write |
| `sync.task.retry` | WARNING | Task retry |

---

*Last Updated: 2026-01-03*
