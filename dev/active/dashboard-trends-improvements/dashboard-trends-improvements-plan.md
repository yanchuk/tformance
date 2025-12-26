# Dashboard & Trends Page Improvements Plan

**Last Updated:** 2025-12-26

## Executive Summary

This plan addresses six UI/UX improvements for the dashboard and Trends analytics page:

1. **Dashboard Icon Removal** - Remove decorative stat-figure icons (checkmark badge, clock, lightbulb, star) from quick stats cards that break UI layout
2. **Trends Page Width Fix** - Fix content width jumping when switching between tabs
3. **Multi-Metric Comparison** - Allow selecting multiple metrics to compare on the Trends chart
4. **ICP Data Analysis** - Identify what data a CTO (ICP) would want to see and how
5. **PR Type Breakdown Trends** - Show feature/bugfix/refactor/etc breakdown in trends (from LLM `summary.type`)
6. **Technology Breakdown Trends** - Show frontend/backend/devops/etc breakdown in trends (from LLM `tech.categories`)

## Current State Analysis

### 1. Dashboard Quick Stats (Issue: Icons Breaking UI)

**File:** `templates/web/components/quick_stats.html`

Current implementation has `stat-figure` SVG icons in each card:
- PRs Merged: Checkmark badge icon (`h-8 w-8`)
- Avg Cycle Time: Clock icon
- AI-Assisted: Lightbulb icon
- Avg Quality: Star icon

These icons appear at the right side of each stat card and may cause layout issues on smaller screens or when values are large.

### 2. Trends Page Width Jumping

**Files:**
- `templates/metrics/analytics/base_analytics.html` - Base template with tabs
- `templates/metrics/analytics/trends.html` - Trends page content

The Trends page extends `base_analytics.html` but has different content structure that causes width inconsistency:
- Other tabs use consistent card layouts
- Trends page has wider chart container and different sections

### 3. Single Metric Selection

**File:** `templates/metrics/analytics/trends.html` (lines 17-31)

Currently uses a single `<select>` dropdown for metric selection:
```html
<select id="metric-selector" ...>
  {% for m in available_metrics %}
    <option value="{{ m.id }}" ...>{{ m.name }}</option>
  {% endfor %}
</select>
```

Only 4 metrics available:
- cycle_time, review_time, pr_count, ai_adoption

### 4. Available LLM Data for PR Breakdown

From `apps/metrics/models/github.py`:
```python
llm_summary = models.JSONField(...)  # Contains full LLM analysis
```

LLM Response Schema (`apps/metrics/prompts/schemas.py`):
```python
# PR Type Classification
"type": {
    "enum": ["feature", "bugfix", "refactor", "docs", "test", "chore", "ci"]
}

# Technology Categories
"categories": {
    "enum": ["backend", "frontend", "devops", "mobile", "data"]
}
```

This data is already stored in `PullRequest.llm_summary` for PRs that have been analyzed.

## Proposed Future State

### 1. Clean Stat Cards (No Icons)
- Remove all `stat-figure` divs from quick_stats.html
- Simpler, more consistent layout across screen sizes
- Metrics values become the visual focus

### 2. Consistent Page Width
- Add container width constraints to Trends page
- Match other analytics tab layouts
- Verify with Playwright E2E test

### 3. Multi-Metric Checkboxes
- Replace single select with checkbox group
- Show 2-3 default metrics (cycle_time, ai_adoption, pr_count)
- Render multiple datasets on same chart with different colors
- Add legend for metric identification

### 4. ICP (CTO) Data Priorities
Key metrics CTOs want to see:
- **AI ROI**: Is AI adoption improving delivery metrics?
- **Team Velocity**: PRs merged trend, cycle time trend
- **Quality Signals**: Revert rate, hotfix frequency
- **Work Distribution**: What types of work is the team doing?
- **Technology Focus**: Where is engineering effort going?

### 5. PR Type Breakdown Chart
New visualization showing:
- Stacked area or bar chart
- Categories: Feature, Bugfix, Refactor, Docs, Test, Chore, CI
- Trend over time (weekly/monthly granularity)
- Percentages and absolute counts

### 6. Technology Breakdown Chart
New visualization showing:
- Stacked area or pie chart
- Categories: Backend, Frontend, DevOps, Mobile, Data
- Trend over time
- Shows where engineering focus is shifting

## Implementation Phases

### Phase 1: Dashboard Icon Removal (Effort: S)
Simple template change, no backend work.

### Phase 2: Trends Width Fix + E2E Test (Effort: S)
CSS/template fixes with Playwright validation.

### Phase 3: Multi-Metric Selection (Effort: M)
Frontend changes + Chart.js multi-dataset support.

### Phase 4: PR Type Breakdown (Effort: M)
New service function + new chart endpoint + template.

### Phase 5: Technology Breakdown (Effort: M)
Similar to Phase 4 - new service + chart.

### Phase 6: ICP Data Review (Effort: S)
Documentation + potential additional metrics.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM data not populated for all PRs | Medium | Medium | Show "N/A" for PRs without llm_summary, add backfill note |
| Chart performance with multiple datasets | Low | Low | Limit to 3-4 simultaneous metrics |
| Browser compatibility for checkbox group | Low | Low | Use Alpine.js for consistent behavior |

## Success Metrics

1. **Icon Removal**: No layout shifts on mobile/desktop
2. **Width Fix**: Playwright test passes for consistent width
3. **Multi-Metric**: Users can select 2-4 metrics to compare
4. **PR Type Trends**: CTOs can see feature vs bugfix ratio over time
5. **Tech Trends**: CTOs can see backend vs frontend focus over time

## Required Resources

### Files to Modify
- `templates/web/components/quick_stats.html`
- `templates/metrics/analytics/trends.html`
- `templates/metrics/analytics/base_analytics.html`
- `apps/metrics/views/trends_views.py`
- `apps/metrics/services/dashboard_service.py`
- `assets/javascript/dashboard/trend-charts.js`

### Files to Create
- `templates/metrics/analytics/trends/pr_type_chart.html`
- `templates/metrics/analytics/trends/tech_breakdown_chart.html`
- `tests/e2e/trends.spec.ts` (E2E test)

### Dependencies
- Chart.js (already installed)
- Alpine.js (already installed)
- Playwright (already installed)
