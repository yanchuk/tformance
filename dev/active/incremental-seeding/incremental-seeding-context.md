# Incremental Seeding Context

**Last Updated:** 2025-12-24

## Strategic Vision - CRITICAL INSIGHT

**Goal**: Maximize real data collection from public GitHub repos. Store ALL data GitHub provides within our OAuth scope.

### Data Collection Philosophy
- **Store everything** - Labels, milestones, assignees, linked issues
- **Real users use OAuth** (single token) - improvements must work for production
- **Core patterns** (retry, batching, caching) live in shared services

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

### ✅ Phase 1: Stability (COMPLETE)

1. **PRCache dataclass** - `apps/metrics/seeding/pr_cache.py`
   - Saves to `.seeding_cache/{org}/{repo}.json`
   - 18 tests in `apps/metrics/tests/test_pr_cache.py`

2. **Cache integration in GitHubGraphQLFetcher**
   - `use_cache` parameter controls behavior
   - Auto-save after fetch, auto-load before fetch

3. **On-the-fly team member creation**
   - `_create_member_from_pr_author()` in real_project_seeder.py
   - No more PR skipping due to max_members limit

4. **Management command flags**
   - `--refresh` - Deletes cache, forces re-fetch
   - `--no-cache` - Disables caching entirely

5. **GraphQL optimization**
   - Reduced batch sizes: 25 PRs/page (was 50)
   - 60-second HTTP timeout with 3 retries

6. **Committed to main**: `a1bff2d`

### ✅ Phase 2: Complete Data Collection (COMPLETE)

1. **GraphQL Query Updates** - All 3 queries updated:
   - `FETCH_PRS_BULK_QUERY`
   - `FETCH_PRS_UPDATED_QUERY`
   - `FETCH_SINGLE_PR_QUERY`

   New fields added:
   - `isDraft` - Draft status
   - `labels(first: 10) { nodes { name color } }` - Label names
   - `milestone { title number dueOn }` - Milestone info
   - `assignees(first: 10) { nodes { login } }` - Assignee usernames
   - `closingIssuesReferences(first: 5) { nodes { number title } }` - Linked issues

2. **Model Changes** - Migration `0017_add_pr_github_metadata.py`:
   - `is_draft` BooleanField (default=False)
   - `labels` JSONField (default=list) - ["bug", "feature"]
   - `milestone_title` CharField (max_length=255, blank=True)
   - `assignees` JSONField (default=list) - ["user1", "user2"]
   - `linked_issues` JSONField (default=list) - [42, 123]

3. **FetchedPRFull Dataclass** - New fields:
   - `milestone_title: str | None = None`
   - `assignees: list[str] = field(default_factory=list)`
   - `linked_issues: list[int] = field(default_factory=list)`

4. **Mapping Logic** - `_map_pr()` updated:
   - Labels from `labels.nodes[].name`
   - Milestone from `milestone.title`
   - Assignees from `assignees.nodes[].login`
   - Linked issues from `closingIssuesReferences.nodes[].number`

5. **Seeding** - `_create_single_pr()` passes all new fields to factory

6. **TDD Tests** - 11 new tests in `TestGitHubGraphQLFetcherMapPR`:
   - Labels mapping (3 tests: normal, empty, null)
   - Milestone mapping (2 tests: normal, null)
   - Assignees mapping (2 tests: normal, empty)
   - Linked issues mapping (2 tests: normal, empty)
   - isDraft mapping (1 test)
   - Complete PR test (1 test)

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/seeding/pr_cache.py` | Local cache for fetched PR data |
| `apps/metrics/seeding/github_graphql_fetcher.py` | GraphQL fetcher with cache |
| `apps/metrics/seeding/real_project_seeder.py` | Orchestrates seeding |
| `apps/integrations/services/github_graphql.py` | **Shared** GraphQL client |
| `apps/metrics/models/github.py` | PullRequest model with Phase 2 fields |
| `apps/metrics/migrations/0017_add_pr_github_metadata.py` | Phase 2 migration |
| `apps/metrics/tests/test_github_graphql_fetcher.py` | Tests including Phase 2 |

## Commands

```bash
# Run all seeding/graphql tests
.venv/bin/pytest apps/metrics/tests/test_pr_cache.py apps/metrics/tests/test_github_graphql_fetcher.py -v

# Seed with cache (default)
python manage.py seed_real_projects --project antiwork

# Force re-fetch from GitHub
python manage.py seed_real_projects --project antiwork --refresh

# Disable caching entirely
python manage.py seed_real_projects --project antiwork --no-cache

# Clear and reseed
python manage.py seed_real_projects --project antiwork --clear
```

## Test Count

- PRCache: 18 tests
- GitHubGraphQLFetcher: 25 tests (14 existing + 11 Phase 2)
- **Total: 43 tests passing**

## Next Steps (Phase 3+)

1. **Speed** - Parallel repo fetching, skip unchanged repos
2. **Production Alignment** - Apply improvements to Celery sync tasks
3. **Analytics** - Filter PRs by label, milestone tracking, assignee workload
