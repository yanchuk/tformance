# GitHub GraphQL Migration - Tasks

**Last Updated:** 2025-12-23 (Phase 5 Member Sync complete)

## Phase 1: GraphQL Client Infrastructure ✅ COMPLETE

- [x] Add `gql[aiohttp]` to pyproject.toml
- [x] Create `apps/integrations/services/github_graphql.py`
  - [x] `GitHubGraphQLClient` class
  - [x] Rate limit monitoring with `rateLimit` query field
  - [x] Error handling (rate limit, query errors)
  - [x] Retry logic with exponential backoff
  - [x] Async execution support
- [x] GraphQL queries extracted to module constants
  - [x] `FETCH_PRS_BULK_QUERY` - PR bulk query template
  - [x] `FETCH_SINGLE_PR_QUERY` - Single PR query template
  - [x] `FETCH_ORG_MEMBERS_QUERY` - Member query template
- [x] Add feature flags to settings.py
  - [x] `GITHUB_USE_GRAPHQL` master switch
  - [x] Per-operation flags (initial_sync, incremental_sync, etc.)
  - [x] `GITHUB_FALLBACK_REST` flag
- [x] Write unit tests for GraphQL client (22 tests passing)

## Phase 1.5: Timeout Handling ✅ COMPLETE

- [x] Add `GitHubGraphQLTimeoutError` exception class
- [x] Implement retry logic with exponential backoff for all fetch methods
  - [x] `fetch_prs_bulk` - retry on TimeoutError
  - [x] `fetch_single_pr` - retry on TimeoutError
  - [x] `fetch_org_members` - retry on TimeoutError
- [x] Add `max_retries` parameter (default: 3) to all fetch methods
- [x] Write TDD tests for timeout handling (12 new tests)
  - [x] `TestGitHubGraphQLTimeoutError` - exception tests (3)
  - [x] `TestTimeoutHandling` - raises on timeout (3)
  - [x] `TestRetryOnTimeout` - retry logic tests (6)
- [x] All 34 client tests passing

## Phase 2: Initial Sync Migration ✅ COMPLETE

- [x] Write failing tests for sync function (21 tests - RED phase)
- [x] Implement `sync_repository_history_graphql()` (GREEN phase)
- [x] Create data mapper: GraphQL → existing model format
  - [x] Map camelCase to snake_case (state, review state, file status)
  - [x] Handle null values
  - [x] Map GraphQL enums to model choices
- [x] Add progress tracking & logging (SyncResult class)
- [x] Fix linting issues (21 tests, all passing)
- [x] Update `sync_repository_initial_task` with try/fallback pattern
- [x] Full test suite passes (2328 tests)

## Phase 3: Incremental Sync Migration ✅ COMPLETE

- [x] Research existing `sync_repository_incremental` REST implementation
- [x] Add `FETCH_PRS_UPDATED_QUERY` - query ordered by UPDATED_AT
- [x] Add `fetch_prs_updated_since` method to client (6 tests)
- [x] Implement `sync_repository_incremental_graphql()` function (11 tests)
- [x] Handle "updated since" filtering - stop pagination when older than since
- [x] Update `sync_repository_task` with `_sync_incremental_with_graphql_or_rest()`
- [x] All 72 GraphQL tests passing (40 client + 32 sync)

## Phase 4: PR Complete Data Task ✅ COMPLETE

- [x] Reuse existing `FETCH_SINGLE_PR_QUERY` and `fetch_single_pr` method
- [x] Implement `fetch_pr_complete_data_graphql()` function (8 tests)
- [x] Add `_process_pr_nested_data_async` helper for existing PR updates
- [x] Update `fetch_pr_complete_data_task` with `_fetch_pr_core_data_with_graphql_or_rest()`
- [x] GraphQL handles commits/files/reviews; REST handles check_runs/comments
- [x] All 5 task tests + 8 new GraphQL tests passing (88 total GraphQL tests)

## Phase 5: Member Sync Migration ✅ COMPLETE

- [x] Research existing `sync_github_members` REST implementation
- [x] Update `FETCH_ORG_MEMBERS_QUERY` to include `databaseId` field
- [x] Implement `sync_github_members_graphql()` function (8 tests)
- [x] Add `_sync_members_with_graphql_or_rest()` helper to tasks.py
- [x] Update `sync_github_members_task` with GraphQL fallback
- [x] All 88 GraphQL tests passing (40 client + 48 sync)

## Phase 6: Testing & Validation (IN PROGRESS)

- [x] **Test with real repository** - synced `ianchuk-1-test/test` in 0.51s
- [ ] Benchmark performance with larger repository (before/after)
- [ ] Validate data consistency (GraphQL vs REST)
- [ ] Test rate limit handling
- [ ] Test fallback behavior
- [ ] Load testing with multiple concurrent syncs

## Phase 7: Production Rollout (NOT STARTED)

- [ ] Deploy with all feature flags OFF
- [ ] Enable `initial_sync` for test team
- [ ] Monitor rate limits and errors
- [ ] Enable for all new connections
- [ ] Update documentation

## Keep REST Permanently (Do Not Migrate)

- [x] Copilot metrics sync - confirmed REST only
- [x] Webhook handlers - GitHub sends REST payloads
- [x] OAuth flow - REST endpoints

## Definition of Done

- [ ] Initial sync for 400-PR repo completes in <5 minutes (was ~60 min)
- [ ] Rate limit usage <40% of hourly quota
- [x] GraphQL client tests pass (40/40) - includes timeout/retry + incremental
- [x] Sync function tests pass (48/48) - includes initial + incremental + PR complete + member sync
- [x] Full GraphQL test suite passes (88/88)
- [x] Feature flags allow instant rollback (USE_GRAPHQL, per-operation flags)
- [x] REST fallback works automatically on errors (FALLBACK_TO_REST)
