# Code Simplification - Task Checklist

**Last Updated:** 2026-01-11

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Completed
- [!] Blocked
- [-] Skipped

---

## Phase 1: Quick Wins (P0) - github_graphql.py
**Estimated:** 4-6 hours | **Risk:** Low

### 1.1 Extract Retry Logic Helper
**Effort:** M | **Priority:** P0 | **Status:** COMPLETED 2026-01-11

- [x] Read and understand current retry pattern in `fetch_prs_bulk()` (lines 608-668)
- [x] Identify all 5 methods with duplicated retry logic
- [x] Write tests for `_execute_with_retry()` helper (existing tests cover behavior)
- [x] Implement `_execute_with_retry()` method
- [x] Run tests: `make test ARGS='apps.integrations.tests.test_github_graphql'`
- [x] Verify all tests pass (60/60 passed)

**Acceptance Criteria:**
- [x] New `_execute_with_retry()` method handles retry, rate limit, and error logic
- [x] All existing tests pass without modification
- [x] No changes to public API

### 1.2 Add Named Constants
**Effort:** S | **Priority:** P0 | **Status:** COMPLETED 2026-01-11

- [x] Add constants at module level:
  - [x] `RATE_LIMIT_THRESHOLD = 100` (already existed)
  - [x] `DEFAULT_TIMEOUT_SECONDS = 90`
  - [x] `DEFAULT_MAX_RETRIES = 3`
  - [x] `DEFAULT_MAX_WAIT_SECONDS = 3600`
  - [x] `GRAPHQL_RATE_LIMIT_POINTS = 5000`
- [x] Update `__init__` to use constants as defaults
- [x] Update all method signatures to use constants
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- [x] No hardcoded magic numbers in method bodies
- [x] All tests pass

### 1.3 Move Import to Module Level
**Effort:** S | **Priority:** P0 | **Status:** COMPLETED 2026-01-11

- [x] Remove `import asyncio` from inside methods (5 occurrences)
- [x] Add `import asyncio` at top of file
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- [x] Single `import asyncio` at module level
- [x] All tests pass

### 1.4 Simplify Fetch Methods
**Effort:** M | **Priority:** P0 | **Status:** COMPLETED 2026-01-11

- [x] Refactor `fetch_prs_bulk()` to use `_execute_with_retry()`
- [x] Refactor `fetch_single_pr()` to use `_execute_with_retry()`
- [x] Refactor `fetch_org_members()` to use `_execute_with_retry()`
- [x] Refactor `fetch_prs_updated_since()` to use `_execute_with_retry()`
- [x] Refactor `search_prs_by_date_range()` to use `_execute_with_retry()`
- [x] Run full test suite (133/133 graphql tests passed)

**Acceptance Criteria:**
- [x] Each method reduced significantly (from 50-90 lines to 15-30 lines)
- [x] All tests pass
- [x] Logging output preserved

### 1.5 Add Unit Tests for Helper
**Effort:** M | **Priority:** P0 | **Status:** COMPLETED 2026-01-11

- [x] Added dedicated `TestExecuteWithRetry` test class with 8 comprehensive tests
- [x] Test: successful execution returns result
- [x] Test: rate limit error passes through immediately (no retry)
- [x] Test: timeout with retry then success
- [x] Test: timeout exhaustion after max retries
- [x] Test: generic exception converts to GitHubGraphQLError (no retry)
- [x] Test: exponential backoff timing (1s, 2s, 4s)
- [x] Test: respects max_retries parameter
- [x] Test: preserves original exception as __cause__
- [x] All 68 GraphQL tests pass (60 original + 8 new TDD tests)

**Acceptance Criteria:**
- [x] `_execute_with_retry()` has dedicated unit tests
- [x] All code paths tested (success, timeout, rate limit, generic error)
- [x] Exponential backoff behavior verified

---

## Phase 2: Structural Improvements (P1) - COMPLETED 2026-01-11
**Estimated:** 8-12 hours | **Risk:** Medium

### 2.1 Create PRContext TypedDict
**Effort:** M | **Priority:** P1 | **Status:** COMPLETED 2026-01-11

