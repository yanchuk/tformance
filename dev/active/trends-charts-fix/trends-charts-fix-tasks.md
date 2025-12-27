# Trends Charts Fix - Tasks

## Overview

Fix the Trends page charts: make PR Types and Technology Breakdown render as full-width stacked bar charts, and fix the 500 error on the benchmark endpoint.

---

## Phase 1: Fix Benchmark 500 Error

- [ ] Reproduce the 500 error locally by hitting `/app/metrics/panels/benchmark/cycle_time/?days=359`
- [ ] Check Django logs for the actual exception
- [ ] Fix the issue in `benchmark_service.get_benchmark_for_team()` or `chart_views.benchmark_panel()`
- [ ] Add error handling for edge cases (no benchmark data, invalid days param)
- [ ] Test with various `days` values (30, 90, 359)

---

## Phase 2: Debug Chart Rendering Issue

- [ ] Add console.log statements to pr_type_chart.html and tech_chart.html to trace execution
- [ ] Verify chart_data JSON is being output correctly by the `json_script` filter
- [ ] Check if canvas elements exist in DOM after HTMX swap
- [ ] Verify Chart.js is available when the inline script runs
- [ ] Identify why charts aren't rendering (DOM, timing, or data issue)

---

## Phase 3: Make Charts Full-Width

Update `trends.html` to display PR Types and Technology charts as full-width stacked bar charts instead of side-by-side.

**Current Layout:**
```html
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <!-- PR Type Breakdown (half width) -->
  <!-- Technology Breakdown (half width) -->
</div>
```

**Target Layout:**
```html
<!-- PR Type Breakdown (full width) -->
<div class="app-card p-0 overflow-hidden">
  <div id="pr-type-chart-container" hx-get="..." hx-trigger="load">
  </div>
</div>

<!-- Technology Breakdown (full width) -->
<div class="app-card p-0 overflow-hidden">
  <div id="tech-chart-container" hx-get="..." hx-trigger="load">
  </div>
</div>
```

Tasks:
- [ ] Remove the 2-column grid wrapper from trends.html
- [ ] Make each chart container full-width like wide_chart.html
- [ ] Increase chart height from 280px to 320px to match the main chart
- [ ] Update partial templates to match wide_chart.html styling

---

## Phase 4: Fix Chart.js Initialization

The inline `<script>` in HTMX-swapped partials may not execute properly. Fix the chart initialization.

**Option A: Use HTMX `afterSwap` event**
```javascript
document.body.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target.id === 'pr-type-chart-container') {
    initPrTypeChart();
  }
});
```

**Option B: Move chart init to main app.js**
Register chart initialization functions globally and call them after HTMX swap.

Tasks:
- [ ] Choose approach (A or B)
- [ ] Implement chart initialization fix
- [ ] Test chart renders on initial load
- [ ] Test chart re-renders on granularity change

---

## Phase 5: Improve Chart Styling

Match the PR Type and Tech charts to the main trend chart styling:

- [ ] Use same font families (DM Sans for labels, JetBrains Mono for values)
- [ ] Match color palette with chart-theme.js
- [ ] Add "Scroll to zoom, drag to pan" hint like wide_chart.html
- [ ] Add Reset Zoom button if interactive

---

## Phase 6: Testing

- [ ] Test all 3 charts render on page load
- [ ] Test granularity toggle (weekly/monthly) updates all charts
- [ ] Test date range presets (7d, 30d, 90d, This Year)
- [ ] Test benchmark panel loads without error
- [ ] Verify responsive layout on mobile

---

## Files to Modify

1. `templates/metrics/analytics/trends.html` - Layout changes
2. `templates/metrics/analytics/trends/pr_type_chart.html` - Chart init fix
3. `templates/metrics/analytics/trends/tech_chart.html` - Chart init fix
4. `apps/metrics/views/chart_views.py` - Benchmark error handling
5. `apps/metrics/services/benchmark_service.py` - Fix 500 error
6. `assets/javascript/app.js` - Global chart init (if Option B)

---

## Definition of Done

- [ ] PR Types Over Time renders as a full-width stacked bar chart
- [ ] Technology Breakdown renders as a full-width stacked bar chart
- [ ] Industry Benchmark panel loads without 500 error
- [ ] Granularity toggle updates all charts correctly
- [ ] No console errors on page load
- [ ] All existing trends tests pass
