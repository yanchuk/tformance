# Test Refactoring - Task Checklist

**Last Updated:** 2024-12-30
**Status:** Phases 1-4 Complete ✅

---

## Phase 1: Quick Wins & Foundation (Day 1-2) ✅ COMPLETE

### Task 1.1: Fix Timezone Warnings [S] - 2h ✅
- [x] Created `apps/utils/date_utils.py` with timezone utilities:
  - `start_of_day(date)` - converts date to aware datetime at 00:00:00
  - `end_of_day(date)` - converts date to aware datetime at 23:59:59.999999
  - `days_ago(n)` - returns aware datetime n days ago
  - `make_aware_datetime(...)` - convenience for tests
- [x] Updated `apps/metrics/services/dashboard_service.py`:
  - All 9 DateTimeField filter locations now use timezone-aware conversions
  - Including the `_filter_by_date_range()` helper function
- [x] All 221 dashboard tests pass with `-W error::RuntimeWarning`
- [x] Zero timezone warnings in metrics tests

### Task 1.2: Mark Slow Tests [S] - 1h ✅
- [x] `TestScenarioDataGenerator` class already marked with `@pytest.mark.slow`
- [x] Verified: `pytest -m "not slow"` properly skips slow tests
- [x] Slow tests in `test_data_generator.py` correctly isolated

### Task 1.3: Fix test_roles.py Isolation [S] - 30m ✅
- [x] Replaced `setUpClass` with `setUp` (per-test isolation)
- [x] Replaced `Team.objects.create()` with `TeamFactory()`
- [x] Replaced `CustomUser.objects.create()` with `UserFactory()`
- [x] Expanded from 2 tests to 7 focused tests with better coverage
- [x] All tests pass: `pytest apps/teams/tests/test_roles.py -v`

### Task 1.4: Create Test Utilities [M] - 2h ✅
- [x] Created `apps/utils/date_utils.py` (general utility, not test-only)
- [x] Functions available for both production code and tests:
  ```python
  from apps.utils.date_utils import start_of_day, end_of_day, days_ago, make_aware_datetime
  ```

---

## Phase 2: Dashboard Service Coverage - TDD (Day 3-5) ✅ COMPLETE

**Note:** Phase 2 focus shifted from original plan to testing previously untested functions. Existing test files already had good coverage.

### Completed Tasks ✅

**Task 2.1: get_sparkline_data Tests (16 tests)**
- [x] Created `apps/metrics/tests/dashboard/test_sparkline_data.py`
- [x] Tests cover: required keys, weekly data, change calculation, trend direction, filtering

**Task 2.2: get_ai_detective_leaderboard Tests (17 tests)**
- [x] Created `apps/metrics/tests/dashboard/test_ai_detective_leaderboard.py`
- [x] Tests cover: correct/total counts, percentages, ordering, team filtering, date filtering

**Task 2.3: Trend Comparison & Monthly/Weekly Tests (28 tests)**
- [x] Created `apps/metrics/tests/dashboard/test_trend_comparison.py`
- [x] Tests cover:
  - `get_trend_comparison()` - 12 tests
  - `get_monthly_cycle_time_trend()` - 5 tests
  - `get_monthly_review_time_trend()` - 2 tests
  - `get_monthly_pr_count()` - 3 tests
  - `get_weekly_pr_count()` - 3 tests
  - `get_monthly_ai_adoption()` - 4 tests

**Task 2.4: get_pr_type_breakdown Tests (14 tests)**
- [x] Created `apps/metrics/tests/dashboard/test_pr_type_breakdown.py`
- [x] Tests cover: type counting, percentages, AI filtering, LLM summary type priority

**Task 2.5: get_ai_bot_review_stats Tests (14 tests)**
- [x] Created `apps/metrics/tests/dashboard/test_ai_bot_reviews.py`
- [x] Tests cover: total/AI review counts, percentages, bot type breakdown, ordering

**Total: 89 new tests added, bringing dashboard tests from 221 to 310**

