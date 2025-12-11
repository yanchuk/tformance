# Security Fixes Implementation Plan

**Last Updated:** 2025-12-11

## Executive Summary

This plan addresses **3 HIGH severity** and **6 MEDIUM severity** security vulnerabilities identified in the tformance Django application. The fixes focus on:
- Removing insecure defaults for cryptographic keys
- Encrypting sensitive data in session storage
- Improving error message handling to prevent information disclosure
- Using safer HTML escaping patterns
- Adding rate limiting to OAuth endpoints

---

## Current State Analysis

### HIGH Severity Issues

| ID | Issue | Location | Risk |
|----|-------|----------|------|
| H1 | Hardcoded SECRET_KEY default | `settings.py:30` | Session hijacking, CSRF forgery |
| H2 | Test encryption key in production code | `settings.py:632-635` | OAuth tokens decryptable with known key |
| H3 | Unencrypted OAuth tokens in session | `onboarding/views.py:163-164` | Token exposure if session compromised |

### MEDIUM Severity Issues

| ID | Issue | Location | Risk |
|----|-------|----------|------|
| M1 | `mark_safe()` usage pattern | `teams/forms.py:30-34` | Potential XSS if inputs change |
| M2 | Error messages expose details | `integrations/views.py:290-291` | Information disclosure |
| M3 | DEBUG default is True | `settings.py:33` | Stack traces in production |
| M4 | ALLOWED_HOSTS allows all | `settings.py:36` | Host header attacks |
| M5 | Missing explicit cookie flags | `settings.py` | Cookie security not explicit |
| M6 | No rate limiting on OAuth | OAuth endpoints | Brute force/DoS attacks |

---

## Proposed Future State

After implementation:
- **Zero hardcoded secrets** - All sensitive values require environment variables
- **Encrypted session data** - OAuth tokens encrypted before session storage
- **Safe HTML rendering** - Use `format_html()` instead of `mark_safe()`
- **Generic error messages** - No implementation details exposed to users
- **Secure defaults** - DEBUG=False, empty ALLOWED_HOSTS by default
- **Rate limiting** - OAuth endpoints protected against abuse

---

## Implementation Phases

### Phase 1: Critical Security Defaults (HIGH Priority)

**Goal:** Remove all hardcoded secrets and insecure defaults

#### 1.1 Remove SECRET_KEY Default
- **File:** `tformance/settings.py:30`
- **Change:** Remove default value, require env variable
- **Effort:** S

```python
# Before
SECRET_KEY = env("SECRET_KEY", default="django-insecure-QlTEH9dbN4QwLcjOBInlUGAVq0qPEwNeXswz3l1c")

# After
SECRET_KEY = env("SECRET_KEY")  # Required - no default
```

#### 1.2 Remove Test Encryption Key Default
- **File:** `tformance/settings.py:632-635`
- **Change:** Move test key to test settings, never in production code
- **Effort:** S

```python
# Before
INTEGRATION_ENCRYPTION_KEY = env(
    "INTEGRATION_ENCRYPTION_KEY",
    default="r8pmePXvrfFN4L_IjvTbZP3hWPTIN0y4KDw2wbuIRYg=" if "test" in sys.argv else None,
)

# After
INTEGRATION_ENCRYPTION_KEY = env("INTEGRATION_ENCRYPTION_KEY", default=None)
# Test key moved to conftest.py or test settings
```

#### 1.3 Change DEBUG Default to False
- **File:** `tformance/settings.py:33`
- **Change:** Default to False (secure by default)
- **Effort:** S

```python
# Before
DEBUG = env.bool("DEBUG", default=True)

# After
DEBUG = env.bool("DEBUG", default=False)
```

#### 1.4 Change ALLOWED_HOSTS Default to Empty
- **File:** `tformance/settings.py:36`
- **Change:** Empty list by default
- **Effort:** S

```python
# Before
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# After
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
```

---

### Phase 2: Session Token Encryption (HIGH Priority)

**Goal:** Encrypt OAuth tokens before storing in session

#### 2.1 Create Session Encryption Utility
- **File:** `apps/integrations/services/encryption.py`
- **Change:** Add `encrypt_for_session()` and `decrypt_from_session()` functions
- **Effort:** M

#### 2.2 Update Onboarding Views
- **File:** `apps/onboarding/views.py:163-164`
- **Change:** Encrypt token before session storage, decrypt when needed
- **Effort:** M

```python
# Before
request.session[ONBOARDING_TOKEN_KEY] = access_token

# After
from apps.integrations.services.encryption import encrypt
request.session[ONBOARDING_TOKEN_KEY] = encrypt(access_token)
```

