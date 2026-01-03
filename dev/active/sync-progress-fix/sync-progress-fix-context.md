# Context: Sync Progress Fix

**Last Updated:** 2026-01-03

## Problem Statement

During onboarding sync, the progress bar shows incorrect percentages because `totalCount` from GraphQL returns ALL PRs in the repository, not just PRs within the date filter.

**Example:**
```
Repository: railsware/mailtrap-halon-scripts
Total PRs (all time): 2410
PRs in last 30 days: 14
Progress shown: 14/2410 = 2% (WRONG)
Should be: 14/14 = 100% (CORRECT)
```

## Related Issue

This is part of the larger LLM misclassification investigation. The files weren't being saved due to `asyncio.run()` bug (now fixed), and this progress tracking issue was discovered during testing.

## Key Files

### Implementation Files

| File | Purpose | Lines to Modify |
|------|---------|-----------------|
| `apps/integrations/services/github_graphql.py` | GitHub GraphQL client | Add query + method at end |
| `apps/integrations/services/github_graphql_sync.py` | Sync orchestration | Lines 208-212 |

### Test Files

| File | Purpose |
|------|---------|
| `apps/integrations/tests/test_github_graphql.py` | Tests for GraphQL client |
| `apps/integrations/tests/test_github_graphql_sync.py` | Tests for sync logic |

## Current Bug Location

**File:** `apps/integrations/services/github_graphql_sync.py`

```python
# Lines 208-212 - THE BUG
if total_prs == 0:
    total_prs = pull_requests_data.get("totalCount", 0)  # Returns ALL PRs!
    await _update_sync_progress(tracked_repo_id, 0, total_prs)
```

## GitHub Search API

The Search API supports date filtering via the search query syntax:

```
repo:owner/repo is:pr created:>=2024-12-01 created:<=2025-01-01
```

GraphQL endpoint:
```graphql
query($searchQuery: String!) {
  search(query: $searchQuery, type: ISSUE, first: 1) {
    issueCount  # Returns exact count matching the query
  }
}
```

## Test Environment

| Property | Value |
|----------|-------|
| Team ID | 151 |
| Team Name | railsware |
| Repo | railsware/mailtrap-halon-scripts |
| Total PRs | 2410 |
| PRs in 30 days | 14 |

## Database State (Before Fix)

```sql
SELECT full_name, sync_progress, sync_prs_completed, sync_prs_total
FROM integrations_trackedrepository
WHERE team_id = 151;
```

Result:
- `sync_progress`: 77
- `sync_prs_completed`: 1860
- `sync_prs_total`: 2410 (WRONG - this is PR number, not count!)

## Related Documentation

- [GitHub Search API](https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests)
- [GraphQL Search Endpoint](https://docs.github.com/en/graphql/reference/queries#search)

## Decisions Made

1. **Use Search API** - Only way to get date-filtered count
2. **Make function reusable** - Can be used for reporting, analytics
3. **Run once at sync start** - Minimal API cost (1 point)
4. **Fallback to current behavior** - If search fails, use totalCount

## Dependencies

- `gql` library (already installed)
- No new packages needed
- No migrations needed
