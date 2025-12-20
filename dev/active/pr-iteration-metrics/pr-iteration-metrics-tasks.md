# PR Iteration Metrics & GitHub Analytics - Task Checklist

**Last Updated:** 2025-12-20 (Session 1)

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

## Phase 4: CI/CD Check Runs 🔄 IN PROGRESS

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

### 4.4 Check Run Sync Function 🔴 RED PHASE
- [x] Write failing tests (4 tests written)
- [ ] **NEXT: Implement `sync_pr_check_runs()` in github_sync.py**
- [ ] Run tests to verify GREEN
- [ ] Refactor if needed

### 4.4 Check Run Sync Tests (Written, Failing)
- [ ] test_sync_pr_check_runs_creates_records
- [ ] test_sync_pr_check_runs_calculates_duration
- [ ] test_sync_pr_check_runs_handles_pending_check
- [ ] test_sync_pr_check_runs_updates_existing

---

## Phase 5: PR Files ⏳ PENDING

### 5.1 Create PRFile Model
- [ ] Add model to `apps/metrics/models.py`
- [ ] Fields: pull_request, filename, status, additions, deletions, changes, file_category
- [ ] Add `categorize_file()` static method
- [ ] Register in admin

### 5.2 Migration
- [ ] Run `make migrations`
- [ ] Run `make migrate`

### 5.3 File Sync Function
- [ ] Create `sync_pr_files()` in `github_sync.py`
- [ ] Fetch via `pr.get_files()`
- [ ] Auto-categorize files

### 5.4 Add File Fields to PullRequest
- [ ] Add `primary_category` CharField
- [ ] Add `files_changed_count` IntegerField
- [ ] Generate migration

### 5.5 Integration & Tests
- [ ] Call in sync pipeline
- [ ] Create `PRFileFactory`
- [ ] Test file sync and categorization

---

## Phase 6: Deployments ⏳ PENDING

### 6.1 Create Deployment Model
- [ ] Add model to `apps/metrics/models.py`
- [ ] Fields: github_deployment_id, github_repo, environment, status, creator, deployed_at, pull_request, sha
- [ ] Register in admin

### 6.2 Migration
- [ ] Run `make migrations`
- [ ] Run `make migrate`

### 6.3 Deployment Sync Function
- [ ] Create `sync_repository_deployments()` in `github_sync.py`
- [ ] Fetch via `repo.get_deployments()`
- [ ] Get status from `deploy.get_statuses()`

### 6.4 Integration & Tests
- [ ] Add to repo sync pipeline
- [ ] Create `DeploymentFactory`
- [ ] Test deployment sync

---

## Phase 2: Comments ⏳ PENDING

### 2.1 Create PRComment Model
- [ ] Add model to `apps/metrics/models.py`
- [ ] Fields: github_comment_id, pull_request, author, body, comment_type, path, line, in_reply_to_id, timestamps
- [ ] Register in admin

### 2.2 Migration
- [ ] Run `make migrations`
- [ ] Run `make migrate`

### 2.3 Comment Sync Functions
- [ ] Create `sync_pr_issue_comments()`
- [ ] Create `sync_pr_review_comments()`

### 2.4 Integration & Tests
- [ ] Call in sync pipeline
- [ ] Create `PRCommentFactory`
- [ ] Test both comment types

---

## Deferred: Analytics (After Data Collection)

### Phase 3: Iteration Metrics
- [ ] Add iteration fields to PullRequest
- [ ] Review round calculation
- [ ] Fix response time calculation

### Phase 7: Review Correlations
- [ ] ReviewerCorrelation model
- [ ] Correlation calculation service
- [ ] Redundancy detection

### Phase 8: Dashboard
- [ ] CI/CD dashboard section
- [ ] Deployment metrics section
- [ ] Review correlation matrix
- [ ] Iteration metrics cards

---

## Session Handoff Notes

### Immediate Next Action
```bash
# 1. Resume TDD GREEN phase for check run sync
# Implement sync_pr_check_runs() in apps/integrations/services/github_sync.py

# 2. Run tests to verify
make test ARGS='apps.integrations.tests.test_github_sync::TestSyncPRCheckRuns --keepdb'

# 3. If all pass, do refactor phase
```

### Key Files to Modify
- `apps/integrations/services/github_sync.py` - Add `sync_pr_check_runs()` function

### Test Classes Already Written
- `TestSyncPRCheckRuns` in `apps/integrations/tests/test_github_sync.py` (4 tests, currently failing)

### Migrations Status
- All migrations created and applied
- No pending migrations

### Verify Commands on Resume
```bash
make test ARGS='--keepdb' 2>&1 | tail -5  # Should show all tests passing except new sync tests
make migrations  # Should show "No changes detected"
```