#### 2.3 Update Token Retrieval
- **File:** `apps/onboarding/views.py:224`
- **Change:** Decrypt token when retrieving from session
- **Effort:** S

---

### Phase 3: Safe HTML Patterns (MEDIUM Priority)

**Goal:** Replace `mark_safe()` with safer alternatives

#### 3.1 Update TeamSignupForm
- **File:** `apps/teams/forms.py:30-34`
- **Change:** Use `format_html()` instead of `mark_safe()`
- **Effort:** S

```python
# Before
from django.utils.safestring import mark_safe
link = '<a class="link" href={} target="_blank">{}</a>'.format(...)
self.fields["terms_agreement"].label = mark_safe(_("I agree to the {terms_link}").format(terms_link=link))

# After
from django.utils.html import format_html
link = format_html('<a class="link" href="{}" target="_blank">{}</a>', reverse("web:terms"), _("Terms and Conditions"))
self.fields["terms_agreement"].label = format_html(_("I agree to the {}"), link)
```

#### 3.2 Audit Other mark_safe Usage
- **Files:** `apps/web/templatetags/form_tags.py`, `apps/content/blocks.py`
- **Change:** Review and update as needed
- **Effort:** S

---

### Phase 4: Error Message Sanitization (MEDIUM Priority)

**Goal:** Prevent information disclosure in error messages

#### 4.1 Update OAuth Error Handling
- **File:** `apps/integrations/views.py`
- **Change:** Log full errors internally, show generic messages to users
- **Effort:** M

```python
# Before
except (GitHubOAuthError, KeyError, Exception) as e:
    messages.error(request, f"Failed to exchange authorization code: {str(e)}")

# After
except (GitHubOAuthError, KeyError, Exception) as e:
    logger.error(f"OAuth token exchange failed: {e}", exc_info=True)
    messages.error(request, "Failed to connect. Please try again.")
```

#### 4.2 Review All Error Messages
- **Files:** All views in `apps/integrations/`, `apps/onboarding/`
- **Change:** Replace exception details with generic messages
- **Effort:** M

---

### Phase 5: Cookie Security Configuration (MEDIUM Priority)

**Goal:** Explicitly configure secure cookie settings

#### 5.1 Add Explicit Cookie Flags
- **File:** `tformance/settings.py`
- **Change:** Add explicit secure cookie configuration
- **Effort:** S

```python
# Add to settings.py
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
```

---

### Phase 6: Rate Limiting (MEDIUM Priority)

**Goal:** Protect OAuth endpoints from abuse

#### 6.1 Install django-ratelimit
- **Change:** Add `django-ratelimit` to dependencies
- **Effort:** S

```bash
uv add django-ratelimit
```

#### 6.2 Add Rate Limiting to OAuth Endpoints
- **Files:** `apps/integrations/views.py`, `apps/onboarding/views.py`
- **Change:** Add `@ratelimit` decorator to OAuth callbacks
- **Effort:** M

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='10/m', method=['GET', 'POST'])
@login_and_team_required
def github_callback(request, team_slug):
    ...
```

#### 6.3 Add Rate Limiting to Jira Endpoints
- **File:** `apps/integrations/views.py`
- **Change:** Add rate limiting to Jira OAuth endpoints
- **Effort:** S

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking dev environment | Medium | Medium | Update .env.example, document required vars |
| Test failures | Medium | Low | Update conftest.py with test encryption key |
| Rate limit false positives | Low | Low | Start with generous limits, monitor |
| Session data migration | Low | Medium | Encrypt new sessions, clear old on next login |

---

## Success Metrics

- [ ] All tests pass after changes
- [ ] No hardcoded secrets in codebase (verified by grep)
- [ ] Zero `mark_safe()` with user-controllable input
- [ ] All OAuth endpoints have rate limiting
- [ ] Error messages contain no stack traces or implementation details
- [ ] Cookie security flags explicitly set
- [ ] Security audit re-run shows no HIGH/MEDIUM issues

---

## Dependencies

- `django-ratelimit` package for Phase 6
- Environment variable updates in all deployment environments
- `.env.example` documentation updates

---

## Testing Requirements

### Unit Tests
- Test encryption/decryption of session tokens
- Test rate limiting decorator behavior
- Test error message sanitization

### Integration Tests
- OAuth flow with encrypted session tokens
- Rate limiting triggers correctly
- Application starts with required env vars

### Security Tests
- Verify no secrets in git history
- Verify error responses don't leak info
- Verify rate limits work under load
