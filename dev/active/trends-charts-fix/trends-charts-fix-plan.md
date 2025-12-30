# Trends Charts Fix - Implementation Plan (v2)

**Last Updated:** 2025-12-30
**Status:** Planning Phase 2
**Priority:** High
**Estimated Effort:** L (Large)

---

## Executive Summary

The Trends & Comparison page (`/app/metrics/analytics/trends/`) has several bugs and UX improvements needed. Previous session fixed basic chart rendering; this phase addresses 6 remaining issues for a complete ICP experience.

**Key Outcome:** CTOs can compare multiple metrics over time, see percentage-based trend charts for technology/PR type composition, and have a reliable, properly formatted chart experience.

---

## Current State Analysis

### What Was Fixed in Phase 1 (Dec 29)
- [x] Benchmark panel 500 error → Fixed response structure
- [x] Basic chart initialization → Added `initPrTypeChart()`, `initTechChart()` to app.js
- [x] Layout → Already full-width, increased height to 320px
- [x] Inline scripts → Removed from HTMX partials

### New Issues Identified (Dec 30)

| # | Issue | Severity | Root Cause |
|---|-------|----------|------------|
| 1 | Comparison chart blank when multiple metrics selected | Critical | `createMultiMetricChart()` fails when datasets don't match expected format |
| 2 | Technology breakdown shows `{}` entries | Medium | Empty dict categories from `effective_tech_categories` not filtered |
| 3 | Cycle time missing "h" suffix | Low | Format functions not applied in multi-metric tooltip callbacks |
| 4 | PRs Merged stat card not showing + no sparklines | Medium | Missing stat card, sparkline component not integrated |
| 5 | Charts only display after page reload | High | Race condition still exists between HTMX swap and chart init |
| 6 | Need 100% Stacked Area Charts | Feature | ICP needs composition trends, not just absolute bar charts |

---

## Architecture Overview

### Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/views/trends_views.py` | View functions: `trends_overview()`, `wide_trend_chart()`, `pr_type_breakdown_chart()`, `tech_breakdown_chart()` |
| `apps/metrics/services/dashboard_service.py:1989-2184` | Data aggregation for PR types and tech breakdown |
| `templates/metrics/analytics/trends.html` | Main page with Alpine controls |
| `templates/metrics/analytics/trends/wide_chart.html` | Single/multi-metric trend chart partial |
| `templates/metrics/analytics/trends/pr_type_chart.html` | PR type stacked bar partial |
| `templates/metrics/analytics/trends/tech_chart.html` | Technology stacked bar partial |
| `assets/javascript/dashboard/trend-charts.js` | `createMultiMetricChart()`, METRIC_CONFIG |
| `assets/javascript/dashboard/chart-manager.js` | ChartManager, `createStackedBarChart()` |
| `assets/javascript/app.js:88-273` | Chart init functions, HTMX handlers |

### Data Flow

```
User selects metrics → Alpine updates URL params → HTMX GET to wide_trend_chart()
→ View builds {labels, datasets} → Template serializes as JSON
→ htmx:afterSwap fires → chartManager.initAll() → createMultiMetricChart()
```

---

## Implementation Phases

### Phase 2A: Critical Bug Fixes (Issues 1, 5)
**Goal:** Make comparison charts work reliably

### Phase 2B: Data Quality & Formatting (Issues 2, 3)
**Goal:** Clean data and proper unit formatting

### Phase 2C: UX Enhancements (Issue 4)
**Goal:** Add PRs Merged stat card and sparklines

### Phase 2D: 100% Stacked Area Charts (Issue 6)
**Goal:** Better composition trend visualization

---

## Detailed Task Breakdown

### Phase 2A: Critical Bug Fixes

#### Task 2A.1: Fix Multi-Metric Comparison Chart
**Effort:** M
**Files:**
- `assets/javascript/dashboard/trend-charts.js` - `createMultiMetricChart()`
- `apps/metrics/views/trends_views.py` - `wide_trend_chart()`
- `templates/metrics/analytics/trends/wide_chart.html`

**Root Cause Analysis:**
In `trend-charts.js:232-366`, `createMultiMetricChart()` expects:
- `chartData.labels` - array of month/week strings
- `chartData.datasets[].label`, `.data`, `.color`, `.yAxisID`, `.unit`

The view at `trends_views.py:262-278` builds this structure, but:
1. If `ds.unit` is undefined, tooltip formatter fails silently
2. Empty datasets (no data for a metric) cause rendering issues

**Changes:**
1. Add defensive checks in `createMultiMetricChart()`:
   ```javascript
   if (!chartData?.datasets?.length) {
     console.warn('No datasets provided to createMultiMetricChart');
     return null;
   }
   ```
2. Ensure `unit` field is always set in view:
   ```python
   dataset["unit"] = config.get("unit", "")  # Default to empty string
   ```
3. Filter empty datasets before chart creation
4. Add console logging for debugging

**Acceptance Criteria:**
- [ ] Select Cycle Time + Review Time → chart renders with both lines
- [ ] Select all 4 metrics → chart renders with dual Y-axes
- [ ] Console shows helpful warnings if data invalid

