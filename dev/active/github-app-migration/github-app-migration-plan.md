# GitHub App Migration Plan

**Last Updated: 2026-01-07**

## Executive Summary

Migrate Tformance from GitHub OAuth to GitHub App as the **primary authentication** method for accessing GitHub data. This supports the critical business claim: **"We don't have access to your code"** by using minimal read-only permissions without Contents access.

**Current Status: Phase 1 COMPLETE ✅**
- GitHub App is primary authentication
- OAuth reduced to Copilot-only scope
- All tests passing (49 GitHub App tests, 28 onboarding tests, 55 OAuth tests)

**Current Work: Phase 2 - Edge Case Hardening**
- 18 edge cases identified across token management, installation lifecycle, sync tasks, and revocation handling
- Focus on production-readiness and graceful error handling

---

## Architecture

**Dual Auth Architecture:**
- **GitHub App (Primary)**: PRs, commits, reviews, files, members - minimal read-only permissions
- **GitHub OAuth (Optional)**: Copilot metrics only - requires `manage_billing:copilot` scope

**GitHub App Permissions (MINIMAL):**
- **Repository**: Pull requests (Read-only) - NO Contents!
- **Organization**: Members (Read-only)
- **Account**: Email addresses (Read-only)
- **Webhooks**: Enabled (for revocation detection - routes already exist)

---

## Phase 2: Edge Case Implementation

### Priority Matrix

| Priority | Edge Cases | Effort | Focus |
|----------|-----------|--------|-------|
| **CRITICAL** | #1, #2, #3 (code), #14 (config) | 2-3 hours | Token safety, auth errors |
| **HIGH** | #4, #5, #6, #7, #15, #16 | 6-8 hours | Sync resilience, revocation |
| **MEDIUM** | #8, #9, #10, #11, #17, #18 | 4-5 hours | Cleanup, UI status |
| **LOW** | #12, #13 | 1-2 hours | Nice-to-have |

**Total Estimated Effort: ~14-18 hours**

---

### CRITICAL Edge Cases

#### #1: Race Condition in Token Refresh
**Location:** `apps/integrations/models.py` GitHubAppInstallation.get_access_token()
**Problem:** Multiple concurrent requests can call GitHub API simultaneously when token expires
**Fix:** Add database locking with `select_for_update()`:
```python
def get_access_token(self) -> str:
    from django.db import transaction

    # Quick check without lock
    if self._token_is_valid():
        return self.cached_token

    # Acquire lock before refresh
    with transaction.atomic():
        locked_self = GitHubAppInstallation.objects.select_for_update().get(pk=self.pk)
        if locked_self._token_is_valid():
            return locked_self.cached_token
        # ... refresh token ...
```

#### #2: TrackedRepository with Neither Auth
**Location:** `apps/integrations/_task_modules/github_sync.py`
**Problem:** `GitHubIntegration.objects.get()` raises DoesNotExist with no helpful error
**Fix:** Explicit check with user-friendly error:
```python
if not app_installation:
    integration = GitHubIntegration.objects.filter(team=team).first()
    if not integration:
        raise GitHubSyncError(
            f"Team {team.name} has no GitHub connection. "
            "Please reconnect via Integrations settings."
        )
```

#### #3: _get_access_token() Returns None Silently
**Location:** `apps/integrations/services/github_graphql_sync/_utils.py`
**Problem:** Returns `None` when both auth methods missing, causing cryptic API errors
**Fix:** Raise explicit exception:
```python
if not tracked_repo.app_installation and not (tracked_repo.integration and tracked_repo.integration.credential):
    raise GitHubAuthError(
        f"Repository {tracked_repo.full_name} has no valid authentication. "
        f"Re-add the repository via Integrations settings."
    )
```

#### #14: Re-enable GitHub App Webhooks
**Location:** `apps/web/urls.py` (routes already exist!)
**Current State:** Webhook routes exist but webhooks disabled in GitHub App settings
**Fix:** Configuration only (no code changes):
1. Go to GitHub → Settings → Developer Settings → GitHub Apps → Tformance
2. Enable "Webhook" (check "Active")
3. Set Webhook URL: `https://tformance.com/webhooks/github-app/`
4. Generate webhook secret, add `GITHUB_APP_WEBHOOK_SECRET` to env vars

