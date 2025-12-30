# Trends Charts Fix - Context

**Last Updated:** 2025-12-30 (Session 5 - End)
**Status:** Phase 5 In Progress - Two New Bugs Reported

---

## Session 5 Progress (2025-12-30)

### Commits Made This Session

1. **`3b58e76`** - Add AI Assisted filter to Tech/PR Type charts and fix granularity bug
   - AI Assisted filter (All/No/Yes) on Tech and PR Type charts
   - Fix for granularity being lost on AI filter click (hidden inputs + hx-include fix)
   - avg_review_time added to get_key_metrics()
   - Zoom disabled on comparison chart

2. **`be6c8a4`** - Remove zoom controls and instructions from Trends charts
   - Removed Reset Zoom button (refresh icon)
   - Removed "Scroll to zoom, drag to pan" instructions
   - Removed zoom tip from Tips section

### New Bugs Reported (Need Implementation)

#### Bug 1: Weekly Grouping Not Working
**Symptom:** Clicking "Weekly" granularity toggle does nothing - chart doesn't change

**Investigation Needed:**
- Check if `setGranularity()` function is being called
- Verify hidden input is being updated
- Check if HTMX request is being triggered for chart partials
- Verify the granularity parameter is reaching the views

**Suspected Areas:**
- `templates/metrics/analytics/trends.html` - Alpine.js `setGranularity()` function
- The function calls `updateUrlAndChart()` which triggers HTMX for wide chart
- BUT Tech/PR Type charts may not be re-fetching on granularity change

**Key Code (trends.html lines 41-47):**
```javascript
setGranularity(g) {
  this.granularity = g;
  // Update hidden input for HTMX hx-include
  const hiddenInput = document.querySelector('input[name=granularity]');
  if (hiddenInput) hiddenInput.value = g;
  this.updateUrlAndChart();
},
```

**Potential Issue:** `updateChart()` only refreshes the wide trend chart and benchmark panel. It does NOT refresh the Tech Breakdown or PR Type charts! They only get refreshed via the `@htmx:afterSwap.window` event handler on the parent div.

#### Bug 2: Default Time Range Should Be "Last 12 Months" Not "Last Year"
**Symptom:** Default shows "Last Year" preset instead of "Last 12 Months"

**Current Behavior:**
- Default uses `preset=12_months` which shows 365 days of data
- User wants "Last 12 months" (rolling 12 months from today)

**Investigation Needed:**
- Check what `preset=12_months` actually does in `_get_trends_context()`
- May need to differentiate between "This Year" (Jan 1 - today) vs "Last 12 Months" (today - 365 days)
- Verify the date range calculation

**Key File:** `apps/metrics/views/trends_views.py` - `_get_trends_context()` function

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `templates/metrics/analytics/trends/wide_chart.html` | Removed Reset Zoom button and zoom instructions |
| `templates/metrics/analytics/trends.html` | Removed zoom tip from Tips section |

---

## Key Code Locations for Next Session

### Weekly Granularity Bug

| File | Location | Purpose |
|------|----------|---------|
| `trends.html` | Lines 41-68 | Alpine.js `setGranularity()` and `updateChart()` functions |
| `trends.html` | Lines 130-137 | `@htmx:afterSwap.window` event handler for Tech/PR charts |
| `trends_views.py` | `_get_trends_context()` | Granularity parameter handling |
| `trends_views.py` | `tech_breakdown_chart()` | Tech chart view with granularity param |
| `trends_views.py` | `pr_type_breakdown_chart()` | PR Type chart view with granularity param |

### Default Time Range Bug

| File | Location | Purpose |
|------|----------|---------|
| `trends_views.py` | `_get_trends_context()` | Default preset and date range calculation |
| `trends_views.py` | `trends_view()` | Main view that sets defaults |
| `apps/metrics/views/base_views.py` | Date range mixin/helper | May have preset definitions |

---

## Commands to Run on Resume

```bash
# Verify tests still pass
make test ARGS='apps.metrics.tests.test_trends_views'
make test ARGS='apps.metrics.tests.dashboard'

# Check for uncommitted changes
git status

# Start dev server for manual testing
make dev

# Test in browser
# Navigate to /a/{team}/metrics/analytics/trends/
# 1. Click Weekly granularity - verify charts change
# 2. Check default date range is "Last 12 Months"
```

---

## Handoff Notes for Next Session

### Immediate Priority
1. **Fix Weekly Granularity Toggle** - User clicks Weekly but nothing changes
2. **Fix Default Time Range** - Should be "Last 12 Months" rolling, not calendar year

### Investigation Steps for Bug 1 (Weekly Granularity)
1. Add console.log to `setGranularity()` to verify it's being called
2. Check if hidden input is being updated via browser DevTools
3. Verify HTMX request URL includes `granularity=weekly`
4. Check if Tech/PR charts are being refreshed (they rely on `@htmx:afterSwap.window` event)

### Investigation Steps for Bug 2 (Default Range)
1. Check `_get_trends_context()` default values
2. Verify `preset=12_months` means rolling 12 months vs calendar year
3. May need to add new preset or change default behavior

### Test Results Status
- 221 dashboard tests pass
- 37 trends views tests pass
- All code formatted with ruff
- No uncommitted production code changes (only dev docs)

---

## Previous Session Context (Session 4)

### Completed Features
- AI Assisted filter for Tech Breakdown and PR Types (All/No/Yes)
- Filter uses `effective_is_ai_assisted` property (LLM data priority)
- Fixed `avg_review_time` in `get_key_metrics()`
- Fixed granularity bug when clicking AI filter buttons
- Disabled zoom on comparison chart
- Removed zoom controls and instructions

### Hidden Inputs Fix
Added hidden inputs to `trends.html` for HTMX hx-include:
```html
<input type="hidden" name="days" value="{{ days }}">
<input type="hidden" name="preset" value="{{ preset }}">
<input type="hidden" name="start" value="{{ start_date|date:'Y-m-d' }}">
<input type="hidden" name="end" value="{{ end_date|date:'Y-m-d' }}">
<input type="hidden" name="granularity" value="{{ granularity }}">
```

And updated `setGranularity()` to sync hidden input when toggle clicked.
