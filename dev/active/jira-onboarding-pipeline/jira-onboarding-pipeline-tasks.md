# Jira Onboarding Pipeline - Tasks

**Last Updated**: 2026-01-01
**Approach**: Strict TDD (Red-Green-Refactor)

---

## Phase 1: Core Pipeline

### 1.1 RED: Write failing tests for `sync_jira_users_onboarding`
- [ ] Create `apps/integrations/tests/test_jira_onboarding_pipeline.py`
- [ ] Write `TestSyncJiraUsersOnboarding` class
- [ ] Test: `test_sync_jira_users_onboarding_calls_sync_service`
- [ ] Test: `test_sync_jira_users_onboarding_returns_result_dict`
- [ ] Test: `test_sync_jira_users_onboarding_handles_missing_integration`
- [ ] Verify tests FAIL (import error expected)

### 1.2 GREEN: Implement `sync_jira_users_onboarding`
- [ ] Add `sync_jira_users_onboarding` task to `apps/integrations/onboarding_pipeline.py`
- [ ] Use `@shared_task(bind=True)` decorator
- [ ] Delegate to existing `sync_jira_users_task`
- [ ] Verify all tests PASS

### 1.3 RED: Write failing tests for `sync_jira_projects_onboarding`
- [ ] Add `TestSyncJiraProjectsOnboarding` class
- [ ] Test: `test_sync_jira_projects_onboarding_syncs_all_projects`
- [ ] Test: `test_sync_jira_projects_onboarding_returns_aggregate_results`
- [ ] Test: `test_sync_jira_projects_onboarding_continues_on_failure`
- [ ] Test: `test_sync_jira_projects_onboarding_handles_empty_list`
- [ ] Verify tests FAIL

### 1.4 GREEN: Implement `sync_jira_projects_onboarding`
- [ ] Add `sync_jira_projects_onboarding` task
- [ ] Loop through project_ids, sync each
- [ ] Aggregate results (synced, failed, issues_created)
- [ ] Continue on individual project failure
- [ ] Verify all tests PASS

### 1.5 RED: Write failing tests for `start_jira_onboarding_pipeline`
- [ ] Add `TestStartJiraOnboardingPipeline` class
- [ ] Test: `test_start_jira_onboarding_pipeline_creates_celery_chain`
- [ ] Test: `test_start_jira_onboarding_pipeline_syncs_users_first`
- [ ] Test: `test_start_jira_onboarding_pipeline_returns_async_result`
- [ ] Verify tests FAIL

### 1.6 GREEN: Implement `start_jira_onboarding_pipeline`
- [ ] Add `start_jira_onboarding_pipeline` function
- [ ] Use `chain(sync_jira_users_onboarding.si(), sync_jira_projects_onboarding.si())`
- [ ] Return `AsyncResult`
- [ ] Verify all tests PASS

### 1.7 REFACTOR
- [ ] Review code for duplication
- [ ] Add logging statements
- [ ] Improve error messages
- [ ] Ensure tests still pass

---

## Phase 2: View Integration

### 2.1 RED: Write failing tests for pipeline trigger
- [ ] Create `apps/onboarding/tests/test_jira_sync_trigger.py`
- [ ] Write `TestSelectJiraProjectsTriggersPipeline` class
- [ ] Test: `test_post_triggers_jira_pipeline`
- [ ] Test: `test_post_stores_task_id_in_session`
- [ ] Test: `test_post_without_projects_skips_pipeline`
- [ ] Verify tests FAIL

### 2.2 GREEN: Modify `select_jira_projects` view
- [ ] Add pipeline trigger after `TrackedJiraProject` creation
- [ ] Get all active project IDs for team
- [ ] Call `start_jira_onboarding_pipeline(team.id, project_ids)`
- [ ] Store `task.id` in session
- [ ] Verify all tests PASS

### 2.3 RED: Write failing tests for `jira_sync_status` endpoint
- [ ] Add `TestJiraSyncStatus` class
- [ ] Test: `test_jira_sync_status_returns_project_statuses`
- [ ] Test: `test_jira_sync_status_returns_issues_count`
- [ ] Test: `test_jira_sync_status_calculates_overall_status`
- [ ] Test: `test_jira_sync_status_requires_authentication`
- [ ] Verify tests FAIL

### 2.4 GREEN: Implement `jira_sync_status` view
- [ ] Add view function to `apps/onboarding/views.py`
- [ ] Query `TrackedJiraProject` for team
- [ ] Query `JiraIssue.count()` for team
- [ ] Calculate overall status from project statuses
- [ ] Return JsonResponse
- [ ] Verify all tests PASS

### 2.5 GREEN: Add URL pattern
- [ ] Add to `apps/onboarding/urls.py`:
  ```python
  path("jira/sync-status/", views.jira_sync_status, name="jira_sync_status"),
  ```
- [ ] Verify URL resolves correctly

### 2.6 REFACTOR
- [ ] Add `@login_and_team_required` decorator
- [ ] Improve logging
- [ ] Handle edge cases (no projects)
- [ ] Ensure tests still pass

---

## Phase 3: Jira Metrics

