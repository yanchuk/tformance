# Metric Toggle Fix - Plan

**Created:** 2025-12-30
**Status:** In Progress

---

## Problem Statement

On the Trends & Comparison page, metric toggle checkboxes don't properly update visual state after deselect + reselect:

1. Select a metric (e.g., Review Time) → **Shows correctly** (checkbox checked, chart updates)
2. Deselect the metric → **Hides correctly** (checkbox unchecked, chart updates)
3. Select the same metric again → **Bug: checkbox doesn't appear checked**, chart may not update

**URL:** `/app/metrics/analytics/trends/?granularity=monthly&metrics=cycle_time%2Creview_time&preset=12_months`

---

## Root Cause Analysis

The bug is in `templates/metrics/analytics/trends.html` lines 30-38:

```javascript
toggleMetric(id) {
  const idx = this.selectedMetrics.indexOf(id);
  if (idx > -1) {
    if (this.selectedMetrics.length > 1) {
      this.selectedMetrics.splice(idx, 1);  // <-- PROBLEM
    }
  } else if (this.selectedMetrics.length < this.maxMetrics) {
    this.selectedMetrics.push(id);  // <-- PROBLEM
  }
  this.updateUrlAndChart();
}
```

**Issue:** Alpine.js array reactivity can miss in-place mutations (`splice()`, `push()`) in certain scenarios. When the array is modified in place, the reactive system may not detect the change, causing bound elements (`:checked`, `:class`) to show stale values.

---

## Solution

Replace in-place array mutations with immutable operations that create new array references:

```javascript
toggleMetric(id) {
  const idx = this.selectedMetrics.indexOf(id);
  if (idx > -1) {
    if (this.selectedMetrics.length > 1) {
      // Create new array without the item
      this.selectedMetrics = this.selectedMetrics.filter((_, i) => i !== idx);
    }
  } else if (this.selectedMetrics.length < this.maxMetrics) {
    // Create new array with the item added
    this.selectedMetrics = [...this.selectedMetrics, id];
  }
  this.updateUrlAndChart();
}
```

By assigning a new array reference, Alpine.js will always detect the change and update all reactive bindings.

---

## Implementation Steps

### Phase 1: Write Failing E2E Test (RED)
1. Create `tests/e2e/metric-toggle.spec.ts`
2. Test: select → deselect → reselect should show checkbox as checked
3. Test: verify chart updates on each toggle
4. Run test and confirm it fails

### Phase 2: Fix the Bug (GREEN)
1. Update `toggleMetric()` in `trends.html` to use immutable operations
2. Run E2E test and confirm it passes

### Phase 3: Refactor (BLUE)
1. Check if `$store.metrics.toggle()` in `alpine.js` has the same issue
2. Apply same fix if needed
3. Ensure all tests pass

---

## Test Coverage

E2E tests to add:
- [ ] Metric selection toggles checkbox visual state
- [ ] Metric deselection toggles checkbox visual state
- [ ] Re-selecting a deselected metric shows checkbox as checked
- [ ] Chart updates when metric is toggled
- [ ] Maximum 3 metrics can be selected
- [ ] At least 1 metric must remain selected

---

## Files to Modify

| File | Change |
|------|--------|
| `templates/metrics/analytics/trends.html` | Replace `splice()`/`push()` with `filter()`/spread |
| `assets/javascript/alpine.js` | Same fix for `$store.metrics.toggle()` if affected |
| `tests/e2e/metric-toggle.spec.ts` | NEW - E2E tests for metric toggle |
