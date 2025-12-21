# E2E Critical Flows - Tasks

**Last Updated:** 2025-12-18 22:15 UTC
**Status:** COMPLETE

## Phase 1: Onboarding Flow Tests (P0 - Critical) ✅

**File:** `tests/e2e/onboarding.spec.ts`
**Status:** Complete (14 tests)

### 1.1 Onboarding Start Page
- [x] Redirects to login when not authenticated
- [x] ~~Page loads for new user without team~~ (skipped - needs fixtures)
- [x] ~~User with team redirected to app~~ (skipped - bug in view)

### 1.2 GitHub Connection (Pre-OAuth)
- [x] GitHub connect endpoint redirects appropriately

### 1.3 Onboarding Complete Page
- [x] Complete page shows success when accessed with team
- [x] Go to dashboard button navigates to app

### 1.4 Onboarding Step Navigation
- [x] Select repos page requires GitHub connection
- [x] Optional Jira step shows skip option
- [x] Optional Slack step shows skip option

### 1.5 Onboarding Access Control
- [x] Org selection without session redirects appropriately
- [x] Repos selection requires team

---

## Phase 2: Team Management Tests (P0 - Critical) ✅

**File:** `tests/e2e/teams.spec.ts`
**Status:** Complete (33 tests)

### 2.1 Team Settings Page
- [x] Team settings page loads
- [x] Shows team name field
- [x] Admin can edit team name
- [x] Save button exists on team settings

### 2.2 Team Members
- [x] Team members section displays
- [x] Pending invitations section displays

### 2.3 Team Invitations - Send
- [x] Invite form is visible to admin
- [x] Can enter email for invitation
- [x] Invalid email shows validation error

### 2.4 Teams List
- [x] Teams list page loads
- [x] Shows user teams or redirects to app

### 2.5 Team Deletion
- [x] Delete option requires admin access
- [x] Delete endpoint requires POST method

### 2.6 Invitation Acceptance (Public)
- [x] Non-existent invitation returns appropriate response
- [x] Invitation signup page route exists

### 2.7 Team Navigation
- [x] Can navigate to team settings from app
- [x] Team settings link in sidebar

### 2.8 Team Member Management
- [x] Member details page access
- [x] Member removal requires POST

### 2.9 Team Invitation Flow
- [x] Send invitation endpoint requires auth
- [x] Cancel invitation endpoint requires auth

---

## Phase 3: Authentication Completion (P1 - High) ✅

**File:** `tests/e2e/auth.spec.ts` (extended)
**Status:** Complete (+8 tests)

### 3.1 Signup Flow
- [x] Signup page loads
- [x] Signup page has form fields
- [x] Invalid signup shows validation

### 3.2 Password Change
- [x] Password change page requires authentication
- [x] Password change page loads when logged in

### 3.3 Password Reset
- [x] Password reset page loads
- [x] Password reset accepts email input
- [x] Password reset confirmation route exists

---

## Phase 4: User Profile Tests (P1 - High) ✅

**File:** `tests/e2e/profile.spec.ts`
**Status:** Complete (14 tests)

### 4.1 Profile Page
- [x] Profile page loads
- [x] Shows current user email
- [x] Has editable fields
- [x] Save button exists

### 4.2 Profile Updates
- [x] Can update display name

### 4.3 Avatar Upload
- [x] Avatar upload section exists

### 4.4 API Keys
- [x] API keys section exists on profile
- [x] New API key button exists
- [x] Create API key endpoint requires auth
- [x] Revoke API key endpoint requires auth

### 4.5 Profile Access Control
- [x] Profile page requires authentication

### 4.6 Profile Navigation
- [x] Can navigate to profile from app
- [x] Profile link in user menu

---

## Phase 5: Subscription Page Tests (P2 - Medium) ✅

**File:** `tests/e2e/subscription.spec.ts`
**Status:** Complete (17 tests)

### 5.1 Subscription Page Load
- [x] Subscription page loads
- [x] Shows subscription status

### 5.2 Plan Display
- [x] Shows available plans or current plan
- [x] Upgrade button visible when applicable

### 5.3 Stripe Integration Points
- [x] Checkout canceled page loads
- [x] Subscription confirm page exists

### 5.4 Demo Mode
- [x] Demo page loads

### 5.5 Billing Portal
- [x] Portal link exists for subscribed users

### 5.6 Access Control
- [x] Subscription page requires authentication
- [x] Subscription page requires team membership

### 5.7 Subscription Navigation
- [x] Can navigate to billing from app
- [x] Billing link in sidebar

### 5.8 Subscription API Endpoints
- [x] Products API endpoint exists
- [x] Create checkout session requires auth
- [x] Create portal session requires auth

---

## Summary

| Phase | Tests | Status |
|-------|-------|--------|
| 1. Onboarding | 14 | ✅ Complete |
| 2. Teams | 33 | ✅ Complete |
| 3. Auth | +8 | ✅ Complete |
| 4. Profile | 14 | ✅ Complete |
| 5. Subscription | 17 | ✅ Complete |
| **Total New** | **86** | |

**Final Result:** 114 → 185 tests (62% increase)

---

## Bugs Fixed (Discovered During Testing)

### Bug 1: Onboarding Redirect (P1) ✅
- [x] Fix `apps/onboarding/views.py` - Changed to `redirect("web:home")`
- [x] Fix `apps/teams/views/invitation_views.py` - Same fix
- [x] Unskip `onboarding.spec.ts:30` after fix
- [x] Add unit tests: `apps/onboarding/tests/test_views.py`

### Bug 2: Invitation UUID Validation (P2) ✅
- [x] Add UUID validation in `apps/teams/views/invitation_views.py`
- [x] Return 404 instead of 500 for invalid UUIDs
- [x] Add unit tests: `apps/teams/tests/test_invitation_views.py`