### 3.1 RED: Write failing tests for `get_jira_sprint_metrics`
- [ ] Create `apps/metrics/tests/services/test_jira_metrics.py`
- [ ] Write `TestJiraSprintMetrics` class
- [ ] Test: `test_get_jira_sprint_metrics_counts_resolved_issues`
- [ ] Test: `test_get_jira_sprint_metrics_sums_story_points`
- [ ] Test: `test_get_jira_sprint_metrics_calculates_avg_cycle_time`
- [ ] Test: `test_get_jira_sprint_metrics_filters_by_date_range`
- [ ] Test: `test_get_jira_sprint_metrics_handles_no_issues`
- [ ] Verify tests FAIL

### 3.2 GREEN: Implement `get_jira_sprint_metrics`
- [ ] Add function to `apps/metrics/services/dashboard_service.py`
- [ ] Query `JiraIssue.objects.filter(team=team, resolved_at__range=...)`
- [ ] Aggregate: count, sum story_points, avg cycle_time_hours
- [ ] Group by issue_type
- [ ] Verify all tests PASS

### 3.3 RED: Write failing tests for `get_pr_jira_correlation`
- [ ] Write `TestPRJiraCorrelation` class
- [ ] Test: `test_get_pr_jira_correlation_calculates_linkage_rate`
- [ ] Test: `test_get_pr_jira_correlation_compares_cycle_times`
- [ ] Test: `test_get_pr_jira_correlation_handles_no_prs`
- [ ] Test: `test_get_pr_jira_correlation_handles_all_linked`
- [ ] Test: `test_get_pr_jira_correlation_handles_all_unlinked`
- [ ] Verify tests FAIL

### 3.4 GREEN: Implement `get_pr_jira_correlation`
- [ ] Add function to `apps/metrics/services/dashboard_service.py`
- [ ] Use `_get_merged_prs_in_range()`
- [ ] Split into linked (jira_key != "") and unlinked
- [ ] Calculate linkage_rate as percentage
- [ ] Calculate avg cycle times for each group
- [ ] Verify all tests PASS

### 3.5 REFACTOR
- [ ] Optimize queries (use select_related if needed)
- [ ] Add docstrings
- [ ] Handle None values in averages
- [ ] Ensure tests still pass

---

## Phase 4: Insights Integration

### 4.1 RED: Write failing tests for Jira in `gather_insight_data`
- [ ] Add to `apps/metrics/tests/services/test_insight_llm.py`
- [ ] Write `TestGatherInsightDataWithJira` class
- [ ] Test: `test_gather_insight_data_includes_jira_when_connected`
- [ ] Test: `test_gather_insight_data_excludes_jira_when_not_connected`
- [ ] Test: `test_gather_insight_data_jira_has_sprint_metrics`
- [ ] Test: `test_gather_insight_data_jira_has_pr_correlation`
- [ ] Verify tests FAIL

### 4.2 GREEN: Modify `gather_insight_data`
- [ ] Check if `JiraIntegration.objects.filter(team=team).exists()`
- [ ] If exists, call `get_jira_sprint_metrics()` and `get_pr_jira_correlation()`
- [ ] Add `"jira": jira_data` to return dict (or `None` if not connected)
- [ ] Verify all tests PASS

### 4.3 GREEN: Update prompt template
- [ ] Edit `apps/metrics/prompts/templates/insight/user.jinja2`
- [ ] Add Jira section with `{% if jira %}` guard
- [ ] Include sprint metrics and PR correlation
- [ ] Handle None values with `|default(0)` filter

### 4.4 REFACTOR
- [ ] Test template rendering with sample data
- [ ] Ensure proper number formatting
- [ ] Handle edge cases (zero division, None values)
- [ ] Ensure tests still pass

---

## Phase 5: UI Polish

### 5.1 Add inline progress indicator
- [ ] Edit `templates/onboarding/select_jira_projects.html`
- [ ] Add Alpine.js component after form
- [ ] Poll `jira_sync_status` endpoint every 2 seconds
- [ ] Show spinner when syncing, checkmark when complete

### 5.2 Add session storage flag
- [ ] Set `sessionStorage.setItem('jira_sync_started', 'true')` after POST
- [ ] Use flag to show/hide progress indicator
- [ ] Clear flag when sync completes

### 5.3 Test polling behavior
- [ ] Verify polling starts after POST
- [ ] Verify polling stops on completion
- [ ] Verify status transitions display correctly

---

## Final Verification

- [ ] Run full test suite: `make test`
- [ ] Manual test: Complete onboarding with Jira
- [ ] Verify JiraIssue records created
- [ ] Verify TeamMember.jira_account_id populated
- [ ] Verify insights include Jira metrics
- [ ] Verify progress indicator works

---

## Summary Checklist

| Phase | Status | Tests | Implementation |
|-------|--------|-------|----------------|
| 1. Core Pipeline | [ ] | [ ] | [ ] |
| 2. View Integration | [ ] | [ ] | [ ] |
| 3. Jira Metrics | [ ] | [ ] | [ ] |
| 4. Insights Integration | [ ] | [ ] | [ ] |
| 5. UI Polish | [ ] | [ ] | [ ] |
| Final Verification | [ ] | - | - |
