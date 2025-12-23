# GitHub GraphQL Migration - Context

**Last Updated:** 2025-12-23 (Phase 5 Member Sync complete)

## Current Implementation State

### Phase 1: GraphQL Client Infrastructure - COMPLETE ✅

**TDD Cycle completed for GitHubGraphQLClient:**
- RED: 22 tests written (all failing)
- GREEN: Implementation created, all tests pass
- REFACTOR: Code cleaned up, queries extracted to constants

### Phase 1.5: Timeout Handling - COMPLETE ✅

**TDD Cycle completed for timeout and retry logic:**
- RED: 12 new tests for timeout/retry scenarios
- GREEN: Implemented `GitHubGraphQLTimeoutError` and retry logic with exponential backoff
- All 3 fetch methods now have `max_retries` parameter (default: 3)

### Phase 2: Initial Sync Function - COMPLETE ✅

**TDD Cycle completed for sync_repository_history_graphql:**
- RED: 21 tests written (all failing)
- GREEN: Implementation created, all tests pass
- Tests use `TransactionTestCase` for async/database compatibility

### Phase 3: Incremental Sync Migration - COMPLETE ✅

**TDD Cycle completed for sync_repository_incremental_graphql:**
- RED: 17 tests written (6 client + 11 sync function)
- GREEN: Implementation created, all 72 GraphQL tests pass
- New GraphQL query `FETCH_PRS_UPDATED_QUERY` ordered by UPDATED_AT
- Task integration via `_sync_incremental_with_graphql_or_rest()` helper

### Phase 4: PR Complete Data Task - COMPLETE ✅

**TDD Cycle completed for fetch_pr_complete_data_graphql:**
- RED: 8 tests written for single PR data fetch
- GREEN: Implementation reuses existing `fetch_single_pr` method
- New `_process_pr_nested_data_async` helper for existing PR updates
- Task integration via `_fetch_pr_core_data_with_graphql_or_rest()` helper
- GraphQL handles commits/files/reviews; REST handles check_runs/comments

### Phase 5: Member Sync Migration - COMPLETE ✅

**TDD Cycle completed for sync_github_members_graphql:**
- RED: 8 tests written for org member sync
- GREEN: Implementation uses existing `fetch_org_members` client method
- Updated `FETCH_ORG_MEMBERS_QUERY` to include `databaseId` field
- Task integration via `_sync_members_with_graphql_or_rest()` helper
- All 88 GraphQL tests passing (40 client + 48 sync)

## Files Created/Modified

| File | Status | Purpose |
|------|--------|---------|
| `apps/integrations/services/github_graphql.py` | ✅ Complete | GraphQL client with 4 queries + timeout handling |
| `apps/integrations/services/github_graphql_sync.py` | ✅ Complete | Initial + incremental + PR complete + member sync functions |
| `apps/integrations/tests/test_github_graphql.py` | ✅ Complete (40 tests) | Client tests including timeout/retry |
| `apps/integrations/tests/test_github_graphql_sync.py` | ✅ Complete (48 tests) | Sync tests (initial + incremental + PR complete + member) |
| `apps/integrations/tasks.py` | ✅ Modified | Added 4 GraphQL helper functions |
| `tformance/settings.py` | ✅ Modified | Added `GITHUB_API_CONFIG` feature flags |

## Key Decisions Made

1. **Library choice:** `gql[aiohttp]` for async GraphQL client
2. **Architecture:** Dual API pattern (GraphQL primary, REST fallback)
3. **Feature flags:** Per-operation control for gradual rollout
4. **Rate limit threshold:** 100 points remaining triggers switch to REST
5. **Error handling:** Wrap all GraphQL errors, fall back to REST on failure
6. **Test isolation:** Use `TransactionTestCase` for async database operations
7. **Async execution:** Use `async with Client() as session` context manager pattern for true async
8. **GraphQL pagination:** All nested connections require `first: N` pagination limits

