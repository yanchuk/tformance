# Trends & Benchmarks Dashboard - Tasks

**Last Updated:** 2025-12-25

---

## Phase 1: Custom Date Range & Extended Data [M] ✅ COMPLETE

**Goal:** Enable 12+ month data viewing with flexible date selection

### Backend

- [x] **1.1** Add `get_monthly_aggregation()` to `dashboard_service.py`
  - Added `get_monthly_cycle_time_trend()`, `get_monthly_review_time_trend()`,
    `get_monthly_pr_count()`, `get_monthly_ai_adoption()`
  - Group by `TruncMonth` for year-long views
  - Acceptance: ✅ 13 tests passing

- [x] **1.2** Create `get_extended_date_range()` in `view_utils.py`
  - Parse `start`, `end`, `granularity`, `preset` query params
  - Support presets: this_year, last_year, this_quarter, yoy
  - Validate: start < end, max range 730 days (2 years)
  - Acceptance: ✅ 20 unit tests passing

- [x] **1.3** Update analytics views to support extended ranges
  - Updated `_get_analytics_context()` to use `get_extended_date_range()`
  - Added granularity, preset, compare_start, compare_end to context
  - Acceptance: ✅ All analytics views support new params

- [ ] **1.4** Add database index for date range queries (DEFERRED)
  - Note: Existing indexes sufficient for current scale

### Frontend

- [x] **1.5** Create custom date picker component
  - Alpine.js component with presets (7d, 30d, 90d)
  - Extended presets: This Year, Last Year, This Quarter, YoY Comparison
  - Custom date range modal with validation
  - File: `templates/metrics/partials/date_range_picker.html`
  - Acceptance: ✅ Works on all analytics pages

- [x] **1.6** Update `base_analytics.html` with new date picker
  - Replaced button group with date picker component
  - Maintains backward compatibility with `?days=` param
  - Acceptance: ✅ Both old and new date params work

- [x] **1.7** Add URL parameter preservation
  - HTMX navigation preserves date params
  - Bookmarkable URLs with date/preset params
  - Acceptance: ✅ Refreshing page maintains date selection

### Tests

- [x] **1.8** Write tests for date range utilities
  - 20 tests for `get_extended_date_range()` in `test_view_utils.py`
  - 13 tests for monthly aggregation in `test_monthly_aggregation.py`
  - Acceptance: ✅ 33 tests passing

---

## Phase 2: Wide Trend Charts Section [L] ✅ COMPLETE

**Goal:** Create dedicated trends page with full-width, long-horizon charts

### Backend

- [x] **2.1** Create `trends_views.py` module
  - `trends_overview()` - Main trends dashboard
  - `trend_chart_data()` - JSON endpoint for chart data
  - `wide_trend_chart()` - HTMX partial for chart loading
  - File: `apps/metrics/views/trends_views.py`
  - Acceptance: ✅ All views return proper templates with context

- [x] **2.2** Use existing dashboard_service functions
  - Reused `get_monthly_*()` and `get_trend_comparison()` from Phase 1
  - No separate trend_service needed
  - Acceptance: ✅ Data available for all metrics

- [x] **2.3** Create trend chart data endpoint
  - `/charts/trend/` - Returns JSON with labels, datasets, granularity
  - Supports `metric`, `days`, `preset` params
  - YoY comparison: adds second dataset when preset=yoy
  - Acceptance: ✅ JSON response with current + comparison data

- [x] **2.4** Add trends URLs to `urls.py`
  - `analytics/trends/` → `trends_overview`
  - `charts/trend/` → `chart_trend`
  - `charts/wide-trend/` → `chart_wide_trend`
  - Acceptance: ✅ All URLs accessible, return 200

### Frontend

- [x] **2.5** Create `trends.html` base template
  - Extends base_analytics.html
  - Full-width chart container
  - Metric selector dropdown (cycle_time, review_time, pr_count, ai_adoption)
  - File: `templates/metrics/analytics/trends.html`
  - Acceptance: ✅ Chart fills container width