#### Task 2A.2: Fix Chart Initialization Race Condition
**Effort:** M
**Files:**
- `assets/javascript/app.js` - `htmx:afterSwap` handler
- `assets/javascript/dashboard/chart-manager.js` - `initAll()`

**Root Cause Analysis:**
The `htmx:afterSwap` handler at `app.js:141-147` calls `chartManager.initAll()` immediately, but:
1. DOM may not be fully settled after HTMX swap
2. JSON script elements may not be accessible yet
3. No retry mechanism for transient failures

**Changes:**
1. Wrap `initAll()` in `requestAnimationFrame`:
   ```javascript
   htmx.on('htmx:afterSwap', (evt) => {
     requestAnimationFrame(() => {
       chartManager.initAll();
     });
   });
   ```
2. Add retry logic with max 3 attempts:
   ```javascript
   initAll(retryCount = 0) {
     const initialized = this._doInit();
     if (!initialized && retryCount < 3) {
       setTimeout(() => this.initAll(retryCount + 1), 100);
     }
   }
   ```
3. Add `data-chart-initialized` attribute to prevent double-init
4. Check canvas exists before each chart creation

**Acceptance Criteria:**
- [ ] Charts render on first HTMX load without page refresh
- [ ] No duplicate chart instances
- [ ] Works across all chart types

### Phase 2B: Data Quality & Formatting

#### Task 2B.1: Filter Empty Dict Entries from Tech Breakdown
**Effort:** S
**Files:**
- `apps/metrics/services/dashboard_service.py` - `get_tech_breakdown()`
- `apps/metrics/views/trends_views.py` - `tech_breakdown_chart()`

**Root Cause Analysis:**
In `dashboard_service.py`, when `pr.effective_tech_categories` returns `{}` (empty dict), it's still included in aggregation. Template then tries `get_item` filter on `{}` which breaks.

**Changes:**
1. In service, skip invalid categories:
   ```python
   for pr in prs:
       categories = pr.effective_tech_categories
       if not categories or categories == {} or not isinstance(categories, (list, set)):
           continue
   ```
2. In view, filter breakdown before template:
   ```python
   breakdown = [b for b in breakdown if b.get('category') and b['category'] != '{}']
   ```

**Acceptance Criteria:**
- [ ] No `{}` entries in tech breakdown legend
- [ ] Percentages sum correctly
- [ ] Empty categories don't appear in chart

#### Task 2B.2: Apply Format Functions Consistently
**Effort:** S
**Files:**
- `assets/javascript/dashboard/trend-charts.js` - tooltip callbacks, METRIC_CONFIG
- `assets/javascript/dashboard/chart-manager.js` - axis tick callbacks

**Root Cause Analysis:**
`METRIC_CONFIG` at `trend-charts.js:20-45` defines format functions, but they're not consistently used in `createMultiMetricChart()` tooltip callbacks.

**Changes:**
1. Create centralized `formatMetricValue(value, unit)`:
   ```javascript
   function formatMetricValue(value, unit) {
     if (unit === 'hours') return `${value.toFixed(1)}h`;
     if (unit === '%') return `${value.toFixed(1)}%`;
     if (unit === 'count') return Math.round(value).toLocaleString();
     return value;
   }
   ```
2. Use in all tooltip label callbacks
3. Use in Y-axis tick callbacks

**Acceptance Criteria:**
- [ ] Cycle time shows "14.8h" in tooltips
- [ ] AI Adoption shows "56%" in tooltips
- [ ] Y-axis labels include units

### Phase 2C: UX Enhancements

#### Task 2C.1: Add PRs Merged Stat Card
**Effort:** S
**Files:**
- `templates/metrics/analytics/trends.html` - stat cards section
- `apps/metrics/views/trends_views.py` - `trends_overview()`

**Changes:**
1. Verify `pr_count` is in view context (already should be from METRIC_CONFIG)
2. Add stat card in template matching existing pattern:
   ```html
   <div class="app-card p-4">
     <h4 class="text-sm text-base-content/70">PRs Merged</h4>
     <div class="app-stat-value font-mono">{{ pr_count }}</div>
     <div class="text-xs {{ pr_count_change_class }}">{{ pr_count_change }}%</div>
   </div>
   ```
3. Calculate period-over-period change in view

**Acceptance Criteria:**
- [ ] PRs Merged card displays with count
- [ ] Shows percentage change vs previous period
- [ ] Consistent styling with other stat cards

#### Task 2C.2: Add Sparklines to Stat Cards
**Effort:** M
**Files:**
- `templates/metrics/analytics/trends.html` - stat cards
- `assets/javascript/dashboard/sparkline.js` - new file
- `apps/metrics/views/trends_views.py` - add sparkline data

**Changes:**
1. Create `createSparkline(canvas, data, color)` function:
   ```javascript
   export function createSparkline(canvas, data, color) {
     return new Chart(canvas, {
       type: 'line',
       data: { labels: data.map((_, i) => i), datasets: [{ data, borderColor: color, fill: false }] },
       options: {
         plugins: { legend: { display: false }, tooltip: { enabled: false } },
         scales: { x: { display: false }, y: { display: false } },
         elements: { point: { radius: 0 } }
       }
     });
   }
   ```
