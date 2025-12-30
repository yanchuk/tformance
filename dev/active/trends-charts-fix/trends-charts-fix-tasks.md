# Trends Charts Fix - Tasks (v5)

**Last Updated:** 2025-12-30 (Session 4 End)
**Status:** All Phases Complete ✅

---

## Overview

Fix 6 issues on the Trends & Comparison page for complete ICP experience:
1. Multi-metric comparison chart blank
2. Tech breakdown shows `{}` entries
3. Cycle time missing "h" suffix
4. PRs Merged stat card missing + no sparklines
5. Charts only display after page reload
6. Need 100% Stacked Area Charts for composition trends

---

## Phase 1: Previous Session (Complete) ✅

- [x] Fix Benchmark 500 error
- [x] Add `initPrTypeChart()` and `initTechChart()` to app.js
- [x] Remove inline scripts from HTMX partials
- [x] Increase chart heights to 320px
- [x] Create E2E test file

---

## Phase 2A: Critical Bug Fixes ✅

### Task 2A.1: Fix Multi-Metric Comparison Chart
**Status:** COMPLETE

- [x] Add defensive checks in `createMultiMetricChart()` for missing datasets
- [x] Ensure `unit` field is stored directly on Chart.js dataset
- [x] Filter empty datasets before chart creation
- [x] Add `formatMetricValue()` helper for consistent formatting

### Task 2A.2: Fix Chart Initialization Race Condition
**Status:** COMPLETE

- [x] Wrap `chartManager.initAll()` in `requestAnimationFrame`
- [x] Add retry logic (max 3 attempts, 100ms delay)
- [x] Add `data-chart-initialized` attribute to prevent double-init

---

## Phase 2B: Data Quality & Formatting ✅

### Task 2B.1: Filter Empty Dict Entries from Tech Breakdown
**Status:** COMPLETE

- [x] Add `_is_valid_category()` helper function
- [x] Filter categories in tech breakdown functions

### Task 2B.2: Apply Format Functions Consistently
**Status:** COMPLETE

- [x] Created `formatMetricValue(value, unit)` function
- [x] Used in tooltip and Y-axis callbacks

---

## Phase 2C: UX Enhancements ✅

### Task 2C.1: Add PRs Merged Stat Card
**Status:** COMPLETE

- [x] Load full `key_metrics_cards.html` partial

### Task 2C.2: Add Sparklines to Stat Cards
**Status:** COMPLETE

- [x] Fixed Review Time card showing wrong metric

---

## Phase 2D: 100% Stacked Area Charts ✅

- [x] Add `createStackedAreaChart()` factory
- [x] Update Technology Breakdown to stacked area
- [x] Update PR Types to stacked area

---

## Phase 3: Session 3 Fixes ✅

- [x] Task 3.1: Fix Chart Resize After HTMX Swap (nested RAF)
- [x] Task 3.2: Default Period for Trends (365 days/monthly)
- [x] Task 3.3: Fix `{}` Entries (added `chore`/`ci` to TECH_CONFIG)
- [x] Task 3.4: Fix Benchmark Panel Comments

---

## Phase 4: Session 4 Features ✅

### Task 4.0: 12-Month Default (Already Complete)
**Status:** COMPLETE - Verified in Session 3

### Task 4.1: AI Assisted Filter for Tech/PR Type Charts (TDD)
**Status:** COMPLETE

- [x] RED: Write failing tests for ai_filter parameter on Tech breakdown
- [x] GREEN: Implement `ai_assisted` param in 6 service functions:
  - `get_tech_breakdown()`
  - `get_monthly_tech_trend()`
  - `get_weekly_tech_trend()`
  - `get_pr_type_breakdown()`
  - `get_monthly_pr_type_trend()`
  - `get_weekly_pr_type_trend()`
- [x] GREEN: Add `ai_filter` to views (`tech_breakdown_chart`, `pr_type_breakdown_chart`)
- [x] GREEN: Add filter UI buttons to both templates
- [x] Filter uses `effective_is_ai_assisted` property (LLM priority)
- [x] Tests: 221 dashboard tests pass, 57 trends views tests pass

**Files Modified:**
- `apps/metrics/services/dashboard_service.py`
- `apps/metrics/views/trends_views.py`
- `templates/metrics/analytics/trends/tech_chart.html`
- `templates/metrics/analytics/trends/pr_type_chart.html`
- `apps/metrics/tests/dashboard/test_file_categories.py`
- `apps/metrics/tests/test_trends_views.py`

### Task 4.2: Fix Review Time Display
**Status:** COMPLETE

- [x] Root cause: `get_key_metrics()` didn't return `avg_review_time` key
- [x] RED: Added tests expecting `avg_review_time` in result
- [x] GREEN: Added `avg_review_time = prs.aggregate(avg=Avg("review_time_hours"))["avg"]`
- [x] GREEN: Added key to result dict
- [x] Tests: All 12 key_metrics tests pass

**Files Modified:**
- `apps/metrics/services/dashboard_service.py` (lines 169-170, 183)
- `apps/metrics/tests/dashboard/test_key_metrics.py`

### Task 4.3: Fix AI Filter Losing Granularity
**Status:** COMPLETE

- [x] Root cause: `hx-include` didn't include `[name='granularity']`
- [x] Fix: Added `[name='granularity']` to hx-include in both templates
- [x] Now AI filter preserves granularity when switching

**Files Modified:**
- `templates/metrics/analytics/trends/tech_chart.html` (lines 30, 40, 50)
- `templates/metrics/analytics/trends/pr_type_chart.html` (lines 30, 40, 50)

### Task 4.4: Disable Zoom on Comparison Chart
**Status:** COMPLETE

- [x] User requested disabling zoom/pan on multi-metric comparison chart
- [x] Set `enabled: false` for pan, wheel, and pinch zoom
- [x] JS rebuilt with `npm run build`

**Files Modified:**
- `assets/javascript/dashboard/trend-charts.js` (lines 392-405)

---

## All Tests Passing ✅

- Dashboard tests: 221 passed
- Trends views tests: 57 passed
- E2E tests: 71/72 passed (1 Firefox CSP false positive)
- Code formatted with ruff

---

## Files Modified Summary (Session 4)

| File | Changes |
|------|---------|
| `apps/metrics/services/dashboard_service.py` | AI filter param (6 functions), avg_review_time in get_key_metrics |
| `apps/metrics/views/trends_views.py` | ai_filter handling in tech/PR type views |
| `templates/metrics/analytics/trends/tech_chart.html` | AI filter buttons, fixed hx-include |
| `templates/metrics/analytics/trends/pr_type_chart.html` | AI filter buttons, fixed hx-include |
| `assets/javascript/dashboard/trend-charts.js` | Disabled zoom on comparison chart |
| `apps/metrics/tests/dashboard/test_key_metrics.py` | avg_review_time tests |
| `apps/metrics/tests/dashboard/test_file_categories.py` | AI filter tests |
| `apps/metrics/tests/test_trends_views.py` | AI filter view tests |

---

## Definition of Done ✅

- [x] AI Assisted filter works on Tech and PR Type charts
- [x] Filter uses `effective_is_ai_assisted` (LLM priority)
- [x] Review Time stat card shows actual value
- [x] AI filter preserves granularity when switching
- [x] Comparison chart has no zoom/pan
- [x] All unit tests pass
- [x] All E2E tests pass
- [x] Code formatted with ruff