- [x] **2.6** Install and configure `chartjs-plugin-zoom`
  - `npm install chartjs-plugin-zoom`
  - Registered in trend-charts.js
  - Pan mode: horizontal drag
  - Zoom mode: scroll wheel
  - Acceptance: ✅ User can pan horizontally, zoom in/out

- [x] **2.7** Create `trend-charts.js` module
  - `createWideTrendChart(canvas, data, options)` - Full-featured line chart
  - `resetChartZoom(chart)` - Reset zoom handler
  - Theme-consistent styling from chart-theme.js
  - File: `assets/javascript/dashboard/trend-charts.js`
  - Acceptance: ✅ Charts render with zoom enabled

- [x] **2.8** Create wide chart template partial
  - File: `templates/metrics/analytics/trends/wide_chart.html`
  - HTMX lazy loading
  - Loading skeleton (animate-pulse)
  - Chart header with reset zoom button
  - Acceptance: ✅ Chart loads via HTMX, shows loading state

- [x] **2.9** Add horizontal scroll for mobile
  - `overflow-x-auto` on chart container
  - Min width 800px for chart area
  - Acceptance: ✅ Usable on mobile devices

- [x] **2.10** Add "Trends" tab to analytics navigation
  - Updated `base_analytics.html` tab list
  - Tab between "Team" and "Pull Requests"
  - Acceptance: ✅ Tab appears, links to trends page

### Tests

- [x] **2.11** Write trends view tests
  - 20 tests in `test_trends_views.py`
  - TestTrendsOverviewView (8 tests)
  - TestTrendChartDataView (6 tests)
  - TestWideTrendChartView (4 tests)
  - TestTrendsTabNavigation (2 tests)
  - Acceptance: ✅ All views tested

- [x] **2.12** Total metrics tests: 1612 passing

---

## Phase 3: Sparkline Summary Cards [S] ✅ COMPLETE

**Goal:** Add mini trend visualizations to key metric cards

### Backend

- [x] **3.1** Add `get_sparkline_data()` to dashboard service
  - Returns last 12 weeks of data as array per metric
  - Each metric has: values (list), change_pct (int), trend (str)
  - Supports: prs_merged, cycle_time, ai_adoption, review_time
  - Acceptance: ✅ 13 tests passing

- [x] **3.2** Update `cards_metrics` view to include sparklines
  - Added `sparklines` to context with 84-day window
  - Calculates change percentage and trend direction
  - Acceptance: ✅ View returns sparkline data for each metric

### Frontend

- [x] **3.3** Create `sparkline.js` module
  - `createSparkline(ctx, data, options)` - Minimal line chart
  - No axes, no legend, just the line
  - Color based on trend direction (green/red for higher-is-better, inverted for time metrics)
  - Auto-initialization on DOMContentLoaded and htmx:afterSwap
  - File: `assets/javascript/dashboard/sparkline.js`
  - Acceptance: ✅ Renders inline with metric cards

- [x] **3.4** Update key metrics card template
  - Added canvas with data-sparkline attributes
  - Shows change percentage with color-coded trend
  - File: `templates/metrics/partials/key_metrics_cards.html`
  - Acceptance: ✅ Cards display sparklines

- [x] **3.5** Style sparkline cards
  - Size: w-20 h-6 (80px x 24px)
  - Flexbox layout aligns value and sparkline
  - Acceptance: ✅ Looks good in 4-column grid

### Tests

- [x] **3.6** Write sparkline data tests
  - 11 unit tests for `get_sparkline_data()` function
  - 2 integration tests for view context
  - Tests: weekly aggregation, change calculation, trend detection, team filtering
  - File: `apps/metrics/tests/test_sparkline_service.py`
  - Acceptance: ✅ 13 tests passing

---

## Phase 4: Industry Benchmarks Foundation [XL] ✅ COMPLETE

**Goal:** Introduce benchmark comparisons against similar companies

### Backend

- [x] **4.1** Create `IndustryBenchmark` model
  - Fields: metric_name, team_size_bucket, p25/p50/p75/p90, source, year
  - File: `apps/metrics/models/benchmarks.py`
  - Migration: `0022_add_industry_benchmark.py`
  - Acceptance: ✅ Migration runs successfully

