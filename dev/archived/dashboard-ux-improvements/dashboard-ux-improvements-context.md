# Dashboard UX Improvements - Context

**Last Updated:** 2025-12-14

## Recent Fixes (2025-12-14)

### HTMX Days Filter Bug - FIXED
- **Files Modified**: `apps/metrics/views/dashboard_views.py`
- **Solution**: Added `request.htmx` check to return partial template (`#page-content`) for HTMX requests
- **E2E Tests Added**: `tests/e2e/dashboard.spec.ts` - "HTMX partial swap" tests for both dashboards

### Slack Icon Color - Investigated
- **Finding**: The red color (#E01E5A) is Slack's official brand color, not a bug
- **Location**: `templates/web/app_home.html:92`
- **Decision**: Keep as-is (official brand color) or optionally change to teal for consistency

### Quick Stats on App Home - Known Issue
- **Issue**: Shows "-" for some stats on app home page
- **Root Cause**: Service returns flat dict but template expects nested structure
- **Status**: Needs fix (update template or service)

---

## Key Files

### Views

| File | Purpose | Modify? |
|------|---------|---------|
| `apps/web/views.py` | `team_home()` - App home page view | Yes |
| `apps/metrics/views/dashboard_views.py` | `team_dashboard()` - Team dashboard | Yes |
| `apps/metrics/views/chart_views.py` | Chart partial views | Yes |
| `apps/metrics/urls.py` | URL patterns for metrics | Yes |

### Templates

| File | Purpose | Modify? |
|------|---------|---------|
| `templates/web/app_home.html` | App home page (rewrite) | Yes |
| `templates/metrics/team_dashboard.html` | Team dashboard layout | Yes |
| `templates/metrics/cto_overview.html` | Reference for chart patterns | No (reference) |
| `templates/metrics/partials/filters.html` | Date range filter | No |

### Models

| File | Purpose | Modify? |
|------|---------|---------|
| `apps/integrations/models.py` | Integration status models | No (read) |
| `apps/metrics/models.py` | PR, Review, Survey models | No (read) |

### Services (to create)

| File | Purpose |
|------|---------|
| `apps/integrations/services/status.py` | Integration status detection |
| `apps/metrics/services/quick_stats.py` | Quick stats calculation |

### JavaScript

| File | Purpose | Modify? |
|------|---------|---------|
| `assets/javascript/dashboard/dashboard-charts.js` | Chart.js utilities | Maybe |
| `assets/javascript/app.js` | Main app bundle | No |

---

## PRD References

### From `prd/DASHBOARDS.md`

**Team Dashboard Widgets (Section 2):**
1. Team Velocity (Line Chart) - Story points by sprint/week
2. PR Cycle Time Trend (Line Chart) - ✅ Exists
3. Review Distribution (Pie Chart) - **To add**
4. AI Detective Leaderboard (Table) - ✅ Exists
5. Recent PRs (Table) - **To add**

**Key Metrics Cards (Section 1.4):**
- PRs Merged (this week vs last week %)
- Avg Cycle Time (hours, vs last week %)
- Avg Quality Rating (x/3, vs last week)
- AI-Assisted PR % (vs last week)

### From `prd/ONBOARDING.md`

**Setup Steps:**
1. Connect GitHub (Required)
2. Connect Jira (Optional)
3. Connect Slack (Optional)

---

## Existing Patterns

### HTMX Lazy Loading (from cto_overview.html)

```html
<div id="container"
     hx-get="{% url 'metrics:chart_name' %}?days={{ days }}"
     hx-trigger="load"
     hx-swap="innerHTML">
  <span class="loading loading-spinner loading-lg"></span>
</div>
```

### Stats Card (from cards_metrics partial)

```html
<div class="stats shadow">
  <div class="stat">
    <div class="stat-title">PRs Merged</div>
    <div class="stat-value">{{ value }}</div>
    <div class="stat-desc text-success">↑ {{ change }}%</div>
  </div>
</div>
```

### Chart Partial Template Pattern

```html
<!-- metrics/partials/cycle_time_chart.html -->
<canvas id="cycle-time-chart"></canvas>
<script>
  document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('cycle-time-chart');
    new Chart(ctx, {
      type: 'line',
      data: {{ chart_data|safe }},
      options: { ... }
    });
  });
</script>
```

---

## Database Queries

### Integration Status Check

```python
from apps.integrations.models import GitHubIntegration, JiraIntegration, SlackIntegration

def get_integration_status(team):
    github = GitHubIntegration.objects.filter(team=team).first()
    jira = JiraIntegration.objects.filter(team=team).first()
    slack = SlackIntegration.objects.filter(team=team).first()

    return {
        'github_connected': github is not None,
        'jira_connected': jira is not None,
        'slack_connected': slack is not None,
    }
```

### Quick Stats Queries

```python
from django.db.models import Avg, Count
from apps.metrics.models import PullRequest, PRSurveyReview

# PRs merged in period
prs = PullRequest.objects.filter(
    team=team,
    state='merged',
    merged_at__gte=start_date
).count()

# Average cycle time
avg_cycle = PullRequest.objects.filter(
    team=team,
    state='merged',
    merged_at__gte=start_date
).aggregate(avg=Avg('cycle_time_hours'))['avg']

# AI-assisted percentage
ai_prs = PRSurvey.objects.filter(
    pull_request__team=team,
    ai_assisted__isnull=False
).aggregate(
    total=Count('id'),
    ai_yes=Count('id', filter=Q(ai_assisted=True))
)
```

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Layout | Stacked (single column) | Better mobile experience, clearer hierarchy |
| Stats position | Top of page | Immediate value visibility |
| Chart order | Stats → Throughput → Cycle → Distribution → Leaderboard → Recent | Importance order |
| Empty state | Show guidance, not blank | Better UX for new users |
| New user detection | Check GitHub integration + PR count | Simplest reliable method |

---

## Test Accounts

| Email | Password | Role | Has Data? |
|-------|----------|------|-----------|
| admin@example.com | admin123 | Admin | Yes (demo) |
| user@example.com | user123 | Member | Yes (demo) |

---

## Related URLs

| URL | View | Purpose |
|-----|------|---------|
| `/app/` | `web_team:home` | App home page |
| `/app/metrics/dashboard/` | `metrics:dashboard_redirect` | Redirects by role |
| `/app/metrics/dashboard/team/` | `metrics:team_dashboard` | Team dashboard |
| `/app/metrics/dashboard/cto/` | `metrics:cto_overview` | CTO dashboard |
| `/app/integrations/` | `integrations:integrations_home` | Integration status |
