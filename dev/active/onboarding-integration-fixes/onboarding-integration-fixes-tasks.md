# Onboarding & Integration Fixes - Tasks

**Last Updated:** 2025-12-29

## Overview

Three issues to fix:
1. Onboarding redirects to dashboard after org selection (should go to repo selection)
2. Repo names/descriptions invisible (light grey text)
3. No sync progress shown when triggering historical data sync

---

## Phase 1: Critical Fixes [Day 1]

### 1.1 Fix Repo Page Styling [S]

- [ ] **1.1.1** Update `repo_card.html` text colors
  - [ ] Line 4: `text-slate-200` → `text-base-content` (repo name)
  - [ ] Line 7: `text-slate-400` → `text-base-content/80` (description)
  - **File:** `apps/integrations/templates/integrations/components/repo_card.html`

- [ ] **1.1.2** Update `member_row.html` text colors
  - [ ] Line 9: `text-slate-300` → `text-base-content/80` (avatar initials)
  - [ ] Line 12: `text-slate-200` → `text-base-content` (member name)
  - [ ] Line 16: `text-slate-400` → `text-base-content/80` (username)
  - [ ] Line 20: `text-slate-400` → `text-base-content/80` (email)
  - **File:** `apps/integrations/templates/integrations/components/member_row.html`

- [ ] **1.1.3** Update `github_repos.html` styling
  - [ ] Line 10: `text-slate-500` + `hover:text-slate-300` → `text-base-content/70` + `hover:text-base-content`
  - [ ] Line 42: `text-slate-500` → `text-base-content/70`
  - **File:** `apps/integrations/templates/integrations/github_repos.html`

- [ ] **1.1.4** Update `github_members.html` styling
  - [ ] Line 10: `text-slate-500` + `hover:text-slate-300` → `text-base-content/70` + `hover:text-base-content`
  - [ ] Line 54: `text-slate-500` → `text-base-content/70`
  - **File:** `apps/integrations/templates/integrations/github_members.html`

- [ ] **1.1.5** Test on dev2.ianchuk.com
  - [ ] Repo names visible
  - [ ] Repo descriptions visible
  - [ ] Member names visible
  - [ ] Back links visible

**Acceptance Criteria:** All text on repos/members pages is clearly readable with proper contrast

---

### 1.2 Add Onboarding State Tracking [M]

- [ ] **1.2.1** Add `onboarding_complete` field to Team model
  - [ ] Add `onboarding_complete = models.BooleanField(default=True)`
  - [ ] Add help_text explaining purpose
  - **File:** `apps/teams/models.py`

- [ ] **1.2.2** Create and apply migration
  - [ ] Run `make migrations`
  - [ ] Verify migration sets default=True (existing teams complete)
  - [ ] Run `make migrate`

- [ ] **1.2.3** Update `_create_team_from_org` to set flag False
  - [ ] After `team.save()`, set `team.onboarding_complete = False`
  - **File:** `apps/onboarding/views.py` (lines 174-218)

- [ ] **1.2.4** Update `onboarding_complete` view to set flag True
  - [ ] At end of view, set `team.onboarding_complete = True`
  - [ ] Save team
  - **File:** `apps/onboarding/views.py` (lines 429-451)

- [ ] **1.2.5** Update `select_organization` guard
  - [ ] Change `if request.user.teams.exists()` to check `onboarding_complete`
  - [ ] Allow users with incomplete onboarding to continue
  - **File:** `apps/onboarding/views.py` (lines 94-97)

- [ ] **1.2.6** Update `select_repositories` guard (if exists)
  - [ ] Allow access if team exists but `onboarding_complete=False`
  - **File:** `apps/onboarding/views.py`

**Acceptance Criteria:** Users can complete org selection → repo selection without redirect

---

## Phase 2: UX Improvements [Day 2]

### 2.1 Fix Onboarding Flow Redirect [M]

- [ ] **2.1.1** Update `web:home` redirect logic
  - [ ] Check `team.onboarding_complete` before redirecting to dashboard
  - [ ] If incomplete, redirect to `onboarding:select_repos`
  - **File:** `apps/web/views.py` (lines 47-59)

- [ ] **2.1.2** Add "Resume Onboarding" for incomplete teams (optional)
  - [ ] If team exists but `onboarding_complete=False`, show banner
  - [ ] Link to `onboarding:select_repos`
  - **File:** `templates/web/app/dashboard.html` or similar

- [ ] **2.1.3** Test complete onboarding flow
  - [ ] Connect GitHub
  - [ ] Select org
  - [ ] Verify redirect to repos (not dashboard)
  - [ ] Select repos
  - [ ] Complete onboarding
  - [ ] Verify can now access dashboard

**Acceptance Criteria:** Full onboarding flow works without premature dashboard redirect

---

### 2.2 Async Manual Sync with Progress [M]