- [x] **4.2** Create benchmark data migration
  - Seed initial DORA 2024 benchmarks
  - Cover: cycle_time, review_time, pr_count, ai_adoption, deployment_freq
  - Migration: `0023_seed_dora_benchmarks.py`
  - 20 benchmark rows (5 metrics × 4 team sizes)
  - Acceptance: ✅ Benchmark data queryable

- [x] **4.3** Create `benchmark_service.py` module
  - `get_team_size_bucket(team)` - Determines team size category
  - `calculate_percentile(value, benchmarks)` - Percentile calculation with interpolation
  - `get_interpretation(value, benchmark)` - Human-readable interpretation
  - `get_benchmark_for_team(team, metric)` - Full benchmark comparison
  - `get_all_benchmarks_for_team(team)` - All metrics comparison
  - File: `apps/metrics/services/benchmark_service.py`
  - Acceptance: ✅ Returns accurate percentile positioning

- [x] **4.4** Create benchmark API endpoint
  - `/api/benchmarks/<metric>/` - Returns JSON benchmark comparison
  - `/panels/benchmark/<metric>/` - Returns HTML panel partial
  - Include team value, percentile, benchmark data, interpretation
  - Files: `apps/metrics/views/chart_views.py`, `apps/metrics/urls.py`
  - Acceptance: ✅ JSON API and HTML panel endpoints working

### Frontend

- [x] **4.5** Create benchmark panel component
  - `templates/metrics/analytics/trends/benchmark_panel.html`
  - Visual percentile bar with colored zones (error/warning/success/primary)
  - Team value display with unit
  - Interpretation text (Elite/High/Medium/Low/Needs Improvement)
  - Acceptance: ✅ Panel displays correctly

- [x] **4.6** Add benchmark section to trends page
  - Benchmark panel loads via HTMX on trends page
  - Updates when metric selector changes
  - File: `templates/metrics/analytics/trends.html`
  - Acceptance: ✅ Benchmark visible on trends page

- [ ] **4.7** Create benchmarks detail page (DEFERRED)
  - Note: Not needed for MVP - benchmark panel on trends page is sufficient
  - Can add dedicated benchmarks page in future iteration

### Tests

- [x] **4.8** Write benchmark model tests
  - 5 tests for IndustryBenchmark model
  - Test creation, string representation, team size buckets, metric names
  - File: `apps/metrics/tests/test_benchmarks.py`
  - Acceptance: ✅ 5 model tests passing

- [x] **4.9** Write benchmark service tests
  - 15 tests for benchmark service functions
  - Test team size bucket detection (4 tests)
  - Test percentile calculation (4 tests)
  - Test interpretation (5 tests)
  - Test full benchmark for team (1 test)
  - Test all benchmarks for team (1 test)
  - Acceptance: ✅ 15 service tests passing

- [x] **4.10** Write view integration tests
  - 3 tests for benchmark API endpoint
  - Test authentication, JSON response, 200 status
  - Acceptance: ✅ 3 view tests passing

---

## Phase 5: Actionable Insights Engine [XL] ✅ COMPLETE

**Goal:** Surface data-driven recommendations and correlations

### Backend

- [x] **5.1** Create insight generation service functions
  - `generate_trend_insights()` - Week-over-week metric comparisons
  - `generate_benchmark_insights()` - Performance vs industry benchmarks
  - `generate_achievement_insights()` - AI adoption and PR count milestones
  - `generate_all_insights()` - Orchestrates all generators, handles dismissed
  - File: `apps/metrics/services/insight_service.py`
  - Acceptance: ✅ All generators return DailyInsight objects

- [x] **5.2** Create InsightRule classes for rule-based engine
  - `BenchmarkComparisonRule` - Elite (top 25%) and needs improvement (bottom 10%)
  - `AchievementMilestoneRule` - AI adoption (25/50/75/90%) and PR count milestones
  - Integrated with existing rules: AIAdoptionTrendRule, CycleTimeTrendRule, etc.
  - File: `apps/metrics/insights/rules.py`
  - Acceptance: ✅ New rules registered in engine

