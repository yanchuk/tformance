# Codebase Improvements: File Splitting Plan

**Last Updated:** 2025-12-21

## Executive Summary

Split large Python files to fix Claude Code read failures (>25k token limit) and improve codebase maintainability. This involves splitting 5 files totaling ~13,000 lines into modular, focused components while maintaining full backward compatibility through `__init__.py` re-exports.

**Impact:** High - Enables AI-assisted development and reduces merge conflicts
**Effort:** Medium - Mechanical refactoring with test verification
**Risk:** Low - Backward-compatible changes with comprehensive test coverage

---

## Current State Analysis

### Files Requiring Splitting

| File | Lines | Classes/Functions | Issue |
|------|-------|-------------------|-------|
| `apps/metrics/models.py` | 1,518 | 15 model classes | Exceeds token limit |
| `apps/integrations/views.py` | 1,321 | 25+ view functions | Exceeds token limit |
| `apps/integrations/tests/test_github_sync.py` | 4,391 | 14 test classes | Far exceeds limit |
| `apps/metrics/tests/test_dashboard_service.py` | 3,142 | 18 test classes | Exceeds limit |
| `apps/metrics/tests/test_models.py` | 2,847 | 17 test classes | Exceeds limit |

### Model Classes Distribution (metrics/models.py)

| Domain | Classes | Lines (approx) |
|--------|---------|----------------|
| Team | TeamMember | ~90 |
| GitHub | PullRequest, PRReview, PRCheckRun, PRFile, PRComment, Commit | ~600 |
| Jira | JiraIssue | ~125 |
| Surveys | PRSurvey, PRSurveyReview | ~160 |
| Aggregations | WeeklyMetrics, ReviewerCorrelation, AIUsageDaily | ~300 |
| Insights | DailyInsight | ~85 |
| Deployments | Deployment | ~90 |

### View Functions Distribution (integrations/views.py)

| Provider | Functions | Lines (approx) |
|----------|-----------|----------------|
| Helpers | 6 helper functions | ~150 |
| GitHub | 10 view functions | ~400 |
| Jira | 6 view functions | ~350 |
| Slack | 5 view functions | ~300 |
| Status/Copilot | 2 view functions | ~100 |

---

## Proposed Future State

### 1. Models Directory Structure

```
apps/metrics/models/
├── __init__.py          # Re-exports all models for backward compatibility
├── base.py              # Shared imports, constants, enums
├── team.py              # TeamMember
├── github.py            # PullRequest, PRReview, PRCheckRun, PRFile, PRComment, Commit
├── jira.py              # JiraIssue
├── surveys.py           # PRSurvey, PRSurveyReview
├── aggregations.py      # WeeklyMetrics, ReviewerCorrelation, AIUsageDaily
├── insights.py          # DailyInsight
└── deployments.py       # Deployment
```

**__init__.py Template:**
```python
# apps/metrics/models/__init__.py
"""
Metrics models - split into domain-specific modules.

All models are re-exported here for backward compatibility.
Import as: from apps.metrics.models import PullRequest
"""

from .team import TeamMember
from .github import PullRequest, PRReview, PRCheckRun, PRFile, PRComment, Commit
from .jira import JiraIssue
from .surveys import PRSurvey, PRSurveyReview
from .aggregations import WeeklyMetrics, ReviewerCorrelation, AIUsageDaily
from .insights import DailyInsight
from .deployments import Deployment

__all__ = [
    "TeamMember",
    "PullRequest", "PRReview", "PRCheckRun", "PRFile", "PRComment", "Commit",
    "JiraIssue",
    "PRSurvey", "PRSurveyReview",
    "WeeklyMetrics", "ReviewerCorrelation", "AIUsageDaily",
    "DailyInsight",
    "Deployment",
]
```

### 2. Views Directory Structure

```
apps/integrations/views/
├── __init__.py          # Re-exports for backward compatibility
├── helpers.py           # Shared helper functions
├── github.py            # GitHub OAuth, repos, members, webhooks
├── jira.py              # Jira OAuth, projects, sites
├── slack.py             # Slack OAuth, settings
└── status.py            # integrations_home, copilot_sync
```

### 3. Test Directory Structures

**GitHub Sync Tests:**
```
apps/integrations/tests/github_sync/
├── __init__.py
├── test_repository_sync.py      # TestSyncRepositoryHistory, TestSyncRepositoryIncremental
├── test_pr_sync.py              # TestGetRepositoryPullRequests, TestGetUpdatedPullRequests
├── test_review_sync.py          # TestGetPullRequestReviews
├── test_commit_sync.py          # TestSyncPRCommits
├── test_check_runs.py           # TestSyncPRCheckRuns
├── test_files.py                # TestSyncPRFiles
├── test_deployments.py          # TestSyncRepositoryDeployments
├── test_comments.py             # TestSyncPRIssueComments, TestSyncPRReviewComments
├── test_jira_key.py             # TestJiraKeyExtraction
├── test_iterations.py           # TestCalculatePRIterationMetrics
└── test_correlations.py         # TestCalculateReviewerCorrelations
```

