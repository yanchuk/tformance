# OAuth-Only Auth - Context & Key Files

**Last Updated: 2025-12-21**
**Status: REVERTED - Email/password restored alongside OAuth**

## Current State

Email/password signup has been **restored** to support seed data users for testing. OAuth (GitHub/Google) remains available as an alternative authentication method.

## Key Files

### Templates (Current State)

| File | Purpose | Current State |
|------|---------|---------------|
| `templates/account/signup.html` | User registration page | Email form + OAuth buttons |
| `templates/account/login.html` | User login page | Email form + OAuth buttons |
| `templates/account/components/social/social_buttons.html` | OAuth button component | Shows "or continue with" divider |
| `templates/account/components/social/login_with_social_button.html` | Individual OAuth button | No changes |

### Settings

| File | Line | Setting | Value |
|------|------|---------|-------|
| `tformance/settings.py` | 289 | `ACCOUNT_LOGIN_BY_CODE_ENABLED` | `False` |

### Related Files (Reference Only)

| File | Purpose |
|------|---------|
| `apps/users/signals.py` | Admin signup notification (line 46-51) |
| `apps/teams/adapter.py` | Custom allauth adapter for invitations |
| `templates/teams/accept_invite.html` | Team invitation acceptance |

## Key Decisions

1. **Email + OAuth for testing** - Need email/password for seed data login
2. **OAuth still available** - GitHub/Google buttons shown below email form
3. **Magic link disabled** - `ACCOUNT_LOGIN_BY_CODE_ENABLED = False` remains

## Dependencies

- `django-allauth` - Handles all OAuth flows
- `allauth.socialaccount.providers.google` - Google OAuth
- `allauth.socialaccount.providers.github` - GitHub OAuth

## OAuth Provider Configuration

OAuth apps must be configured in Django admin at `/admin/socialaccount/socialapp/`:
- GitHub OAuth App
- Google OAuth App

## URLs (for reference)

- `/accounts/signup/` - Registration (email form + OAuth)
- `/accounts/login/` - Login (email form + OAuth)
- `/accounts/github/login/` - GitHub OAuth start
- `/accounts/google/login/` - Google OAuth start

## Test Credentials

- **Email**: `admin@example.com`
- **Password**: `admin123`

## Implementation History

### Session 1 (2025-12-21) - OAuth-Only
- Removed email/password forms in favor of OAuth-only
- Committed: `41536bf Switch to OAuth-only authentication (GitHub/Google)`

### Session 2 (2025-12-21) - Restore Email/Password
- **Reason**: Need email/password for seed data users to enable testing
- Restored email forms to signup.html and login.html
- Restored "or continue with" divider in social_buttons.html
- Unskipped 4 signup tests
- Committed: `d6f5827 Restore email/password signup alongside OAuth`

## Files Modified (Latest)

| File | Change |
|------|--------|
| `templates/account/signup.html` | Email form + invitation context + OAuth |
| `templates/account/login.html` | Email form + OAuth |
| `templates/account/components/social/social_buttons.html` | Divider restored |
| `apps/teams/tests/test_signup.py` | Removed @skip decorators |

## Test Status

- All 4 signup unit tests pass
- All 18 auth E2E tests pass
- Email/password login works with seed data

## Notes

- No migrations needed (template changes only)
- Admin notification email still works (`apps/users/signals.py`)
- Team adapter handles both OAuth and email invitation flows
