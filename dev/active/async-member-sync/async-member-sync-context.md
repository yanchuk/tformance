# Async GitHub Member Sync - Context

**Last Updated: 2025-12-29**

## Key Files

### Views (to modify)

| File | Lines | Purpose |
|------|-------|---------|
| `apps/integrations/views/github.py` | 191-235 | `github_members_sync` - manual sync button |
| `apps/integrations/views/helpers.py` | 152-172 | `_sync_github_members_after_connection` |

### Models

| File | Lines | Purpose |
|------|-------|---------|
| `apps/integrations/models.py` | 82-142 | `GitHubIntegration` - add member sync fields |

### Tasks (existing)

| File | Lines | Purpose |
|------|-------|---------|
| `apps/integrations/tasks.py` | 492-539 | `sync_github_members_task` - reuse this |

### Templates

| File | Purpose |
|------|---------|
| `apps/integrations/templates/integrations/github_members.html` | Members page with Sync Now button |
| `apps/integrations/templates/integrations/partials/member_sync_progress.html` | NEW: Progress partial |

### Tests

| File | Lines | Purpose |
|------|-------|---------|
| `apps/integrations/tests/test_views.py` | 472-510 | Member sync view tests (update to mock .delay) |

---

## Key Decisions

### Decision 1: Reuse Existing Task vs. Create New

**Choice**: Reuse `sync_github_members_task`

**Rationale**:
- Task already exists with retry logic, error handling
- Just needs status field updates added
- Avoids code duplication

### Decision 2: Separate Member Sync Status Fields

**Choice**: Add `member_sync_status`, `member_sync_started_at`, etc.

**Rationale**:
- Existing `sync_status` field is used for repo sync
- Member sync is independent operation
- Allows tracking both sync types simultaneously

### Decision 3: Progress Polling Interval

**Choice**: 3 seconds

**Rationale**:
- Member sync is typically 5-30 seconds
- 3s provides responsive updates without excessive requests
- Consistent with repo sync polling (5s)

### Decision 4: Post-Connection Behavior

**Choice**: Queue task + show "syncing in background" message

**Rationale**:
- Don't block onboarding flow
- User can proceed immediately
- Members will appear when sync completes

---

## Dependencies

### Internal

- `apps/integrations/services/member_sync.py` - Core sync logic (unchanged)
- `apps/integrations/services/github_graphql_sync.py` - GraphQL sync (unchanged)
- Celery worker running for task execution

### External

- GitHub API (REST or GraphQL)
- Redis for Celery broker

---

## Reference: Existing Sync Status Constants

```python
# apps/integrations/constants.py
SYNC_STATUS_PENDING = "pending"
SYNC_STATUS_SYNCING = "syncing"
SYNC_STATUS_COMPLETE = "complete"
SYNC_STATUS_ERROR = "error"

SYNC_STATUS_CHOICES = [
    (SYNC_STATUS_PENDING, "Pending"),
    (SYNC_STATUS_SYNCING, "Syncing"),
    (SYNC_STATUS_COMPLETE, "Complete"),
    (SYNC_STATUS_ERROR, "Error"),
]
```

---

## Reference: Similar Pattern (Repo Sync)

Just implemented for `github_repo_sync`:

```python
# apps/integrations/views/github.py:461-501
@login_and_team_required
def github_repo_sync(request, repo_id):
    tracked_repo = TrackedRepository.objects.get(team=team, id=repo_id)

    # Set status to syncing immediately
    tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_SYNCING
    tracked_repo.sync_started_at = timezone.now()
    tracked_repo.save(update_fields=["sync_status", "sync_started_at"])

    # Queue async task
    sync_repository_manual_task.delay(repo_id)

    # Return progress partial
    return render(request, "integrations/partials/sync_progress.html", {"repo": tracked_repo})
```

Follow this exact pattern for member sync.

---

## URL Pattern

```python
# apps/integrations/urls.py - add:
path("github/members/sync/progress/", views.github_members_sync_progress, name="github_members_sync_progress"),
```

---

## Test Mocking Pattern

```python
# Before (mocks sync function)
@patch("apps.integrations.services.member_sync.sync_github_members")
def test_github_members_sync_triggers_sync_and_shows_results(self, mock_sync):
    mock_sync.return_value = {"created": 3, "updated": 2, ...}
    ...

# After (mocks Celery task.delay)
@patch("apps.integrations.tasks.sync_github_members_task.delay")
def test_github_members_sync_queues_celery_task(self, mock_task_delay):
    response = self.client.post(...)
    mock_task_delay.assert_called_once_with(integration.id)
```
