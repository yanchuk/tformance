# GitHub App Migration Plan

## Product Specification

**Author:** Product & Engineering
**Status:** Draft
**Created:** January 2026

---

## 1. Executive Summary

### Current State: OAuth App

We currently use a **GitHub OAuth App** for authentication and API access. This requires:
- Users to authorize via OAuth flow
- Storing long-lived access tokens
- Per-repository webhook setup
- Fixed rate limits (5,000 req/hour)

### Target State: GitHub App

Migrate to a **GitHub App** for:
- Fine-grained permissions (not broad scopes)
- Short-lived tokens (1 hour vs indefinite)
- Built-in webhooks (no per-repo setup)
- Scalable rate limits
- Act independently of users (for background jobs)

---

## 2. Why Migrate?

### Benefits Comparison

| Feature | OAuth App (Current) | GitHub App (Target) |
|---------|---------------------|---------------------|
| **Permissions** | Broad scopes (`repo`, `read:org`) | Fine-grained per-resource |
| **Token Lifetime** | Indefinite until revoked | 1 hour (installation tokens) |
| **Webhooks** | Per-repository setup | Single app-level webhook |
| **Rate Limits** | Fixed 5,000/hour | Scales with installations |
| **User Dependency** | Always acts as user | Can act independently |
| **Repository Access** | All repos user can access | User selects specific repos |
| **Seat Consumption** | N/A | Does not consume org seats |

### Business Value

1. **Better Security Posture** - Short-lived tokens, minimal permissions
2. **Simpler Onboarding** - User installs app, selects repos, done
3. **Reliable Webhooks** - No webhook setup failures per-repo
4. **Higher Rate Limits** - Better for teams with many repos
5. **Enterprise Ready** - GitHub Apps are the recommended approach

---

## 3. Current OAuth Implementation

### Files Affected

| File | Purpose | Lines |
|------|---------|-------|
| `apps/integrations/services/github_oauth.py` | OAuth flow, token exchange, API calls | 440 |
| `apps/auth/views.py` | Login via GitHub OAuth | ~300 |
| `apps/onboarding/views.py` | Onboarding OAuth flow | ~400 |
| `apps/integrations/views/github.py` | Integration OAuth flow | ~350 |
| `apps/integrations/services/github_webhooks.py` | Per-repo webhook setup | ~100 |
| `tformance/settings.py` | `GITHUB_CLIENT_ID`, `GITHUB_SECRET_ID` | ~20 |

### Current Scopes

```python
GITHUB_OAUTH_SCOPES = " ".join([
    "read:org",           # Organization membership
    "repo",               # Full repository access
    "read:user",          # User profile
    "user:email",         # User emails
    "manage_billing:copilot",  # Copilot metrics
])
```

### Current Flows

1. **Login Flow**: User → GitHub OAuth → Create/Login user → Redirect to app
2. **Onboarding Flow**: User → GitHub OAuth → Select org → Create team → Sync repos
3. **Integration Flow**: Team admin → GitHub OAuth → Select org → Store credential

---

## 4. GitHub App Architecture

### Authentication Types

| Type | Use Case | Token Prefix |
|------|----------|--------------|
| **App (JWT)** | Manage app resources, get installation tokens | N/A |
| **Installation** | Background jobs, API calls for repos | `ghs_` |
| **User Access** | Actions on behalf of user | `ghu_` |

### Required Permissions (Equivalent to Current Scopes)

| Permission | Access Level | Purpose |
|------------|--------------|---------|
| **Repository: Contents** | Read | Fetch code, commits |
| **Repository: Pull requests** | Read | Fetch PRs, reviews |
| **Repository: Metadata** | Read | Repo info (automatic) |
| **Organization: Members** | Read | Sync org members |
| **Organization: Administration** | Read | Org settings (optional) |

### Webhook Events to Subscribe

| Event | Purpose |
|-------|---------|
| `pull_request` | PR opened, closed, merged, etc. |
| `pull_request_review` | Reviews submitted |
| `push` | Commits pushed |
| `installation` | App installed/uninstalled |
| `installation_repositories` | Repos added/removed |

---

## 5. Migration Strategy

### Option A: Parallel (Recommended)

Run both OAuth App and GitHub App simultaneously during transition.

```
Phase 1: Build GitHub App infrastructure
Phase 2: New customers use GitHub App
Phase 3: Migrate existing customers
Phase 4: Deprecate OAuth App
```

**Pros:**
- Zero downtime for existing customers
- Gradual rollout, catch issues early
- Rollback possible

**Cons:**
- More code to maintain temporarily
- Dual credential storage

### Option B: Big Bang

Switch all customers at once.

**Pros:**
- Simpler codebase (one path)
- Faster cleanup

**Cons:**
- Higher risk
- Requires coordinated migration
- Users must re-authorize

---

## 6. Implementation Plan

### Phase 1: GitHub App Creation & Infrastructure (Week 1-2)

#### 1.1 Create GitHub App

