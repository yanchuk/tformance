# PR Iteration Metrics & GitHub Analytics - Task Checklist

**Last Updated:** 2025-12-20 (Session 3)

## Priority: Data Collection First

Focus on syncing all data now, build analytics later.

---

## Phase 1: Commit Sync ✅ COMPLETE

### 1.1 Commit Sync Function ✅
- [x] Create `sync_pr_commits()` in `github_sync.py`
- [x] Fetch commits via `pr.get_commits()`
- [x] Map to existing `Commit` model fields
- [x] Handle author lookup via `_get_team_member_by_github_id()`
- [x] Use `update_or_create` for idempotency
- [x] Add `errors` parameter for error accumulation

### 1.2 Tests ✅
- [x] test_sync_pr_commits_creates_commit_records
- [x] test_sync_pr_commits_links_to_pull_request
- [x] test_sync_pr_commits_maps_author_by_github_id
- [x] test_sync_pr_commits_handles_unknown_author
- [x] test_sync_pr_commits_handles_null_author
- [x] test_sync_pr_commits_updates_existing_commits

---

## Phase 4: CI/CD Check Runs ✅ COMPLETE

### 4.1 Create PRCheckRun Model ✅
- [x] Add model to `apps/metrics/models.py`
- [x] Fields: github_check_run_id, pull_request, name, status, conclusion, started_at, completed_at, duration_seconds
- [x] Add indexes (pr_name, started_at)
- [x] Register in admin
- [x] Create migration (0003_prcheckrun.py)
- [x] Apply migration
- [x] Add index on started_at (0004 migration)

### 4.2 PRCheckRun Model Tests ✅
- [x] test_pr_check_run_creation
- [x] test_pr_check_run_pull_request_relationship
- [x] test_pr_check_run_unique_constraint
- [x] test_pr_check_run_str_representation

### 4.3 PRCheckRunFactory ✅
- [x] Create factory in `apps/metrics/factories.py`

### 4.4 Check Run Sync Function ✅
- [x] Write failing tests (4 tests)
- [x] Implement `sync_pr_check_runs()` in github_sync.py
- [x] All tests passing
- [x] Refactored for consistency

### 4.4 Check Run Sync Tests ✅
- [x] test_sync_pr_check_runs_creates_records
- [x] test_sync_pr_check_runs_calculates_duration
- [x] test_sync_pr_check_runs_handles_pending_check
- [x] test_sync_pr_check_runs_updates_existing

---

## Phase 5: PR Files ✅ COMPLETE

### 5.1 Create PRFile Model ✅
- [x] Add model to `apps/metrics/models.py`
- [x] Fields: pull_request, filename, status, additions, deletions, changes, file_category
- [x] Add `categorize_file()` static method
- [x] Register in admin
- [x] Migration 0005_prfile.py created and applied

### 5.2 PRFile Tests ✅
- [x] test_pr_file_creation
- [x] test_pr_file_pull_request_relationship
- [x] test_pr_file_unique_constraint
- [x] test_pr_file_categorize_frontend
- [x] test_pr_file_categorize_backend
- [x] test_pr_file_categorize_test
- [x] test_pr_file_categorize_docs
- [x] test_pr_file_categorize_config
- [x] test_pr_file_categorize_other

### 5.3 File Sync Function ✅
- [x] Create `sync_pr_files()` in `github_sync.py`
- [x] Fetch via `pr.get_files()`
- [x] Auto-categorize files using PRFile.categorize_file()
- [x] 4 tests passing

---

## Phase 6: Deployments ✅ COMPLETE

### 6.1 Create Deployment Model ✅
- [x] Add model to `apps/metrics/models.py`
- [x] Fields: github_deployment_id, github_repo, environment, status, creator, deployed_at, pull_request, sha
- [x] STATUS_CHOICES and ENVIRONMENT_CHOICES
- [x] Register in admin
- [x] Migrations 0006 and 0007 created and applied

### 6.2 Deployment Tests ✅
- [x] test_deployment_creation
- [x] test_deployment_team_relationship
- [x] test_deployment_unique_constraint
- [x] test_deployment_str_representation
- [x] test_deployment_creator_relationship
- [x] test_deployment_pull_request_relationship

### 6.3 Deployment Sync Function ✅
- [x] Create `sync_repository_deployments()` in `github_sync.py`
- [x] Fetch via `repo.get_deployments()`
- [x] Get status from `deploy.get_statuses()`
- [x] 6 tests passing

---

## Phase 2: Comments ✅ COMPLETE

### 2.1 Create PRComment Model ✅
- [x] Add model to `apps/metrics/models.py`
- [x] Fields: github_comment_id, pull_request, author, body, comment_type, path, line, in_reply_to_id, timestamps
- [x] COMMENT_TYPE_CHOICES (issue, review)
- [x] Register in admin
- [x] Migration 0008_prcomment.py created and applied

### 2.2 PRComment Tests ✅
- [x] test_pr_comment_creation
- [x] test_pr_comment_team_relationship
- [x] test_pr_comment_unique_constraint
- [x] test_pr_comment_str_representation
- [x] test_pr_comment_author_relationship
- [x] test_pr_comment_pull_request_relationship
- [x] test_pr_comment_type_choices
- [x] test_pr_comment_review_fields

