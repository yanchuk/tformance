# GitHub App Migration - Tasks

**Last Updated: 2026-01-07**

## Phase 1: Initial Implementation (COMPLETE ✅)

All initial implementation tasks completed:
- ✅ Token management with caching
- ✅ TrackedRepository FK to GitHubAppInstallation
- ✅ Onboarding flow using App install
- ✅ GraphQL sync using App tokens
- ✅ OAuth scope reduced to Copilot-only
- ✅ All 132 tests passing

---

## Phase 2: Edge Case Hardening

### CRITICAL Priority

#### EC-1: Race Condition in Token Refresh ✅ COMPLETE
- **Effort**: M
- **File**: `apps/integrations/models.py`
- **Dependencies**: None

**TDD Steps:**
- [x] RED: Write test `test_uses_select_for_update_locking`
- [x] RED: Write test `test_second_call_returns_cached_without_api_call`
- [x] GREEN: Add `select_for_update()` locking to `get_access_token()`
- [x] GREEN: Add `_token_is_valid()` helper method
- [x] Tests pass (30 tests in test_github_app_installation.py)

**Acceptance Criteria:**
- [x] Multiple concurrent requests only trigger one GitHub API call
- [x] Database row lock prevents race condition
- [x] Lock timeout is reasonable (< 1 second)
- [x] Tests pass

---

#### EC-2: TrackedRepository with Neither Auth ✅ COMPLETE
- **Effort**: S
- **File**: `apps/integrations/_task_modules/github_sync.py`
- **Dependencies**: None

**TDD Steps:**
- [x] RED: Write test `test_sync_raises_clear_error_when_no_auth`
- [x] RED: Write test `test_error_includes_integrations_settings_guidance`
- [x] GREEN: Updated error message to include team name and guidance
- [x] Tests pass (2 tests in test_historical_sync.py::TestSyncHistoricalDataNoAuth)

**Acceptance Criteria:**
- [x] Clear error message: "Team {name} has no GitHub connection"
- [x] Error includes guidance: "Please reconnect via Integrations settings"
- [x] No DoesNotExist exception reaches user
- [x] Tests pass

---

#### EC-3: _get_access_token() Returns None Silently ✅ COMPLETE
- **Effort**: S
- **File**: `apps/integrations/services/github_graphql_sync/_utils.py`
- **Dependencies**: None

**TDD Steps:**
- [x] RED: Write test `test_get_access_token_raises_when_no_auth`
- [x] RED: Write test `test_get_access_token_error_includes_guidance`
- [x] GREEN: Raise `GitHubAuthError` instead of returning None
- [x] Import exception from `apps/integrations/exceptions.py`
- [x] Tests pass (6 tests in test_github_graphql_sync_utils.py)

**Acceptance Criteria:**
- [x] `GitHubAuthError` raised when no auth available
- [x] Error message includes repository `full_name`
- [x] Error includes guidance to re-add repository
- [x] Tests pass

---

#### EC-7: Check is_active Before Returning Cached Token ✅ COMPLETE
- **Effort**: S
- **File**: `apps/integrations/models.py`
- **Dependencies**: EC-1

**TDD Steps:**
- [x] RED: Write test `test_get_access_token_raises_when_inactive`
- [x] RED: Write test `test_get_access_token_returns_token_when_active`
- [x] GREEN: Check `is_active` before returning cached token
- [x] GREEN: Raise `GitHubAppDeactivatedError` if not active
- [x] Tests pass (3 tests in TestGetAccessTokenIsActiveCheck)

**Acceptance Criteria:**
- [x] `is_active` checked before returning cached token
- [x] Stale cached tokens not used after installation removed
- [x] Clear error message for deactivated installations
- [x] Tests pass

---

#### EC-14: Re-enable GitHub App Webhooks ⏳ CONFIG READY
- **Effort**: S (Config only)
- **File**: None (GitHub App settings)
- **Dependencies**: None

**Code Status:** ✅ COMPLETE - Webhook handler exists at `apps/integrations/webhooks/github_app.py`

**Configuration Steps (manual):**
- [x] Add `GITHUB_APP_WEBHOOK_SECRET` to `.env.example`
- [ ] Generate webhook secret: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Add secret to `.env` (local) and Heroku config vars (prod)
- [ ] Enable webhooks in GitHub App settings
- [ ] Set webhook URL: `https://tformance.com/webhooks/github-app/`
- [ ] Subscribe to `installation` events (created, deleted, suspended, unsuspended)

