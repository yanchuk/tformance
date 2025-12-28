# Tformance Authentication & User Registration - Comprehensive Overview

> **Generated**: December 2024
> **Last Updated**: 2024-12-28
> **Purpose**: Documentation of all authentication flows, onboarding steps, and security features

## Auth Mode Feature Flag

The application supports two authentication modes controlled by `AUTH_MODE` environment variable:

| Mode | Setting | Email/Password | GitHub OAuth | Google OAuth |
|------|---------|----------------|--------------|--------------|
| **Development** | `AUTH_MODE=all` | Visible | Visible | Hidden |
| **Production** | `AUTH_MODE=github_only` | Hidden | Visible | Hidden |

**Configuration** (`settings.py`):
```python
AUTH_MODE = env("AUTH_MODE", default="all" if DEBUG else "github_only")
ALLOW_EMAIL_AUTH = AUTH_MODE == "all"
ALLOW_GOOGLE_AUTH = False  # Disabled for simplicity
```

**Template Usage**:
```html
{% if ALLOW_EMAIL_AUTH %}
  {# Email/password form #}
{% else %}
  {# GitHub-only CTA #}
{% endif %}
```

---

## Executive Summary

Tformance uses **django-allauth** for authentication with custom extensions for team-based onboarding. The system supports email/password registration, Google OAuth for login, and dedicated OAuth flows for GitHub/Jira/Slack integrations.

---

## 1. SIGN UP FLOW

### Entry Point
- **URL**: `/accounts/signup/` (django-allauth)
- **Template**: `templates/account/signup.html`

### Required Fields
| Field | Required | Notes |
|-------|----------|-------|
| Email | Yes | Must be unique, becomes username |
| Password | Yes | Single password field (no confirmation) |
| Terms Agreement | Yes | Checkbox for terms acceptance |
| Invitation ID | No | Pre-filled if invited to team |

### Form Implementation
- **Form**: `TeamSignupForm` (`apps/teams/forms.py:12-77`)
- **Extends**: `TurnstileSignupForm` (CAPTCHA support)
- **Settings**: `ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]`

### Anti-Bot Protection
1. **Honeypot Field**: `phone_number_x` (hidden field, fails if filled)
2. **Turnstile CAPTCHA**: Optional, enabled via `TURNSTILE_ENABLED` setting

### Email Verification Status
**Current Default**: `ACCOUNT_EMAIL_VERIFICATION = "none"` (no verification required)

Can be set to:
- `"none"` - No verification, immediate access
- `"optional"` - Email sent but not required
- `"mandatory"` - Must verify before accessing app

### What Happens After Signup
1. `user_signed_up` signal fires (`apps/users/signals.py:29-42`)
2. Admins notified of new signup
3. PostHog event tracked (method: email vs social)
4. If `invitation_id` present: User added to team (`apps/teams/signals.py:11-29`)
5. Redirect to `/` (homepage checks if team exists → onboarding)

### Email Verification (if enabled)
- `ACCOUNT_CONFIRM_EMAIL_ON_GET = True` - Auto-confirms via link click
- `ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True` - Auto-login after confirm
- Template: `templates/account/email/email_confirmation_signup_message.html`

---

## 2. SIGN IN FLOW

### Entry Point
- **URL**: `/accounts/login/`
- **Template**: `templates/account/login.html`

### Authentication Methods
1. **Email + Password** (primary)
2. **Google OAuth** (social login)
3. **GitHub OAuth** (social login via allauth)

### Settings
```python
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGIN_METHODS = {"email"}  # Email-only, no username
ACCOUNT_LOGIN_BY_CODE_ENABLED = False  # No magic links
```

### Authentication Backends
1. `django.contrib.auth.backends.ModelBackend` - Standard auth
2. `allauth.account.auth_backends.AuthenticationBackend` - Email-based

### Post-Login Flow
1. `user_logged_in` signal fires (`apps/users/signals.py:17-26`)
2. **Session key rotated** (prevents session fixation attacks)
3. Adapter checks for pending team invitation (`apps/teams/adapter.py:8-29`)
4. Redirect based on:
   - Pending invitation → `/teams/invitation/{id}/accept/`
   - Has team → `/app/` (dashboard)
   - No team → `/onboarding/start`

---

## 3. PASSWORD RESET FLOW

### Steps
| Step | URL | Template |
|------|-----|----------|
| 1. Request reset | `/accounts/password/reset/` | `password_reset.html` |
| 2. Confirmation | `/accounts/password/reset/done/` | `password_reset_done.html` |
| 3. Set new password | `/accounts/password/reset/key/{key}/` | `password_reset_from_key.html` |
| 4. Success | `/accounts/password/reset/key/done/` | `password_reset_from_key_done.html` |

