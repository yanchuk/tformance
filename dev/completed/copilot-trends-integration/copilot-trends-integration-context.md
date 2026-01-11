# Copilot Acceptance in Trends Tab - Context

**Last Updated:** 2026-01-11

## Key Files

### Service Layer

| File | Purpose | Current State |
|------|---------|---------------|
| `apps/metrics/services/dashboard/copilot_metrics.py` | Copilot metrics functions | Has `get_copilot_trend()` (weekly), needs monthly + wrapper |
| `apps/metrics/services/dashboard/__init__.py` | Service exports | Needs new function exports |
| `apps/metrics/models/aggregations.py` | `AIUsageDaily` model | Ready, has all required fields |

### View Layer

| File | Purpose | Current State |
|------|---------|---------------|
| `apps/metrics/views/trends_views.py` | Trends page views | Has 4 metrics, needs `copilot_acceptance` |
| `templates/metrics/analytics/trends.html` | Trends UI | Ready, auto-renders from METRIC_CONFIG |

### Test Files

| File | Purpose | Status |
|------|---------|--------|
| `apps/metrics/tests/dashboard/test_copilot_metrics.py` | Service tests | Exists, needs new tests |
| `apps/metrics/tests/test_trends_views.py` | View tests | May need creation |

---

## Critical Code Patterns

### Existing Monthly Trend Pattern (from `trend_metrics.py`)

```python
def get_monthly_cycle_time_trend(
    team: Team, start_date: date, end_date: date, repo: str | None = None
) -> list[dict]:
    """Get monthly cycle time trend."""
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    monthly_data = (
        prs.annotate(month=TruncMonth("merged_at"))
        .values("month")
        .annotate(avg_value=Avg("cycle_time_hours"))
        .order_by("month")
    )

    return [
        {"month": entry["month"].strftime("%Y-%m"), "value": float(entry["avg_value"] or 0)}
        for entry in monthly_data
    ]
```

### Existing Weekly Copilot Trend (from `copilot_metrics.py`)

```python
def get_copilot_trend(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get Copilot acceptance rate trend by week.

    Returns:
        list of dicts with keys:
            - week (date): Week start date
            - acceptance_rate (Decimal): Acceptance rate percentage
    """
    copilot_usage = AIUsageDaily.objects.filter(
        team=team,
        source="copilot",
        date__gte=start_date,
        date__lte=end_date,
    )

    weekly_data = (
        copilot_usage.annotate(week=TruncWeek("date"))
        .values("week")
        .annotate(
            total_suggestions=Sum("suggestions_shown"),
            total_accepted=Sum("suggestions_accepted"),
        )
        .order_by("week")
    )
    # ... calculates acceptance_rate
```

### METRIC_CONFIG Pattern (from `trends_views.py`)

```python
METRIC_CONFIG = {
    "cycle_time": {
        "name": "Cycle Time",
        "unit": "hours",
        "color": "#F97316",  # primary - coral orange
        "yAxisID": "y",
    },
    "ai_adoption": {
        "name": "AI Adoption",
        "unit": "%",
        "color": "#FDA4AF",  # secondary - rose
        "yAxisID": "y2",
    },
}
```

### Function Maps Pattern (from `trends_views.py`)

```python
# In trend_chart_data()
metric_functions = {
    "cycle_time": dashboard_service.get_monthly_cycle_time_trend,
    "review_time": dashboard_service.get_monthly_review_time_trend,
    "pr_count": dashboard_service.get_monthly_pr_count,
    "ai_adoption": dashboard_service.get_monthly_ai_adoption,
}

weekly_functions = {
    "cycle_time": dashboard_service.get_cycle_time_trend,
    "review_time": dashboard_service.get_review_time_trend,
    "pr_count": dashboard_service.get_weekly_pr_count,
    "ai_adoption": dashboard_service.get_ai_adoption_trend,
}
```

---

## Key Decisions Made

