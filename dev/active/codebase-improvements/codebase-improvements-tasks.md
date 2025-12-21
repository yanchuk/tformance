# Codebase Improvements: Task Checklist

**Last Updated:** 2025-12-21

## Overview

- **Total Tasks:** 32
- **Completed:** 0
- **In Progress:** 0
- **Remaining:** 32

---

## Phase 1: Split metrics/models.py [10/10] ✅ COMPLETE

### 1.1 Setup [2/2]
- [x] Create `apps/metrics/models/` directory
- [x] Create `apps/metrics/models/base.py` with shared imports

### 1.2 Move Model Classes [7/7]
- [x] Create `team.py` with TeamMember
- [x] Create `github.py` with PullRequest, PRReview, PRCheckRun, PRFile, PRComment, Commit
- [x] Create `jira.py` with JiraIssue
- [x] Create `surveys.py` with PRSurvey, PRSurveyReview
- [x] Create `aggregations.py` with WeeklyMetrics, ReviewerCorrelation, AIUsageDaily
- [x] Create `insights.py` with DailyInsight
- [x] Create `deployments.py` with Deployment

### 1.3 Finalize [1/1]
- [x] Create `__init__.py` with all re-exports and `__all__`

### 1.4 Verify [PASSED]
- 116+ tests verified passing (seeding, survey service, PR processor)

---

## Phase 2: Split integrations/views.py [0/8]

### 2.1 Setup [0/1]
- [ ] Create `apps/integrations/views/` directory

### 2.2 Move View Functions [0/5]
- [ ] Create `helpers.py` with 6 helper functions (_create_repository_webhook, etc.)
- [ ] Create `github.py` with 10 GitHub view functions
- [ ] Create `jira.py` with 6 Jira view functions
- [ ] Create `slack.py` with 4 Slack view functions
- [ ] Create `status.py` with integrations_home, copilot_sync

### 2.3 Finalize [0/2]
- [ ] Create `__init__.py` with all re-exports
- [ ] Update `urls.py` imports if needed

### 2.4 Verify [0/0] (automated)
- Run `make test ARGS='apps.integrations'` after Phase 2 complete

---

## Phase 3: Split test_github_sync.py [0/5]

### 3.1 Setup [0/1]
- [ ] Create `apps/integrations/tests/github_sync/` directory with `__init__.py`

### 3.2 Move Test Classes [0/4]
- [ ] Create `test_pr_sync.py` (TestGetRepositoryPullRequests, TestGetUpdatedPullRequests)
- [ ] Create `test_review_sync.py` (TestGetPullRequestReviews)
- [ ] Create `test_repository_sync.py` (TestSyncRepositoryHistory, TestSyncRepositoryIncremental)
- [ ] Create remaining test files (jira_key, commits, check_runs, files, deployments, comments, iterations, correlations)

### 3.3 Verify [0/0] (automated)
- Run `make test ARGS='apps.integrations.tests.github_sync'` after complete

---

## Phase 4: Split test_dashboard_service.py [0/4]

### 4.1 Setup [0/1]
- [ ] Create `apps/metrics/tests/dashboard/` directory with `__init__.py`

### 4.2 Move Test Classes [0/3]
- [ ] Create `test_key_metrics.py` (TestGetKeyMetrics)
- [ ] Create `test_ai_metrics.py` (TestGetAIAdoptionTrend, TestGetAIQualityComparison)
- [ ] Create remaining test files (cycle_time, team_breakdown, review_*, pr_*, copilot, cicd, deployments, file_categories)

### 4.3 Verify [0/0] (automated)
- Run `make test ARGS='apps.metrics.tests.dashboard'` after complete

---

## Phase 5: Split test_models.py [0/4]

### 5.1 Setup [0/1]
- [ ] Create `apps/metrics/tests/models/` directory with `__init__.py`

### 5.2 Move Test Classes [0/3]
- [ ] Create `test_team_member.py` (TestTeamMemberModel)
- [ ] Create `test_pull_request.py` (TestPullRequestModel, TestPullRequestIterationFields, TestPullRequestFactory)
- [ ] Create remaining test files (pr_review, commit, jira, ai_usage, surveys, weekly_metrics, pr_check_run, pr_file, deployment, pr_comment, reviewer_correlation)

### 5.3 Verify [0/0] (automated)
- Run `make test ARGS='apps.metrics.tests.models'` after complete

---

## Final Verification [0/1]

- [ ] Run full test suite: `make test`
- [ ] Verify no migration changes: `python manage.py makemigrations --check --dry-run`
- [ ] Run code quality check: `make ruff`

---

## Cleanup [0/0]

After all phases verified:
- Delete original backup files (if created)
- Update this task file with completion status

---

## Notes

### Blockers
- None

### Decisions Made
- Using subdirectories for tests (not flat files)
- Maintaining backward-compatible imports via `__init__.py`
- Grouping tests by domain/feature

### Lessons Learned
(To be filled in after implementation)
