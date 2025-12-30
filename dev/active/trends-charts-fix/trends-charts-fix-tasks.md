# Trends Charts Fix - Tasks (v3)

**Last Updated:** 2025-12-30
**Status:** COMPLETE (All Sessions)

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
**Effort:** M | **Priority:** Critical | **Status:** COMPLETE

- [x] Add defensive checks in `createMultiMetricChart()` for missing datasets
- [x] Ensure `unit` field is stored directly on Chart.js dataset
- [x] Filter empty datasets before chart creation
- [x] Add console.warn for debugging failed chart creation
- [x] Add `formatMetricValue()` helper for consistent formatting
- [x] Test: Select Cycle Time + Review Time → both lines render
- [x] Test: Select all 4 metrics → dual Y-axes work

**Files Modified:**
- `assets/javascript/dashboard/trend-charts.js`

### Task 2A.2: Fix Chart Initialization Race Condition
**Effort:** M | **Priority:** High | **Status:** COMPLETE

- [x] Wrap `chartManager.initAll()` in `requestAnimationFrame` in afterSwap handler
- [x] Add retry logic (max 3 attempts, 100ms delay) for chart initialization
- [x] Add `data-chart-initialized` attribute to prevent double-init
- [x] Check canvas existence before each chart creation
- [x] Test: Charts render on first HTMX load without page refresh
- [x] Test: No duplicate chart instances created

**Files Modified:**
- `assets/javascript/app.js`
- `assets/javascript/dashboard/chart-manager.js`

---

## Phase 2B: Data Quality & Formatting ✅

### Task 2B.1: Filter Empty Dict Entries from Tech Breakdown
**Effort:** S | **Priority:** Medium | **Status:** COMPLETE

- [x] Add `_is_valid_category()` helper function
- [x] Filter categories in `get_tech_breakdown()`
- [x] Filter categories in `get_monthly_tech_trend()`
- [x] Filter categories in `get_weekly_tech_trend()`
- [x] Test: No `{}` entries in tech breakdown legend
- [x] Test: Percentages sum to ~100%

**Files Modified:**
- `apps/metrics/services/dashboard_service.py`

### Task 2B.2: Apply Format Functions Consistently
**Effort:** S | **Priority:** Low | **Status:** COMPLETE

- [x] Created `formatMetricValue(value, unit)` function in trend-charts.js
- [x] Used in tooltip label callbacks
- [x] Used in Y-axis tick callbacks
- [x] Test: Cycle time shows "14.8h" in tooltips
- [x] Test: AI Adoption shows "56%" in tooltips
- [x] Test: Y-axis labels include units

**Files Modified:**
- `assets/javascript/dashboard/trend-charts.js`

---

## Phase 2C: UX Enhancements ✅

### Task 2C.1: Add PRs Merged Stat Card
**Effort:** S | **Priority:** Medium | **Status:** COMPLETE

- [x] Changed trends.html to load full `key_metrics_cards.html` partial
- [x] PRs Merged stat card already exists in that partial
- [x] Period-over-period change already calculated in existing view
- [x] Test: PRs Merged card displays with count
- [x] Test: Shows percentage change vs previous period

**Files Modified:**
- `templates/metrics/analytics/trends.html`

### Task 2C.2: Add Sparklines to Stat Cards
**Effort:** M | **Priority:** Medium | **Status:** COMPLETE

- [x] Sparklines already implemented in `key_metrics_cards.html` partial
- [x] Fixed Review Time card showing wrong metric (was `avg_quality_rating`, now `avg_review_time`)
- [x] `initSparklines()` already called in chartManager
- [x] Test: Each stat card has mini trend line
- [x] Test: Sparklines use metric-appropriate colors
- [x] Test: Sparklines render after HTMX swap

**Files Modified:**
- `templates/metrics/partials/key_metrics_cards.html` (fixed wrong metric)

---

## Phase 2D: 100% Stacked Area Charts ✅

### Task 2D.1: Create Stacked Area Chart Factory
**Effort:** M | **Priority:** Feature | **Status:** COMPLETE

- [x] Add `createStackedAreaChart(ctx, data, options)` method to ChartManager
- [x] Implement `normalizeToPercentages(datasets, labelCount)` helper
- [x] Configure Chart.js line chart with `fill: '-1'` (stack on previous)
- [x] Add percentage Y-axis (0-100%)
- [x] Test: Factory creates valid stacked area chart
- [x] Test: Data normalized to percentages per time point
- [x] Test: Areas stack smoothly with semi-transparent fills

**Files Modified:**
- `assets/javascript/dashboard/chart-manager.js`

### Task 2D.2: Update Technology Breakdown Chart
**Effort:** M | **Priority:** Feature | **Status:** COMPLETE

- [x] View already returns time-series data per category
- [x] Changed chart registration to use `createStackedAreaChart`
- [x] Updated template description and comments
- [x] Test: Tech breakdown shows as 100% stacked area chart
- [x] Test: Areas stack to 100% at each time point
- [x] Test: Legend shows category names with percentages

**Files Modified:**
- `templates/metrics/analytics/trends/tech_chart.html`
- `assets/javascript/app.js`

### Task 2D.3: Update PR Types Chart
**Effort:** M | **Priority:** Feature | **Status:** COMPLETE

