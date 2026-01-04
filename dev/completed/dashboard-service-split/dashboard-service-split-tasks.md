# Dashboard Service Split - Task Checklist

**Last Updated:** 2026-01-04 (Session 4)

## Overview

Split `apps/metrics/services/dashboard_service.py` (originally 3,712 lines, 69 functions) into domain-focused modules using TDD.

---

## Phase 1: Setup & Helpers (TDD) ✅ COMPLETE

### Setup
- [x] Create `apps/metrics/services/dashboard/` directory
- [x] Create `apps/metrics/services/dashboard/__init__.py` with initial re-exports
- [x] Verify existing tests pass before starting (425 tests)

### Extract _helpers.py
- [x] **RED:** Verify existing tests for helper usage
- [x] **GREEN:** Create `dashboard/_helpers.py` with 15 private helpers
- [x] **REFACTOR:** Clean up imports
- [x] Add to `__init__.py` (if needed for internal use)
- [x] Verify tests pass (425 passed)

**Functions moved:**
- [x] `_apply_repo_filter`
- [x] `_get_merged_prs_in_range`
- [x] `_calculate_ai_percentage`
- [x] `_calculate_ai_percentage_from_detection`
- [x] `_get_github_url`
- [x] `_get_author_name`
- [x] `_compute_initials`
- [x] `_avatar_url_from_github_id`
- [x] `_get_key_metrics_cache_key`
- [x] `_get_metric_trend`
- [x] `_filter_by_date_range`
- [x] `_calculate_channel_percentages`
- [x] `_calculate_average_response_times`
- [x] `_get_monthly_metric_trend`
- [x] `_is_valid_category`

---

## Phase 2: Core Metrics (TDD) ✅ COMPLETE

### Extract key_metrics.py ✅
- [x] **RED:** Verify `test_key_metrics.py` passes
- [x] **GREEN:** Create `dashboard/key_metrics.py`
- [x] **REFACTOR:** Clean imports
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_key_metrics`

### Extract ai_metrics.py ✅
- [x] **RED:** Verify AI-related tests pass
- [x] **GREEN:** Create `dashboard/ai_metrics.py`
- [x] **REFACTOR:** Clean imports
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_ai_adoption_trend`
- [x] `get_ai_quality_comparison`
- [x] `get_ai_detective_leaderboard`
- [x] `get_ai_detected_metrics`
- [x] `get_ai_tool_breakdown`
- [x] `get_ai_category_breakdown`
- [x] `get_ai_bot_review_stats`
- [x] `get_ai_detection_metrics`
- [x] `get_ai_impact_stats`

### Extract team_metrics.py ✅
- [x] **RED:** Verify team-related tests pass
- [x] **GREEN:** Create `dashboard/team_metrics.py`
- [x] **REFACTOR:** Clean imports
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_team_breakdown`
- [x] `get_copilot_by_member`
- [x] `get_team_velocity`

---

## Phase 3: Trend & Review Metrics (TDD) ✅ COMPLETE

### Extract trend_metrics.py ✅
- [x] **RED:** Verify trend tests pass
- [x] **GREEN:** Create `dashboard/trend_metrics.py`
- [x] **REFACTOR:** Clean imports
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_cycle_time_trend`
- [x] `get_review_time_trend`
- [x] `get_monthly_cycle_time_trend`
- [x] `get_monthly_review_time_trend`
- [x] `get_monthly_pr_count`
- [x] `get_weekly_pr_count`
- [x] `get_monthly_ai_adoption`
- [x] `get_trend_comparison`
- [x] `get_sparkline_data`
- [x] `get_velocity_trend`

**Constants moved:**
- [x] `MIN_SPARKLINE_SAMPLE_SIZE = 3`
- [x] `MAX_TREND_PERCENTAGE = 500`

### Extract review_metrics.py ✅
- [x] **RED:** Verify review-related tests pass
- [x] **GREEN:** Create `dashboard/review_metrics.py`
- [x] **REFACTOR:** Clean imports
- [x] Add to `__init__.py` exports
- [x] Verify tests pass (425 passed)

**Functions:**
- [x] `get_review_distribution`
- [x] `get_reviewer_workload`
- [x] `get_reviewer_correlations`
- [x] `get_response_channel_distribution`
- [x] `get_response_time_metrics`
- [x] `detect_review_bottleneck`

---

## Phase 4: Remaining PR & Specialized Metrics (TDD) ✅ COMPLETE

