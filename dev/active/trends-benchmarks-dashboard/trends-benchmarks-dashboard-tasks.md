# Trends & Benchmarks Dashboard - Tasks

**Last Updated:** 2025-12-25

---

## Phase 1: Custom Date Range & Extended Data [M]

**Goal:** Enable 12+ month data viewing with flexible date selection

### Backend

- [ ] **1.1** Add `get_monthly_aggregation()` to `dashboard_service.py`
  - Group by `TruncMonth` instead of `TruncWeek`
  - Support all existing metrics (cycle_time, ai_adoption, prs_merged, review_time)
  - Acceptance: Returns 12 monthly data points for year range

- [ ] **1.2** Create `get_date_range_from_params()` in `view_utils.py`
  - Parse `start`, `end`, `granularity` query params
  - Support ISO date strings and relative keywords (this_year, last_year)
  - Validate: start < end, max range 2 years
  - Acceptance: Unit tests for all date formats

- [ ] **1.3** Update chart endpoints to support extended ranges
  - Modify `chart_cycle_time`, `chart_ai_adoption`, `chart_review_time`
  - Add `granularity` parameter (weekly, monthly)
  - Acceptance: Endpoints return monthly data when requested

- [ ] **1.4** Add database index for date range queries
  - Create migration adding index on `(team_id, merged_at)`
  - Acceptance: EXPLAIN shows index usage for date range queries

### Frontend

- [ ] **1.5** Create custom date picker component
  - Alpine.js component with start/end date inputs
  - Quick presets: Last 7d, 30d, 90d, This Year, Last Year, Custom
  - Apply button triggers HTMX update
  - Acceptance: Works on all analytics pages
  - File: `templates/metrics/partials/date_range_picker.html`

- [ ] **1.6** Update `base_analytics.html` with new date picker
  - Replace current button group with date picker component
  - Maintain backward compatibility with `?days=` param
  - Acceptance: Both old and new date params work

- [ ] **1.7** Add URL parameter preservation
  - Date range persists across tab navigation
  - Bookmarkable URLs with date params
  - Acceptance: Refreshing page maintains date selection

### Tests

- [ ] **1.8** Write tests for monthly aggregation
  - Test `get_monthly_aggregation()` with various date ranges
  - Test edge cases: partial months, empty data
  - Acceptance: 10+ test cases, all passing

---

## Phase 2: Wide Trend Charts Section [L]

**Goal:** Create dedicated trends page with full-width, long-horizon charts

### Backend

- [ ] **2.1** Create `trends_views.py` module
  - `trends_overview()` - Main trends dashboard
  - `trends_cycle_time()`, `trends_ai_adoption()`, `trends_delivery()` - Deep dives
  - Acceptance: All views return proper templates with context

- [ ] **2.2** Create `trend_service.py` module
  - `get_trend_comparison(team, metric, period1, period2)` - YoY data
  - `get_trend_summary(team, metric, start, end)` - Aggregated stats
  - Acceptance: Returns both current and comparison period data

- [ ] **2.3** Create trend chart data endpoint
  - `/api/chart/trend/<metric>/` - Returns trend data for any metric
  - Support `compare` param for YoY overlay
  - Acceptance: JSON response with current + comparison data

- [ ] **2.4** Add trends URLs to `urls.py`
  - Register all new views
  - Acceptance: All URLs accessible, return 200

### Frontend

- [ ] **2.5** Create `trends.html` base template
  - Full-width chart container (no card grid)
  - Metric selector dropdown
  - Granularity toggle (weekly/monthly)
  - Acceptance: Chart fills container width

- [ ] **2.6** Install and configure `chartjs-plugin-zoom`
  - `npm install chartjs-plugin-zoom`
  - Configure pan/zoom for trend charts
  - Acceptance: User can pan horizontally, zoom in/out

- [ ] **2.7** Create `trend-charts.js` module
  - `createTrendChart(ctx, data, comparisonData)` - Dual-line chart
  - `createTrendBarChart(ctx, data)` - Wide bar chart
  - Theme-consistent styling
  - Acceptance: Charts render with zoom enabled

- [ ] **2.8** Create wide chart template partial
  - `templates/metrics/analytics/trends/wide_chart.html`
  - HTMX lazy loading
  - Loading skeleton
  - Empty state
  - Acceptance: Chart loads via HTMX, shows loading state

