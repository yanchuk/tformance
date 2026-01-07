# GitHub App Migration - Context

**Last Updated: 2026-01-07**

## Current Status

**Phase 1: COMPLETE ✅**
- GitHub App primary authentication working
- OAuth reduced to Copilot-only scope
- All 132 tests passing

**Phase 2: Edge Case Hardening ✅ COMPLETE**
- 13 edge cases implemented (EC-1 through EC-13, EC-15 through EC-18)
- 1 edge case config pending (EC-14: Enable webhooks in GitHub App settings)
- ~110 total tests passing
- Focus: production-readiness, graceful error handling, revocation detection

---

## Key Files for Edge Cases

### Token Management (#1, #4, #7)
| File | Purpose | Edge Cases |
|------|---------|------------|
| `apps/integrations/models.py:566-650` | `GitHubAppInstallation.get_access_token()` | #1 race condition, #7 is_active check |
| `apps/integrations/services/github_app.py` | Token fetching | #4 token expiry |

### Auth Error Handling (#2, #3, #15, #16)
| File | Purpose | Edge Cases |
|------|---------|------------|
| `apps/integrations/_task_modules/github_sync.py` | Sync tasks | #2 neither auth, #15 401 retry loop |
| `apps/integrations/services/github_graphql_sync/_utils.py` | GraphQL token | #3 silent None |
| `apps/integrations/services/copilot_metrics.py` | Copilot sync | #16 401 not checked |

### Installation Lifecycle (#5, #6, #8, #9, #11, #12, #13)
| File | Purpose | Edge Cases |
|------|---------|------------|
| `apps/integrations/webhooks/github_app.py` | Webhook handler | #5 mid-sync uninstall, #6 reinstall, #11 duplicate webhooks, #13 account type change |
| `apps/integrations/models.py` | GitHubAppInstallation | #9 suspended vs deleted errors, #12 refresh_from_db |
| `apps/integrations/management/commands/cleanup_orphaned_installations.py` | Cleanup orphans | #8 orphaned installations |

### Revocation Handling (#14, #17, #18)
| File | Purpose | Edge Cases |
|------|---------|------------|
| `apps/web/urls.py:23-24` | Webhook routes (exist!) | #14 re-enable webhooks |
| `apps/integrations/models.py` | IntegrationCredential revocation fields | #17 revocation tracking |
| `apps/integrations/services/status.py` | Status service | #18 revocation status in API |

### Auth Fallback (#10)
| File | Purpose | Edge Cases |
|------|---------|------------|
| `apps/integrations/models.py` | TrackedRepository.access_token | #10 App → OAuth → Error fallback chain |

---

## Key Decisions (Phase 2)

### Decision 1: Database Locking for Token Refresh
**Decision**: Use `select_for_update()` for race condition prevention.

**Rationale**:
- PostgreSQL row locks work across Celery threads (`--pool=threads`)
- Lock timeout is minimal (< 100ms typical)
- Prevents duplicate GitHub API calls

**Code Pattern**:
```python
with transaction.atomic():
    locked = Model.objects.select_for_update().get(pk=self.pk)
    # ... modify and save locked ...
```

### Decision 2: Fail Fast on 401
**Decision**: Treat 401 as permanent failure, not transient.

**Rationale**:
- 401 = "Bad credentials" = token revoked or installation removed
- Retrying wastes resources and delays error notification
- Mark installation as `is_active=False` immediately

**Code Pattern**:
```python
except GithubException as e:
    if e.status == 401:
        installation.is_active = False
        installation.save()
        raise TokenRevokedError(...)
    elif e.status == 403:
        raise self.retry(exc=e, countdown=60)  # Rate limit - retry
```

### Decision 3: Webhooks for Revocation Detection
**Decision**: Re-enable GitHub App webhooks (routes already exist).

**Rationale**:
- Real-time notification when user uninstalls App
- More reliable than checking 401 errors
- Routes exist at `apps/web/urls.py` - just need to enable in GitHub

**Configuration**:
```bash
GITHUB_APP_WEBHOOK_SECRET="<generate with secrets.token_hex(32)>"
```

---

## Dependencies

### Celery Worker Configuration
```bash
# Development
celery worker --pool=threads --concurrency=4

# Production
celery worker --pool=threads --concurrency=10
```

**Important**: `select_for_update()` works with thread pool because PostgreSQL row locks are connection-level, not process-level.

