# Jira-PR Correlation - Context & Key Files

**Last Updated**: 2026-01-01

---

## Key Files by Phase

### Phase 1: Data Foundation

| File | Lines | Purpose |
|------|-------|---------|
| `apps/metrics/models/jira.py` | 10-136 | JiraIssue model - add 4 new fields |
| `apps/integrations/services/jira_client.py` | 84-121 | `get_project_issues()` - request new fields |
| `apps/integrations/services/jira_sync.py` | 46-93 | `_convert_jira_issue_to_dict()` - map new fields |
| `apps/metrics/factories.py` | JiraIssueFactory | Update factory with new fields |

**New Fields to Add**:
```python
# In apps/metrics/models/jira.py after line 46 (after status field)
description = models.TextField(
    blank=True,
    default="",
    verbose_name="Description",
    help_text="Full issue description",
)
labels = models.JSONField(
    default=list,
    verbose_name="Labels",
    help_text="Issue labels as list",
)
priority = models.CharField(
    max_length=50,
    blank=True,
    default="",
    verbose_name="Priority",
    help_text="Issue priority (High, Medium, Low)",
)
parent_issue_key = models.CharField(
    max_length=50,
    blank=True,
    default="",
    verbose_name="Parent Issue Key",
    help_text="Parent epic/story key",
)
```

**jira_client.py Field Update**:
```python
# Line 115 - add new fields to the fields parameter
fields="summary,status,issuetype,assignee,created,updated,resolutiondate,customfield_10016,description,labels,priority,parent"
```

**jira_sync.py Extraction Update**:
```python
# In _convert_jira_issue_to_dict(), add after line 80:
description = fields.get("description", "")
labels = fields.get("labels", [])
priority_obj = fields.get("priority")
priority = priority_obj.get("name", "") if priority_obj else ""
parent_obj = fields.get("parent")
parent_issue_key = parent_obj.get("key", "") if parent_obj else ""
```

---

### Phase 2A: Linkage Donut Widget

| File | Lines | Purpose |
|------|-------|---------|
| `apps/metrics/services/dashboard_service.py` | 3159+ | Add `get_linkage_trend()` function |
| `apps/metrics/views/chart_views.py` | End | Add `jira_linkage_chart()` view |
| `apps/metrics/urls.py` | team_urlpatterns | Add URL pattern |
| `templates/metrics/cto_overview.html` | TBD | Add widget to dashboard |
| `templates/metrics/partials/jira_linkage_chart.html` | New | Donut chart partial |

**Dashboard Service Function**:
```python
def get_linkage_trend(team: Team, weeks: int = 4) -> list[dict]:
    """Get PR-Jira linkage rate trend over time.

    Returns:
        List of dicts with week_start, linkage_rate, linked_count, total_prs
    """
    # Implementation: Query PRs grouped by week, calculate linkage rate
```

---

### Phase 2B: Story Point Correlation

| File | Lines | Purpose |
|------|-------|---------|
| `apps/metrics/services/dashboard_service.py` | End | Add `get_story_point_correlation()` |
| `apps/metrics/views/chart_views.py` | End | Add `sp_correlation_chart()` view |
| `apps/metrics/urls.py` | team_urlpatterns | Add URL pattern |
| `templates/metrics/partials/sp_correlation_chart.html` | New | Grouped bar chart |

**Story Point Correlation Function**:
```python
def get_story_point_correlation(team: Team, start_date: date, end_date: date) -> dict:
    """Compare estimated story points vs actual PR delivery time.

    Returns:
        {
            "buckets": [
                {"sp_range": "1-2", "avg_hours": 4.2, "pr_count": 45, "expected_hours": 3},
                {"sp_range": "3-5", "avg_hours": 12.8, "pr_count": 82, "expected_hours": 8},
                ...
            ],
            "velocity": 2.4,  # hours per story point
            "sample_size": 162,  # total linked PRs
        }
    """
```

**Query Pattern**:
```python
# Get merged PRs with jira_key, join to JiraIssue for story_points
prs_with_sp = (
    PullRequest.objects.filter(
        team=team, state="merged", jira_key__gt="",
        merged_at__range=(start_date_dt, end_date_dt)
    )
    .select_related()  # If FK exists, otherwise manual join
)

# For each PR, look up JiraIssue by jira_key, get story_points
# Group into buckets: 1-2, 3-5, 5-8, 8-13, 13+
# Calculate average cycle_time_hours per bucket
```

---

### Phase 2C: Velocity Trend

| File | Lines | Purpose |
|------|-------|---------|
| `apps/metrics/services/dashboard_service.py` | End | Add `get_velocity_trend()` |
| `apps/metrics/views/chart_views.py` | End | Add `velocity_trend_chart()` view |
| `templates/metrics/partials/velocity_trend_chart.html` | New | Line chart |
| `templates/metrics/analytics/team/index.html` | TBD | Add widget |

**Velocity Trend Function**:
```python
def get_velocity_trend(team: Team, months: int = 6) -> list[dict]:
    """Get story points completed per week/sprint over time.

    Args:
        team: Team instance
        months: Number of months to look back

    Returns:
        List of dicts with period, story_points, issues_resolved
    """
    # If team has sprint data: group by sprint_name
    # Otherwise: group by calendar week
```

---

### Phase 3: LLM Infrastructure

