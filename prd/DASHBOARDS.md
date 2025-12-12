# Dashboard Views (Chart.js + HTMX)

> Part of [PRD Documentation](README.md)

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
<select hx-get="/dashboard/chart-data/" hx-target="#chart-container"
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
     hx-get="{% url 'dashboard:pr_throughput_chart' team_slug=team.slug %}"
     hx-trigger="load"
     hx-swap="innerHTML">
  <span class="loading loading-spinner loading-lg"></span>
</div>
```

### Django View Pattern

```python
@login_and_team_required
def pr_throughput_chart(request, team_slug):
    team = get_team_from_request(request)
    date_range = request.GET.get('date_range', 30)

    # Query data
    data = PullRequest.objects.for_team(team).aggregate_by_day(...)

    # Return partial template with chart data
    return render(request, 'dashboard/partials/pr_throughput_chart.html', {
        'chart_data': json.dumps(data),
        'chart_id': 'pr-throughput',
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

```
apps/dashboard/
├── views.py          # Dashboard page views
├── api_views.py      # Chart data endpoints
├── services.py       # Data aggregation logic
├── urls.py           # URL patterns
└── templates/
    └── dashboard/
        ├── cto_overview.html
        ├── team_dashboard.html
        ├── individual_dashboard.html
        ├── ai_correlation.html
        └── partials/
            ├── stat_card.html
            ├── pr_throughput_chart.html
            ├── cycle_time_chart.html
            └── ...

assets/javascript/dashboard/
├── dashboard-charts.js    # Existing Chart.js utilities
├── chart-init.js          # Chart initialization for HTMX
└── filters.js             # Filter state management
```
