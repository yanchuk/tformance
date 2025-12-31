# Security Remediation Tasks

**Last Updated:** 2025-12-31

## Progress Overview

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Critical Bug Fixes | ✅ Complete | 2/2 |
| Phase 2: Security Configuration | ✅ Complete | 5/5 |
| Phase 3: Privacy & Error Handling | Not Started | 0/3 |
| **Total** | **In Progress** | **7/10** |

---

## Phase 1: Critical Bug Fixes (TDD) ✅ COMPLETE

### 1.1 Fix GitHub Webhook Multi-Team Bug ✅

**Priority:** CRITICAL | **Effort:** Low | **TDD Required:** Yes

#### RED Phase ✅
- [x] Extended `apps/web/tests/test_webhooks.py` with `TestGitHubWebhookMultiTeam` class
- [x] Test: multi-team webhook with correct signature → processes for right team
- [x] Test: multi-team webhook with invalid signature → 401 error
- [x] Test: regression test - 3 teams tracking same repo
- [x] Verified tests FAIL with `MultipleObjectsReturned`

#### GREEN Phase ✅
- [x] Changed `.get()` to `.filter()` in `apps/web/views.py:189-208`
- [x] Added signature validation loop to find matching team
- [x] Return 401 if no signature matches any tracked repo
- [x] Verified all 4 tests PASS

#### REFACTOR Phase ✅
- [x] Code is clean and minimal - no refactoring needed
- [x] All 17 webhook tests pass (no regressions)

**Files Modified:**
- `apps/web/views.py:189-208` (multi-team signature validation)
- `apps/web/tests/test_webhooks.py:376-522` (new test class)

---

### 1.2 Encrypt Webhook Secret Field ✅

**Priority:** HIGH | **Effort:** Low | **TDD Required:** Yes

#### RED Phase ✅
- [x] Added tests in `apps/integrations/tests/test_models.py`
- [x] `test_webhook_secret_is_encrypted_in_database` - verifies Fernet encryption
- [x] `test_webhook_secret_decrypts_correctly_after_save_and_reload`
- [x] `test_webhook_validation_works_with_encrypted_secret`
- [x] Verified encryption test FAILS (raw value == plaintext)

#### GREEN Phase ✅
- [x] Changed `CharField` to `EncryptedTextField` in `apps/integrations/models.py:112-115`
- [x] Created migration `0017_encrypt_webhook_secret.py`
- [x] Verified all 3 tests PASS

#### REFACTOR Phase ✅
- [x] All 29 webhook + integration tests pass
- [x] No refactoring needed

**Files Modified:**
- `apps/integrations/models.py:112-115` (EncryptedTextField)
- `apps/integrations/migrations/0017_encrypt_webhook_secret.py` (new)
- `apps/integrations/tests/test_models.py:395-476` (new tests)

---

## Phase 2: Security Configuration ✅ COMPLETE

### 2.1 Lock Down Django-Hijack ✅

- [x] Added `HIJACK_PERMISSION_CHECK = "hijack.permissions.superusers_only"` to settings
- Location: `tformance/settings.py:318-320`

---

### 2.2 Add Login Rate Limiting ✅

- [x] Added production rate limits with else clause:
  ```python
  ACCOUNT_RATE_LIMITS = {
      "login_failed": "5/m,20/h",
      "signup": "5/m",
      "password_reset": "3/h",
  }
  ```
- [x] Removed DEBUG condition - rate limits apply in production only
- Location: `tformance/settings.py:300-307`

---

### 2.3 POST-Only Logout ✅

- [x] Changed `ACCOUNT_LOGOUT_ON_GET = False` in settings
- [x] Updated logout links to use POST forms in:
  - `templates/web/components/app_nav_menu_items.html:30-38`
  - `templates/teams/accept_invite.html:51-56`
  - `templates/onboarding/base.html:14-20`
- Location: `tformance/settings.py:290-291`

---

### 2.4 Reduce Webhook Replay Window ✅

- [x] Changed `WEBHOOK_REPLAY_CACHE_TIMEOUT = 300` (was 3600)
- Location: `apps/web/views.py:37-39`

---

### 2.5 Configure Session Timeout ✅

- [x] Added explicit session settings:
  ```python
  SESSION_COOKIE_AGE = 86400 * 7  # 7 days
  SESSION_SAVE_EVERY_REQUEST = True  # Extend on activity
  ```
- Location: `tformance/settings.py:245-246`

---

## Phase 3: Privacy & Error Handling (TDD) - PENDING

### 3.1 Add LLM Opt-Out Setting

**Priority:** MEDIUM | **Effort:** Medium | **TDD Required:** Yes

#### RED Phase (Write Failing Tests)
- [ ] Test: Team with `llm_analysis_enabled=False` skips LLM analysis
- [ ] Test: Team with `llm_analysis_enabled=True` runs LLM analysis
- [ ] Test: New teams default to enabled
- [ ] Verify tests FAIL

#### GREEN Phase (Make Tests Pass)
- [ ] Add `llm_analysis_enabled = models.BooleanField(default=True)` to Team model
- [ ] Create migration
- [ ] Add check in `apps/integrations/tasks.py` LLM task
- [ ] Verify tests PASS

**Files:**
- `apps/teams/models.py` (modify)
- `apps/teams/migrations/XXXX_llm_opt_out.py` (create)
- `apps/integrations/tasks.py` (modify)

---

### 3.2 Sanitize Error Messages in Celery Tasks

**Priority:** MEDIUM | **Effort:** Medium | **TDD Required:** Yes

#### RED Phase (Write Failing Tests)
- [ ] Create `apps/utils/tests/test_errors.py`
- [ ] Test: ConnectionError → "Connection failed..."
- [ ] Test: Timeout → "Request timed out..."
- [ ] Test: HTTPError 401 → "Authentication failed..."
- [ ] Verify tests FAIL

#### GREEN Phase (Make Tests Pass)
- [ ] Create `apps/utils/errors.py` with `sanitize_error()` function
- [ ] Implement error type mapping
- [ ] Verify tests PASS

**Files:**
- `apps/utils/errors.py` (create)
- `apps/utils/tests/test_errors.py` (create)
- `apps/integrations/tasks.py` (modify)

---

### 3.3 Add JSON Parsing Error Handling

**Priority:** MEDIUM | **Effort:** Low | **TDD Required:** Yes

#### RED Phase (Write Failing Tests)
- [ ] Test: malformed JSON returns None
- [ ] Test: valid JSON parses correctly
- [ ] Verify tests FAIL

#### GREEN Phase (Make Tests Pass)
- [ ] Add try-except around `.json()` calls
- [ ] Log errors with response URL
- [ ] Verify tests PASS

**Files:**
- `apps/integrations/services/copilot_metrics.py` (modify)
- `apps/integrations/webhooks/slack_interactions.py` (modify)

---

## Future Backlog (Deferred)

### CSP Nonces
- [ ] Research django-csp or custom middleware
- [ ] Audit all inline scripts in templates
- [ ] Generate per-request nonces
- [ ] Update CSP header in middleware

---

## Completion Checklist

Before merging:

- [x] Phase 1 TDD complete (RED → GREEN → REFACTOR)
- [x] Phase 2 configuration changes applied
- [ ] Phase 3 TDD complete
- [ ] `make test` passes (full test suite)
- [ ] `make ruff` passes (linting)
- [ ] No new security warnings in logs
- [ ] Manual testing of critical flows:
  - [ ] GitHub webhook with multiple teams
  - [ ] Logout flow (POST-only)
  - [ ] Rate limiting (try 6 failed logins)
- [ ] Code reviewed and approved
