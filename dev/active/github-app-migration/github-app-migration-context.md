# GitHub App Migration - Context

**Last Updated:** 2026-01-01

---

## 1. Key Files

### Core Files to Create

| File | Purpose | Status |
|------|---------|--------|
| `apps/integrations/services/github_app.py` | GitHub App service (JWT, tokens) | Pending |
| `apps/integrations/webhooks/github_app.py` | App webhook event handlers | Pending |
| `apps/integrations/tests/test_github_app.py` | GitHub App service tests | Pending |
| `apps/integrations/tests/test_github_app_webhooks.py` | Webhook handler tests | Pending |

### Files to Modify

| File | Changes | Status |
|------|---------|--------|
| `apps/integrations/models.py` | Add GitHubAppInstallation model | Pending |
| `apps/integrations/services/github_client.py` | Add installation token support | Pending |
| `tformance/settings.py` | Add GITHUB_APP_* settings | Pending |
| `apps/onboarding/views.py` | Add GitHub App installation flow | Pending |
| `apps/integrations/views/github.py` | Add app management views | Pending |
| `apps/web/views.py` | Add app webhook endpoint | Pending |
| `apps/web/urls.py` | Add webhook URL | Pending |

### Reference Files (Do Not Modify)

| File | Why Important |
|------|---------------|
| `apps/integrations/services/github_oauth.py` | Keep for Copilot, pattern reference |
| `apps/integrations/services/github_webhooks.py` | Signature verification to reuse |
| `prd/GITHUB-APP-MIGRATION.md` | Complete migration plan |

---

## 2. Key Decisions

### Scope Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Copilot handling** | Keep OAuth separately | `manage_billing:copilot` is OAuth-only scope |
| **User login** | Keep OAuth for allauth | GitHub App user OAuth more complex, no benefit |
| **Migration approach** | New installs only first | Lower risk, validate before migrating |
| **OAuth removal** | Never (keep for Copilot) | Copilot metrics need OAuth |

### Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **PyGithub integration** | Use `GithubIntegration` class | Built-in JWT handling |
| **Token caching** | Cache in model with expiry | Avoid API calls for every request |
| **Webhook verification** | Same HMAC-SHA256 pattern | Reuse existing code |
| **Model location** | `apps/integrations/models.py` | Consistent with other integrations |

---

## 3. Environment Variables

### Required for Development

```bash
# GitHub App credentials (get from github.com/settings/apps)
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_APP_WEBHOOK_SECRET=your_webhook_secret_here
GITHUB_APP_CLIENT_ID=Iv1.xxxxxxxxxxxx
GITHUB_APP_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Existing (Keep As-Is)

```bash
# OAuth App credentials (still needed for Copilot + user login)
GITHUB_CLIENT_ID=existing_oauth_client_id
GITHUB_SECRET_ID=existing_oauth_secret
```

---

## 4. GitHub App Configuration

### Permissions Required

| Permission | Access | Purpose |
|------------|--------|---------|
| **Contents** | Read | Fetch commits, files |
| **Pull requests** | Read + Write | Read PRs, post comments |
| **Metadata** | Read | Automatic with any access |
| **Members** | Read | Sync organization members |

### Webhook Events

| Event | Purpose |
|-------|---------|
| `installation` | Track app install/uninstall |
| `installation_repositories` | Track repo additions/removals |
| `pull_request` | PR opened, closed, merged |
| `pull_request_review` | Reviews submitted |
| `push` | Commits pushed (optional) |

### App URLs

| URL | Value |
|-----|-------|
| Homepage | `https://tformance.com` |
| Callback URL | `https://app.tformance.com/auth/github/app/callback/` |
| Setup URL | `https://app.tformance.com/onboarding/github-app/` |
| Webhook URL | `https://app.tformance.com/webhooks/github/app/` |

---

## 5. Data Model

### GitHubAppInstallation

```python
class GitHubAppInstallation(BaseTeamModel):
    """Tracks GitHub App installations per team.

    Replaces IntegrationCredential for GitHub (except Copilot).
    Stores installation_id, which is used to get short-lived tokens.
    """

    # GitHub installation identifier
    installation_id = models.BigIntegerField(unique=True)

    # Account that installed the app
    account_type = models.CharField(max_length=20)  # "Organization" or "User"
    account_login = models.CharField(max_length=100)
    account_id = models.BigIntegerField()

    # Installation state
    is_active = models.BooleanField(default=True)
    suspended_at = models.DateTimeField(null=True, blank=True)

    # Permissions snapshot (for display/debugging)
    permissions = models.JSONField(default=dict)
    events = models.JSONField(default=list)
    repository_selection = models.CharField(max_length=20, default="selected")

    # Cached installation token (avoid API calls)
    cached_token = EncryptedTextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "integrations_github_app_installation"
        indexes = [
            models.Index(fields=["account_login"], name="gh_app_inst_login_idx"),
            models.Index(fields=["is_active"], name="gh_app_inst_active_idx"),
        ]
```

