# GitHub API Best Practices Compliance - Tasks

**Last Updated:** 2025-12-22

## Phase 1: Create Request Queue Infrastructure

- [x] **1.1** Create `github_request_queue.py` with basic structure
  - File: `apps/integrations/services/github_request_queue.py`
  - Class: `GitHubRequestQueue` with `request()` method
  - Ensure serial execution (no concurrency)
  - Effort: M

- [x] **1.2** Add rate limit header parsing
  - Parse `x-ratelimit-remaining`, `x-ratelimit-reset` from responses
  - Store in queue state
  - Effort: S

- [x] **1.3** Add `retry-after` header handling
  - Parse `retry-after` header from 403/429 responses
  - Wait specified duration before retry
  - Effort: S

- [x] **1.4** Write tests for request queue
  - File: `apps/integrations/tests/test_github_request_queue.py`
  - Test serial execution
  - Test retry-after parsing
  - Test header extraction
  - Effort: M

## Phase 2: Refactor Seeding Fetcher (Critical)

- [x] **2.1** Remove `ThreadPoolExecutor` from `_fetch_batch_with_retry()`
  - File: `apps/metrics/seeding/github_authenticated_fetcher.py`
  - Removed entire method (replaced by serial `_fetch_prs()`)
  - Effort: M

- [x] **2.2** Remove `ThreadPoolExecutor` from `_fetch_pr_details()`
  - File: `apps/metrics/seeding/github_authenticated_fetcher.py`
  - Now fetches commits, reviews, files, check_runs serially
  - Effort: M

- [x] **2.3** Remove `_fetch_prs_parallel()` method entirely
  - File: `apps/metrics/seeding/github_authenticated_fetcher.py`
  - Method completely removed
  - Effort: S

- [x] **2.4** Rename `_fetch_prs_sequential()` to `_fetch_prs()`
  - File: `apps/metrics/seeding/github_authenticated_fetcher.py`
  - Now the default (and only) implementation
  - Enhanced with progress reporting and checkpoint support
  - Effort: S

- [x] **2.5** Update tests for refactored fetcher
  - File: `apps/metrics/tests/test_github_authenticated_fetcher.py`
  - All 27 tests pass with serial implementation
  - Effort: S

- [x] **2.6** Test seeding with small dataset
  - All 173 GitHub-related tests pass
  - Import validation successful
  - Effort: S

## Phase 3: Enhance Rate Limit Handling

- [ ] **3.1** Add `parse_rate_limit_headers()` to `github_rate_limit.py`
  - File: `apps/integrations/services/github_rate_limit.py`
  - Extract all rate limit headers from response
  - Return structured dict
  - Effort: S

- [ ] **3.2** Add `get_retry_after()` function
  - File: `apps/integrations/services/github_rate_limit.py`
  - Parse retry-after from exception or response
  - Handle both seconds and date formats
  - Effort: S

- [ ] **3.3** Update token pool to track headers from responses
  - File: `apps/metrics/seeding/github_token_pool.py`
  - Update remaining/reset from actual API responses
  - Don't rely solely on separate API calls
  - Effort: M

- [ ] **3.4** Write tests for new rate limit functions
  - File: `apps/integrations/tests/test_github_rate_limit.py`
  - Test header parsing
  - Test retry-after handling
  - Effort: S

## Phase 4: Add Point-Based Budget Tracking

- [ ] **4.1** Create `RateLimitBudget` class
  - File: `apps/integrations/services/github_rate_limit.py`
  - Track points used per minute (GET=1, POST=5)
  - Max 900 points/minute
  - Effort: M

- [ ] **4.2** Integrate budget tracking with request queue
  - File: `apps/integrations/services/github_request_queue.py`
  - Check budget before each request
  - Wait if approaching limit
  - Effort: M

- [ ] **4.3** Add 1-second delay for mutative requests
  - Apply to POST, PATCH, PUT, DELETE
  - Per GitHub best practices
  - Effort: S

- [ ] **4.4** Write tests for budget tracking
  - Test point calculation
  - Test minute window reset
  - Test wait behavior
  - Effort: S

## Phase 5: Implement Conditional Requests (Optional)

- [ ] **5.1** Add `etag` field to TrackedRepository model
  - File: `apps/integrations/models.py`
  - Migration needed
  - Effort: S

- [ ] **5.2** Store ETags from responses
  - Update after successful sync
  - Effort: S

- [ ] **5.3** Send `If-None-Match` header on requests
  - Skip processing if 304 Not Modified
  - Effort: M

- [ ] **5.4** Write tests for conditional requests
  - Test ETag storage
  - Test 304 handling
  - Effort: S

## Verification

- [ ] **V.1** Run full Polar seeding without errors
  - Command: `python scripts/seed_with_progress.py --project polar --clear`
  - Expected: Completes without 403 errors
  - Effort: M (time)

- [ ] **V.2** Run full test suite
  - Command: `make test`
  - All tests pass
  - Effort: S

- [ ] **V.3** Manual code review against checklist
  - No ThreadPoolExecutor in GitHub code
  - All requests use queue
  - retry-after respected
  - Effort: S

## Notes

- Phase 1-2 are **COMPLETED** - ThreadPoolExecutor removed, serial execution enforced
- Phase 3-4 are **important** for robustness (pending)
- Phase 5 is **optional** optimization (deferred)
- Accept slower seeding speed (~30-60 min vs 10 min) for reliability
- Can run seeding overnight if needed
