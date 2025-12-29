# Unified Login OAuth - Use Single GitHub OAuth Callback

**Last Updated:** 2025-12-29

## Executive Summary

Add a `FLOW_TYPE_LOGIN` to our unified OAuth callback (`/auth/github/callback/`) so that BOTH login AND integration flows use the same callback URL. This allows using a single GitHub OAuth App without needing multiple callback URLs.

## Problem Statement

GitHub OAuth Apps only support **ONE callback URL**. Currently:

| Flow | Callback URL | Status |
|------|--------------|--------|
| Login (allauth) | `/accounts/github/login/callback/` | ❌ Broken (URL not registered) |
| Integration | `/auth/github/callback/` | ✅ Works (URL is registered) |

**User set callback to:** `https://dev2.ianchuk.com/auth/github/callback/`

## Proposed Solution

Route login through our unified callback instead of allauth's:

```
Current:
Login Button → allauth OAuth → /accounts/github/login/callback/ ❌

Proposed:
Login Button → our auth → /auth/github/callback/ ✅
```

## Implementation Phases

### Phase 1: Add FLOW_TYPE_LOGIN to oauth_state.py
- Add `FLOW_TYPE_LOGIN = "login"` constant
- Add to `VALID_FLOW_TYPES` tuple
- Login flow has no team_id requirement

### Phase 2: Create Login Initiation View
- Create `/auth/github/login/` endpoint
- Generates OAuth state with `FLOW_TYPE_LOGIN`
- Redirects to GitHub OAuth with minimal scopes (`user:email`)

### Phase 3: Add Login Handler to Callback
- In `github_callback` view, handle `FLOW_TYPE_LOGIN`
- Create or get user based on GitHub profile
- Log user in with Django's `login()` function
- Redirect to appropriate page (onboarding if no team, dashboard if has team)

### Phase 4: Update Templates
- Change GitHub login button to use `/auth/github/login/` instead of allauth's URL
- Update `social_buttons.html` template

## Technical Design

### OAuth State (oauth_state.py)
```python
# Add new flow type
FLOW_TYPE_LOGIN = "login"

# Update valid types tuple
VALID_FLOW_TYPES = (
    FLOW_TYPE_LOGIN,  # NEW
    FLOW_TYPE_ONBOARDING,
    FLOW_TYPE_INTEGRATION,
    ...
)
```

### Login Initiation View (views.py)
```python
def github_login(request):
    """Initiate GitHub OAuth for login."""
    from urllib.parse import urlencode

    # Minimal scopes for login
    login_scopes = "user:email"

    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))
    state = create_oauth_state(FLOW_TYPE_LOGIN)

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": callback_url,
        "scope": login_scopes,
        "state": state,
    }
    auth_url = f"{GITHUB_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    return redirect(auth_url)
```

### Callback Handler (views.py)
```python
# In github_callback:
if state_data["type"] == FLOW_TYPE_LOGIN:
    return _handle_login_callback(request, code)

def _handle_login_callback(request, code):
    """Handle GitHub OAuth callback for login flow."""
    # Exchange code for token
    # Get GitHub user info
    # Create or get Django user
    # Login user
    # Redirect to onboarding or dashboard
```

### Template Change (social_buttons.html)
```html
<!-- Change from allauth URL to our URL -->
<a href="{% url 'tformance_auth:github_login' %}">
    Sign in with GitHub
</a>
```

## Files to Modify

| File | Change |
|------|--------|
| `apps/auth/oauth_state.py` | Add `FLOW_TYPE_LOGIN` |
| `apps/auth/views.py` | Add `github_login` view, add login handler |
| `apps/auth/urls.py` | Add `/github/login/` route |
| `templates/account/components/social/social_buttons.html` | Use new URL |

## Files to Create

| File | Purpose |
|------|---------|
| `apps/auth/tests/test_github_login.py` | Tests for login flow |

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing sessions | Medium | Users can re-login |
| Missing user data | Low | Fetch from GitHub API |
| Email conflicts | Medium | Match by GitHub ID first, then email |

## Success Metrics

1. Both login and integration use `/auth/github/callback/`
2. Single OAuth App works for all flows
3. All existing tests pass
4. New login tests pass

## Dependencies

- No new packages
- No database migrations
- Uses existing GitHub OAuth credentials