**Acceptance Criteria:**
- [x] Webhook handler implemented (handles all installation events)
- [x] `.env.example` documented
- [ ] Webhook secret configured in production
- [ ] GitHub App sends webhook on installation changes

---

### HIGH Priority

#### EC-4: Token Expires During Long Sync ✅ COMPLETE
- **Effort**: M
- **File**: `apps/integrations/_task_modules/github_sync.py`, `apps/integrations/services/onboarding_sync.py`
- **Dependencies**: EC-1

**TDD Steps:**
- [x] RED: Write tests for per-repo token refresh behavior
- [x] GREEN: Remove upfront token fetch from `sync_historical_data_task`
- [x] GREEN: Make `github_token` optional in `OnboardingSyncService`
- [x] REFACTOR: Document that GraphQL sync functions handle token refresh via `_get_access_token()`
- [x] Tests pass (3 new tests, 79 total edge case tests)

**Acceptance Criteria:**
- [x] Long syncs (>1 hour) complete successfully (tokens refreshed per-repo by GraphQL)
- [x] Token refreshed before each repo sync via `_get_access_token()`
- [x] No 401 errors due to token expiry mid-sync
- [x] Tests pass

**Implementation Notes:**
- GraphQL sync functions already called `_get_access_token()` per-repo
- Removed wasteful upfront token fetch from `sync_historical_data_task`
- Task now verifies auth exists via `.exists()` check (no API call)
- `OnboardingSyncService.github_token` is now optional (backward compatible)

---

#### EC-5: User Uninstalls App Mid-Sync ✅ COMPLETE
- **Effort**: M
- **File**: `apps/integrations/_task_modules/github_sync.py`
- **Dependencies**: EC-14

**TDD Steps:**
- [x] RED: Write test `test_sync_repository_task_handles_deactivated_installation`
- [x] RED: Write test `test_get_access_token_raises_when_installation_deactivated_mid_sync`
- [x] GREEN: Updated `is_permanent_github_auth_failure()` to include `GitHubAppDeactivatedError`
- [x] GREEN: Sync task now fails fast with clear message (no retries)
- [x] Tests pass (2 new tests + all 43 historical sync tests)

**Acceptance Criteria:**
- [x] Running sync fails gracefully with clear message
- [x] Webhook immediately marks installation inactive (already implemented)
- [x] Error message: "Installation is no longer active. Please reinstall the GitHub App."
- [x] Tests pass

**Implementation Notes:**
- Added `GitHubAppDeactivatedError` and `GitHubAuthError` to `is_permanent_github_auth_failure()`
- Sync task now uses exception message directly (user-friendly guidance)
- No retry loop for deactivated installations - fails fast

---

#### EC-6: User Reinstalls App (New Installation ID) ✅ COMPLETE
- **Effort**: M
- **File**: `apps/integrations/webhooks/github_app.py`
- **Dependencies**: EC-5

**TDD Steps:**
- [x] RED: Write test `test_reinstall_migrates_tracked_repos`
- [x] RED: Write test `test_reinstall_deactivates_old_installation`
- [x] RED: Write test `test_reinstall_inherits_team_from_old_installation`
- [x] RED: Write test `test_fresh_install_has_no_team`
- [x] GREEN: Check for old installation with same `account_id`
- [x] GREEN: Migrate TrackedRepository records to new installation
- [x] GREEN: Inherit team from old installation
- [x] GREEN: Deactivate old installation
- [x] Tests pass (4 new tests, 19 total webhook tests)

**Acceptance Criteria:**
- [x] New installation linked to existing TrackedRepository records
- [x] Old installation marked as `is_active=False`
- [x] Sync resumes without user re-selecting repos
- [x] Tests pass

**Implementation Notes:**
- On `installation.created` webhook, check for old installation with same `account_id`
- If found: inherit team, deactivate old, migrate TrackedRepository records
- Fresh installs still have `team=None` (set during onboarding callback)

---

#### EC-7: Installation Deleted After Token Cached
- **Effort**: S
- **File**: `apps/integrations/models.py`
- **Dependencies**: EC-1

