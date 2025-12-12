# Phase 3.2: Jira Sync - Task Checklist

**Last Updated:** 2025-12-11
**Status:** IN PROGRESS (Sections 1-5 Complete, Section 5 REFACTOR phase pending)

---

## Section 1: TrackedJiraProject Model (TDD)

### 1.1 Create TrackedJiraProject model
- [x] Add model class to `apps/integrations/models.py`
- [x] Fields: integration (FK), jira_project_id, jira_project_key, name
- [x] Fields: is_active, last_sync_at, sync_status, last_sync_error
- [x] Add indexes on jira_project_key and sync_status
- [x] Write model tests (12 tests)

### 1.2 Create migration
- [x] Generate migration with `make migrations`
- [x] Review migration file (0009_trackedjiraproject.py)
- [x] Apply with `make migrate`

### 1.3 Register in admin
- [x] Add TrackedJiraProjectAdmin to admin.py
- [x] Add TrackedJiraProjectInline to JiraIntegrationAdmin
- [x] Configure list_display, list_filter, search_fields

### 1.4 Create factory
- [x] Add TrackedJiraProjectFactory to factories.py
- [x] Include related JiraIntegration creation
- [x] Write factory tests

**Status:** COMPLETE (12 tests)

---

## Section 2: Jira Client Service (TDD)

### 2.1 Add jira-python package
- [x] Run `uv add jira`
- [x] Verify package installed (jira==3.10.5)

### 2.2 Create jira_client.py module
- [x] Create `apps/integrations/services/jira_client.py`
- [x] Define JiraClientError exception class
- [x] Write initial tests

### 2.3 Implement get_jira_client()
- [x] Create authenticated JIRA instance
- [x] Use `ensure_valid_jira_token()` for token refresh
- [x] Handle authentication errors
- [x] Write tests with mocked JIRA class

### 2.4 Implement get_accessible_projects()
- [x] Fetch all projects user can access
- [x] Return list of project dicts (id, key, name)
- [x] Handle pagination if needed
- [x] Write tests with mocked responses

### 2.5 Implement get_project_issues()
- [x] Accept project_key and optional since datetime
- [x] Build JQL query for full or incremental sync
- [x] Fetch issues with required fields
- [x] Handle pagination automatically
- [x] Write tests with mocked responses

**Status:** COMPLETE (13 tests)

---

## Section 3: Project Selection Views (TDD)

### 3.1 Create jira_projects_list view
- [x] `@team_admin_required` decorator
- [x] Fetch accessible projects from Jira API
- [x] Load existing TrackedJiraProject records
- [x] Render template with combined data
- [x] Write view tests

### 3.2 Create jira_project_toggle view
- [x] `@team_admin_required` decorator
- [x] Accept POST with project_id, project_key, name, action (add/remove)
- [x] Create or delete TrackedJiraProject record
- [x] Return success/error response (JSON)
- [x] Write view tests

### 3.3 Add URL patterns
- [x] Add `jira/projects/` → `jira_projects_list`
- [x] Add `jira/projects/toggle/` → `jira_project_toggle`

### 3.4 Create jira_projects_list.html template
- [x] Extend base template
- [x] List all accessible projects
- [x] Show tracked/untracked status

**Status:** COMPLETE (16 tests)

---

## Section 4: User Matching Service (TDD)

### 4.1 Create jira_user_matching.py module
- [x] Create `apps/integrations/services/jira_user_matching.py`
- [x] Write initial tests

### 4.2 Implement sync_jira_users()
- [x] Fetch all Jira users
- [x] For each user, attempt email match to TeamMember
- [x] Update TeamMember.jira_account_id for matches
- [x] Return summary (matched, unmatched, errors)
- [x] Write tests

### 4.3 Create user matching report
- [x] Generate list of unmatched Jira users
- [x] Return for admin review
- [x] Write tests

**Status:** COMPLETE (12 tests)

---

## Section 5: Issue Sync Service (TDD)

