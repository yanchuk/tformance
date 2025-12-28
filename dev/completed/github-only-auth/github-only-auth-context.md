# GitHub-Only Auth - Context & Reference

> **Last Updated**: 2024-12-28

## Key Files

### Settings
| File | Purpose |
|------|---------|
| `tformance/settings.py` | Main settings, add AUTH_MODE here (line ~270) |

### Context Processors
| File | Purpose |
|------|---------|
| `apps/web/context_processors.py` | Add `auth_mode()` function here |
| `tformance/settings.py:188-200` | Register context processor here |

### Templates to Modify
| File | Current State |
|------|---------------|
| `templates/account/login.html` | Email form (lines 12-21) + social buttons include |
| `templates/account/signup.html` | Email form (lines 27-51) + social buttons include |
| `templates/account/components/social/social_buttons.html` | Loops all providers |

### Templates to Leave Unchanged
| File | Reason |
|------|--------|
| `templates/account/password_reset*.html` | Only accessible if user has email auth |
| `templates/account/email*.html` | Internal flows |
| `templates/account/profile.html` | Post-login, not auth |

## Key Decisions

### 1. Feature Flag Approach
**Decision**: Use environment variable `AUTH_MODE` with values `all` or `github_only`
**Rationale**: Simple, clear, easily configurable per environment

### 2. Default Behavior
**Decision**: Default to `github_only` in production, `all` in DEBUG
**Rationale**: Safe default for prod, convenient for dev

### 3. Google OAuth
**Decision**: Disable Google OAuth entirely (not just hide)
**Rationale**: Simplify - target audience all has GitHub

### 4. URL Protection
**Decision**: Optional - implement if time permits
**Rationale**: Users shouldn't find hidden URLs, low risk

### 5. Invitation Flow
**Decision**: Keep working - invited users still sign up via GitHub
**Rationale**: Invitation just pre-fills team association

## Code Patterns

### Context Processor Pattern (existing)
```python
# From apps/web/context_processors.py
def project_meta(request):
    return {
        "project_meta": project_data,
        "turnstile_key": getattr(settings, "TURNSTILE_KEY", None),
    }
```

### Template Conditional Pattern
```html
{% if ALLOW_EMAIL_AUTH %}
  {# content #}
{% endif %}
```

### Settings Pattern (existing)
```python
# Environment-based with default
SOME_SETTING = env("SOME_SETTING", default="value")
```

## Dependencies

### Upstream (this feature depends on)
- GitHub OAuth already configured (`SOCIALACCOUNT_PROVIDERS["github"]`)
- django-allauth social auth working
- `social_buttons.html` template include

### Downstream (depends on this feature)
- None - isolated change

## Testing Considerations

### E2E Tests
File: `tests/e2e/auth.spec.ts`
- Uses email/password login
- Need `AUTH_MODE=all` in test environment

### Unit Tests
- No existing unit tests for auth templates
- Context processor can have unit test

## Environment Variables

### New
```bash
AUTH_MODE=github_only  # or "all"
```

### Existing Related
```bash
GITHUB_CLIENT_ID=xxx
GITHUB_SECRET_ID=xxx
GOOGLE_CLIENT_ID=xxx      # Can be removed if disabling Google
GOOGLE_SECRET_ID=xxx      # Can be removed if disabling Google
```

## Rollback Plan

1. Set `AUTH_MODE=all` in environment
2. Deploy
3. Email auth immediately available

No database changes = instant rollback.