**TDD Steps:**
- [ ] RED: Write test `test_get_access_token_checks_is_active_first`
- [ ] GREEN: Check `is_active` before returning cached token
- [ ] GREEN: Raise `GitHubAppDeactivatedError` if not active
- [ ] REFACTOR: Combine with EC-5 implementation

**Acceptance Criteria:**
- [ ] `is_active` checked before returning cached token
- [ ] Stale cached tokens not used after installation removed
- [ ] Clear error message for deactivated installations
- [ ] Tests pass

---

#### EC-15: 401 Errors Treated as Transient (Retry Loop)
- **Effort**: M
- **File**: `apps/integrations/_task_modules/github_sync.py`
- **Dependencies**: None

**TDD Steps:**
- [ ] RED: Write test `test_401_does_not_retry`
- [ ] RED: Write test `test_401_marks_installation_inactive`
- [ ] RED: Write test `test_403_rate_limit_retries_with_backoff`
- [ ] GREEN: Catch `GithubException` and check status code
- [ ] GREEN: Fail fast on 401, retry on 403
- [ ] REFACTOR: Extract error handling to helper function

**Acceptance Criteria:**
- [ ] 401 error does not trigger Celery retry
- [ ] 401 error marks installation as inactive
- [ ] 403 (rate limit) retries with 60s countdown
- [ ] Clear error message: "GitHub access revoked"
- [ ] Tests pass

---

#### EC-16: Copilot Sync Only Checks 403, Not 401
- **Effort**: S
- **File**: `apps/integrations/services/copilot_metrics.py`
- **Dependencies**: None

**TDD Steps:**
- [ ] RED: Write test `test_copilot_sync_raises_on_401`
- [ ] RED: Write test `test_401_includes_reconnect_message`
- [ ] GREEN: Add 401 status code check before `raise_for_status()`
- [ ] GREEN: Raise `TokenRevokedError` with clear message

**Acceptance Criteria:**
- [ ] 401 error raises `TokenRevokedError`
- [ ] Error message: "GitHub OAuth token was revoked. Please reconnect."
- [ ] 403 still raises `CopilotMetricsError`
- [ ] Tests pass

---

### MEDIUM Priority

#### EC-8: Orphaned Installations Without Team ✅ COMPLETE
- **Effort**: S
- **File**: `apps/integrations/management/commands/cleanup_orphaned_installations.py` (NEW)
- **Dependencies**: None

**TDD Steps:**
- [x] RED: Write test `test_cleanup_command_deletes_orphaned_installations`
- [x] RED: Write test `test_cleanup_preserves_recent_installations`
- [x] RED: Write test `test_dry_run_does_not_delete`
- [x] RED: Write test `test_handles_no_orphans`
- [x] RED: Write test `test_custom_hours_threshold`
- [x] GREEN: Create `cleanup_orphaned_installations` management command
- [x] GREEN: Delete installations older than 24 hours without team
- [x] GREEN: Add dry-run option
- [x] Tests pass (5 tests in test_cleanup_orphaned_installations.py)

**Acceptance Criteria:**
- [x] Management command cleans up orphaned installations
- [x] Preserves installations < 24 hours old (user might be mid-flow)
- [x] Dry-run option to preview deletions
- [x] Custom `--hours` threshold option
- [x] Tests pass

---

#### EC-9: Suspended vs Deleted Not Distinguished ✅ COMPLETE
- **Effort**: S
- **File**: `apps/integrations/models.py`
- **Dependencies**: EC-5

**TDD Steps:**
- [x] RED: Write test `test_error_message_for_suspended_installation`
- [x] RED: Write test `test_error_message_for_deleted_installation`
- [x] GREEN: Add `_get_deactivated_error_message()` helper method
- [x] GREEN: Check `suspended_at` in error messages
- [x] GREEN: Provide different guidance for suspended vs deleted
- [x] Tests pass (2 tests in TestSuspendedVsDeletedErrorMessages)

**Acceptance Criteria:**
- [x] Suspended: "GitHub App installation for {login} was suspended by GitHub. Please contact your organization administrator to resolve this issue."
- [x] Deleted: "GitHub App installation for {login} was removed. Please reinstall the GitHub App to continue syncing."
- [x] Tests pass

---

