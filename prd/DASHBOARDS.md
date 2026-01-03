# Tformance Dashboard Views (Chart.js + HTMX)

> Part of [PRD Documentation](README.md)

**Current Implementation:** Dashboard functionality lives in `apps/metrics/` with analytics views and chart endpoints. This document describes the specification and current implementation.

## Overview

Dashboards are built natively using Django views, Chart.js for visualizations, and HTMX for interactivity. All charts and data tables are rendered server-side with lazy loading for optimal performance.

**Why Native Dashboards (not Metabase):**
- No external dependencies or separate deployment
- Full control over styling (DaisyUI/TailwindCSS)
- Chart.js already integrated in codebase via Vite
- HTMX enables lazy loading and dynamic updates
- Git version control for dashboard definitions
- Faster MVP development

**Technology Stack:**
- **Chart.js 4.5.1** - Already installed, utilities in `assets/javascript/dashboard/`
- **HTMX** - Lazy loading with `hx-trigger="load"`, dynamic filtering
- **DaisyUI** - Consistent styling for cards, tables, filters
- **Django Views** - Server-side data preparation and permissions

---

## Dashboard Structure

| Dashboard | Audience | Access |
|-----------|----------|--------|
| CTO Overview | CTO/Admin | Full org data |
| Team Dashboard | Team Lead | Their team only |
| Individual Dashboard | Developer | Their own data only |
| AI Correlation Deep Dive | CTO/Admin | Full org data |

---

## 1. CTO Overview Dashboard

**Purpose:** High-level health check and AI impact

### Widgets

#### 1.1 AI Adoption Trend (Line Chart)
- **X-axis:** Weeks
- **Y-axis:** % of PRs marked AI-assisted
- **Overlay:** Team avg Copilot suggestions accepted (if available)
- **Chart.js type:** `line` with dual Y-axis

#### 1.2 AI vs Delivery Correlation (Scatter Plot)
- **X-axis:** AI-assisted PRs per week (per developer)
- **Y-axis:** Total PRs merged per week
- **Points:** One per developer
- **Trend line:** Show correlation direction
- **Chart.js type:** `scatter` with regression line plugin

#### 1.3 Quality by AI Status (Bar Chart)
- **Bars:** AI-assisted PRs vs Non-AI PRs
- **Y-axis:** Average quality rating (1-3)
- **Goal:** Show if AI-assisted code has different quality perception
- **Chart.js type:** `bar` grouped

#### 1.4 Key Metrics Cards (DaisyUI Stats)
| Card | Value | Comparison |
|------|-------|------------|
| PRs Merged | This week count | vs last week % |
| Avg Cycle Time | Hours | vs last week % |
| Avg Quality Rating | x/3 | vs last week |
| AI-Assisted PR % | % | vs last week |

**Implementation:** DaisyUI `stat` components with comparison badges

#### 1.5 Team Breakdown Table
| Column | Description |
|--------|-------------|
| Team | Team name |
| Members | Count |
| PRs Merged | This week |
| Avg Cycle Time | Hours |
| AI Adoption % | % of PRs AI-assisted |

**Implementation:** DaisyUI `table` with sortable headers via Alpine.js

---

## 2. Team Dashboard

**Purpose:** Team lead view of their team's performance

### Widgets

#### 2.1 Team Velocity (Line Chart)
- **X-axis:** Sprints or weeks
- **Y-axis:** Story points completed
- **Chart.js type:** `line`

#### 2.2 PR Cycle Time Trend (Line Chart)
- **X-axis:** Weeks
- **Y-axis:** Average cycle time (hours)
- **Chart.js type:** `line` with `cumulativeChartWithDates()` utility

#### 2.3 Review Distribution (Pie Chart)
- **Slices:** Team members
- **Value:** Number of reviews done
- **Goal:** Identify if review load is balanced
- **Chart.js type:** `pie` via `renderChart('pie', ...)` utility

#### 2.4 AI Detective Leaderboard (Table)
| Column | Description |
|--------|-------------|
| Rank | 1, 2, 3... |
| Name | Team member |
| Correct Guesses | x/y |
| Accuracy | % |

**Implementation:** DaisyUI `table` with medal icons for top 3

#### 2.5 Recent PRs (Table)
| Column | Description |
|--------|-------------|
| PR Title | Linked to GitHub |
| Author | Name |
| Cycle Time | Hours |
| Quality Rating | Could be better / OK / Super |
| AI Status | Yes/No (if revealed) |

