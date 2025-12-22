# Insights DateTime Bug - Tasks

**Last Updated:** 2025-12-22

## Phase 1: TDD Red - Write Failing Tests

- [x] **1.1** Write test that `get_ai_adoption_trend` returns JSON-serializable data
  - File: `apps/metrics/tests/test_insight_rules.py`
  - Verify "week" field is string, not datetime
  - Effort: S

- [x] **1.2** Write test that `AIAdoptionTrendRule` can save insight to database
  - File: `apps/metrics/tests/test_insight_rules.py`
  - Full integration test with real database save
  - Effort: S

- [x] **1.3** Write test that `CycleTimeTrendRule` can save insight to database
  - File: `apps/metrics/tests/test_insight_rules.py`
  - Similar to 1.2 but for cycle time
  - Effort: S

- [x] **1.4** Run tests, confirm they fail
  - Command: `make test ARGS='apps.metrics.tests.test_insight_rules -k serializ'`
  - Effort: S

## Phase 2: TDD Green - Implement Fix

- [x] **2.1** Fix `_get_metric_trend()` helper to return ISO date strings
  - File: `apps/metrics/services/dashboard_service.py`
  - Convert datetime to `strftime("%Y-%m-%d")`
  - Also convert Decimal to float for JSON serialization
  - Effort: S

- [x] **2.2** Fix `get_ai_adoption_trend()` to return ISO date strings
  - File: `apps/metrics/services/dashboard_service.py`
  - Same conversion pattern
  - Effort: S

- [x] **2.3** Run tests, confirm they pass
  - Command: `make test ARGS='apps.metrics.tests.test_insight_rules'`
  - All 4 new tests passed, 39 total insight rules tests passed
  - Effort: S

## Phase 3: TDD Refactor - Clean Up

- [x] **3.1** Review other dashboard functions for similar issues
  - Checked all functions using TruncWeek/TruncMonth
  - Both affected functions (`get_ai_adoption_trend`, `_get_metric_trend`) fixed
  - Effort: S

- [x] **3.2** Run full test suite
  - Command: `make test`
  - All 185 dashboard tests passed, no regressions
  - Effort: S

## Phase 4: Verification

- [x] **4.1** Regenerate insights for Gumroad team
  - Used shell script to regenerate insights
  - Generated 3 insights successfully:
    - AI adoption increased 17%
    - Cycle time regressed 81%
    - 79 PRs missing Jira links
  - Effort: S

- [x] **4.2** Check dashboard displays correctly
  - Verified dev server running at http://localhost:8000/
  - Gumroad team shows 4 insights in database
  - Effort: S

## Additional Work

- [x] **5.1** Add insights generation to seeding script
  - File: `apps/metrics/seeding/real_project_seeder.py`
  - Added Step 8: `_generate_insights()` method
  - Added `insights_generated: int = 0` to `RealProjectStats`
  - Updated `_log_stats()` to include insights count
  - Effort: S

## Notes

- All tasks completed
- TDD approach successfully used for bug fix
- Seeding script now automatically generates insights as final step
