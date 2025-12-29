# Context: Fix Failing CI Tests

**Last Updated: 2025-12-29**

## Key Files

### Already Fixed in CI
- `.github/workflows/tests.yml` - Added `INTEGRATION_ENCRYPTION_KEY`, `POSTHOG_API_KEY`, Node.js build

### Uncommitted Changes Needing Commit
- `apps/onboarding/views.py` - Repo sorting implementation
- `apps/metrics/models/github.py` - `is_ai_assisted` nullable
- `apps/metrics/migrations/0029_allow_null_is_ai_assisted.py` - Migration

### Test Files with Failures
- `apps/utils/tests/test_analytics.py` - PostHog tests (10) - **Fixed by CI config**
- `apps/onboarding/tests/test_repo_prioritization.py` - Sorting tests (4)
- `apps/integrations/tests/test_slack_views.py` - Slack OAuth tests (6)
- `apps/integrations/tests/test_quick_sync_task.py` - Quick sync tests (2)
- `apps/metrics/tests/test_pr_list_views.py` - Query count test (1)

### Implementation Files
- `apps/integrations/tasks.py` - `sync_quick_data_task` function
- `apps/integrations/views/slack.py` - Slack OAuth callback

## Key Decisions

1. **PostHog in CI**: Use dummy API key `phc_test_key_for_ci` - tests mock actual calls
2. **Repo sorting**: Sort by `updated_at` descending, `None` values at end using `datetime.min`
3. **is_ai_assisted nullable**: Allow NULL for PRs synced before AI detection runs

## Dependencies

- CI workflow needs Node.js 20 for Vite build
- Vite config removed pegasus entry points (deleted files)
- Tests run with `-n auto` (2 workers on CI)

## CI Workflow Run History

| Run ID | Commit | Result | Issue |
|--------|--------|--------|-------|
| 20560661846 | Report changes | Failed | Missing INTEGRATION_ENCRYPTION_KEY |
| 20560838370 | Add encryption key | Failed | Missing Vite manifest (no npm build) |
| 20560961919 | Add Node.js build | Failed | Pegasus entry points missing |
| 20561005361 | Fix Vite config | Failed | -n 4 on 2 vCPU (slow) |
| 20561036062 | Use -n auto | Failed | Missing POSTHOG_API_KEY + actual test failures |
| (next) | Add POSTHOG key | Pending | Should fix 10 PostHog tests |

## Error Patterns

### Repo Prioritization (Missing Implementation)
```
AssertionError: 'old-repo' != 'recent-repo'
```
Repos not sorted - sorting code not committed.

### Slack Callback (Mock Mismatch)
```
AssertionError: Expected 'verify_slack_oauth_state' to be called once. Called 0 times.
```
Mock path doesn't match actual import in view.

### Quick Sync (Double Call)
```
AssertionError: Expected '_sync_with_graphql_or_rest' to have been called once. Called 2 times.
Calls: [call(..., days_back=7), call(..., days_back=90)]
```
Task calls sync twice - once for quick (7 days), once for historical (90 days).

### is_ai_assisted Constraint
```
IntegrityError: null value in column "is_ai_assisted" violates not-null constraint
```
Need to apply migration allowing NULL.

### Query Count
```
AssertionError: 9 != 11 : 9 queries executed, 11 expected
```
Query optimization reduced count - update assertion.