- [ ] **2.9** Add horizontal scroll for mobile
  - Overflow-x-auto on chart container
  - Touch-friendly scroll hints
  - Acceptance: Usable on mobile devices

- [ ] **2.10** Add "Trends" tab to analytics navigation
  - Update `base_analytics.html` tab list
  - Acceptance: Tab appears, links to trends page

### Tests

- [ ] **2.11** Write trend service tests
  - Test YoY comparison calculation
  - Test missing data handling
  - Acceptance: 15+ test cases, all passing

- [ ] **2.12** Write trends view tests
  - Test all view responses
  - Test date param parsing
  - Acceptance: All views tested

---

## Phase 3: Sparkline Summary Cards [S]

**Goal:** Add mini trend visualizations to key metric cards

### Backend

- [ ] **3.1** Add `get_sparkline_data()` to dashboard service
  - Returns last 12 weeks of data as array
  - Minimal format: just values, no dates
  - Acceptance: Returns array of 12 numbers

- [ ] **3.2** Update `cards_metrics` view to include sparklines
  - Add sparkline data to each metric card context
  - Calculate change percentage
  - Acceptance: View returns sparkline data for each metric

### Frontend

- [ ] **3.3** Create `sparkline.js` module
  - `createSparkline(ctx, data, options)` - Minimal line chart
  - No axes, no legend, just the line
  - Color based on trend direction (green/red)
  - Acceptance: Renders inline with metric cards

- [ ] **3.4** Update key metrics card template
  - Add small canvas for sparkline
  - Show change percentage with arrow
  - Acceptance: Cards display sparklines

- [ ] **3.5** Style sparkline cards
  - Consistent sizing (80px x 24px)
  - Proper alignment with metric value
  - Acceptance: Looks good in 4-column grid

### Tests

- [ ] **3.6** Write sparkline data tests
  - Test 12-week window calculation
  - Test change percentage accuracy
  - Acceptance: Data is correct

---

## Phase 4: Industry Benchmarks Foundation [XL]

**Goal:** Introduce benchmark comparisons against similar companies

### Backend

- [ ] **4.1** Create `IndustryBenchmark` model
  - Fields: metric_name, team_size_bucket, percentiles, source, year
  - Add to `apps/metrics/models/`
  - Acceptance: Migration runs successfully

- [ ] **4.2** Create benchmark data migration
  - Seed initial DORA 2024 benchmarks
  - Cover: cycle_time, deployment_freq, change_failure_rate, lead_time
  - Acceptance: Benchmark data queryable

- [ ] **4.3** Create `benchmark_service.py` module
  - `get_benchmark_for_team(team, metric)` - Returns benchmark + team percentile
  - `calculate_percentile(value, benchmarks)` - Percentile calculation
  - Acceptance: Returns accurate percentile positioning

- [ ] **4.4** Create benchmark API endpoint
  - `/api/benchmarks/<metric>/` - Returns benchmark comparison
  - Include interpretation text
  - Acceptance: JSON with team value, percentile, benchmarks

### Frontend

- [ ] **4.5** Create benchmark panel component
  - `templates/metrics/analytics/trends/benchmark_panel.html`
  - Visual percentile bar
  - Interpretation text ("Better than 72% of teams")
  - Acceptance: Panel displays correctly

- [ ] **4.6** Add benchmark section to trends page
  - Show benchmark for selected metric
  - Link to detailed benchmarks page
  - Acceptance: Benchmark visible on trends page

- [ ] **4.7** Create benchmarks detail page
  - Show all metrics with benchmarks
  - Explain methodology
  - Acceptance: All benchmarks displayed

### Tests

- [ ] **4.8** Write benchmark model tests
  - Test team size bucket matching
  - Test percentile calculation
  - Acceptance: 10+ test cases

- [ ] **4.9** Write benchmark service tests
  - Test various team values against benchmarks
  - Test edge cases (no data, extreme values)
  - Acceptance: All calculations verified

---

## Phase 5: Actionable Insights Engine [XL]

**Goal:** Surface data-driven recommendations and correlations

### Backend

- [ ] **5.1** Create `TrendInsight` model
  - Fields: type, title, description, metric, value, change, dismissed
  - Add to `apps/metrics/models/`
  - Acceptance: Migration runs successfully

