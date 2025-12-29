# Tasks: Fix Failing CI Tests

**Last Updated: 2025-12-29**

## Phase 1: Commit Missing Implementation (4 tests)

- [ ] 1.1 Commit `apps/onboarding/views.py` with repo sorting code
  - File: `apps/onboarding/views.py` line 287-288
  - Effort: S
  - Fixes: 4 repo prioritization tests

## Phase 2: Apply Migration (1 test)

- [ ] 2.1 Commit `apps/metrics/models/github.py` with is_ai_assisted nullable change
  - Effort: S

- [ ] 2.2 Commit migration `apps/metrics/migrations/0029_allow_null_is_ai_assisted.py`
  - Effort: S
  - Fixes: `test_prs_have_is_ai_assisted_set_after_quick_sync`

## Phase 3: Fix Slack Callback Tests (6 tests)

- [ ] 3.1 Investigate Slack callback view implementation
  - File: `apps/integrations/views/slack.py`
  - Check actual OAuth flow vs what tests expect
  - Effort: M

- [ ] 3.2 Update test mocks to match actual implementation OR fix view
  - Option A: Update `@patch` decorators to correct import paths
  - Option B: Ensure view calls `verify_slack_oauth_state`
  - Effort: M
  - Fixes: 6 Slack callback tests

## Phase 4: Fix Quick Sync Task (1 test)

- [ ] 4.1 Investigate why `_sync_with_graphql_or_rest` called twice
  - File: `apps/integrations/tasks.py` - `sync_quick_data_task`
  - Effort: M

- [ ] 4.2 Update task logic OR update test expectation
  - If calling twice is intentional, update test
  - If bug, fix task to call once with days_back=7
  - Effort: M
  - Fixes: `test_sync_quick_data_task_syncs_only_7_days`

## Phase 5: Update Query Count Assertion (1 test)

- [ ] 5.1 Update expected query count from 11 to 9
  - File: `apps/metrics/tests/test_pr_list_views.py`
  - Find `test_export_query_count_is_constant`
  - Effort: S
  - Fixes: `test_export_query_count_is_constant`

## Summary

| Phase | Tests Fixed | Effort |
|-------|-------------|--------|
| 1 | 4 | S |
| 2 | 1 | S |
| 3 | 6 | M |
| 4 | 1 | M |
| 5 | 1 | S |
| **Total** | **13** | - |

Note: 10 PostHog tests already fixed by adding `POSTHOG_API_KEY` to CI.
