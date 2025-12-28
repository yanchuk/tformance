# GitHub-Only Auth - Task Checklist

> **Last Updated**: 2024-12-28
> **Status**: Completed

## Phase 1: Settings & Context Processor

### 1.1 Add Auth Mode Settings
- [x] Add `AUTH_MODE` env variable to `settings.py`
- [x] Add `ALLOW_EMAIL_AUTH` derived setting
- [x] Add `ALLOW_GOOGLE_AUTH` setting (set to False)
- [x] Test settings load correctly in shell

**Files**: `tformance/settings.py:309-313`
**Effort**: S

### 1.2 Create Context Processor
- [x] Add `auth_mode()` function to `apps/web/context_processors.py`
- [x] Register in `TEMPLATES["OPTIONS"]["context_processors"]`
- [x] Verify variables available in template (`{{ AUTH_MODE }}`)

**Files**: `apps/web/context_processors.py:55-67`, `tformance/settings.py:200-201`
**Effort**: S

---

## Phase 2: Template Updates

### 2.1 Update Login Template
- [x] Wrap email form in `{% if ALLOW_EMAIL_AUTH %}`
- [x] Add GitHub-only hero section when email disabled
- [x] Update "Sign up" link (hide or change to GitHub signup)
- [x] Test both modes visually

**File**: `templates/account/login.html`
**Effort**: S

### 2.2 Update Signup Template
- [x] Wrap email form in `{% if ALLOW_EMAIL_AUTH %}`
- [x] Add GitHub-only CTA section when email disabled
- [x] Keep invitation banner visible (still useful context)
- [x] Update "Sign in" link appropriately
- [x] Test both modes visually

**File**: `templates/account/signup.html`
**Effort**: S

### 2.3 Update Social Buttons Component
- [x] Filter out Google if `ALLOW_GOOGLE_AUTH` is False
- [x] Hide divider when in github_only mode
- [x] Test with different provider configurations

**File**: `templates/account/components/social/social_buttons.html`
**Effort**: S

---

## Phase 3: Testing

### 3.1 Unit Tests
- [x] Test `auth_mode()` context processor
- [x] Test context variables in login/signup pages
- [x] Test template rendering in both modes

**File**: `apps/web/tests/test_context_processors.py`
**Tests**: 11 tests, all passing

### 3.2 E2E Tests
- [x] Create auth-mode.spec.ts test file
- [x] Test login page elements in both modes
- [x] Test signup page elements in both modes
- [x] Test Google OAuth is hidden
- [x] Test navigation between auth pages

**File**: `tests/e2e/auth-mode.spec.ts`

### 3.3 Manual Verification
- [x] Test login page in `AUTH_MODE=all`
- [x] Test login page in `AUTH_MODE=github_only`
- [x] Verify settings load correctly

---

## Acceptance Criteria - All Met

- [x] Login page shows only GitHub button in github_only mode
- [x] Email form hidden in github_only mode
- [x] Email auth still works in development (AUTH_MODE=all)
- [x] Unit tests pass (11/11)
- [x] No changes to OAuth integration flows (those stay as-is)
- [x] Google OAuth hidden (ALLOW_GOOGLE_AUTH=False)

---

## Files Modified

| File | Change |
|------|--------|
| `tformance/settings.py` | Added AUTH_MODE, ALLOW_EMAIL_AUTH, ALLOW_GOOGLE_AUTH |
| `apps/web/context_processors.py` | Added `auth_mode()` function |
| `templates/account/login.html` | Conditional email form rendering |
| `templates/account/signup.html` | Conditional email form rendering |
| `templates/account/components/social/social_buttons.html` | Filter providers, conditional divider |

## Files Created

| File | Purpose |
|------|---------|
| `apps/web/tests/test_context_processors.py` | Unit tests for auth mode |
| `tests/e2e/auth-mode.spec.ts` | E2E tests for auth mode |

---

## Quick Start Commands

```bash
# Development mode (email + GitHub)
make dev  # AUTH_MODE=all by default when DEBUG=True

# Production mode (GitHub only)
AUTH_MODE=github_only make dev

# Run unit tests
.venv/bin/pytest apps/web/tests/test_context_processors.py -v

# Run E2E tests
npx playwright test auth-mode.spec.ts
```

---

## Configuration Reference

```python
# settings.py
AUTH_MODE = env("AUTH_MODE", default="all" if DEBUG else "github_only")
ALLOW_EMAIL_AUTH = AUTH_MODE == "all"
ALLOW_GOOGLE_AUTH = False  # Disabled - GitHub only
```

| Environment | DEBUG | AUTH_MODE | Email | GitHub | Google |
|-------------|-------|-----------|-------|--------|--------|
| Development | True | `all` | Yes | Yes | No |
| Testing/CI | True | `all` | Yes | Yes | No |
| Production | False | `github_only` | No | Yes | No |
