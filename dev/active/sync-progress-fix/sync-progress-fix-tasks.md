# Tasks: Sync Progress Fix

**Last Updated:** 2026-01-03

## Phase 1: RED - Write Failing Tests - COMPLETE

**Effort: Small | Priority: High**

- [x] Create test class `TestGetPRCountInDateRange` in `test_github_graphql.py`
  - [x] Test: Returns issueCount from search API response
  - [x] Test: Builds correct search query with since/until dates
  - [x] Test: Handles no since date (open-ended start)
  - [x] Test: Handles no until date (open-ended end)
  - [x] Test: Returns 0 when no results

- [x] Create test class `TestSyncProgressTracking` in `test_github_graphql_sync.py`
  - [x] Test: Progress uses date-filtered count from get_pr_count_in_date_range

- [x] Run tests to confirm they FAIL
  ```bash
  .venv/bin/pytest apps/integrations/tests/test_github_graphql.py::TestGetPRCountInDateRange -v
  .venv/bin/pytest apps/integrations/tests/test_github_graphql_sync.py::TestSyncProgressTracking -v
  ```

## Phase 2: GREEN - Implement - COMPLETE

**Effort: Medium | Priority: High**

- [x] Add `SEARCH_PR_COUNT_QUERY` to `apps/integrations/services/github_graphql.py`

- [x] Add `get_pr_count_in_date_range()` method to `GitHubGraphQLClient`
  - [x] Build search query with repo, is:pr, created date filters
  - [x] Execute query and return issueCount
  - [x] Handle errors gracefully (fallback to totalCount)

- [x] Update `sync_repository_history_graphql()` in `github_graphql_sync.py`
  - [x] Calculate cutoff_date and skip_before_date
  - [x] Call `get_pr_count_in_date_range()` before pagination loop
  - [x] Use returned count for `_update_sync_progress()`

- [x] Run tests to confirm they PASS (6 passed)

## Phase 3: REFACTOR - COMPLETE

**Effort: Small | Priority: Medium**

- [x] Add proper type hints (`datetime | None`)
- [x] Create `create_mock_graphql_client()` helper for tests
- [x] Fix 63 existing tests that needed the new async method mocked
- [x] Run full regression tests (116 passed)

## Phase 4: Manual Verification

**Effort: Small | Priority: High**

- [ ] Clear team 151 progress data
  ```sql
  UPDATE integrations_trackedrepository
  SET sync_progress = 0, sync_prs_completed = 0, sync_prs_total = 0
  WHERE team_id = 151;
  ```

- [ ] Restart Celery worker
  ```bash
  pkill -f 'celery.*tformance'
  make celery
  ```

- [ ] Re-run sync for team 151
  ```python
  from apps.integrations.models import TrackedRepository
  from apps.integrations.services.onboarding_sync import OnboardingSyncService

  repo = TrackedRepository.objects.get(team_id=151)
  service = OnboardingSyncService(repo.team, repo.integration.credential.access_token)
  result = service.sync_repository(repo, days_back=30)
  ```

- [ ] Verify correct progress
  ```sql
  SELECT full_name, sync_progress, sync_prs_completed, sync_prs_total
  FROM integrations_trackedrepository
  WHERE team_id = 151;
  -- Expected: sync_prs_total = 14, sync_progress = 100
  ```

---

## Quick Reference

### Test Commands

```bash
# Run specific test classes
.venv/bin/pytest apps/integrations/tests/test_github_graphql.py::TestGetPRCountInDateRange -v
.venv/bin/pytest apps/integrations/tests/test_github_graphql_sync.py::TestSyncProgressTracking -v

# Run all integration tests
.venv/bin/pytest apps/integrations/tests/ -v --tb=short

# Run full test suite
make test
```

### Files to Modify

| File | What to Add |
|------|-------------|
| `apps/integrations/services/github_graphql.py` | `SEARCH_PR_COUNT_QUERY`, `get_pr_count_in_date_range()` |
| `apps/integrations/services/github_graphql_sync.py` | Use new function, remove totalCount usage |
| `apps/integrations/tests/test_github_graphql.py` | `TestGetPRCountInDateRange` class |
| `apps/integrations/tests/test_github_graphql_sync.py` | `TestSyncProgressTracking` class |

### Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| `sync_prs_total` | 2410 | 14 |
| `sync_progress` | 2% | 100% |
| Time estimate | "~7 min remaining" | Complete |
