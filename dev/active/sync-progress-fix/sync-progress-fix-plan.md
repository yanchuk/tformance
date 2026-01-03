# Plan: Fix Sync Progress Tracking

**Last Updated:** 2026-01-03

## Executive Summary

The onboarding sync progress bar shows incorrect percentages (e.g., 2% when actually complete) because it uses GitHub GraphQL's `totalCount` which returns ALL PRs in a repository, not just PRs within the sync date range.

**Bug Example:**
- Repository has 2410 total PRs (all time)
- Sync filters to last 30 days = 14 PRs
- Progress shows: 14/2410 = 2% (WRONG)
- Should show: 14/14 = 100% (CORRECT)

## Current State

### Root Cause Location

**File:** `apps/integrations/services/github_graphql_sync.py`, lines 208-212

```python
# BUG: totalCount returns ALL repository PRs, not date-filtered count
if total_prs == 0:
    total_prs = pull_requests_data.get("totalCount", 0)  # Returns 2410
    await _update_sync_progress(tracked_repo_id, 0, total_prs)
```

### Impact

- Sync appears stuck at low percentage when actually complete
- Wrong time estimates ("~7 minutes remaining" when done)
- Confusing user experience during onboarding

## Proposed Solution

Create a **reusable function** `get_pr_count_in_date_range()` using GitHub's Search API, which supports date filtering.

### Why Search API?

GitHub GraphQL's `pullRequests` connection returns `totalCount` for the entire repository. The Search API allows querying:
```
repo:owner/repo is:pr created:>=2024-12-01 created:<=2025-01-01
```

This returns the exact count of PRs in the date range.

## Implementation Phases

### Phase 1: RED - Write Failing Tests (TDD)

Create tests before implementation:

1. **Test `get_pr_count_in_date_range()`** - New method in `GitHubGraphQLClient`
2. **Test sync progress accuracy** - Verify progress uses date-filtered count

### Phase 2: GREEN - Implement

1. Add `SEARCH_PR_COUNT_QUERY` to `github_graphql.py`
2. Add `get_pr_count_in_date_range()` method to `GitHubGraphQLClient`
3. Update `sync_repository_history_graphql()` to use new function

### Phase 3: REFACTOR

1. Add error handling for search query
2. Add logging for debugging
3. Consider caching if called multiple times

## Files to Modify

| File | Changes |
|------|---------|
| `apps/integrations/services/github_graphql.py` | Add `SEARCH_PR_COUNT_QUERY`, add `get_pr_count_in_date_range()` |
| `apps/integrations/services/github_graphql_sync.py` | Use new function for progress total |
| `apps/integrations/tests/test_github_graphql.py` | Add tests for new function |
| `apps/integrations/tests/test_github_graphql_sync.py` | Add tests for progress accuracy |

## Technical Details

### New GraphQL Query

```graphql
query($searchQuery: String!) {
  search(query: $searchQuery, type: ISSUE, first: 1) {
    issueCount
  }
  rateLimit {
    remaining
    resetAt
  }
}
```

### New Function Signature

```python
async def get_pr_count_in_date_range(
    self,
    owner: str,
    repo: str,
    since: datetime | None = None,
    until: datetime | None = None,
) -> int:
    """Get exact count of PRs created within a date range.

    Uses GitHub Search API which supports date filtering.
    Reusable for progress tracking, reporting, etc.
    """
```

### Integration Point

```python
# In sync_repository_history_graphql()
cutoff_date = timezone.now() - timedelta(days=days_back)
skip_before_date = timezone.now() - timedelta(days=skip_recent) if skip_recent else None

# NEW: Get accurate count for progress
total_prs = await client.get_pr_count_in_date_range(
    owner=owner,
    repo=repo,
    since=cutoff_date,
    until=skip_before_date,
)
await _update_sync_progress(tracked_repo_id, 0, total_prs)
```

## Reusability

The new function can be reused for:
- Progress tracking during sync (primary use case)
- Dashboard metrics (PRs per time period)
- Analytics queries
- Rate limiting decisions (estimate work before starting)

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| `sync_prs_total` | 2410 (all PRs) | 14 (date-filtered) |
| `sync_progress` | 2% (wrong) | 100% (correct) |
| Time estimate | "~7 min remaining" | Complete |

## Verification SQL

```sql
SELECT full_name, sync_status, sync_progress, sync_prs_completed, sync_prs_total
FROM integrations_trackedrepository
WHERE team_id = 151;
```

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| GitHub Search API rate limits | Search costs ~1 point, runs once per sync start |
| Search API availability | Fallback to current behavior if search fails |
| Date edge cases | Use `>=` and `<=` for inclusive ranges |

## Dependencies

- No new packages required
- No database migrations needed
- Uses existing `gql` library for GraphQL

## Test Commands

```bash
# RED Phase - Tests should FAIL
.venv/bin/pytest apps/integrations/tests/test_github_graphql.py::TestGetPRCountInDateRange -v
.venv/bin/pytest apps/integrations/tests/test_github_graphql_sync.py::TestSyncProgressTracking -v

# GREEN Phase - Tests should PASS
.venv/bin/pytest apps/integrations/tests/test_github_graphql.py -v
.venv/bin/pytest apps/integrations/tests/test_github_graphql_sync.py -v

# Full regression
.venv/bin/pytest apps/integrations/tests/ -v --tb=short
```