#### EC-10: TrackedRepository with Both App AND OAuth ✅ COMPLETE
- **Effort**: S
- **File**: `apps/integrations/models.py`
- **Dependencies**: EC-1

**TDD Steps:**
- [x] RED: Write test `test_access_token_prefers_app_installation`
- [x] RED: Write test `test_access_token_falls_back_to_oauth_when_app_deactivated`
- [x] RED: Write test `test_access_token_falls_back_to_oauth_when_no_app_installation`
- [x] RED: Write test `test_access_token_raises_when_neither_available`
- [x] GREEN: Update `access_token` property with fallback logic
- [x] GREEN: Catch `GitHubAppDeactivatedError` and fall back to OAuth
- [x] Tests pass (10 tests in test_tracked_repository.py)

**Acceptance Criteria:**
- [x] App installation used when available and active
- [x] Falls back to OAuth credential if App unavailable/deactivated
- [x] Raises `GitHubAuthError` if neither available
- [x] Tests pass

**Implementation Notes:**
- Fallback chain: App → OAuth → GitHubAuthError
- When App deactivated, silently falls back to OAuth (no error surfaced)
- Updated existing test to expect OAuth fallback behavior

---

#### EC-11: User Cancels GitHub App Install Mid-Flow ✅ COMPLETE
- **Effort**: S
- **File**: `apps/integrations/webhooks/github_app.py`
- **Dependencies**: None