- [x] Read current `apps/metrics/types.py`
- [x] Add `PRContext` TypedDict with flat fields (matching 26 parameters)
- [x] Run pyright to verify types: `.venv/bin/pyright apps/metrics/types.py`

**Note:** Used flat fields instead of nested TypedDicts as recommended by plan reviewer.

**Acceptance Criteria:**
- [x] TypedDict has comprehensive docstring
- [x] Pyright passes with no errors

### 2.2 Add get_user_prompt_v2() and build_pr_context()
**Effort:** M | **Priority:** P1 | **Status:** COMPLETED 2026-01-11

- [x] Read current `get_user_prompt()` implementation
- [x] Implement `get_user_prompt_v2()` accepting PRContext
- [x] Implement `build_pr_context(pr)` to bridge PullRequest model to PRContext
- [x] Run tests - all 132 llm_prompts tests pass

**Acceptance Criteria:**
- [x] New function produces identical output for equivalent inputs
- [x] Function signature takes single `PRContext` parameter
- [x] `build_pr_context(pr)` helper bridges model to context
- [x] All tests pass

### 2.3 Deprecate Old get_user_prompt()
**Effort:** S | **Priority:** P1 | **Status:** DEFERRED

Deferred per plan reviewer recommendation - add deprecation warning after all consumers updated.

### 2.4 Create pr_filters.py Module
**Effort:** S | **Priority:** P1 | **Status:** COMPLETED 2026-01-11

- [x] Create new file `apps/metrics/services/pr_filters.py`
- [x] Add module docstring with usage examples
- [x] Create test file `apps/metrics/tests/services/test_pr_filters.py`

**Acceptance Criteria:**
- [x] New module created with proper structure
- [x] Test file created with 18 TDD tests

### 2.5 Extract Date Range Filter
**Effort:** M | **Priority:** P1 | **Status:** COMPLETED 2026-01-11

- [x] Write tests for `apply_date_range_filter()` - 5 TDD tests
- [x] Implement `apply_date_range_filter()` in pr_filters.py
- [x] Implement `_filter_by_date_field()` helper
- [x] Implement `_filter_all_states_date_range()` helper
- [x] Run tests - all pass

**Acceptance Criteria:**
- [x] Function handles all 3 date range scenarios
- [x] Tests cover open, merged, closed, and all states
- [x] All tests pass

### 2.6 Extract Issue Type Filter
**Effort:** M | **Priority:** P1 | **Status:** COMPLETED 2026-01-11

- [x] Write tests for `apply_issue_type_filter()` - 10 TDD tests
- [x] Implement `apply_issue_type_filter()` with handler dict pattern
- [x] Implement `_calculate_long_cycle_threshold()` shared helper
- [x] Implement all 5 filter handlers (revert, hotfix, long_cycle, large_pr, missing_jira)
- [x] Run tests - all 18 pass

**Acceptance Criteria:**
- [x] Each issue type correctly filtered
- [x] Priority exclusions work correctly (threshold passed to handlers)
- [x] All tests pass

### 2.7 Update pr_list_service.py
**Effort:** M | **Priority:** P1 | **Status:** COMPLETED 2026-01-11

- [x] Import new filter functions from pr_filters.py
- [x] Replace inline date range logic (~35 lines) with `apply_date_range_filter()`
- [x] Replace inline issue type logic (~45 lines) with `apply_issue_type_filter()`
- [x] Run date range tests - all pass

**Acceptance Criteria:**
- [x] `get_prs_queryset()` reduced by ~80 lines
- [x] Existing date range/issue type tests pass
- [x] No functional changes

---

## Phase 3: Major Refactoring (P2)
**Estimated:** 12-16 hours | **Risk:** High

### 3.1 Split github_sync.py into Module
**Effort:** XL | **Priority:** P2 | **Depends on:** Phase 2 complete

