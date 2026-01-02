# GitHub App Migration - Implementation Plan

**Last Updated:** 2026-01-01
**Status:** In Progress
**Reference PRD:** `prd/GITHUB-APP-MIGRATION.md`

---

## 1. Executive Summary

Migrate from GitHub OAuth App to GitHub App for improved security, simpler onboarding, and professional bot identity. Key scope decision: **Copilot metrics will remain on OAuth** and be handled separately.

### Goals

1. **Replace OAuth for repo/PR access** with GitHub App installation tokens
2. **Enable bot comments** that appear as `tformance[bot]` instead of the user
3. **Simplify onboarding** - users install app and select repos in one step
4. **Eliminate per-repo webhook setup** - app-level webhooks are automatic
5. **Maintain OAuth for Copilot** - `manage_billing:copilot` scope requires OAuth

### Non-Goals (This Phase)

- Migrating existing OAuth customers (future phase)
- Removing OAuth code (kept for Copilot)
- User authentication changes (keep GitHub login via OAuth)

---

## 2. Current State Analysis

### Files That Will Change

| File | Current Purpose | Changes Needed |
|------|-----------------|----------------|
| `apps/integrations/models.py` | OAuth credentials | Add `GitHubAppInstallation` model |
| `apps/integrations/services/github_client.py` | Simple OAuth wrapper | Add installation token support |
| `apps/integrations/services/github_webhooks.py` | Per-repo webhooks | Add app-level signature verification |
| `apps/onboarding/views.py` | OAuth connect flow | Add GitHub App installation flow |
| `apps/integrations/views/github.py` | OAuth integration | Add app installation views |
| `tformance/settings.py` | OAuth credentials | Add `GITHUB_APP_*` settings |
| `apps/web/views.py` | Webhook handling | Add app webhook endpoint |

### New Files to Create

| File | Purpose |
|------|---------|
| `apps/integrations/services/github_app.py` | GitHub App service (JWT, installation tokens) |
| `apps/integrations/webhooks/github_app.py` | App webhook event handlers |
| `apps/integrations/tests/test_github_app.py` | Unit tests for GitHub App service |
| `apps/integrations/tests/test_github_app_webhooks.py` | Webhook handler tests |

---

## 3. Implementation Phases

### Phase 1: Infrastructure & Models (TDD)

**Effort: M (2-3 days)**

Create the foundational GitHub App service and model.

#### 1.1 Settings Configuration

Add to `tformance/settings.py`:
```python
# GitHub App credentials
GITHUB_APP_ID = env("GITHUB_APP_ID", default="")
GITHUB_APP_PRIVATE_KEY = env("GITHUB_APP_PRIVATE_KEY", default="")
GITHUB_APP_WEBHOOK_SECRET = env("GITHUB_APP_WEBHOOK_SECRET", default="")
GITHUB_APP_CLIENT_ID = env("GITHUB_APP_CLIENT_ID", default="")  # For user OAuth via App
GITHUB_APP_CLIENT_SECRET = env("GITHUB_APP_CLIENT_SECRET", default="")
```

#### 1.2 GitHubAppInstallation Model

```python
class GitHubAppInstallation(BaseTeamModel):
    """Tracks GitHub App installations per team."""

    installation_id = models.BigIntegerField(unique=True)
    account_type = models.CharField(max_length=20)  # "Organization" or "User"
    account_login = models.CharField(max_length=100)
    account_id = models.BigIntegerField()

    is_active = models.BooleanField(default=True)
    suspended_at = models.DateTimeField(null=True, blank=True)

    permissions = models.JSONField(default=dict)
    events = models.JSONField(default=list)
    repository_selection = models.CharField(max_length=20, default="selected")

    # Token caching
    cached_token = EncryptedTextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
```

#### 1.3 GitHubAppService

```python
class GitHubAppService:
    """Service for GitHub App authentication and operations."""

    def get_jwt(self) -> str:
        """Generate JWT for app authentication (10 min expiry)."""

    def get_installation_token(self, installation_id: int) -> str:
        """Get installation access token for API calls (1 hour expiry)."""

    def get_installation_client(self, installation_id: int) -> Github:
        """Get authenticated PyGithub client for installation."""

    def get_installation(self, installation_id: int) -> dict:
        """Fetch installation details from GitHub API."""

    def get_installation_repositories(self, installation_id: int) -> list[dict]:
        """List repositories accessible to an installation."""
```

### Phase 2: Webhook Infrastructure (TDD)

**Effort: M (2-3 days)**

Handle GitHub App webhooks for installation lifecycle and PR events.

#### 2.1 Webhook Handler

