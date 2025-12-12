# Chart Visualization Fixes - Context

**Last Updated**: 2025-12-12
**Status**: Partially Complete (data working, visualization needs work)

## Session Summary

This session focused on fixing dashboard chart rendering issues discovered during Playwright testing.

## Problems Discovered & Fixed

### 1. Date Format Mismatch (FIXED)
- **File**: `apps/metrics/services/chart_formatters.py`
- **Issue**: `isoformat()` returned full ISO timestamps (`2025-11-10T00:00:00+00:00`)
- **Problem**: JavaScript `listToDict` created keys with full ISO, but lookup used `YYYY-MM-DD`
- **Fix**: Changed to `strftime("%Y-%m-%d")` for Chart.js compatibility

### 2. String vs Number Values (FIXED)
- **File**: `apps/metrics/services/chart_formatters.py`
- **Issue**: Django Decimal fields serialize as strings in JSON
- **Problem**: Count values like `"40.0000"` instead of `40.0`
- **Fix**: Added `float(count_value)` conversion

### 3. Daily Interpolation Issue (FIXED)
- **File**: `assets/javascript/dashboard/dashboard-charts.js`
- **Issue**: `barChartWithDates` iterates EVERY day, but data has weekly points
- **Problem**: 29 bars where only 5 have data, bars too thin to see
- **Fix**: Added new `weeklyBarChart(ctx, data, label)` function that uses data points directly

### 4. HTMX afterSwap Handler (PARTIALLY WORKING)
- **File**: `assets/javascript/app.js`
- **Added**: Event listener for `htmx:afterSwap` to initialize charts
- **Added**: `destroyChartIfExists(canvas)` helper using `Chart.getChart()`
- **Issue**: Charts create successfully but don't render visibly
- **Root cause**: Likely timing/canvas replacement issue with multiple HTMX swaps

## Files Modified

| File | Changes |
|------|---------|
| `apps/metrics/services/chart_formatters.py` | Date format + float conversion |
| `assets/javascript/app.js` | afterSwap handler + destroy helper |
| `assets/javascript/dashboard/dashboard-charts.js` | Added `weeklyBarChart` function |

## What Works

- All dashboard DATA displays correctly (cards, tables, stats)
- Chart data is formatted correctly (verified via browser console)
- `weeklyBarChart` function works when called manually
- All 361 metrics tests pass

## What Needs Work

- Charts don't render automatically on page load
- HTMX afterSwap timing issue with multiple concurrent swaps
- Possible solutions:
  1. Add inline scripts to chart partials that call `weeklyBarChart`
  2. Use HTMX extension for script execution
  3. Add `hx-on::after-swap` attribute to chart containers

## Key Learnings

1. **HTMX doesn't execute inline scripts** by default after swap (security)
2. **Chart.js canvas reuse** requires explicit `.destroy()` before recreation
3. **Django Decimal → JSON** serializes as strings, need explicit float conversion
4. **Date formats matter** - Chart.js time scales need consistent format

## Commit Made

```
ed40fa8 Fix chart data formatting and add weekly chart support
```

## Next Steps (Priority Order)

1. Fix chart initialization - add inline script to partials OR use hx-on attribute
2. Consider using chart partials with `<script>` that checks for `weeklyBarChart` availability
3. Test with 7-day and 90-day ranges

## Commands to Verify

```bash
make test ARGS='apps.metrics.tests --keepdb'  # All pass
curl http://localhost:8000/  # Dev server running
```
