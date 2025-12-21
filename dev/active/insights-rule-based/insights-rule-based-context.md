# Phase 1: Rule-Based Insights - Context

**Last Updated:** 2025-12-21

## Key Files

### Data Sources
- `apps/metrics/services/dashboard_service.py` - 20+ aggregation functions
- `apps/metrics/services/aggregation_service.py` - Weekly metrics computation
- `apps/metrics/models.py` - All metric models

### Key Functions to Use
```python
# From dashboard_service.py
get_key_metrics(team, start_date, end_date)
get_ai_adoption_trend(team, start_date, end_date)
get_ai_quality_comparison(team, start_date, end_date)
get_team_breakdown(team, start_date, end_date)
get_reviewer_correlations(team)
get_copilot_metrics(team, start_date, end_date)
get_revert_hotfix_stats(team, start_date, end_date)
get_reviewer_workload(team, start_date, end_date)
get_iteration_metrics(team, start_date, end_date)
get_cicd_pass_rate(team, start_date, end_date)
```

### Celery Integration
- `apps/metrics/tasks.py` - Existing sync tasks
- `tformance/celery.py` - Celery config

### Dashboard Integration
- `apps/metrics/views/dashboard_views.py` - CTO dashboard view
- `templates/metrics/cto_dashboard.html` - Dashboard template

## Decisions Made

1. **Store insights in DB** - Enables history, dismissal, LLM access
2. **Categories**: trend, anomaly, comparison, action
3. **Priorities**: high, medium, low
4. **Daily computation** - Run after GitHub/Jira sync
5. **Show top 5** - Avoid overwhelming users

## Dependencies

- Phase 1 is standalone (no external APIs)
- Builds on existing `dashboard_service.py` functions
- Integrates with existing Celery beat schedule

## Patterns to Follow

### Model Pattern (from existing models)
```python
class DailyInsight(BaseTeamModel):
    # Use BaseTeamModel for team isolation
    # Add db_index on frequently queried fields
    # Use choices for constrained fields
```

### Service Pattern
```python
# From dashboard_service.py
def get_insights(team: Team, date: date) -> list[dict]:
    """Return computed insights for a team."""
    pass
```

### Celery Task Pattern
```python
# From tasks.py
@shared_task
def compute_daily_insights(team_id: int) -> dict:
    """Compute insights for a team."""
    pass
```
