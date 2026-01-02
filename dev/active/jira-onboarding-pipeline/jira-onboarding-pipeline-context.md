# Jira Onboarding Pipeline - Context

**Last Updated**: 2026-01-01

---

## Key Files to Modify

### Phase 1: Core Pipeline
| File | Lines | Purpose |
|------|-------|---------|
| `apps/integrations/onboarding_pipeline.py` | End of file | Add Jira pipeline functions |

### Phase 2: View Integration
| File | Lines | Purpose |
|------|-------|---------|
| `apps/onboarding/views.py` | 531-622 | Modify `select_jira_projects` to trigger pipeline |
| `apps/onboarding/views.py` | End of file | Add `jira_sync_status` view |
| `apps/onboarding/urls.py` | After line 18 | Add URL pattern |

### Phase 3: Jira Metrics
| File | Lines | Purpose |
|------|-------|---------|
| `apps/metrics/services/dashboard_service.py` | End of file | Add `get_jira_sprint_metrics`, `get_pr_jira_correlation` |

### Phase 4: Insights Integration
| File | Lines | Purpose |
|------|-------|---------|
| `apps/metrics/services/insight_llm.py` | In `gather_insight_data` | Add Jira data to return dict |
| `apps/metrics/prompts/templates/insight/user.jinja2` | End of file | Add Jira section |

### Phase 5: UI
| File | Lines | Purpose |
|------|-------|---------|
| `templates/onboarding/select_jira_projects.html` | After form | Add Alpine.js progress indicator |

---

## Files to Create (Tests First - TDD)

| File | Purpose |
|------|---------|
| `apps/integrations/tests/test_jira_onboarding_pipeline.py` | Pipeline task tests |
| `apps/onboarding/tests/test_jira_sync_trigger.py` | View integration tests |
| `apps/metrics/tests/services/test_jira_metrics.py` | Jira metrics tests |

---

## Key Decisions Log

### 2026-01-01: Architecture Decision
**Decision**: Parallel pipeline (not integrated into GitHub Phase 1/Phase 2)
**Rationale**:
- Jira is optional during onboarding
- Jira sync should not block dashboard access
- No LLM analysis needed for Jira issues
- Simpler error handling (Jira failure doesn't affect GitHub pipeline)

### 2026-01-01: UI Approach
**Decision**: Inline indicator (not dedicated page)
**Rationale**:
- Don't block navigation to Slack step
- User can continue onboarding while Jira syncs
- Simpler implementation

### 2026-01-01: Error Handling
**Decision**: Silent retry
**Rationale**:
- Log errors for debugging
- Retry in nightly batch job
- Don't bother user with transient failures

### 2026-01-01: Insights Scope
**Decision**: Include Jira insights in this work
**Rationale**:
- Full value requires Jira metrics
- Sprint metrics and PR correlation are high-value
- Already have data model and sync in place

---

## Existing Services Reference

### Jira Sync Service
**File**: `apps/integrations/services/jira_sync.py`
```python
def sync_project_issues(tracked_project: TrackedJiraProject, full_sync: bool = False) -> dict:
    """Sync issues from a tracked Jira project.
    Returns: {"issues_created": int, "issues_updated": int, "errors": int}
    """
```

### Jira User Matching
**File**: `apps/integrations/services/jira_user_matching.py`
```python
def sync_jira_users(team, credential) -> dict:
    """Sync Jira users to TeamMembers by email matching.
    Returns: {"matched_count": int, "unmatched_count": int, "unmatched_users": list}
    """
```

### Existing Jira Tasks
**File**: `apps/integrations/tasks.py`
```python
@shared_task
def sync_jira_project_task(project_id: int) -> dict:
    """Sync a single tracked Jira project."""

@shared_task
def sync_jira_users_task(team_id: int) -> dict:
    """Sync Jira users to TeamMembers for a team."""
```

---

## Models Reference

### TrackedJiraProject
**File**: `apps/integrations/models.py:378-459`
- `jira_project_id` - Jira project ID
- `jira_project_key` - e.g., "PROJ"
- `sync_status` - pending/syncing/completed/error
- `last_sync_at` - timestamp
- `last_sync_error` - error message

### JiraIssue
**File**: `apps/metrics/models/jira.py`
- `jira_key` - e.g., "PROJ-123"
- `assignee` - FK to TeamMember
- `story_points` - decimal
- `cycle_time_hours` - calculated
- `resolved_at` - timestamp
- `related_prs` - property returning linked PRs

### PullRequest.jira_key
**File**: `apps/metrics/models/github.py:253`
- Extracted from PR title/branch during GitHub sync
- Pattern: `PROJ-123`

---

## Test Patterns to Follow

### Factory Usage
```python
from apps.integrations.factories import (
    JiraIntegrationFactory,
    TrackedJiraProjectFactory,
    IntegrationCredentialFactory,
)
from apps.metrics.factories import (
    TeamFactory,
    TeamMemberFactory,
    JiraIssueFactory,
    PullRequestFactory,
)
```

### Mocking Jira API
```python
@patch("apps.integrations.services.jira_sync.sync_project_issues")
def test_sync_calls_service(self, mock_sync):
    mock_sync.return_value = {"issues_created": 5, "issues_updated": 2, "errors": 0}
    # ... test code ...
```

### Celery Task Testing
```python
# With CELERY_TASK_ALWAYS_EAGER = True in test settings
result = sync_jira_projects_onboarding(team.id, [project.id])
assert result["synced"] == 1
```

---

## URL Patterns

### Current Jira URLs
```python
# apps/onboarding/urls.py
path("jira/", views.connect_jira, name="connect_jira"),
path("jira/projects/", views.select_jira_projects, name="select_jira_projects"),
```

### New URL to Add
```python
path("jira/sync-status/", views.jira_sync_status, name="jira_sync_status"),
```

---

## Environment Notes

- **Celery**: Required for async task execution
- **Redis**: Required as message broker
- **Jira API**: Uses `jira-python` library via `apps/integrations/services/jira_client.py`
- **Test Mode**: `CELERY_TASK_ALWAYS_EAGER=True` runs tasks synchronously