---

### HIGH Edge Cases

#### #4: Token Expires During Long Sync
**Location:** `apps/integrations/_task_modules/github_sync.py`
**Problem:** Token obtained once at task start, expires after 1 hour during multi-repo sync
**Fix:** Pass `installation_id` instead of `token`, refresh per-repo

#### #5: User Uninstalls App Mid-Sync
**Location:** Running tasks don't check `is_active` after webhook updates
**Problem:** Running sync tasks fail with 401/403 instead of graceful message
**Fix:** Check `is_active` at task start and before token refresh

#### #6: User Reinstalls App (New Installation ID)
**Location:** Old TrackedRepository records still point to old installation
**Problem:** Syncs fail because old installation is `is_active=False`
**Fix:** In webhook handler, migrate repos to new installation

#### #7: Installation Deleted After Token Cached
**Location:** `get_access_token()` uses cached token without checking `is_active`
**Problem:** Cached token used even after installation deleted
**Fix:** Check `is_active` before returning cached token

#### #15: 401 Errors Treated as Transient (Retry Loop)
**Location:** `apps/integrations/_task_modules/github_sync.py`, `copilot.py`
**Problem:** 401 "Bad credentials" (revoked token) triggers retry loop
**Fix:** Detect 401 and fail fast, mark installation as revoked

#### #16: Copilot Sync Only Checks 403, Not 401
**Location:** `apps/integrations/services/copilot_metrics.py`
**Problem:** Only checks for 403 (no Copilot license), ignores 401 (token revoked)
**Fix:** Add 401 check with clear error message

---

### MEDIUM Edge Cases

#### #8: Orphaned Installations Without Team
**Problem:** Installation with `team=None` stays in DB forever
**Fix:** Add management command or periodic task to cleanup

#### #9: Suspended vs Deleted Not Distinguished
**Problem:** User can't tell if installation is recoverable (suspended) or permanent (deleted)
**Fix:** Use `suspended_at` in error messaging

#### #10: TrackedRepository with Both App AND OAuth
**Problem:** No fallback when App becomes unavailable
**Fix:** Add explicit fallback logic in `access_token` property

#### #11: User Cancels GitHub App Install Mid-Flow
**Problem:** Unique constraint violation on retry
**Fix:** Use `update_or_create` instead of `create`

#### #17: No Revocation Tracking on IntegrationCredential
**Problem:** Can't persist "this OAuth token is revoked"
**Fix:** Add `is_revoked`, `revoked_at`, `revocation_reason` fields

#### #18: UI Doesn't Show Revocation Status
**Problem:** Dashboard shows "Connected ✓" even after revocation
**Fix:** Check `is_active` and `is_revoked` in status view

---

### LOW Edge Cases

#### #12: Race Between Webhook and Sync Check
**Problem:** Sync task grabs reference, webhook updates DB
**Fix:** Refresh from DB before using token

#### #13: Account Type Changes (User→Org)
**Problem:** GitHub user converts to organization
**Fix:** Log warning when `account_type` changes

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token expiry during long sync | Medium | High | Edge case #4: Refresh per-repo |
| Race condition on token refresh | Low | Medium | Edge case #1: Database locking |
| Installation deleted by user | Low | Medium | Edge cases #5, #7, #14: Webhook + checks |
| 401 retry loop wastes resources | Medium | Medium | Edge case #15: Fail fast on 401 |

---

## Success Metrics

1. **Reliability**: No silent failures - all auth errors have clear messages
2. **Performance**: Token refresh adds < 100ms latency (database lock)
3. **Resilience**: Long syncs complete despite token expiry
4. **UX**: Users see clear status when access is revoked
5. **Test Coverage**: 90%+ coverage on edge case code

---

## TDD Workflow

Each edge case follows Red-Green-Refactor:

1. **RED**: Write failing test first
2. **GREEN**: Write minimum code to pass
3. **REFACTOR**: Clean up while keeping tests green

Test files to modify:
- `apps/integrations/tests/test_github_app.py`
- `apps/integrations/tests/test_github_app_installation.py`
- `apps/integrations/tests/test_github_sync.py`
- `apps/integrations/tests/test_graphql_utils.py`
