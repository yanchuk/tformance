# MVP Gaps Fix Implementation Plan

**Last Updated: 2025-12-18**
**Status: PLANNING**

## Executive Summary

This plan addresses two integration gaps discovered during MVP verification:

1. **WeeklyMetrics Aggregation** - The WeeklyMetrics model exists but is never populated by automated tasks
2. **Jira-PR Bidirectional Linking** - PRs have jira_key but JiraIssue model has no reverse reference to PRs

These gaps don't block MVP launch but affect data completeness for dashboards and historical tracking.

---

## Current State Analysis

### Gap 1: WeeklyMetrics Not Populated

**Model Exists** (`apps/metrics/models.py:755-884`):
- `WeeklyMetrics` has fields for all aggregated data
- `member` (FK to TeamMember), `week_start` (DateField)
- Delivery: `prs_merged`, `avg_cycle_time_hours`, `avg_review_time_hours`, `commits_count`, `lines_added`, `lines_removed`
- Quality: `revert_count`, `hotfix_count`
- Jira: `story_points_completed`, `issues_resolved`
- AI: `ai_assisted_prs`, `avg_quality_rating`, `surveys_completed`, `guess_accuracy`

**No Aggregation Task**:
- No task in `apps/integrations/tasks.py` populates this model
- Only populated by `seed_demo_data` management command
- Dashboard queries this table but gets empty results in production

**Scheduled Tasks Exist For**:
- `sync-github-repositories-daily` (4:00 AM UTC)
- `sync-github-members-daily` (4:15 AM UTC)
- `sync-jira-projects-daily` (4:30 AM UTC)
- `check-leaderboards-hourly` (every hour)

### Gap 2: Jira-PR One-Way Linking

**PullRequest Model** (`apps/metrics/models.py:205`):
```python
jira_key = models.CharField(max_length=50, blank=True, db_index=True)
```
- Extracted from PR title/branch via `extract_jira_key()`
- Used by `get_unlinked_prs()` dashboard function

**JiraIssue Model** (`apps/metrics/models.py:406`):
```python
jira_key = models.CharField(max_length=50)  # e.g., PROJ-123
jira_id = models.CharField(max_length=50)   # Jira internal ID
```
- Synced from Jira API
- No reference to related PRs
- No method to find PRs that implement this issue

---

## Proposed Future State

### Gap 1 Fix: Weekly Metrics Aggregation Task

Create a Celery task that runs weekly to aggregate metrics per member:

```python
@shared_task
def aggregate_weekly_metrics_task():
    """Aggregate metrics for the previous week for all teams."""
```

**Scheduled**: Sunday 11:59 PM UTC (after all daily syncs)

### Gap 2 Fix: Jira-PR Linking Enhancement

Option A (Recommended): Add `related_prs` property to JiraIssue
Option B: Add `jira_issue` FK to PullRequest (requires migration)

We recommend Option A as it's non-breaking and uses existing `jira_key` field.

---

## Implementation Phases

### Phase 1: WeeklyMetrics Aggregation (Priority: High)

**Effort**: Medium (4-6 hours)

Creates automated weekly aggregation to populate the existing WeeklyMetrics model.

#### Files to Create/Modify:
| File | Action | Purpose |
|------|--------|---------|
| `apps/metrics/services/aggregation_service.py` | CREATE | Aggregation logic |
| `apps/integrations/tasks.py` | MODIFY | Add Celery task |
| `tformance/settings.py` | MODIFY | Add scheduled task |
| `apps/metrics/tests/test_aggregation_service.py` | CREATE | Unit tests |

#### Data Sources for Aggregation:
- **prs_merged**: `PullRequest.objects.filter(merged_at__range=week_range, author=member)`
- **avg_cycle_time_hours**: Average of `cycle_time_hours` for merged PRs
- **avg_review_time_hours**: Average of `review_time_hours` for merged PRs
- **commits_count**: `Commit.objects.filter(committed_at__range=week_range, author=member).count()`
- **lines_added/removed**: Sum from PR data
- **revert_count**: PRs where `is_revert=True`
- **hotfix_count**: PRs where `is_hotfix=True`
- **story_points_completed**: From JiraIssue completed by member
- **ai_assisted_prs**: From PRSurvey responses
- **avg_quality_rating**: From PRSurveyReview responses
- **guess_accuracy**: From PRSurveyReview.guess_correct

### Phase 2: Jira-PR Linking Property (Priority: Low)

**Effort**: Small (2-3 hours)

Adds a reverse lookup from JiraIssue to related PRs.

#### Files to Modify:
| File | Action | Purpose |
|------|--------|---------|
| `apps/metrics/models.py` | MODIFY | Add `related_prs` property |
| `apps/metrics/services/dashboard_service.py` | MODIFY | Use new property |
| `apps/metrics/tests/test_models.py` | MODIFY | Add tests |

#### Implementation:
```python
# In JiraIssue model
@property
def related_prs(self):
    """Get all PRs that reference this Jira issue."""
    return PullRequest.objects.for_team(self.team).filter(jira_key=self.jira_key)
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Aggregation task takes too long | Medium | Batch by team, use iterator() |
| Historical data missing | Low | Add backfill management command |
| Jira key format mismatch | Low | Use existing extract_jira_key() |

---

## Success Metrics

1. **WeeklyMetrics populated**: Records exist for past 4 weeks after task runs
2. **Dashboard shows trends**: Historical charts display real data
3. **Jira-PR linking works**: `issue.related_prs` returns correct PRs
4. **No performance regression**: Task completes within 10 minutes

---

## Test Commands

```bash
# Run aggregation tests
make test ARGS='apps.metrics.tests.test_aggregation_service --keepdb'

# Run Jira-PR linking tests
make test ARGS='apps.metrics.tests.test_models::TestJiraIssuePRLinking --keepdb'

# Full test suite
make test ARGS='--keepdb'
```
