# MVP Gaps Fix - Task Checklist

**Last Updated: 2025-12-18**
**Status: COMPLETE**

## Phase 1: WeeklyMetrics Aggregation (M - 4-6h) ✅ COMPLETE

### 1.1 Create Aggregation Service ✅
- [x] Create `apps/metrics/services/aggregation_service.py`
- [x] Implement `get_week_boundaries(date)` helper
- [x] Implement `_get_week_datetime_range()` helper (refactored)
- [x] Implement `compute_member_weekly_metrics(team, member, week_start, week_end)`
- [x] Implement `aggregate_team_weekly_metrics(team, week_start)`
- [x] Handle edge cases (no data, partial data)

### 1.2 Create Celery Task ✅
- [x] Add `aggregate_team_weekly_metrics_task(team_id)` to tasks.py
- [x] Add `aggregate_all_teams_weekly_metrics_task()` for all teams
- [x] Add error handling and logging
- [x] Add Sentry error capture

### 1.3 Add Scheduled Task ✅
- [x] Add to `SCHEDULED_TASKS` in `tformance/settings.py`
- [x] Schedule for Monday 1:00 AM UTC
- [x] Set 2 hour expire_seconds

### 1.4 Unit Tests (TDD) ✅
- [x] Create `apps/metrics/tests/test_aggregation_service.py`
- [x] Test `get_week_boundaries()` returns correct Monday-Sunday range (3 tests)
- [x] Test `compute_member_weekly_metrics()` with full data
- [x] Test `compute_member_weekly_metrics()` with no data (zeros)
- [x] Test `aggregate_team_weekly_metrics()` creates records
- [x] Test `aggregate_team_weekly_metrics()` updates existing records
- [x] Test task dispatches correctly (4 tests)

**Tests:** 12 service tests + 4 task tests = **16 tests passing**

---

## Phase 2: Jira-PR Linking Property (S - 2-3h) ✅ COMPLETE

### 2.1 Add Model Property ✅
- [x] Add `related_prs` property to `JiraIssue` model
- [x] Filter by `team=self.team` and `jira_key=self.jira_key`
- [x] Add docstring explaining the property

### 2.2 Add Property Tests ✅
- [x] Test `related_prs` returns correct PRs
- [x] Test `related_prs` returns empty QuerySet when no matches
- [x] Test `related_prs` respects team isolation
- [x] Test `related_prs` handles multiple PRs per issue

**Tests:** 4 tests passing

---

## Test Commands

```bash
# Phase 1 tests
make test ARGS='apps.metrics.tests.test_aggregation_service --keepdb'

# Phase 2 tests
make test ARGS='apps.metrics.tests.test_models.TestJiraIssuePRLinking --keepdb'

# Full test suite
make test ARGS='--keepdb'
```

---

## Definition of Done ✅ ALL COMPLETE

### Phase 1 Complete ✅
- [x] WeeklyMetrics model exists (already done)
- [x] Aggregation service implemented
- [x] Celery tasks created and scheduled
- [x] 16 unit tests passing

### Phase 2 Complete ✅
- [x] `related_prs` property added to JiraIssue
- [x] 4 unit tests passing

### All Done ✅
- [x] All unit tests passing (20 new tests)
- [x] No regressions in existing tests
- [x] Code passes ruff linting
- [x] Documentation updated