- [x] **5.3** Create Celery tasks for daily insight generation
  - `compute_team_insights(team_id)` - Generate insights for single team
  - `compute_all_team_insights()` - Dispatch tasks for all teams
  - Registered rules at module import time
  - File: `apps/metrics/tasks.py`
  - Acceptance: ✅ Tasks can be called via Celery

- [x] **5.4** Add dismiss insight endpoint
  - `POST /a/<team>/metrics/insights/<id>/dismiss/`
  - Sets `is_dismissed=True` and `dismissed_at` timestamp
  - Returns 200 for HTMX partial removal
  - File: `apps/metrics/views/dashboard_views.py`
  - Acceptance: ✅ Dismiss works from dashboard

- [x] **5.5** Get recent insights service function
  - `get_recent_insights(team, limit=5)` - Returns non-dismissed insights
  - Orders by date desc, priority, category
  - File: `apps/metrics/services/insight_service.py`
  - Acceptance: ✅ Dashboard shows latest insights

### Frontend

- [x] **5.6** Insights panel on CTO dashboard
  - Shows 5 most recent non-dismissed insights
  - Dismiss button with HTMX for smooth removal
  - Priority-based styling (high=warning, medium=info, low=default)
  - File: `templates/metrics/cto_dashboard.html`
  - Acceptance: ✅ Panel displays on dashboard

### Tests

- [x] **5.7** Write insight generation tests
  - 12 tests for `insight_service.py` functions
  - TestTrendInsightGeneration (4 tests)
  - TestBenchmarkInsightGeneration (3 tests)
  - TestAchievementInsightGeneration (2 tests)
  - TestGenerateAllInsights (3 tests)
  - File: `apps/metrics/tests/test_insight_generation.py`
  - Acceptance: ✅ All 12 tests passing

- [x] **5.8** Write insight rules tests
  - 51 tests for all InsightRule implementations
  - Tests for CycleTimeTrendRule, AIAdoptionTrendRule
  - Tests for HotfixSpikeRule, RevertSpikeRule, CIFailureRateRule
  - Tests for RedundantReviewerRule, UnlinkedPRsRule
  - Tests for BenchmarkComparisonRule, AchievementMilestoneRule
  - File: `apps/metrics/tests/test_insight_rules.py`
  - Acceptance: ✅ All 51 tests passing

- [x] **5.9** Write insight dashboard tests
  - 11 tests for dashboard views and service
  - TestGetRecentInsightsService (4 tests)
  - TestDismissInsightView (6 tests)
  - TestCTOOverviewWithInsights (2 tests)
  - File: `apps/metrics/tests/test_insight_dashboard.py`
  - Acceptance: ✅ All 11 tests passing

---

## Phase 6: Educational Content & Upsells [M]

**Goal:** Connect insights to solutions (case studies, consulting)

(Tasks unchanged - see full details above)

---

## Completion Checklist

### Phase 1 Complete When: ✅
- [x] Date picker works on all analytics pages
- [x] Monthly data available for 12+ months
- [x] URLs are bookmarkable with date params
- [x] All unit tests passing (33 new tests)

### Phase 2 Complete When: ✅
- [x] Trends page accessible from analytics nav
- [x] Full-width chart renders correctly
- [x] YoY comparison works
- [x] Zoom/pan functional on charts
- [x] All unit tests passing (20 new tests)

### Phase 3 Complete When: ✅
- [x] Sparklines visible on all key metric cards
- [x] Change percentages accurate
- [x] Mobile-friendly display (w-20 h-6 sparklines)
- [x] All unit tests passing (13 new tests, 1652 total)

### Phase 4 Complete When: ✅
- [x] Benchmark data seeded (20 rows: 5 metrics × 4 team sizes)
- [x] Team percentile calculated correctly
- [x] Benchmark panel displays on trends page
- [x] All unit tests passing (23 new tests)

### Phase 5 Complete When: ✅
- [x] Insights generate automatically
- [x] All insight types implemented (9 rules total)
- [x] Dismiss functionality works
- [x] Daily refresh task running (Celery tasks)
- [x] All unit tests passing (74 new tests)

