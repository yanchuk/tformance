# Onboarding & Integration Fixes Plan

**Last Updated:** 2025-12-29

## Executive Summary

This plan addresses three critical issues discovered during dev2.ianchuk.com testing:
1. **Onboarding flow break**: User redirected to dashboard after org selection instead of repo selection
2. **Repo page readability**: Repo names/descriptions use hardcoded grey text, barely visible
3. **Sync progress missing**: No visual feedback when triggering historical data sync

All issues impact the first-time user experience and need immediate attention.

---

## Issue 1: Onboarding Flow Bypass

### Current State

After selecting a GitHub organization, users should proceed to repository selection (`/onboarding/repos/`). Instead, they're being redirected to the dashboard (`/app/`).

### Root Causes Identified

1. **`web:home` auto-redirect** (`apps/web/views.py:47-59`):
   - Once a team exists, visiting `/` auto-redirects to dashboard
   - If user navigates away during onboarding, they can't return to repo selection

2. **Team existence check** (`apps/onboarding/views.py:94-97`):
   ```python
   def select_organization(request):
       if request.user.teams.exists():
           return redirect("web:home")  # Bypasses repo selection!
   ```
   - Team is created AFTER org selection but BEFORE repo selection
   - Any re-visit to onboarding redirects to dashboard

3. **No onboarding state tracking**:
   - No session/model flag to indicate user is mid-onboarding
   - No way to distinguish "completed onboarding" vs "started but didn't finish"

### Proposed Solution

**Option A: Onboarding State Flag (Recommended)**
- Add `onboarding_complete` field to Team model
- Check this flag instead of just `teams.exists()`
- Set flag to True only when user reaches "complete" page
- Allows users to resume onboarding if they leave mid-flow

**Option B: Session-based State**
- Store onboarding step in session (`ONBOARDING_STEP`)
- Check session before redirecting
- Less persistent but simpler

**Option C: TrackedRepository Check**
- Don't redirect to dashboard if user has team but NO tracked repos
- Check: `if request.user.teams.exists() and team.tracked_repositories.exists()`

### Recommended Approach: Hybrid

1. Add `onboarding_complete` boolean to Team model (Option A)
2. In `web:home`, check flag before redirecting to dashboard
3. In `select_repos`, allow access even if team exists (check flag instead)

---

## Issue 2: Repo Names/Descriptions Not Visible

### Current State

On `/app/integrations/github/repos/`, repo names appear in very light grey (`text-slate-200`) and descriptions in even lighter grey (`text-slate-400`). Both are nearly invisible against the dark background.

### Root Cause

Templates use **hardcoded Tailwind Slate classes** instead of the semantic DaisyUI theme system:

| Location | Current (Wrong) | Should Be |
|----------|-----------------|-----------|
| `repo_card.html:4` | `text-slate-200` | `text-base-content` |
| `repo_card.html:7` | `text-slate-400` | `text-base-content/80` |
| `member_row.html:12` | `text-slate-200` | `text-base-content` |
| `member_row.html:16,20` | `text-slate-400` | `text-base-content/80` |
| `github_repos.html:10,42` | `text-slate-500` | `text-base-content/70` |
| `github_members.html:10,54` | `text-slate-500` | `text-base-content/70` |

### Proposed Solution

Replace all `text-slate-*` classes with semantic DaisyUI classes per the design system:

| Current | Replace With | Use Case |
|---------|--------------|----------|
| `text-slate-200` | `text-base-content` | Primary text |
| `text-slate-300` | `text-base-content/80` | Secondary text |
| `text-slate-400` | `text-base-content/80` | Descriptions |
| `text-slate-500` | `text-base-content/70` | Muted text |

---

## Issue 3: Historical Data Sync Progress Not Showing

### Current State

When clicking the sync icon on a repository, no progress indicator appears. Users don't know if sync is happening.

### Root Causes Identified

1. **Synchronous sync call** (`views/github.py:461-491`):
   ```python
   def github_repo_sync(request, repo_id):
       result = github_sync.sync_repository_history(tracked_repo)  # BLOCKS!
       return JsonResponse(result)
   ```
   - Sync runs inline, blocking the HTTP request
   - No Celery task queued

