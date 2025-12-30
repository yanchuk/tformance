# Code Structure Cleanup - Implementation Plan

**Last Updated:** 2024-12-30

## Executive Summary

This plan addresses 5 low-hanging fruit code structure improvements identified during codebase analysis. Total estimated effort: 4-6 hours. All changes are refactoring-only with no functional changes.

## Current State Analysis

| Issue | File | Lines | Severity |
|-------|------|-------|----------|
| Avatar/Initials duplication | `dashboard_service.py` | 99-130 | HIGH - DRY violation |
| PR size magic numbers | `dashboard_service.py` | 30-35 | LOW - maintainability |
| Orphaned TODOs | `auth/views.py`, `survey_service.py` | 526, 156 | LOW - visibility |
| Monolithic service | `dashboard_service.py` | 2,307 | MEDIUM - maintainability |
| Monolithic tasks | `integrations/tasks.py` | 2,197 | MEDIUM - maintainability |

## Implementation Phases

### Phase 1: Quick Wins (30 min)

#### 1.1 Remove Avatar/Initials Duplication
**Problem:** `dashboard_service.py` defines `_compute_initials()` and `_avatar_url_from_github_id()` which duplicate `TeamMember.initials` and `TeamMember.avatar_url` properties.

**Solution:**
- Delete the duplicate helper functions
- Update 4 call sites to use TeamMember model properties
- Requires adding `select_related('author')` or using annotation values appropriately

**Call sites to update:**
- Line 409-410: `get_team_breakdown()` - uses aggregated values, keep helper but rename
- Line 465-466: `get_ai_detective_leaderboard()` - uses annotation values
- Line 502-503: `get_review_distribution()` - uses annotation values
- Line 999-1000: `get_copilot_by_member()` - uses annotation values

**Acceptance Criteria:**
- [ ] Helper functions removed or consolidated
- [ ] All 4 call sites work correctly
- [ ] Tests pass
- [ ] No duplicate logic between service and model

#### 1.2 Centralize PR Size Constants
**Problem:** Magic numbers for PR size thresholds defined inline.

**Solution:**
- Create `apps/metrics/constants.py`
- Move PR_SIZE_* constants there
- Import in dashboard_service.py and any other files using these values

**Acceptance Criteria:**
- [ ] `apps/metrics/constants.py` created
- [ ] Constants imported where needed
- [ ] Tests pass

#### 1.3 Address Orphaned TODOs
**Problem:** Two TODOs without tracking:
1. `apps/auth/views.py:526` - "Add site selection if multiple sites" (Jira OAuth)
2. `apps/metrics/services/survey_service.py:156` - "Actually send the reveal message via Slack"

**Solution:**
- Evaluate if features are still needed
- Either implement (if trivial) or create GitHub issues with proper tracking
- Add issue reference to TODO comment

**Acceptance Criteria:**
- [ ] TODOs either resolved or tracked in GitHub issues
- [ ] Comments updated with issue references

---

### Phase 2: Dashboard Service Split (2 hours)

**Problem:** `dashboard_service.py` is 2,307 lines with 29+ public functions covering multiple domains.

**Solution:** Split into domain-specific modules:

```
apps/metrics/services/dashboard/
├── __init__.py          # Re-exports all public functions
├── _helpers.py          # Private helper functions (_get_merged_prs_in_range, etc.)
├── key_metrics.py       # get_key_metrics, get_metrics_trend
├── ai_metrics.py        # get_ai_adoption_trends, get_ai_detective_leaderboard
├── team_metrics.py      # get_team_breakdown, get_copilot_by_member
├── review_metrics.py    # get_review_distribution, get_quality_comparison
├── pr_metrics.py        # get_recent_prs, get_pr_cycle_time, get_pr_size_distribution
└── deployment_metrics.py # get_deployment_metrics, get_ci_cd_metrics
```

**Function Distribution:**

