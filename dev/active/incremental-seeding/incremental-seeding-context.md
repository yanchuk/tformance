# Incremental Seeding Context

**Last Updated:** 2025-12-24

## Strategic Vision - CRITICAL INSIGHT

**Goal**: Maximize real data collection from public GitHub repos to power our analytics demo and product development.

### Key Realization
The seeding infrastructure improvements MUST also benefit real users:
- **Real users use OAuth** (single token) - not multiple PATs
- **Improvements must work for both** seeding AND production sync
- **Core patterns** (retry, batching, caching) should live in shared services

### Architecture Alignment
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
│   (Multiple tokens) │          │   (Single OAuth token)      │
│   PRCache for local │          │   DB-backed state           │
│   .seeding_cache/   │          │   Celery for async          │
└─────────────────────┘          └─────────────────────────────┘
```

## Current Implementation State

### ✅ COMPLETED (This Session)

1. **PRCache dataclass** - `apps/metrics/seeding/pr_cache.py`
   - Saves to `.seeding_cache/{org}/{repo}.json`
   - 18 tests in `apps/metrics/tests/test_pr_cache.py`

2. **Cache integration in GitHubGraphQLFetcher**
   - `use_cache` parameter controls behavior
   - Auto-save after fetch, auto-load before fetch
   - Output: `📦 Loaded from cache` / `💾 Saved to cache`

3. **On-the-fly team member creation**
   - `_create_member_from_pr_author()` in real_project_seeder.py
   - No more PR skipping due to max_members limit

4. **Management command flags**
   - `--refresh` - Deletes cache, forces re-fetch
   - `--no-cache` - Disables caching entirely
   - `use_cache` passed through RealProjectSeeder to fetcher

5. **GraphQL optimization** (earlier this session)
   - Reduced batch sizes: 25 PRs/page (was 50)
   - 60-second HTTP timeout with 3 retries
   - In `apps/integrations/services/github_graphql.py`

6. **Added .seeding_cache/ to .gitignore**

## Key Files Modified This Session

| File | Changes |
|------|---------|
| `apps/metrics/seeding/pr_cache.py` | NEW - Cache dataclass |
| `apps/metrics/seeding/github_graphql_fetcher.py` | Added cache integration, serialize/deserialize |
| `apps/metrics/seeding/real_project_seeder.py` | Added `_create_member_from_pr_author()`, `use_cache` |
| `apps/metrics/management/commands/seed_real_projects.py` | Added `--refresh`, `--no-cache` flags |
| `apps/integrations/services/github_graphql.py` | Reduced batch sizes, added 60s timeout |
| `.gitignore` | Added `.seeding_cache/` |
| `apps/metrics/tests/test_pr_cache.py` | NEW - 18 tests |

## Improvements Roadmap - Aligned with Production

### Phase 2: Speed (APPLIES TO PRODUCTION TOO)
- [ ] **Parallel repo fetching** - ThreadPoolExecutor
- [ ] **Incremental sync** - Only fetch new PRs since last sync
  - For seeding: compare cache date
  - For production: use `updated_since` parameter (already exists in GraphQL query)

### Phase 3: Resilience (CRITICAL FOR PRODUCTION)
- [ ] **Smart rate limit handling** - Wait instead of fail
  - Parse `X-RateLimit-Reset` header
  - Implement exponential backoff with jitter
  - This benefits OAuth users who hit limits
- [ ] **Resume capability** - Track sync progress per repo
  - For seeding: store in checkpoint file
  - For production: store in `GitHubIntegration` or new `SyncState` model

### Phase 4: Production Sync Improvements
- [ ] **Webhook-triggered sync** - Only sync changed repos
- [ ] **Priority queue** - Sync recently active repos first
- [ ] **Celery task improvements** - Better error handling, retry

## Database Models Involved

No new migrations needed this session. Existing models used:
- `PullRequest` - stores fetched PR data
- `TeamMember` - auto-created from PR authors
- `PRReview`, `Commit`, `PRFile`, `PRCheckRun` - nested data

## Testing Status

```bash
# All passing:
.venv/bin/pytest apps/metrics/tests/test_pr_cache.py  # 18 tests
.venv/bin/pytest apps/metrics/tests/test_github_graphql_fetcher.py  # 14 tests
.venv/bin/pytest apps/metrics/tests/test_real_project_seeding.py  # 6 tests
```

## Uncommitted Changes

```bash
# Modified files:
M apps/integrations/services/github_graphql.py  # Batch size, timeout
M apps/metrics/seeding/real_project_seeder.py  # On-the-fly members, use_cache
M apps/metrics/management/commands/seed_real_projects.py  # New flags
A apps/metrics/seeding/pr_cache.py  # NEW
A apps/metrics/tests/test_pr_cache.py  # NEW
M .gitignore  # Added .seeding_cache/
```

## Commands to Run on Resume

```bash
# Verify tests pass
.venv/bin/pytest apps/metrics/tests/test_pr_cache.py apps/metrics/tests/test_github_graphql_fetcher.py -v

# Test seeding with cache
python manage.py seed_real_projects --project antiwork --max-prs 10

# Check for ruff issues
.venv/bin/ruff check apps/metrics/seeding/ apps/integrations/services/github_graphql.py
```

## Next Immediate Steps

1. **Commit current changes** - All tests pass, ready to commit
2. **Implement incremental sync** - Benefits both seeding and production
3. **Add rate limit wait logic** - Critical for single-token (OAuth) users
4. **Align production sync tasks** with new patterns
