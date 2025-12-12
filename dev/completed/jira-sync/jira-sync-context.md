# Phase 3.2: Jira Sync - Context & Patterns

**Last Updated:** 2025-12-11
**Status:** Sections 1-5 Complete (GREEN), Section 5 REFACTOR pending

---

## Current Session State

### Active Work
- **Section 5 Issue Sync Service**: GREEN phase COMPLETE, was starting REFACTOR phase when session ended
- 16 tests written and passing for jira_sync.py
- Need to run `tdd-refactorer` agent on Section 5 to complete TDD cycle

### Test Status
- **Total tests:** 776 passing
- **New tests this session:** 69 tests across 5 sections

### Uncommitted Changes
All Phase 3.2 work is uncommitted:
```
M  apps/integrations/admin.py
M  apps/integrations/factories.py
M  apps/integrations/models.py
M  apps/integrations/tests/test_models.py
M  apps/integrations/urls.py
M  apps/integrations/views.py
M  pyproject.toml
M  uv.lock
?? apps/integrations/migrations/0009_trackedjiraproject.py
?? apps/integrations/migrations/0010_rename_tracked_jira_sync_idx_tracked_jira_sync_status_idx_and_more.py
?? apps/integrations/services/jira_client.py
?? apps/integrations/services/jira_sync.py
?? apps/integrations/services/jira_user_matching.py
?? apps/integrations/tests/test_jira_client.py
?? apps/integrations/tests/test_jira_sync.py
?? apps/integrations/tests/test_jira_user_matching.py
?? apps/integrations/tests/test_jira_views_projects.py
?? templates/integrations/jira_projects_list.html
```

---

## Key Implementation Files

### Service Layer (`apps/integrations/services/`)

1. **jira_client.py** - Jira API client with bearer token auth
   - `JiraClientError` - Custom exception
   - `get_jira_client(credential)` - Creates authenticated JIRA instance
   - `get_accessible_projects(credential)` - List projects
   - `get_project_issues(credential, project_key, since=None)` - Fetch issues with JQL

2. **jira_user_matching.py** - User matching by email
   - `get_jira_users(credential)` - Fetch all Jira users
   - `match_jira_user_to_team_member(jira_user, team)` - Email matching
   - `sync_jira_users(team, credential)` - Bulk sync with report

3. **jira_sync.py** - Issue synchronization
   - `JiraSyncError` - Custom exception
   - `_parse_jira_datetime(dt_string)` - Parse ISO datetime
   - `_calculate_cycle_time(created, resolved)` - Hours calculation
   - `_convert_jira_issue_to_dict(issue_data)` - API to model mapping
   - `sync_project_issues(tracked_project, full_sync=False)` - Main sync

### Model (`apps/integrations/models.py`)

**TrackedJiraProject** (BaseTeamModel):
- `integration` - FK to JiraIntegration
- `jira_project_id` - Jira's internal ID
- `jira_project_key` - Project key (e.g., "PROJ")
- `name` - Display name
- `is_active` - Currently tracking
- `last_sync_at` - Last successful sync
- `sync_status` - pending/syncing/complete/error
- `last_sync_error` - Error message if failed

### Views (`apps/integrations/views.py`)

- `jira_projects_list` (lines 912-954) - List projects, show tracked status
- `jira_project_toggle` (lines 957-1011) - Add/remove tracked projects

### URLs (`apps/integrations/urls.py`)

Added to `team_urlpatterns`:
- `jira/projects/` → `jira_projects_list`
- `jira/projects/toggle/` → `jira_project_toggle`

---

## jira-python Library Patterns

### Bearer Token Authentication (Atlassian Cloud)
```python
from jira import JIRA

headers = JIRA.DEFAULT_OPTIONS["headers"].copy()
headers["Authorization"] = f"Bearer {access_token}"
jira = JIRA(
    server=f"https://api.atlassian.com/ex/jira/{cloud_id}",
    options={"headers": headers}
)
```

### Fetching Projects
```python
projects = jira.projects()  # Returns list of Project objects
# Access: project.id, project.key, project.name
```

