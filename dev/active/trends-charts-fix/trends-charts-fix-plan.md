# Trends Charts Fix - Implementation Plan

## Summary

Fix three issues on the Trends page (`/app/metrics/analytics/trends/`):
1. PR Types Over Time and Technology Breakdown charts not rendering
2. Layout wrong - charts should be full-width, not side-by-side
3. Industry Benchmark endpoint returns 500 error

## Validation

**E2E Test Created:** `tests/e2e/trends-charts.spec.ts`
- Tests will FAIL until fixes are implemented (TDD approach)
- Run with: `npx playwright test trends-charts.spec.ts` (requires AUTH_MODE=all)

---

## Phase 1: Fix Benchmark 500 Error (Priority: High)

### Root Cause Analysis
The benchmark endpoint `/app/metrics/panels/benchmark/cycle_time/?days=359` returns 500. Need to identify:
- Missing error handling for edge cases
- Null reference when no benchmark data exists
- Query issues with large day ranges

### Implementation Steps

1. **Reproduce and Debug**
   ```bash
   curl -v "http://localhost:8000/app/metrics/panels/benchmark/cycle_time/?days=359"
   ```
   - Check Django logs for exception traceback
   - Identify exact line causing 500

2. **Fix Error Handling** in `apps/metrics/views/chart_views.py:505`
   ```python
   def benchmark_panel(request):
       try:
           benchmark_data = benchmark_service.get_benchmark_for_team(...)
           if not benchmark_data:
               return render(request, 'metrics/panels/benchmark_empty.html')
           return render(request, 'metrics/panels/benchmark.html', {'data': benchmark_data})
       except Exception as e:
           logger.error(f"Benchmark panel error: {e}")
           return render(request, 'metrics/panels/benchmark_error.html')
   ```

3. **Fix Service Layer** in `apps/metrics/services/benchmark_service.py`
   - Add null checks for missing IndustryBenchmark records
   - Handle edge case of days > 365

### Files to Modify
- `apps/metrics/views/chart_views.py` - Add try/except, null handling
- `apps/metrics/services/benchmark_service.py` - Add defensive checks
- `templates/metrics/panels/benchmark_error.html` - Create error template (optional)

---

## Phase 2: Fix Chart.js Initialization (Priority: High)

### Root Cause Analysis
Charts have canvas elements and data, but Chart.js instances aren't created. The issue is likely:
- Inline `<script>` in HTMX-swapped partials doesn't execute
- Chart.js not loaded when partial script runs
- DOM timing issues with HTMX swap

### Implementation Steps

1. **Verify Data is Present**
   - Add console.log to pr_type_chart.html to trace execution
   - Confirm `{{ chart_data|json_script }}` outputs valid JSON

2. **Fix Script Execution** - Use HTMX `htmx:afterSwap` event:
   ```javascript
   // In main app.js or trends.html
   document.body.addEventListener('htmx:afterSwap', function(evt) {
     if (evt.detail.target.id === 'pr-type-chart-container') {
       initPrTypeChart();
     }
     if (evt.detail.target.id === 'tech-chart-container') {
       initTechChart();
     }
   });
   ```

3. **Alternative: Use `hx-on` Attribute**
   ```html
   <div id="pr-type-chart-container"
        hx-get="..."
        hx-trigger="load"
        hx-on::after-swap="initPrTypeChart()">
   ```

4. **Move Chart Functions to Global Scope**
   - Extract `initPrTypeChart()` and `initTechChart()` to a shared module
   - Register them on `window` or use a chart registry

### Files to Modify
- `templates/metrics/analytics/trends/pr_type_chart.html` - Script execution fix
- `templates/metrics/analytics/trends/tech_chart.html` - Script execution fix
- `assets/javascript/app.js` - Add global chart init functions (if using Option B)

---

## Phase 3: Make Charts Full-Width (Priority: Medium)

### Current Layout (Broken)
```html
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <!-- PR Type Chart - half width on lg screens -->
  <!-- Tech Chart - half width on lg screens -->
</div>
```

### Target Layout (Fixed)
```html
<!-- PR Type Chart - full width -->
<div class="app-card p-0 overflow-hidden mb-6">
  <div id="pr-type-chart-container" hx-get="..." hx-trigger="load">
  </div>
</div>

<!-- Tech Chart - full width -->
<div class="app-card p-0 overflow-hidden">
  <div id="tech-chart-container" hx-get="..." hx-trigger="load">
  </div>
</div>
```

### Implementation Steps

1. **Update trends.html Layout**
   - Remove the 2-column grid wrapper
   - Make each chart container full-width (same as wide_chart.html)

2. **Update Chart Heights**
   - Increase from 280px to 320px to match main chart
   - Add consistent padding and styling

3. **Update Partial Templates**
   - Match header styling with wide_chart.html
   - Ensure responsive canvas sizing

### Files to Modify
- `templates/metrics/analytics/trends.html` - Layout changes
- `templates/metrics/analytics/trends/pr_type_chart.html` - Height, styling
- `templates/metrics/analytics/trends/tech_chart.html` - Height, styling

---

## Phase 4: Polish and Consistency (Priority: Low)

### Implementation Steps

1. **Match Chart Styling**
   - Use DM Sans for labels, JetBrains Mono for values
   - Apply chart-theme.js color palette
   - Add "Scroll to zoom, drag to pan" hint

2. **Add Reset Zoom Button**
   - Match wide_chart.html pattern
   - Position consistently

3. **Test Granularity Toggle**
   - Verify weekly/monthly switch updates all charts
   - Test with various date ranges

### Files to Modify
- `templates/metrics/analytics/trends/pr_type_chart.html` - Zoom controls
- `templates/metrics/analytics/trends/tech_chart.html` - Zoom controls

---

## Testing Strategy

### Unit Tests
No new Django unit tests needed - this is a frontend rendering issue.

### E2E Tests
Created `tests/e2e/trends-charts.spec.ts` with tests for:
- Chart canvas renders with Chart.js instance
- Charts are full-width (not lg:grid-cols-2)
- Benchmark panel loads without 500
- Chart heights are 300px+
- No JavaScript console errors

### Manual Testing
1. Load `/app/metrics/analytics/trends/`
2. Verify all 3 charts render
3. Toggle granularity (weekly/monthly)
4. Test date range presets (7d, 30d, 90d)
5. Check responsive layout on mobile

---

## Definition of Done

- [ ] All tests in `tests/e2e/trends-charts.spec.ts` pass
- [ ] PR Types Over Time renders as full-width stacked bar
- [ ] Technology Breakdown renders as full-width stacked bar
- [ ] Industry Benchmark panel loads without 500 error
- [ ] Granularity toggle updates all charts correctly
- [ ] No console errors on page load
- [ ] Visual consistency with main trend chart

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| HTMX script timing | High | Use htmx:afterSwap event |
| Chart.js version conflict | Medium | Check Chart.js is loaded before init |
| Benchmark service edge cases | Medium | Add comprehensive null checks |
| Mobile layout regression | Low | Test with mobile viewport |

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 1: Benchmark Fix | ~30 min |
| Phase 2: Chart Init Fix | ~45 min |
| Phase 3: Full-Width Layout | ~20 min |
| Phase 4: Polish | ~30 min |
| **Total** | ~2-3 hours |
