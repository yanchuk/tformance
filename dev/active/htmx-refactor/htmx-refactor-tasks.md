# HTMX Refactoring - Task Checklist

**Last Updated:** 2025-12-30
**Status:** Phases 1-2 Complete, Phase 3 Ready

---

## Setup

- [x] Create git worktree: `git worktree add ../tformance-htmx-refactor -b htmx-refactor`
- [x] Navigate to worktree: `cd ../tformance-htmx-refactor`
- [x] Verify dev server runs: `make dev`
- [x] Verify existing tests pass: `make test && make e2e`

---

## Phase 1: Critical Fixes ✅ COMPLETE

### 1.1 Global HTMX Error Handling ✅

**TDD RED Phase:**
- [x] Create `tests/e2e/htmx-error-handling.spec.ts`
- [x] Write test: Mock 500 response, assert error message appears
- [x] Write test: Mock 404 response, assert error message appears
- [x] Write test: Assert retry button present
- [x] Run tests - verify they FAIL

**TDD GREEN Phase:**
- [x] Edit `assets/javascript/htmx.js`
- [x] Add `htmx:afterRequest` event listener (for 4xx/5xx)
- [x] Add `htmx:sendError` event listener (network errors)
- [x] Create error UI using safe DOM methods (createElement, textContent)
- [x] Run tests - verify they PASS

**TDD REFACTOR Phase:**
- [x] Extract error UI creation to helper function
- [x] Add console.error for debugging
- [x] Run tests - verify still PASS

### 1.2 Wide Chart Inline Script Fix ✅

**TDD RED Phase:**
- [x] Add test to `tests/e2e/trends-charts.spec.ts`
- [x] Test: Navigate to trends, change granularity, assert chart canvas exists
- [x] Test: Assert no console errors
- [x] Run tests - verify they FAIL (or pass - baseline)

**TDD GREEN Phase:**
- [x] Create `initWideTrendChart()` function in `assets/javascript/app.js`
- [x] Move chart creation logic from `wide_chart.html:57-109`
- [x] Add call to `initWideTrendChart()` in htmx:afterSwap handler
- [x] Export function globally: `window.initWideTrendChart = initWideTrendChart`
- [x] Remove inline `<script>` from `templates/metrics/analytics/trends/wide_chart.html`
- [x] Run tests - verify they PASS

**TDD REFACTOR Phase:**
- [x] Ensure chart destruction before re-creation
- [x] Clean up any unused code
- [x] Run tests - verify still PASS

### 1.3 Time Range Button Highlighting ✅

**TDD RED Phase:**
- [x] Create `tests/e2e/htmx-navigation.spec.ts`
- [x] Test: Click 90d, navigate to Quality tab, assert 90d button is highlighted
- [x] Test: Use browser back, assert button state preserved
- [x] Run tests - verify they FAIL

**TDD GREEN Phase:**
- [x] Verified: Button highlighting already works via Alpine store binding
- [x] No additional changes needed - Alpine stores handle state persistence
- [x] Run tests - verify they PASS

---

## Phase 2: Alpine.js State Management ✅ COMPLETE

### 2.1 Alpine.store() Implementation ✅

**TDD RED Phase:**
- [x] Create E2E tests for store behavior in `tests/e2e/alpine-htmx-integration.spec.ts`
- [x] Test: dateRange store initializes with defaults
- [x] Test: dateRange.setDays() updates days and clears preset
- [x] Test: dateRange.setPreset() updates preset and clears days
- [x] Test: metrics store toggle() adds/removes metrics
- [x] Test: metrics store respects maxMetrics
- [x] Run tests - verify they FAIL

**TDD GREEN Phase:**
- [x] Edit `assets/javascript/alpine.js`
- [x] Add `alpine:init` event listener
- [x] Create `Alpine.store('dateRange', {...})`
- [x] Create `Alpine.store('metrics', {...})`
- [x] Run tests - verify they PASS

**TDD REFACTOR Phase:**
- [x] Store definitions kept in alpine.js (reasonable size)
- [x] Run tests - verify still PASS

### 2.2 Alpine Re-initialization on HTMX Swap ✅

**TDD RED Phase:**
- [x] Tests in `tests/e2e/alpine-htmx-integration.spec.ts`
- [x] Test: HTMX swap brings Alpine components, verify they work
- [x] Run tests - verify they FAIL

**TDD GREEN Phase:**
- [x] Edit `assets/javascript/htmx.js`
- [x] Add `htmx:afterSwap` handler
- [x] Call `Alpine.initTree(evt.detail.target)` if Alpine available
- [x] Run tests - verify they PASS

**TDD REFACTOR Phase:**
- [x] Added null check for window.Alpine
- [x] Run tests - verify still PASS

### 2.3 Date Range Picker Refactor ✅

**TDD RED Phase:**
- [x] Tests in `tests/e2e/alpine-htmx-integration.spec.ts` (date picker tests)
- [x] Test: Click 7d, assert URL updates
- [x] Test: Navigate away and back, assert date range preserved
- [x] Run tests - verify baseline behavior

**TDD GREEN Phase:**
- [x] Create `assets/javascript/components/date-range-picker.js`
- [x] Extract Alpine.data('dateRangePicker', ...) from template
- [x] Register component using Alpine.data() in alpine.js
- [x] Component uses $store.dateRange for shared state
- [x] Remove inline script from `templates/metrics/partials/date_range_picker.html`
- [x] Run tests - verify they PASS

**TDD REFACTOR Phase:**
- [x] Clean separation: UI state in component, shared state in store
- [x] Run tests - verify still PASS

