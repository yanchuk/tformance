# Phase 2.2: GitHub OAuth Flow - Context Reference

> Last Updated: 2025-12-10

## Current Implementation Status

**Status:** COMPLETE ✅

**Depends on:** Phase 2.1 Integration App Foundation ✅ Complete

---

## Implementation Summary

Phase 2.2 is fully implemented with:
- 77 new tests (all passing)
- Full OAuth flow (connect, callback, disconnect, org selection)
- Styled templates using DaisyUI/Tailwind
- Navigation link added to team sidebar

### Files Created
| File | Purpose |
|------|---------|
| `apps/integrations/urls.py` | URL routing for all OAuth endpoints |
| `apps/integrations/services/github_oauth.py` | OAuth business logic (state, token exchange, API calls) |
| `apps/integrations/templates/integrations/home.html` | Dashboard with GitHub/Jira/Slack cards |
| `apps/integrations/templates/integrations/select_org.html` | Organization selection UI |
| `apps/integrations/tests/test_urls.py` | 12 URL resolution tests |
| `apps/integrations/tests/test_github_oauth.py` | 23 OAuth service tests |
| `apps/integrations/tests/test_views.py` | 42 view tests |

### Files Modified
| File | Changes |
|------|---------|
| `tformance/urls.py` | Added integrations to team_urlpatterns |
| `tformance/settings.py` | Added GITHUB_CLIENT_ID, GITHUB_SECRET_ID at module level |
| `apps/integrations/views.py` | Implemented all 5 OAuth views |
| `templates/web/components/team_nav.html` | Added "Integrations" link to sidebar |

---

## Key Implementation Decisions

### 1. State Parameter CSRF Protection
Used Django's built-in `Signer` class instead of manual HMAC:
```python
from django.core.signing import Signer

def create_oauth_state(team_id: int) -> str:
    signer = Signer()
    data = json.dumps({"team_id": team_id})
    return signer.sign(base64.b64encode(data.encode()).decode())
```

### 2. Custom OAuth vs django-allauth
Used custom OAuth flow (NOT allauth social login) because:
- We need team-scoped tokens, not user-scoped
- allauth stores tokens per-user, we need per-team
- More control over the flow

### 3. View Decorators
- `@team_admin_required` for connect/disconnect (only admins)
- `@login_and_team_required` for read-only views (callback, select_org, home)

### 4. Disconnect Confirmation
Used Alpine.js inline confirmation instead of modal:
```html
<form x-data="{ confirming: false }">
  <button x-show="!confirming" @click="confirming = true">Disconnect</button>
  <div x-show="confirming">
    <button type="submit">Confirm</button>
    <button @click="confirming = false">Cancel</button>
  </div>
</form>
```

### 5. Template Structure
Templates extend `web/app/app_base.html` and use:
- DaisyUI card components
- Tailwind utility classes
- SVG icons inline (GitHub, Jira, Slack logos)

---

## URL Endpoints Implemented

```
/a/{team}/integrations/                    → integrations_home
/a/{team}/integrations/github/connect/     → github_connect
/a/{team}/integrations/github/callback/    → github_callback
/a/{team}/integrations/github/select-org/  → github_select_org
/a/{team}/integrations/github/disconnect/  → github_disconnect
```

---

## OAuth Service Functions

```python
# apps/integrations/services/github_oauth.py

# Constants
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_OAUTH_SCOPES = "read:org repo read:user"

# Functions
create_oauth_state(team_id: int) -> str
verify_oauth_state(state: str) -> dict[str, Any]
get_authorization_url(team_id: int, redirect_uri: str) -> str
exchange_code_for_token(code: str, redirect_uri: str) -> dict[str, Any]
get_authenticated_user(access_token: str) -> dict[str, Any]
get_user_organizations(access_token: str) -> list[dict[str, Any]]

# Exception
class GitHubOAuthError(Exception)
```

---

## View Helper Functions

```python
# apps/integrations/views.py

def _create_github_credential(team, access_token, user) -> IntegrationCredential:
    """Create an encrypted GitHub credential for a team."""

def _create_github_integration(team, credential, org) -> GitHubIntegration:
    """Create a GitHub integration for a team."""
```

---

## Environment Variables Required

```bash
# GitHub OAuth App credentials (must be set to test real flow)
GITHUB_CLIENT_ID=Iv1.xxxxxxxxxxxxxxx
GITHUB_SECRET_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Already configured (Phase 2.1)
INTEGRATION_ENCRYPTION_KEY=r8pmePXvrfFN4L_IjvTbZP3hWPTIN0y4KDw2wbuIRYg=
```

---

## Test Patterns Used

### Mocking GitHub API
```python
@patch("apps.integrations.services.github_oauth.get_user_organizations")
@patch("apps.integrations.services.github_oauth.exchange_code_for_token")
@patch("apps.integrations.services.github_oauth.verify_oauth_state")
def test_github_callback_success(self, mock_verify, mock_exchange, mock_get_orgs):
    mock_verify.return_value = {"team_id": self.team.id}
    mock_exchange.return_value = {"access_token": "gho_test_token"}
    mock_get_orgs.return_value = [{"login": "acme-corp", "id": 12345}]
    # ...
```

### Factory Usage
```python
from apps.integrations.factories import (
    IntegrationCredentialFactory,
    GitHubIntegrationFactory,
)
from apps.metrics.factories import TeamFactory, UserFactory

# Create test fixtures
team = TeamFactory()
admin = UserFactory()
team.members.add(admin, through_defaults={"role": ROLE_ADMIN})
credential = IntegrationCredentialFactory(team=team, provider="github")
```

---

## Next Phase: 2.3 Organization Discovery

After Phase 2.2, the next step is Phase 2.3 which will:
1. Fetch organization members from GitHub API
2. Create/update TeamMember records in `apps/metrics/models.py`
3. Match members by `github_id` field
4. Sync repository list for selection

---

## Verification Commands

```bash
# Run all tests (383 total, including 77 new OAuth tests)
make test ARGS='--keepdb'

# Run only integrations tests
make test ARGS='apps.integrations --keepdb'

# Check linting
make ruff

# Check for missing migrations (none needed - no model changes)
make migrations

# Start dev server and test manually
make dev
# Visit http://localhost:8000/a/{team}/integrations/
```

---

## Session Handoff Notes

**Session Complete:**
- Phase 2.2 GitHub OAuth Flow is FULLY IMPLEMENTED
- All 383 tests passing
- All linting passes
- No uncommitted migrations needed

**Ready for Next Session:**
1. Move `dev/active/github-oauth/` to `dev/completed/` (optional)
2. Start Phase 2.3: Organization Discovery
3. Or create PR for Phase 2.2 work

**Uncommitted Changes:**
Run `git status` to see all uncommitted files. Key changes:
- New files in `apps/integrations/`
- Modified `tformance/urls.py`, `tformance/settings.py`
- Modified `templates/web/components/team_nav.html`
- Updated `dev/active/github-oauth/` docs
