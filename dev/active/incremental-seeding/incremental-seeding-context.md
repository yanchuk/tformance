# Incremental Seeding Context

**Last Updated:** 2025-12-24 (Session End)

## Strategic Vision

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

### ✅ Phase 1: Stability (COMPLETE) - Commit `a1bff2d`

1. **PRCache dataclass** - `apps/metrics/seeding/pr_cache.py`
2. **Cache integration** - `use_cache` parameter in GitHubGraphQLFetcher
3. **On-the-fly team member creation** - No more PR skipping
4. **Management command flags** - `--refresh`, `--no-cache`
5. **GraphQL optimization** - 25 PRs/page, 60s timeout

### ✅ Phase 2: Complete Data Collection (COMPLETE) - Commit `c93c575`

**This Session's Work:**

1. **GraphQL Query Updates** (`apps/integrations/services/github_graphql.py`)
   - All 3 queries updated: FETCH_PRS_BULK_QUERY, FETCH_PRS_UPDATED_QUERY, FETCH_SINGLE_PR_QUERY
   - New fields: `isDraft`, `labels`, `milestone`, `assignees`, `closingIssuesReferences`

2. **Model Changes** (`apps/metrics/models/github.py:149-180`)
   - Migration: `0017_add_pr_github_metadata.py` (APPLIED)
   - Fields: `is_draft`, `labels`, `milestone_title`, `assignees`, `linked_issues`

3. **FetchedPRFull Dataclass** (`apps/metrics/seeding/github_authenticated_fetcher.py:171-174`)
   - Added: `milestone_title`, `assignees`, `linked_issues`

4. **Mapping Logic** (`apps/metrics/seeding/github_graphql_fetcher.py:181-201`)
   - `_map_pr()` extracts all Phase 2 fields from GraphQL response

5. **Seeding** (`apps/metrics/seeding/real_project_seeder.py:516-521`)
   - `_create_single_pr()` passes all new fields to factory

6. **TDD Tests** (`apps/metrics/tests/test_github_graphql_fetcher.py:668-965`)
   - 11 new tests in `TestGitHubGraphQLFetcherMapPR`
   - All 43 seeding tests passing

## Key Files Modified This Session

| File | Lines | Changes |
|------|-------|---------|
| `apps/integrations/services/github_graphql.py` | 17-288 | Added Phase 2 fields to 3 GraphQL queries |
| `apps/metrics/models/github.py` | 149-180 | Added 5 new fields to PullRequest model |
| `apps/metrics/seeding/github_authenticated_fetcher.py` | 171-174 | Added fields to FetchedPRFull dataclass |
| `apps/metrics/seeding/github_graphql_fetcher.py` | 181-201 | Updated _map_pr() for Phase 2 fields |
| `apps/metrics/seeding/real_project_seeder.py` | 516-521 | Updated _create_single_pr() |
| `apps/metrics/tests/test_github_graphql_fetcher.py` | 668-965 | Added 11 TDD tests |
| `apps/metrics/migrations/0017_add_pr_github_metadata.py` | NEW | Phase 2 migration |

## Decisions Made This Session

1. **JSONField over M2M** - Chose JSONField for labels/assignees/linked_issues for simplicity
2. **Store label names only** - Not storing color (can fetch if needed later)
3. **linked_issues as list of ints** - Just issue numbers, not full Issue model

## Commands for Next Session

```bash
# Verify Phase 2 commit
git log -1 --oneline  # Should show c93c575

# Run all seeding tests
.venv/bin/pytest apps/metrics/tests/test_pr_cache.py apps/metrics/tests/test_github_graphql_fetcher.py -v

# Test seeding with new fields (requires GITHUB_SEEDING_TOKENS)
python manage.py seed_real_projects --project antiwork --refresh --max-prs 10
```

## Test Count

- PRCache: 18 tests
- GitHubGraphQLFetcher: 25 tests (14 existing + 11 Phase 2)
- **Total: 43 tests passing**

## Uncommitted Changes

Check with: `git status --short`

May include:
- `apps/metrics/seeding/real_projects.py` - Unrelated changes
- `apps/metrics/services/ai_detector.py` - Unrelated AI detection work
- `dev/active/ai-detection-pr-descriptions/` - Different feature

## Next Steps (Phase 3+)

1. **Speed** - Parallel repo fetching, skip unchanged repos
2. **Production Alignment** - Apply improvements to Celery sync tasks
3. **Analytics** - Filter PRs by label, milestone tracking, assignee workload

## Blockers / Issues

- GitHub API rate limits hit during testing (403 on REST check runs endpoint)
- Seeding works for GraphQL PR fetch, but REST fallback for check runs can fail
- Consider: Make check runs fetch optional or use GraphQL for those too
