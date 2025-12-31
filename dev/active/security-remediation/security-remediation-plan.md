# Security Remediation Plan

**Last Updated:** 2025-12-31

## Executive Summary

This plan addresses security vulnerabilities identified during a comprehensive architecture review of the Tformance platform. The remediation follows strict TDD methodology and prioritizes critical bugs over configuration improvements.

**Key Decisions:**
- GitHub OAuth only in production (no email verification needed)
- CSP nonces deferred to future sprint
- All fixes follow Red-Green-Refactor TDD cycle

---

## Current State Analysis

### Security Posture: GOOD with targeted improvements needed

| Area | Current State | Target State |
|------|--------------|--------------|
| Token Encryption | Excellent (Fernet AES-128) | No change |
| Team Isolation | Excellent (BaseTeamModel) | No change |
| Webhook Security | Bug: Multi-team lookup broken | Fix with signature-based routing |
| Webhook Secret | Plain text in DB | Encrypted at rest |
| Hijack | Unrestricted (any staff) | Superusers only |
| Rate Limiting | OAuth only | All auth endpoints |
| LLM Privacy | No opt-out | Per-team opt-out |
| Error Handling | Leaks internal details | Sanitized messages |

---

## Implementation Phases

### Phase 1: Critical Bug Fixes (TDD)

**Duration:** 1-2 days

| Task | Effort | Files |
|------|--------|-------|
| 1.1 Fix webhook multi-team bug | Low | `apps/web/views.py`, `apps/web/tests/test_webhooks.py` |
| 1.2 Encrypt webhook secret | Low | `apps/integrations/models.py`, migration |

### Phase 2: Security Configuration

**Duration:** 1 day

| Task | Effort | Files |
|------|--------|-------|
| 2.1 Lock down hijack | Very Low | `tformance/settings.py` |
| 2.2 Add login rate limiting | Low | `tformance/settings.py` |
| 2.3 POST-only logout | Low | `tformance/settings.py`, templates |
| 2.4 Reduce replay window | Very Low | `apps/web/views.py` |
| 2.5 Session timeout config | Very Low | `tformance/settings.py` |

### Phase 3: Privacy & Error Handling (TDD)

**Duration:** 2-3 days

| Task | Effort | Files |
|------|--------|-------|
| 3.1 LLM opt-out setting | Medium | `apps/teams/models.py`, `apps/integrations/tasks.py` |
| 3.2 Error sanitization | Medium | `apps/utils/errors.py` (new), `apps/integrations/tasks.py` |
| 3.3 JSON parsing safety | Low | `apps/integrations/services/copilot_metrics.py`, `apps/integrations/webhooks/slack_interactions.py` |

### Future Backlog (Deferred)

| Task | Reason for Deferral |
|------|-------------------|
| CSP Nonces | Requires template changes, acceptable risk for MVP |
| Account Lockout | django-axes for enterprise tier |
| MFA Enforcement | Future enterprise feature |
| LLM PII Redaction | Future enterprise feature |

---

## Detailed Task Specifications

### 1.1 Fix GitHub Webhook Multi-Team Bug

**Problem:** `TrackedRepository.objects.get(github_repo_id=id)` fails when multiple teams track same repo.

**TDD Approach:**
1. **RED:** Write test for multi-team webhook scenario
2. **GREEN:** Change to `.filter()` + signature validation loop
3. **REFACTOR:** Extract signature-based routing to service

**Acceptance Criteria:**
- [ ] Test exists for multi-team webhook delivery
- [ ] Test exists for invalid signature rejection
- [ ] Webhook processes for correct team based on signature match
- [ ] No 500 error when multiple teams track same repo
- [ ] Performance acceptable (< 100ms for 10 candidates)

**Implementation:**
```python
# Before (broken)
tracked_repo = TrackedRepository.objects.get(github_repo_id=github_repo_id)

# After (fixed)
tracked_repos = TrackedRepository.objects.filter(
    github_repo_id=github_repo_id
).select_related("integration")

for tracked_repo in tracked_repos:
    if validate_webhook_signature(
        request.body, signature_header, tracked_repo.integration.webhook_secret
    ):
        break
else:
    return JsonResponse({"error": "Invalid signature"}, status=401)
```

---

### 1.2 Encrypt Webhook Secret Field

**Problem:** `webhook_secret` stored as plain `CharField` while other credentials use `EncryptedTextField`.

**TDD Approach:**
1. **RED:** Write test asserting encrypted storage
2. **GREEN:** Change field type, create migration
3. **REFACTOR:** Verify webhook validation still works

