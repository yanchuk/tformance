# Fix Slow Incremental Tests - Tasks

**Last Updated: 2025-12-22**
**Status: In Progress**

## Phase 1: Fix Non-Review Tests

### 1.1 Fix test_sync_repository_incremental_creates_new_pull_requests
- [ ] Add comprehensive mock decorators
- [ ] Add mock return values in test body
- [ ] Verify test passes

**Effort**: S | **Priority**: P0

### 1.2 Fix test_sync_repository_incremental_updates_existing_pull_requests
- [ ] Add comprehensive mock decorators
- [ ] Add mock return values in test body
- [ ] Verify test passes

**Effort**: S | **Priority**: P0

### 1.3 Fix test_sync_repository_incremental_returns_correct_summary_dict
- [ ] Add comprehensive mock decorators
- [ ] Add mock return values in test body
- [ ] Verify test passes

**Effort**: S | **Priority**: P0

### 1.4 Fix test_sync_repository_incremental_handles_individual_pr_errors_gracefully
- [ ] Add comprehensive mock decorators
- [ ] Add mock return values in test body
- [ ] Verify test passes

**Effort**: S | **Priority**: P0

---

## Phase 2: Fix Review Tests

### 2.1 Fix test_sync_repository_incremental_syncs_reviews_for_each_updated_pr
- [ ] Add mocks for sync subfunctions (NOT _sync_pr_reviews)
- [ ] Keep existing get_pull_request_reviews mock
- [ ] Add mock return values
- [ ] Verify test passes

**Effort**: S | **Priority**: P0

### 2.2 Fix test_sync_repository_incremental_creates_review_records
- [ ] Add mocks for sync subfunctions (NOT _sync_pr_reviews)
- [ ] Keep existing get_pull_request_reviews mock
- [ ] Add mock return values
- [ ] Verify test passes

**Effort**: S | **Priority**: P0

---

## Phase 3: Verify and Commit

### 3.1 Run timing verification
- [ ] Run `pytest apps/integrations/tests/github_sync/test_repository_sync.py --durations=20`
- [ ] Confirm all 6 tests are <0.5s
- [ ] Document before/after times

**Effort**: S | **Priority**: P0

### 3.2 Run full test suite
- [ ] Run `make test`
- [ ] Confirm all 2035 tests pass

**Effort**: S | **Priority**: P0

### 3.3 Commit changes
- [ ] Stage changes
- [ ] Commit with descriptive message
- [ ] Push to remote

**Effort**: S | **Priority**: P0

---

## Progress Summary

| Phase | Status | Tasks Done | Tasks Total |
|-------|--------|------------|-------------|
| Phase 1: Non-Review Tests | In Progress | 0 | 4 |
| Phase 2: Review Tests | Pending | 0 | 2 |
| Phase 3: Verify & Commit | Pending | 0 | 3 |
| **Total** | **In Progress** | **0** | **9** |

---

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Slowest incremental test | 3.30s | <0.5s |
| File total time | ~19s | <5s |
| Parallel test time | ~30s | ~25s |
