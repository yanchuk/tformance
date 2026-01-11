# Copilot Acceptance in Trends Tab - Tasks

**Last Updated:** 2026-01-11

## Overview

Add Copilot Acceptance Rate as a selectable metric in the Trends tab using TDD workflow.

## Review Findings (2026-01-11)

**Resolved Decisions:**
- Weekly format: Use `YYYY-MM-DD` (matches `ai_adoption`, same % metric type)
- Import: Add `TruncMonth` to imports
- Additional tests: 4 edge case tests added

---

## Phase 1: Service Layer

### 1.1 TDD RED - Write Failing Tests
- [ ] Create test `test_get_monthly_copilot_acceptance_trend_returns_monthly_data`
  - Acceptance: Test fails with `AttributeError` (function doesn't exist)
  - Effort: S
- [ ] Create test `test_get_monthly_copilot_acceptance_trend_empty_data`
  - Acceptance: Test fails with `AttributeError`
  - Effort: S
- [ ] Create test `test_get_monthly_copilot_acceptance_trend_calculates_rate`
  - Acceptance: Test fails with `AttributeError`
  - Effort: S
- [ ] Create test `test_get_monthly_copilot_acceptance_trend_zero_suggestions`
  - Acceptance: Month with 0 suggestions returns 0.0 (no division error)
  - Effort: S
- [ ] Create test `test_get_monthly_copilot_acceptance_trend_aggregates_multiple_members`
  - Acceptance: Data from multiple members aggregates into single month value
  - Effort: S
- [ ] Create test `test_get_monthly_copilot_acceptance_trend_excludes_cursor_source`
  - Acceptance: Only 'copilot' source included, 'cursor' excluded
  - Effort: S
- [ ] Create test `test_get_weekly_copilot_acceptance_trend_format`
  - Acceptance: Returns `{week: "YYYY-MM-DD", value: float}` format
  - Effort: S
- [ ] Run tests and confirm RED state
  - Command: `.venv/bin/pytest apps/metrics/tests/dashboard/test_copilot_metrics.py -v -k "monthly_copilot or weekly_copilot"`
  - Acceptance: All 7 tests fail

### 1.2 TDD GREEN - Implement Service Functions
- [ ] Add `get_monthly_copilot_acceptance_trend()` function
  - File: `apps/metrics/services/dashboard/copilot_metrics.py`
  - Acceptance: Returns `[{month: "YYYY-MM", value: float}, ...]`
  - Effort: M
- [ ] Add `get_weekly_copilot_acceptance_trend()` wrapper
  - File: `apps/metrics/services/dashboard/copilot_metrics.py`
  - Acceptance: Returns `[{week: "YYYY-MM-DD", value: float}, ...]`
  - Effort: S
- [ ] Export functions in `__init__.py`
  - File: `apps/metrics/services/dashboard/__init__.py`
  - Acceptance: Functions importable via `dashboard_service`
  - Effort: S
- [ ] Run tests and confirm GREEN state
  - Command: `.venv/bin/pytest apps/metrics/tests/dashboard/test_copilot_metrics.py -v -k monthly_copilot`
  - Acceptance: All 4 tests pass

### 1.3 TDD REFACTOR (if needed)
- [ ] Review code for improvements
  - Acceptance: No code smells, follows existing patterns
  - Effort: S

---

## Phase 2: View Layer Integration

### 2.1 TDD RED - Write Failing View Tests
- [ ] Create test `test_trend_chart_data_accepts_copilot_acceptance_metric`
  - Acceptance: Test fails (metric not recognized)
  - Effort: S
- [ ] Create test `test_wide_trend_chart_includes_copilot_acceptance`
  - Acceptance: Test fails (metric not in METRIC_CONFIG)
  - Effort: S
- [ ] Create test `test_copilot_acceptance_uses_emerald_color`
  - Acceptance: Test fails (color check fails)
  - Effort: S
- [ ] Run tests and confirm RED state
  - Command: `.venv/bin/pytest apps/metrics/tests/ -v -k "copilot_acceptance and trend"`
  - Acceptance: All view tests fail

### 2.2 TDD GREEN - Update Views
- [ ] Add `copilot_acceptance` to METRIC_CONFIG
  - File: `apps/metrics/views/trends_views.py`
  - Acceptance: Entry with name, unit, color (#10B981), yAxisID
  - Effort: S
- [ ] Update `trend_chart_data()` metric_functions
  - Acceptance: Monthly function mapped
  - Effort: S
- [ ] Update `trend_chart_data()` weekly_functions
  - Acceptance: Weekly function mapped
  - Effort: S
- [ ] Update `wide_trend_chart()` metric_functions (both weekly and monthly)
  - Acceptance: Both granularities mapped
  - Effort: S
- [ ] Update `_get_metric_display_name()`
  - Acceptance: Returns "Copilot Acceptance (%)"
  - Effort: S
- [ ] Run tests and confirm GREEN state
  - Command: `.venv/bin/pytest apps/metrics/tests/ -v -k copilot`
  - Acceptance: All tests pass

### 2.3 TDD REFACTOR (if needed)
- [ ] Review view code for duplication
  - Acceptance: DRY principle maintained
  - Effort: S

---

## Phase 3: Verification

### 3.1 Full Test Suite
- [ ] Run related test files
  - Command: `.venv/bin/pytest apps/metrics/tests/dashboard/test_copilot_metrics.py apps/metrics/tests/test_trends_views.py -v`
  - Acceptance: All tests pass
  - Effort: S

### 3.2 Visual Verification
- [ ] Start dev server
  - Command: `make dev`
  - Acceptance: Server running on localhost:8000
  - Effort: S
- [ ] Navigate to Trends page
  - URL: `http://localhost:8000/a/tformance/metrics/analytics/trends/`
  - Acceptance: Page loads without errors
  - Effort: S
- [ ] Verify Copilot Acceptance appears in metric selector
  - Acceptance: Checkbox visible with label "Copilot Acceptance"
  - Effort: S
- [ ] Select Copilot Acceptance metric
  - Acceptance: Chart renders with emerald green line
  - Effort: S
- [ ] Toggle weekly/monthly granularity
  - Acceptance: Chart updates correctly
  - Effort: S
- [ ] Compare with another metric (e.g., Cycle Time)
  - Acceptance: Both lines render on chart
  - Effort: S
- [ ] Take screenshot for documentation
  - Acceptance: Screenshot captured via Playwright
  - Effort: S

---

## Phase 4: Commit & Cleanup

### 4.1 Commit
- [ ] Stage changes
  - Files: copilot_metrics.py, __init__.py, trends_views.py, tests
  - Effort: S
- [ ] Create commit
  - Message: `feat(trends): add Copilot Acceptance metric to Trends tab`
  - Effort: S

### 4.2 Move Documentation
- [ ] Move task directory to completed
  - From: `dev/active/copilot-trends-integration/`
  - To: `dev/completed/copilot-trends-integration/`
  - Effort: S

---

## Progress Summary

| Phase | Status | Tests |
|-------|--------|-------|
| Phase 1: Service Layer | Not Started | 0/7 |
| Phase 2: View Layer | Not Started | 0/3 |
| Phase 3: Verification | Not Started | - |
| Phase 4: Commit | Not Started | - |

**Total Tests:** 10 (7 service + 3 view)

---

## Commands Reference

```bash
# Run service tests
.venv/bin/pytest apps/metrics/tests/dashboard/test_copilot_metrics.py -v -k copilot

# Run view tests
.venv/bin/pytest apps/metrics/tests/test_trends_views.py -v -k copilot

# Run all related tests
.venv/bin/pytest apps/metrics/tests/ -v -k copilot

# Start dev server
make dev

# Format code
make ruff
```
