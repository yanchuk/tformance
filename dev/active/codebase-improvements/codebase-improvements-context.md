# Codebase Improvements: Context

**Last Updated:** 2025-12-21

## Key Files

### Files to Split

| File | Lines | Action |
|------|-------|--------|
| `apps/metrics/models.py` | 1,518 | Split into `apps/metrics/models/` (8 files) |
| `apps/integrations/views.py` | 1,321 | Split into `apps/integrations/views/` (5 files) |
| `apps/integrations/tests/test_github_sync.py` | 4,391 | Split into `tests/github_sync/` (11 files) |
| `apps/metrics/tests/test_dashboard_service.py` | 3,142 | Split into `tests/dashboard/` (12 files) |
| `apps/metrics/tests/test_models.py` | 2,847 | Split into `tests/models/` (13 files) |

### Files to Update

| File | Update Required |
|------|----------------|
| `apps/metrics/admin.py` | May need import updates (verify after split) |
| `apps/integrations/urls.py` | May need import updates (verify after split) |
| `apps/metrics/factories.py` | Uses models - backward compatible |
| `apps/metrics/processors.py` | Uses models - backward compatible |

### Reference Files

| File | Purpose |
|------|---------|
| `apps/teams/models.py` | BaseTeamModel definition |
| `apps/utils/models.py` | BaseModel definition |
| `CLAUDE.md` | Coding guidelines |

---

## Model Class Mapping

### models.py -> models/github.py
```python
# Line 97: class PullRequest(BaseTeamModel)
# Line 288: class PRReview(BaseTeamModel)
# Line 378: class PRCheckRun(BaseTeamModel)
# Line 466: class PRFile(BaseTeamModel)
# Line 570: class Commit(BaseTeamModel)
# Line 1159: class PRComment(BaseTeamModel)
```

### models.py -> models/team.py
```python
# Line 6: class TeamMember(BaseTeamModel)
```

### models.py -> models/jira.py
```python
# Line 665: class JiraIssue(BaseTeamModel)
```

### models.py -> models/surveys.py
```python
# Line 870: class PRSurvey(BaseTeamModel)
# Line 958: class PRSurveyReview(BaseTeamModel)
```

### models.py -> models/aggregations.py
```python
# Line 791: class AIUsageDaily(BaseTeamModel)
# Line 1027: class WeeklyMetrics(BaseTeamModel)
# Line 1347: class ReviewerCorrelation(BaseTeamModel)
```

### models.py -> models/insights.py
```python
# Line 1432: class DailyInsight(BaseTeamModel)
```

### models.py -> models/deployments.py
```python
# Line 1256: class Deployment(BaseTeamModel)
```

---

## View Function Mapping

### views.py -> views/helpers.py
```python
# Line 42: def _create_repository_webhook(...)
# Line 69: def _delete_repository_webhook(...)
# Line 90: def _create_integration_credential(...)
# Line 111: def _validate_oauth_callback(...)
# Line 158: def _create_github_integration(...)
# Line 178: def _sync_github_members_after_connection(...)
```

### views.py -> views/github.py
```python
# Line 278: def github_connect(request)
# Line 312: def github_callback(request)
# Line 381: def github_disconnect(request)
# Line 412: def github_select_org(request)
# Line 465: def github_members(request)
# Line 499: def github_members_sync(request)
# Line 547: def github_member_toggle(request, member_id)
# Line 591: def github_repos(request)
# Line 646: def github_repo_toggle(request, repo_id)
# Line 754: def github_repo_sync(request, repo_id)
```

### views.py -> views/jira.py
```python
# Line 788: def jira_connect(request)
# Line 822: def jira_callback(request)
# Line 894: def jira_disconnect(request)
# Line 925: def jira_select_site(request)
# Line 981: def jira_projects_list(request)
# Line 1028: def jira_project_toggle(request)
```

### views.py -> views/slack.py
```python
# Line 1085: def slack_connect(request)
# Line 1119: def slack_callback(request)
# Line 1199: def slack_disconnect(request)
# Line 1230: def slack_settings(request)
```

### views.py -> views/status.py
```python
# Line 202: def integrations_home(request)
# Line 1293: def copilot_sync(request)
```

---

## Test Class Mapping

### test_github_sync.py -> github_sync/