### JQL Queries
```python
# Full sync
jql = f"project = {key} ORDER BY updated DESC"

# Incremental sync
since_str = since.strftime("%Y-%m-%d %H:%M")
jql = f'project = {key} AND updated >= "{since_str}" ORDER BY updated DESC'

# Fetch with pagination
issues = jira.search_issues(jql, maxResults=False, fields="summary,status,...")
```

### User Search
```python
users = jira.search_users(query="", maxResults=1000)
# Access: user.accountId, user.emailAddress, user.displayName
# Note: emailAddress may not be present on all users
```

---

## Field Mapping (Jira API → JiraIssue model)

| API Field | Model Field | Notes |
|-----------|-------------|-------|
| `key` | `jira_key` | e.g., "PROJ-123" |
| `id` | `jira_id` | Internal Jira ID |
| `fields.summary` | `summary` | Issue title |
| `fields.issuetype.name` | `issue_type` | Bug, Story, etc. |
| `fields.status.name` | `status` | To Do, In Progress, Done |
| `fields.assignee.accountId` | `assignee` | FK lookup via jira_account_id |
| `fields.customfield_10016` | `story_points` | Configurable field ID |
| `fields.created` | `issue_created_at` | ISO datetime string |
| `fields.resolutiondate` | `resolved_at` | ISO datetime string |
| (calculated) | `cycle_time_hours` | resolved - created in hours |

---

## Testing Patterns

### Factory Setup
```python
from apps.integrations.factories import (
    JiraIntegrationFactory,
    TrackedJiraProjectFactory,
)
from apps.metrics.factories import TeamMemberFactory, JiraIssueFactory

class TestJiraSync(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.integration = JiraIntegrationFactory(team=self.team)
        self.tracked_project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
        )
```

### Mocking Jira API
```python
@patch("apps.integrations.services.jira_client.ensure_valid_jira_token")
@patch("apps.integrations.services.jira_client.JIRA")
def test_get_jira_client(self, mock_jira_class, mock_ensure_token):
    mock_ensure_token.return_value = "valid_token"
    mock_jira = MagicMock()
    mock_jira_class.return_value = mock_jira

    result = get_jira_client(self.credential)

    self.assertEqual(result, mock_jira)
```

### Mocking Issue Data
```python
mock_issue = MagicMock()
mock_issue.key = "PROJ-123"
mock_issue.id = "10001"
mock_issue.fields.summary = "Test issue"
mock_issue.fields.issuetype.name = "Story"
mock_issue.fields.status.name = "Done"
mock_issue.fields.assignee.accountId = "user123"
mock_issue.fields.created = "2024-01-01T10:00:00.000+0000"
mock_issue.fields.resolutiondate = "2024-01-02T10:00:00.000+0000"
```

---

## Next Steps

1. **Complete Section 5 REFACTOR phase**
   - Run `tdd-refactorer` agent on jira_sync.py
   - Check lint compliance, type hints

2. **Section 6: Celery Tasks**
   - `sync_jira_project_task` - Single project sync
   - `sync_all_jira_projects_task` - Daily batch sync
   - `sync_jira_users_task` - User matching task
   - Add to Celery Beat schedule

3. **Section 7: UI Integration**
   - Add Jira section to integrations home.html
   - Show connection status and tracked projects

4. **Commit all work**
   - Commit message: "Implement Phase 3.2: Jira Project Sync"
   - 69 new tests, migrations, services, views

---

## Verification Commands

```bash
# Test all Jira-related tests
make test ARGS='apps.integrations.tests.test_jira_client --keepdb'
make test ARGS='apps.integrations.tests.test_jira_sync --keepdb'
make test ARGS='apps.integrations.tests.test_jira_user_matching --keepdb'
make test ARGS='apps.integrations.tests.test_jira_views_projects --keepdb'

# Full test suite
make test ARGS='--keepdb'

# Lint check
make ruff

# Migrations already applied
# 0009_trackedjiraproject.py
# 0010_rename_tracked_jira_sync_idx_tracked_jira_sync_status_idx_and_more.py
```
