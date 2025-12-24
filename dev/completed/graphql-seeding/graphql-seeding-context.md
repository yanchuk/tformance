# GraphQL Seeding Context

**Last Updated:** 2025-12-24

## Current Implementation State

### ✅ COMPLETED

1. Created `GitHubGraphQLFetcher` class in `apps/metrics/seeding/github_graphql_fetcher.py`
2. Provides same interface as `GitHubAuthenticatedFetcher`:
   - `fetch_prs_with_details(repo, since, max_prs)` → `list[FetchedPRFull]`
   - `get_top_contributors(repo, max_count, since)` → `list[ContributorInfo]`
3. Integrated into `RealProjectSeeder` with `use_graphql=True` default
4. Added `--no-graphql` flag to management command
5. **Added REST fallback for check runs** - CI/CD data now included
6. **Optimized check runs fetching** - 1 API call/PR (was 3)
7. **Reduced batch sizes per GitHub best practices** - 25 PRs/page (was 50), preventing timeouts

### Performance Comparison

| Metric | REST (old) | GraphQL only | GraphQL + Check Runs (optimized) |
|--------|------------|--------------|----------------------------------|
| API calls for 10 PRs | ~100 | ~4 | **~27** |
| API calls for 100 PRs | ~500 | ~6 | **~110** |
| API calls for 5000 PRs | ~25,000 | ~30 | **~5,030** |
| Time for 10 PRs | ~2 min | ~10 sec | **~27 sec** |
| Data completeness | 100% | 95% (no check runs) | **100%** |

### Optimizations Applied

1. **GraphQL for bulk data** - PRs, reviews, commits, files in single query
2. **Repo object caching** - Each repo fetched once and cached
3. **Commit SHA reuse** - Use SHA from GraphQL instead of re-fetching PR
4. **Parallel check run fetching** - ThreadPoolExecutor with 4 workers

### Data Fetching Strategy

| Data Type | Source | API Calls | Notes |
|-----------|--------|-----------|-------|
| PRs (metadata) | GraphQL | 1 per 25 PRs | Bulk fetch with pagination |
| Reviews | GraphQL | 0 (nested) | Up to 25 per PR |
| Commits | GraphQL | 0 (nested) | Up to 50 per PR, includes SHA |
| Files | GraphQL | 0 (nested) | Up to 50 per PR |
| Check runs | REST | **1 per PR** | Uses commit SHA from GraphQL |
| Contributors | GraphQL | 1 per 100 | Uses mentionableUsers |

### Batch Size Rationale (GitHub Best Practices)

Per [GitHub GraphQL Rate Limits](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api):
- Use `first: 10-25` for queries with nested connections
- Reduce nested limits for complex queries
- Prevents timeouts on large repositories

**Current limits:**
- PRs per page: 25 (was 50)
- Reviews per PR: 25 (was 50)
- Commits per PR: 50 (was 100)
- Files per PR: 50 (was 100)

## Key Files

### Seeding (GraphQL + REST hybrid)
- `apps/metrics/seeding/github_graphql_fetcher.py`
  - `GitHubGraphQLFetcher` - main class
  - `_fetch_check_runs_for_commit(repo, sha)` - **1 API call** using cached commit SHA
  - `_add_check_runs_to_prs()` - parallel fetching with ThreadPoolExecutor

### Production Sync (REST only)
- `apps/integrations/services/github_sync.py`
  - `sync_pr_check_runs()` - **2 API calls** (get_pull + get_commit)
  - Could be optimized to pass head SHA from parent sync

### GraphQL Client
- `apps/integrations/services/github_graphql.py`
  - `GitHubGraphQLClient` - async client
  - `FETCH_PRS_BULK_QUERY` - includes commits with SHA

## Test Results

### Antiwork (3 repos, 10 PRs, 7 days) - Optimized
```
Pull requests: 10
Check runs: 155
GitHub API calls: 27  (was 63 before optimization)
Time: 26.7s
```

## Configuration

### Real Projects Registry
```python
REAL_PROJECTS = {
    "antiwork": RealProjectConfig(
        repos=("antiwork/gumroad", "antiwork/flexile", "antiwork/helper"),
        # 473 PRs in 90 days
    ),
    "polar": RealProjectConfig(
        repos=("polarsource/polar", "polarsource/polar-adapters",
               "polarsource/polar-python", "polarsource/polar-js"),
        # 1,193 PRs in 90 days
    ),
    "posthog": RealProjectConfig(
        repos=("PostHog/posthog", "PostHog/posthog.com",
               "PostHog/posthog-js", "PostHog/posthog-python"),
        # 5,165 PRs in 90 days
    ),
}
```

## Seeding Commands

```bash
# Full coverage for all orgs (90 days)
python manage.py seed_real_projects --project antiwork --clear --max-prs 500 --days-back 90
python manage.py seed_real_projects --project polar --clear --max-prs 1200 --days-back 90
python manage.py seed_real_projects --project posthog --clear --max-prs 5200 --days-back 90

# Or all at once
python manage.py seed_real_projects --project antiwork --clear --max-prs 500 --days-back 90 && \
python manage.py seed_real_projects --project polar --clear --max-prs 1200 --days-back 90 && \
python manage.py seed_real_projects --project posthog --clear --max-prs 5200 --days-back 90
```

## Potential Future Optimizations

1. **Production sync optimization** - Pass head SHA to `sync_pr_check_runs()` to avoid extra API call
2. **GraphQL check runs** - GitHub's GraphQL API does support check runs via `checkSuites`, could eliminate REST entirely
3. **Batch commit lookups** - Could potentially batch multiple commit SHA lookups

## Comparison: Seeding vs Production Sync

| Aspect | Seeding | Production Sync |
|--------|---------|-----------------|
| PR fetching | GraphQL (bulk) | REST (per PR) |
| Check runs API calls | 1 per PR | 2 per PR |
| Parallelization | Yes (4 workers) | No |
| Commit SHA source | GraphQL response | Fetch from GitHub |
| Use case | Demo data | Live user data |