### Security Features
- **Email enumeration prevention**: `ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False`
  - Doesn't reveal if email exists in system
- **Token expiry**: 24 hours (Django default)
- **Single-use tokens**: Cannot reuse reset links

### Email Configuration
```python
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
# Production: Resend.com via django-anymail
```

---

## 4. EMAIL CONFIRMATION FLOW

### Configuration
```python
ACCOUNT_EMAIL_VERIFICATION = "none"  # Current default
ACCOUNT_CONFIRM_EMAIL_ON_GET = True  # Click link = confirmed
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True  # Auto-login after
ACCOUNT_UNIQUE_EMAIL = True
```

### Confirmation Process (when enabled)
1. User signs up → confirmation email sent
2. User clicks link in email
3. Email marked verified (`GET` auto-confirms)
4. `email_confirmed` signal fires (`apps/users/signals.py:45-52`)
5. Email set as primary via `email_address.set_as_primary()`
6. User auto-logged in

### Email Change (from profile)
Located in `apps/users/views.py:20-55`:
1. User updates email in profile form
2. If verification required AND email changed:
   - Confirmation email sent to new address
   - Original email kept until confirmed
3. After confirmation → email updated in User model

### Templates
- Signup confirmation: `templates/account/email/email_confirmation_signup_message.html`
- Change confirmation: `templates/account/email/email_confirmation_message.html`
- Confirmation page: `templates/account/email_confirm.html`

---

## 5. SOCIAL AUTHENTICATION (OAuth)

### Providers for User Login
| Provider | Configured | Purpose |
|----------|------------|---------|
| Google | Yes | User signup/login |
| GitHub | Yes | User signup/login + Team integration |

### Google OAuth Settings (`settings.py:317-332`)
```python
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_CLIENT_ID,
            "secret": GOOGLE_SECRET_ID,
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}
```

### Social Signup Form
- **Form**: `CustomSocialSignupForm` (`apps/users/forms.py:58-64`)
- **Feature**: `prevent_enumeration = False` (shows if email exists for UX)

### OAuth Flow (allauth-managed)
1. User clicks "Continue with Google/GitHub"
2. Redirects to provider
3. Provider returns to `/accounts/google/login/callback/`
4. allauth creates/links user account
5. Redirect per `LOGIN_REDIRECT_URL`

---

## 6. TEAM INTEGRATION OAUTH (Not User Auth)

These are **separate** from user authentication - for connecting external services:

### GitHub Integration OAuth
- **Initiate**: `/onboarding/github/` or `/app/{team}/integrations/github/connect/`
- **Callback**: `/auth/github/callback/`
- **Scopes**: `read:org`, `repo`, `read:user`, `manage_billing:copilot`
- **Token storage**: `IntegrationCredential` model (encrypted)

### Jira Integration OAuth
- **Initiate**: `/onboarding/jira/` or `/app/{team}/integrations/jira/connect/`
- **Callback**: `/auth/jira/callback/`
- **Scopes**: `read:jira-work`, `read:jira-user`, `offline_access`
- **Token refresh**: Automatic when near expiration

### Slack Integration OAuth
- **Initiate**: `/app/{team}/integrations/slack/connect/`
- **Callback**: `/app/{team}/integrations/slack/callback/`
- **Scopes**: `chat:write`, `users:read`, `users:read.email`

### OAuth State Security
- **File**: `apps/auth/oauth_state.py`
- **Flow types**: `onboarding`, `integration`, `jira_onboarding`, `jira_integration`
- **Expiry**: 10 minutes
- **Protection**: Signed + timestamped + CSRF validated

---

## 7. ONBOARDING FLOW (Post-Signup)

### Flow Diagram
```
Signup → Home Check → No Team?
                ↓
        /onboarding/start (Step 1)
                ↓
        Connect GitHub [REQUIRED]
                ↓
        Select Organization (if multiple)
                ↓
        Team Created + Members Synced
                ↓
        /onboarding/repos (Step 2)
        Select Repositories [REQUIRED]
                ↓
        /onboarding/jira (Step 3) [OPTIONAL - can skip]
        → Connect Jira OR Skip
                ↓
        /onboarding/jira/projects (Step 3b)
        Select Projects (if connected)
                ↓
        /onboarding/slack (Step 4) [OPTIONAL - can skip]
                ↓
        /onboarding/complete (Step 5)
        Shows sync progress
                ↓
        Go to Dashboard → /app/
```

