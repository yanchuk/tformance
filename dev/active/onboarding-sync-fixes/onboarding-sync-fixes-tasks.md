# Onboarding Sync & UX Fixes - Tasks

**Last Updated: 2025-12-29**

## Task Checklist

### Phase 1: Debug & Fix Celery Task Execution

- [x] **1.1 Add comprehensive logging to sync tasks** ✅
  - Added `[SYNC_TASK]` prefixed logs at task entry with team_id, repo_ids, task_id
  - Added token access logging (prefix + length, not full token)
  - Added per-repo sync start/complete logging
  - Added final result summary logging

- [x] **1.2 Fix token access in Celery context** ✅
  - Added explicit try/catch around `credential.access_token`
  - Added empty token check with clear error
  - Added detailed error logging with exception type

- [x] **1.3 Add retry mechanism for failed syncs** ✅
  - Added "Retry Sync" button to sync_progress page
  - Button triggers new sync via existing endpoint
  - Error state shown with skip option

- [ ] **1.4 Verify sync works in test**
  - Run sync_historical_data_task synchronously in test
  - Verify PR records created
  - Verify member records created

### Phase 2: Add Loading States to Onboarding

- [x] **2.1 Add loading state to repos page** ✅
  - Split view: `select_repos` (page shell) + `fetch_repos` (HTMX endpoint)
  - Created `/onboarding/repos/fetch/` endpoint
  - Added loading spinner with "Fetching repositories from GitHub..."
  - Created `partials/repos_error.html` for error handling with retry

- [x] **2.2 Improve sync progress error handling** ✅
  - Added 45-second stall detection (configurable via `stallTimeoutMs`)
  - Added "Sync May Have Stalled" message section
  - Added retry button and skip option
  - Added FAILURE/REVOKED state detection

- [ ] **2.3 Add real-time status from DB**
  - Create `/onboarding/sync/status/` endpoint
  - Return TrackedRepository sync_status values
  - Compare with Celery task state
  - Show discrepancy to user

### Phase 3: Tests

- [x] **3.1 Test loading states** ✅
  - Added `TestSelectReposPageLoading` with 3 tests
  - Tests verify HTMX trigger, loading indicator, no API call on initial load
  - Updated existing tests to use `fetch_repos` endpoint

- [ ] **3.2 Test error handling**
  - Test sync page shows error state on failure
  - Test retry button works

---

## Summary of Changes

### Files Modified

| File | Changes |
|------|---------|
| `apps/integrations/tasks.py` | Added comprehensive `[SYNC_TASK]` logging at entry, token access, per-repo, and completion |
| `apps/onboarding/views.py` | Added `fetch_repos` HTMX endpoint, removed sync repo fetch from initial page load |
| `apps/onboarding/urls.py` | Added `repos/fetch/` URL pattern |
| `templates/onboarding/select_repos.html` | Replaced repo list with HTMX loading pattern |
| `templates/onboarding/partials/repos_list.html` | New partial for repo list (loaded via HTMX) |
| `templates/onboarding/partials/repos_error.html` | New partial for error state with retry |
| `templates/onboarding/sync_progress.html` | Added error/stalled section, stall detection JS, retry button |
| `apps/onboarding/tests/test_repo_prioritization.py` | Updated tests to use `fetch_repos` endpoint |
| `apps/onboarding/tests/test_ux_improvements.py` | Updated search input test to use `fetch_repos` endpoint |

### Key Features Added

1. **Loading State for Repo Selection**: Shows spinner while fetching repos from GitHub API
2. **Stall Detection**: 45-second timeout triggers error state if sync makes no progress
3. **Retry Mechanism**: Users can retry failed/stalled syncs without page reload
4. **Comprehensive Logging**: Celery task now logs detailed progress for debugging

---

## Quick Commands

### Check Celery Status
```bash
# Check if workers are running
pgrep -fl celery

# Check Redis connection
redis-cli ping
```

### Manual Sync Commands
```bash
# Sync members for a team
.venv/bin/python manage.py shell -c "
from apps.integrations.models import GitHubIntegration
from apps.integrations.services.member_sync import sync_github_members
gh = GitHubIntegration.objects.get(organization_slug='railsware')
result = sync_github_members(team=gh.team, access_token=gh.credential.access_token, org_slug=gh.organization_slug)
print(result)
"

# Sync repos for a team
.venv/bin/python manage.py shell -c "
from apps.integrations.models import TrackedRepository
from apps.integrations.services.github_sync import sync_repository_history
repo = TrackedRepository.objects.filter(full_name='railsware/falcon').first()
result = sync_repository_history(repo)
print(result)
"
```

### Test Celery Task Directly
```bash
.venv/bin/python manage.py shell -c "
from apps.integrations.tasks import sync_historical_data_task
from apps.teams.models import Team
from apps.integrations.models import TrackedRepository

team = Team.objects.get(name='railsware')
repo_ids = list(TrackedRepository.objects.filter(team=team).values_list('id', flat=True))
print(f'Team: {team.name}, Repos: {repo_ids}')

# Run synchronously (not via Celery)
result = sync_historical_data_task(team.id, repo_ids)
print(f'Result: {result}')
"
```

---

## Progress Notes

### Session 1 (2025-12-29)
**Findings:**
- Member sync works when called directly (`sync_github_members()`)
- Celery task queued but didn't execute
- Token decryption via EncryptedTextField works (tested manually)
- 131 members synced manually
- PR sync still pending

**Next Steps:**
1. Add logging to Celery tasks to trace failure point
2. Add loading state to select_repos page
3. Add error handling to sync_progress page

---

## File Changes Tracking

| File | Status | Changes |
|------|--------|---------|
| `apps/integrations/tasks.py` | Pending | Add logging, error handling |
| `apps/onboarding/views.py` | Pending | Split repo fetch, add status endpoint |
| `templates/onboarding/select_repos.html` | Pending | Add HTMX loading |
| `templates/onboarding/sync_progress.html` | Pending | Add error handling |