**Implementation:** DaisyUI `table` with HTMX pagination

---

## 3. Individual Dashboard

**Purpose:** Developer's personal view (visible only to themselves + CTO)

### Widgets

#### 3.1 My Activity (Line Chart)
- **X-axis:** Weeks
- **Y-axis:** PRs merged, commits (dual axis)
- **Chart.js type:** `line` with dual Y-axis

#### 3.2 My Quality Ratings (Distribution)
- **Chart:** Bar chart or histogram
- **Buckets:** Could be better / OK / Super
- **Shows:** How my PRs are rated over time
- **Chart.js type:** `bar`

#### 3.3 My AI Usage (Line Chart)
- **X-axis:** Weeks
- **Y-axis:** AI-assisted PR count
- **Note:** Copilot metrics if available
- **Chart.js type:** `line`

#### 3.4 My Stats Cards
| Card | Value |
|------|-------|
| Total PRs | This month |
| Avg Quality Rating | x/3 |
| AI Guess Accuracy | % (as reviewer) |

**Implementation:** DaisyUI `stat` components

#### 3.5 My Recent PRs (Table)
| Column | Description |
|--------|-------------|
| PR Title | Linked to GitHub |
| Merged | Date |
| Quality Rating | Rating received |
| AI-Assisted | Self-reported |

---

## 4. AI Correlation Deep Dive

**Purpose:** Detailed analysis for CTO decision-making

### Widgets

#### 4.1 Correlation Matrix (Heatmap)
- **Rows/Cols:** Various metrics
- **Values:** Correlation coefficients
- **Metrics:** AI-assisted %, Cycle time, Quality rating, PRs merged, Story points
- **Implementation:** Chart.js matrix plugin or custom canvas rendering

#### 4.2 Before/After Analysis (Comparison Table)
| Metric | Before AI Adoption | After AI Adoption | Change |
|--------|-------------------|-------------------|--------|
| Avg Cycle Time | x hrs | y hrs | -z% |
| PRs/Week | x | y | +z% |
| Quality Rating | x | y | +z |

**Note:** Requires 8+ weeks of data with clear adoption inflection point

#### 4.3 High AI Users vs Low AI Users (Comparison)
- **Split:** Top 50% AI usage vs Bottom 50%
- **Compare:** Cycle time, quality, throughput
- **Goal:** See if heavy AI users perform differently
- **Chart.js type:** Grouped `bar` chart

#### 4.4 AI by Repository (Table)
| Column | Description |
|--------|-------------|
| Repository | Repo name |
| Total PRs | Count |
| AI-Assisted | % |
| Avg Quality | Rating |

#### 4.5 Quality Trend by AI Adoption (Line Chart)
- **X-axis:** Weeks
- **Y-axis (dual):** AI adoption %, Avg quality rating
- **Goal:** See if quality changed as AI adoption increased
- **Chart.js type:** `line` with dual Y-axis

---

## Filters (Global)

Available on all dashboards:

| Filter | Options | Implementation |
|--------|---------|----------------|
| Date Range | Last 7 days, 30 days, 90 days, custom | HTMX `hx-get` with query params |
| Team | All teams, specific team | Alpine.js dropdown + HTMX |
| Repository | All repos, specific repo | Alpine.js dropdown + HTMX |

CTO-only filters:
| Filter | Options |
|--------|---------|
| Individual | All, specific person (for 1:1 prep) |

**Implementation Pattern:**
```html
<select hx-get="/a/{team_slug}/analytics/chart-data/" hx-target="#chart-container"
        hx-include="[name='date_range'],[name='team']">
  <option value="7">Last 7 days</option>
  <option value="30">Last 30 days</option>
</select>
```

---

## Technical Implementation

### Lazy Loading Pattern

Charts are loaded asynchronously to improve page load time:

```html
<!-- Template -->
<div id="pr-chart"
     hx-get="{% url 'metrics:cycle_time_chart' team_slug=team.slug %}"
     hx-trigger="load"
     hx-swap="innerHTML">
  <span class="loading loading-spinner loading-lg"></span>
</div>
```

### Django View Pattern