### Step Summary
| Step | URL | Required | Can Skip |
|------|-----|----------|----------|
| 1. Start | `/onboarding/start` | Yes | No |
| 2. GitHub | `/onboarding/github/` | Yes | No |
| 3. Org Selection | `/onboarding/org/` | If multiple orgs | Auto-selects if single |
| 4. Repositories | `/onboarding/repos/` | Yes | No |
| 5. Jira | `/onboarding/jira/` | No | Yes |
| 5b. Jira Projects | `/onboarding/jira/projects/` | If Jira connected | N/A |
| 6. Slack | `/onboarding/slack/` | No | Yes |
| 7. Complete | `/onboarding/complete/` | Yes | No |

### Alternative Skip Path
- **URL**: `/onboarding/skip/`
- Creates basic team without integrations
- User can add integrations later from settings

### What Gets Created During Onboarding
1. **Team** - Name from GitHub org
2. **Membership** - User as ADMIN
3. **IntegrationCredential** - Encrypted OAuth tokens
4. **GitHubIntegration** - Org config + webhook
5. **TrackedRepository** - Selected repos (triggers background sync)
6. **JiraIntegration** + **TrackedJiraProject** (if connected)

---

## 8. KEY SECURITY FEATURES

### Cookie Security (`settings.py:238-250`)
```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in prod
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
```

### Session Security
- **Session fixation prevention**: Key rotated on login
- **Session rotation**: `request.session.cycle_key()` in login signal

### Rate Limiting (OAuth Callbacks)
- `/auth/github/callback/`: 10 req/min per IP
- `/auth/jira/callback/`: 10 req/min per IP
- `/integrations/slack/callback/`: 10 req/min per IP

### Token Storage
- **Field**: `EncryptedTextField` (`apps/utils/fields.py`)
- **Encryption**: At rest in database
- **Decryption**: Automatic on model access

### Email Security
- **No enumeration**: `ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False`
- **Unique enforcement**: `ACCOUNT_UNIQUE_EMAIL = True`

---

## 9. USER MODEL

### Custom User (`apps/users/models.py`)
- **Base**: `AbstractUser`
- **Username strategy**: Email as username (`EmailAsUsernameAdapter`)
- **Key properties**:
  - `get_display_name()` - Full name or email
  - `avatar_url` - With Gravatar fallback
  - `has_verified_email` - Cached check

### AUTH_USER_MODEL
```python
AUTH_USER_MODEL = "users.CustomUser"
```

---

## 10. KEY FILE PATHS

| Component | Path |
|-----------|------|
| Settings (allauth) | `tformance/settings.py:269-350` |
| Signup Form | `apps/teams/forms.py:12-77` |
| User Model | `apps/users/models.py` |
| User Signals | `apps/users/signals.py` |
| Team Signals | `apps/teams/signals.py` |
| Login Adapter | `apps/teams/adapter.py` |
| OAuth State | `apps/auth/oauth_state.py` |
| OAuth Callbacks | `apps/auth/views.py` |
| Onboarding Views | `apps/onboarding/views.py` |
| Integration Models | `apps/integrations/models.py` |
| Templates | `templates/account/*.html` |
| E2E Tests | `tests/e2e/auth.spec.ts` |

---

## 11. SUMMARY: USER JOURNEY

### New User (Email Signup)
```
1. /accounts/signup/ → Enter email + password + terms
2. Account created (no email verification by default)
3. Redirect to / → Checks for team → No team
4. Redirect to /onboarding/start
5. Connect GitHub (required)
6. Select org → Team created
7. Select repos (required)
8. Optional: Connect Jira
9. Optional: Connect Slack
10. /onboarding/complete → Dashboard
```

### Returning User (Login)
```
1. /accounts/login/ → Enter email + password
2. Session created + key rotated
3. Check for pending invitation → Accept if exists
4. Redirect to /app/ (team dashboard)
```

### Password Reset
```
1. /accounts/password/reset/ → Enter email
2. Email sent (if account exists, no leak either way)
3. Click link in email
4. /accounts/password/reset/key/{key}/ → Set new password
5. Confirmation shown → Login
```

### Social Login (Google)
```
1. /accounts/login/ → Click "Continue with Google"
2. Redirect to Google → Authorize
3. Return to /accounts/google/login/callback/
4. Account created/linked
5. Same flow as email signup after
```

---

## 12. IMPROVEMENT RECOMMENDATIONS

### High Priority

#### 1. Enable Email Verification (Security)
**Current**: `ACCOUNT_EMAIL_VERIFICATION = "none"`
**Recommendation**: Change to `"mandatory"` or at least `"optional"`

