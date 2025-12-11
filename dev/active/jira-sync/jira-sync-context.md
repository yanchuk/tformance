# Phase 3.2: Jira Sync - Context Document

**Last Updated:** 2025-12-11

---

## Key Files Reference

### Files to Create

| File | Purpose |
|------|---------|
| `apps/integrations/services/jira_client.py` | Jira API client using jira-python |
| `apps/integrations/services/jira_sync.py` | Issue sync logic |
| `apps/integrations/services/jira_user_matching.py` | User matching service |
| `apps/integrations/migrations/0009_trackedjiraproject.py` | New model migration |
| `apps/integrations/tests/test_jira_client.py` | Client tests |
| `apps/integrations/tests/test_jira_sync.py` | Sync service tests |
| `apps/integrations/tests/test_jira_views_projects.py` | Project selection view tests |
| `templates/integrations/jira_projects.html` | Project selection template |

### Files to Modify

| File | Changes |
|------|---------|
| `apps/integrations/models.py` | Add TrackedJiraProject model |
| `apps/integrations/views.py` | Add project selection views |
| `apps/integrations/urls.py` | Add project URL patterns |
| `apps/integrations/admin.py` | Register TrackedJiraProject |
| `apps/integrations/factories.py` | Add TrackedJiraProjectFactory |
| `apps/integrations/tasks.py` | Add Jira sync tasks |
| `templates/integrations/home.html` | Show Jira status |

### Existing Files to Reference

| File | Patterns to Reuse |
|------|-------------------|
| `apps/integrations/services/github_sync.py` | Sync service structure |
| `apps/integrations/services/jira_oauth.py` | `ensure_valid_jira_token()` |
| `apps/integrations/tasks.py` | Celery task patterns |
| `apps/integrations/models.py` | TrackedRepository as template |
| `apps/metrics/models.py` | JiraIssue model structure |

---

## Architectural Decisions

### Decision 1: Use jira-python Library

**Choice:** Use `jira` package instead of raw API calls

**Reasoning:**
- Automatic pagination handling
- Proper authentication management
- Well-documented, actively maintained
- Handles JQL queries cleanly
- Type hints available

**Implementation:**
```python
from jira import JIRA

def get_jira_client(credential):
    token = ensure_valid_jira_token(credential)
    jira_integration = credential.jira_integration

    return JIRA(
        server=f"https://api.atlassian.com/ex/jira/{jira_integration.cloud_id}",
        options={"headers": {"Authorization": f"Bearer {token}"}}
    )
```

### Decision 2: TrackedJiraProject Model

**Choice:** Create separate model similar to TrackedRepository

**Reasoning:**
- Consistent with GitHub pattern
- Allows per-project sync status tracking
- Enables selective project tracking
- Supports future features (webhooks, etc.)

### Decision 3: User Matching by Email

**Choice:** Primary matching by email, display name fallback

**Reasoning:**
- Email is most reliable identifier across systems
- Same pattern used for GitHub user matching
- Display name as backup for edge cases
- Unmatched users logged for admin review

### Decision 4: Incremental Sync with JQL

**Choice:** Use JQL `updated >= "{date}"` for incremental sync

**Reasoning:**
- Efficient - only fetches changed issues
- Jira supports date filtering natively
- Similar to GitHub's `since` parameter pattern

---

## API Reference

### Jira REST API v3 (via jira-python)

**Base URL Pattern:**
```
https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/
```

### Key Endpoints

**List Projects:**
```python
jira = get_jira_client(credential)
projects = jira.projects()
# Returns list of Project objects
```

**Search Issues (JQL):**
```python
issues = jira.search_issues(
    jql_str='project = PROJ AND updated >= "2024-01-01"',
    maxResults=100,
    startAt=0,
    fields='summary,status,issuetype,assignee,created,resolutiondate,customfield_10016'
)
```

**Get Issue Details:**
```python
issue = jira.issue('PROJ-123')
# Access fields: issue.fields.summary, issue.fields.status.name, etc.
```

**Search Users:**
```python
users = jira.search_users(query='', maxResults=1000)
# Returns users with access to the instance
```

### Field Mapping

| Jira API Field | JiraIssue Model Field |
|----------------|----------------------|
| `key` | `jira_key` |
| `id` | `jira_id` |
| `fields.summary` | `summary` |
| `fields.issuetype.name` | `issue_type` |
| `fields.status.name` | `status` |
| `fields.assignee.accountId` | `assignee` (FK via jira_account_id) |
| `fields.customfield_10016` | `story_points` |
| `fields.sprint[0].id` | `sprint_id` |
| `fields.sprint[0].name` | `sprint_name` |
| `fields.created` | `issue_created_at` |
| `fields.resolutiondate` | `resolved_at` |

### Sprint Field Format

Sprint data comes as a list of sprint objects:
```python
# Jira returns sprint as complex object
sprint = issue.fields.sprint  # List of Sprint objects or None
if sprint:
    sprint_id = str(sprint[0].id)
    sprint_name = sprint[0].name
```

