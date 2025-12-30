# Test Refactoring - Task Checklist

**Last Updated:** 2024-12-30
**Status:** Phase 1 Complete ✅

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

## Phase 2: Dashboard Service Coverage - TDD (Day 3-5)

### Task 2.1: Key Metrics Tests [L] - 4h

**🔴 RED Phase:**
- [ ] Create `apps/metrics/tests/dashboard/test_key_metrics.py`
- [ ] Write test class `TestGetKeyMetrics`:
  - [ ] `test_returns_dict_with_required_keys`
  - [ ] `test_calculates_prs_merged_count`
  - [ ] `test_calculates_avg_cycle_time`
  - [ ] `test_filters_by_date_range`
  - [ ] `test_filters_by_team`
  - [ ] `test_handles_empty_data_returns_zeros`
  - [ ] `test_calculates_trend_vs_previous_period`
  - [ ] `test_uses_cache_when_available`
- [ ] Run tests - all MUST fail (function may already exist)

**🟢 GREEN Phase:**
- [ ] Verify implementation satisfies all tests
- [ ] All tests pass

**🔵 REFACTOR Phase:**
- [ ] Review test quality
- [ ] Add edge case tests if gaps found
- [ ] Commit: "Add TDD tests for get_key_metrics()"

### Task 2.2: AI Metrics Tests [L] - 4h

**🔴 RED Phase:**
- [ ] Create `apps/metrics/tests/dashboard/test_ai_metrics.py`
- [ ] Write test class `TestGetAIAdoptionTrend`:
  - [ ] `test_returns_list_of_monthly_data`
  - [ ] `test_calculates_ai_percentage_correctly`
  - [ ] `test_handles_no_ai_assisted_prs`
  - [ ] `test_handles_all_ai_assisted_prs`
  - [ ] `test_filters_by_team`
- [ ] Write test class `TestGetAIToolBreakdown`:
  - [ ] `test_groups_by_tool_name`
  - [ ] `test_calculates_tool_counts`
  - [ ] `test_handles_empty_tools_list`
- [ ] Write test class `TestGetAIQualityComparison`:
  - [ ] `test_compares_ai_vs_non_ai_quality`
  - [ ] `test_calculates_review_time_difference`
- [ ] Run tests - verify failures

**🟢 GREEN Phase:**
- [ ] Verify implementation satisfies all tests
- [ ] All tests pass

**🔵 REFACTOR Phase:**
- [ ] Commit: "Add TDD tests for AI metrics functions"

### Task 2.3: Team Metrics Tests [M] - 3h

**🔴 RED Phase:**
- [ ] Create `apps/metrics/tests/dashboard/test_team_metrics.py`
- [ ] Write test class `TestGetTeamBreakdown`:
  - [ ] `test_returns_list_of_member_stats`
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

## Phase 3: E2E Reliability (Day 6-7)

### Task 3.1: Audit waitForTimeout [S] - 1h
- [ ] Run: `grep -rn "waitForTimeout" tests/e2e/*.spec.ts | wc -l`
- [ ] Create list of all occurrences by file
- [ ] Categorize each:
  - **Required:** Network operations, animations
  - **Avoidable:** UI elements, HTMX responses
  - **Unnecessary:** Defensive waits
- [ ] Commit: audit results to `dev/active/test-refactoring/e2e-waits-audit.md`

### Task 3.2: Fix alpine-htmx-integration.spec.ts [M] - 2h
- [ ] Read file and identify all `waitForTimeout` calls
- [ ] Replace each with appropriate conditional wait:
  ```typescript
  // Instead of: await page.waitForTimeout(2000);
  // Use: await expect(element).toBeVisible({ timeout: 5000 });
  ```
- [ ] Run tests 3 times to verify stability:
  - [ ] Run 1: Pass
  - [ ] Run 2: Pass
  - [ ] Run 3: Pass
- [ ] Commit: "Replace hardcoded waits in alpine-htmx-integration.spec.ts"

### Task 3.3: Fix analytics.spec.ts [L] - 3h
- [ ] List all `waitForTimeout` calls (largest file)
- [ ] Replace each systematically:
  - [ ] Section 1: Overview tests
  - [ ] Section 2: Tab navigation tests
  - [ ] Section 3: Chart loading tests
  - [ ] Section 4: Filter tests
- [ ] Keep only truly necessary waits (with comments)
- [ ] Run tests 3 times:
  - [ ] Run 1: Pass
  - [ ] Run 2: Pass
  - [ ] Run 3: Pass
- [ ] Commit: "Replace hardcoded waits in analytics.spec.ts"

### Task 3.4: Create E2E Best Practices Guide [S] - 1h
- [ ] Create `tests/e2e/README.md` with:
  - [ ] Wait patterns (when to use each)
  - [ ] Selector strategies
  - [ ] Reliability tips
  - [ ] Example transformations
- [ ] Add reference in CLAUDE.md E2E section
- [ ] Commit: "Add E2E testing best practices guide"

---

## Phase 4: Auth & Model Coverage - TDD (Day 8-10)

### Task 4.1: OAuth Flow Tests [L] - 6h

