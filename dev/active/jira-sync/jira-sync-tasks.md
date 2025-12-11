# Phase 3.2: Jira Sync - Task Checklist

**Last Updated:** 2025-12-11

---

## Section 1: TrackedJiraProject Model (TDD)

### 1.1 Create TrackedJiraProject model
- [ ] Add model class to `apps/integrations/models.py`
- [ ] Fields: integration (FK), jira_project_id, jira_project_key, name
- [ ] Fields: is_active, last_sync_at, sync_status, last_sync_error
- [ ] Add indexes on jira_project_key and sync_status
- [ ] Write model tests

**Effort:** S
**Dependencies:** None

### 1.2 Create migration
- [ ] Generate migration with `make migrations`
- [ ] Review migration file
- [ ] Apply with `make migrate`

**Effort:** S
**Dependencies:** 1.1

### 1.3 Register in admin
- [ ] Add TrackedJiraProjectAdmin to admin.py
- [ ] Add TrackedJiraProjectInline to JiraIntegrationAdmin
- [ ] Configure list_display, list_filter, search_fields

**Effort:** S
**Dependencies:** 1.1

### 1.4 Create factory
- [ ] Add TrackedJiraProjectFactory to factories.py
- [ ] Include related JiraIntegration creation
- [ ] Write factory tests

**Effort:** S
**Dependencies:** 1.1

---

## Section 2: Jira Client Service (TDD)

### 2.1 Add jira-python package
- [ ] Run `uv add jira`
- [ ] Verify package installed

**Effort:** S
**Dependencies:** None

### 2.2 Create jira_client.py module
- [ ] Create `apps/integrations/services/jira_client.py`
- [ ] Define JiraClientError exception class
- [ ] Write initial tests

**Effort:** S
**Dependencies:** 2.1

### 2.3 Implement get_jira_client()
- [ ] Create authenticated JIRA instance
- [ ] Use `ensure_valid_jira_token()` for token refresh
- [ ] Handle authentication errors
- [ ] Write tests with mocked JIRA class

**Effort:** M
**Dependencies:** 2.2

### 2.4 Implement get_accessible_projects()
- [ ] Fetch all projects user can access
- [ ] Return list of project dicts (id, key, name)
- [ ] Handle pagination if needed
- [ ] Write tests with mocked responses

**Effort:** M
**Dependencies:** 2.3

### 2.5 Implement get_project_issues()
- [ ] Accept project_key and optional since datetime
- [ ] Build JQL query for full or incremental sync
- [ ] Fetch issues with required fields
- [ ] Handle pagination automatically
- [ ] Write tests with mocked responses

**Effort:** M
**Dependencies:** 2.3

---

## Section 3: Project Selection Views (TDD)

### 3.1 Create jira_projects_list view
- [ ] `@team_admin_required` decorator
- [ ] Fetch accessible projects from Jira API
- [ ] Load existing TrackedJiraProject records
- [ ] Render template with combined data
- [ ] Write view tests

**Effort:** M
**Dependencies:** 2.4

### 3.2 Create jira_project_toggle view
- [ ] `@team_admin_required` decorator
- [ ] Accept POST with project_id, project_key, name, action (add/remove)
- [ ] Create or delete TrackedJiraProject record
- [ ] Return success/error response (HTMX compatible)
- [ ] Write view tests

**Effort:** M
**Dependencies:** 3.1

### 3.3 Add URL patterns
- [ ] Add `jira/projects/` → `jira_projects_list`
- [ ] Add `jira/projects/toggle/` → `jira_project_toggle`

**Effort:** S
**Dependencies:** 3.1, 3.2

### 3.4 Create jira_projects.html template
- [ ] Extend base template
- [ ] List all accessible projects
- [ ] Show tracked/untracked status
- [ ] Add toggle buttons with HTMX
- [ ] Show sync status for tracked projects

**Effort:** M
**Dependencies:** 3.3

---

## Section 4: User Matching Service (TDD)

### 4.1 Create jira_user_matching.py module
- [ ] Create `apps/integrations/services/jira_user_matching.py`
- [ ] Define UserMatchingResult dataclass
- [ ] Write initial tests

**Effort:** S
**Dependencies:** 2.3

### 4.2 Implement sync_jira_users()
- [ ] Fetch all Jira users with project access
- [ ] For each user, attempt email match to TeamMember
- [ ] Update TeamMember.jira_account_id for matches
- [ ] Return summary (matched, unmatched, errors)
- [ ] Write tests

**Effort:** M
**Dependencies:** 4.1

### 4.3 Create user matching report
- [ ] Generate list of unmatched Jira users
- [ ] Store for admin review (session or model)
- [ ] Write tests

**Effort:** S
**Dependencies:** 4.2

---

## Section 5: Issue Sync Service (TDD)

### 5.1 Create jira_sync.py module
- [ ] Create `apps/integrations/services/jira_sync.py`
- [ ] Define JiraSyncError exception class
- [ ] Write initial tests

