# Trends Charts Fix - Context

**Last Updated:** 2025-12-30 (Session 4 - End)
**Status:** Phase 4 Complete, All Bugs Fixed

---

## Session 4 Progress (2025-12-30)

### Completed: AI Assisted Filter Implementation (TDD)

**Phase 1: Tech Breakdown Filter**
- [x] RED: Added 8 failing tests for ai_filter parameter
- [x] GREEN: Implemented `ai_assisted` parameter in 3 service functions:
  - `get_tech_breakdown()`
  - `get_monthly_tech_trend()`
  - `get_weekly_tech_trend()`
- [x] GREEN: Added `ai_filter` to `tech_breakdown_chart` view
- [x] GREEN: Added filter UI buttons to `tech_chart.html`

**Phase 2: PR Type Filter**
- [x] Applied same pattern to 3 service functions:
  - `get_pr_type_breakdown()`
  - `get_monthly_pr_type_trend()`
  - `get_weekly_pr_type_trend()`
- [x] Added `ai_filter` to `pr_type_breakdown_chart` view
- [x] Added filter UI buttons to `pr_type_chart.html`

**Phase 3: Review Time Fix**
- [x] RED: Added tests expecting `avg_review_time` in `get_key_metrics()`
- [x] GREEN: Added `avg_review_time = prs.aggregate(avg=Avg("review_time_hours"))["avg"]` to function
- [x] GREEN: Added key to result dict

### Test Results
- 221 dashboard tests pass
- 57 trends views tests pass
- All code formatted with ruff

---

## BUG FOUND: AI Filter Loses Granularity Parameter

**Reported by user with screenshots**

### Symptoms
1. **Initial state (All filter)**: Shows monthly granularity, 12 months of data (2025-03 to 2025-12)
2. **After clicking "No" filter**: Shows weekly granularity, only 5 weeks (2025-W48 to 2025-W52)
3. **Returning to "All" filter**: Data doesn't match initial state

### Root Cause
The `hx-include` in `tech_chart.html` and `pr_type_chart.html` does NOT include `granularity`:

```html
hx-include="[name='days'],[name='preset'],[name='start'],[name='end']"
```

Missing: `[name='granularity']`

### What Happens
1. Page loads with `preset=12_months` and `granularity=monthly`
2. User clicks "No" AI filter button
3. HTMX request sends date params but NOT granularity
4. View's `_get_trends_context()` has special logic:
   - If `has_date_params=False` (no days/preset/start/end), use 365 days + monthly
   - Otherwise, use 30 days + weekly defaults
5. Since days/preset ARE included, `has_date_params=True` but granularity is lost
6. View uses default weekly granularity instead of monthly

### Fix Applied (Two Parts)

**Part 1:** Added `[name='granularity']` to `hx-include` in both chart templates:
```html
hx-include="[name='days'],[name='preset'],[name='start'],[name='end'],[name='granularity']"
```

**Part 2:** The `hx-include` selectors were looking for inputs that didn't exist! Added hidden inputs to `trends.html`:
```html
<input type="hidden" name="days" value="{{ days }}">
<input type="hidden" name="preset" value="{{ preset }}">
<input type="hidden" name="start" value="{{ start_date|date:'Y-m-d' }}">
<input type="hidden" name="end" value="{{ end_date|date:'Y-m-d' }}">
<input type="hidden" name="granularity" value="{{ granularity }}">
```

**Part 3:** Updated `setGranularity()` in Alpine.js to sync the hidden input:
```javascript
setGranularity(g) {
  this.granularity = g;
  // Update hidden input for HTMX hx-include
  const hiddenInput = document.querySelector('input[name=granularity]');
  if (hiddenInput) hiddenInput.value = g;
  this.updateUrlAndChart();
},
```

**Status:** VERIFIED FIXED with Playwright test

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `apps/metrics/services/dashboard_service.py` | Added `ai_assisted` param to 6 functions, added `avg_review_time` to `get_key_metrics()` |
| `apps/metrics/views/trends_views.py` | Added `ai_filter` param handling to `tech_breakdown_chart` and `pr_type_breakdown_chart` |
| `templates/metrics/analytics/trends.html` | **Added hidden inputs for days/preset/start/end/granularity**, updated setGranularity() |
| `templates/metrics/analytics/trends/tech_chart.html` | Added AI filter button group, fixed hx-include to include granularity |
| `templates/metrics/analytics/trends/pr_type_chart.html` | Added AI filter button group, fixed hx-include to include granularity |
| `apps/metrics/tests/dashboard/test_key_metrics.py` | Added `avg_review_time` tests |
| `apps/metrics/tests/dashboard/test_file_categories.py` | Added AI filter tests |
| `apps/metrics/tests/test_trends_views.py` | Added AI filter view tests |
| `assets/javascript/dashboard/trend-charts.js` | Disabled zoom/pan on comparison chart |

---

## Additional Fixes This Session

### Comparison Chart Zoom Disabled
User requested disabling zoom/pan on the multi-metric comparison chart.

**Fix Applied:** Set `enabled: false` for both pan and zoom in `createMultiMetricChart()`:
- `assets/javascript/dashboard/trend-charts.js:392-405`

### Commands to Verify
```bash
# Rebuild JS
npm run build

# Verify tests still pass
make test ARGS='apps.metrics.tests.dashboard'

# Test manually in browser
# Navigate to /a/{team}/metrics/analytics/trends/
# Click AI filter buttons - granularity should persist
# Comparison chart should not zoom on scroll/pinch
```

---

## Key Code Locations

### AI Filter Implementation

| File | Location |
|------|----------|
| Service functions | `dashboard_service.py:1989-2335` (6 functions with ai_assisted param) |
| View ai_filter handling | `trends_views.py:133-141` and `trends_views.py:196-204` |
| Template filter buttons | `tech_chart.html:19-54` and `pr_type_chart.html:19-54` |
| Review time fix | `dashboard_service.py:169-170` and `dashboard_service.py:183` |

### Bug Location

| File | Line | Issue |
|------|------|-------|
| `tech_chart.html` | 30, 40, 50 | Missing `[name='granularity']` in hx-include |
| `pr_type_chart.html` | 30, 40, 50 | Missing `[name='granularity']` in hx-include |

---

## Verification After Fix

```
http://localhost:8000/a/{team_slug}/metrics/analytics/trends/?preset=12_months&granularity=monthly
```

Expected:
1. Load with monthly granularity (2025-03 to 2025-12 or similar)
2. Click "No" AI filter → Still monthly granularity
3. Click "Yes" AI filter → Still monthly granularity
4. Click "All" AI filter → Same data as initial load
