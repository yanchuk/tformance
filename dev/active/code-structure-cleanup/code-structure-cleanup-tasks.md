# Code Structure Cleanup - Task Checklist

**Last Updated:** 2024-12-30

## Phase 1: Quick Wins (30 min)

### Task 1.1: Consolidate Avatar/Initials Helpers [S]
- [ ] Review helper usage - confirm they're needed for `.values()` aggregations
- [ ] Keep helpers but add docstring noting relationship to TeamMember properties
- [ ] Consider renaming to `_avatar_url_for_github_id()` (clearer intent)
- [ ] Add comment: "Use TeamMember.avatar_url property when working with model instances"
- [ ] Run tests: `make test ARGS='apps.metrics.tests.dashboard'`

### Task 1.2: Create metrics/constants.py [S]
- [ ] Create `apps/metrics/constants.py`
- [ ] Move PR_SIZE_* constants from dashboard_service.py
- [ ] Add docstrings explaining size categories
- [ ] Update dashboard_service.py imports
- [ ] Search for other files using similar magic numbers
- [ ] Run tests: `make test ARGS='apps.metrics'`

### Task 1.3: Address TODOs [S]
- [ ] Review `apps/auth/views.py:526` - Jira multi-site TODO
  - [ ] Create GitHub issue for multi-site Jira support
  - [ ] Update TODO comment with issue reference
- [ ] Review `apps/metrics/services/survey_service.py:156` - Slack reveal TODO
  - [ ] Determine if feature is still planned
  - [ ] Create issue or mark as won't-do
  - [ ] Update TODO comment with decision
- [ ] Verify no other orphaned TODOs in critical paths

---

## Phase 2: Dashboard Service Split (2 hours)

### Task 2.1: Create Directory Structure [S]
- [ ] Create `apps/metrics/services/dashboard/` directory
- [ ] Create empty `__init__.py`
- [ ] Create empty `_helpers.py`

### Task 2.2: Extract Helper Functions [M]
- [ ] Move to `_helpers.py`:
  - [ ] `_get_merged_prs_in_range()`
  - [ ] `_calculate_ai_percentage()`
  - [ ] `_get_github_url()`
  - [ ] `_get_author_name()`
  - [ ] `_compute_initials()`
  - [ ] `_avatar_url_from_github_id()`
  - [ ] `_calculate_change_and_trend()`
  - [ ] `_get_key_metrics_cache_key()`
- [ ] Add necessary imports
- [ ] Verify no circular imports

### Task 2.3: Extract Key Metrics [M]
- [ ] Create `key_metrics.py`
- [ ] Move `get_key_metrics()`
- [ ] Move `get_metrics_trend()`
- [ ] Update imports from `_helpers`
- [ ] Add to `__init__.py` exports
- [ ] Run related tests

### Task 2.4: Extract AI Metrics [M]
- [ ] Create `ai_metrics.py`
- [ ] Move `get_ai_adoption_trends()`
- [ ] Move `get_ai_detective_leaderboard()`
- [ ] Move tool trends functions
- [ ] Update imports
- [ ] Add to `__init__.py` exports
- [ ] Run related tests

### Task 2.5: Extract Team Metrics [M]
- [ ] Create `team_metrics.py`
- [ ] Move `get_team_breakdown()`
- [ ] Move `get_copilot_by_member()`
- [ ] Update imports
- [ ] Add to `__init__.py` exports
- [ ] Run related tests

### Task 2.6: Extract Review Metrics [M]
- [ ] Create `review_metrics.py`
- [ ] Move `get_review_distribution()`
- [ ] Move `get_quality_comparison()`
- [ ] Move `get_average_review_time()`
- [ ] Update imports
- [ ] Add to `__init__.py` exports
- [ ] Run related tests

### Task 2.7: Extract PR Metrics [M]
- [ ] Create `pr_metrics.py`
- [ ] Move `get_recent_prs()`
- [ ] Move `get_pr_cycle_time()`
- [ ] Move `get_pr_size_distribution()`
- [ ] Move `get_pr_type_trends()`
- [ ] Update imports
- [ ] Add to `__init__.py` exports
- [ ] Run related tests

### Task 2.8: Extract Deployment Metrics [M]
- [ ] Create `deployment_metrics.py`
- [ ] Move `get_deployment_metrics()`
- [ ] Move `get_ci_cd_metrics()`
- [ ] Move `get_revert_hotfix_stats()`
- [ ] Update imports
- [ ] Add to `__init__.py` exports
- [ ] Run related tests

