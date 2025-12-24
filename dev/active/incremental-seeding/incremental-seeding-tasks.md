# Incremental Seeding Tasks

**Last Updated:** 2025-12-24 (Phase 3 Complete)

## Phase 1: Stability ✅ COMPLETE (Commit: a1bff2d)

- [x] **1.1** Create `PRCache` dataclass in `apps/metrics/seeding/pr_cache.py`
- [x] **1.2** Add cache directory to `.gitignore`
- [x] **1.3** Integrate cache save into `GitHubGraphQLFetcher`
- [x] **1.4** Integrate cache load into `GitHubGraphQLFetcher`
- [x] **1.5** Add `--refresh` flag to management command
- [x] **1.6** Add `--no-cache` flag to management command
- [x] **1.7** Remove team member limit for PR creation
- [x] **1.8** Commit changes

## Phase 2: Complete Data Collection ✅ COMPLETE (Commit: c93c575)

- [x] **2.1** Add new fields to GraphQL queries
  - `isDraft` field
  - `labels(first: 10) { nodes { name color } }`
  - `milestone { title number dueOn }`
  - `assignees(first: 10) { nodes { login } }`
  - `closingIssuesReferences(first: 5) { nodes { number title } }`

- [x] **2.2** Add fields to PullRequest model (migration 0017)
  - `is_draft` BooleanField
  - `labels` JSONField (list of label names)
  - `milestone_title` CharField
  - `assignees` JSONField (list of usernames)
  - `linked_issues` JSONField (list of issue numbers)

- [x] **2.3** Update FetchedPRFull dataclass with new fields

- [x] **2.4** Update `_map_pr()` in github_graphql_fetcher.py

- [x] **2.5** Update `_create_single_pr()` in real_project_seeder.py

- [x] **2.6** Add TDD tests for Phase 2 (11 tests)

- [x] **2.7** Commit changes

## Phase 3: GitHub API Best Practices (IN PROGRESS)

### 3.0 Fix Parallel Check Runs ✅ COMPLETE
- [x] Remove `ThreadPoolExecutor` from `_add_check_runs_to_prs()`
- [x] Make requests sequential per GitHub guidelines
- [x] Add docstring reference to GitHub best practices URL
- [x] Update test names to reflect sequential behavior
- [x] Add test for sequential execution order

### 3.1 Repository Change Detection ✅ COMPLETE
- [x] Add `FETCH_REPO_METADATA_QUERY` to `github_graphql.py`
- [x] Add `fetch_repo_metadata()` method to `GitHubGraphQLClient`
- [x] Add `repo_pushed_at` field to `PRCache` dataclass
- [x] Update `PRCache.is_valid()` to accept `repo_pushed_at` parameter
- [x] Update `PRCache.save()/load()` for new field with backward compat
- [x] Add `_fetch_repo_pushed_at()` helper to `GitHubGraphQLFetcher`
- [x] Integrate repo change detection into `fetch_prs_with_details()`
- [x] Add 7 TDD tests for repo_pushed_at functionality

### 3.2 Rate Limit Monitoring ✅ COMPLETE
- [x] Track `x-ratelimit-remaining` via `_check_rest_rate_limit()` method
- [x] Log warning when remaining points drop below threshold (100)
- [x] Skip check runs fetch if not enough points remaining
- [x] Show remaining points in console output
- [x] Add 5 TDD tests for rate limit monitoring

### 3.3 Incremental PR Sync ✅ COMPLETE
- [x] Add `_fetch_updated_prs_async()` method using `FETCH_PRS_UPDATED_QUERY`
- [x] Add `_merge_prs()` method to merge cached and updated PRs
- [x] Update `fetch_prs_with_details()` to use incremental sync when cache is stale
- [x] PRs merged by number, sorted by updated_at DESC
- [x] Add 6 TDD tests for incremental sync

### 3.4 Exponential Backoff with Jitter (DEFERRED)
- [ ] Add random jitter to retry delays
- [ ] ~~Not needed for single-user seeding - thundering herd isn't a problem~~

## Phase 4: Production Alignment (PLANNED)

- [ ] **4.1** Apply Phase 1-2 improvements to production Celery tasks
- [ ] **4.2** Rate limit wait logic for single-token users
- [ ] **4.3** Better error handling and resume in sync tasks

## Phase 5: Analytics (PLANNED)

- [ ] **5.1** Filter/group PRs by label in dashboard
- [ ] **5.2** Milestone progress tracking view
- [ ] **5.3** Assignee workload analysis

## Verification Checklist

### Phase 1 (Complete)
- [x] Run seeding, interrupt, resume - uses cache
- [x] Run without --clear - loads from cache
- [x] Run with --refresh - re-fetches from GitHub
- [x] Run with --no-cache - fetches without caching
- [x] All PR authors become team members

### Phase 2 (Complete)
- [x] Labels stored in PullRequest model
- [x] Milestones stored in PullRequest model
- [x] Assignees stored in PullRequest model
- [x] Linked issues stored in PullRequest model
- [x] 43 tests passing (32 Phase 1 + 11 Phase 2)

### Phase 3 ✅ COMPLETE
- [x] Check runs fetched sequentially (not parallel) - Commit `3f1f928`
- [x] Repo metadata query costs ~1 point - Commit `3f1f928`
- [x] Cache uses `repo_pushed_at` for change detection - Commit `3f1f928`
- [x] Old cache files without `repo_pushed_at` still load - Commit `3f1f928`
- [x] Rate limit warnings logged when low - Commit `7e5094e`
- [x] Check runs skipped when rate limit too low - Commit `7e5094e`
- [x] Incremental sync fetches only updated PRs and merges with cache
- [x] **62 tests passing** (25 PRCache + 37 GitHubGraphQLFetcher)
- [~] Exponential backoff with jitter - deferred (not needed for single-user)

## Test Commands

```bash
# Run Phase 1-3 tests
.venv/bin/pytest apps/metrics/tests/test_pr_cache.py apps/metrics/tests/test_github_graphql_fetcher.py -v

# Check for missing migrations
python manage.py makemigrations --check

# Test seeding end-to-end
python manage.py seed_real_projects --project antiwork --max-prs 10 --refresh
```
