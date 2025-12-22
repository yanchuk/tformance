# GitHub API Best Practices Compliance - Plan

**Last Updated:** 2025-12-22

## Executive Summary

This plan addresses critical violations of GitHub's REST API best practices that are causing rate limit issues (403 Forbidden errors) during data seeding and sync operations. The primary issues are:

1. **Concurrent requests** triggering GitHub's abuse detection
2. **Missing `retry-after` header handling** for secondary rate limits
3. **No point-based request tracking** (GET=1pt, POST=5pts, max 900pts/min)
4. **Missing conditional requests** (ETags) for optimization

The goal is to make all GitHub API operations compliant with GitHub's documented best practices to eliminate 403 errors and improve reliability.

## Current State Analysis

### Problem Areas Identified

| Issue | Severity | Location | Impact |
|-------|----------|----------|--------|
| Parallel requests via ThreadPoolExecutor | Critical | `github_authenticated_fetcher.py:675-676, 757-763` | Triggers 403 abuse detection |
| No retry-after header parsing | High | `github_authenticated_fetcher.py:573-582` | Suboptimal backoff timing |
| No point-based rate tracking | Medium | All GitHub API code | Risk of hitting 900pts/min limit |
| No ETag/conditional requests | Low | All sync operations | Wastes rate limit quota |

### Current Architecture

```
github_authenticated_fetcher.py (Seeding)
├── _fetch_prs_parallel()     # Uses ThreadPoolExecutor - VIOLATES best practices
├── _fetch_batch_with_retry() # Uses ThreadPoolExecutor - VIOLATES best practices
├── _fetch_pr_details()       # Uses ThreadPoolExecutor for sub-requests - VIOLATES
└── _fetch_prs_sequential()   # Correct serial approach - EXISTS but unused by default

github_sync.py (Production)
├── sync_repository_history()      # Serial, but no point tracking
├── sync_repository_incremental()  # Serial, but no ETag support
└── _process_prs()                 # Has basic error handling

github_rate_limit.py (Utilities)
├── check_rate_limit()       # Makes extra API call
├── should_pause_for_rate_limit()  # Threshold-based check
└── wait_for_rate_limit_reset()    # Wait utility
```

## Proposed Future State

### New Architecture

```
github_request_queue.py (NEW)
├── GitHubRequestQueue class
│   ├── request()           # Serial request with point tracking
│   ├── _track_points()     # Track 900pts/min budget
│   ├── _handle_response()  # Parse rate limit headers
│   └── _wait_if_needed()   # Respect retry-after

github_authenticated_fetcher.py (MODIFIED)
├── _fetch_prs_serial()     # Renamed from sequential, now default
├── _fetch_pr_details()     # Remove ThreadPoolExecutor, use queue
└── Remove _fetch_prs_parallel(), _fetch_batch_with_retry()

github_sync.py (MODIFIED)
├── Use GitHubRequestQueue for all operations
└── Add ETag caching for incremental syncs

github_rate_limit.py (ENHANCED)
├── parse_rate_limit_headers()   # Extract from response headers
├── get_retry_after()            # Parse retry-after header
└── RateLimitBudget class        # Track points per minute
```

## Implementation Phases

### Phase 1: Create Request Queue Infrastructure (Priority: Critical)

Create a centralized request queue that enforces serial execution and tracks rate limits.

**Rationale:** This is the foundation for all other fixes. Without it, we can't properly enforce GitHub's best practices.

### Phase 2: Refactor Seeding Fetcher (Priority: Critical)

Remove all `ThreadPoolExecutor` usage from `github_authenticated_fetcher.py` and use serial requests.

**Rationale:** This is the direct cause of the 403 errors we're seeing.

### Phase 3: Enhance Rate Limit Handling (Priority: High)

Add proper `retry-after` header parsing and response header tracking.

**Rationale:** Improves reliability and reduces unnecessary waiting.

### Phase 4: Add Point-Based Budget Tracking (Priority: Medium)

Implement tracking for the 900 points/minute secondary rate limit.

**Rationale:** Prevents hitting secondary limits proactively.

### Phase 5: Implement Conditional Requests (Priority: Low)

Add ETag support for sync operations to reduce API quota usage.

**Rationale:** Optimization that saves rate limit quota for unchanged data.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Seeding becomes slower | High | Medium | Accept slower speed for reliability; can run overnight |
| Breaking existing sync operations | Medium | High | Comprehensive tests; feature flag for rollout |
| Complex refactoring causes bugs | Medium | Medium | TDD approach; incremental changes |
| ETag storage adds DB complexity | Low | Low | Defer Phase 5 if needed |

## Success Metrics

1. **Zero 403 errors** during normal seeding operations
2. **100% compliance** with GitHub best practices checklist
3. **All tests pass** including new rate limit tests
4. **Seeding completes** for all projects without manual intervention

## Required Resources and Dependencies

### Dependencies
- No new external packages required
- PyGithub already handles most low-level details

### Files to Modify
1. `apps/metrics/seeding/github_authenticated_fetcher.py` (major changes)
2. `apps/metrics/seeding/github_token_pool.py` (minor changes)
3. `apps/integrations/services/github_rate_limit.py` (enhancements)
4. `apps/integrations/services/github_sync.py` (adopt queue)

### Files to Create
1. `apps/integrations/services/github_request_queue.py` (new)

### Test Files
1. `apps/metrics/tests/test_github_request_queue.py` (new)
2. Updates to existing fetcher tests
