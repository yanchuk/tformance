# Fix Slow Incremental Sync Tests

**Last Updated: 2025-12-22**
**Status: In Progress**

## Executive Summary

The `TestSyncRepositoryIncremental` test class contains 6 tests that take 1.7-3.3 seconds each due to missing mocks for sync subfunctions. These tests only mock `get_updated_pull_requests` but don't mock the sync subfunctions (`sync_pr_commits`, `sync_pr_files`, etc.) that get called during PR processing.

This is a follow-up to the pytest migration work where we already fixed slow tests in `TestSyncRepositoryHistory` (18.8s → 0.69s).

## Current State Analysis

### Slow Tests Identified

| Test | Current Time | Target |
|------|-------------|--------|
| `test_sync_repository_incremental_returns_correct_summary_dict` | 3.30s | <0.5s |
| `test_sync_repository_incremental_syncs_reviews_for_each_updated_pr` | 2.92s | <0.5s |
| `test_sync_repository_incremental_handles_individual_pr_errors_gracefully` | 2.26s | <0.5s |
| `test_sync_repository_incremental_creates_review_records` | 1.93s | <0.5s |
| `test_sync_repository_incremental_updates_existing_pull_requests` | 1.71s | <0.5s |
| `test_sync_repository_incremental_creates_new_pull_requests` | 1.70s | <0.5s |

### Root Cause

The `sync_repository_incremental` function calls these subfunctions for each PR:
- `sync_pr_commits`
- `sync_pr_check_runs`
- `sync_pr_files`
- `sync_pr_issue_comments`
- `sync_pr_review_comments`
- `sync_repository_deployments`
- `_sync_pr_reviews` (or `get_pull_request_reviews`)

Tests only mock the top-level API call but not these subfunctions, causing slow execution.

## Proposed Solution

Add comprehensive mocks using the same pattern applied to `TestSyncRepositoryHistory`:

```python
@patch("apps.integrations.services.github_sync.sync_repository_deployments")
@patch("apps.integrations.services.github_sync.sync_pr_review_comments")
@patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
@patch("apps.integrations.services.github_sync.sync_pr_files")
@patch("apps.integrations.services.github_sync.sync_pr_check_runs")
@patch("apps.integrations.services.github_sync.sync_pr_commits")
@patch("apps.integrations.services.github_sync._sync_pr_reviews")  # or get_pull_request_reviews
@patch("apps.integrations.services.github_sync.get_updated_pull_requests")
def test_xxx(self, mock_get_prs, mock_reviews, mock_commits, ...):
    # Mock all sync functions to return 0
    mock_reviews.return_value = 0
    mock_commits.return_value = 0
    # ... etc
```

## Implementation Phases

### Phase 1: Fix Non-Review Tests
Tests that don't test review functionality need all sync mocks including `_sync_pr_reviews`:
- `test_sync_repository_incremental_creates_new_pull_requests`
- `test_sync_repository_incremental_updates_existing_pull_requests`
- `test_sync_repository_incremental_returns_correct_summary_dict`
- `test_sync_repository_incremental_handles_individual_pr_errors_gracefully`

### Phase 2: Fix Review Tests
Tests that test review functionality need all sync mocks EXCEPT `_sync_pr_reviews` (but keep `get_pull_request_reviews` mock):
- `test_sync_repository_incremental_syncs_reviews_for_each_updated_pr`
- `test_sync_repository_incremental_creates_review_records`

### Phase 3: Verify and Commit
- Run full test suite
- Verify timing improvements
- Commit changes

## Success Metrics

- All 6 incremental tests complete in <0.5s each
- Total file test time reduced from ~19s to <5s
- All 2035 tests still pass
- Parallel test execution time reduced

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking test assertions | Low | Medium | Run tests after each change |
| Missing a mock | Low | Low | Pattern is well-established from history tests |

## Dependencies

- pytest migration already complete
- `TestSyncRepositoryHistory` fixes already applied (reference pattern)
