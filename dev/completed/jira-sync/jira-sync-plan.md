# Phase 3.2: Jira Project Selection & Issue Sync

**Last Updated:** 2025-12-11

---

## Executive Summary

Phase 3.2 builds on the completed Jira OAuth integration (Phase 3.1) to enable Jira project selection and issue synchronization. This phase allows teams to select which Jira projects to track and syncs issues to the local database for metrics analysis.

### Key Deliverables

1. **TrackedJiraProject model** - Store selected Jira projects for each team
2. **Project selection UI** - Allow admins to choose which projects to track
3. **Jira issue sync service** - Fetch and store issues using jira-python library
4. **User matching** - Link Jira users to existing TeamMembers by email
5. **Celery tasks** - Background jobs for initial and incremental sync

### Success Criteria

- [ ] Admin can select Jira projects to track
- [ ] Issues sync from selected projects to JiraIssue model
- [ ] Jira users auto-match to TeamMembers by email
- [ ] Incremental sync updates only recently changed issues
- [ ] All operations use `ensure_valid_jira_token()` for auto-refresh

---

## Current State Analysis

### What Exists (Phase 3.1 Complete)

| Component | Status | Location |
|-----------|--------|----------|
| Jira OAuth flow | Complete | `services/jira_oauth.py` |
| JiraIntegration model | Complete | `integrations/models.py` |
| Token refresh helper | Complete | `ensure_valid_jira_token()` |
| JiraIssue model | Complete | `metrics/models.py` |
| TeamMember model | Complete | Has `jira_account_id` field |

### What's Missing (Phase 3.2 Scope)

| Component | Required | Notes |
|-----------|----------|-------|
| TrackedJiraProject model | New | Similar to TrackedRepository |
| Project selection views | New | List projects, select/deselect |
| Jira API client service | New | Use jira-python library |
| Issue sync service | New | Historical + incremental |
| User matching service | New | Email-based matching |
| Celery sync tasks | New | Background sync jobs |

---

## Proposed Architecture

### Data Flow

```
JiraIntegration (OAuth tokens)
        │
        ▼
TrackedJiraProject (selected projects)
        │
        ▼
Jira API (jira-python library)
        │
        ├──▶ JiraIssue (metrics/models.py)
        └──▶ TeamMember.jira_account_id (user matching)
```

### Model Relationships

```
Team
  ├── JiraIntegration (1:1)
  │     └── IntegrationCredential (1:1)
  │
  └── TrackedJiraProject (1:N) [NEW]
        └── JiraIssue (via jira_key linkage)
```

### API Patterns

**Jira REST API v3** (via jira-python library):
- `GET /rest/api/3/project` - List accessible projects
- `GET /rest/api/3/search` - Search issues with JQL
- `GET /rest/api/3/user/search` - Search users
- `GET /rest/api/3/myself` - Get current user

All calls go through:
```
https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/...
```

---

## Implementation Sections

### Section 1: TrackedJiraProject Model

Create model to store selected Jira projects.

**Fields:**
- `integration` - FK to JiraIntegration
- `jira_project_id` - Jira's internal project ID
- `jira_project_key` - Project key (e.g., "PROJ")
- `name` - Display name
- `is_active` - Whether currently tracking
- `last_sync_at` - Last successful sync
- `sync_status` - pending/syncing/complete/error
- `last_sync_error` - Error message if failed

**Effort:** Small

---

### Section 2: Jira Client Service

Create service layer for Jira API calls using jira-python library.

**Functions:**
- `get_jira_client(credential)` - Create authenticated JIRA instance
- `get_accessible_projects(credential)` - List all accessible projects
- `get_project_issues(credential, project_key, since=None)` - Get issues with JQL
- `get_jira_users(credential, project_key)` - Get users with access to project

**Key Considerations:**
- Use `ensure_valid_jira_token()` before each API call
- Handle pagination automatically (jira-python does this)
- Convert Jira datetime strings to Python datetime objects
- Map issue types and statuses correctly

**Effort:** Medium

---

### Section 3: Project Selection Views

Allow admins to select which Jira projects to track.

**Views:**
- `jira_projects_list` - Show available and selected projects
- `jira_project_toggle` - Add/remove project from tracking

**URL Patterns:**
- `jira/projects/` - List projects
- `jira/projects/toggle/` - Toggle tracking (POST)

**Template:** `jira_projects.html`
- Show all accessible projects from Jira
- Checkbox/toggle for each project
- Show sync status for tracked projects

**Effort:** Medium

