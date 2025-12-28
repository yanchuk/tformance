# GitHub-Only Authentication Mode

> **Last Updated**: 2024-12-28
> **Status**: Planning
> **Priority**: Medium

## Executive Summary

Implement a feature flag system to show only GitHub authentication in production while keeping email/password auth available for development and testing. This simplifies the user experience for our target audience (dev teams with GitHub) without removing any functionality.

## Current State Analysis

### Existing Auth Methods
| Method | Status | Template |
|--------|--------|----------|
| Email/Password | Active | `login.html`, `signup.html` |
| GitHub OAuth | Active | via `social_buttons.html` |
| Google OAuth | Active | via `social_buttons.html` |
| Password Reset | Active | `password_reset*.html` |

### Current Template Structure
```
templates/account/
├── login.html                    # Email form + social buttons
├── signup.html                   # Email form + social buttons
├── password_reset.html           # Email-based reset
├── password_reset_done.html
├── password_reset_from_key.html
├── password_reset_from_key_done.html
├── components/
│   └── social/
│       ├── social_buttons.html        # Loops through socialapps
│       └── login_with_social_button.html  # Individual button
```

### Context Processors (settings.py:188-200)
Currently uses:
- `apps.web.context_processors.project_meta` - Has `turnstile_key`
- `apps.teams.context_processors.team`
- `apps.teams.context_processors.user_teams`
- `apps.web.context_processors.google_analytics_id`
- `apps.web.context_processors.posthog_config`

## Proposed Future State

### Auth Mode Configuration
```python
# settings.py
AUTH_MODE = env("AUTH_MODE", default="github_only" if not DEBUG else "all")
ALLOW_EMAIL_AUTH = AUTH_MODE == "all"
ALLOW_GOOGLE_AUTH = False  # Disabled for now, GitHub only
```

### Environment Matrix
| Environment | DEBUG | AUTH_MODE | Email | GitHub | Google |
|-------------|-------|-----------|-------|--------|--------|
| Development | True | `all` | ✅ | ✅ | ❌ |
| Testing/CI | False | `all` | ✅ | ✅ | ❌ |
| Staging | False | `github_only` | ❌ | ✅ | ❌ |
| Production | False | `github_only` | ❌ | ✅ | ❌ |

### UI Changes

**Login Page (github_only mode)**:
- Hide email/password form
- Show prominent "Sign in with GitHub" button
- Hide "Don't have an account? Sign up" link (signup via GitHub)

**Signup Page (github_only mode)**:
- Replace form with "Get Started with GitHub" CTA
- Keep invitation banner if present (user still needs GitHub)

## Implementation Phases

### Phase 1: Settings & Context Processor
Add feature flags and expose to templates.

### Phase 2: Template Updates
Conditionally render auth forms based on flags.

### Phase 3: URL Protection (Optional)
Block direct access to email auth URLs in github_only mode.

### Phase 4: Testing
Verify both modes work correctly.

## Technical Design

### New Context Processor
```python
# apps/web/context_processors.py (add to existing file)

def auth_mode(request):
    """Expose auth mode settings to templates."""
    from django.conf import settings
    return {
        "ALLOW_EMAIL_AUTH": getattr(settings, "ALLOW_EMAIL_AUTH", False),
        "ALLOW_GOOGLE_AUTH": getattr(settings, "ALLOW_GOOGLE_AUTH", False),
        "AUTH_MODE": getattr(settings, "AUTH_MODE", "github_only"),
    }
```

### Template Logic Pattern
```html
{% if ALLOW_EMAIL_AUTH %}
  {# Show email form #}
{% endif %}

{# GitHub always shown #}
```

### Affected Files
| File | Change Type | Description |
|------|-------------|-------------|
| `tformance/settings.py` | Modify | Add AUTH_MODE, ALLOW_* settings |
| `apps/web/context_processors.py` | Modify | Add auth_mode() function |
| `templates/account/login.html` | Modify | Conditional email form |
| `templates/account/signup.html` | Modify | Conditional email form |
| `templates/account/components/social/social_buttons.html` | Modify | Filter providers |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Existing users can't login | Low | High | Email auth still works, just hidden |
| E2E tests break | Medium | Medium | Set AUTH_MODE=all in test env |
| Invited users confused | Low | Medium | Keep invitation flow working via GitHub |
| GitHub outage | Low | High | Accept risk - rare occurrence |

## Success Metrics

- [ ] Login page shows only GitHub button in github_only mode
- [ ] Signup page shows only GitHub CTA in github_only mode
- [ ] Email auth still works in development (AUTH_MODE=all)
- [ ] E2E tests pass with AUTH_MODE=all
- [ ] No changes to OAuth integration flows (those stay as-is)

## Dependencies

- None - uses existing GitHub OAuth already configured
- No new packages required
- No database changes

## Effort Estimate

| Phase | Effort | Description |
|-------|--------|-------------|
| Phase 1 | S | Settings + context processor (~30 min) |
| Phase 2 | M | Template updates (~1 hour) |
| Phase 3 | S | Optional URL protection (~30 min) |
| Phase 4 | S | Testing (~30 min) |
| **Total** | **M** | **~2.5 hours** |