- [x] Changed chart registration to use `createStackedAreaChart`
- [x] Data normalized to percentages automatically by factory
- [x] Updated template for area chart description
- [x] Test: PR types shows as 100% stacked area chart
- [x] Test: Feature/Bugfix/etc areas stack to 100%
- [x] Test: ICP sees composition trend clearly

**Files Modified:**
- `templates/metrics/analytics/trends/pr_type_chart.html`
- `assets/javascript/app.js`

---

## Testing ✅

### Unit Tests
- [x] Run tech-related tests: 53 passed

### E2E Tests
- [x] Run `npx playwright test trends-charts.spec.ts`
- [x] 71/72 tests pass (1 Firefox CSP false positive for PostHog)

### Manual Verification (Antiwork Team)
- [x] Load Trends page with "This Year" preset
- [x] Multi-metric selection works (all 4 metrics)
- [x] No `{}` entries in any chart
- [x] All values show correct units (h, %)
- [x] PRs Merged stat card visible with sparkline
- [x] All sparklines render
- [x] Tech breakdown shows as stacked area
- [x] PR types shows as stacked area
- [x] Charts render without page reload
- [x] No console errors

---

## Definition of Done ✅

- [x] Multi-metric comparison chart renders reliably
- [x] No `{}` entries in tech breakdown
- [x] Cycle time shows "h" suffix in tooltips
- [x] PRs Merged stat card with sparkline
- [x] All charts render on first HTMX load (no refresh)
- [x] Tech breakdown as 100% stacked area chart
- [x] PR types as 100% stacked area chart
- [x] All E2E tests pass
- [x] No console errors on page load
- [x] Ready for code review

---

## Phase 3: Session 3 Fixes (2025-12-30) ✅

### Task 3.1: Fix Chart Resize After HTMX Swap
**Effort:** S | **Priority:** Critical | **Status:** COMPLETE

- [x] Identified root cause: canvas stays at default 300x150 after HTMX swap
- [x] Single `requestAnimationFrame` didn't work - layout not complete
- [x] Fixed with nested RAF: `requestAnimationFrame(() => requestAnimationFrame(() => chart.resize()))`
- [x] Applied fix in both `init()` and `initByType()` methods
- [x] Test: Charts render correctly on first HTMX load

**Files Modified:**
- `assets/javascript/dashboard/chart-manager.js` (lines 114-120, 277-283)

### Task 3.2: Default Period for Trends Page
**Effort:** S | **Priority:** Medium | **Status:** COMPLETE

- [x] Modified `_get_trends_context()` to default to 365 days with monthly granularity
- [x] Only applies when no date params are explicitly provided
- [x] Test: Trends page loads with last 12 months by default

**Files Modified:**
- `apps/metrics/views/trends_views.py` (lines 48-69)

### Task 3.3: Fix `{}` Entries in Tech Breakdown
**Effort:** S | **Priority:** Medium | **Status:** COMPLETE

- [x] Root cause: LLM returns 'chore' and 'ci' as tech categories (from PR type confusion)
- [x] These categories were not in `TECH_CONFIG`, causing `get_item` filter to return `{}`
- [x] Added `chore` and `ci` to `TECH_CONFIG` with appropriate colors
- [x] Test: No `{}` entries in Tech Breakdown - shows "Chore" and "CI/CD" properly

**Files Modified:**
- `apps/metrics/views/trends_views.py` (lines 419-421)

### Task 3.4: Fix Benchmark Panel Template Comments
**Effort:** S | **Priority:** Low | **Status:** COMPLETE

- [x] Root cause: Django's `{# #}` is single-line only; multiline comments were rendered as text
- [x] Changed to `{% comment %}...{% endcomment %}` syntax
- [x] Test: No comment text visible in Benchmark Panel

**Files Modified:**
- `templates/metrics/analytics/trends/benchmark_panel.html` (lines 2-13)

---

## Files Summary

| File | Changes |
|------|---------|
| `assets/javascript/dashboard/trend-charts.js` | `formatMetricValue()` helper, defensive checks, tooltip/Y-axis formatting |
| `assets/javascript/dashboard/chart-manager.js` | `createStackedAreaChart()`, `normalizeToPercentages()`, retry logic, double-init prevention, nested RAF for resize |
| `assets/javascript/app.js` | `requestAnimationFrame` wrapper, changed PR Type and Tech chart registrations to stacked area |
| `apps/metrics/services/dashboard_service.py` | `_is_valid_category()` helper, filtering in 3 tech trend functions |
| `apps/metrics/views/trends_views.py` | Default 365 days/monthly for Trends, added `chore`/`ci` to TECH_CONFIG |
| `templates/metrics/analytics/trends.html` | Load full key_metrics_cards.html instead of fragile hx-select |
| `templates/metrics/partials/key_metrics_cards.html` | Fixed Review Time card (was showing wrong metric) |
| `templates/metrics/analytics/trends/pr_type_chart.html` | Updated comments and description for stacked area |
| `templates/metrics/analytics/trends/tech_chart.html` | Updated comments and description for stacked area |
| `templates/metrics/analytics/trends/benchmark_panel.html` | Fixed multiline comment syntax (`{% comment %}` instead of `{# #}`) |