**Manual Steps:**
1. Go to GitHub → Settings → Developer settings → GitHub Apps
2. Create new GitHub App:
   - Name: "Tformance"
   - Homepage: https://tformance.com
   - Webhook URL: https://app.tformance.com/webhooks/github/app/
   - Webhook secret: Generate secure secret
3. Set permissions (see Section 4)
4. Subscribe to webhook events
5. Generate private key (download `.pem` file)

**Environment Variables:**
```bash
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
GITHUB_APP_WEBHOOK_SECRET=xxx
GITHUB_APP_CLIENT_ID=Iv1.xxx  # For user OAuth
GITHUB_APP_CLIENT_SECRET=xxx
```

#### 1.2 New Service Module

Create `apps/integrations/services/github_app.py`:

```python
"""GitHub App authentication and API service."""

import jwt
import time
from datetime import datetime, timedelta
from github import Github, GithubIntegration

class GitHubAppService:
    """Service for GitHub App authentication and operations."""

    def __init__(self):
        self.app_id = settings.GITHUB_APP_ID
        self.private_key = settings.GITHUB_APP_PRIVATE_KEY

    def get_jwt(self) -> str:
        """Generate JWT for app authentication (10 min expiry)."""
        payload = {
            "iat": int(time.time()),
            "exp": int(time.time()) + 600,
            "iss": self.app_id,
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def get_installation_token(self, installation_id: int) -> str:
        """Get installation access token for API calls."""
        integration = GithubIntegration(self.app_id, self.private_key)
        return integration.get_access_token(installation_id).token

    def get_installation_client(self, installation_id: int) -> Github:
        """Get authenticated PyGithub client for installation."""
        token = self.get_installation_token(installation_id)
        return Github(token)
```

#### 1.3 New Model for App Installations

```python
# apps/integrations/models.py

class GitHubAppInstallation(BaseTeamModel):
    """Tracks GitHub App installations per team."""

    installation_id = models.BigIntegerField(unique=True)
    account_type = models.CharField(max_length=20)  # "Organization" or "User"
    account_login = models.CharField(max_length=100)
    account_id = models.BigIntegerField()

    # Installation state
    is_active = models.BooleanField(default=True)
    suspended_at = models.DateTimeField(null=True, blank=True)

    # Permissions snapshot
    permissions = models.JSONField(default=dict)
    events = models.JSONField(default=list)

    # Tracked repositories (populated on install/update)
    repository_selection = models.CharField(max_length=20)  # "all" or "selected"

    class Meta:
        db_table = "integrations_github_app_installation"
```

#### 1.4 New Webhook Handler

```python
# apps/web/views.py - Add GitHub App webhook endpoint

@csrf_exempt
def github_app_webhook(request):
    """Handle GitHub App webhook events."""
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_github_webhook_signature(request.body, signature):
        return HttpResponseForbidden()

    event = request.headers.get("X-GitHub-Event")
    payload = json.loads(request.body)

    if event == "installation":
        handle_installation_event(payload)
    elif event == "installation_repositories":
        handle_repos_event(payload)
    elif event == "pull_request":
        handle_pr_event(payload)
    # ... more events

    return HttpResponse(status=200)
```

---

### Phase 2: Onboarding with GitHub App (Week 2-3)

#### 2.1 New Onboarding Flow

```
Current OAuth Flow:
1. User clicks "Connect GitHub"
2. Redirect to GitHub OAuth
3. User authorizes scopes
4. Callback with code → exchange for token
5. Store encrypted token
6. Select org → create team

New GitHub App Flow:
1. User clicks "Install Tformance App"
2. Redirect to GitHub App installation
3. User selects org + repos
4. GitHub redirects with installation_id
5. Store installation_id (no token storage!)
6. Team created from org
```

#### 2.2 Installation Callback

```python
# apps/onboarding/views.py

def github_app_callback(request):
    """Handle GitHub App installation callback."""
    installation_id = request.GET.get("installation_id")
    setup_action = request.GET.get("setup_action")  # "install" or "update"

    if not installation_id:
        messages.error(request, "Installation failed")
        return redirect("onboarding:start")

    # Fetch installation details via API
    app_service = GitHubAppService()
    installation = app_service.get_installation(installation_id)

    # Create or update team
    team = Team.objects.create(
        name=installation["account"]["login"],
        slug=slugify(installation["account"]["login"]),
    )

    # Store installation reference
    GitHubAppInstallation.objects.create(
        team=team,
        installation_id=installation_id,
        account_type=installation["account"]["type"],
        account_login=installation["account"]["login"],
        account_id=installation["account"]["id"],
        permissions=installation["permissions"],
        events=installation["events"],
        repository_selection=installation["repository_selection"],
    )

    return redirect("onboarding:select_repos", team_slug=team.slug)
```

---

### Phase 3: Background Jobs with Installation Tokens (Week 3-4)

#### 3.1 Update Sync Tasks

```python
# apps/integrations/tasks.py

@shared_task
def sync_repository_task(repo_id: int):
    """Sync repository using installation token."""
    repo = TrackedRepository.objects.get(id=repo_id)

    # Get installation for this team
    installation = GitHubAppInstallation.objects.get(team=repo.team)

    # Get fresh installation token (1 hour validity)
    app_service = GitHubAppService()
    client = app_service.get_installation_client(installation.installation_id)

    # Sync PRs
    github_repo = client.get_repo(repo.github_repo)
    # ... sync logic
```