```python
# apps/integrations/webhooks/github_app.py

def handle_installation_event(payload: dict) -> None:
    """Handle installation created/deleted/suspended events."""

def handle_installation_repositories_event(payload: dict) -> None:
    """Handle repositories added/removed from installation."""

def handle_pull_request_event(payload: dict) -> None:
    """Handle PR opened/closed/merged events."""
```

#### 2.2 URL Routing

```python
# apps/web/urls.py
path("webhooks/github/app/", views.github_app_webhook, name="github_app_webhook"),
```

#### 2.3 Signature Verification

Reuse existing `validate_webhook_signature` but with app webhook secret.

### Phase 3: Onboarding Flow (TDD)

**Effort: L (3-4 days)**

New onboarding flow using GitHub App installation.

#### 3.1 Installation Initiation

```python
# apps/onboarding/views.py

def github_app_install(request):
    """Redirect to GitHub App installation page."""
    # Generate state for callback
    # Redirect to: https://github.com/apps/tformance/installations/new
```

#### 3.2 Installation Callback

```python
def github_app_callback(request):
    """Handle GitHub App installation callback."""
    installation_id = request.GET.get("installation_id")
    setup_action = request.GET.get("setup_action")  # "install" or "update"

    # Fetch installation details
    # Create team + GitHubAppInstallation
    # Redirect to repo selection
```

#### 3.3 Repository Selection

Update existing `select_repositories` to work with installation token instead of OAuth.

### Phase 4: Sync Task Updates (TDD)

**Effort: M (2-3 days)**

Update background sync tasks to use installation tokens.

#### 4.1 Client Resolution

```python
# apps/integrations/services/github_client.py

def get_github_client_for_team(team: Team) -> Github:
    """Get GitHub client using best available auth method."""
    # Prefer GitHub App installation
    try:
        installation = GitHubAppInstallation.objects.get(team=team)
        return GitHubAppService().get_installation_client(installation.installation_id)
    except GitHubAppInstallation.DoesNotExist:
        pass

    # Fall back to OAuth credential (for legacy/Copilot)
    credential = IntegrationCredential.objects.get(team=team, provider="github")
    return Github(credential.access_token)
```

#### 4.2 Update Sync Tasks

- `sync_repository_initial_task`
- `sync_repository_manual_task`
- All PR sync tasks

### Phase 5: Integration Views (TDD)

**Effort: S (1-2 days)**

Add GitHub App management views for team admins.

#### 5.1 Installation Status View

Show installation status, permissions, and repositories.

#### 5.2 Reconfigure Installation

Link to GitHub to modify installation settings.

---

## 4. TDD Workflow

For each component, follow strict Red-Green-Refactor:

### RED Phase (Write Failing Test)
```python
class TestGitHubAppService(TestCase):
    def test_get_jwt_returns_valid_jwt(self):
        """Test that get_jwt returns a properly signed JWT."""
        service = GitHubAppService()
        jwt_token = service.get_jwt()

        # Decode and verify
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        self.assertEqual(decoded["iss"], settings.GITHUB_APP_ID)
        self.assertIn("exp", decoded)
        self.assertIn("iat", decoded)
```

### GREEN Phase (Minimal Implementation)
```python
def get_jwt(self) -> str:
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "iss": self.app_id,
    }
    return jwt.encode(payload, self.private_key, algorithm="RS256")
```

### REFACTOR Phase (Improve)
- Add caching if beneficial
- Improve error handling
- Add logging

---

## 5. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| PyJWT version incompatibility | M | L | Pin version, test in CI |
| GitHub API rate limits during testing | L | M | Use vcr.py for recorded responses |
| Installation webhook missed | H | L | Add reconciliation job |
| Token refresh race condition | M | L | Add locking mechanism |

---

## 6. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| All existing tests pass | 100% | `make test` |
| New code coverage | >90% | Coverage report |
| No OAuth regressions | 0 failures | Manual testing |
| Installation flow works | E2E pass | Playwright test |

---

## 7. Dependencies

### PyPI Packages (Already Installed)

- `PyGithub` - GitHub API client
- `PyJWT` - JWT encoding/decoding (verify version supports RS256)
- `cryptography` - For RSA private key handling

### Manual Prerequisites

1. **Create GitHub App** at github.com/settings/apps
2. **Generate private key** (.pem file)
3. **Set environment variables** in .env

---

## 8. Migration Strategy (Future Phase)

After initial implementation is stable:

1. Enable for new onboardings only
2. Run parallel for 2-4 weeks
3. Send migration emails to existing teams
4. Migrate existing teams with script
5. Deprecate OAuth for new connections (keep for Copilot)

---

## References

- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [Authenticating with GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app)
- [PyGithub GithubIntegration](https://pygithub.readthedocs.io/en/latest/github_objects/GithubIntegration.html)
- [PRD: GitHub App Migration](../../prd/GITHUB-APP-MIGRATION.md)