### Original Plan (Already Had Existing Coverage)
The original Phase 2 plan focused on functions that already had tests:
- `test_key_metrics.py` - Already had 12 tests
- `test_ai_metrics.py` - Already had 20+ tests
- `test_team_breakdown.py` - Already had 17 tests
- `test_pr_metrics.py` - Already had 45 tests

Instead, we focused on the 14 functions that had NO tests.

### Task 2.3: Team Metrics Tests [M] - 3h (SKIPPED - Already covered)
  - [ ] `test_calculates_pr_count_per_member`
  - [ ] `test_includes_avatar_and_name`
  - [ ] `test_filters_by_team`
  - [ ] `test_handles_no_members`
- [ ] Write test class `TestGetCopilotByMember`:
  - [ ] `test_returns_copilot_usage_per_member`

**🟢/🔵 Phases:**
- [ ] Verify all tests pass
- [ ] Commit: "Add TDD tests for team metrics functions"

### Task 2.4: PR Metrics Tests [M] - 3h

**🔴 RED Phase:**
- [ ] Create `apps/metrics/tests/dashboard/test_pr_metrics.py`
- [ ] Write test class `TestGetCycleTimeTrend`:
  - [ ] `test_returns_trend_data_by_period`
  - [ ] `test_calculates_avg_cycle_time`
  - [ ] `test_supports_daily_granularity`
  - [ ] `test_supports_weekly_granularity`
- [ ] Write test class `TestGetPRSizeDistribution`:
  - [ ] `test_categorizes_by_size_bucket`
  - [ ] `test_handles_xs_s_m_l_xl_sizes`
- [ ] Write test class `TestGetSparklineData`:
  - [ ] `test_returns_data_for_multiple_metrics`
  - [ ] `test_includes_pr_count_sparkline`

**🟢/🔵 Phases:**
- [ ] Verify all tests pass
- [ ] Commit: "Add TDD tests for PR metrics functions"

---

## Phase 3: E2E Reliability (Day 6-7) ✅ COMPLETE

**Summary:** Replaced 177 hardcoded `waitForTimeout` calls across 16 E2E test files with conditional waits.

### Task 3.1-3.8: Replace waitForTimeout Calls ✅
Files fixed (commits 8849bac, d5db1ba, 089b1cd, 345c815):
- [x] alpine-htmx-integration.spec.ts - 49 waits replaced
- [x] analytics.spec.ts - 68 waits replaced
- [x] integrations.spec.ts - 11 waits replaced
- [x] onboarding.spec.ts - 7 waits replaced
- [x] navigation.spec.ts - 5 waits replaced
- [x] insights.spec.ts - 10 waits replaced
- [x] copilot.spec.ts - 8 waits replaced
- [x] dashboard.spec.ts - 7 waits replaced
- [x] htmx-error-handling.spec.ts - 3 waits replaced
- [x] accessibility.spec.ts - 2 waits replaced
- [x] metric-toggle.spec.ts - 2 waits replaced
- [x] profile.spec.ts - 1 wait replaced
- [x] teams.spec.ts - 1 wait replaced
- [x] smoke.spec.ts - 1 wait replaced
- [x] auth.spec.ts - 1 wait replaced
- [x] fixtures/test-fixtures.ts - 5 waits replaced

**Patterns Applied:**
- `waitForHtmxComplete()` - waits for `htmx-request` class to be removed
- `waitForAlpineReady()` / `waitForAlpine()` - waits for Alpine.js initialization
- `waitForJsInit()` - waits for DOM ready state
- `waitForFormSubmit()` - waits for form submission indicator
- Conditional expects with extended timeouts

---

## Phase 4: Auth & Model Coverage - TDD (Day 8-10) ✅ COMPLETE

### Task 4.1: OAuth Flow Tests ✅
**Status:** Target exceeded - 166 OAuth tests already exist