| Decision | Choice | Date | Rationale |
|----------|--------|------|-----------|
| Color | Emerald green (#10B981) | 2026-01-11 | Distinct from AI Adoption rose, success family |
| Y-Axis | y2 (secondary) | 2026-01-11 | Percentage metric, like AI Adoption |
| Repo filter | Ignored (documented) | 2026-01-11 | Copilot data is org-level |
| Format | `{month/week, value}` | 2026-01-11 | Match existing trend functions |
| Weekly format | `YYYY-MM-DD` | 2026-01-11 | Match `ai_adoption` (same % metric type), not `pr_count` (`YYYY-WNN`) |

## Plan Review Findings (2026-01-11)

**Issues Identified:**
1. ✅ Weekly format clarified - use `YYYY-MM-DD` like `ai_adoption`
2. ✅ Added `TruncMonth` import requirement
3. ✅ Added 4 additional test cases for edge cases

**Additional Tests Added:**
- `test_get_monthly_copilot_acceptance_trend_zero_suggestions` - Division edge case
- `test_get_monthly_copilot_acceptance_trend_aggregates_multiple_members` - Cross-member aggregation
- `test_get_monthly_copilot_acceptance_trend_excludes_cursor_source` - Source filtering
- Repo parameter test (implicit in existing tests)

**Metric Distinction (for UI tooltip):**
| Metric | Data Source | What It Measures |
|--------|-------------|------------------|
| AI Adoption % | PR analysis (LLM detection) | % of PRs that used ANY AI tool |
| Copilot Acceptance % | GitHub Copilot API | % of Copilot suggestions accepted |

---

## Dependencies

### Internal Dependencies

| Component | Dependency | Status |
|-----------|------------|--------|
| `AIUsageDaily` model | Django ORM | ✅ Ready |
| `TruncMonth`, `TruncWeek` | Django functions | ✅ Available |
| `dashboard_service` | Service exports | Needs update |

### Related Task: copilot-mock-data-realism

**Location:** `dev/active/copilot-mock-data-realism/`

**Relationship:** NO BLOCKING DEPENDENCY

| This Task | Related Task |
|-----------|--------------|
| Reads from `AIUsageDaily` | Writes to `AIUsageDaily` |
| Aggregates existing data | Changes how new data is created |
| Service layer only | Generator + parser changes |

**Why no dependency:**
- `AIUsageDaily` has stable fields: `suggestions_shown`, `suggestions_accepted`, `acceptance_rate`
- Mock data fix changes API response parsing, not database schema
- Existing demo data already in database works fine
- After both complete, re-seed for realistic patterns (30% vs 40-50%)

### External Dependencies

None - all data already exists in database.

---

## Data Model Reference

### AIUsageDaily Model

```python
class AIUsageDaily(BaseTeamModel):
    """Daily AI tool usage statistics per team member."""
    member = models.ForeignKey(TeamMember, ...)
    date = models.DateField()
    source = models.CharField(choices=[("copilot", "Copilot"), ("cursor", "Cursor")])
    suggestions_shown = models.IntegerField(default=0)
    suggestions_accepted = models.IntegerField(default=0)
    acceptance_rate = models.DecimalField(...)  # Pre-calculated
```

### Acceptance Rate Calculation

```python
acceptance_rate = (suggestions_accepted / suggestions_shown) * 100
# Example: 1000 accepted / 2500 shown = 40%
```

---

## Test Data Setup

### Factory Pattern

```python
from apps.metrics.factories import TeamFactory, TeamMemberFactory
from apps.metrics.models import AIUsageDaily

class TestCopilotTrend(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

        # Create test data across months
        AIUsageDaily.objects.create(
            team=self.team,
            member=self.member,
            date=date(2025, 1, 15),
            source="copilot",
            suggestions_shown=1000,
            suggestions_accepted=400,
            acceptance_rate=Decimal("40.00"),
        )
```

---

## Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| No Copilot data | Return empty list `[]` |
| Zero suggestions shown | Return 0.0% (not division error) |
| Invalid date range | Let Django handle, return empty |
| Non-existent team | Return empty (team filter handles) |

---

## Related PRs/Commits

| Commit | Description | Date |
|--------|-------------|------|
| `68e465a` | feat(team): add Copilot % column and Champion badges | 2026-01-11 |
| `0e1ce67` | feat(copilot): improve AI Adoption dashboard UX | 2026-01-11 |

---

## Notes for Context Reset

If context is lost:
1. This task adds "Copilot Acceptance" as a 5th metric to the Trends tab
2. Follow the same pattern as existing metrics (cycle_time, ai_adoption, etc.)
3. The data already exists in `AIUsageDaily` - just needs aggregation functions
4. Tests should follow TDD workflow: RED → GREEN → REFACTOR
