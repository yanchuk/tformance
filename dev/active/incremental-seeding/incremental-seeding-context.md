# Incremental Seeding Context

**Last Updated:** 2025-12-24 (Phase 3 Complete - Ready to Commit)

## Strategic Vision

**Goal**: Maximize real data collection from public GitHub repos while following GitHub API best practices.

### Key Principles (from GitHub API Best Practices)

1. **Sequential requests** - "Make requests serially instead of concurrently" to avoid secondary rate limits
2. **Conditional requests** - Check if data changed before re-fetching
3. **Rate limit awareness** - Monitor `x-ratelimit-remaining`, pause if low
4. **Exponential backoff** - With jitter on retries (deferred - not needed for single-user)

Sources:
- [GitHub REST API Best Practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)
- [GitHub GraphQL Rate Limits](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api)

### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Shared Services                         │
│  apps/integrations/services/github_graphql.py               │
│  - GitHubGraphQLClient (retry, timeout, rate limit)         │
│  - Used by BOTH seeding AND production sync                 │
└─────────────────────────────────────────────────────────────┘
         ↑                                    ↑
┌─────────────────────┐          ┌─────────────────────────────┐
│   Seeding Layer     │          │   Production Sync Layer     │
│   PRCache for local │          │   DB-backed state           │
│   .seeding_cache/   │          │   Celery for async          │
└─────────────────────┘          └─────────────────────────────┘
```

## Implementation Status

### ✅ Phase 1: Stability (COMPLETE) - Commit `a1bff2d`

1. **PRCache dataclass** - `apps/metrics/seeding/pr_cache.py`
2. **Cache integration** - `use_cache` parameter in GitHubGraphQLFetcher
3. **On-the-fly team member creation** - No more PR skipping
4. **Management command flags** - `--refresh`, `--no-cache`
5. **GraphQL optimization** - 25 PRs/page, 60s timeout

### ✅ Phase 2: Complete Data Collection (COMPLETE) - Commit `c93c575`

1. **GraphQL Query Updates** (`apps/integrations/services/github_graphql.py`)
   - All 3 queries updated: FETCH_PRS_BULK_QUERY, FETCH_PRS_UPDATED_QUERY, FETCH_SINGLE_PR_QUERY
   - New fields: `isDraft`, `labels`, `milestone`, `assignees`, `closingIssuesReferences`

2. **Model Changes** (`apps/metrics/models/github.py`)
   - Migration: `0017_add_pr_github_metadata.py` (APPLIED)
   - Fields: `is_draft`, `labels`, `milestone_title`, `assignees`, `linked_issues`

3. **FetchedPRFull Dataclass** (`apps/metrics/seeding/github_authenticated_fetcher.py`)
   - Added: `milestone_title`, `assignees`, `linked_issues`

4. **Mapping Logic** (`apps/metrics/seeding/github_graphql_fetcher.py`)
   - `_map_pr()` extracts all Phase 2 fields from GraphQL response

5. **Seeding** (`apps/metrics/seeding/real_project_seeder.py`)
   - `_create_single_pr()` passes all new fields to factory

6. **TDD Tests** (`apps/metrics/tests/test_github_graphql_fetcher.py`)
   - 11 new tests in `TestGitHubGraphQLFetcherMapPR`

### ✅ Phase 3: GitHub API Best Practices (COMPLETE) - UNCOMMITTED

#### 3.0 Fix Parallel Check Runs ✅ (Commit `3f1f928`)
- Removed `ThreadPoolExecutor` from `_add_check_runs_to_prs()`
- Requests now made sequentially per GitHub guidelines
- Added docstring with reference to GitHub best practices

#### 3.1 Repository Change Detection ✅ (Commit `3f1f928`)
- Added lightweight `FETCH_REPO_METADATA_QUERY` (~1 point)
- Added `fetch_repo_metadata()` method to `GitHubGraphQLClient`
- Extended `PRCache` with `repo_pushed_at` field
- Updated `is_valid()` to check if repo has changed
- Cache now skipped if repo was pushed to since last fetch

#### 3.2 Rate Limit Monitoring ✅ (Commit `7e5094e`)
- Added `_check_rest_rate_limit()` method to `GitHubGraphQLFetcher`
- Checks REST API rate limit before fetching check runs
- Logs warning when remaining points are low (<100)
- Skips check runs fetch if not enough points remaining

#### 3.3 Incremental PR Sync ✅ (UNCOMMITTED - This Session)
- Added `_fetch_updated_prs_async()` method using `FETCH_PRS_UPDATED_QUERY`
- Added `_merge_prs()` method to merge cached and updated PRs by number
- Updated `fetch_prs_with_details()` to use incremental sync when cache is stale
- PRs merged by number, sorted by `updated_at` DESC
- 6 new TDD tests in `TestGitHubGraphQLFetcherIncrementalSync`

#### 3.4 Exponential Backoff with Jitter (DEFERRED)
- Not needed for single-user seeding - thundering herd isn't a problem

## This Session's Work (Phase 3.3)

### Files Modified

| File | Changes |
|------|---------|
| `apps/metrics/seeding/github_graphql_fetcher.py` | +119 lines: `_fetch_updated_prs_async()`, `_merge_prs()`, updated `fetch_prs_with_details()` |
| `apps/metrics/tests/test_github_graphql_fetcher.py` | +350 lines: 6 new tests in `TestGitHubGraphQLFetcherIncrementalSync` |
| `dev/active/incremental-seeding/*.md` | Documentation updates |

### Key Methods Added

1. **`_fetch_updated_prs_async(repo, since)`** (lines 537-591)
   - Fetches PRs updated since a datetime using `FETCH_PRS_UPDATED_QUERY`
   - Stops pagination when encountering PRs older than `since`

2. **`_merge_prs(cached_prs, updated_prs)`** (lines 593-615)
   - Merges updated PRs with cached PRs by PR number
   - Replaces cached PRs with updated versions
   - Adds new PRs not in cache
   - Sorts by `updated_at` DESC

3. **Updated `fetch_prs_with_details()`** (lines 491-525)
   - Detects stale cache (repo pushed to since cache created)
   - Fetches only updated PRs since `cache.fetched_at`
   - Merges with cached PRs
   - Saves merged result to new cache

### Incremental Sync Flow
```
1. Load cache → cache exists but is_valid() returns False
2. Detect: repo_pushed_at > cache.repo_pushed_at (repo changed)
3. Fetch only PRs updated since cache.fetched_at
4. Merge: {cached_pr.number: cached_pr} | {updated_pr.number: updated_pr}
5. Sort by updated_at DESC
6. Save merged PRs to new cache
```

## Test Count

- PRCache: 25 tests
- GitHubGraphQLFetcher: 37 tests (31 existing + 6 incremental sync)
- **Total: 62 tests passing**

## Session Commits

| Commit | Description |
|--------|-------------|
| `3f1f928` | Phase 3.0 (sequential check runs) + Phase 3.1 (repo change detection) |
| `7e5094e` | Phase 3.2 (REST API rate limit monitoring) |
| PENDING | Phase 3.3 (incremental PR sync) - ready to commit |

## Handoff Notes

### Current State
- **Phase 3 complete** (3.3 uncommitted, ready to commit)
- **62 tests passing**
- No migrations needed (seeding utilities only)

### Uncommitted Changes Ready for Commit
```bash
git -C /Users/yanchuk/Documents/GitHub/tformance add \
  apps/metrics/seeding/github_graphql_fetcher.py \
  apps/metrics/tests/test_github_graphql_fetcher.py \
  dev/active/incremental-seeding/

git -C /Users/yanchuk/Documents/GitHub/tformance commit -m "Add incremental PR sync for seeding (Phase 3.3)

Implements incremental sync when cache is stale instead of full re-fetch:
- _fetch_updated_prs_async() fetches only PRs updated since cache.fetched_at
- _merge_prs() merges updated PRs with cached PRs by number
- fetch_prs_with_details() uses incremental sync when cache exists but is stale

Benefits: Faster re-seeding when repo has few updates, reduced API calls.

Tests: 6 new TDD tests in TestGitHubGraphQLFetcherIncrementalSync
All 62 tests passing (25 PRCache + 37 GitHubGraphQLFetcher)"
```

### Verification Commands
```bash
# Verify tests pass
.venv/bin/pytest apps/metrics/tests/test_pr_cache.py apps/metrics/tests/test_github_graphql_fetcher.py -v

# Check git status
git status --short

# Test seeding with incremental sync
python manage.py seed_real_projects --project antiwork --max-prs 10
# (run twice - second run should use incremental sync if repo has updates)
```

### No Migrations Needed
- No model changes in Phase 3
- All changes are to seeding utilities (not production models)

### Next Steps (Phase 4+)
- Phase 4: Apply improvements to production Celery sync tasks
- Phase 5: Analytics (filter by label, milestone tracking, assignee workload)