**Why**:
- Prevents fake signups and spam accounts
- Ensures valid contact for password reset
- Required for compliance (GDPR email consent)
- Reduces support burden from typo emails

**Implementation**:
```python
# settings.py
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
```

#### 2. Add Rate Limiting to Login/Signup
**Current**: Only OAuth callbacks are rate-limited
**Missing**: `/accounts/login/`, `/accounts/signup/`

**Why**: Prevents brute force attacks and credential stuffing

**Implementation**:
```python
# Using django-ratelimit
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    ...
```

#### 3. Add Account Lockout After Failed Attempts
**Current**: No lockout mechanism
**Recommendation**: Lock account after 5 failed attempts

**Why**: Prevents brute force password attacks

**Options**:
- `django-axes` - Full-featured lockout
- `django-defender` - Alternative with Redis
- Custom signal handler on failed login

#### 4. Password Strength Requirements
**Current**: Relies on Django defaults
**Recommendation**: Enforce stronger requirements

**Implementation**:
```python
# settings.py
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

### Medium Priority

#### 5. Add Two-Factor Authentication (2FA)
**Current**: Not implemented
**Recommendation**: Add TOTP-based 2FA

**Why**:
- Standard security expectation for B2B SaaS
- Protects against credential theft
- May be required by enterprise customers

**Options**:
- `django-allauth-2fa` - Integrates with existing allauth
- `django-otp` - Lower-level, more flexible

#### 6. Session Timeout Configuration
**Current**: Using Django defaults
**Recommendation**: Add configurable session timeout

```python
# settings.py
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Or True for stricter
SESSION_SAVE_EVERY_REQUEST = True  # Extend on activity
```

#### 7. Add "Remember Me" Functionality
**Current**: `ACCOUNT_SESSION_REMEMBER = True` (always remembers)
**Recommendation**: Give users explicit choice

```python
ACCOUNT_SESSION_REMEMBER = None  # User decides via checkbox
```

#### 8. Improve OAuth Token Rotation
**Current**: GitHub tokens don't expire/refresh
**Recommendation**: Implement token refresh for GitHub

**Why**: Long-lived tokens are a security risk if leaked

#### 9. Add Login Notifications
**Current**: Only admin notified of signups
**Recommendation**: Notify users of new logins

**Implementation**: Email on login from new device/location

### Low Priority (Nice-to-Have)

#### 10. Magic Link Login Option
**Current**: `ACCOUNT_LOGIN_BY_CODE_ENABLED = False`
**Consideration**: Enable for passwordless option

```python
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_TIMEOUT = 300  # 5 minutes
```

#### 11. Social Account Linking
**Current**: Can sign up with Google, but linking unclear
**Recommendation**: Allow users to link multiple social accounts

#### 12. Login History/Audit Log
**Current**: Only PostHog event tracking
**Recommendation**: Store login history in database

```python
class LoginHistory(models.Model):
    user = models.ForeignKey(User)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    success = models.BooleanField()
```

#### 13. Unified OAuth State Management
**Current**: Multiple state creation functions (unified + per-provider)
**Recommendation**: Consolidate to single implementation

Files to merge:
- `apps/auth/oauth_state.py` (unified)
- `apps/integrations/services/github_oauth.py` (has own state)
- `apps/integrations/services/jira_oauth.py` (has own state)

#### 14. Add CAPTCHA to Password Reset
**Current**: Only signup has Turnstile option
**Recommendation**: Add to password reset to prevent abuse

#### 15. Improve E2E Test Coverage
**Current**: Basic auth tests exist
**Missing**:
- Password reset full flow
- Email verification flow
- OAuth flow mocking
- Account lockout scenarios
- Session timeout behavior

---

## Summary: Priority Matrix

| Priority | Improvement | Effort | Impact |
|----------|-------------|--------|--------|
| High | Enable email verification | Low | High |
| High | Rate limit login/signup | Low | High |
| High | Account lockout | Medium | High |
| High | Password strength | Low | Medium |
| Medium | Add 2FA | High | High |
| Medium | Session timeout config | Low | Medium |
| Medium | Remember me choice | Low | Low |
| Medium | GitHub token refresh | Medium | Medium |
| Medium | Login notifications | Medium | Medium |
| Low | Magic link login | Low | Low |
| Low | Social account linking | Medium | Low |
| Low | Login history/audit | Medium | Medium |
| Low | Unified OAuth state | Medium | Low |
| Low | CAPTCHA on reset | Low | Low |
| Low | E2E test coverage | High | Medium |