---

## Phase 3: Centralized Chart Management (~10 hours) 🔜 NEXT

### 3.1 ChartManager Class

**TDD RED Phase:**
- [ ] Create `tests/javascript/chart-manager.test.js` (or E2E test approach)
- [ ] Test: register() adds chart to registry
- [ ] Test: init() creates chart on canvas
- [ ] Test: init() destroys existing chart first
- [ ] Test: destroy() removes chart instance
- [ ] Test: initAll() initializes all registered charts
- [ ] Run tests - verify they FAIL

**TDD GREEN Phase:**
- [ ] Create `assets/javascript/dashboard/chart-manager.js`
- [ ] Implement ChartManager class with Map registry
- [ ] Implement register(canvasId, createFn)
- [ ] Implement init(canvasId) with Chart.getChart() for destruction
- [ ] Implement destroy(canvasId)
- [ ] Implement initAll()
- [ ] Export singleton instance
- [ ] Run tests - verify they PASS

**TDD REFACTOR Phase:**
- [ ] Add error handling for missing canvas
- [ ] Add logging for debugging
- [ ] Run tests - verify still PASS

### 3.2 Migrate Existing Charts

**Pre-check:**
- [ ] Ensure `tests/e2e/trends-charts.spec.ts` passes
- [ ] Ensure dashboard charts render correctly

**Migrate PR Type Chart:**
- [ ] Register PR type chart with ChartManager
- [ ] Remove `initPrTypeChart()` from app.js afterSwap
- [ ] Verify E2E tests still pass

**Migrate Tech Chart:**
- [ ] Register tech chart with ChartManager
- [ ] Remove `initTechChart()` from app.js afterSwap
- [ ] Verify E2E tests still pass

**Migrate Dashboard Charts:**
- [ ] Register AI Adoption chart
- [ ] Register Cycle Time chart
- [ ] Register Review Time chart
- [ ] Register Copilot Trend chart
- [ ] Remove individual handlers from app.js
- [ ] Verify E2E tests still pass

**Migrate Wide Trend Chart:**
- [ ] Register with ChartManager (use initWideTrendChart)
- [ ] Remove from afterSwap handler
- [ ] Verify E2E tests still pass

**Post-check:**
- [ ] All E2E tests pass
- [ ] No duplicate chart instances (check dev tools)

### 3.3 Declarative Data Attributes

**TDD RED Phase:**
- [ ] Add test: Chart with data-chart-type renders correctly
- [ ] Add test: Chart reads options from data-chart-options
- [ ] Run tests - verify they FAIL

**TDD GREEN Phase:**
- [ ] Modify ChartManager to read data-chart-type attribute
- [ ] Modify ChartManager to read data-chart-data-id attribute
- [ ] Modify ChartManager to parse data-chart-options JSON
- [ ] Update one chart template to use attributes (test template)
- [ ] Run tests - verify they PASS

**TDD REFACTOR Phase:**
- [ ] Update remaining chart templates to use data attributes
- [ ] Run tests - verify still PASS

---

## Phase 4: Documentation & Cleanup (~4 hours)

### 4.1 CLAUDE.md Update

- [ ] Add "## HTMX Integration Patterns" section
- [ ] Document: Never use inline scripts in HTMX partials
- [ ] Document: Use htmx:afterSwap for post-swap initialization
- [ ] Document: Use Alpine.store() for persistent state
- [ ] Document: Use ChartManager for chart initialization
- [ ] Add code examples for each pattern

### 4.2 Code Cleanup

- [ ] Remove unused initPrTypeChart from app.js (after ChartManager migration)
- [ ] Remove unused initTechChart from app.js (after ChartManager migration)
- [ ] Remove any remaining inline scripts
- [ ] Clean up unused Alpine.data definitions
- [ ] Run linter: `make ruff`

### 4.3 E2E Test Consolidation

- [ ] Create `tests/e2e/htmx-integration.spec.ts`
- [ ] Move related tests from individual files
- [ ] Add comprehensive test suite for HTMX flows
- [ ] Verify all tests pass: `make e2e`

---

## Final Validation

- [ ] All E2E tests pass: `make e2e`
- [ ] All unit tests pass: `make test`
- [ ] No console errors on any analytics page
- [ ] Charts render correctly after navigation
- [ ] State persists across tab changes
- [ ] Error handling works for failed requests

---

## Merge & Cleanup

- [ ] Commit all changes with descriptive messages
- [ ] Push branch: `git push -u origin htmx-refactor`
- [ ] Create PR for review
- [ ] After approval, merge to main
- [ ] Remove worktree: `git worktree remove ../tformance-htmx-refactor`
- [ ] Delete remote branch after merge

---

## Session Notes

### 2025-12-30 Session
- Completed Phases 1 and 2 (all 6 tasks)
- 78 E2E tests passing across all browsers/devices
- Key files created:
  - `assets/javascript/components/date-range-picker.js`
  - `tests/e2e/htmx-error-handling.spec.ts`
  - `tests/e2e/htmx-navigation.spec.ts`
  - `tests/e2e/alpine-htmx-integration.spec.ts`
- Commits made on `htmx-refactor` branch
- Ready to start Phase 3: ChartManager

### Commands to Resume
```bash
cd /Users/yanchuk/Documents/GitHub/tformance-htmx-refactor
npm run build
DJANGO_VITE_DEV_MODE=False DEBUG=True .venv/bin/python manage.py runserver 8000 &
sleep 3
npx playwright test tests/e2e/alpine-htmx-integration.spec.ts --reporter=list
```