2. Add `<canvas class="sparkline" width="80" height="24">` to each stat card
3. Pass last 12 data points for each metric from view
4. Initialize sparklines in `chartManager.initAll()`

**Acceptance Criteria:**
- [ ] Each stat card has mini trend line
- [ ] Sparklines use metric-appropriate colors
- [ ] Sparklines render after HTMX swap

### Phase 2D: 100% Stacked Area Charts

#### Task 2D.1: Create Stacked Area Chart Factory
**Effort:** M
**Files:**
- `assets/javascript/dashboard/chart-manager.js` - new factory method

**Changes:**
1. Add `createStackedAreaChart(ctx, data, options)`:
   ```javascript
   createStackedAreaChart(ctx, data, options = {}) {
     // Normalize data to percentages
     const normalizedDatasets = this.normalizeToPercentages(data.datasets, data.labels.length);

     return new Chart(ctx, {
       type: 'line',
       data: {
         labels: data.labels,
         datasets: normalizedDatasets.map((ds, i) => ({
           label: ds.label,
           data: ds.data,
           fill: i === 0 ? 'origin' : '-1',
           backgroundColor: ds.color + '80', // 50% opacity
           borderColor: ds.color,
           tension: 0.3,
         }))
       },
       options: {
         scales: {
           y: { stacked: true, max: 100, ticks: { callback: v => v + '%' } },
           x: { stacked: true }
         },
         plugins: {
           tooltip: {
             callbacks: {
               label: (ctx) => `${ctx.dataset.label}: ${ctx.raw.toFixed(1)}%`
             }
           }
         }
       }
     });
   }

   normalizeToPercentages(datasets, labelCount) {
     // For each time point, calculate total and convert to %
     const totals = Array(labelCount).fill(0);
     datasets.forEach(ds => ds.data.forEach((v, i) => totals[i] += v));

     return datasets.map(ds => ({
       ...ds,
       data: ds.data.map((v, i) => totals[i] ? (v / totals[i]) * 100 : 0)
     }));
   }
   ```

**Acceptance Criteria:**
- [ ] Factory creates valid stacked area chart
- [ ] Data normalized to percentages per time point
- [ ] Areas stack smoothly

#### Task 2D.2: Update Technology Breakdown Chart
**Effort:** M
**Files:**
- `templates/metrics/analytics/trends/tech_chart.html`
- `apps/metrics/views/trends_views.py` - `tech_breakdown_chart()`
- `assets/javascript/app.js` - chart registration

**Changes:**
1. Update view to return time-series data per category (not aggregated totals)
2. Change `initTechChart()` to use `createStackedAreaChart`
3. Update template canvas attributes

**Acceptance Criteria:**
- [ ] Tech breakdown shows as 100% stacked area chart
- [ ] Areas stack to 100% at each time point
- [ ] Legend shows category names with current percentages

#### Task 2D.3: Update PR Types Chart
**Effort:** M
**Files:**
- `templates/metrics/analytics/trends/pr_type_chart.html`
- `apps/metrics/views/trends_views.py` - `pr_type_breakdown_chart()`
- `assets/javascript/app.js` - chart registration

**Changes:**
1. Same pattern as Task 2D.2
2. Data already has time-series structure from `get_monthly_pr_type_trend()`
3. Change from stacked bar to stacked area

**Acceptance Criteria:**
- [ ] PR types shows as 100% stacked area chart
- [ ] Feature/Bugfix/etc areas stack to 100%
- [ ] ICP sees composition trend clearly

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Chart.js stacked area edge cases | Medium | Medium | Thorough testing with real data; fallback option |
| Race condition fix incomplete | Low | High | Comprehensive retry logic with logging |
| Data normalization division by zero | Medium | Low | Handle zero-sum periods gracefully |
| Sparkline performance | Low | Low | Limit to 12 data points |

---

## Success Metrics

1. **Reliability:** All chart types render on first load (no refresh needed)
2. **Data Quality:** No empty/invalid entries in any chart
3. **Formatting:** All values display with correct units
4. **UX:** All 4 stat cards visible with sparklines
5. **Visualization:** Stacked area charts show clear composition trends

---

## Testing Strategy

1. **E2E Tests:** Update `tests/e2e/trends-charts.spec.ts`
   - Test multi-metric selection
   - Test chart rendering without refresh
   - Test sparklines
   - Test stacked area charts

2. **Manual Testing:** Antiwork team
   - All time range presets
   - All metric combinations
   - Weekly vs monthly granularity

---

## Definition of Done

- [ ] Multi-metric comparison chart renders reliably
- [ ] No `{}` entries in tech breakdown
- [ ] Cycle time shows "h" suffix
- [ ] PRs Merged stat card with sparkline
- [ ] All charts render on first HTMX load
- [ ] Tech breakdown as 100% stacked area
- [ ] PR types as 100% stacked area
- [ ] E2E tests pass
- [ ] No console errors
