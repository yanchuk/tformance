# GitHub Search API Sync Implementation Plan

**Last Updated:** 2026-01-04
**Status:** Ready for Implementation
**Approach:** Test-Driven Development (TDD)

---

## Executive Summary

Replace the inefficient GraphQL `pullRequests` connection (which has no date filtering) with the GitHub Search API to enable accurate progress tracking during onboarding sync. This fixes the "stuck progress bar" issue where we fetch ALL PRs but only process those within the date range.

### Key Benefits
1. **Accurate progress**: Search API returns `issueCount` - exact count for progress tracking
2. **Efficient fetching**: Only fetches PRs within the specified date range
3. **Phase 2 optimization**: Can fetch days 31-90 directly without paginating through recent PRs
4. **Cleaner code**: Remove complex `cutoff_date`/`skip_before_date` filtering logic

---

## Problem Statement

### Current Flow (Inefficient)

```
1. GET PR COUNT (Search API) - "How many PRs in last 30 days?"
   Query: "repo:owner/repo is:pr created:>=2025-12-05"
   Returns: 13 PRs

2. FETCH ALL PRs (GraphQL pullRequests connection) - NO DATE FILTER
   Page 1: PRs #2200-2191 (newest) → process 10 within range
   Page 2: PRs #2190-2181 → process 3, skip 7
   Page 3: PRs #2180-2171 → ALL older, skip all
   Page 4-200+: Keep fetching and skipping!

3. Progress appears stuck:
   - Total = 13 (from Search API)
   - Pagination continues through 200+ pages
   - Only 13 increment prs_processed
```

### Root Cause