**Dashboard Service Tests:**
```
apps/metrics/tests/dashboard/
├── __init__.py
├── test_key_metrics.py          # TestGetKeyMetrics
├── test_ai_metrics.py           # TestGetAIAdoptionTrend, TestGetAIQualityComparison
├── test_cycle_time.py           # TestGetCycleTimeTrend
├── test_team_breakdown.py       # TestGetTeamBreakdown
├── test_review_metrics.py       # TestGetReviewDistribution, TestGetReviewTimeTrend, TestGetReviewerWorkload
├── test_pr_metrics.py           # TestGetRecentPrs, TestGetPrSizeDistribution, TestGetUnlinkedPrs
├── test_revert_hotfix.py        # TestGetRevertHotfixStats
├── test_copilot.py              # TestCopilotDashboardService
├── test_iterations.py           # TestGetIterationMetrics, TestGetReviewerCorrelations
├── test_cicd.py                 # TestGetCicdPassRate
├── test_deployments.py          # TestGetDeploymentMetrics
└── test_file_categories.py      # TestGetFileCategoryBreakdown
```

**Model Tests:**
```
apps/metrics/tests/models/
├── __init__.py
├── test_team_member.py          # TestTeamMemberModel
├── test_pull_request.py         # TestPullRequestModel, TestPullRequestIterationFields, TestPullRequestFactory
├── test_pr_review.py            # TestPRReviewModel
├── test_commit.py               # TestCommitModel
├── test_jira.py                 # TestJiraIssueModel, TestJiraIssuePRLinking
├── test_ai_usage.py             # TestAIUsageDailyModel
├── test_surveys.py              # TestPRSurveyModel, TestPRSurveyReviewModel
├── test_weekly_metrics.py       # TestWeeklyMetricsModel
├── test_pr_check_run.py         # TestPRCheckRunModel
├── test_pr_file.py              # TestPRFileModel
├── test_deployment.py           # TestDeploymentModel
├── test_pr_comment.py           # TestPRCommentModel
└── test_reviewer_correlation.py # TestReviewerCorrelationModel
```

---

## Implementation Phases

### Phase 1: Split metrics/models.py (Priority: HIGH)

**Objective:** Split 1,518-line models.py into 8 domain-specific modules

**Steps:**
1. Create `apps/metrics/models/` directory
2. Create `base.py` with shared imports (django.db.models, BaseTeamModel)
3. Move each model class to its domain file
4. Create `__init__.py` with all re-exports
5. Rename original `models.py` to `models.py.bak` (for reference)
6. Run `make test ARGS='apps.metrics'` to verify
7. Delete backup file after verification

**Acceptance Criteria:**
- All existing imports like `from apps.metrics.models import PullRequest` work unchanged
- All 30+ metrics test files pass
- Django migrations continue to work
- No circular import errors

### Phase 2: Split integrations/views.py (Priority: HIGH)

**Objective:** Split 1,321-line views.py into 5 provider-specific modules

**Steps:**
1. Create `apps/integrations/views/` directory
2. Create `helpers.py` with shared helper functions
3. Move GitHub views to `github.py`
4. Move Jira views to `jira.py`
5. Move Slack views to `slack.py`
6. Move status/copilot views to `status.py`
7. Create `__init__.py` with all re-exports
8. Update `urls.py` imports if needed
9. Run `make test ARGS='apps.integrations'` to verify

**Acceptance Criteria:**
- All URL patterns resolve correctly
- All OAuth flows work
- All 28+ integration test files pass
- No duplicate function definitions

### Phase 3: Split Large Test Files (Priority: MEDIUM)

**Objective:** Split 3 test files totaling ~10,300 lines into subdirectory structures

**Steps for each test file:**
1. Create test subdirectory (e.g., `tests/github_sync/`)
2. Create `__init__.py` (empty)
3. Group related test classes into focused files
4. Move test classes with their helper methods
5. Ensure imports are updated in each file
6. Run specific test directory to verify

**Acceptance Criteria:**
- All test classes discoverable by Django test runner
- No duplicate test class names
- Test count unchanged before/after split
- All tests pass

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Circular imports | Low | High | Careful import ordering in `__init__.py` |
| Missing re-exports | Low | Medium | Comprehensive `__all__` lists |
| Broken Django migrations | Very Low | High | Keep model `Meta.app_label` unchanged |
| Test discovery issues | Low | Medium | Proper `__init__.py` in test subdirs |
| URL routing breaks | Low | Medium | Verify all URL patterns after split |

---

## Success Metrics

1. **All files under 500 lines** - Each split file should be focused and readable
2. **Zero import failures** - All existing imports continue to work
3. **100% test pass rate** - No test regressions after splitting
4. **Claude Code can read all files** - No more token limit errors
5. **Migration stability** - Django makemigrations produces no changes

---

## Required Resources

- **Time Estimate:** 4-6 hours total
  - Phase 1 (models): 1.5-2 hours
  - Phase 2 (views): 1.5-2 hours
  - Phase 3 (tests): 2-3 hours

- **Dependencies:**
  - No external dependencies
  - No database changes
  - No new packages

- **Verification:**
  - `make test` - Full test suite
  - `make ruff` - Code quality
  - Manual verification of OAuth flows