### 5.1 Create jira_sync.py module
- [x] Create `apps/integrations/services/jira_sync.py`
- [x] Define JiraSyncError exception class
- [x] Write initial tests

### 5.2 Implement _convert_jira_issue_to_dict()
- [x] Map Jira issue fields to JiraIssue model fields
- [x] Handle story points
- [x] Handle missing/null fields gracefully
- [x] Write tests for various issue formats

### 5.3 Implement _calculate_cycle_time()
- [x] Calculate hours from created to resolved
- [x] Return None if not resolved
- [x] Write tests

### 5.4 Implement sync_project_issues()
- [x] Accept TrackedJiraProject and full_sync flag
- [x] Build JQL query based on sync type
- [x] Fetch issues from Jira API
- [x] Convert and upsert to JiraIssue model
- [x] Update sync status and timestamp
- [x] Return sync results summary
- [x] Write comprehensive tests

### 5.5 Implement assignee lookup
- [x] Look up TeamMember by jira_account_id
- [x] Handle unmatched assignees (set null, log)
- [x] Write tests

### 5.6 Handle sync errors
- [x] Catch and log individual issue errors
- [x] Continue sync on non-fatal errors
- [x] Set error status on tracked project if fatal
- [x] Write error handling tests

**Status:** GREEN COMPLETE, REFACTOR PENDING (16 tests)

---

## Section 6: Celery Tasks (TDD)

### 6.1 Create sync_jira_project_task
- [ ] Accept project_id parameter
- [ ] Set sync_status to syncing
- [ ] Call sync_project_issues()
- [ ] Update sync_status on completion
- [ ] Implement retry with exponential backoff
- [ ] Write tests

### 6.2 Create sync_all_jira_projects_task
- [ ] Query all active TrackedJiraProject records
- [ ] Dispatch sync_jira_project_task for each
- [ ] Return dispatch summary
- [ ] Write tests

### 6.3 Create sync_jira_users_task
- [ ] Accept team_id parameter
- [ ] Call sync_jira_users()
- [ ] Return matching results
- [ ] Write tests

### 6.4 Add to Celery Beat schedule
- [ ] Schedule sync_all_jira_projects_task daily
- [ ] Configure schedule time (same as GitHub)
- [ ] Test schedule configuration

**Status:** PENDING

---

## Section 7: UI Integration

### 7.1 Update integrations home page
- [ ] Add Jira section to `home.html`
- [ ] Show connection status
- [ ] Show number of tracked projects
- [ ] Add "Manage Projects" link
- [ ] Show last sync time and status

### 7.2 Add navigation
- [ ] Add Jira projects link to sidebar/nav
- [ ] Update breadcrumbs

**Status:** PENDING

---

## Summary

| Section | Tasks | Status | Tests |
|---------|-------|--------|-------|
| 1. TrackedJiraProject Model | 4 | COMPLETE | 12 |
| 2. Jira Client Service | 5 | COMPLETE | 13 |
| 3. Project Selection Views | 4 | COMPLETE | 16 |
| 4. User Matching Service | 3 | COMPLETE | 12 |
| 5. Issue Sync Service | 6 | GREEN DONE | 16 |
| 6. Celery Tasks | 4 | PENDING | 0 |
| 7. UI Integration | 2 | PENDING | 0 |
| **Total** | **28** | **5/7 done** | **69** |

---

## Verification Commands

```bash
# Pre-flight check
make test ARGS='--keepdb'
# Expected: 776 tests pass

# Run section tests
make test ARGS='apps.integrations.tests.test_jira_client --keepdb'
make test ARGS='apps.integrations.tests.test_jira_sync --keepdb'
make test ARGS='apps.integrations.tests.test_jira_user_matching --keepdb'
make test ARGS='apps.integrations.tests.test_jira_views_projects --keepdb'

# Lint check
make ruff

# Check migrations - already created and applied
# 0009_trackedjiraproject.py
# 0010_rename_tracked_jira_sync_idx_tracked_jira_sync_status_idx_and_more.py
```
