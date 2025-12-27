# Trends Charts Fix - Context

## Problem Statement

The Trends page (`/app/metrics/analytics/trends/`) has three issues:

1. **PR Types Over Time and Technology Breakdown charts not rendering** - The sections show data (legend with counts/percentages) but the actual Chart.js canvas charts are not appearing. The chart containers are empty.

2. **Layout issue** - PR Types and Technology Breakdown should be **full-width charts** (like the main trend chart), not side-by-side in a 2-column grid.

3. **500 error on Industry Benchmark endpoint** - `/app/metrics/panels/benchmark/cycle_time/?days=359` returns 500.

## Investigation Summary

### Issue 1: Charts Not Rendering

**Observed Behavior:**
- Main wide chart ("Cycle Time vs Review Time vs PRs Merged") renders correctly
- "PR Types Over Time" shows: Bugfix 907 (36.0%), Feature 675 (26.8%), etc. - but NO chart
- "Technology Breakdown" shows: Frontend 1761 (70.0%), Backend 1257 (50.0%), etc. - but NO chart

**Root Cause Analysis:**
The templates (`pr_type_chart.html` and `tech_chart.html`) have proper Chart.js initialization code, but something is preventing the charts from rendering. Possible causes:

1. **Chart.js not loaded** when HTMX swaps in the partial
2. **Canvas element not found** - the `initChart()` function may run before DOM is ready
3. **Chart data JSON parsing failure** - the `json_script` filter may not be producing valid JSON
4. **HTMX swap timing** - the inline `<script>` may not execute properly after HTMX swap

**Key Files:**
- `templates/metrics/analytics/trends/pr_type_chart.html` - Has canvas `#pr-type-chart` + Chart.js init
- `templates/metrics/analytics/trends/tech_chart.html` - Has canvas `#tech-chart` + Chart.js init
- `apps/metrics/views/trends_views.py` - `pr_type_breakdown_chart()` and `tech_breakdown_chart()` views
- `apps/metrics/services/dashboard_service.py` - `get_monthly_pr_type_trend()`, `get_tech_breakdown()` etc.

**Data Flow:**
1. Trends page loads → HTMX triggers `hx-get` on `#pr-type-chart-container`
2. View returns partial with `chart_data` context variable
3. Template uses `{{ chart_data|json_script:"pr-type-chart-data" }}`
4. Inline `<script>` reads JSON and creates Chart.js instance

### Issue 2: Benchmark 500 Error

**Observed Behavior:**
- Console error: `500 from /app/metrics/panels/benchmark/cycle_time/?days=359`
- Industry Benchmark panel shows loading skeleton forever

**Possible Causes:**
1. `days=359` (full year) may cause issues with the benchmark service
2. Database query error in `benchmark_service.get_benchmark_for_team()`
3. No `IndustryBenchmark` record for this metric/size combination

**Key Files:**
- `apps/metrics/views/chart_views.py:505` - `benchmark_panel()` view
- `apps/metrics/services/benchmark_service.py` - `get_benchmark_for_team()`

## Current Architecture

### Trends Page Structure

```
trends.html
├── wide-chart-container (HTMX load) → wide_chart.html ✓ WORKS
├── pr-type-chart-container (HTMX load) → pr_type_chart.html ✗ BROKEN
├── tech-chart-container (HTMX load) → tech_chart.html ✗ BROKEN
├── benchmark-panel-container (HTMX load) → benchmark_panel.html ✗ 500 ERROR
└── Quick Stats Cards
```

### Chart Data Format (Working)

PR Type chart expects:
```json
{
  "labels": ["2024-01", "2024-02", ...],
  "datasets": [
    {"type": "feature", "label": "Feature", "color": "#F97316", "data": [10, 15, ...]},
    {"type": "bugfix", "label": "Bugfix", "color": "#F87171", "data": [5, 8, ...]},
    ...
  ]
}
```

Tech chart expects the same format with `category` instead of `type`.

## Related Code

### View Functions

```python
# trends_views.py:326
@team_admin_required
def pr_type_breakdown_chart(request: HttpRequest) -> HttpResponse:
    date_range = get_extended_date_range(request)
    granularity = date_range["granularity"]

    if granularity == "weekly":
        type_data = dashboard_service.get_weekly_pr_type_trend(...)
    else:
        type_data = dashboard_service.get_monthly_pr_type_trend(...)

    # Build datasets...
    context = {
        "chart_data": chart_data,
        "breakdown": breakdown,
        ...
    }
    return TemplateResponse(request, "metrics/analytics/trends/pr_type_chart.html", context)
```

### Template Chart Init Pattern

```javascript
(function() {
    initChart();

    function initChart() {
        const canvas = document.getElementById('pr-type-chart');
        if (!canvas) return;  // Early exit if no canvas

        const chartDataEl = document.getElementById('pr-type-chart-data');
        if (!chartDataEl) return;

        if (typeof Chart === 'undefined') {
            setTimeout(initChart, 100);  // Wait for Chart.js
            return;
        }

        // ... create chart
    }
})();
```

## Environment

- Django 5.1
- Chart.js (via Vite)
- HTMX 2.x
- Alpine.js
- DaisyUI + Tailwind CSS