```python
@team_admin_required
def cycle_time_chart(request, team_slug):
    team = request.team
    days = int(request.GET.get('days', 30))

    # Query data using team-scoped manager
    data = get_cycle_time_trend(team, days=days)

    # Return partial template with chart data
    return render(request, 'metrics/partials/cycle_time_chart.html', {
        'chart_data': json.dumps(data),
        'chart_id': 'cycle-time',
    })
```

### Chart.js Integration

Existing utilities in `assets/javascript/dashboard/dashboard-charts.js`:

```javascript
import Chart from 'chart.js/auto';

export const DashboardCharts = {
  barChartWithDates: (ctx, start, end, data, label) => { ... },
  cumulativeChartWithDates: (ctx, start, end, data, label, startValue) => { ... }
};
```

Additional chart types to add:
- `pieChart(ctx, data, labels)` - For distribution charts
- `scatterChart(ctx, data, options)` - For correlation plots
- `lineChartDualAxis(ctx, data1, data2, labels)` - For trends with comparison

### Permission Filtering

All data queries are filtered by user role at the view level:

```python
def get_visible_members(user, team):
    """Return team members visible to the current user."""
    if user.has_admin_access(team):
        return TeamMember.objects.filter(team=team)
    elif user.has_lead_access(team):
        return TeamMember.objects.filter(team=team, lead=user)
    else:
        return TeamMember.objects.filter(team=team, user=user)
```

---

## File Organization

**Current Implementation** (as of Jan 2026):

```
apps/metrics/
├── views/                    # 58 exported view functions
│   ├── __init__.py           # Re-exports all views
│   ├── analytics_views.py    # Tabbed analytics pages (5 functions)
│   ├── chart_views.py        # HTMX chart/card/table endpoints (36 functions)
│   ├── dashboard_views.py    # Dashboard pages & insights (8 functions)
│   ├── pr_list_views.py      # Pull Requests data explorer (3 functions)
│   └── trends_views.py       # Trends & benchmarks (5 functions)
├── services/                 # 16 service modules
│   ├── dashboard_service.py  # Key metrics, team breakdown, trends
│   ├── pr_list_service.py    # PR filtering, export, categorization
│   ├── benchmark_service.py  # Industry benchmarks (DORA)
│   ├── aggregation_service.py # Time-series data aggregation
│   ├── chart_formatters.py   # Chart data formatting utilities
│   ├── quick_stats.py        # Quick metrics calculations
│   ├── survey_service.py     # Survey data processing
│   ├── survey_tokens.py      # Survey token management
│   ├── insight_service.py    # Insight aggregation & display
│   ├── insight_llm.py        # LLM-powered insight generation
│   ├── ai_detector.py        # Main AI detection coordinator
│   ├── ai_patterns.py        # Regex patterns + PATTERNS_VERSION
│   ├── ai_signals.py         # Signal aggregation for AI detection
│   ├── ai_categories.py      # AI tool categorization (code vs review)
│   ├── ai_adoption_helpers.py # Adoption trend helpers
│   └── llm_prompts.py        # LLM prompt templates + PROMPT_VERSION
├── urls.py                   # URL patterns (metrics namespace)
└── templatetags/
    └── pr_list_tags.py       # Custom template filters

templates/metrics/            # 59 template files
├── analytics/
│   ├── base_analytics.html   # Tab navigation, date filters
│   ├── overview.html         # CTO Overview (insights, key metrics)
│   ├── ai_adoption.html      # AI metrics deep dive
│   ├── delivery.html         # Cycle time, PR size
│   ├── quality.html          # Review time, CI/CD
│   ├── team.html             # Member breakdown, leaderboard
│   └── trends.html           # Trends & benchmarks
│   └── trends/               # Trend-specific templates
│       ├── benchmark_panel.html
│       ├── pr_type_chart.html
│       ├── tech_chart.html
│       └── wide_chart.html
├── partials/                 # 41 chart/card/table partials
│   ├── key_metrics_cards.html
│   ├── cycle_time_chart.html
│   ├── ai_adoption_chart.html
│   ├── team_breakdown_table.html
│   ├── copilot_metrics_card.html
│   ├── copilot_trend_chart.html
│   ├── copilot_members_table.html
│   ├── survey_ai_detection_card.html
│   ├── survey_response_time_card.html
│   ├── jira_linkage_chart.html
│   ├── velocity_trend_chart.html
│   ├── sp_correlation_chart.html
│   ├── insights_panel.html
│   └── ...                   # Plus 28 more partials
├── pull_requests/
│   ├── list.html             # Full PR list page
│   ├── list_standalone.html  # Non-team context PR list
│   └── partials/
│       ├── table.html        # HTMX table partial
│       └── expanded_row.html # PR detail expansion
├── metrics_home.html         # Entry point
├── cto_overview.html         # Legacy (redirects to analytics)
└── team_dashboard.html       # Team lead view

assets/javascript/dashboard/  # 5 JavaScript modules
├── chart-manager.js          # Chart lifecycle management (HTMX compatible)
├── dashboard-charts.js       # Chart.js utilities (bar, line, cumulative)
├── chart-theme.js            # Easy Eyes theme colors
├── trend-charts.js           # Trend visualization
└── sparkline.js              # Inline sparkline charts
```

