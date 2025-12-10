# Phase 2.2: GitHub OAuth Flow - Implementation Plan

> Last Updated: 2025-12-10

## Executive Summary

This phase implements the GitHub OAuth flow for tformance, allowing teams to connect their GitHub organization and authorize the app to access repositories, pull requests, and team members. This is a **low-medium complexity** phase that builds on the Phase 2.1 foundation.

### Key Outcomes
- Team admins can initiate GitHub OAuth from team settings
- OAuth callback handles token exchange and storage
- Encrypted tokens stored in IntegrationCredential model
- Organization selection when user has multiple orgs
- Disconnect flow with token revocation

### Dependencies
- Phase 2.1 (Integration App Foundation) - ✅ Complete
- IntegrationCredential, GitHubIntegration models exist
- Encryption service implemented

---

## Current State Analysis

### Existing Infrastructure
- **Models**: IntegrationCredential, GitHubIntegration, TrackedRepository (Phase 2.1)
- **Encryption**: `apps/integrations/services/encryption.py` working
- **django-allauth**: Already configured with GitHub provider in settings
- **Settings**: GITHUB_CLIENT_ID, GITHUB_SECRET_ID already defined (but empty)

### What Exists in Settings
```python
SOCIALACCOUNT_PROVIDERS = {
    "github": {
        "APPS": [{
            "client_id": env("GITHUB_CLIENT_ID", default=""),
            "secret": env("GITHUB_SECRET_ID", default=""),
            "key": "",
        }],
        "SCOPE": ["user", "repo", "read:org"],
    },
}
```

### Missing Components
- No `apps/integrations/urls.py` (needs to be created)
- No OAuth views for integrations
- No `github_oauth.py` service
- No integrations UI templates
- Main URL router doesn't include integrations app

---

## Technical Architecture

### OAuth Flow
```
1. User clicks "Connect GitHub" on /a/{team}/integrations/
   │
   ▼
2. Redirect to GitHub OAuth (with state param containing team_id)
   URL: https://github.com/login/oauth/authorize
   Scopes: read:org, repo, read:user
   │
   ▼
3. User authorizes on GitHub
   │
   ▼
4. GitHub redirects to /a/{team}/integrations/github/callback/?code=xxx&state=yyy
   │
   ▼
5. Backend exchanges code for access token
   POST https://github.com/login/oauth/access_token
   │
   ▼
6. Fetch user's organizations
   GET https://api.github.com/user/orgs
   │
   ▼
7. If single org: auto-select
   If multiple orgs: show org selection UI
   │
   ▼
8. Create IntegrationCredential (encrypted token)
   Create GitHubIntegration (org details)
   │
   ▼
9. Redirect to repository selection (Phase 2.4)
```

### Key Design Decisions

1. **Custom OAuth vs django-allauth social login**
   - Using CUSTOM OAuth flow (not allauth social login)
   - Reason: We need team-scoped tokens, not user-scoped
   - allauth stores tokens per-user, we need per-team

2. **State Parameter**
   - Encode `team_id` in state parameter
   - Verify state on callback to prevent CSRF

3. **Scopes**
   - `read:org` - List org members, teams
   - `repo` - Read repository data, PRs, commits
   - `read:user` - Read user profile data

---

## Implementation Phases

### 2.2.1: URL Configuration (Effort: S)
Create URL patterns for integrations app.

**Deliverables:**
- `apps/integrations/urls.py` with team_urlpatterns
- Update main `tformance/urls.py` to include integrations
- Basic routing working

### 2.2.2: OAuth Service (Effort: M)
Implement the OAuth business logic.

**Deliverables:**
- `apps/integrations/services/github_oauth.py`
- Token exchange function
- User info/orgs fetching
- State parameter handling

### 2.2.3: OAuth Views (Effort: M)
Create views for OAuth flow.

**Deliverables:**
- `github_connect` view - Initiates OAuth
- `github_callback` view - Handles callback
- `github_disconnect` view - Removes integration
- `github_select_org` view - Org selection if multiple

### 2.2.4: Integration Dashboard (Effort: M)
Create UI for managing integrations.

**Deliverables:**
- Integrations list page (`/a/{team}/integrations/`)
- GitHub connection status display
- Connect/disconnect buttons
- Error handling UI

### 2.2.5: Tests (Effort: M)
Comprehensive test coverage.

**Deliverables:**
- OAuth service unit tests
- View integration tests
- End-to-end flow tests with mocked GitHub

---

