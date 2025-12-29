# HTMX + Alpine.js Integration Refactoring Plan

**Last Updated:** 2025-12-29
**Status:** Planning Complete - Ready for Implementation
**Branch:** `htmx-refactor` (git worktree)
**TDD Mode:** Strict Red-Green-Refactor

---

## Executive Summary

Refactor the frontend integration layer to fix 5 critical issues causing "constant HTMX integration issues":
1. Inline scripts in HTMX partials don't execute
2. No global HTMX error handling
3. Alpine.js state lost on HTMX swap
4. Time range button highlighting not updating
5. Inconsistent chart initialization patterns

**Estimated Effort:** ~20-30 hours across 4 phases

---

## Implementation Approach

### TDD Workflow (Strict)

For each feature:
1. **RED**: Write failing E2E/unit test that describes expected behavior
2. **GREEN**: Implement minimum code to make test pass
3. **REFACTOR**: Clean up while keeping tests green

### Git Worktree Strategy

```bash
# Create worktree for isolated development
git worktree add ../tformance-htmx-refactor -b htmx-refactor

# Work in worktree
cd ../tformance-htmx-refactor

# When complete, merge back
git checkout main
git merge htmx-refactor
git worktree remove ../tformance-htmx-refactor
```

---

## Phase 1: Critical Fixes (~6 hours)

### 1.1 Global HTMX Error Handling

**Goal:** Failed HTMX requests show user-friendly error instead of infinite spinner

**TDD Sequence:**
1. Write E2E test: Mock failing endpoint, assert error message appears
2. Implement error handler in `htmx.js`
3. Verify test passes

**Files:**
- `tests/e2e/htmx-error-handling.spec.ts` (new)
- `assets/javascript/htmx.js`

**Acceptance Criteria:**
- [ ] E2E test for error handling passes
- [ ] Error message uses safe DOM methods (createElement, textContent)
- [ ] Console logs error details for debugging
- [ ] Works for both 4xx and 5xx errors

### 1.2 Wide Chart Inline Script Fix

**Goal:** Remove inline script from wide_chart.html, move to centralized app.js

**TDD Sequence:**
1. Write E2E test: Navigate to trends, change granularity, assert chart re-renders
2. Move chart init logic to app.js
3. Remove inline script from template
4. Verify test passes

**Files:**
- `tests/e2e/trends-charts.spec.ts` (existing - add test)
- `templates/metrics/analytics/trends/wide_chart.html`
- `assets/javascript/app.js`

**Acceptance Criteria:**
- [ ] No inline `<script>` in wide_chart.html
- [ ] Chart renders on initial page load
- [ ] Chart re-renders after HTMX swap
- [ ] E2E test passes

### 1.3 Time Range Button Highlighting

**Goal:** 7d/30d/90d buttons update visual state after HTMX navigation

**TDD Sequence:**
1. Write E2E test: Click 90d, navigate tabs, assert 90d still highlighted
2. Add afterSwap handler to call updateTimeRangeButtons()
3. Verify test passes

**Files:**
- `tests/e2e/htmx-navigation.spec.ts` (new)
- `templates/metrics/analytics/base_analytics.html`

**Acceptance Criteria:**
- [ ] Button highlighting persists after tab navigation
- [ ] Works with browser back/forward
- [ ] E2E test passes

---

## Phase 2: Alpine.js State Management (~8 hours)

### 2.1 Alpine.store() Implementation

**Goal:** Implement global stores for date range and metrics selection

**TDD Sequence:**
1. Write unit test for store initialization and methods
2. Implement stores in alpine.js
3. Verify tests pass

**Files:**
- `tests/javascript/alpine-stores.test.js` (new)
- `assets/javascript/alpine.js`

**Stores to Create:**
- `$store.dateRange` - days, preset, granularity, customStart, customEnd
- `$store.metrics` - selected metrics array, toggle method

**Acceptance Criteria:**
- [ ] Stores initialize before Alpine.start()
- [ ] Store methods work correctly (unit tests)
- [ ] State persists across HTMX swaps (E2E test)

### 2.2 Alpine Re-initialization on HTMX Swap

**Goal:** Newly swapped content initializes Alpine components

**TDD Sequence:**
1. Write E2E test: HTMX swap brings in Alpine component, verify it works
2. Add Alpine.initTree() call in htmx:afterSwap handler
3. Verify test passes