- [ ] **5.2** Create `insight_engine.py` module
  - `generate_trend_insights(team, date_range)` - Main entry point
  - Insight types: trend_alert, correlation, achievement, recommendation
  - Acceptance: Generates relevant insights from data

- [ ] **5.3** Implement trend alert detection
  - Detect significant metric changes (>20% week-over-week)
  - Generate alert insight with context
  - Acceptance: Alerts generated for significant changes

- [ ] **5.4** Implement correlation detection
  - Detect AI adoption vs cycle time correlation
  - Detect AI adoption vs review time correlation
  - Acceptance: Correlations identified and scored

- [ ] **5.5** Implement achievement detection
  - Milestones: 100 PRs, 50% AI adoption, etc.
  - Generate celebratory insights
  - Acceptance: Achievements detected and displayed

- [ ] **5.6** Implement recommendation engine
  - Based on benchmark position
  - Based on observed patterns
  - Acceptance: Actionable recommendations generated

- [ ] **5.7** Create Celery task for insight generation
  - Daily insight refresh
  - Cleanup old dismissed insights
  - Acceptance: Task runs on schedule

### Frontend

- [ ] **5.8** Create insight card component
  - `templates/metrics/partials/insight_card.html`
  - Icon, title, description, action button
  - Dismiss functionality
  - Acceptance: Cards render with all data

- [ ] **5.9** Add insights section to trends page
  - Display top 3-5 insights
  - "View all" link
  - Acceptance: Insights visible on page

- [ ] **5.10** Implement insight dismissal
  - HTMX dismiss endpoint
  - Animate removal
  - Don't show dismissed insights again
  - Acceptance: Dismiss works, persists

### Tests

- [ ] **5.11** Write insight generation tests
  - Test each insight type
  - Test edge cases (no data, all good)
  - Acceptance: 20+ test cases

---

## Phase 6: Educational Content & Upsells [M]

**Goal:** Connect insights to solutions (case studies, consulting)

### Backend

- [ ] **6.1** Create content linking system
  - Map insight types to content URLs
  - Support internal docs and external links
  - Acceptance: Insights link to relevant content

- [ ] **6.2** Create consulting request endpoint
  - Form submission endpoint
  - Email notification to sales
  - Acceptance: Requests logged and emailed

### Frontend

- [ ] **6.3** Create case study card component
  - Teaser card linking to full case study
  - Contextual to current metric
  - Acceptance: Cards render with data

- [ ] **6.4** Add "Get Help" section to trends page
  - Case study cards
  - Consulting CTA button
  - Acceptance: Section visible, links work

- [ ] **6.5** Create consulting request modal
  - Form with contact info, topic
  - Submit via HTMX
  - Success confirmation
  - Acceptance: Form submits, shows confirmation

### Tests

- [ ] **6.6** Write consulting request tests
  - Test form validation
  - Test email notification
  - Acceptance: Full flow tested

---

## Completion Checklist

### Phase 1 Complete When:
- [ ] Date picker works on all analytics pages
- [ ] Monthly data available for 12+ months
- [ ] URLs are bookmarkable with date params
- [ ] All unit tests passing

### Phase 2 Complete When:
- [ ] Trends page accessible from analytics nav
- [ ] Full-width chart renders correctly
- [ ] YoY comparison works
- [ ] Zoom/pan functional on charts
- [ ] All unit tests passing

### Phase 3 Complete When:
- [ ] Sparklines visible on all key metric cards
- [ ] Change percentages accurate
- [ ] Mobile-friendly display
- [ ] All unit tests passing

### Phase 4 Complete When:
- [ ] Benchmark data seeded
- [ ] Team percentile calculated correctly
- [ ] Benchmark panel displays on trends page
- [ ] All unit tests passing

### Phase 5 Complete When:
- [ ] Insights generate automatically
- [ ] All insight types implemented
- [ ] Dismiss functionality works
- [ ] Daily refresh task running
- [ ] All unit tests passing

### Phase 6 Complete When:
- [ ] Case study cards display
- [ ] Consulting request form works
- [ ] Email notifications sent
- [ ] All unit tests passing

---

## Notes

- Start with Phase 1 - it's the foundation for everything else
- Phase 2 can run in parallel with Phase 3 (independent work)
- Phase 4 requires research for benchmark data
- Phase 5 is complex - may need to simplify initially
- Phase 6 depends on having content ready (marketing input needed)
