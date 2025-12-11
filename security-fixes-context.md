# Security Fixes - Context & Reference

**Last Updated:** 2025-12-11

## Key Files to Modify

### Settings
| File | Purpose | Changes Needed |
|------|---------|----------------|
| `tformance/settings.py` | Django settings | Remove insecure defaults, add cookie flags |
| `.env.example` | Env template | Document required security vars |
| `conftest.py` | Test config | Add test encryption key |

### OAuth & Authentication
| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/onboarding/views.py` | Onboarding OAuth flow | Encrypt session tokens |
| `apps/integrations/views.py` | Integration OAuth flows | Rate limiting, error sanitization |
| `apps/integrations/services/encryption.py` | Encryption utils | Already good, may add helpers |

### Forms & Templates
| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/teams/forms.py` | Team signup form | Replace mark_safe with format_html |
| `apps/web/templatetags/form_tags.py` | Form rendering | Review mark_safe usage |
| `apps/content/blocks.py` | Wagtail blocks | Review mark_safe usage |

---

## Critical Code Locations

### H1: SECRET_KEY Default (Line 30)
```python
# tformance/settings.py:30
SECRET_KEY = env("SECRET_KEY", default="django-insecure-QlTEH9dbN4QwLcjOBInlUGAVq0qPEwNeXswz3l1c")
```

### H2: Test Encryption Key (Lines 632-635)
```python
# tformance/settings.py:632-635
INTEGRATION_ENCRYPTION_KEY = env(
    "INTEGRATION_ENCRYPTION_KEY",
    default="r8pmePXvrfFN4L_IjvTbZP3hWPTIN0y4KDw2wbuIRYg=" if "test" in sys.argv else None,
)
```

### H3: Unencrypted Session Token (Lines 163-164)
```python
# apps/onboarding/views.py:163-164
request.session[ONBOARDING_TOKEN_KEY] = access_token
request.session[ONBOARDING_ORGS_KEY] = orgs
```

### M1: mark_safe Usage (Lines 30-34)
```python
# apps/teams/forms.py:30-34
link = '<a class="link" href={} target="_blank">{}</a>'.format(
    reverse("web:terms"),
    _("Terms and Conditions"),
)
self.fields["terms_agreement"].label = mark_safe(_("I agree to the {terms_link}").format(terms_link=link))
```

### M2: Error Message Disclosure (Line 290-291)
```python
# apps/integrations/views.py (approximate)
except (GitHubOAuthError, KeyError, Exception) as e:
    messages.error(request, f"Failed to exchange authorization code: {str(e)}")
```

---

## Environment Variables Required

After fixes, these environment variables will be **REQUIRED** (no defaults):

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `SECRET_KEY` | Django secret key | `django-insecure-<random-50-chars>` |
| `INTEGRATION_ENCRYPTION_KEY` | OAuth token encryption | Fernet key (base64) |

### Generating Values

```bash
# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate INTEGRATION_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Design Decisions

### Why require SECRET_KEY with no default?
- Hardcoded secrets in source code are a major security risk
- The current default is clearly marked "insecure" and could be guessed
- Forcing env var ensures each environment has unique key

### Why encrypt session tokens?
- Session storage (database) could be compromised
- Defense in depth - even if session data leaks, tokens are protected
- Consistent with how we store tokens in IntegrationCredential

### Why format_html over mark_safe?
- `format_html()` automatically escapes arguments
- Prevents XSS if any argument becomes user-controllable in future
- Django's recommended pattern for safe HTML construction

### Why rate limiting on OAuth?
- OAuth endpoints are high-value targets
- Prevents brute force attempts
- Protects against DoS by limiting request volume

---

## Testing Approach

### Test Encryption Key
Add to `conftest.py`:
```python
import os
os.environ.setdefault("INTEGRATION_ENCRYPTION_KEY", "r8pmePXvrfFN4L_IjvTbZP3hWPTIN0y4KDw2wbuIRYg=")
```

### Test Required Settings
Create `tests/test_security.py`:
```python
def test_secret_key_not_default():
    """Verify SECRET_KEY is not the insecure default."""
    from django.conf import settings
    assert "django-insecure" not in settings.SECRET_KEY

def test_debug_false_in_production():
    """Verify DEBUG is False unless explicitly enabled."""
    # This would run in a production-like test environment
    pass
```

---

## Rollback Plan

If issues arise after deployment:

1. **SECRET_KEY issues**: Set env var to old default temporarily
2. **Session encryption issues**: Clear all sessions, users re-login
3. **Rate limiting issues**: Remove `@ratelimit` decorators temporarily

---

## Related Documentation

- [Django Security Settings](https://docs.djangoproject.com/en/5.0/topics/security/)
- [django-ratelimit Docs](https://django-ratelimit.readthedocs.io/)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
