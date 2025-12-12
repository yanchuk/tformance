# Phase 2.2: GitHub OAuth Flow - Task Checklist

> Last Updated: 2025-12-10

## Overview

Total tasks: 28
Estimated effort: Low-Medium (Phase complexity: Medium)
**Status: COMPLETE**

---

## 2.2.1 URL Configuration [Effort: S]

### Setup
- [x] Create `apps/integrations/urls.py` with app_name and team_urlpatterns
- [x] Add integrations to `tformance/urls.py` team_urlpatterns
- [x] Verify URL routing works (404 → view not found)

### Test URLs
- [x] Write test for URL resolution
- [x] Verify team_slug is properly captured

---

## 2.2.2 OAuth Service [Effort: M]

### Core Service
- [x] Create `apps/integrations/services/github_oauth.py`
- [x] Implement `create_oauth_state(team_id)` - signed state parameter
- [x] Implement `verify_oauth_state(state)` - decode and verify state
- [x] Implement `get_authorization_url(team, callback_url)` - build GitHub auth URL
- [x] Implement `exchange_code_for_token(code)` - POST to GitHub for token
- [x] Implement `get_authenticated_user(token)` - fetch authenticated user
- [x] Implement `get_user_organizations(token)` - fetch user's organizations

### Error Handling
- [x] Handle invalid/expired code
- [x] Handle network errors
- [x] Handle rate limiting
- [x] Create custom exceptions (GitHubOAuthError, etc.)

### Tests
- [x] Test state creation/verification
- [x] Test authorization URL generation
- [x] Test token exchange (mocked)
- [x] Test user/org fetching (mocked)
- [x] Test error handling

---

## 2.2.3 OAuth Views [Effort: M]

### Connect View
- [x] Create `github_connect` view
  - Check if already connected
  - Generate state parameter
  - Redirect to GitHub authorization URL
- [x] Add `@login_and_team_required` decorator
- [x] Add `@team_admin_required` decorator (only admins can connect)

### Callback View
- [x] Create `github_callback` view
  - Verify state parameter
  - Exchange code for token
  - Fetch user orgs
  - If single org: create integration
  - If multiple orgs: redirect to selection
- [x] Handle OAuth errors (access_denied, etc.)
- [x] Store encrypted token in IntegrationCredential
- [x] Create GitHubIntegration with org details

### Org Selection View
- [x] Create `github_select_org` view (GET)
  - Display list of available orgs
  - Show org details (name, avatar)
- [x] Handle org selection (POST)
  - Create integration for selected org
  - Redirect to success page

### Disconnect View
- [x] Create `github_disconnect` view
  - Require POST method
  - Delete GitHubIntegration and IntegrationCredential
- [x] Add confirmation step (Alpine.js inline confirmation)

### Tests
- [x] Test connect redirect
- [x] Test callback success (single org)
- [x] Test callback success (multiple orgs)
- [x] Test callback errors
- [x] Test disconnect

---

## 2.2.4 Integration Dashboard [Effort: M]

### Templates Directory
- [x] Create `apps/integrations/templates/integrations/` directory
- [x] Create base layout extending team app template

### Integrations Home
- [x] Create `home.html` template
  - List all integration types (GitHub, Jira, Slack)
  - Show connection status for each
  - Connect/disconnect buttons
- [x] Create `integrations_home` view
- [x] Add Integrations link to team navigation sidebar

### GitHub Card Component
- [x] Show connection status
- [x] Show org name if connected
- [x] Show last sync time
- [x] Connect/disconnect button

### Select Org Page
- [x] Create `github_select_org.html`
  - List orgs with avatars
  - Clickable selection buttons
  - Back link to integrations

### Error States
- [x] Handle OAuth errors gracefully
- [x] Show helpful error messages via Django messages framework

### Tests
- [x] Test integrations home page loads
- [x] Test org selection UI

---

## 2.2.5 Environment & Configuration [Effort: S]

### GitHub OAuth App
- [x] Add GITHUB_CLIENT_ID to settings.py
- [x] Add GITHUB_SECRET_ID to settings.py
- [x] Verify settings load correctly

### Validation
- [x] Check settings in OAuth service
- [ ] Add helpful error if GITHUB_CLIENT_ID not configured (deferred)

---

## Post-Implementation

### Documentation
- [x] Update github-oauth-tasks.md to mark complete

### Cleanup
- [ ] Run ruff format and lint
- [x] Ensure all tests pass (383 tests passing)

---

## Completion Criteria

Phase 2.2 is complete when:
1. [x] User can click "Connect GitHub" and be redirected to GitHub OAuth
2. [x] After authorization, token is stored encrypted in database
3. [x] GitHubIntegration record is created with org details
4. [x] User can see connection status on integrations page
5. [x] User can disconnect (removes integration)
6. [x] Multiple org scenario shows selection UI
7. [x] All tests pass (383 tests, 77 new for OAuth flow)
8. [ ] Code reviewed and merged

---

## Implementation Notes

### Files Created
- `apps/integrations/urls.py` - URL routing for integrations
- `apps/integrations/services/github_oauth.py` - OAuth service with state management
- `apps/integrations/templates/integrations/home.html` - Dashboard with cards for GitHub/Jira/Slack
- `apps/integrations/templates/integrations/select_org.html` - Organization selection page
- `apps/integrations/tests/test_urls.py` - 12 URL tests
- `apps/integrations/tests/test_github_oauth.py` - 23 OAuth service tests
- `apps/integrations/tests/test_views.py` - 42 view tests

### Files Modified
- `tformance/urls.py` - Added integrations to team_urlpatterns
- `tformance/settings.py` - Added GITHUB_CLIENT_ID, GITHUB_SECRET_ID at module level
- `apps/integrations/views.py` - Implemented all 5 OAuth views
- `templates/web/components/team_nav.html` - Added Integrations link to sidebar

### Key Design Decisions
1. Used Django's `Signer` for state parameter CSRF protection
2. Token encryption uses Fernet from Phase 2.1
3. Alpine.js for inline disconnect confirmation (no modal needed)
4. Cards for all 3 integrations (Jira/Slack marked "Coming soon")
5. Views use `@team_admin_required` for connect/disconnect, `@login_and_team_required` for read-only

---

## Quick Reference

### URLs implemented:
```
/a/{team}/integrations/                    → integrations_home
/a/{team}/integrations/github/connect/     → github_connect
/a/{team}/integrations/github/callback/    → github_callback
/a/{team}/integrations/github/select-org/  → github_select_org
/a/{team}/integrations/github/disconnect/  → github_disconnect
```

### Key imports:
```python
from apps.teams.decorators import login_and_team_required, team_admin_required
from apps.integrations.services.encryption import encrypt, decrypt
from apps.integrations.services import github_oauth
from apps.integrations.models import IntegrationCredential, GitHubIntegration
```

### TDD Summary:
- RED phase: Wrote 77 failing tests first
- GREEN phase: Implemented minimum code to pass
- REFACTOR phase: Added type hints, constants, helper functions
