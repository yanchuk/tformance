# Phase 2.3: Organization Discovery - Task Checklist

> Last Updated: 2025-12-10 (Session Complete)

## Overview

Total tasks: 32
**Status: COMPLETE** ✅

---

## 2.3.1 GitHub API Service Extension [Effort: S] ✅ COMPLETE

### New API Functions
- [x] Add `get_organization_members(access_token, org_slug)` to github_oauth.py
- [x] Add pagination support (handle `per_page`, `page` params)
- [x] Add `get_user_details(access_token, username)` for name/email
- [x] Handle Link header for pagination navigation
- [x] Add rate limit detection and graceful handling

### Tests
- [x] Test `get_organization_members` returns member list
- [x] Test pagination handling for large orgs
- [x] Test `get_user_details` returns user data
- [x] Test error handling for API failures
- [x] Test rate limit detection

---

## 2.3.2 Member Sync Service [Effort: M] ✅ COMPLETE

### Core Service
- [x] Create `apps/integrations/services/member_sync.py`
- [x] Implement `sync_github_members(team, access_token, org_slug)` function
- [x] Create new TeamMember records for new members
- [x] Update existing TeamMember records if username changed
- [x] Fetch and store user details (name, email) when available
- [x] Return sync results (created, updated, unchanged counts)

### Edge Cases
- [x] Handle members with no public email
- [x] Handle members with no public name (use username)
- [x] Handle duplicate github_id (should not happen, but defensive)
- [x] Log sync progress for debugging

### Tests
- [x] Test sync creates new TeamMember for new GitHub user
- [x] Test sync updates existing TeamMember if username changed
- [x] Test sync fetches user details (name, email)
- [x] Test sync handles private email gracefully
- [x] Test sync returns accurate counts
- [x] Test sync is idempotent (running twice doesn't duplicate)

---

## 2.3.3 Post-OAuth Member Import [Effort: S] ✅ COMPLETE

### OAuth Callback Integration
- [x] Update `github_callback` view to trigger member sync
- [x] Decision: Sync inline vs background task (chose inline for small orgs)
- [x] Add member count to success message
- [x] Handle sync errors gracefully (don't fail OAuth)

### Alternative: Async Import
- [ ] (Optional) Create intermediate "Importing members..." page - SKIPPED for MVP
- [ ] (Optional) Use Celery task for background import - SKIPPED for MVP
- [ ] (Optional) Redirect to members page after completion - SKIPPED for MVP

### Tests
- [x] Test OAuth callback triggers member sync
- [x] Test success message shows member count
- [x] Test OAuth completes even if sync fails

---

## 2.3.4 Member Management Views [Effort: M] ✅ COMPLETE

### List View
- [x] Create `github_members` view
- [x] Require login and team membership
- [x] Require GitHub integration exists
- [x] Query TeamMember records with github_id populated
- [x] Pass members to template with pagination

### Sync View
- [x] Create `github_members_sync` view (POST only)
- [x] Require team admin role
- [x] Trigger member sync
- [x] Return to members page with results message
- [x] HTMX support for inline refresh

### Toggle View
- [x] Create `github_member_toggle` view (POST only)
- [x] Toggle member `is_active` status
- [x] HTMX support for inline update
- [x] Return updated member partial

### URL Configuration
- [x] Add `github/members/` URL
- [x] Add `github/members/sync/` URL
- [x] Add `github/members/<int:member_id>/toggle/` URL

### Tests
- [x] Test members view requires login
- [x] Test members view requires team membership
- [x] Test members view shows GitHub members only
- [x] Test sync view triggers sync and shows message
- [x] Test toggle view changes is_active status
- [x] Test toggle view returns partial for HTMX

---

## 2.3.5 Member Management Templates [Effort: M] ✅ COMPLETE

### Main Template
- [x] Create `integrations/github_members.html`
- [x] Extend `web/app/app_base.html`
- [x] Show page title and description
- [x] Add "Sync Members" button
- [x] Show last sync timestamp
- [x] Show member count

### Member List
- [x] Display members in grid/list layout
- [x] Show avatar from GitHub (if available)
- [x] Show display name and username
- [x] Show email (if available)
- [x] Show active/inactive status badge
- [x] Add toggle button for active status

### Components
- [x] Create `integrations/components/member_row.html` partial
- [x] Support HTMX swap for toggle action

### Empty State
- [x] Handle no members case
- [x] Show helpful message with sync button

### Integration Dashboard Update
- [x] Add "Members" link to GitHub card in home.html
- [x] Show member count on GitHub card

---

## 2.3.6 Background Sync Task [Effort: M] - DEFERRED

### Celery Task
- [ ] Create `apps/integrations/tasks.py` - DEFERRED to future phase
- [ ] Implement `sync_github_org_members(team_id)` task
- [ ] Decrypt token within task
- [ ] Call member sync service
- [ ] Update GitHubIntegration `last_sync_at` and `sync_status`
- [ ] Handle errors and set error status

### Celery Beat Schedule
- [ ] Add daily schedule for member sync - DEFERRED
- [ ] Configure in settings or admin
- [ ] Only sync teams with active GitHub integration

### Error Handling
- [ ] Implement retry logic (max 3 attempts) - DEFERRED
- [ ] Log failures for debugging
- [ ] Send notification on repeated failures (future)

### Tests
- [ ] Test Celery task executes sync - DEFERRED
- [ ] Test task updates last_sync_at
- [ ] Test task handles errors gracefully

**Note:** Background sync deferred to Phase 2.6 or later. Manual sync via UI is available.

---

## Post-Implementation ✅ COMPLETE

### Documentation
- [x] Update org-discovery-tasks.md to mark complete
- [x] Update org-discovery-context.md with implementation notes
- [ ] Update github-integration-tasks.md to mark 2.3 complete

### Cleanup
- [x] Run ruff format and lint
- [x] Ensure all tests pass
- [x] Remove any debug logging

---

## Completion Criteria ✅ ALL MET

Phase 2.3 is complete when:
1. [x] GitHub org members are auto-imported on OAuth completion
2. [x] TeamMember records created with github_id, github_username
3. [x] Member list viewable in integrations UI
4. [x] Admin can toggle member active status
5. [x] Manual sync button works
6. [ ] Background sync task runs daily - DEFERRED
7. [x] All tests pass (431 tests)
8. [ ] Code reviewed and merged - PENDING PR

---

## Quick Reference

### URLs implemented:
```
/a/{team}/integrations/github/members/              → github_members
/a/{team}/integrations/github/members/sync/         → github_members_sync
/a/{team}/integrations/github/members/{id}/toggle/  → github_member_toggle
```

### Key imports:
```python
from apps.metrics.models import TeamMember
from apps.integrations.models import GitHubIntegration, IntegrationCredential
from apps.integrations.services.encryption import decrypt
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.integrations.services.member_sync import sync_github_members
from apps.teams.decorators import login_and_team_required, team_admin_required
```

### TDD Cycles Completed:
1. `get_organization_members()` - RED → GREEN → REFACTOR ✅
2. `get_user_details()` - RED → GREEN → REFACTOR ✅
3. Pagination support - RED → GREEN → REFACTOR ✅
4. `sync_github_members()` - RED → GREEN → REFACTOR ✅
5. OAuth callback integration - RED → GREEN → REFACTOR ✅
6. Member management views - RED → GREEN → REFACTOR ✅