## Feature Flags Added to settings.py

```python
GITHUB_API_CONFIG = {
    "USE_GRAPHQL": env.bool("GITHUB_USE_GRAPHQL", default=False),
    "GRAPHQL_OPERATIONS": {
        "initial_sync": env.bool("GITHUB_GRAPHQL_INITIAL_SYNC", default=True),
        "incremental_sync": env.bool("GITHUB_GRAPHQL_INCREMENTAL_SYNC", default=False),
        "pr_complete_data": env.bool("GITHUB_GRAPHQL_PR_COMPLETE", default=True),
        "member_sync": env.bool("GITHUB_GRAPHQL_MEMBERS", default=False),
    },
    "FALLBACK_TO_REST": env.bool("GITHUB_FALLBACK_REST", default=True),
    "GRAPHQL_RATE_LIMIT_THRESHOLD": env.int("GITHUB_GRAPHQL_RATE_LIMIT_THRESHOLD", default=100),
}
```

## sync_repository_history_graphql API

```python
from apps.integrations.services.github_graphql_sync import sync_repository_history_graphql

# Async function - call with asyncio.run() or in async context
result = await sync_repository_history_graphql(tracked_repo, days_back=90)

# Returns dict with counts:
{
    "prs_synced": 50,
    "reviews_synced": 120,
    "commits_synced": 200,
    "files_synced": 450,
    "comments_synced": 0,  # Not yet implemented
    "errors": ["error msg", ...]  # Empty if successful
}
```

## sync_repository_incremental_graphql API

```python
from apps.integrations.services.github_graphql_sync import sync_repository_incremental_graphql

# Async function - syncs PRs updated since last_sync_at
result = await sync_repository_incremental_graphql(tracked_repo)

# Uses UPDATED_AT ordering, stops when reaching PRs older than since timestamp
# Returns same dict format as initial sync
```

## sync_github_members_graphql API

```python
from apps.integrations.services.github_graphql_sync import sync_github_members_graphql

# Async function - syncs org members to TeamMember records
result = await sync_github_members_graphql(integration, org_name="acme-corp")

# Returns dict with counts:
{
    "members_created": 5,
    "members_updated": 2,
    "errors": []  # Empty if successful
}
```

## Data Mapping (GraphQL → Model)

| GraphQL Field | Model Field | Transformation |
|--------------|-------------|----------------|
| `number` | `github_pr_id` | Direct |
| `state` | `state` | MERGED→merged, OPEN→open, CLOSED→closed |
| `createdAt` | `pr_created_at` | ISO8601 → datetime |
| `mergedAt` | `merged_at` | ISO8601 → datetime (nullable) |
| `author.login` | `author` | Lookup TeamMember by github_id |
| `reviews.nodes[].state` | `PRReview.state` | APPROVED→approved, etc. |
| `files.nodes[].status` | `PRFile.status` | ADDED→added, etc. |

## Technical Notes

### Async/Database Compatibility

Django ORM operations must run in sync context when called from async:
- Use `sync_to_async` decorator for database operations
- Pass IDs instead of model instances to avoid cross-thread issues
- Use `TrackedRepository.objects.filter(id=id).update()` instead of `save()`

### Test Patterns

```python
# Tests use TransactionTestCase for async compatibility
from django.test import TransactionTestCase

class TestSyncFunction(TransactionTestCase):
    def test_async_sync(self):
        result = asyncio.run(sync_repository_history_graphql(repo))
```

## Commands to Verify

```bash
# Run all GraphQL tests (88 total: 40 client + 48 sync)
.venv/bin/pytest apps/integrations/tests/test_github_graphql.py apps/integrations/tests/test_github_graphql_sync.py -v

# Run PR complete data task tests (5 tests)
.venv/bin/pytest apps/integrations/tests/test_fetch_pr_complete_data.py -v

# Run member sync tests (7 tests)
.venv/bin/pytest apps/integrations/tests/test_member_sync.py -v

# Lint check
.venv/bin/ruff check apps/integrations/services/github_graphql*.py apps/integrations/tests/test_github_graphql*.py apps/integrations/tasks.py
```