#### 3.2 No More Per-Repo Webhook Setup!

With GitHub App, webhooks are automatic for all repos the app has access to.

```python
# DELETE: apps/integrations/services/github_webhooks.py (mostly)
# KEEP: Webhook signature verification
```

---

### Phase 4: User Authentication (Week 4-5)

GitHub Apps can also handle user authentication via OAuth, but with app-specific tokens.

#### 4.1 Update Login Flow

```python
# apps/auth/views.py

def github_app_login(request):
    """Initiate GitHub App OAuth for user login."""
    params = {
        "client_id": settings.GITHUB_APP_CLIENT_ID,  # App's client ID
        "redirect_uri": redirect_uri,
        "state": create_oauth_state({"flow": "login"}),
    }
    return redirect(f"https://github.com/login/oauth/authorize?{urlencode(params)}")
```

**Key Difference:** User access tokens from GitHub Apps:
- Expire in 8 hours (not indefinite)
- Have refresh tokens (6 month validity)
- Permissions are intersection of app permissions + user permissions

---

### Phase 5: Migrate Existing Customers (Week 5-6)

#### 5.1 Migration Script

```python
# apps/integrations/management/commands/migrate_to_github_app.py

class Command(BaseCommand):
    """Migrate teams from OAuth App to GitHub App."""

    def handle(self, *args, **options):
        teams_with_oauth = Team.objects.filter(
            integrationcredential__platform="github"
        ).exclude(
            githubappinstallation__isnull=False
        )

        for team in teams_with_oauth:
            self.stdout.write(f"Team {team.name} needs migration")
            # Send email to team admin with installation link
            send_migration_email(team)
```

#### 5.2 Migration Email

```
Subject: Action Required: Upgrade to Tformance GitHub App

Hi {team_admin},

We're upgrading our GitHub integration to use GitHub Apps for
better security and reliability.

Please install the Tformance app for your organization:
{installation_link}

Benefits:
- More secure (short-lived tokens)
- Simpler setup (no webhook issues)
- Better rate limits

Your current connection will continue working until {deadline}.
```

---

### Phase 6: Deprecate OAuth App (Week 6+)

1. Set deadline for OAuth deprecation
2. Send reminders to non-migrated teams
3. Disable new OAuth connections
4. Archive OAuth-related code

---

## 7. Dual-Support Period

During migration, support both authentication methods:

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

    # Fall back to OAuth credential
    try:
        credential = IntegrationCredential.objects.get(team=team, platform="github")
        return Github(credential.access_token)
    except IntegrationCredential.DoesNotExist:
        raise NoGitHubConnectionError(f"Team {team.slug} has no GitHub connection")
```

---

## 8. Testing Strategy

### Unit Tests

- JWT generation and validation
- Installation token refresh
- Webhook signature verification
- Migration script

### Integration Tests

- Full installation flow (mock GitHub API)
- Webhook event processing
- Sync with installation tokens

### E2E Tests

- Install app on test org
- Verify repos appear
- Verify webhooks received
- Verify PR sync works

---

## 9. Rollback Plan

If issues arise:

1. **Webhook failures**: Fall back to per-repo webhooks temporarily
2. **Token issues**: Use cached OAuth tokens
3. **Full rollback**: Re-enable OAuth flow, pause GitHub App installations

---

## 10. Timeline Summary

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1-2 | Infrastructure | GitHub App created, new services, models |
| 2-3 | Onboarding | New installation flow, callback handlers |
| 3-4 | Background Jobs | Sync tasks use installation tokens |
| 4-5 | User Auth | Login via GitHub App OAuth |
| 5-6 | Migration | Email campaigns, migration script |
| 6+ | Cleanup | Deprecate OAuth, archive code |

---

## 11. Decision Points

| Question | Recommendation |
|----------|----------------|
| **Public or Private App?** | Public (so any org can install) |
| **Parallel or Big Bang?** | Parallel (safer rollout) |
| **When to deprecate OAuth?** | 60 days after GitHub App launch |
| **Handle Copilot metrics?** | Requires separate permission, may need user OAuth still |

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users confused by new flow | Medium | Clear docs, in-app guidance |
| Installation webhook missed | High | Retry logic, reconciliation job |
| Token refresh failures | Medium | Fallback to re-installation prompt |
| Copilot API incompatible | Medium | Keep user OAuth for Copilot only |

---

## References

- [GitHub Apps Documentation](https://docs.github.com/en/apps/creating-github-apps)
- [Differences: GitHub Apps vs OAuth Apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/differences-between-github-apps-and-oauth-apps)
- [Authenticating with GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app)
- [Migrating OAuth Apps to GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/guides/migrating-oauth-apps-to-github-apps)
- [GitHub App Webhooks](https://docs.github.com/en/apps/creating-github-apps/writing-code-for-a-github-app/building-a-github-app-that-responds-to-webhook-events)

---

*Created: January 2026*