**Acceptance Criteria:**
- [ ] `webhook_secret` uses `EncryptedTextField`
- [ ] Migration encrypts existing data
- [ ] Webhook signature validation still passes
- [ ] Decryption works correctly in view

**Migration Strategy:**
- RunPython operation to encrypt existing plain-text secrets
- No downtime required

---

### 2.1 Lock Down Django-Hijack

**Change:** Add setting to restrict hijack to superusers.

**Acceptance Criteria:**
- [ ] `HIJACK_PERMISSION_CHECK` set to superusers_only
- [ ] Non-superuser staff cannot hijack
- [ ] Superuser can still hijack

---

### 2.2 Add Login Rate Limiting

**Change:** Configure allauth rate limits for production.

**Acceptance Criteria:**
- [ ] Rate limits only disabled for TESTING (not DEBUG)
- [ ] Login failures: 5/min, 20/hour
- [ ] Signup: 5/min
- [ ] Password reset: 3/hour

---

### 2.3 POST-Only Logout

**Change:** Disable GET logout to prevent CSRF-triggered logouts.

**Acceptance Criteria:**
- [ ] `ACCOUNT_LOGOUT_ON_GET = False`
- [ ] All logout links use POST forms
- [ ] E2E tests updated for POST logout

---

### 3.1 LLM Opt-Out Setting

**Problem:** PR data sent to Groq with no way for teams to opt out.

**TDD Approach:**
1. **RED:** Test that disabled teams skip LLM analysis
2. **GREEN:** Add `llm_analysis_enabled` field, check in task
3. **REFACTOR:** Add admin UI toggle

**Acceptance Criteria:**
- [ ] `Team.llm_analysis_enabled` field (default True)
- [ ] LLM task skips analysis when disabled
- [ ] Team settings page shows toggle
- [ ] Existing teams default to enabled

---

### 3.2 Error Message Sanitization

**Problem:** `str(exc)` exposes internal details to users.

**TDD Approach:**
1. **RED:** Test that specific exceptions map to user-friendly messages
2. **GREEN:** Create `sanitize_error()` utility
3. **REFACTOR:** Apply to all Celery tasks

**Acceptance Criteria:**
- [ ] `apps/utils/errors.py` with `sanitize_error(exc)` function
- [ ] Maps common exceptions to user-friendly messages
- [ ] Full exception logged internally
- [ ] Applied to all `last_sync_error` fields

**Error Mapping:**
| Exception | User Message |
|-----------|-------------|
| `ConnectionError` | "Connection failed. Please try again." |
| `Timeout` | "Request timed out. Please try again." |
| `HTTPError 401` | "Authentication failed. Please reconnect." |
| `HTTPError 403` | "Access denied. Check permissions." |
| `HTTPError 404` | "Resource not found." |
| Default | "An error occurred. Please try again or contact support." |

---

### 3.3 JSON Parsing Safety

**Problem:** `.json()` calls without error handling can crash on malformed responses.

**TDD Approach:**
1. **RED:** Test malformed JSON returns None/error gracefully
2. **GREEN:** Wrap in try-except with logging
3. **REFACTOR:** Create utility function if pattern repeated

**Acceptance Criteria:**
- [ ] `JSONDecodeError` caught and logged
- [ ] Function returns `None` or raises custom exception
- [ ] No unhandled crashes from external API responses

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Migration breaks existing secrets | Low | High | Test migration on staging first |
| Multi-team webhook routing slow | Low | Medium | Add performance test, index if needed |
| Rate limits too aggressive | Medium | Low | Monitor false positives, adjust limits |
| Logout change breaks UX | Low | Medium | Update all templates before deploying |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| All TDD tests passing | 100% |
| No security regressions | 0 new vulnerabilities |
| Webhook processing time | < 100ms for 10 team candidates |
| Error message sanitization coverage | 100% of Celery tasks |

---

## Dependencies

- `apps/utils/fields.py` - `EncryptedTextField` already exists
- `apps/integrations/services/github_webhooks.py` - `validate_webhook_signature()` exists
- Django migrations framework
- pytest + pytest-django for TDD

---

## Testing Strategy

All changes follow TDD Red-Green-Refactor:

1. **Unit Tests:** Each fix has dedicated test file/class
2. **Integration Tests:** Webhook flow tested end-to-end
3. **E2E Tests:** Logout flow tested in Playwright

**Test Files:**
- `apps/web/tests/test_github_webhook.py` (new/extend)
- `apps/integrations/tests/test_models.py` (extend)
- `apps/utils/tests/test_errors.py` (new)
- `apps/teams/tests/test_models.py` (extend)