### Environment Variables to Add
```bash
# GitHub App Webhook (required for revocation detection)
GITHUB_APP_WEBHOOK_SECRET="<generate>"
```

---

## Test Strategy

### Unit Tests for Edge Cases

```python
# apps/integrations/tests/test_github_app_installation.py

class TestGetAccessTokenRaceCondition:
    """Edge case #1: Race condition in token refresh."""

    def test_concurrent_requests_only_refresh_once(self):
        """Multiple threads should not all call GitHub API."""
        # Use threading to simulate concurrent requests
        # Verify only one GitHub API call made

    def test_second_request_gets_cached_token(self):
        """Second concurrent request should get cached token."""

class TestGetAccessTokenIsActiveCheck:
    """Edge case #7: Check is_active before returning token."""

    def test_raises_if_not_active(self):
        """GitHubAppDeactivatedError raised for inactive installation."""

    def test_returns_token_if_active(self):
        """Token returned for active installation."""
```

```python
# apps/integrations/tests/test_github_sync.py

class TestSyncAuthErrorHandling:
    """Edge cases #2, #15: Auth error handling in sync tasks."""

    def test_clear_error_when_no_auth(self):
        """User-friendly error when neither App nor OAuth configured."""

    def test_401_fails_fast_no_retry(self):
        """401 error should not trigger Celery retry."""

    def test_401_marks_installation_inactive(self):
        """401 error should set is_active=False."""

    def test_403_retries_with_backoff(self):
        """403 (rate limit) should retry with countdown."""
```

```python
# apps/integrations/tests/test_graphql_utils.py

class TestGetAccessTokenExplicitError:
    """Edge case #3: Explicit error instead of None."""

    def test_raises_when_no_auth(self):
        """GitHubAuthError raised when no authentication available."""

    def test_error_includes_repo_name(self):
        """Error message should include repository name."""
```

### Integration Tests

```python
# apps/integrations/tests/test_webhook_handler.py

class TestInstallationWebhook:
    """Edge cases #5, #6: Webhook handling for installation events."""

    def test_installation_deleted_sets_inactive(self):
        """Webhook sets is_active=False when installation deleted."""

    def test_installation_suspended_sets_timestamp(self):
        """Webhook sets suspended_at when installation suspended."""

    def test_reinstall_migrates_tracked_repos(self):
        """New installation inherits TrackedRepository records."""
```

---

## Error Classes to Add

```python
# apps/integrations/exceptions.py

class GitHubAppDeactivatedError(Exception):
    """Raised when GitHubAppInstallation is no longer active."""
    pass

class GitHubAuthError(Exception):
    """Raised when no valid authentication is available for a repository."""
    pass

class TokenRevokedError(Exception):
    """Raised when GitHub token has been revoked."""
    pass
```

---

## Webhook Events to Handle

| Event | Action |
|-------|--------|
| `installation.created` | Create/update GitHubAppInstallation |
| `installation.deleted` | Set `is_active=False` |
| `installation.suspended` | Set `suspended_at` timestamp |
| `installation.unsuspended` | Clear `suspended_at` |
| `installation_repositories.added` | (Optional) Log new repos available |
| `installation_repositories.removed` | (Optional) Deactivate TrackedRepository |

---

## Rollback Plan

If edge case fixes cause issues:
1. Revert specific edge case commit
2. Database state unchanged (no new migrations for CRITICAL/HIGH)
3. Webhooks can be disabled in GitHub App settings instantly

---

## API Reference

### PyGithub Exception Handling
```python
from github import GithubException

try:
    # GitHub API call
except GithubException as e:
    e.status  # HTTP status code (401, 403, 404, etc.)
    e.data    # Response body as dict
```

### Common Status Codes
| Code | Meaning | Action |
|------|---------|--------|
| 401 | Bad credentials | Fail fast, mark revoked |
| 403 | Rate limit OR forbidden | Check for rate limit, retry if so |
| 404 | Not found | Resource doesn't exist |
| 422 | Validation failed | Check request parameters |

---

## Implementation Notes (MEDIUM/LOW Edge Cases)

### EC-8: Orphaned Installations Cleanup
**File Created**: `apps/integrations/management/commands/cleanup_orphaned_installations.py`

