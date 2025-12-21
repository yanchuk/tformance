# OAuth-Only Auth - Task Checklist

**Last Updated: 2025-12-21**

## Phase 1: Template Updates

### 1.1 Update signup.html
- [ ] Remove email/password form fields
- [ ] Remove Turnstile captcha (no form to protect)
- [ ] Add descriptive text about OAuth options
- [ ] Display OAuth buttons prominently
- [ ] Keep "Already have account?" link to login
- [ ] Test page renders without errors

**File:** `templates/account/signup.html`

### 1.2 Update login.html
- [ ] Remove email/password form fields
- [ ] Remove "Mail me a sign-in code" link
- [ ] Display OAuth buttons prominently
- [ ] Add "Don't have account?" link to signup
- [ ] Test page renders without errors

**File:** `templates/account/login.html`

### 1.3 Update social_buttons.html
- [ ] Remove divider and "or continue with" text
- [ ] Component should work standalone

**File:** `templates/account/components/social/social_buttons.html`

---

## Phase 2: Settings Configuration

### 2.1 Disable login-by-code
- [ ] Set `ACCOUNT_LOGIN_BY_CODE_ENABLED = False`
- [ ] Verify magic link URL returns appropriate response

**File:** `tformance/settings.py`

---

## Phase 3: Testing

### 3.1 Test OAuth Signup
- [ ] New user can sign up via GitHub
- [ ] New user can sign up via Google
- [ ] User is redirected to onboarding after signup
- [ ] Admin receives signup notification email

### 3.2 Test OAuth Login
- [ ] Existing user can log in via GitHub
- [ ] Existing user can log in via Google
- [ ] User is redirected to dashboard after login

### 3.3 Test Team Invitations
- [ ] Invited user can accept via OAuth
- [ ] User is added to correct team after OAuth
- [ ] Invitation is marked as accepted

### 3.4 Visual Verification
- [ ] Signup page looks correct (no broken layout)
- [ ] Login page looks correct
- [ ] OAuth buttons have correct styling
- [ ] No console errors on auth pages

---

## Completion Checklist

- [ ] All Phase 1 tasks complete
- [ ] All Phase 2 tasks complete
- [ ] All Phase 3 tests pass
- [ ] Code committed and pushed
- [ ] Tested in production environment