**Effort:** S
**Dependencies:** 2.5

### 5.2 Implement _convert_jira_issue_to_dict()
- [ ] Map Jira issue fields to JiraIssue model fields
- [ ] Handle sprint field parsing
- [ ] Handle story points custom field
- [ ] Handle missing/null fields gracefully
- [ ] Write tests for various issue formats

**Effort:** M
**Dependencies:** 5.1

### 5.3 Implement _calculate_cycle_time()
- [ ] Calculate hours from created to resolved
- [ ] Return None if not resolved
- [ ] Write tests

**Effort:** S
**Dependencies:** 5.1

### 5.4 Implement sync_project_issues()
- [ ] Accept TrackedJiraProject and full_sync flag
- [ ] Build JQL query based on sync type
- [ ] Fetch issues from Jira API
- [ ] Convert and upsert to JiraIssue model
- [ ] Update sync status and timestamp
- [ ] Return sync results summary
- [ ] Write comprehensive tests

**Effort:** L
**Dependencies:** 5.2, 5.3

### 5.5 Implement assignee lookup
- [ ] Look up TeamMember by jira_account_id
- [ ] Handle unmatched assignees (set null, log)
- [ ] Write tests

**Effort:** S
**Dependencies:** 5.4, 4.2

### 5.6 Handle sync errors
- [ ] Catch and log individual issue errors
- [ ] Continue sync on non-fatal errors
- [ ] Set error status on tracked project if fatal
- [ ] Write error handling tests

**Effort:** M
**Dependencies:** 5.4

---

## Section 6: Celery Tasks (TDD)

### 6.1 Create sync_jira_project_task
- [ ] Accept project_id parameter
- [ ] Set sync_status to syncing
- [ ] Call sync_project_issues()
- [ ] Update sync_status on completion
- [ ] Implement retry with exponential backoff
- [ ] Write tests

**Effort:** M
**Dependencies:** 5.4

### 6.2 Create sync_all_jira_projects_task
- [ ] Query all active TrackedJiraProject records
- [ ] Dispatch sync_jira_project_task for each
- [ ] Return dispatch summary
- [ ] Write tests

**Effort:** S
**Dependencies:** 6.1

### 6.3 Create sync_jira_users_task
- [ ] Accept team_id parameter
- [ ] Call sync_jira_users()
- [ ] Return matching results
- [ ] Write tests

**Effort:** S
**Dependencies:** 4.2

### 6.4 Add to Celery Beat schedule
- [ ] Schedule sync_all_jira_projects_task daily
- [ ] Configure schedule time (same as GitHub)
- [ ] Test schedule configuration

**Effort:** S
**Dependencies:** 6.2

---

## Section 7: UI Integration

### 7.1 Update integrations home page
- [ ] Add Jira section to `home.html`
- [ ] Show connection status
- [ ] Show number of tracked projects
- [ ] Add "Manage Projects" link
- [ ] Show last sync time and status

**Effort:** M
**Dependencies:** 3.4

### 7.2 Add navigation
- [ ] Add Jira projects link to sidebar/nav
- [ ] Update breadcrumbs

**Effort:** S
**Dependencies:** 7.1

---

## Summary

| Section | Tasks | Effort | Status |
|---------|-------|--------|--------|
| 1. TrackedJiraProject Model | 4 | S | Pending |
| 2. Jira Client Service | 5 | M | Pending |
| 3. Project Selection Views | 4 | M | Pending |
| 4. User Matching Service | 3 | S | Pending |
| 5. Issue Sync Service | 6 | L | Pending |
| 6. Celery Tasks | 4 | M | Pending |
| 7. UI Integration | 2 | S | Pending |
| **Total** | **28** | **M-L** | |

---

## TDD Workflow Reminder

For each task:

1. **RED**: Write failing test first
2. **GREEN**: Write minimum code to pass
3. **REFACTOR**: Clean up while keeping tests green

Use TDD agents:
- `tdd-test-writer` - RED phase
- `tdd-implementer` - GREEN phase
- `tdd-refactorer` - REFACTOR phase

---

## Verification Commands

```bash
# Pre-flight check
make test ARGS='--keepdb'

# Run section tests
make test ARGS='apps.integrations.tests.test_jira_client --keepdb'
make test ARGS='apps.integrations.tests.test_jira_sync --keepdb'
make test ARGS='apps.integrations.tests.test_jira_views_projects --keepdb'

# Lint check
make ruff

# Check migrations
make migrations  # Should create 0009_trackedjiraproject
make migrate
```

---

## Dependencies Graph

```
Section 1: Model
    │
    ▼
Section 2: Client Service ───────┐
    │                            │
    ▼                            ▼
Section 3: Views          Section 4: User Matching
    │                            │
    └────────────┬───────────────┘
                 │
                 ▼
          Section 5: Issue Sync
                 │
                 ▼
          Section 6: Celery Tasks
                 │
                 ▼
          Section 7: UI Integration
```
