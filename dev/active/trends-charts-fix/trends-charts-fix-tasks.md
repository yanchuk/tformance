# Trends Charts Fix - Tasks (v6)

**Last Updated:** 2025-12-30 (Session 5 End)
**Status:** Phase 5 - Two New Bugs to Fix

---

## Overview

Fix issues on the Trends & Comparison page for complete ICP experience.

---

## Phase 5: Session 5 Bugs (IN PROGRESS)

### Task 5.1: Fix Weekly Granularity Toggle
**Status:** NOT STARTED
**Priority:** HIGH

**Symptom:** Clicking "Weekly" button does nothing - chart doesn't change

**Root Cause Analysis Needed:**
- [ ] Verify `setGranularity()` is called when button clicked
- [ ] Check if hidden input `granularity` is updated
- [ ] Verify wide chart HTMX request includes granularity param
- [ ] Check if Tech/PR Type charts are being refreshed

**Suspected Issue:**
The `updateChart()` function only refreshes:
1. Wide trend chart (`#wide-chart-container`)
2. Benchmark panel (`#benchmark-panel-container`)

It does NOT explicitly refresh:
- Tech Breakdown chart (`#tech-chart-container`)
- PR Type chart (`#pr-type-chart-container`)

These charts rely on `@htmx:afterSwap.window` event handler, which only fires when the wide chart swaps. If the granularity change doesn't trigger a wide chart refresh properly, Tech/PR charts won't update.

**Fix Approach:**
- [ ] Add explicit HTMX refresh for Tech/PR charts in `setGranularity()` or `updateChart()`
- [ ] OR: Trigger page-level refresh with new granularity param

### Task 5.2: Fix Default Time Range to "Last 12 Months"
**Status:** NOT STARTED
**Priority:** HIGH

**Symptom:** Default shows "Last Year" instead of "Last 12 Months" rolling

**Current Behavior:**
- `preset=12_months` → shows 365 days from today backward
- User expects: Last 12 calendar months

**Fix Approach:**
- [ ] Investigate `_get_trends_context()` to understand current default logic
- [ ] Verify `preset=12_months` calculates correct date range
- [ ] If different from "This Year" (Jan 1 - today), may need clarification
- [ ] May need to add/modify preset options

---

## Phase 4: Session 4 Features ✅ COMPLETE

### Task 4.1: AI Assisted Filter (TDD)
**Status:** COMPLETE

- [x] AI filter (All/No/Yes) on Tech and PR Type charts
- [x] Filter uses `effective_is_ai_assisted` property
- [x] Tests: 221 dashboard tests pass

### Task 4.2: Fix Review Time Display
**Status:** COMPLETE

- [x] Added `avg_review_time` to `get_key_metrics()`

### Task 4.3: Fix AI Filter Losing Granularity
**Status:** COMPLETE

- [x] Added `[name='granularity']` to hx-include
- [x] Added hidden inputs to trends.html
- [x] Updated setGranularity() to sync hidden input

### Task 4.4: Disable Zoom on Comparison Chart
**Status:** COMPLETE

- [x] Disabled pan, wheel, and pinch zoom

### Task 4.5: Remove Zoom Controls
**Status:** COMPLETE

- [x] Removed Reset Zoom button (refresh icon)
- [x] Removed "Scroll to zoom, drag to pan" instructions
- [x] Removed zoom tip from Tips section

---

## Previous Phases (All Complete) ✅

### Phase 1: Foundation
- [x] Fix Benchmark 500 error
- [x] Add chart init functions to app.js
- [x] Remove inline scripts from HTMX partials

### Phase 2A: Critical Bug Fixes
- [x] Fix Multi-Metric Comparison Chart
- [x] Fix Chart Initialization Race Condition

### Phase 2B: Data Quality
- [x] Filter Empty Dict Entries from Tech Breakdown
- [x] Apply Format Functions Consistently

### Phase 2C: UX Enhancements
- [x] Add PRs Merged Stat Card
- [x] Add Sparklines to Stat Cards

### Phase 2D: Stacked Area Charts
- [x] Add createStackedAreaChart() factory
- [x] Update charts to stacked area

### Phase 3: Session 3 Fixes
- [x] Fix Chart Resize After HTMX Swap
- [x] Default Period for Trends
- [x] Fix {} Entries
- [x] Fix Benchmark Panel Comments

---

## Commits This Session

| Commit | Message |
|--------|---------|
| `3b58e76` | Add AI Assisted filter to Tech/PR Type charts and fix granularity bug |
| `be6c8a4` | Remove zoom controls and instructions from Trends charts |

---

## Test Status

- Dashboard tests: 221 passed ✅
- Trends views tests: 37 passed ✅
- Code formatted with ruff ✅

---

## Key Files for Next Session

| File | Purpose |
|------|---------|
| `templates/metrics/analytics/trends.html` | Alpine.js granularity toggle, hidden inputs |
| `apps/metrics/views/trends_views.py` | `_get_trends_context()`, default date range logic |
| `templates/metrics/analytics/trends/tech_chart.html` | Tech chart partial |
| `templates/metrics/analytics/trends/pr_type_chart.html` | PR Type chart partial |

---

## Definition of Done for Phase 5

- [ ] Weekly granularity toggle works - clicking Weekly changes all charts
- [ ] Default time range is "Last 12 Months" (rolling 365 days)
- [ ] All existing tests still pass
- [ ] Code formatted with ruff