### Story Points Custom Field

Story points location varies by Jira instance. Common field IDs:
- `customfield_10016` (most common)
- `customfield_10004`
- `customfield_10034`

**Configurable approach:** Store field ID on JiraIntegration or TrackedJiraProject.

---

## Error Handling

### Common Jira API Errors

| Error | Cause | Handling |
|-------|-------|----------|
| 401 Unauthorized | Token expired | `ensure_valid_jira_token()` handles this |
| 403 Forbidden | No access to resource | Log and skip project/issue |
| 404 Not Found | Project/issue deleted | Remove from tracked, log warning |
| 429 Rate Limited | Too many requests | Retry with backoff |

### Retry Strategy

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_jira_project_task(self, project_id):
    try:
        result = sync_project_issues(tracked_project)
        return result
    except Exception as exc:
        countdown = self.default_retry_delay * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
```

---

## Testing Patterns

### Mocking jira-python

```python
from unittest.mock import MagicMock, patch

@patch('apps.integrations.services.jira_client.JIRA')
def test_get_accessible_projects(self, mock_jira_class):
    # Create mock JIRA instance
    mock_jira = MagicMock()
    mock_jira_class.return_value = mock_jira

    # Mock projects response
    mock_project = MagicMock()
    mock_project.id = '10001'
    mock_project.key = 'PROJ'
    mock_project.name = 'Test Project'
    mock_jira.projects.return_value = [mock_project]

    # Test
    projects = get_accessible_projects(self.credential)

    self.assertEqual(len(projects), 1)
    self.assertEqual(projects[0]['key'], 'PROJ')
```

### Factory for TrackedJiraProject

```python
class TrackedJiraProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrackedJiraProject

    team = factory.SubFactory(TeamFactory)
    integration = factory.SubFactory(
        JiraIntegrationFactory,
        team=factory.SelfAttribute('..team')
    )
    jira_project_id = factory.Sequence(lambda n: f'1000{n}')
    jira_project_key = factory.Sequence(lambda n: f'PROJ{n}')
    name = factory.Sequence(lambda n: f'Project {n}')
    is_active = True
    sync_status = 'pending'
```

---

## Verification Commands

```bash
# Add jira package
uv add jira

# Run all tests
make test ARGS='--keepdb'

# Run Jira-specific tests
make test ARGS='apps.integrations.tests.test_jira_client --keepdb'
make test ARGS='apps.integrations.tests.test_jira_sync --keepdb'

# Check migrations
make migrations
make migrate

# Lint check
make ruff
```

---

## Environment Variables

No new environment variables required.

Existing (from Phase 3.1):
- `JIRA_CLIENT_ID` - OAuth client ID
- `JIRA_CLIENT_SECRET` - OAuth client secret

---

## Integration Points

### From Phase 3.1 (Complete)

| Component | Usage |
|-----------|-------|
| `ensure_valid_jira_token(credential)` | Call before every API request |
| `JiraIntegration.cloud_id` | Build API base URL |
| `IntegrationCredential` | OAuth tokens storage |

### To Phase 3.3 (Future)

| Component | Purpose |
|-----------|---------|
| Unmatched user list | Input for manual matching UI |
| `TeamMember.jira_account_id` | Pre-populated for matched users |

### To Dashboards (Phase 4)

| Data | Metric |
|------|--------|
| `JiraIssue.story_points` | Velocity charts |
| `JiraIssue.cycle_time_hours` | Issue lead time |
| `JiraIssue.resolved_at` | Resolution trends |
| `JiraIssue + PullRequest.jira_key` | Issue ↔ PR correlation |

---

## Code Style Notes

### Service Function Pattern

```python
def sync_project_issues(tracked_project, full_sync=False):
    """Sync issues from a tracked Jira project.

    Args:
        tracked_project: TrackedJiraProject instance
        full_sync: If True, sync all issues; if False, only since last_sync_at

    Returns:
        Dict with sync results: issues_synced, issues_updated, errors

    Raises:
        JiraOAuthError: If token refresh fails
    """
```

### Model Pattern (from TrackedRepository)

```python
class TrackedJiraProject(BaseTeamModel):
    # Import sync status constants
    SYNC_STATUS_PENDING = SYNC_STATUS_PENDING
    SYNC_STATUS_SYNCING = SYNC_STATUS_SYNCING
    SYNC_STATUS_COMPLETE = SYNC_STATUS_COMPLETE
    SYNC_STATUS_ERROR = SYNC_STATUS_ERROR
    SYNC_STATUS_CHOICES = SYNC_STATUS_CHOICES

    # ... fields ...

    class Meta:
        ordering = ['name']
        verbose_name = 'Tracked Jira Project'
        verbose_name_plural = 'Tracked Jira Projects'
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'jira_project_id'],
                name='unique_team_jira_project'
            )
        ]
```
