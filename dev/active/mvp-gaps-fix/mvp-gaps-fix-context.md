# MVP Gaps Fix - Context Document

**Last Updated: 2025-12-18**
**Status: COMPLETE**

## Implementation Summary

Both MVP gaps have been fixed using TDD:

1. **WeeklyMetrics Aggregation** - Automated weekly aggregation of metrics per team member
2. **Jira-PR Linking** - Bidirectional linking via `related_prs` property

## Files Created

| File | Purpose |
|------|---------|
| `apps/metrics/services/aggregation_service.py` | Aggregation logic with 3 functions |
| `apps/metrics/tests/test_aggregation_service.py` | 12 unit tests for aggregation |

## Files Modified

| File | Changes |
|------|---------|
| `apps/integrations/tasks.py` | Added 2 Celery tasks for aggregation |
| `apps/integrations/tests/test_tasks.py` | Added 4 tests for new tasks |
| `apps/metrics/models.py` | Added `related_prs` property to JiraIssue |
| `apps/metrics/tests/test_models.py` | Added 4 tests for Jira-PR linking |
| `tformance/settings.py` | Added scheduled task for Monday 1 AM UTC |

## Key Implementation Details

### Aggregation Service Functions

```python
# apps/metrics/services/aggregation_service.py

def get_week_boundaries(date):
    """Returns (week_start, week_end) tuple for Monday-Sunday."""

def compute_member_weekly_metrics(team, member, week_start, week_end):
    """Computes all WeeklyMetrics fields for a single member."""
    # Returns dict with: prs_merged, avg_cycle_time_hours, commits_count,
    # ai_assisted_prs, avg_quality_rating, guess_accuracy, etc.

def aggregate_team_weekly_metrics(team, week_start):
    """Creates/updates WeeklyMetrics for all active team members."""
```

### Celery Tasks

```python
# apps/integrations/tasks.py

@shared_task
def aggregate_team_weekly_metrics_task(team_id):
    """Aggregate metrics for a single team (previous week)."""

@shared_task
def aggregate_all_teams_weekly_metrics_task():
    """Dispatch aggregation for all teams with GitHub integration."""
```

### Scheduled Task

```python
# tformance/settings.py SCHEDULED_TASKS
"aggregate-weekly-metrics-monday": {
    "task": "apps.integrations.tasks.aggregate_all_teams_weekly_metrics_task",
    "schedule": schedules.crontab(minute=0, hour=1, day_of_week=1),  # Monday 1 AM UTC
    "expire_seconds": 60 * 60 * 2,
},
```

### Jira-PR Linking Property

```python
# apps/metrics/models.py JiraIssue class

@property
def related_prs(self):
    """Get all PRs that reference this Jira issue via jira_key."""
    return PullRequest.objects.filter(team=self.team, jira_key=self.jira_key)
```

## Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Aggregation service | 12 | ✅ Pass |
| Celery tasks | 4 | ✅ Pass |
| Jira-PR linking | 4 | ✅ Pass |
| **Total new tests** | **20** | ✅ All pass |

## Data Flow

### Weekly Aggregation
```
Monday 1:00 AM UTC
    │
    ▼
aggregate_all_teams_weekly_metrics_task()
    │
    ├── Find teams with GitHub integration
    │
    ├── For each team:
    │   └── aggregate_team_weekly_metrics_task(team_id)
    │       │
    │       ├── compute_member_weekly_metrics() for each active member
    │       │
    │       └── WeeklyMetrics.objects.update_or_create()
    │
    └── Done
```

### Jira-PR Linking
```
jira_issue.related_prs
    │
    ▼
PullRequest.objects.filter(team=self.team, jira_key=self.jira_key)
    │
    ▼
QuerySet of related PRs
```

## Verification Commands

```bash
# Run all MVP gaps tests
make test ARGS='apps.metrics.tests.test_aggregation_service --keepdb'
make test ARGS='apps.metrics.tests.test_models.TestJiraIssuePRLinking --keepdb'

# Run full test suite
make test ARGS='--keepdb'

# Manually trigger aggregation
python manage.py shell
>>> from apps.integrations.tasks import aggregate_all_teams_weekly_metrics_task
>>> aggregate_all_teams_weekly_metrics_task()
```
