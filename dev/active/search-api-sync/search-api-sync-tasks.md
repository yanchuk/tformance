# Search API Sync - TDD Task Checklist

**Last Updated:** 2026-01-04
**Methodology:** Test-Driven Development (Red-Green-Refactor)
**Status:** ✅ Core Implementation Complete

---

## Phase 1: Add Search-based PR Fetching ✅

### 1.1 Add Search Query to GraphQL Client ✅

**File:** `apps/integrations/services/github_graphql.py`

#### RED: Write Failing Tests ✅
- [x] Test: `test_search_prs_by_date_query_builds_correct_string`
- [x] Test: `test_search_prs_by_date_range_query_builds_correct_string`
- [x] Test: `test_search_prs_returns_issue_count`
- [x] Test: `test_search_prs_returns_pr_nodes`
- [x] Test: `test_search_prs_handles_pagination`
- [x] Additional tests: rate limit error, empty results, retries on timeout

#### GREEN: Implement ✅
- [x] Add `SEARCH_PRS_BY_DATE_QUERY` GraphQL query constant
- [x] Add `async search_prs_by_date_range(owner, repo, since_date, until_date=None)` method
- [x] Return structure: `{"issue_count": int, "prs": list[dict], "has_next_page": bool, "end_cursor": str}`

#### REFACTOR ✅
- [x] Add type hints
- [x] Add docstrings
- [x] Linting passes

---

## Phase 2: Update Sync Service ✅

### 2.1 Add Search-based Sync Function ✅

**File:** `apps/integrations/services/github_graphql_sync.py`

#### RED: Write Failing Tests ✅
- [x] Test: `test_sync_by_search_function_exists`
- [x] Test: `test_sync_by_search_sets_prs_total_from_issue_count`
- [x] Test: `test_sync_by_search_creates_pull_requests`
- [x] Test: `test_sync_by_search_increments_prs_processed`
- [x] Test: `test_sync_by_search_phase1_uses_since_only`
- [x] Test: `test_sync_by_search_phase2_uses_date_range`
- [x] Test: `test_sync_by_search_paginates_through_all_pages`
- [x] Test: `test_sync_by_search_returns_result_dict`

#### GREEN: Implement ✅
- [x] Add `async sync_repository_history_by_search(tracked_repo, days_back, skip_recent=0)`
- [x] Calculate date range from parameters
- [x] Call `client.search_prs_by_date_range()`
- [x] Set `tracked_repo.sync_prs_total = response['issue_count']`
- [x] Process each PR using `_process_pr_from_search_async()`
- [x] No Python date filtering needed (Search API handles dates)

#### REFACTOR ✅
- [x] Use `sync_to_async` for DB operations (not asyncio.run!)
- [x] Use F() expression for atomic `sync_prs_completed` increment
- [x] Linting passes

---

### 2.2 Update Task Module to Use New Sync ✅

**File:** `apps/integrations/_task_modules/github_sync.py`

#### GREEN: Implement ✅
- [x] Update `_sync_with_graphql_or_rest()` to use `sync_repository_history_by_search()`
- [x] Add feature flag: `GITHUB_API_CONFIG.GRAPHQL_OPERATIONS.use_search_api`
- [x] Replace `asyncio.run()` with `async_to_sync()` (critical fix!)
- [x] Support `skip_recent` parameter for Phase 2

---

## Phase 3: Update Onboarding Pipeline ✅

### 3.1 Update Pipeline Service ✅

**File:** `apps/integrations/services/onboarding_sync.py`

#### GREEN: Implement ✅
- [x] Import `sync_repository_history_by_search`
- [x] Check `use_search_api` config flag
- [x] Use Search API when enabled for accurate progress

---

## Phase 4: Integration Testing

### 4.1 End-to-End Tests (Optional - covered by unit tests)

**File:** `apps/integrations/tests/test_search_api_sync_integration.py`

- [ ] Test: `test_full_onboarding_sync_with_search_api`
- [ ] Test: `test_two_phase_sync_no_duplicates`

### 4.2 Manual Verification Checklist

- [x] Enable feature flag: `GITHUB_API_CONFIG.GRAPHQL_OPERATIONS.use_search_api = True` (now default!)
- [ ] Start Celery worker with `make celery-dev`
- [ ] Create new team, start onboarding
- [ ] Watch progress bar - should show accurate count
- [ ] Verify final PR count matches total displayed
- [ ] Check Flower for task progression

---

## Cleanup Tasks

### After All Tests Pass

- [ ] Update CLAUDE.md with any new patterns (if needed)
- [ ] Update prd/ONBOARDING.md if flow changed
- [x] Run `make ruff` for formatting/linting
- [x] Run core tests to verify no regressions

---

## Configuration

### Search API (Enabled by Default)

The Search API is now enabled by default in `tformance/settings.py`:

```python
GITHUB_API_CONFIG = {
    "USE_GRAPHQL": True,
    "GRAPHQL_OPERATIONS": {
        "initial_sync": True,
        "incremental_sync": True,
        "pr_complete_data": True,
        "member_sync": True,
        "use_search_api": True,  # ✅ Enabled by default for accurate progress
    },
    "FALLBACK_TO_REST": True,
}
```

To disable (fallback to old pullRequests API), set env var:
```bash
GITHUB_USE_SEARCH_API=False
```

---

## Notes

### TDD Reminder

For each task:
1. **RED** - Write test first, see it fail
2. **GREEN** - Write minimum code to pass
3. **REFACTOR** - Clean up while keeping tests green

### Async/Sync Pattern

```python
# CORRECT - use async_to_sync() in Celery tasks
from asgiref.sync import async_to_sync
result = async_to_sync(sync_repository_history_by_search)(tracked_repo, days_back=30)

# WRONG - don't use asyncio.run()
import asyncio
result = asyncio.run(...)  # Breaks @sync_to_async thread context!
```

### Progress Update Pattern

```python
# Use F() expression for atomic updates
from django.db.models import F
TrackedRepository.objects.filter(id=tracked_repo_id).update(
    sync_prs_completed=F("sync_prs_completed") + 1
)
```

---

## Test Results

All core tests pass:
- 60 tests in `test_github_graphql.py` ✅
- 8 tests in `TestSyncRepositoryHistoryBySearch` ✅

---

## Completion Criteria

- [x] Core implementation complete
- [x] Tests pass for new functionality
- [x] Linting passes (`make ruff`)
- [ ] Manual verification with real GitHub data
- [ ] No regressions in existing sync functionality (full test suite)
- [ ] Progress bar shows accurate count during onboarding
