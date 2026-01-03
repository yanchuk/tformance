# AI Adoption Feature Flag - Task Checklist

**Last Updated:** 2026-01-02
**Status:** ✅ Complete

---

## Overview

| Phase | Description | Effort | Status | Tests | Implementation |
|-------|-------------|--------|--------|-------|----------------|
| 1 | Core Infrastructure | S | ✅ Complete | [x] | [x] |
| 2 | Dashboard Service | L | ✅ Complete | [x] | [x] |
| 3 | Aggregation & Quick Stats | M | ✅ Complete | [x] | [x] |
| 4 | LLM Insights | S | ✅ Complete | [x] | [x] |
| 5 | Cache Invalidation | S | ✅ Complete | [x] | [x] |
| 6 | Admin & Documentation | S | ✅ Complete | [x] | [x] |

---

## Phase 1: Core Infrastructure ✅ COMPLETE

### RED Phase - Write Failing Tests

- [x] **1.1** Create test file `apps/metrics/tests/test_ai_adoption_helpers.py`
- [x] **1.2** Test: `should_use_survey_data` returns False when flag inactive
- [x] **1.3** Test: `should_use_survey_data` returns True when flag active for team
- [x] **1.4** Test: `get_pr_ai_status` uses detection when use_surveys=False
- [x] **1.5** Test: `get_pr_ai_status` uses survey when use_surveys=True and survey exists
- [x] **1.6** Test: `get_pr_ai_status` falls back to detection when no survey
- [x] **1.7** Run tests and confirm they FAIL

### GREEN Phase - Implementation

- [x] **1.8** Create `apps/metrics/services/ai_adoption_helpers.py`
- [x] **1.9** Implement `AI_ADOPTION_SURVEY_FLAG` constant
- [x] **1.10** Implement `should_use_survey_data(request_or_team)` function
- [x] **1.11** Implement `get_pr_ai_status(pr, use_surveys)` function
- [x] **1.12** Create migration `apps/teams/migrations/0007_add_ai_adoption_survey_flag.py`
- [x] **1.13** Run migration
- [x] **1.14** Run tests and confirm they PASS (13 tests)

### REFACTOR Phase

- [x] **1.15** Review code for clarity and DRY principles
- [x] **1.16** Add docstrings and type hints
- [x] **1.17** Run full test suite to verify no regressions

---

## Phase 2: Dashboard Service Refactor ✅ COMPLETE

### RED Phase - Write Failing Tests

- [x] **2.1** Add flag-aware tests to `test_key_metrics.py`
  - [x] Test: `get_key_metrics` uses detection when flag=False
  - [x] Test: `get_key_metrics` uses surveys when flag=True
  - [x] Added `TestGetKeyMetricsFeatureFlag` class with 3 tests
- [x] **2.2** Updated `test_sparkline_service.py` to work with detection default
  - [x] Test: `test_ai_adoption_calculates_percentage_per_week` - uses detection
- [x] **2.3** Run tests and confirm they FAIL

### GREEN Phase - Implementation

- [x] **2.4** Added `_calculate_ai_percentage_from_detection()` helper function
- [x] **2.5** Updated `get_key_metrics()` with `use_survey_data` parameter
  - Default: `use_survey_data=False` (detection-based)
  - Added data source suffix to cache key
- [x] **2.6** Updated `get_sparkline_data()` with `use_survey_data` parameter
  - Default: `use_survey_data=False` (detection-based)
  - Added weekly detection-based calculation
- [x] **2.7** Run tests and confirm they PASS

### REFACTOR Phase

- [x] **2.8** Extract common flag-checking logic to helper
- [x] **2.9** Update function docstrings to document flag behavior
- [x] **2.10** Run full test suite

---

## Phase 3: Aggregation & Quick Stats ✅ COMPLETE

### RED Phase - Write Failing Tests

- [x] **3.1** Add flag-aware tests to `test_aggregation_service.py`
  - [x] Test: `compute_member_weekly_metrics` uses detection when use_survey_data=False
  - [x] Test: `compute_member_weekly_metrics` uses surveys when use_survey_data=True
  - [x] Added `TestComputeMemberWeeklyMetricsFeatureFlag` class with 4 tests
- [x] **3.2** Add flag-aware tests to `test_quick_stats.py`
  - [x] Test: `get_team_quick_stats` uses detection when use_survey_data=False
  - [x] Test: `get_team_quick_stats` uses surveys when use_survey_data=True
  - [x] Added `TestGetTeamQuickStatsFeatureFlag` class with 5 tests
- [x] **3.3** Run tests and confirm they FAIL (9 tests failed)

### GREEN Phase - Implementation

- [x] **3.4** Update `compute_member_weekly_metrics()` in aggregation_service.py
  - Added `use_survey_data` parameter (default: False)
  - Detection-based uses `effective_is_ai_assisted`