| File | Test Classes |
|------|-------------|
| `test_pr_sync.py` | TestGetRepositoryPullRequests, TestGetUpdatedPullRequests |
| `test_review_sync.py` | TestGetPullRequestReviews |
| `test_repository_sync.py` | TestSyncRepositoryHistory, TestSyncRepositoryIncremental |
| `test_jira_key.py` | TestJiraKeyExtraction |
| `test_commit_sync.py` | TestSyncPRCommits |
| `test_check_runs.py` | TestSyncPRCheckRuns |
| `test_files.py` | TestSyncPRFiles |
| `test_deployments.py` | TestSyncRepositoryDeployments |
| `test_issue_comments.py` | TestSyncPRIssueComments |
| `test_review_comments.py` | TestSyncPRReviewComments |
| `test_iterations.py` | TestCalculatePRIterationMetrics |
| `test_correlations.py` | TestCalculateReviewerCorrelations |

### test_dashboard_service.py -> dashboard/

| File | Test Classes |
|------|-------------|
| `test_key_metrics.py` | TestGetKeyMetrics |
| `test_ai_metrics.py` | TestGetAIAdoptionTrend, TestGetAIQualityComparison |
| `test_cycle_time.py` | TestGetCycleTimeTrend |
| `test_team_breakdown.py` | TestGetTeamBreakdown |
| `test_review_distribution.py` | TestGetReviewDistribution |
| `test_review_time.py` | TestGetReviewTimeTrend |
| `test_recent_prs.py` | TestGetRecentPrs |
| `test_revert_hotfix.py` | TestGetRevertHotfixStats |
| `test_pr_size.py` | TestGetPrSizeDistribution |
| `test_unlinked_prs.py` | TestGetUnlinkedPrs |
| `test_reviewer_workload.py` | TestGetReviewerWorkload |
| `test_copilot.py` | TestCopilotDashboardService |
| `test_iterations.py` | TestGetIterationMetrics |
| `test_correlations.py` | TestGetReviewerCorrelations |
| `test_cicd.py` | TestGetCicdPassRate |
| `test_deployments.py` | TestGetDeploymentMetrics |
| `test_file_categories.py` | TestGetFileCategoryBreakdown |

### test_models.py -> models/

| File | Test Classes |
|------|-------------|
| `test_team_member.py` | TestTeamMemberModel |
| `test_pull_request.py` | TestPullRequestModel, TestPullRequestIterationFields, TestPullRequestFactory |
| `test_pr_review.py` | TestPRReviewModel |
| `test_commit.py` | TestCommitModel |
| `test_jira.py` | TestJiraIssueModel, TestJiraIssuePRLinking |
| `test_ai_usage.py` | TestAIUsageDailyModel |
| `test_surveys.py` | TestPRSurveyModel, TestPRSurveyReviewModel |
| `test_weekly_metrics.py` | TestWeeklyMetricsModel |
| `test_pr_check_run.py` | TestPRCheckRunModel |
| `test_pr_file.py` | TestPRFileModel |
| `test_deployment.py` | TestDeploymentModel |
| `test_pr_comment.py` | TestPRCommentModel |
| `test_reviewer_correlation.py` | TestReviewerCorrelationModel |

---

## Key Decisions

1. **Backward Compatibility**: All existing imports continue to work via `__init__.py` re-exports
2. **No Migration Changes**: Model app_label remains unchanged (metrics)
3. **Test Organization**: Use subdirectories to group related tests
4. **Naming Convention**: Match domain names (github, jira, slack, surveys, etc.)

---

## Dependencies

### Internal Dependencies
- `apps/teams/models.py` - BaseTeamModel used by all models
- `apps/utils/models.py` - BaseModel (extended by BaseTeamModel)

### External Dependencies
- Django ORM (no changes needed)
- Factory Boy (backward compatible)

### No Breaking Changes To
- API endpoints
- URL patterns
- Database schema
- Celery tasks
- Admin registrations

---

## Verification Commands

```bash
# Run all metrics tests
make test ARGS='apps.metrics'

# Run all integration tests
make test ARGS='apps.integrations'

# Run specific test directory
make test ARGS='apps.integrations.tests.github_sync'

# Check for migration issues
python manage.py makemigrations --check --dry-run

# Verify code quality
make ruff

# Full test suite
make test
```