### Relationship to Existing Models

```
Team
 ├── GitHubIntegration (existing, keep for OAuth/Copilot)
 │    └── IntegrationCredential (OAuth tokens)
 │
 └── GitHubAppInstallation (new, prefer for API access)
      └── (no credentials stored - tokens are ephemeral)
```

---

## 6. Service Architecture

### GitHubAppService

```python
class GitHubAppService:
    """GitHub App authentication and API service.

    Usage:
        service = GitHubAppService()
        client = service.get_installation_client(installation_id)
        repos = client.get_organization("acme").get_repos()
    """

    def __init__(self):
        self.app_id = settings.GITHUB_APP_ID
        self.private_key = settings.GITHUB_APP_PRIVATE_KEY

    def get_jwt(self) -> str:
        """Generate JWT for app-level authentication.

        Returns:
            JWT token valid for 10 minutes
        """

    def get_installation_token(self, installation_id: int) -> str:
        """Get installation access token for API calls.

        Returns:
            Access token valid for 1 hour

        Raises:
            GitHubAppError: If installation not found or suspended
        """

    def get_installation_client(self, installation_id: int) -> Github:
        """Get authenticated PyGithub client.

        Returns:
            Github client configured with installation token
        """

    def get_installation(self, installation_id: int) -> dict:
        """Fetch installation details from GitHub API.

        Returns:
            Installation data including account, permissions, events
        """

    def get_installation_repositories(self, installation_id: int) -> list[dict]:
        """List repositories accessible to an installation.

        Returns:
            List of repository dictionaries
        """
```

### get_github_client_for_team (Updated)

```python
def get_github_client_for_team(team: Team) -> Github:
    """Get GitHub client using best available auth method.

    Priority:
    1. GitHub App installation (preferred)
    2. OAuth credential (fallback/Copilot)

    Returns:
        Authenticated Github client

    Raises:
        NoGitHubConnectionError: If no auth method available
    """
    # Try GitHub App first
    try:
        installation = GitHubAppInstallation.objects.get(team=team, is_active=True)
        return GitHubAppService().get_installation_client(installation.installation_id)
    except GitHubAppInstallation.DoesNotExist:
        pass

    # Fall back to OAuth
    try:
        credential = IntegrationCredential.objects.get(
            team=team, provider=IntegrationCredential.PROVIDER_GITHUB
        )
        return Github(credential.access_token)
    except IntegrationCredential.DoesNotExist:
        raise NoGitHubConnectionError(f"Team {team.slug} has no GitHub connection")
```

---

## 7. Testing Strategy

### Unit Tests

| Test Class | Coverage |
|------------|----------|
| `TestGitHubAppService` | JWT generation, token fetching, client creation |
| `TestGitHubAppInstallationModel` | Model validation, token caching |
| `TestGitHubAppWebhooks` | Event handling, signature verification |

### Integration Tests

| Test Class | Coverage |
|------------|----------|
| `TestGitHubAppInstallationFlow` | Full installation callback flow |
| `TestGitHubAppClientResolution` | Client selection logic |
| `TestGitHubAppSyncTasks` | Sync with installation tokens |

### Mocking Strategy

- Use `unittest.mock.patch` for GitHub API calls
- Use `responses` or `vcr.py` for recorded HTTP responses
- Create factory for `GitHubAppInstallation`

---

## 8. Related Documentation

| Document | Purpose |
|----------|---------|
| `prd/GITHUB-APP-MIGRATION.md` | Full migration plan (6 phases) |
| `CLAUDE.md` | Coding guidelines, TDD requirements |
| `dev/guides/AUTHENTICATION-FLOWS.md` | OAuth patterns |

---

## 9. Open Questions

| Question | Status | Decision |
|----------|--------|----------|
| Should we cache installation tokens in Redis? | Pending | Start with model field, optimize later |
| How to handle suspended installations? | Pending | Mark inactive, prompt reinstall |
| What about private repos in user accounts? | Pending | Support "User" account type |