2. **`sync_status` never updated**:
   - Manual sync doesn't set `sync_status = "syncing"`
   - HTMX polling condition (`if repo.sync_status == 'syncing'`) is never true
   - Progress template is never shown

3. **Progress fields not populated**:
   - `sync_progress`, `sync_prs_total`, `sync_prs_completed` never updated during manual sync

4. **Immediate JSON response**:
   - Returns `JsonResponse` with result (or times out)
   - No visual feedback to user

### Proposed Solution

**Convert to Async Task Pattern:**

1. Create new Celery task `sync_repository_manual_task`:
   ```python
   @celery_app.task
   def sync_repository_manual_task(repo_id):
       tracked_repo = TrackedRepository.objects.get(id=repo_id)
       tracked_repo.sync_status = "syncing"
       tracked_repo.sync_started_at = timezone.now()
       tracked_repo.save()

       try:
           result = github_sync.sync_repository_history(tracked_repo)
           tracked_repo.sync_status = "complete"
       except Exception as e:
           tracked_repo.sync_status = "error"
           tracked_repo.last_sync_error = str(e)
       finally:
           tracked_repo.save()
   ```

2. Update `github_repo_sync` view:
   ```python
   def github_repo_sync(request, repo_id):
       tracked_repo = get_object_or_404(...)
       sync_repository_manual_task.delay(repo_id)  # Non-blocking
       tracked_repo.sync_status = "syncing"
       tracked_repo.save()
       # Return partial that shows "Starting sync..."
       return render(request, "integrations/partials/sync_progress.html", {"repo": tracked_repo})
   ```

3. Change HTMX attributes in `repo_card.html`:
   - Change `hx-swap="none"` to `hx-swap="innerHTML"`
   - Target the sync status container

4. Add progress updates during sync (optional enhancement):
   - Update `sync_prs_completed` after each PR processed
   - Enables real progress bar

---

## Implementation Phases

### Phase 1: Critical Fixes (Day 1)

**1.1 Fix Repo Styling** [Effort: S]
- Update `repo_card.html` text colors
- Update `member_row.html` text colors
- Update `github_repos.html` and `github_members.html` back links/footers
- Test on dev2.ianchuk.com

**1.2 Add Onboarding State Tracking** [Effort: M]
- Add `onboarding_complete` field to Team model
- Create migration
- Update `_create_team_from_org` to set flag False initially
- Update `onboarding_complete` view to set flag True
- Update guards in `select_organization` and `select_repos`

### Phase 2: UX Improvements (Day 2)

**2.1 Fix Onboarding Flow** [Effort: M]
- Update `web:home` to check `onboarding_complete` before dashboard redirect
- Allow users with incomplete onboarding to reach repo selection
- Add "Resume Onboarding" CTA in dashboard for incomplete teams

**2.2 Async Manual Sync** [Effort: M]
- Create `sync_repository_manual_task` Celery task
- Update `github_repo_sync` view to queue task
- Update HTMX swap behavior for immediate feedback
- Test progress polling

### Phase 3: Polish (Day 3)

**3.1 Progress Updates During Sync** [Effort: L]
- Add progress callback to sync service
- Update `sync_prs_completed` during sync
- Real-time progress bar

**3.2 Testing & Deployment** [Effort: M]
- Write tests for onboarding flow
- Test complete flow on dev2
- Deploy to production

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Migration breaks existing teams | High | Low | Make `onboarding_complete` default to True for existing teams |
| Async sync causes race conditions | Medium | Medium | Add locking/status checks before queueing |
| Text color changes affect other pages | Low | Low | Only modify integration templates |
| Celery task failures silent | Medium | Low | Add error logging, status tracking |

---

## Success Metrics

1. **Onboarding Completion Rate**: Users who start onboarding successfully reach repo selection
2. **Repo Page Readability**: All text meets WCAG AA contrast standards
3. **Sync Feedback**: Users see progress indication within 2 seconds of clicking sync
4. **No Regressions**: All existing tests pass

---

## Required Resources

- Celery worker running for async sync
- Database migration for `onboarding_complete` field
- Access to dev2.ianchuk.com for testing