## API Endpoints

### Integration Management URLs
| Method | URL | View | Purpose |
|--------|-----|------|---------|
| GET | `/a/{team}/integrations/` | `integrations_home` | List integrations |
| GET | `/a/{team}/integrations/github/connect/` | `github_connect` | Initiate OAuth |
| GET | `/a/{team}/integrations/github/callback/` | `github_callback` | OAuth callback |
| POST | `/a/{team}/integrations/github/disconnect/` | `github_disconnect` | Remove integration |
| GET | `/a/{team}/integrations/github/select-org/` | `github_select_org` | Org selection |
| POST | `/a/{team}/integrations/github/select-org/` | `github_select_org` | Confirm org |

---

## Data Flow

### Token Storage
```python
# In github_callback view
from apps.integrations.services.encryption import encrypt

credential = IntegrationCredential.objects.create(
    team=team,
    provider="github",
    access_token=encrypt(raw_token),  # Encrypted!
    scopes=["read:org", "repo", "read:user"],
    connected_by=request.user,
)

github_integration = GitHubIntegration.objects.create(
    team=team,
    credential=credential,
    organization_slug=org["login"],
    organization_id=org["id"],
    webhook_secret=secrets.token_urlsafe(32),
)
```

### State Parameter Handling
```python
import json
import base64
from django.core.signing import Signer

def create_oauth_state(team_id: int) -> str:
    """Create signed state parameter for OAuth."""
    signer = Signer()
    data = json.dumps({"team_id": team_id})
    return signer.sign(base64.b64encode(data.encode()).decode())

def verify_oauth_state(state: str) -> dict:
    """Verify and decode state parameter."""
    signer = Signer()
    unsigned = signer.unsign(state)
    return json.loads(base64.b64decode(unsigned).decode())
```

---

## Risk Assessment

### High Risk
1. **State Parameter Tampering**
   - Mitigation: Use Django's Signer for HMAC signing

2. **Token Exposure**
   - Mitigation: Always encrypt before storage, never log tokens

### Medium Risk
1. **Rate Limiting During OAuth**
   - Mitigation: Minimal API calls during flow

2. **Multiple Orgs Confusion**
   - Mitigation: Clear org selection UI

### Low Risk
1. **OAuth App Not Configured**
   - Mitigation: Check settings on view load, show helpful error

---

## Environment Variables

```bash
# Required for OAuth
GITHUB_CLIENT_ID=your_github_oauth_app_client_id
GITHUB_SECRET_ID=your_github_oauth_app_secret

# Already configured
INTEGRATION_ENCRYPTION_KEY=xxx
```

### GitHub OAuth App Setup

1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - Application name: `tformance (dev)` or `tformance`
   - Homepage URL: `http://localhost:8000` (dev) or production URL
   - Authorization callback URL: `http://localhost:8000/a/TEAM_SLUG/integrations/github/callback/`
4. Copy Client ID and Client Secret to `.env`

**Note:** The callback URL must match exactly. For development, you may need to use a wildcard or update the OAuth app for each team slug you test with.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| OAuth completion rate | >90% of attempts |
| Error rate | <5% |
| Token encryption verified | 100% |
| Test coverage | >80% |

---

## File Structure (to create)

```
apps/integrations/
├── urls.py                    # NEW - URL patterns
├── views.py                   # UPDATE - OAuth views
├── services/
│   └── github_oauth.py        # NEW - OAuth logic
└── templates/
    └── integrations/
        ├── integrations_home.html      # Integration list
        ├── github_connect.html         # Connect button/status
        ├── github_select_org.html      # Org selection
        └── components/
            └── github_status.html      # Status component
```

---

## Template Structure

### Base Layout
Integrations pages should use the team app layout with:
- Team navigation active
- "Integrations" as active tab in sidebar

### HTMX Integration
- Use HTMX for disconnect confirmation
- Use HTMX for connection status refresh
- Follow project patterns from `apps/metrics/views.py`

---

## Testing Strategy

### Unit Tests
- State parameter creation/verification
- Token encryption during storage
- OAuth URL generation

### Integration Tests
- Full OAuth flow with mocked GitHub responses
- Error handling (invalid code, network error)
- Disconnect flow

### Manual Testing Checklist
1. Click "Connect GitHub" - redirects to GitHub
2. Authorize app - redirects back with token
3. Single org - auto-creates integration
4. Multiple orgs - shows selection UI
5. Disconnect - removes integration
6. Re-connect - works after disconnect