| Module | Functions |
|--------|-----------|
| `_helpers.py` | `_get_merged_prs_in_range`, `_calculate_ai_percentage`, `_get_github_url`, `_get_author_name`, `_calculate_change_and_trend` |
| `key_metrics.py` | `get_key_metrics`, `get_key_metrics_cache_key` |
| `ai_metrics.py` | `get_ai_adoption_trends`, `get_ai_detective_leaderboard`, `get_tool_trends_*` |
| `team_metrics.py` | `get_team_breakdown`, `get_copilot_by_member` |
| `review_metrics.py` | `get_review_distribution`, `get_quality_comparison`, `get_average_review_time` |
| `pr_metrics.py` | `get_recent_prs`, `get_pr_cycle_time`, `get_pr_size_distribution`, `get_pr_type_trends` |
| `deployment_metrics.py` | `get_deployment_metrics`, `get_ci_cd_metrics`, `get_revert_hotfix_stats` |

**Acceptance Criteria:**
- [ ] Directory structure created
- [ ] Functions moved to appropriate modules
- [ ] `__init__.py` re-exports all public functions
- [ ] All imports work (backward compatibility)
- [ ] All tests pass
- [ ] No circular imports

---

### Phase 3: Tasks File Split (2 hours)

**Problem:** `integrations/tasks.py` is 2,197 lines with 35+ Celery tasks mixing multiple domains.

**Solution:** Split into domain-specific task files:

```
apps/integrations/tasks/
├── __init__.py           # Re-exports all tasks
├── github_sync.py        # Repository sync, webhooks, member sync
├── jira_sync.py          # Project sync, user sync
├── slack.py              # Surveys, reveals, leaderboards, user sync
├── copilot.py            # Copilot metrics sync
├── metrics.py            # Weekly aggregation, LLM batch
└── pr_data.py            # PR complete data fetch, languages
```

**Task Distribution:**

| Module | Tasks |
|--------|-------|
| `github_sync.py` | `sync_repository_task`, `create_repository_webhook_task`, `sync_repository_initial_task`, `sync_repository_manual_task`, `sync_all_repositories_task`, `sync_github_members_task`, `sync_all_github_members_task`, `sync_quick_data_task`, `sync_full_history_task`, `sync_historical_data_task` |
| `jira_sync.py` | `sync_jira_project_task`, `sync_all_jira_projects_task`, `sync_jira_users_task` |
| `slack.py` | `send_pr_surveys_task`, `send_reveal_task`, `sync_slack_users_task`, `post_weekly_leaderboards_task`, `schedule_slack_survey_fallback_task` |
| `copilot.py` | `sync_copilot_metrics_task` |
| `metrics.py` | `aggregate_team_weekly_metrics_task`, `aggregate_all_teams_weekly_metrics_task`, `queue_llm_analysis_batch_task` |
| `pr_data.py` | `fetch_pr_complete_data_task`, `refresh_repo_languages_task`, `refresh_all_repo_languages_task`, `post_survey_comment_task`, `update_pr_description_survey_task` |

**Acceptance Criteria:**
- [ ] Directory structure created
- [ ] Tasks moved to appropriate modules
- [ ] `__init__.py` re-exports all tasks (Celery autodiscover needs this)
- [ ] All Celery beat schedules still work
- [ ] All task imports work
- [ ] All tests pass

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Import breakage | Use `__init__.py` re-exports for backward compatibility |
| Circular imports | Move helpers to `_helpers.py`, import carefully |
| Celery autodiscover | Ensure `__init__.py` imports all tasks |
| Test failures | Run full test suite after each phase |

## Success Metrics

- [ ] All 5 issues addressed
- [ ] No new test failures
- [ ] dashboard_service.py reduced to <100 lines (just imports)
- [ ] tasks.py reduced to <100 lines (just imports)
- [ ] No duplicate avatar/initials logic

## Dependencies

- None - all changes are internal refactoring
- No database migrations needed
- No API changes

## Testing Strategy

1. Run `make test` after each sub-task
2. Run `make test ARGS='apps.metrics'` for metrics-focused tests
3. Run `make test ARGS='apps.integrations'` for integration tests
4. Verify Celery tasks still schedule correctly in dev environment
