# OAuth-Only Auth - Task Checklist

**Last Updated: 2025-12-21**
**Status: COMPLETE (Email + OAuth hybrid)**

## Summary

Originally implemented OAuth-only auth, then reverted to email+OAuth hybrid to support seed data testing.

---

## Phase 1: Template Updates (COMPLETE)

### 1.1 Signup Page
- [x] Email/password form with OAuth fallback
- [x] Invitation context display when present
- [x] "Already have account?" link
- [x] Turnstile captcha support (conditional)

**File:** `templates/account/signup.html`

### 1.2 Login Page
- [x] Email/password form with OAuth fallback
- [x] "Don't have account?" link

**File:** `templates/account/login.html`

### 1.3 Social Buttons Component
- [x] "or continue with" divider
- [x] OAuth buttons rendered for configured providers

**File:** `templates/account/components/social/social_buttons.html`

---

## Phase 2: Settings (COMPLETE)

- [x] `ACCOUNT_LOGIN_BY_CODE_ENABLED = False` (magic link disabled)

**File:** `tformance/settings.py`

---

## Phase 3: Testing (COMPLETE)

### 3.1 Unit Tests
- [x] All 4 signup tests pass (unskipped)
- [x] `test_signup_creates_user_without_team`
- [x] `test_signup_with_invitation_joins_existing_team`
- [x] `test_signup_with_invalid_invitation_shows_error`
- [x] `test_signup_with_wrong_email_for_invitation_shows_error`

### 3.2 E2E Tests
- [x] All 18 auth E2E tests pass
- [x] Valid credentials redirect to app
- [x] Signup form has required fields
- [x] OAuth buttons visible and functional

---

## Commits

1. `41536bf` - Switch to OAuth-only authentication (GitHub/Google)
2. `d6f5827` - Restore email/password signup alongside OAuth

---

## Verification Commands

```bash
# Run signup tests
make test ARGS='apps.teams.tests.test_signup --keepdb'

# Run auth E2E tests
npx playwright test tests/e2e/auth.spec.ts

# Test login manually
# Email: admin@example.com
# Password: admin123
```

---

## Notes

- Email/password restored for seed data testing
- OAuth still works as alternative
- No further work needed on this task