## Timeout Handling Pattern

All fetch methods now implement retry logic with exponential backoff:

```python
async def fetch_prs_bulk(self, owner, repo, cursor=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = await self._execute(query, variables)
            return result
        except TimeoutError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                await asyncio.sleep(wait_time)
            else:
                raise GitHubGraphQLTimeoutError(f"timed out after {max_retries} attempts") from e
```

**Error hierarchy:**
- `GitHubGraphQLError` - base exception (generic query failures)
- `GitHubGraphQLRateLimitError` - rate limit exceeded (NOT retried, raises immediately)
- `GitHubGraphQLTimeoutError` - timeout after all retries exhausted

## Real Repository Test Results

Tested with `ianchuk-1-test/test` repository:
- **Sync time:** 0.51 seconds
- **PRs synced:** 1
- **Commits synced:** 1
- **Files synced:** 1
- **Errors:** None

## Next Immediate Steps

1. ✅ **Integration:** `sync_repository_initial_task` uses `_sync_with_graphql_or_rest()` helper
2. ✅ **Integration:** `sync_repository_task` uses `_sync_incremental_with_graphql_or_rest()` helper
3. ✅ **Test with real repository** - validated with `ianchuk-1-test/test`
4. ✅ **Phase 3: Incremental sync** - complete with TDD
5. ✅ **Phase 4: PR Complete Data** - `_fetch_pr_core_data_with_graphql_or_rest()` helper
6. ✅ **Phase 5: Member Sync** - `_sync_members_with_graphql_or_rest()` helper

7. **Benchmark with larger repository** (400+ PRs) to measure actual performance improvement
8. **Production rollout** - enable GraphQL flags progressively

## Dependencies Added

```toml
# pyproject.toml - already added
gql = "^4.0.0"  # with aiohttp extras
```

Installed packages:
- gql 4.0.0
- graphql-core 3.2.7
- aiohttp 3.13.2
- aiohappyeyeballs, aiosignal, frozenlist, multidict, propcache, yarl

## No Migrations Needed

This feature adds new service files only - no model changes.

## Session Handoff Notes (2025-12-23)

### What Was Completed This Session

**Phase 5 (Member Sync Migration) - COMPLETE:**
- Updated `FETCH_ORG_MEMBERS_QUERY` to include `databaseId` field for GitHub user ID matching
- Implemented `sync_github_members_graphql()` async function with TDD (8 tests)
- Added `_sync_members_with_graphql_or_rest()` helper in tasks.py
- Updated `sync_github_members_task` to use GraphQL with REST fallback
- All 88 GraphQL tests passing

### All GraphQL Migration Phases Complete

| Phase | Status | Tests |
|-------|--------|-------|
| 1. Client Infrastructure | ✅ | 22 tests |
| 1.5. Timeout Handling | ✅ | 12 tests |
| 2. Initial Sync | ✅ | 21 tests |
| 3. Incremental Sync | ✅ | 17 tests |
| 4. PR Complete Data | ✅ | 8 tests |
| 5. Member Sync | ✅ | 8 tests |
| **Total** | | **88 tests** |

### Verify Commands

```bash
# All GraphQL tests
.venv/bin/pytest apps/integrations/tests/test_github_graphql.py apps/integrations/tests/test_github_graphql_sync.py -v

# Lint
.venv/bin/ruff check apps/integrations/services/github_graphql*.py apps/integrations/tests/test_github_graphql*.py apps/integrations/tasks.py
```

### Next Steps (Future Sessions)

1. **Benchmark with larger repository** - test with 400+ PRs to measure performance improvement
2. **Production rollout** - enable `GITHUB_USE_GRAPHQL=true` progressively
3. **Monitor rate limits** - validate GraphQL point-based limits vs REST request limits
