# OAuth-Only Auth - Context & Key Files

**Last Updated: 2025-12-21**
**Status: COMPLETE - Committed to main**

## Key Files

### Templates to Modify

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `templates/account/signup.html` | User registration page | Remove form, show OAuth buttons only |
| `templates/account/login.html` | User login page | Remove form, show OAuth buttons only |
| `templates/account/components/social/social_buttons.html` | OAuth button component | Remove "or continue with" divider |
| `templates/account/components/social/login_with_social_button.html` | Individual OAuth button | No changes needed |

### Settings

| File | Line | Setting | Current | Target |
|------|------|---------|---------|--------|
| `tformance/settings.py` | 289 | `ACCOUNT_LOGIN_BY_CODE_ENABLED` | `True` | `False` |

### Related Files (Reference Only)

| File | Purpose |
|------|---------|
| `apps/users/signals.py` | Admin signup notification (line 46-51) |
| `apps/teams/adapter.py` | Custom allauth adapter for invitations |
| `templates/teams/accept_invite.html` | Team invitation acceptance |

## Key Decisions

1. **Keep GitHub + Google OAuth** - Both configured and working
2. **Remove email/password entirely** - Not just hide, but remove form
3. **Disable magic link login** - Also email-based, remove it
4. **Keep admin signup notification** - Still useful to know when users join

## Dependencies

- `django-allauth` - Handles all OAuth flows
- `allauth.socialaccount.providers.google` - Google OAuth
- `allauth.socialaccount.providers.github` - GitHub OAuth

## OAuth Provider Configuration

OAuth apps must be configured in Django admin at `/admin/socialaccount/socialapp/`:
- GitHub OAuth App
- Google OAuth App

## Template Tags Used

```django
{% load social_tags %}
{% get_socialapps as socialapps %}
{% for provider in socialapps %}
  {% include 'account/components/social/login_with_social_button.html' %}
{% endfor %}
```

## URLs (for reference)

- `/accounts/signup/` - Registration
- `/accounts/login/` - Login
- `/accounts/github/login/` - GitHub OAuth start
- `/accounts/google/login/` - Google OAuth start

## Test Considerations

1. **New user signup via GitHub** - Creates account, redirects to onboarding
2. **New user signup via Google** - Creates account, redirects to onboarding
3. **Existing user login** - Matches by email, logs in
4. **Team invitation flow** - User accepts invite, OAuth, joins team

## Implementation Summary (Session 2025-12-21)

### Completed
- ✅ Replaced email/password forms with OAuth-only buttons
- ✅ Updated signup.html, login.html, social_buttons.html
- ✅ Disabled magic link login (ACCOUNT_LOGIN_BY_CODE_ENABLED=False)
- ✅ Added invitation context display on signup page
- ✅ Skipped 4 email/password tests (no longer applicable)
- ✅ All 1602 tests pass
- ✅ Committed: `41536bf Switch to OAuth-only authentication (GitHub/Google)`

### Key Decisions
1. **OAuth-only for MVP** - Target audience (dev teams) have GitHub accounts
2. **Keep invitation flow** - OAuth adapter handles team joining via session
3. **Skip tests vs delete** - Kept test code with @skip decorators for reference

### Files Modified
| File | Change |
|------|--------|
| `templates/account/signup.html` | OAuth buttons + invitation context |
| `templates/account/login.html` | OAuth buttons only |
| `templates/account/components/social/social_buttons.html` | Removed divider |
| `tformance/settings.py:289` | `ACCOUNT_LOGIN_BY_CODE_ENABLED = False` |
| `apps/teams/tests/test_signup.py` | Added @skip to 4 tests |

### Remaining (Manual Testing)
- [ ] Test OAuth signup with real GitHub/Google accounts
- [ ] Test team invitation flow end-to-end
- [ ] Push to origin when ready

### Notes
- No migrations needed (template/settings changes only)
- Admin notification email still works (`apps/users/signals.py`)
- Team adapter (`apps/teams/adapter.AcceptInvitationAdapter`) handles OAuth invitation flow
