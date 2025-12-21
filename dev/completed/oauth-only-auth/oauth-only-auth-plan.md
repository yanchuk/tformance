# OAuth-Only Authentication Implementation Plan

**Last Updated: 2025-12-21**

## Executive Summary

Remove email/password registration and login from tformance, keeping only GitHub and Google OAuth as authentication methods. This simplifies the authentication flow for developer teams (the target audience) and eliminates password storage security concerns.

## Current State Analysis

### Authentication Methods Currently Enabled
1. **Email/Password signup** - `templates/account/signup.html` with full form
2. **Email/Password login** - `templates/account/login.html` with form
3. **Login by code (magic link)** - `ACCOUNT_LOGIN_BY_CODE_ENABLED = True`
4. **GitHub OAuth** - Configured in settings
5. **Google OAuth** - Configured in settings

### Key Settings (tformance/settings.py:273-301)
```python
ACCOUNT_ADAPTER = "apps.teams.adapter.AcceptInvitationAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="none")
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
```

### Admin Notification Email
The email user received ("Yowsers, someone signed up...") is from `apps/users/signals.py:46-51` - this notifies admins of signups but doesn't send confirmation to users.

### Templates Affected
- `templates/account/signup.html` - Email/password form
- `templates/account/login.html` - Email/password form + magic link
- `templates/account/components/social/social_buttons.html` - "or continue with" text
- `templates/account/password_*.html` - Password reset flows

## Proposed Future State

### Authentication Flow
1. User clicks "Sign Up" or "Sign In"
2. Same page shows GitHub and Google buttons only
3. OAuth flow handles everything
4. No passwords stored, no email verification needed

### Benefits
- Simpler UX for developer audience (all have GitHub)
- No password storage = reduced security surface
- No email verification complexity
- Leverages identity from trusted providers

## Implementation Phases

### Phase 1: Template Updates (Priority: High)
Update authentication templates to OAuth-only UI.

### Phase 2: Settings Configuration (Priority: High)
Disable email-based authentication features.

### Phase 3: Testing & Cleanup (Priority: Medium)
Verify flows work, clean up unused code.

## Detailed Tasks

See `oauth-only-auth-tasks.md` for checklist format.

### Phase 1: Template Updates

| Task | Effort | Description |
|------|--------|-------------|
| 1.1 Update signup.html | S | Replace email/password form with OAuth buttons |
| 1.2 Update login.html | S | Replace email/password form with OAuth buttons |
| 1.3 Update social_buttons.html | S | Remove "or continue with" divider |

### Phase 2: Settings Configuration

| Task | Effort | Description |
|------|--------|-------------|
| 2.1 Disable login-by-code | S | Set `ACCOUNT_LOGIN_BY_CODE_ENABLED = False` |

### Phase 3: Testing & Cleanup

| Task | Effort | Description |
|------|--------|-------------|
| 3.1 Test OAuth signup | M | Verify new user creation via GitHub/Google |
| 3.2 Test OAuth login | M | Verify existing user login |
| 3.3 Test team invitations | M | Verify invitation flow with OAuth |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Existing email-only users locked out | Low | Medium | Users can link OAuth via same email address |
| OAuth provider outage | Low | High | Two providers for redundancy |
| Team invitation flow breaks | Medium | High | Test explicitly before deploying |

## Success Metrics

- No email/password fields on auth pages
- OAuth signup creates user correctly
- OAuth login works for existing users
- Team invitations work with OAuth
- No 500 errors on auth pages

## Files to Modify

1. `templates/account/signup.html`
2. `templates/account/login.html`
3. `templates/account/components/social/social_buttons.html`
4. `tformance/settings.py`