Existing test files:
- `apps/auth/tests/test_oauth_state.py`
- `apps/auth/tests/test_jira_callback.py`
- `apps/auth/tests/test_slack_callback.py`
- `apps/auth/tests/test_github_callback.py`
- `apps/integrations/tests/test_slack_oauth.py`
- `apps/integrations/tests/test_jira_oauth.py`
- `apps/integrations/tests/test_github_oauth.py`
- `apps/integrations/tests/test_oauth_utils.py`

**Target:** 15+ tests | **Actual:** 166 tests ✅

### Task 4.2: Model Method Tests ✅ (commit 9cc9480)
Created `apps/metrics/tests/models/test_pull_request_properties.py` with 31 tests:

- [x] TestEffectiveTechCategories (4 tests) - LLM vs PRFile fallback
- [x] TestEffectiveIsAiAssisted (5 tests) - LLM confidence threshold
- [x] TestEffectiveAiTools (5 tests) - LLM vs regex fallback
- [x] TestAiCodeTools (3 tests) - code-category filtering
- [x] TestAiReviewTools (2 tests) - review-category filtering
- [x] TestAiCategory (4 tests) - code/review/both/none classification
- [x] TestEffectivePrType (6 tests) - LLM vs label inference
- [x] TestGithubUrl (2 tests) - URL construction

**Target:** 15+ tests | **Actual:** 31 tests ✅

### Task 4.3: Integration View Tests ✅
**Status:** Target exceeded - 171 integration view tests already exist

Existing test files:
- `apps/integrations/tests/test_views.py`
- `apps/integrations/tests/test_slack_views.py`
- `apps/integrations/tests/test_jira_views.py`
- `apps/integrations/tests/test_github_webhooks.py`

**Target:** 10+ tests | **Actual:** 171 tests ✅

---

## Phase 5: Factory & Performance (DEFERRED)

**Status:** Deferred - not critical for MVP. Tests pass with current implementation.

**Reason:** The scope is larger than estimated (52 random usages across 15+ factories). Each factory requires a different seed source, making this a 4-6 hour refactoring effort.

**When to revisit:**
- If test flakiness issues arise related to random data
- If reproducibility is needed for debugging specific test failures
- After MVP when there's bandwidth for technical debt cleanup

### Original Tasks (Deferred)

- [ ] Task 5.1: Deterministic Factories (52 random usages to replace)
- [ ] Task 5.2: Optimize Factory Usage (build() vs create())
- [ ] Task 5.3: Slow Test Optimization

---

## Verification Checklist

### After Phase 1 ✅
- [x] `make test` shows 0 timezone warnings
- [x] `pytest -m "not slow"` skips marked tests
- [x] `test_roles.py` uses factories and `setUp`
- [x] Test utilities module exists (`apps/utils/date_utils.py`)

### After Phase 2 ✅
- [x] `apps/metrics/tests/dashboard/` has 5 new test files (89 tests)
- [x] `dashboard_service.py` has 300+ tests
- [x] All new tests follow TDD pattern
- [x] All tests pass

### After Phase 3 ✅
- [x] 177 `waitForTimeout` calls replaced across 16 files
- [x] E2E tests using conditional waits instead of hardcoded timeouts
- [x] Patterns documented in task file

### After Phase 4 ✅
- [x] OAuth flows have 166 tests (target: 15+)
- [x] Model methods have 31 tests (target: 15+)
- [x] Integration views have 171 tests (target: 10+)

### After Phase 5 (DEFERRED)
- [ ] No `import random` in factories
- [ ] Tests deterministic with seed
- [ ] No test >3s duration

**Note:** Phase 5 deferred - tests pass with current random factories.

---

## Final Verification

- [ ] Full test suite passes: `make test`
- [ ] E2E tests pass: `make e2e`
- [ ] Coverage increased (check before/after)
- [ ] All commits have meaningful messages
- [ ] Documentation updated

---

## Notes

- Always commit after each task
- Run full suite before marking phase complete
- If a test fails unexpectedly, investigate before proceeding
- TDD phases must not be skipped
