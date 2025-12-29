# Onboarding Sync & UX Fixes - Context

**Last Updated: 2025-12-29**

## Key Files

### Primary Files to Modify
| File | Purpose | Key Lines |
|------|---------|-----------|
| `apps/integrations/tasks.py` | Celery sync tasks | 2044-2094 (sync_historical_data_task) |
| `apps/onboarding/views.py` | Onboarding views | 286-311 (select_repos), 315-338 (sync_progress) |
| `templates/onboarding/select_repos.html` | Repo selection UI | Full file - needs loading state |
| `templates/onboarding/sync_progress.html` | Sync progress UI | 105-214 (JavaScript polling) |

### Related Files (Reference Only)
| File | Purpose |
|------|---------|
| `apps/integrations/services/github_sync.py` | Low-level sync logic |
| `apps/integrations/services/member_sync.py` | Member sync service |
| `apps/utils/fields.py` | EncryptedTextField implementation |
| `apps/integrations/models.py` | IntegrationCredential model |

## Key Decisions

### D1: Debug Before Fix
**Decision**: Add logging first to understand Celery failure mode
**Rationale**: Multiple possible causes - need to identify actual root cause

### D2: Keep Existing Architecture
**Decision**: Fix within current Celery task framework
**Rationale**: Architecture is sound, likely a specific bug not design issue

### D3: Progressive Enhancement for Loading
**Decision**: Use HTMX for async repo loading
**Rationale**: Already used in project, minimal JS, works without JS

### D4: Fallback Sync Mechanism
**Decision**: Add manual sync button as fallback
**Rationale**: Ensures users can complete onboarding even if Celery has issues

## Dependencies

### External
- Celery with Redis broker
- celery-progress package
- PyGithub library

### Internal
- `apps/integrations/tasks.py` - Task definitions
- `apps/utils/fields.py` - EncryptedTextField
- `apps/integrations/services/encryption.py` - encrypt/decrypt functions

## Current Flow Analysis

### Onboarding Flow
```
1. /onboarding/start/ → Connect GitHub
2. /tformance_auth/github_callback → OAuth complete
3. /onboarding/select-org/ → Create team + sync members
4. /onboarding/select-repos/ → Select repos (ISSUE: slow API call)
5. /onboarding/sync/ → Show progress (ISSUE: task may fail)
6. /onboarding/jira/ → Connect Jira (optional)
7. /onboarding/slack/ → Connect Slack (optional)
8. /onboarding/complete/ → Done
```

### Sync Flow
```
1. User selects repos → POST /onboarding/select-repos/
2. Creates TrackedRepository records
3. Calls sync_historical_data_task.delay(team_id, repo_ids)
4. Redirects to /onboarding/sync/
5. Page loads, calls POST /onboarding/sync/start/
6. Task ID returned, polls /celery-progress/{task_id}/
7. Progress updates shown
8. On complete, shows "Continue" button
```

## API Reference

### GitHub Repo Fetch (Slow Operation)
```python
# apps/onboarding/views.py line 289
repos = github_oauth.get_organization_repositories(
    integration.credential.access_token,
    integration.organization_slug,
    exclude_archived=True,
)
```
- Takes 2-5 seconds for large orgs
- Called synchronously on page load
- No loading indicator currently

### Celery Task Start
```python
# apps/onboarding/views.py line 358
task = sync_historical_data_task.delay(team.id, repo_ids)
return JsonResponse({"task_id": task.id})
```

### Task Token Access (Potential Issue)
```python
# apps/integrations/tasks.py line 2093
github_token = integration.credential.access_token
```
- Uses EncryptedTextField descriptor
- May have issues in Celery process context

## Testing Strategy

### Unit Tests
- Mock Celery task execution
- Test token access in task context
- Test error handling paths

### Integration Tests
- Test full sync flow end-to-end
- Verify PRs created after sync
- Test loading states render correctly

## Code Patterns

### HTMX Loading Pattern (from existing code)
```html
<!-- Example from other templates -->
<div hx-get="/api/data"
     hx-trigger="load"
     hx-indicator="#loading">
  <span id="loading" class="htmx-indicator">
    <i class="fa-solid fa-spinner fa-spin"></i>
    Loading...
  </span>
</div>
```

### Celery Task Error Pattern
```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def my_task(self, arg):
    try:
        # work
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f"Task failed after max retries: {exc}")
            return {"status": "error", "error": str(exc)}
```

## Notes

- The `member_sync.sync_github_members(team)` call in `_create_team_from_org` (line 179) works synchronously but the Celery version fails
- The EncryptedTextField uses a descriptor pattern that auto-decrypts on access - verify this works in Celery worker process
- The `sync_progress.html` JavaScript assumes task will eventually complete - needs timeout/error handling