- [x] **3.5** Update `get_team_quick_stats()` in quick_stats.py
  - Added `use_survey_data` parameter (default: False)
  - Detection-based calculation for both AI percentage and recent activity
- [x] **3.6** Fixed existing tests to use `use_survey_data=True` for survey-based behavior
- [x] **3.7** Fixed sparkline service tests (MIN_SPARKLINE_SAMPLE_SIZE requirement)
- [x] **3.8** Run tests and confirm they PASS (135 tests)

### REFACTOR Phase

- [x] **3.9** Review for consistency with dashboard service changes
- [x] **3.10** Run full test suite

---

## Phase 4: LLM Insights ✅ COMPLETE

### Verification

- [x] **4.1** Verify `get_ai_impact_stats` uses detection by default
- [x] **4.2** Updated `get_ai_impact_stats()` with `use_survey_data` parameter
  - Default: `use_survey_data=False` (detection-based)
  - Survey-based uses fallback to detection when no survey
- [x] **4.3** Verify `gather_insight_data` uses detection-based AI stats by default
- [x] **4.4** Run tests and confirm they PASS (50 tests)

---

## Phase 5: Cache Invalidation ✅ COMPLETE

### Verification

- [x] **5.1** Verify `get_key_metrics` cache key includes data source suffix
  - Cache key format: `key_metrics:{team_id}:{start_date}:{end_date}:{repo}:{data_source}`
  - `data_source` is "detection" or "survey" based on `use_survey_data` flag
- [x] **5.2** No view-level caching found that needs updating
- [x] **5.3** Cache keys properly differentiate between data sources

---

## Phase 6: Admin & Documentation ✅ COMPLETE

- [x] **6.1** Verify flag appears in Django admin (`/admin/teams/flag/`)
- [x] **6.2** Updated task checklist with complete implementation details
- [x] **6.3** All functions documented with `use_survey_data` parameter behavior

---

## Final Verification

- [x] **7.1** Run feature flag related tests: 135 tests pass
- [x] **7.2** Run dashboard tests: 458 tests pass
- [x] **7.3** Default behavior is detection-based (flag=False)
  - Dashboard uses `effective_is_ai_assisted`
  - Sparklines use detection-based values
  - Insights use detection-based percentages
- [x] **7.4** Survey-based behavior available when `use_survey_data=True`
  - Falls back to detection when no survey response
- [x] **7.5** Update task status to COMPLETE

---

## Files Changed

| File | Changes |
|------|---------|
| `apps/metrics/services/ai_adoption_helpers.py` | NEW - Helper functions |
| `apps/metrics/services/dashboard_service.py` | Added `use_survey_data` to `get_key_metrics()`, `get_sparkline_data()`, `get_ai_impact_stats()` |
| `apps/metrics/services/aggregation_service.py` | Added `use_survey_data` to `compute_member_weekly_metrics()` |
| `apps/metrics/services/quick_stats.py` | Added `use_survey_data` to `get_team_quick_stats()` |
| `apps/teams/migrations/0007_add_ai_adoption_survey_flag.py` | NEW - Add waffle flag |
| `apps/metrics/tests/test_ai_adoption_helpers.py` | NEW - Helper tests |
| `apps/metrics/tests/dashboard/test_key_metrics.py` | Flag-aware tests |
| `apps/metrics/tests/dashboard/test_sparkline_data.py` | Updated for detection default |
| `apps/metrics/tests/test_aggregation_service.py` | Flag-aware tests |
| `apps/metrics/tests/test_quick_stats.py` | Flag-aware tests |
| `apps/metrics/tests/test_sparkline_service.py` | Fixed MIN_SPARKLINE_SAMPLE_SIZE tests |

---

## Test Results

| Phase | Tests Added | Tests Passed | Notes |
|-------|-------------|--------------|-------|
| 1 | 13 | 13 | Core infrastructure |
| 2 | 16 | 16 | Dashboard service |
| 3 | 9 | 135 | Aggregation & Quick Stats (9 new + existing) |
| 4 | 0 | 50 | LLM Insights verification |
| 5 | 0 | N/A | Cache key verification |
| 6 | 0 | N/A | Documentation |
| **Total** | ~38 | ~600+ | Feature flag implementation complete |

---

## Summary

The feature flag implementation is complete. By default (flag=False), all AI adoption calculations use detection-based data (`effective_is_ai_assisted` which prioritizes LLM > regex pattern detection). When the flag is enabled for a team (flag=True), survey data is used with fallback to detection when no survey response exists.

Key behavior:
- **Default (flag=False)**: Uses `effective_is_ai_assisted` property - LLM analysis takes priority over regex patterns
- **Flag enabled (flag=True)**: Uses `PRSurvey.author_ai_assisted` with fallback to detection
- All functions have a `use_survey_data` parameter for explicit control
- Cache keys include data source to prevent cross-contamination
