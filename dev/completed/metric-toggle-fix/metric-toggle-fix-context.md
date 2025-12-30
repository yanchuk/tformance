# Metric Toggle Fix - Context

**Last Updated:** 2025-12-30
**Status:** COMPLETE

---

## Bug Discovery

User reported on Trends & Comparison page:
- Select another metric → shows
- Deselect it → hides
- Select it again → **NOT shown** (checkbox appears unchecked)

**Additional bug found during investigation:**
- 12_months preset not preserved when navigating between tabs (reverted to days=30)

---

## Root Causes

### 1. Array Reactivity Issue

The `toggleMetric()` function used `splice()` and `push()` which modify arrays in-place. Alpine.js sometimes doesn't detect these mutations properly, causing `:checked` bindings to show stale values.

**Fix:** Use immutable operations that create new array references:
- `filter()` instead of `splice()` for removal
- Spread operator `[...arr, item]` instead of `push()` for addition

### 2. Checkbox Click Handler Location

The `@change` handler on the checkbox ran AFTER the browser toggled the checkbox visually, creating a race condition.

**Fix:** Move handler to label with `@click.prevent` to control state entirely through Alpine.

### 3. Preset Not Preserved in Tab Navigation

The tab navigation `getDateParams()` only returned `days`, not `preset`:
```javascript
// BEFORE (broken)
getDateParams() { return JSON.stringify({days: $store.dateRange.days || 30}) }
```

**Fix:** Check for preset first:
```javascript
// AFTER (fixed)
getDateParams() {
  const store = $store.dateRange;
  if (store.preset) {
    return JSON.stringify({ preset: store.preset });
  }
  return JSON.stringify({ days: store.days || 30 });
}
```

---

## Files Modified

| File | Change |
|------|--------|
| `templates/metrics/analytics/trends.html` | Fixed `toggleMetric()`, moved handler to label |
| `assets/javascript/alpine.js` | Fixed `$store.metrics.toggle()` with immutable ops |
| `templates/metrics/analytics/base_analytics.html` | Fixed `getDateParams()` to preserve preset |
| `tests/e2e/metric-toggle.spec.ts` | NEW - 8 E2E tests for metric toggle |
| `tests/e2e/htmx-navigation.spec.ts` | Added preset preservation test |

---

## Test Coverage

E2E tests added (all pass):
- ✅ Metric selection toggles checkbox visual state
- ✅ Metric deselection toggles checkbox visual state
- ✅ Re-selecting a deselected metric shows checkbox as checked
- ✅ Multiple toggle cycles maintain correct state
- ✅ Maximum 3 metrics can be selected
- ✅ At least 1 metric must remain selected
- ✅ URL updates when metric is toggled
- ✅ Chart updates when metric is toggled
- ✅ 12_months preset preserved when navigating between tabs

---

## Session Progress

### Session 1 (2025-12-30)

- [x] Created dev docs (plan, context, tasks)
- [x] Write failing E2E tests (RED phase)
- [x] Fix toggleMetric() in trends.html (GREEN phase)
- [x] Fix $store.metrics.toggle() in alpine.js (REFACTOR phase)
- [x] Fix getDateParams() for preset preservation
- [x] All 47 E2E tests pass
- [x] Ready to commit