| File | Lines | Purpose |
|------|-------|---------|
| `apps/metrics/services/insight_llm.py` | 339-344 | Add trends to `gather_insight_data()` |

**Enhanced gather_insight_data()**:
```python
# Add after existing jira_data (line 343)
if JiraIntegration.objects.filter(team=team).exists():
    jira_data = {
        "sprint_metrics": get_jira_sprint_metrics(team, start_date, end_date),
        "pr_correlation": get_pr_jira_correlation(team, start_date, end_date),
        # NEW: Add trends for LLM context
        "linkage_trend": get_linkage_trend(team, weeks=4),
        "velocity_trend": get_velocity_trend(team, months=3),
    }
```

---

## Existing Patterns to Follow

### Chart View Pattern (from chart_views.py)

```python
@login_and_team_required
def jira_linkage_chart(request: HttpRequest) -> HttpResponse:
    """Jira linkage donut chart."""
    start_date, end_date = get_date_range_from_request(request)
    # Use existing get_pr_jira_correlation()
    data = dashboard_service.get_pr_jira_correlation(request.team, start_date, end_date)
    trend = dashboard_service.get_linkage_trend(request.team, weeks=4)
    return TemplateResponse(
        request,
        "metrics/partials/jira_linkage_chart.html",
        {
            "linkage_data": data,
            "trend_data": trend,
        },
    )
```

### Dashboard Service Pattern (existing functions)

```python
def get_jira_sprint_metrics(team: Team, start_date: date, end_date: date) -> dict:
    """Existing pattern - query JiraIssue, aggregate, return dict."""
    from apps.metrics.models import JiraIssue

    start_date_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_date_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    issues = JiraIssue.for_team.filter(
        resolved_at__range=(start_date_dt, end_date_dt)
    )
    # ... aggregate ...
```

### Test Pattern (from test_jira_metrics.py)

```python
class TestStoryPointCorrelation(TestCase):
    """Tests for get_story_point_correlation function."""

    def setUp(self):
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()
        self.start_date = self.today - timedelta(days=90)
        self.end_date = self.today

    def test_get_story_point_correlation_function_exists(self):
        """Test that function is importable."""
        from apps.metrics.services.dashboard_service import get_story_point_correlation
        self.assertTrue(callable(get_story_point_correlation))

    def test_get_story_point_correlation_groups_by_bucket(self):
        """Should group PRs by story point range."""
        # Create JiraIssue with story_points
        issue = JiraIssueFactory(
            team=self.team,
            jira_key="PROJ-123",
            story_points=Decimal("5"),
            resolved_at=timezone.now() - timedelta(days=5),
        )
        # Create PR linked to that issue
        PullRequestFactory(
            team=self.team,
            jira_key="PROJ-123",
            state="merged",
            merged_at=timezone.now() - timedelta(days=3),
            cycle_time_hours=Decimal("12.0"),
        )

        from apps.metrics.services.dashboard_service import get_story_point_correlation
        result = get_story_point_correlation(self.team, self.start_date, self.end_date)

        # Should have bucket for 3-5 SP with 12h avg
        self.assertIn("buckets", result)
```

---

## OAuth Scope Verification

Current Jira OAuth scopes (sufficient for all enhancements):

```
read:jira-work   - Read issues, projects, sprints, story points, description, labels, priority
read:jira-user   - Read user profiles for assignee matching
offline_access   - Token refresh
```

**No scope changes required.**

---

## Database Indexes

Existing indexes on JiraIssue (sufficient):
- `jira_issue_key_idx` on `jira_key` - for PR→Jira lookups
- `jira_resolved_at_idx` on `resolved_at` - for date filtering
- `jira_sprint_idx` on `sprint_id` - for sprint grouping

Consider adding for SP correlation performance:
```python
# Optional - only if queries are slow
models.Index(fields=["team", "resolved_at", "story_points"], name="jira_sp_correlation_idx")
```

---

## Chart.js Configuration

### Donut Chart (Linkage)

```javascript
// Use ChartManager pattern
chartManager.register('jira-linkage-chart', (canvas, data) => {
  return new Chart(canvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: ['Linked', 'Unlinked'],
      datasets: [{
        data: [data.linked_count, data.unlinked_count],
        backgroundColor: [getColors().accent, getColors().baseContent + '30'],
      }]
    },
    options: {
      cutout: '60%',
      plugins: { legend: { position: 'bottom' } }
    }
  });
}, { dataId: 'jira-linkage-data' });
```

### Grouped Bar Chart (SP Correlation)

```javascript
chartManager.register('sp-correlation-chart', (canvas, data) => {
  return new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels: data.buckets.map(b => b.sp_range),
      datasets: [
        { label: 'Expected (h)', data: data.buckets.map(b => b.expected_hours), /* ... */ },
        { label: 'Actual (h)', data: data.buckets.map(b => b.avg_hours), /* ... */ }
      ]
    }
  });
}, { dataId: 'sp-correlation-data' });
```

---

## Error Handling

- **No Jira Integration**: Check `JiraIntegration.objects.filter(team=team).exists()` before calling functions
- **No Story Points**: Filter `story_points__isnull=False` in queries
- **No Linked PRs**: Return empty buckets with sample_size=0
- **API Errors**: Already handled in jira_client.py with JiraClientError