```bash
# Preview orphans older than 24 hours
python manage.py cleanup_orphaned_installations --dry-run

# Delete orphans older than 48 hours
python manage.py cleanup_orphaned_installations --hours=48
```

### EC-9: Suspended vs Deleted Error Messages
Added `_get_deactivated_error_message()` helper to `GitHubAppInstallation`:
```python
def _get_deactivated_error_message(self) -> str:
    if self.suspended_at:
        return "GitHub App installation for {login} was suspended by GitHub..."
    else:
        return "GitHub App installation for {login} was removed..."
```

### EC-10: Auth Fallback Chain
`TrackedRepository.access_token` now implements fallback:
```python
@property
def access_token(self) -> str:
    # 1. Try App installation
    if self.app_installation is not None:
        try:
            return self.app_installation.get_access_token()
        except GitHubAppDeactivatedError:
            pass  # Fall back to OAuth

    # 2. Fall back to OAuth
    if self.integration and self.integration.credential:
        return self.integration.credential.access_token

    # 3. Neither available
    raise GitHubAuthError(f"Repository {self.full_name} has no valid authentication.")
```

### EC-11: Duplicate Webhook Handling
Changed webhook handler from `create()` to `update_or_create()`:
```python
defaults = {...}
if team:
    defaults["team"] = team  # Only set if reinstall scenario

new_installation, created = GitHubAppInstallation.objects.update_or_create(
    installation_id=installation_id,
    defaults=defaults,
)
```

### EC-12: Concurrent Deactivation Detection
Added `refresh_from_db()` to detect webhook-triggered deactivation:
```python
def get_access_token(self) -> str:
    # EC-12: Refresh is_active from DB to detect webhook deactivation
    self.refresh_from_db(fields=["is_active", "suspended_at"])
    if not self.is_active:
        raise GitHubAppDeactivatedError(self._get_deactivated_error_message())
    # ... rest of method
```

### EC-13: Account Type Change Warning
Logs warning when GitHub user converts to organization:
```python
new_account_type = account.get("type", "")
existing_installation = GitHubAppInstallation.objects.filter(installation_id=installation_id).first()
if existing_installation and existing_installation.account_type != new_account_type:
    logger.warning(
        f"Account type changed for installation {installation_id}: "
        f"'{existing_installation.account_type}' → '{new_account_type}'"
    )
```

### EC-17: IntegrationCredential Revocation Fields
Added 3 fields with migration `0023_add_revocation_fields_to_credential.py`:
```python
is_revoked = models.BooleanField(default=False)
revoked_at = models.DateTimeField(null=True, blank=True)
revocation_reason = models.CharField(max_length=255, blank=True, default="")
```

### EC-18: Status Service Revocation Reporting
Updated `GitHubStatus` TypedDict and `get_team_integration_status()`:
```python
class GitHubStatus(TypedDict):
    connected: bool
    org_name: str | None
    member_count: int
    repo_count: int
    is_revoked: bool  # NEW
    error: str | None  # NEW

# Checks both App installation and OAuth credential:
if app_installation and not app_installation.is_active:
    is_revoked = True
    error = "GitHub App was uninstalled. Please reconnect."
if credential and credential.is_revoked:
    is_revoked = True
    error = "OAuth access was revoked. Please reconnect."
```

---

## New Test Files Created

| File | Tests | Edge Cases |
|------|-------|------------|
| `test_cleanup_orphaned_installations.py` | 5 | EC-8 |
| `test_github_app_installation.py` (added) | 36 | EC-1, EC-5, EC-7, EC-9, EC-12 |
| `test_tracked_repository.py` (added) | 10 | EC-10 |
| `test_github_app_webhooks.py` (added) | 7 | EC-6, EC-11, EC-13 |
| `test_models.py` (added) | 3 | EC-17 |
| `test_status_service.py` (added) | 12 | EC-18 |

---

## Remaining Work

**EC-14: Enable Webhooks (Config Only)**

No code changes needed. Steps:
1. Generate webhook secret: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Add to `.env`: `GITHUB_APP_WEBHOOK_SECRET="<generated>"`
3. Add to Heroku: `heroku config:set GITHUB_APP_WEBHOOK_SECRET="<generated>"`
4. Enable webhooks in GitHub App settings:
   - Webhook URL: `https://tformance.com/webhooks/github-app/`
   - Subscribe to: `installation` events (created, deleted, suspended, unsuspended)