**🔴 RED Phase:**
- [ ] Create `apps/auth/tests/test_oauth_views.py`
- [ ] Write test class `TestGitHubOAuthCallback`:
  - [ ] `test_successful_oauth_creates_github_integration`
  - [ ] `test_invalid_state_returns_error_page`
  - [ ] `test_oauth_error_param_displays_message`
  - [ ] `test_existing_integration_updates_token`
  - [ ] `test_redirects_to_integrations_on_success`
- [ ] Write test class `TestJiraOAuthCallback`:
  - [ ] `test_successful_oauth_creates_jira_integration`
  - [ ] `test_handles_multiple_jira_sites`
- [ ] Write test class `TestSlackOAuthCallback`:
  - [ ] `test_successful_oauth_creates_slack_integration`
  - [ ] `test_stores_bot_token`
- [ ] Mock external API calls with `@patch`

**🟢/🔵 Phases:**
- [ ] Verify all tests pass
- [ ] Commit: "Add TDD tests for OAuth callback views"

### Task 4.2: Model Method Tests [L] - 4h

**🔴 RED Phase:**
- [ ] Create `apps/metrics/tests/models/test_pull_request_methods.py`
- [ ] Write test class `TestEffectiveProperties`:
  - [ ] `test_effective_is_ai_assisted_uses_llm_when_available`
  - [ ] `test_effective_is_ai_assisted_falls_back_to_field`
  - [ ] `test_effective_ai_tools_uses_llm_when_available`
  - [ ] `test_effective_tech_categories_from_llm`
- [ ] Write test class `TestComputedFields`:
  - [ ] `test_cycle_time_calculated_correctly`
  - [ ] `test_review_time_calculated_correctly`
  - [ ] `test_lines_changed_sums_additions_deletions`
- [ ] Write test class `TestModelManagers`:
  - [ ] `test_for_team_filters_by_current_team`

**🟢/🔵 Phases:**
- [ ] Verify all tests pass
- [ ] Commit: "Add TDD tests for PullRequest model methods"

### Task 4.3: Integration View Tests [M] - 3h

**🔴 RED Phase:**
- [ ] Create `apps/integrations/tests/test_webhook_views.py`
- [ ] Write test class `TestGitHubWebhookView`:
  - [ ] `test_validates_webhook_signature`
  - [ ] `test_rejects_invalid_signature`
  - [ ] `test_processes_push_event`
  - [ ] `test_processes_pull_request_event`
  - [ ] `test_returns_200_for_unknown_event`
- [ ] Write test class `TestIntegrationStatusView`:
  - [ ] `test_returns_connected_integrations`
  - [ ] `test_shows_last_sync_time`

**🟢/🔵 Phases:**
- [ ] Verify all tests pass
- [ ] Commit: "Add TDD tests for integration views"

---

## Phase 5: Factory & Performance (Day 11-12)

### Task 5.1: Deterministic Factories [M] - 2h
- [ ] Read `apps/metrics/factories.py`
- [ ] Identify all `random` usage (lines 76, 160-182, etc.)
- [ ] Replace with deterministic alternatives:
  ```python
  # BEFORE
  additions = factory.LazyFunction(lambda: random.randint(10, 500))

  # AFTER
  additions = factory.LazyAttribute(lambda o: (o.github_pr_id * 17) % 490 + 10)
  ```
- [ ] Test determinism: `pytest --randomly-seed=12345` (run twice, same results)
- [ ] Update factory docstrings
- [ ] Commit: "Make factories deterministic"

### Task 5.2: Optimize Factory Usage [M] - 2h
- [ ] Audit tests for `create()` vs `build()` usage
- [ ] Identify tests that don't need DB:
  - [ ] Unit tests for pure functions
  - [ ] Tests only checking return values
- [ ] Replace `create()` with `build()` where safe
- [ ] Run tests to verify no breakage
- [ ] Commit: "Optimize factory usage with build() vs create()"

### Task 5.3: Slow Test Optimization [M] - 2h
- [ ] Profile top 10 slow tests: `pytest --durations=10`
- [ ] For each slow test, evaluate:
  - [ ] Can batch size be reduced?
  - [ ] Can `build()` replace `create()`?
  - [ ] Is all data actually needed?
- [ ] Apply optimizations
- [ ] Verify no test >3s
- [ ] Commit: "Optimize slow tests"

---

## Verification Checklist

### After Phase 1
- [ ] `make test` shows 0 timezone warnings
- [ ] `pytest -m "not slow"` skips marked tests
- [ ] `test_roles.py` uses factories and `setUp`
- [ ] Test utilities module exists

### After Phase 2
- [ ] `apps/metrics/tests/dashboard/` has 4 new test files
- [ ] `dashboard_service.py` has 25+ tests
- [ ] All new tests follow TDD pattern
- [ ] All tests pass

### After Phase 3
- [ ] `grep -c "waitForTimeout" tests/e2e/*.spec.ts` < 50
- [ ] E2E tests pass 3/3 times
- [ ] E2E README.md exists

### After Phase 4
- [ ] OAuth flows have 15+ tests
- [ ] Model methods have 15+ tests
- [ ] Integration views have 10+ tests

### After Phase 5
- [ ] No `import random` in factories
- [ ] Tests deterministic with seed
- [ ] No test >3s duration

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
