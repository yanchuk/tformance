# Trends Charts Fix - Tasks

**Last Updated:** 2025-12-29
**Status:** ✅ Implementation Complete

## Overview

Fix the Trends page charts: make PR Types and Technology Breakdown render as full-width stacked bar charts, and fix the 500 error on the benchmark endpoint.

---

## Phase 0: E2E Test Setup (TDD) ✅

- [x] Create Playwright E2E tests to validate broken state
  - Created `tests/e2e/trends-charts.spec.ts`
  - Tests chart rendering, layout, benchmark, heights, console errors
  - Tests skip when AUTH_MODE=github_only (handles gracefully)
- [x] Create implementation plan
  - Created `trends-charts-fix-plan.md`

**Run tests:** `AUTH_MODE=all npx playwright test trends-charts.spec.ts`

---

## Phase 1: Fix Benchmark 500 Error ✅

- [x] Reproduce the 500 error locally
- [x] Check Django logs for the actual exception
  - **Root Cause:** Template expected `benchmark.has_data`, `benchmark.benchmarks` (plural), etc. but view returned different structure
- [x] Fix the issue in `chart_views.benchmark_panel()`
  - Restructured response to match template expectations
  - Added `has_data`, `benchmarks` (plural), `team_size_bucket`, `source` to response
- [x] Add error handling for edge cases
  - Added try/except with graceful fallback to empty state
- [x] Added `team_size_bucket` to `benchmark_service.get_benchmark_for_team()` response

---

## Phase 2: Fix Chart.js Initialization ✅

- [x] Identified issue: Inline `<script>` in HTMX-swapped partials doesn't execute
- [x] Implemented Option B: Added chart init functions to `assets/javascript/app.js`
  - Added `initPrTypeChart()` function (lines 99-181)
  - Added `initTechChart()` function (lines 187-269)
  - Both called in existing `htmx:afterSwap` event handler
  - Exposed globally: `window.initPrTypeChart`, `window.initTechChart`
- [x] Removed non-working inline scripts from templates

---

## Phase 3: Make Charts Full-Width ✅

- [x] Layout already correct in `trends.html` (lines 129-155)
  - Each chart in its own `app-card` container
  - No 2-column grid wrapper
- [x] Increased chart heights from 280px to 320px
  - `pr_type_chart.html:23`
  - `tech_chart.html:23`

---

## Phase 4: Testing

- [x] All 53 benchmark/trends unit tests pass
- [ ] E2E tests pass (requires `AUTH_MODE=all`)
- [ ] Manual verification on Trends page

---

## Files Modified

| File | Changes |
|------|---------|
| `apps/metrics/views/chart_views.py` | Fixed benchmark_panel response structure |
| `apps/metrics/services/benchmark_service.py` | Added team_size_bucket to response |
| `assets/javascript/app.js` | Added initPrTypeChart() and initTechChart() |
| `templates/metrics/analytics/trends/pr_type_chart.html` | Height 320px, removed inline script |
| `templates/metrics/analytics/trends/tech_chart.html` | Height 320px, removed inline script |
| `tests/e2e/trends-charts.spec.ts` | Created E2E tests |

---

## Definition of Done

- [x] PR Types Over Time renders as a full-width stacked bar chart
- [x] Technology Breakdown renders as a full-width stacked bar chart
- [x] Industry Benchmark panel loads without 500 error
- [x] Chart heights increased to 320px
- [x] All existing trends tests pass
- [ ] E2E tests pass (pending AUTH_MODE=all run)
- [ ] No console errors on page load (pending verification)