- [ ] **2.2.1** Create `sync_repository_manual_task` Celery task
  - [ ] Set `sync_status = "syncing"` at start
  - [ ] Set `sync_started_at = timezone.now()`
  - [ ] Call existing sync service
  - [ ] Set `sync_status = "complete"` or `"error"` on finish
  - [ ] Save all changes
  - **File:** `apps/integrations/tasks.py`

- [ ] **2.2.2** Update `github_repo_sync` view
  - [ ] Queue Celery task instead of sync call
  - [ ] Set status to "syncing" immediately
  - [ ] Return progress partial (not JSON)
  - **File:** `apps/integrations/views/github.py` (lines 461-491)

- [ ] **2.2.3** Update sync button HTMX attributes in `repo_card.html`
  - [ ] Change `hx-swap="none"` to `hx-swap="innerHTML"`
  - [ ] Ensure target is sync status container
  - **File:** `apps/integrations/templates/integrations/components/repo_card.html` (lines 70-82)

- [ ] **2.2.4** Test sync progress
  - [ ] Click sync icon
  - [ ] Verify "Syncing" badge appears
  - [ ] Verify polling shows progress
  - [ ] Verify "Complete" status on finish

**Acceptance Criteria:** Users see immediate feedback when clicking sync, progress updates show

---

## Phase 3: Polish [Day 3]

### 3.1 Real-time Progress Updates [L] (Optional)

- [ ] **3.1.1** Add progress callback to sync service
  - [ ] Update `sync_prs_completed` during sync
  - [ ] Save periodically (not every PR - batch of 10?)
  - **File:** `apps/integrations/services/github_sync.py`

- [ ] **3.1.2** Enable progress bar display
  - [ ] `sync_progress.html` already has progress bar template
  - [ ] Ensure `sync_prs_total` is set at sync start
  - **File:** `apps/integrations/templates/integrations/partials/sync_progress.html`

**Acceptance Criteria:** Progress bar shows real % during sync

---

### 3.2 Testing & Deployment [M]

- [ ] **3.2.1** Write tests for onboarding flow
  - [ ] Test incomplete onboarding allows repo access
  - [ ] Test complete sets flag
  - [ ] Test home redirect behavior
  - **File:** `apps/onboarding/tests/test_onboarding_flow.py`

- [ ] **3.2.2** Write tests for manual sync
  - [ ] Test task is queued
  - [ ] Test status updates
  - **File:** `apps/integrations/tests/test_github_sync.py`

- [ ] **3.2.3** Run full test suite
  - [ ] `make test`
  - [ ] Fix any failures

- [ ] **3.2.4** Deploy and test on dev2.ianchuk.com
  - [ ] Full onboarding flow
  - [ ] Repo page readability
  - [ ] Sync progress

- [ ] **3.2.5** Deploy to production (when ready)

**Acceptance Criteria:** All tests pass, production deployment successful

---

## Quick Reference

### Files to Modify

| Phase | File | Changes |
|-------|------|---------|
| 1.1 | `repo_card.html` | Text colors |
| 1.1 | `member_row.html` | Text colors |
| 1.1 | `github_repos.html` | Back link, footer |
| 1.1 | `github_members.html` | Back link, footer |
| 1.2 | `apps/teams/models.py` | Add field |
| 1.2 | `apps/onboarding/views.py` | Set flag, update guards |
| 2.1 | `apps/web/views.py` | Check flag before redirect |
| 2.2 | `apps/integrations/tasks.py` | New task |
| 2.2 | `apps/integrations/views/github.py` | Queue task |
| 2.2 | `repo_card.html` | HTMX swap |

### Commands

```bash
# Create migration
make migrations

# Apply migration
make migrate

# Run tests
make test

# Run specific tests
make test ARGS='apps.onboarding.tests.test_onboarding_flow'

# Deploy to dev2
docker compose pull && docker compose up -d
```

---

## Progress Tracking

| Task | Status | Notes |
|------|--------|-------|
| 1.1.1 repo_card.html | [ ] | |
| 1.1.2 member_row.html | [ ] | |
| 1.1.3 github_repos.html | [ ] | |
| 1.1.4 github_members.html | [ ] | |
| 1.1.5 Test styling | [ ] | |
| 1.2.1 Add field | [ ] | |
| 1.2.2 Migration | [ ] | |
| 1.2.3 Set False on create | [ ] | |
| 1.2.4 Set True on complete | [ ] | |
| 1.2.5 Update org guard | [ ] | |
| 1.2.6 Update repos guard | [ ] | |
| 2.1.1 Home redirect | [ ] | |
| 2.1.2 Resume banner | [ ] | Optional |
| 2.1.3 Test flow | [ ] | |
| 2.2.1 Celery task | [ ] | |
| 2.2.2 Update view | [ ] | |
| 2.2.3 HTMX swap | [ ] | |
| 2.2.4 Test sync | [ ] | |
| 3.1.* Progress | [ ] | Optional |
| 3.2.* Tests/Deploy | [ ] | |