- [ ] Create directory `apps/integrations/services/github_sync/`
- [ ] Create `__init__.py` with re-exports
- [ ] Extract sync orchestration to `sync.py`
- [ ] Extract processors to `processors.py`
- [ ] Extract rate limit handling to `rate_limit.py`
- [ ] Extract metrics calculation to `metrics.py`
- [ ] Update imports in dependent files
- [ ] Update original `github_sync.py` to import from module
- [ ] Run full test suite

**Acceptance Criteria:**
- Original file preserved as facade
- Each module under 300 lines
- All tests pass
- No import errors in dependent code

### 3.2 Extract InsightDataGatherer
**Effort:** L | **Priority:** P2 | **Depends on:** Phase 2 complete

- [ ] Create `apps/metrics/services/insight_data.py`
- [ ] Define `InsightData` dataclass
- [ ] Implement `InsightDataGatherer` class
- [ ] Write tests for gatherer
- [ ] Update `insight_llm.py` to use gatherer
- [ ] Run full test suite

**Acceptance Criteria:**
- Data gathering logic isolated
- `insight_llm.py` reduced to LLM-specific code
- All tests pass

---

## Verification Checklist

### After Each Task
- [ ] All tests pass: `make test`
- [ ] No type errors: `.venv/bin/pyright <changed_files>`
- [ ] Team isolation check: `make lint-team-isolation`

### After Each Phase
- [ ] Full test suite passes: `make test`
- [ ] Coverage maintained: `make test-coverage`
- [ ] Manual smoke test of affected features
- [ ] Update this task file with completion dates

---

## Notes & Blockers

<!-- Add any notes, blockers, or discoveries here -->

### Phase 1 Notes
- **2026-01-11:** Completed all Phase 1 tasks with full TDD coverage
- File reduced from 1,066 lines to 1,000 lines (net -66 lines after adding helper)
- 5 methods simplified: each now 15-30 lines instead of 50-90 lines
- Added 8 dedicated TDD unit tests for `_execute_with_retry()` helper
- All 68 github_graphql tests pass (60 original + 8 new TDD tests)
- All 133 graphql-related tests pass
- The `fetch_prs_bulk` method preserved extra sync logger timing that other methods don't have
- TDD tests cover: success, rate limit passthrough, timeout retry, timeout exhaustion, generic errors, exponential backoff, max_retries parameter, exception chaining

### Phase 2 Notes
- **Ready to start:** Phase 1 complete, can proceed with TypedDict and filter extraction
- **Recommended order:** 2.4 (create pr_filters.py) → 2.5/2.6 (extract filters) → 2.1 (PRContext TypedDict) → 2.2/2.3 (get_user_prompt_v2)
- **Key files to read first:** `apps/metrics/types.py`, `apps/metrics/services/pr_list_service.py`, `apps/metrics/services/llm_prompts.py`

### Phase 3 Notes
-

---

## Completion Log

| Phase | Task | Completed | Notes |
|-------|------|-----------|-------|
| 1.1 | Extract retry helper | 2026-01-11 | Added `_execute_with_retry()` (~55 lines) |
| 1.2 | Add constants | 2026-01-11 | 4 new constants at module level |
| 1.3 | Move imports | 2026-01-11 | `import asyncio` moved to top |
| 1.4 | Simplify methods | 2026-01-11 | 5 methods refactored |
| 1.5 | Add tests | 2026-01-11 | Added 8 TDD tests in TestExecuteWithRetry class |
| 2.1 | PRContext TypedDict | 2026-01-11 | Flat fields matching 26 parameters |
| 2.2 | get_user_prompt_v2 | 2026-01-11 | + build_pr_context() helper |
| 2.3 | Deprecate old function | DEFERRED | Add after all consumers updated |
| 2.4 | Create pr_filters.py | 2026-01-11 | New module + 18 TDD tests |
| 2.5 | Date range filter | 2026-01-11 | 5 TDD tests, 3 helper functions |
| 2.6 | Issue type filter | 2026-01-11 | 10 TDD tests, 6 handler functions |
| 2.7 | Update pr_list_service | 2026-01-11 | Reduced ~80 lines |
| 3.1 | Split github_sync | | |
| 3.2 | Extract gatherer | | |