---

### Section 4: User Matching Service

Match Jira users to existing TeamMembers by email.

**Functions:**
- `sync_jira_users(team, credential)` - Fetch and match users
- `match_jira_user_to_team_member(jira_user, team)` - Single user matching

**Matching Strategy:**
1. Primary: Match by email address
2. Fallback: Match by display name (exact)
3. Unmatched: Log for manual resolution

**Updates:**
- Set `TeamMember.jira_account_id` when matched
- Create report of unmatched users for admin review

**Effort:** Small

---

### Section 5: Issue Sync Service

Sync Jira issues to local database.

**Functions:**
- `sync_project_issues(tracked_project, full_sync=False)` - Main sync function
- `_convert_jira_issue_to_dict(issue)` - Normalize issue data
- `_calculate_cycle_time(issue)` - Calculate time from creation to resolution

**JQL Queries:**
- Full sync: `project = {key} ORDER BY updated DESC`
- Incremental: `project = {key} AND updated >= "{last_sync}"`

**Data Mapping:**
| Jira Field | JiraIssue Field |
|------------|-----------------|
| `key` | `jira_key` |
| `id` | `jira_id` |
| `fields.summary` | `summary` |
| `fields.issuetype.name` | `issue_type` |
| `fields.status.name` | `status` |
| `fields.assignee.accountId` | `assignee` (FK lookup) |
| `fields.customfield_10016` | `story_points` (configurable) |
| `fields.sprint[0]` | `sprint_id`, `sprint_name` |
| `fields.created` | `issue_created_at` |
| `fields.resolutiondate` | `resolved_at` |

**Effort:** Large

---

### Section 6: Celery Tasks

Background jobs for sync operations.

**Tasks:**
- `sync_jira_project_task(project_id)` - Sync single project
- `sync_all_jira_projects_task()` - Dispatch sync for all active projects
- `sync_jira_users_task(team_id)` - Sync users for a team

**Scheduling:**
- Daily sync via Celery Beat (same as GitHub)
- Retry with exponential backoff on failure

**Effort:** Medium

---

### Section 7: Integration with Existing UI

Update integrations home page to show Jira status.

**Updates to `home.html`:**
- Show Jira connection status
- Link to project selection
- Show sync status summary

**Effort:** Small

---

## Risk Assessment

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Jira rate limiting | Implement backoff, batch requests |
| Token expiration mid-sync | `ensure_valid_jira_token()` checks before each call |
| Large projects with many issues | Paginate, use date filters for incremental |
| Story points in custom field | Make field ID configurable |
| Sprint data in complex format | Parse sprint string format |

### API Limitations

| Limitation | Workaround |
|------------|------------|
| No dev info API (linked PRs) | Already solved: extract jira_key from GitHub PRs |
| 50 results per page default | jira-python handles pagination |
| JQL date format specific | Use ISO format: `"2024-01-01 00:00"` |

---

## Success Metrics

1. **Functional**
   - Projects selectable and trackable
   - Issues sync with correct field mapping
   - Users matched to TeamMembers by email
   - Incremental sync works correctly

2. **Performance**
   - Initial sync completes within 5 minutes per 1000 issues
   - Incremental sync processes only changed issues
   - No token expiration errors during sync

3. **Quality**
   - 100% test coverage for new code (TDD)
   - All lint checks pass
   - No regressions in existing functionality

---

## Dependencies

### External
- `jira` package (jira-python library) - Add to requirements

### Internal (All Complete)
- Phase 3.1: Jira OAuth ✅
- `ensure_valid_jira_token()` ✅
- `JiraIssue` model ✅
- `TeamMember.jira_account_id` field ✅

---

## Estimated Effort

| Section | Tasks | Effort |
|---------|-------|--------|
| 1. TrackedJiraProject Model | 4 | S |
| 2. Jira Client Service | 5 | M |
| 3. Project Selection Views | 4 | M |
| 4. User Matching Service | 3 | S |
| 5. Issue Sync Service | 6 | L |
| 6. Celery Tasks | 4 | M |
| 7. UI Integration | 2 | S |
| **Total** | **28** | **M-L** |

---

## Next Phase Preview

**Phase 3.3: User Matching Resolution**
- Manual matching UI for unmatched users
- Bulk actions for admin
- Exclude option for service accounts/bots

**Phase 3.4: Jira-GitHub Correlation**
- Link JiraIssue to PullRequest via jira_key
- Cross-reference metrics in dashboards
- Issue velocity vs PR throughput
