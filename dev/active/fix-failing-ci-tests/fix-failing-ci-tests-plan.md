# Plan: Fix Failing CI Tests

**Last Updated: 2025-12-29**

## Executive Summary

The CI pipeline has 23 failing tests across 5 categories. Most are caused by missing configuration, uncommitted code changes, or tests expecting features not yet fully implemented.

## Current State Analysis

### Test Failure Breakdown (23 total)

| Category | Count | Root Cause | Fix Type |
|----------|-------|------------|----------|
| PostHog analytics | 10 | Missing `POSTHOG_API_KEY` in CI | ✅ Fixed (pushed) |
| Repo prioritization | 4 | Sorting code not committed | Commit local change |
| Slack callback | 6 | Tests mock wrong path / view changes | Update tests or views |
| Quick sync task | 2 | Sync logic called twice + migration | Fix logic + apply migration |
| PR export query count | 1 | Query optimization improved | Update expected count |

### Files with Uncommitted Changes

```
 M apps/onboarding/views.py       <- Repo sorting implementation
 M apps/metrics/models/github.py  <- PullRequest.is_ai_assisted nullable change
?? apps/metrics/migrations/0029_allow_null_is_ai_assisted.py <- Migration
```

## Proposed Solution

### Phase 1: Commit Missing Implementation (Immediate)

The repo prioritization sorting code exists locally but wasn't committed with the tests:

```python
# apps/onboarding/views.py line 287-288
# Sort repos by updated_at descending (most recent first), None values at end
repos = sorted(repos, key=lambda r: r.get("updated_at") or datetime.min.replace(tzinfo=UTC), reverse=True)
```

**Action**: Commit this change.

### Phase 2: Apply Migration for is_ai_assisted Nullable (Immediate)

The quick sync test fails because `is_ai_assisted` column has NOT NULL constraint but the migration to allow NULL hasn't been applied.

**Action**: Commit and run migration `0029_allow_null_is_ai_assisted.py`.

### Phase 3: Fix Slack Callback Tests (Medium Priority)

The Slack callback tests are failing because:
1. Mocks target wrong path (`apps.integrations.services.slack_oauth.verify_slack_oauth_state`)
2. View may have changed to use different OAuth flow

**Options**:
- Option A: Update tests to match current implementation
- Option B: Fix implementation if OAuth flow is broken

### Phase 4: Fix Quick Sync 7-Day Logic (Medium Priority)

Test expects `_sync_with_graphql_or_rest` called once with `days_back=7`, but it's called twice.

**Investigation needed**: Check `sync_quick_data_task` to see why it calls sync twice.

### Phase 5: Update Query Count Assertion (Low Priority)

`test_export_query_count_is_constant` expects 11 queries but only 9 are executed. This is actually an improvement.

**Action**: Update test to expect 9 queries.

## Implementation Order

1. Commit `apps/onboarding/views.py` changes (fixes 4 tests)
2. Commit migration and model changes (fixes 1 test)
3. Fix Slack callback tests (fixes 6 tests)
4. Fix quick sync task logic (fixes 1 test)
5. Update query count assertion (fixes 1 test)

PostHog tests (10) already fixed by CI config push.

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Slack OAuth flow broken | High | Test manually before fixing tests |
| Quick sync calls wrong API | Medium | Review task implementation |
| Query count assertion brittle | Low | Consider using range or <= assertion |

## Success Metrics

- All 23 tests passing in CI
- No regressions in existing functionality
- Clean git status with all changes committed