### Task 2.9: Finalize Dashboard Split [S]
- [ ] Complete `__init__.py` with all exports
- [ ] Update original `dashboard_service.py` to import from new module
- [ ] Or: Delete original and ensure all imports work
- [ ] Run full dashboard tests: `make test ARGS='apps.metrics.tests.dashboard'`
- [ ] Run full metrics tests: `make test ARGS='apps.metrics'`

---

## Phase 3: Tasks File Split (2 hours)

### Task 3.1: Create Tasks Directory Structure [S]
- [ ] Create `apps/integrations/tasks/` directory
- [ ] Create empty `__init__.py`

### Task 3.2: Extract GitHub Sync Tasks [L]
- [ ] Create `github_sync.py`
- [ ] Move tasks:
  - [ ] `sync_repository_task`
  - [ ] `create_repository_webhook_task`
  - [ ] `sync_repository_initial_task`
  - [ ] `sync_repository_manual_task`
  - [ ] `sync_all_repositories_task`
  - [ ] `sync_github_members_task`
  - [ ] `sync_all_github_members_task`
  - [ ] `sync_quick_data_task`
  - [ ] `sync_full_history_task`
  - [ ] `sync_historical_data_task`
- [ ] Move helper function `_sync_incremental_with_graphql_or_rest`
- [ ] Update imports
- [ ] Add to `__init__.py` exports

### Task 3.3: Extract Jira Sync Tasks [M]
- [ ] Create `jira_sync.py`
- [ ] Move tasks:
  - [ ] `sync_jira_project_task`
  - [ ] `sync_all_jira_projects_task`
  - [ ] `sync_jira_users_task`
- [ ] Update imports
- [ ] Add to `__init__.py` exports

### Task 3.4: Extract Slack Tasks [M]
- [ ] Create `slack.py`
- [ ] Move tasks:
  - [ ] `send_pr_surveys_task`
  - [ ] `send_reveal_task`
  - [ ] `sync_slack_users_task`
  - [ ] `post_weekly_leaderboards_task`
  - [ ] `schedule_slack_survey_fallback_task`
- [ ] Update imports
- [ ] Add to `__init__.py` exports

### Task 3.5: Extract Copilot Tasks [S]
- [ ] Create `copilot.py`
- [ ] Move `sync_copilot_metrics_task`
- [ ] Update imports
- [ ] Add to `__init__.py` exports

### Task 3.6: Extract Metrics/Aggregation Tasks [M]
- [ ] Create `metrics.py`
- [ ] Move tasks:
  - [ ] `aggregate_team_weekly_metrics_task`
  - [ ] `aggregate_all_teams_weekly_metrics_task`
  - [ ] `queue_llm_analysis_batch_task`
- [ ] Update imports
- [ ] Add to `__init__.py` exports

### Task 3.7: Extract PR Data Tasks [M]
- [ ] Create `pr_data.py`
- [ ] Move tasks:
  - [ ] `fetch_pr_complete_data_task`
  - [ ] `refresh_repo_languages_task`
  - [ ] `refresh_all_repo_languages_task`
  - [ ] `post_survey_comment_task`
  - [ ] `update_pr_description_survey_task`
- [ ] Update imports
- [ ] Add to `__init__.py` exports

### Task 3.8: Finalize Tasks Split [M]
- [ ] Complete `__init__.py` with all task exports
- [ ] Update Celery beat schedule imports if needed
- [ ] Update any direct task imports in views/services
- [ ] Keep or delete original `tasks.py` (prefer delete with re-export)
- [ ] Run integration tests: `make test ARGS='apps.integrations'`
- [ ] Test Celery beat schedules manually

---

## Verification Checklist

### After Phase 1
- [ ] `make test` passes
- [ ] No new linting errors: `make ruff-lint`
- [ ] Constants properly imported

### After Phase 2
- [ ] `make test ARGS='apps.metrics'` passes
- [ ] Dashboard views still work: manual test
- [ ] `from apps.metrics.services.dashboard_service import get_key_metrics` works
- [ ] No circular import errors

### After Phase 3
- [ ] `make test ARGS='apps.integrations'` passes
- [ ] Celery tasks discoverable: `celery -A tformance inspect registered`
- [ ] Celery beat schedules work: check django-celery-beat admin
- [ ] `from apps.integrations.tasks import sync_repository_task` works

### Final Verification
- [ ] Full test suite passes: `make test`
- [ ] Dev server runs without errors: `make dev`
- [ ] E2E smoke tests pass: `make e2e-smoke`

---

## Notes

- **Effort estimates:** S=Small (<30min), M=Medium (30-60min), L=Large (1-2hr)
- **Run tests incrementally** after each task, not just at end
- **Backward compatibility** is critical - existing imports must work
- **Celery autodiscover** requires tasks in `__init__.py` or registered explicitly
