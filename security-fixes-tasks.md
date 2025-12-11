# Security Fixes - Task Checklist

**Last Updated:** 2025-12-11

## Phase 1: Critical Security Defaults (HIGH)

### 1.1 Remove SECRET_KEY Default
- [ ] Edit `tformance/settings.py:30` - remove default value
- [ ] Update `.env.example` with SECRET_KEY placeholder
- [ ] Update local `.env` with valid SECRET_KEY
- [ ] Verify app starts with env var set
- [ ] Verify app fails gracefully without env var

### 1.2 Remove Test Encryption Key Default
- [ ] Edit `tformance/settings.py:632-635` - remove conditional default
- [ ] Add test encryption key to `conftest.py`
- [ ] Update `.env.example` with INTEGRATION_ENCRYPTION_KEY placeholder
- [ ] Update local `.env` with valid encryption key
- [ ] Run tests to verify they still pass

### 1.3 Change DEBUG Default to False
- [ ] Edit `tformance/settings.py:33` - change default to False
- [ ] Update local `.env` to explicitly set DEBUG=True
- [ ] Verify development mode works with explicit DEBUG=True
- [ ] Document in `.env.example`

### 1.4 Change ALLOWED_HOSTS Default to Empty
- [ ] Edit `tformance/settings.py:36` - change default to []
- [ ] Update local `.env` with ALLOWED_HOSTS=localhost,127.0.0.1
- [ ] Verify app works with explicit ALLOWED_HOSTS
- [ ] Document in `.env.example`

---

## Phase 2: Session Token Encryption (HIGH)

### 2.1 Encrypt Tokens in Session
- [ ] Update `apps/onboarding/views.py:163` - encrypt before storing
- [ ] Update `apps/onboarding/views.py:164` - orgs don't need encryption (not sensitive)
- [ ] Update `apps/onboarding/views.py:224` - decrypt when retrieving

### 2.2 Test Session Encryption
- [ ] Write test for encrypted session storage
- [ ] Write test for decryption on retrieval
- [ ] Test full onboarding flow end-to-end
- [ ] Verify existing sessions handled gracefully

---

## Phase 3: Safe HTML Patterns (MEDIUM)

### 3.1 Update TeamSignupForm
- [ ] Edit `apps/teams/forms.py:4` - change import to format_html
- [ ] Edit `apps/teams/forms.py:30-34` - use format_html pattern
- [ ] Test signup form renders correctly
- [ ] Verify link is clickable and correct

### 3.2 Audit Other mark_safe Usage
- [ ] Review `apps/web/templatetags/form_tags.py:10`
- [ ] Review `apps/content/blocks.py:13`
- [ ] Update if user input could reach mark_safe
- [ ] Document any intentional mark_safe usage

---

## Phase 4: Error Message Sanitization (MEDIUM)

### 4.1 GitHub OAuth Errors
- [ ] Find all `messages.error()` in `apps/integrations/views.py`
- [ ] Replace exception details with generic messages
- [ ] Add `logger.error()` with full exception info
- [ ] Test error scenarios show generic messages

### 4.2 Jira OAuth Errors
- [ ] Find all `messages.error()` for Jira in views
- [ ] Replace exception details with generic messages
- [ ] Add `logger.error()` with full exception info

### 4.3 Onboarding Errors
- [ ] Find all `messages.error()` in `apps/onboarding/views.py`
- [ ] Replace exception details with generic messages
- [ ] Verify error UX is still helpful

---

## Phase 5: Cookie Security Configuration (MEDIUM)

### 5.1 Add Cookie Security Flags
- [ ] Add `SESSION_COOKIE_HTTPONLY = True` to settings
- [ ] Add `SESSION_COOKIE_SECURE = not DEBUG` to settings
- [ ] Add `SESSION_COOKIE_SAMESITE = "Lax"` to settings
- [ ] Add `CSRF_COOKIE_HTTPONLY = True` to settings
- [ ] Add `CSRF_COOKIE_SECURE = not DEBUG` to settings
- [ ] Add `CSRF_COOKIE_SAMESITE = "Lax"` to settings
- [ ] Test login/logout flow works
- [ ] Test CSRF protection works

---

## Phase 6: Rate Limiting (MEDIUM)

### 6.1 Install Package
- [ ] Run `uv add django-ratelimit`
- [ ] Verify package installed

### 6.2 Add Rate Limiting to OAuth Callbacks
- [ ] Add `@ratelimit` to `github_callback` in integrations/views.py
- [ ] Add `@ratelimit` to `jira_callback` in integrations/views.py
- [ ] Add `@ratelimit` to `github_callback` in onboarding/views.py
- [ ] Configure rate limit response (403 or custom template)

### 6.3 Test Rate Limiting
- [ ] Write test that triggers rate limit
- [ ] Verify rate limit returns appropriate response
- [ ] Test that normal usage doesn't trigger limits

---

## Final Verification

### Security Checklist
- [ ] Run full test suite: `make test`
- [ ] Search for hardcoded secrets: `grep -r "django-insecure" .`
- [ ] Search for test keys in non-test code
- [ ] Verify no exception details in user-facing messages
- [ ] Test app starts with minimal required env vars

### Documentation
- [ ] Update `.env.example` with all required vars
- [ ] Update README if needed
- [ ] Document rate limiting in API docs (if applicable)

### Deployment
- [ ] Update staging env vars
- [ ] Update production env vars
- [ ] Deploy to staging and test
- [ ] Deploy to production

---

## Notes

- **Effort Legend:** S = Small (<1hr), M = Medium (1-3hr), L = Large (3-8hr)
- **Priority:** Complete HIGH items first, then MEDIUM
- **Dependencies:** Phase 6 requires `django-ratelimit` package