### Chart Manager (HTMX Integration)

The `chart-manager.js` module provides centralized Chart.js lifecycle management to prevent duplicate instances during HTMX content swaps:

```javascript
// Register chart factories
chartManager.register('cycle-time', (canvas, data) => {
  return new Chart(canvas.getContext('2d'), { /* config */ });
}, { dataId: 'cycle-time-data' });

// Charts auto-initialize on htmx:afterSwap via chartManager.initAll()
```

**Registered charts:** ai-adoption-chart, cycle-time-chart, review-time-chart, copilot-trend-chart, pr-type-chart, tech-chart, trend-chart, and more.

> **Note:** A future refactoring may extract dashboard functionality into a dedicated `apps/dashboard/` app for better separation of concerns.

---

## View Endpoints Reference

### Analytics Views (analytics_views.py)
| Function | URL Pattern | Purpose |
|----------|-------------|---------|
| `analytics_overview` | `/analytics/` | Main CTO overview tab |
| `analytics_ai_adoption` | `/analytics/ai/` | AI adoption metrics |
| `analytics_delivery` | `/analytics/delivery/` | Delivery performance |
| `analytics_quality` | `/analytics/quality/` | Quality metrics |
| `analytics_team` | `/analytics/team/` | Team breakdown |

### Chart Views (chart_views.py) - 36 Endpoints
**Key Metrics:**
- `key_metrics_cards` - Summary stat cards
- `cycle_time_chart` - Cycle time trends
- `pr_size_chart` - PR size distribution
- `review_time_chart` - Review turnaround

**AI Detection:**
- `ai_adoption_chart` - AI usage trends
- `ai_detected_metrics_card` - Detection stats
- `ai_quality_chart` - Quality by AI status
- `ai_tool_breakdown_chart` - Tool distribution
- `ai_bot_reviews_card` - Bot review stats

**Copilot Integration:**
- `copilot_metrics_card` - Copilot usage summary
- `copilot_trend_chart` - Copilot trends
- `copilot_members_table` - Per-member Copilot stats

**Jira Integration:**
- `jira_linkage_chart` - PR-issue linking
- `sp_correlation_chart` - Story points vs metrics
- `velocity_trend_chart` - Sprint velocity

**Survey Metrics:**
- `survey_ai_detection_card` - AI survey results
- `survey_response_time_card` - Response latency
- `survey_channel_distribution_card` - Survey channels

**Team & Quality:**
- `team_breakdown_table` - Team metrics table
- `leaderboard_table` - AI detective rankings
- `reviewer_workload_table` - Review distribution
- `reviewer_correlations_table` - Review patterns
- `revert_rate_card` - Revert statistics
- `cicd_pass_rate_card` - CI/CD health

### Dashboard Views (dashboard_views.py)
| Function | Purpose |
|----------|---------|
| `home` | Metrics home page |
| `cto_overview` | CTO dashboard |
| `team_dashboard` | Team lead view |
| `engineering_insights` | AI-powered insights |
| `refresh_insight` | Regenerate insight |
| `dismiss_insight` | Hide insight |
| `background_progress` | Async task status |

### Trends Views (trends_views.py)
| Function | Purpose |
|----------|---------|
| `trends_overview` | Trends dashboard |
| `trend_chart_data` | Trend data endpoint |
| `wide_trend_chart` | Full-width trend |
| `pr_type_breakdown_chart` | PR type distribution |
| `tech_breakdown_chart` | Technology breakdown |
| `benchmark_data` | DORA benchmarks |
| `benchmark_panel` | Benchmark display |