**TDD Steps:**
- [x] RED: Write test `test_handle_installation_created_handles_duplicate_webhook`
- [x] GREEN: Replace `create()` with `update_or_create()` in webhook handler
- [x] GREEN: Only set team in defaults if we have one (don't override existing team with None)
- [x] Tests pass (6 tests in test_github_app_webhooks.py)

**Acceptance Criteria:**
- [x] Retry after cancel doesn't cause unique constraint error
- [x] Existing installation updated instead of duplicate created
- [x] Tests pass

**Implementation Notes:**
- Changed webhook handler from `create()` to `update_or_create()`
- Team field only set in defaults if reinstall scenario (not None override)
- Handles GitHub webhook retries gracefully

---

#### EC-17: No Revocation Tracking on IntegrationCredential ✅ COMPLETE
- **Effort**: M
- **File**: `apps/integrations/models.py`
- **Dependencies**: None

**TDD Steps:**
- [x] RED: Write test `test_revocation_fields_exist_with_defaults`
- [x] RED: Write test `test_can_mark_credential_as_revoked`
- [x] RED: Write test `test_revocation_reason_can_be_set`
- [x] GREEN: Add `is_revoked`, `revoked_at`, `revocation_reason` fields
- [x] GREEN: Create migration `0023_add_revocation_fields_to_credential.py`
- [x] Tests pass (3 tests in TestIntegrationCredentialModel)

**Acceptance Criteria:**
- [x] New fields added to `IntegrationCredential` model
- [x] Migration created and applies cleanly
- [x] Revocation status persisted in database
- [x] Tests pass

---

#### EC-18: UI Doesn't Show Revocation Status ✅ COMPLETE
- **Effort**: M
- **File**: `apps/integrations/services/status.py`
- **Dependencies**: EC-17

**TDD Steps:**
- [x] RED: Write test `test_github_status_shows_revoked_when_app_inactive`
- [x] RED: Write test `test_github_status_shows_revoked_when_oauth_revoked`
- [x] RED: Write test `test_github_status_not_revoked_when_active`
- [x] GREEN: Add `is_revoked` and `error` fields to `GitHubStatus` TypedDict
- [x] GREEN: Check `is_active` on App installation and `is_revoked` on credential
- [x] GREEN: Return appropriate error messages
- [x] Tests pass (12 tests in test_status_service.py)

**Acceptance Criteria:**
- [x] Status shows `is_revoked=True` when App inactive
- [x] Status shows `is_revoked=True` when OAuth credential revoked
- [x] Clear error message explains what happened
- [x] Tests pass

**Implementation Notes:**
- Updated `GitHubStatus` TypedDict with `is_revoked: bool` and `error: str | None`
- Checks both App installation `is_active` and credential `is_revoked`
- Error messages guide user to reconnect

---

### LOW Priority

#### EC-12: Race Between Webhook and Sync Check ✅ COMPLETE
- **Effort**: S
- **File**: `apps/integrations/models.py`
- **Dependencies**: EC-5

**TDD Steps:**
- [x] RED: Write test `test_detects_deactivation_from_database`
- [x] GREEN: Add `refresh_from_db(fields=["is_active", "suspended_at"])` to `get_access_token()`
- [x] Tests pass (1 test in TestRaceBetweenWebhookAndSyncCheck)

**Acceptance Criteria:**
- [x] Fresh installation state used for each sync operation
- [x] Detects webhook-triggered deactivation mid-sync
- [x] Tests pass

**Implementation Notes:**
- Added `refresh_from_db()` at start of `get_access_token()` to detect concurrent DB updates
- If webhook marks installation inactive while sync holds reference, next token fetch fails correctly

---

#### EC-13: Account Type Changes (User→Org) ✅ COMPLETE
- **Effort**: S
- **File**: `apps/integrations/webhooks/github_app.py`
- **Dependencies**: EC-14

**TDD Steps:**
- [x] RED: Write test `test_handle_installation_created_logs_warning_on_account_type_change`
- [x] GREEN: Log warning when `account_type` changes
- [x] Tests pass (7 tests in test_github_app_webhooks.py)

**Acceptance Criteria:**
- [x] Warning logged when account type changes
- [x] No crash on account type change
- [x] Tests pass

**Implementation Notes:**
- Checks existing installation for `account_type` before update
- Logs warning with old and new account types for admin attention
- Warning includes account login for identification

---

## Summary

| Priority | Tasks | Status |
|----------|-------|--------|
| **CRITICAL** | EC-1 ✅, EC-2 ✅, EC-3 ✅, EC-7 ✅, EC-14 ⏳ | ✅ Code Complete (config pending) |
| **HIGH** | EC-4 ✅, EC-5 ✅, EC-6 ✅, EC-15 ✅, EC-16 ✅ | ✅ Complete |
| **MEDIUM** | EC-8 ✅, EC-9 ✅, EC-10 ✅, EC-11 ✅, EC-17 ✅, EC-18 ✅ | ✅ Complete |
| **LOW** | EC-12 ✅, EC-13 ✅ | ✅ Complete |

**Completed CRITICAL Tasks (2026-01-07):**
- ✅ EC-1: Race condition fixed with `select_for_update()`
- ✅ EC-2: Clear error message with team name
- ✅ EC-3: `GitHubAuthError` raised instead of None
- ✅ EC-7: `is_active` check before returning cached token
- ⏳ EC-14: Webhook handler ready, config pending

**Completed HIGH Tasks (2026-01-07):**
- ✅ EC-4: Token refresh per-repo (removed upfront fetch)
- ✅ EC-5: Sync fails fast when App deactivated mid-sync
- ✅ EC-6: Reinstall migrates repos, inherits team, deactivates old
- ✅ EC-15: 401 errors fail fast, mark installation inactive
- ✅ EC-16: Copilot sync raises `TokenRevokedError` on 401

**Completed MEDIUM Tasks (2026-01-07):**
- ✅ EC-8: Management command `cleanup_orphaned_installations` with dry-run
- ✅ EC-9: Distinct error messages for suspended vs deleted installations
- ✅ EC-10: Auth fallback chain (App → OAuth → GitHubAuthError)
- ✅ EC-11: Webhook uses `update_or_create` for duplicate handling
- ✅ EC-17: Added `is_revoked`, `revoked_at`, `revocation_reason` to IntegrationCredential
- ✅ EC-18: Status service returns revocation status with error messages

**Completed LOW Tasks (2026-01-07):**
- ✅ EC-12: `refresh_from_db()` detects concurrent DB updates
- ✅ EC-13: Warning logged when account type changes

**Tests Added:** 78 new edge case tests passing (~110 total with utils)

**Implementation Order:**
1. ~~CRITICAL first (2-3 hours)~~ ✅ Done
2. ~~HIGH (5 of 5 done)~~ ✅ Complete
3. ~~MEDIUM for GA readiness (4-5 hours)~~ ✅ Complete
4. ~~LOW as time permits (1-2 hours)~~ ✅ Complete

**Remaining Work:**
- ⏳ EC-14: Enable webhooks in GitHub App settings (config only, no code changes)

**Total Effort: ~14-18 hours (completed)**