### Phase 6 Complete When:
- [ ] Case study cards display
- [ ] Consulting request form works
- [ ] Email notifications sent
- [ ] All unit tests passing

---

## Notes

- ✅ Phase 1 complete - extended date ranges working
- ✅ Phase 2 complete - trends page with wide charts
- ✅ Phase 3 complete - sparkline mini-charts on key metric cards
- ✅ Phase 4 complete - industry benchmarks with DORA 2024 data
- ✅ Phase 5 complete - actionable insights engine with 9 rules
- Phase 6 depends on having content ready (marketing input needed)
- Future: Consider adding industry/vertical-based benchmarks via onboarding survey

## Files Created/Modified

### Phase 1
- `apps/metrics/view_utils.py` - Added `get_extended_date_range()`, `ExtendedDateRange` TypedDict
- `apps/metrics/services/dashboard_service.py` - Added monthly aggregation functions
- `apps/metrics/views/analytics_views.py` - Updated context builder
- `templates/metrics/partials/date_range_picker.html` - New Alpine.js component
- `templates/metrics/analytics/base_analytics.html` - Updated with date picker
- `apps/metrics/tests/test_view_utils.py` - 20 new tests
- `apps/metrics/tests/test_monthly_aggregation.py` - 13 new tests

### Phase 2
- `apps/metrics/views/trends_views.py` - New views module
- `apps/metrics/views/__init__.py` - Added exports
- `apps/metrics/urls.py` - Added trends URLs
- `templates/metrics/analytics/trends.html` - Main trends page
- `templates/metrics/analytics/trends/wide_chart.html` - Chart partial
- `templates/metrics/analytics/base_analytics.html` - Added Trends tab
- `assets/javascript/dashboard/trend-charts.js` - New JS module
- `assets/javascript/app.js` - Added trend charts imports
- `apps/metrics/tests/test_trends_views.py` - 20 new tests

### Phase 3
- `apps/metrics/services/dashboard_service.py` - Added `get_sparkline_data()` function
- `apps/metrics/views/chart_views.py` - Updated `key_metrics_cards` view with sparklines context
- `templates/metrics/partials/key_metrics_cards.html` - Added sparkline canvases and trend indicators
- `assets/javascript/dashboard/sparkline.js` - New sparkline Chart.js module
- `assets/javascript/app.js` - Added sparkline imports and exports
- `apps/metrics/tests/test_sparkline_service.py` - 13 new tests

### Phase 4
- `apps/metrics/models/benchmarks.py` - New IndustryBenchmark model
- `apps/metrics/models/__init__.py` - Added model export
- `apps/metrics/migrations/0022_add_industry_benchmark.py` - Model migration
- `apps/metrics/migrations/0023_seed_dora_benchmarks.py` - Data seed migration
- `apps/metrics/services/benchmark_service.py` - New benchmark service module
- `apps/metrics/services/__init__.py` - Added service export
- `apps/metrics/views/chart_views.py` - Added `benchmark_data` and `benchmark_panel` views
- `apps/metrics/views/__init__.py` - Added view exports
- `apps/metrics/urls.py` - Added benchmark URLs
- `templates/metrics/analytics/trends/benchmark_panel.html` - New panel component
- `templates/metrics/analytics/trends.html` - Added benchmark section
- `apps/metrics/tests/test_benchmarks.py` - 23 new tests

### Phase 5
- `apps/metrics/services/insight_service.py` - Insight generation functions
- `apps/metrics/insights/rules.py` - Added BenchmarkComparisonRule, AchievementMilestoneRule
- `apps/metrics/tasks.py` - Registered new insight rules, LLM analysis tasks
- `apps/metrics/views/dashboard_views.py` - Added dismiss_insight endpoint
- `apps/metrics/tests/test_insight_generation.py` - 12 tests for insight generators
- `apps/metrics/tests/test_insight_rules.py` - 51 tests for all insight rules
- `apps/metrics/tests/test_insight_dashboard.py` - 11 tests for dashboard integration