### Extract pr_metrics.py ✅
- [x] **RED:** Verify PR-related tests pass
- [x] **GREEN:** Create `dashboard/pr_metrics.py`
- [x] **REFACTOR:** Clean imports
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_recent_prs`
- [x] `get_revert_hotfix_stats`
- [x] `get_pr_size_distribution`
- [x] `get_unlinked_prs`
- [x] `get_iteration_metrics`
- [x] `get_pr_type_breakdown`
- [x] `get_monthly_pr_type_trend`
- [x] `get_weekly_pr_type_trend`
- [x] `get_needs_attention_prs`
- [x] `get_open_prs_stats`

**Constants:**
- [x] `PR_SIZE_XS_MAX = 10`
- [x] `PR_SIZE_S_MAX = 50`
- [x] `PR_SIZE_M_MAX = 200`
- [x] `PR_SIZE_L_MAX = 500`

### Extract copilot_metrics.py ✅
- [x] **RED:** Verify copilot tests pass
- [x] **GREEN:** Create `dashboard/copilot_metrics.py`
- [x] **REFACTOR:** Clean imports
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_copilot_metrics`
- [x] `get_copilot_trend`

### Extract cicd_metrics.py ✅
- [x] **RED:** Verify CI/CD tests pass
- [x] **GREEN:** Create `dashboard/cicd_metrics.py`
- [x] **REFACTOR:** Clean imports
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_cicd_pass_rate`
- [x] `get_deployment_metrics`

### Extract tech_metrics.py ✅
- [x] **RED:** Verify tech/category tests pass
- [x] **GREEN:** Create `dashboard/tech_metrics.py`
- [x] **REFACTOR:** Clean imports
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_file_category_breakdown`
- [x] `get_tech_breakdown`
- [x] `get_monthly_tech_trend`
- [x] `get_weekly_tech_trend`

### Extract velocity_metrics.py ✅
- [x] **GREEN:** Create `dashboard/velocity_metrics.py`
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_velocity_comparison`
- [x] `get_quality_metrics`
- [x] `get_team_health_metrics`

### Extract jira_metrics.py ✅
- [x] **GREEN:** Create `dashboard/jira_metrics.py`
- [x] Add to `__init__.py` exports
- [x] Verify tests pass

**Functions:**
- [x] `get_jira_sprint_metrics`
- [x] `get_pr_jira_correlation`
- [x] `get_linkage_trend`
- [x] `get_story_point_correlation`

---

## Phase 5: Finalization ✅ COMPLETE

### Update Re-exports ✅
- [x] Update `dashboard/__init__.py` with all public functions
- [x] Keep `dashboard_service.py` as re-exports only (for backward compat)
- [x] Verify original import paths still work

### Final Verification ✅
- [x] Run full test suite: `make test ARGS='apps.metrics.tests.dashboard'`
- [x] Verify no file exceeds 600 lines
- [x] Check all imports work: both `dashboard` and `dashboard_service`
- [x] Run `make ruff` for code quality

### Documentation ✅
- [x] Update this task file with completion status

---

## Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| All tests pass | ✓ | ✓ (425 passed) |
| `dashboard_service.py` lines | <150 | 92 ✅ |
| Largest module | <600 lines | 587 (`pr_metrics.py`) ✅ |
| Backward compat | 100% | ✓ |
| Modules created | 11 | 12 ✅ |

### Module Line Counts (Final)
| Module | Lines |
|--------|-------|
| `dashboard_service.py` (re-exports only) | 92 |
| `__init__.py` | 208 |
| `_helpers.py` | 333 |
| `key_metrics.py` | 97 |
| `copilot_metrics.py` | 123 |
| `cicd_metrics.py` | 147 |
| `velocity_metrics.py` | 240 |
| `team_metrics.py` | 265 |
| `tech_metrics.py` | 279 |
| `jira_metrics.py` | 282 |
| `review_metrics.py` | 447 |
| `ai_metrics.py` | 509 |
| `trend_metrics.py` | 537 |
| `pr_metrics.py` | 587 |
| **Total** | **4,146** |

---

## Notes

- Run tests after EACH function move, not just per module
- If a test fails, check import paths first
- Constants `MIN_SPARKLINE_SAMPLE_SIZE` and `MAX_TREND_PERCENTAGE` moved to `trend_metrics.py`
- PR size constants moved to `pr_metrics.py`
- All helper functions must be re-exported from `dashboard_service.py` for backward compatibility
- Split originally 3,712 lines into 12 domain-focused modules + re-export file