### 2.3 Comment Sync Functions ✅
- [x] Create `sync_pr_issue_comments()` - general PR comments
- [x] Create `sync_pr_review_comments()` - inline code comments
- [x] Refactored to shared `_sync_pr_comments()` helper
- [x] 8 tests passing (4 per function)

---

## Phase 9: Update Real-Life Testing Guide ✅ COMPLETE

- [x] Added Phase 2.6 section to REAL-WORLD-TESTING.md
- [x] Documented verification for all sync features
- [x] Added database verification queries
- [x] Added troubleshooting section

---

## Phase 3: Iteration Metrics ✅ COMPLETE

### 3.1 Add Iteration Fields to PullRequest ✅
- [x] review_rounds (IntegerField) - cycles of changes_requested → commit
- [x] avg_fix_response_hours (DecimalField) - average time to address reviews
- [x] commits_after_first_review (IntegerField) - post-review commit count
- [x] total_comments (IntegerField) - total PR comments
- [x] Migration 0009_add_iteration_fields.py created and applied

### 3.2 Iteration Field Tests ✅
- [x] test_iteration_fields_null_by_default
- [x] test_iteration_fields_can_be_set

### 3.3 Iteration Metrics Calculation ✅
- [x] Create `calculate_pr_iteration_metrics()` in github_sync.py
- [x] Calculate total_comments from PRComment count
- [x] Calculate commits_after_first_review from Commit queryset
- [x] Calculate review_rounds from changes_requested → commit cycles
- [x] Calculate avg_fix_response_hours from review-to-commit times
- [x] 6 calculation tests passing

### 3.4 Pipeline Integration ✅
- [x] Call `calculate_pr_iteration_metrics()` from `_process_prs()`

---

## Phase 7: Reviewer Correlations ✅ COMPLETE

### 7.1 ReviewerCorrelation Model ✅
- [x] Add model to `apps/metrics/models.py`
- [x] Fields: reviewer_1, reviewer_2, prs_reviewed_together, agreements, disagreements
- [x] Properties: agreement_rate, is_redundant
- [x] Migration 0010_reviewercorrelation.py created and applied
- [x] Admin registration with computed fields
- [x] 8 model tests passing

### 7.2 Correlation Calculation ✅
- [x] Create `calculate_reviewer_correlations()` in github_sync.py
- [x] Analyze PRReview records for reviewer pairs
- [x] Count agreements (both approved or both changes_requested)
- [x] Count disagreements (mixed states)
- [x] Ignore "commented" reviews
- [x] 5 calculation tests passing

### 7.3 Redundancy Detection ✅
- [x] `is_redundant` property on model
- [x] Thresholds: 95% agreement on 10+ shared PRs
- [x] Tests for high agreement detection
- [x] Tests for low sample size handling

---

## Phase 8: Dashboard Integration ✅ COMPLETE

### 8.1 Dashboard Service Functions ✅
- [x] `get_iteration_metrics()` - aggregate iteration metrics
- [x] `get_reviewer_correlations()` - reviewer pair analysis

### 8.2 Views and URLs ✅
- [x] `iteration_metrics_card` view
- [x] `reviewer_correlations_table` view
- [x] URL patterns added

### 8.3 Templates ✅
- [x] `iteration_metrics_card.html` - 4-stat grid
- [x] `reviewer_correlations_table.html` - table with badges

### 8.4 CTO Dashboard Integration ✅
- [x] Added Iteration Metrics section
- [x] Added Reviewer Correlations section

### 8.5 Tests ✅
- [x] 6 tests for get_iteration_metrics
- [x] 6 tests for get_reviewer_correlations

---

## Future Enhancements ✅ COMPLETE

- [x] CI/CD pass rate dashboard section (from PRCheckRun)
- [x] Deployment metrics section (DORA from Deployment)
- [x] File category breakdown charts (from PRFile)

---

## Session 2 Summary

### Completed This Session
- Phase 4: CI/CD Check Runs (sync function)
- Phase 5: PR Files (model + sync)
- Phase 6: Deployments (model + sync)
- Phase 2: PR Comments (model + sync)
- Phase 9: Testing guide update
- **Pipeline Integration** - All syncs now called automatically

### New Models Created
| Model | Migration | Tests |
|-------|-----------|-------|
| PRCheckRun | 0003, 0004 | 4 model + 4 sync |
| PRFile | 0005 | 9 model + 4 sync |
| Deployment | 0006, 0007 | 6 model + 6 sync |
| PRComment | 0008 | 8 model + 8 sync |

### New Sync Functions
- `sync_pr_commits()` - PR commits
- `sync_pr_check_runs()` - CI/CD check runs
- `sync_pr_files()` - Files changed
- `sync_repository_deployments()` - GitHub deployments
- `sync_pr_issue_comments()` - General PR comments
- `sync_pr_review_comments()` - Inline code comments

### Pipeline Integration
`_process_prs()` now calls all sync functions for each PR.
`sync_repository_history()` and `sync_repository_incremental()` now include deployments.

### Test Count
All tests passing: **1507 total tests** (73 in test_github_sync.py)

### Verify Commands
```bash
make test ARGS='--keepdb'  # All 1507 tests
make test ARGS='apps.integrations.tests.test_github_sync --keepdb'
make migrations  # Should show "No changes detected"
```
