# Incremental Seeding Context

**Last Updated:** 2025-12-24 (Phase 3 in Progress)

## Strategic Vision

**Goal**: Maximize real data collection from public GitHub repos while following GitHub API best practices.

### Key Principles (from GitHub API Best Practices)

1. **Sequential requests** - "Make requests serially instead of concurrently" to avoid secondary rate limits
2. **Conditional requests** - Check if data changed before re-fetching
3. **Rate limit awareness** - Monitor `x-ratelimit-remaining`, pause if low
4. **Exponential backoff** - With jitter on retries

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

### 🔄 Phase 3: GitHub API Best Practices (IN PROGRESS)

**This Session's Work:**

#### 3.0 Fix Parallel Check Runs ✅
- Removed `ThreadPoolExecutor` from `_add_check_runs_to_prs()`
- Requests now made sequentially per GitHub guidelines
- Added docstring with reference to GitHub best practices
- Files changed:
  - `apps/metrics/seeding/github_graphql_fetcher.py` (lines 376-410)
  - `apps/metrics/tests/test_github_graphql_fetcher.py` (test updates)

#### 3.1 Repository Change Detection ✅
- Added lightweight `FETCH_REPO_METADATA_QUERY` (~1 point)
- Added `fetch_repo_metadata()` method to `GitHubGraphQLClient`
- Extended `PRCache` with `repo_pushed_at` field
- Updated `is_valid()` to check if repo has changed
- Cache now skipped if repo was pushed to since last fetch
- Files changed:
  - `apps/integrations/services/github_graphql.py` (lines 315-330, 663-702)
  - `apps/metrics/seeding/pr_cache.py` (lines 35, 56-58, 84-95, 97-121)
  - `apps/metrics/seeding/github_graphql_fetcher.py` (lines 433-466, 470-493)
  - `apps/metrics/tests/test_pr_cache.py` (lines 330-462, 7 new tests)

#### 3.2 Rate Limit Monitoring ✅
- Added `_check_rest_rate_limit()` method to `GitHubGraphQLFetcher`
- Checks REST API rate limit before fetching check runs
- Logs warning when remaining points are low (<100)
- Skips check runs fetch if not enough points remaining
- Shows remaining points in console output
- Files changed:
  - `apps/metrics/seeding/github_graphql_fetcher.py` (lines 112-139, 422-435)
  - `apps/metrics/tests/test_github_graphql_fetcher.py` (5 new tests)

## Key Files Modified This Session

| File | Lines | Changes |
|------|-------|---------|
| `apps/integrations/services/github_graphql.py` | 315-330, 663-702 | Added FETCH_REPO_METADATA_QUERY and fetch_repo_metadata() |
| `apps/metrics/seeding/pr_cache.py` | 35, 56-58, 84-95, 97-121 | Added repo_pushed_at field, updated is_valid() |
| `apps/metrics/seeding/github_graphql_fetcher.py` | 376-410, 433-493 | Sequential check runs, repo change detection |
| `apps/metrics/tests/test_pr_cache.py` | 330-462 | 7 new tests for repo_pushed_at |
| `apps/metrics/tests/test_github_graphql_fetcher.py` | 451, 525, 666-744 | Updated tests for sequential behavior |

## Decisions Made This Session

1. **Sequential over parallel** - GitHub explicitly says "make requests serially" for REST
2. **repo_pushed_at for change detection** - Cheaper than ETags, works with GraphQL
3. **Backward compatible cache** - Old cache files without repo_pushed_at still load

## Commands for Next Session

```bash
# Verify tests pass
.venv/bin/pytest apps/metrics/tests/test_pr_cache.py apps/metrics/tests/test_github_graphql_fetcher.py -v

# Test seeding with repo change detection
python manage.py seed_real_projects --project antiwork --max-prs 10
# (first run fetches, second run should use cache if repo unchanged)

# Check uncommitted changes
git status --short
```

## Test Count

- PRCache: 25 tests
- GitHubGraphQLFetcher: 31 tests (26 existing + 5 rate limit)
- **Total: 56 tests passing**

## Next Steps (Remaining Phase 3)

1. ~~**Rate Limit Monitoring**~~ ✅ - Checks REST API limit, skips if low
2. **Incremental PR Sync** - Fetch only updated PRs using FETCH_PRS_UPDATED_QUERY
3. **Exponential Backoff with Jitter** - Add random jitter to retry delays

## Blockers / Issues

- GitHub API rate limits hit during testing (403 on REST check runs endpoint)
- Seeding works for GraphQL PR fetch, but REST fallback for check runs can fail
- Consider: Make check runs fetch optional or use GraphQL for those too