**Files:**
- `tests/e2e/alpine-htmx-integration.spec.ts` (new)
- `assets/javascript/htmx.js`

**Acceptance Criteria:**
- [ ] Alpine components in swapped content initialize
- [ ] Existing Alpine components not affected
- [ ] No duplicate initialization

### 2.3 Date Range Picker Refactor

**Goal:** Replace inline Alpine.data with store-based approach

**TDD Sequence:**
1. Write E2E test: Full date picker workflow (7d, 30d, custom range)
2. Extract Alpine.data to JS module
3. Refactor template to use $store
4. Verify test passes

**Files:**
- `tests/e2e/date-range-picker.spec.ts` (new)
- `assets/javascript/components/date-range-picker.js` (new)
- `templates/metrics/partials/date_range_picker.html`

**Acceptance Criteria:**
- [ ] No inline `<script>` in date_range_picker.html
- [ ] All date picker functionality works
- [ ] State persists after HTMX navigation
- [ ] E2E tests pass

---

## Phase 3: Centralized Chart Management (~10 hours)

### 3.1 ChartManager Class

**Goal:** Single source of truth for chart initialization

**TDD Sequence:**
1. Write unit tests for ChartManager class
2. Implement ChartManager with registry pattern
3. Verify tests pass

**Files:**
- `tests/javascript/chart-manager.test.js` (new)
- `assets/javascript/dashboard/chart-manager.js` (new)

**ChartManager API:**
```javascript
chartManager.register(canvasId, createFn)
chartManager.init(canvasId)
chartManager.destroy(canvasId)
chartManager.initAll()
```

**Acceptance Criteria:**
- [ ] ChartManager handles registration
- [ ] Safe destruction of existing charts
- [ ] Auto-init on htmx:afterSwap
- [ ] Unit tests pass

### 3.2 Migrate Existing Charts

**Goal:** Move all chart init logic to ChartManager

**TDD Sequence:**
1. E2E tests already exist for charts (ensure they pass)
2. Register each chart type with ChartManager
3. Remove inline scripts and app.js handlers
4. Verify E2E tests still pass

**Charts to Migrate:**
- AI Adoption chart
- Cycle Time chart
- Review Time chart
- Copilot Trend chart
- PR Type chart
- Tech chart
- Wide Trend chart

**Acceptance Criteria:**
- [ ] All charts registered with ChartManager
- [ ] No inline chart initialization scripts
- [ ] All existing E2E tests pass
- [ ] Charts render correctly in all analytics pages

### 3.3 Declarative Data Attributes

**Goal:** Charts use data attributes for configuration

**Pattern:**
```html
<canvas data-chart-type="bar"
        data-chart-data-id="chart-data-json"
        data-chart-options='{"stacked": true}'>
</canvas>
```

**Files:**
- All chart partial templates
- `assets/javascript/dashboard/chart-manager.js`

**Acceptance Criteria:**
- [ ] Charts configured via data attributes
- [ ] ChartManager reads data attributes
- [ ] Backward compatible with existing charts

---

## Phase 4: Documentation & Cleanup (~4 hours)

### 4.1 CLAUDE.md Update

**Goal:** Document HTMX + Alpine patterns for future development

**Sections to Add:**
- HTMX Integration Patterns
- Alpine.js Store Usage
- Chart Management via ChartManager
- Common Pitfalls (inline scripts, state loss)

**Files:**
- `CLAUDE.md`

### 4.2 Code Cleanup

**Goal:** Remove dead code and unused patterns

**Tasks:**
- Remove unused inline scripts
- Remove duplicate chart initialization code
- Clean up unused Alpine.data definitions

### 4.3 E2E Test Suite Consolidation

**Goal:** Comprehensive E2E test coverage for HTMX flows

**Files:**
- `tests/e2e/htmx-integration.spec.ts` (consolidate)

**Test Coverage:**
- [ ] Error handling
- [ ] Tab navigation
- [ ] Date range changes
- [ ] Chart rendering
- [ ] State persistence

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Alpine.store breaks existing pages | Test each page individually before moving on |
| Chart timing issues | MutationObserver as fallback |
| Worktree merge conflicts | Regular rebases from main |
| E2E test flakiness | Add retries and waits |

---

## Success Metrics

- [ ] All E2E tests pass
- [ ] No inline scripts in HTMX partials
- [ ] No JavaScript console errors on any analytics page
- [ ] State persists across navigation
- [ ] Charts render reliably after HTMX swaps