GitHub's GraphQL `pullRequests` connection does NOT support date filtering.
Source: [GitHub Community Discussion](https://github.com/orgs/community/discussions/24611)

### Solution: Use Search API

```graphql
# Phase 1: Last 30 days
search(query: "repo:owner/repo is:pr created:>=2024-12-05", type: ISSUE, first: 10)

# Phase 2: Days 31-90 only
search(query: "repo:owner/repo is:pr created:2024-10-05..2024-12-04", type: ISSUE, first: 10)
```

The `search` query:
- Supports date filtering (`created:>=DATE`, `created:DATE1..DATE2`)
- Returns `issueCount` for accurate progress
- Provides full PR data via `... on PullRequest { }` fragment

---

## Architecture Changes

### Before (Current)

```
TrackedRepository.prs_total = get_pr_count_in_date_range()  # Search API
                                      ↓
GitHubGraphQLClient.fetch_prs_bulk()  # pullRequests connection (NO DATE FILTER)
                                      ↓
Python filtering: if pr.created < cutoff_date: skip  # Wasteful!
```

### After (Proposed)

```
Search API: "repo:x is:pr created:>=DATE"
            ↓
issueCount → TrackedRepository.prs_total (accurate!)
nodes → Full PR data via ... on PullRequest { }
            ↓
No Python filtering needed - query only returns matching PRs
```

---

## Implementation Phases

### Phase 1: Add Search-based PR Fetching

**File:** `apps/integrations/services/github_graphql.py`

1. Add `SEARCH_PRS_BY_DATE_QUERY` GraphQL query
2. Add `search_prs_by_date_range(owner, repo, since_date, until_date)` method
3. Return both `issueCount` (for progress) and PR data

### Phase 2: Update Sync Service

**File:** `apps/integrations/services/github_graphql_sync.py`

1. Create `sync_repository_history_by_search()` function
2. Use Search API instead of `fetch_prs_bulk`
3. Remove `cutoff_date`/`skip_before_date` Python filtering
4. Progress = PRs processed / issueCount

### Phase 3: Update Onboarding Pipeline

**File:** `apps/integrations/onboarding_pipeline.py`

1. Update Phase 1 task to use new sync function (30 days)
2. Update Phase 2 task with exact date range (31-90 days)
3. Add staged insight generation:
   - After Phase 1: Generate 7-day + 30-day insights
   - After Phase 2: Generate 90-day insights

---

## New Sync Flow

```
Phase 1 (30 days):
1. Search: "repo:x is:pr created:>=2024-12-05"
   → Response: issueCount=13, nodes=[...PR data...]
2. Update prs_total = 13
3. Paginate search results, process each PR
4. Progress: 1/13, 2/13, ... 13/13 ✓
5. Generate 7-day + 30-day insights

Phase 2 (31-90 days):
1. Search: "repo:x is:pr created:2024-10-05..2024-12-04"
   → Response: issueCount=45, nodes=[...PR data...]
2. Update prs_total = 45
3. Paginate search results, process each PR
4. Progress: 1/45, 2/45, ... 45/45 ✓
5. Generate 90-day insights
```

---

## Search API Considerations

| Aspect | Details |
|--------|---------|
| Max results | 1000 total (paginated) - usually enough for 90 days |
| Page size | 10 PRs per page (configurable up to 100) |
| Rate limit | Similar cost to current approach |
| Fields | Full PR data via `... on PullRequest { }` fragment |
| Sorting | `sort:created-desc` for newest first |

### Comparison

| Aspect | Current (`pullRequests`) | Proposed (`search`) |
|--------|-------------------------|---------------------|
| Date filter | Not supported | Built-in |
| Total count | Separate API call | `issueCount` in response |
| Phase 2 efficiency | Fetches ALL PRs, skips recent | Fetches only 31-90 day range |
| Same PR fields | Yes | Yes (via fragment) |

---

## Risk Assessment

### Low Risk
- **Search API stability**: Part of GitHub's core API, well-documented
- **Data consistency**: Same PR fields available via fragment

### Medium Risk
- **1000 result limit**: Could affect very active repos (>1000 PRs in 90 days)
  - Mitigation: Log warning if issueCount > 1000, consider chunking by month
- **Search syntax errors**: Malformed queries could fail
  - Mitigation: Unit test query string generation

### Mitigated
- **Breaking existing sync**: Keep old `fetch_prs_bulk` method, add new method alongside
- **Async/sync issues**: Follow existing `async_to_sync()` pattern from CLAUDE.md

---

## Success Metrics

1. **Progress bar accuracy**: Total displayed = PRs actually processed
2. **Phase 2 efficiency**: No pagination through recent 30-day PRs
3. **API call reduction**: Fewer total requests for repos with long history
4. **Test coverage**: 100% for new code (TDD approach)

---

## Future Enhancement: Streaming Batch Processing

> **Status:** Deferred - implement if repos with 1000+ PRs cause issues

### Current Sequential Flow
```
[Fetch ALL PRs] → [Process ALL Keywords] → [Process ALL LLM] → [Insights]
```

### Future Streaming Flow
```
[Fetch 100 PRs] → [Keywords batch] → [LLM batch] ─┐
[Fetch next 100] → [Keywords batch] → [LLM batch] ─┼→ [Insights]
[Fetch next 100] → [Keywords batch] → [LLM batch] ─┘
```

### Implementation Notes (for later)

1. **Batch trigger threshold**: After every 100 PRs fetched
2. **Celery chord orchestration**: Parallel fetch + process
3. **Dual progress tracking**: "Fetching... 150/200" + "Processing... 100/150"
4. **Benefits**: Memory efficient, faster user feedback
5. **Complexity**: Task orchestration, partial failure handling

---

## Appendix: GraphQL Query

```graphql
query SearchPRsByDateRange($searchQuery: String!, $cursor: String) {
  search(query: $searchQuery, type: ISSUE, first: 10, after: $cursor) {
    issueCount
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        number
        title
        body
        state
        createdAt
        mergedAt
        additions
        deletions
        isDraft
        author { login }
        labels(first: 10) { nodes { name color } }
        milestone { title number dueOn }
        assignees(first: 10) { nodes { login } }
        closingIssuesReferences(first: 5) { nodes { number title } }
        reviews(first: 25) { nodes { databaseId state body submittedAt author { login } } }
        commits(first: 50) { nodes { commit { oid message additions deletions author { date user { login } } } } }
        files(first: 50) { nodes { path additions deletions changeType } }
      }
    }
  }
  rateLimit {
    remaining
    resetAt
  }
}
```

### Search Query Strings

```python
# Phase 1: Last 30 days
f"repo:{owner}/{repo} is:pr created:>={cutoff_30d.strftime('%Y-%m-%d')} sort:created-desc"

# Phase 2: Days 31-90
f"repo:{owner}/{repo} is:pr created:{cutoff_90d.strftime('%Y-%m-%d')}..{cutoff_31d.strftime('%Y-%m-%d')} sort:created-desc"
```
