# Trends URL Parameters Fix - Context

**Last Updated**: 2025-12-26 19:00 UTC

## Problem Statement

The Trends dashboard (`/app/metrics/analytics/trends/`) had issues with URL parameter persistence:

1. **Granularity not in URL**: When user changed grouping from "Weekly" to "Monthly", the URL didn't update to include `?granularity=monthly`
2. **Preset not replacing days**: When selecting "This Year" preset, URL still showed `?days=30` instead of `?preset=this_year`
3. **Parameters not preserved**: Changing one parameter would lose others (e.g., changing granularity would lose the preset)

## Solution

### Files Modified

| File | Change |
|------|--------|
| `templates/metrics/analytics/trends.html` | Updated Alpine.js to use `updateUrlAndChart()` that calls `history.pushState()` before HTMX ajax |
| `templates/metrics/partials/date_range_picker.html` | Updated `navigate()` function to preserve existing params and use `history.pushState()` |
| `apps/metrics/tests/test_trends_views.py` | Added 7 new tests for URL parameter handling |

### Key Changes

#### 1. trends.html - Granularity & Metrics URL Update

```javascript
// Old: Only made HTMX calls, didn't update URL
updateChart() {
  htmx.ajax('GET', url, {target:'#wide-chart-container', swap:'innerHTML'});
}

// New: Updates URL first, then makes HTMX calls
updateUrlAndChart() {
  const params = new URLSearchParams(window.location.search);
  params.set('granularity', this.granularity);
  params.set('metrics', this.selectedMetrics.join(','));
  history.pushState({}, '', window.location.pathname + '?' + params.toString());
  this.updateChart();
}
```

#### 2. date_range_picker.html - Date Range URL Update

```javascript
// Old: Used htmx.ajax with pushUrl option (doesn't work)
navigate(query) {
  htmx.ajax('GET', url, {target, swap, pushUrl: true});
}

// New: Preserves existing params, uses history.pushState
navigate(newParams) {
  const params = new URLSearchParams(window.location.search);
  // Clear conflicting date params, set new ones
  // Preserve granularity, metrics
  history.pushState({}, '', url);
  htmx.ajax('GET', url, {target, swap});
}
```

## URL Parameter Behavior

| Parameter | Type | Values | Notes |
|-----------|------|--------|-------|
| `days` | integer | 7, 30, 90 | Quick presets, mutually exclusive with `preset` |
| `preset` | string | this_year, last_year, this_quarter, yoy | Extended presets, mutually exclusive with `days` |
| `granularity` | string | weekly, monthly | Data grouping, preserved across all changes |
| `metrics` | string | cycle_time,review_time,pr_count,ai_adoption | Comma-separated, max 3 |
| `start`/`end` | date | YYYY-MM-DD | Custom date range |

## Testing

### Unit Tests Added (7 tests)

- `test_granularity_parameter_in_context` - monthly/weekly params
- `test_metrics_parameter_in_context` - single/multiple metrics
- `test_preset_and_granularity_both_in_context` - combined params
- `test_all_parameters_preserved` - all params together
- `test_invalid_granularity_defaults_to_auto` - graceful fallback
- `test_wide_chart_respects_all_parameters` - chart partial
- `test_days_parameter_overrides_preset` - days precedence

### Playwright Testing Verified

1. Navigate to `/trends/?days=30` - Weekly selected by default
2. Click "Monthly" - URL updates to `?days=30&granularity=monthly&metrics=cycle_time`
3. Click "This Year" - URL updates to `?granularity=monthly&metrics=cycle_time&preset=this_year`
4. Click "Weekly" - URL updates to `?granularity=weekly&metrics=cycle_time&preset=this_year`
5. Click "30d" - URL updates to `?granularity=weekly&metrics=cycle_time&days=30`

## Dependencies

- HTMX for partial page updates
- Alpine.js for client-side state management
- Browser History API (`history.pushState()`)
