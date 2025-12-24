# Fix Slow Incremental Tests - Context

**Last Updated: 2025-12-22**

## Key Files

| File | Purpose |
|------|---------|
| `apps/integrations/tests/github_sync/test_repository_sync.py` | Test file containing slow tests |
| `apps/integrations/services/github_sync.py` | Source module being tested |
| `conftest.py` | Root pytest fixtures |

## Test Class Location

```
apps/integrations/tests/github_sync/test_repository_sync.py
├── TestSyncRepositoryHistory (already fixed)
└── TestSyncRepositoryIncremental (needs fixing - lines 931-1265)
```

## Sync Functions to Mock

These functions are called during PR sync and need to be mocked:

```python
# From apps/integrations/services/github_sync.py
sync_pr_commits(token, repo, pr_number, pr_obj) -> int
sync_pr_check_runs(token, repo, pr_obj) -> int
sync_pr_files(token, repo, pr_number, pr_obj) -> int
sync_pr_issue_comments(token, repo, pr_number, pr_obj) -> int
sync_pr_review_comments(token, repo, pr_number, pr_obj) -> int
sync_repository_deployments(token, repo, tracked_repo) -> int
_sync_pr_reviews(token, repo, pr_number, pr_obj) -> int
get_pull_request_reviews(token, repo, pr_number) -> list
```

## Mock Pattern (from fixed history tests)

```python
@patch("apps.integrations.services.github_sync.sync_repository_deployments")
@patch("apps.integrations.services.github_sync.sync_pr_review_comments")
@patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
@patch("apps.integrations.services.github_sync.sync_pr_files")
@patch("apps.integrations.services.github_sync.sync_pr_check_runs")
@patch("apps.integrations.services.github_sync.sync_pr_commits")
@patch("apps.integrations.services.github_sync._sync_pr_reviews")
@patch("apps.integrations.services.github_sync.get_updated_pull_requests")
def test_xxx(
    self,
    mock_get_updated_prs,
    mock_reviews,
    mock_commits,
    mock_checks,
    mock_files,
    mock_issues,
    mock_review_comments,
    mock_deployments,
):
    # Mock all sync functions to return 0
    mock_reviews.return_value = 0
    mock_commits.return_value = 0
    mock_checks.return_value = 0
    mock_files.return_value = 0
    mock_issues.return_value = 0
    mock_review_comments.return_value = 0
    mock_deployments.return_value = 0
    # ... rest of test
```

## Tests to Fix

### Non-Review Tests (mock `_sync_pr_reviews`)
1. `test_sync_repository_incremental_creates_new_pull_requests` (line 1013)
2. `test_sync_repository_incremental_updates_existing_pull_requests` (line 1055)
3. `test_sync_repository_incremental_returns_correct_summary_dict` (line 1155)
4. `test_sync_repository_incremental_handles_individual_pr_errors_gracefully` (line 1207)

### Review Tests (mock subfunctions but NOT `_sync_pr_reviews`)
5. `test_sync_repository_incremental_syncs_reviews_for_each_updated_pr` (line 1107)
6. `test_sync_repository_incremental_creates_review_records` (line 1167)

## Related Work

- pytest migration commit: `f8feefa`
- Pre-push hook fix: `329a497`
- `TestSyncRepositoryHistory` fixes applied in same commit

## Commands

```bash
# Run just the incremental tests
pytest apps/integrations/tests/github_sync/test_repository_sync.py::TestSyncRepositoryIncremental -v

# Check timings
pytest apps/integrations/tests/github_sync/test_repository_sync.py --durations=20 -q

# Full test suite
make test
```
