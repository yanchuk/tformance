# E2E Critical Flows - Context

**Last Updated:** 2025-12-18 22:15 UTC
**Status:** COMPLETE - All phases implemented

## Implementation Summary

Successfully increased e2e test coverage from **114 tests** to **185 tests** (62% increase).

### Test Results
```
185 passed (52.4s)
4 skipped (documented limitations)
```

## New Test Files Created

| File | Tests | Description |
|------|-------|-------------|
| `tests/e2e/onboarding.spec.ts` | 14 | Onboarding flow, GitHub/Jira/Slack steps, access control |
| `tests/e2e/teams.spec.ts` | 33 | Team settings, members, invitations, navigation |
| `tests/e2e/profile.spec.ts` | 14 | Profile page, API keys, avatar, access control |
| `tests/e2e/subscription.spec.ts` | 17 | Billing page, plans, Stripe integration points |
| `tests/e2e/auth.spec.ts` (extended) | +8 | Signup flow, password change/reset |

## Key Files

### E2E Test Files (Complete Suite)
- `tests/e2e/smoke.spec.ts` - Basic page load tests
- `tests/e2e/auth.spec.ts` - Login, logout, signup, password flows
- `tests/e2e/dashboard.spec.ts` - Dashboard charts, tables, filters
- `tests/e2e/integrations.spec.ts` - Integration status page
- `tests/e2e/surveys.spec.ts` - Survey token validation
- `tests/e2e/copilot.spec.ts` - Copilot metrics section
- `tests/e2e/interactive.spec.ts` - Buttons, forms, modals, HTMX
- `tests/e2e/accessibility.spec.ts` - Basic a11y checks
- `tests/e2e/onboarding.spec.ts` - **NEW** Onboarding flow
- `tests/e2e/teams.spec.ts` - **NEW** Team management
- `tests/e2e/profile.spec.ts` - **NEW** User profile
- `tests/e2e/subscription.spec.ts` - **NEW** Billing/subscription

### Test Infrastructure
- `tests/e2e/fixtures/test-users.ts` - Test credentials and `loginAs()` helper
- `tests/e2e/fixtures/seed-helpers.ts` - Seed data utilities
- `tests/e2e/fixtures/test-fixtures.ts` - Custom Playwright fixtures
- `playwright.config.ts` - Playwright configuration

## Key Decisions Made

1. **OAuth Testing Strategy**
   - Test up to OAuth redirect URL generation
   - Don't test actual external OAuth flows (Playwright blocks external redirects)
   - Accept any valid redirect (app, external OAuth, or onboarding)

2. **Stripe Testing Strategy**
   - Test subscription page loads and navigation
   - Test demo mode functionality
   - Use page navigation instead of direct API calls for product tests
   - Skip actual Stripe checkout/portal flows

3. **Element Selector Strategy**
   - Use flexible selectors with multiple fallbacks (heading OR input OR text)
   - Page headings discovered: "Team Details" (not "team settings"), "My Details" (not "profile")
   - API Keys section has "New API Key" button

4. **HTMX Testing Pattern**
   - Use `waitForLoadState('domcontentloaded')` (not `networkidle`)
   - Wait for specific elements after HTMX updates
   - Use `waitForTimeout` sparingly for dynamic content

5. **UUID Validation**
   - Use valid UUID format for non-existent records (`00000000-0000-0000-0000-000000000000`)
   - Invalid UUID format causes 500 error (view doesn't validate format)

## Bugs Discovered

### 1. Onboarding Redirect Bug (P1)
**Location:** `apps/onboarding/views.py:77`
**Error:** `NoReverseMatch for 'web_team:home' with team_slug`
**Cause:** View calls `redirect("web_team:home", team_slug=team.slug)` but URL pattern doesn't exist
**Impact:** Users with existing teams get 500 error when visiting /onboarding/
**Fix Required:** Change redirect to use correct URL pattern (likely `redirect("web:home")`)
**Test:** `onboarding.spec.ts:30` - marked as `test.skip`

### 2. Invitation UUID Validation Bug (P2)
**Location:** `apps/teams/views/invitation_views.py`
**Error:** `ValidationError: "invalid-uuid" is not a valid UUID`
**Cause:** View doesn't catch invalid UUID format before database lookup
**Impact:** Invalid invitation URLs return 500 instead of 404
**Fix Required:** Validate UUID format or catch ValidationError
**Workaround:** Tests use valid UUID format that doesn't exist

## Technical Notes

### Page Headings (Actual vs Expected)
| Page | Expected | Actual |
|------|----------|--------|
| Team settings | "Team Settings" | "Team Details" |
| Profile | "Profile" | "My Details" |
| API Keys | varies | "API Keys" heading with "New API Key" button |

### URL Patterns Covered
- `/onboarding/` - Start page (redirects based on user state)
- `/onboarding/github/` - GitHub OAuth initiation
- `/onboarding/org/` - Organization selection
- `/onboarding/repos/` - Repository selection
- `/onboarding/jira/` - Optional Jira connection
- `/onboarding/slack/` - Optional Slack connection
- `/onboarding/complete/` - Completion page
- `/app/team/` - Team settings
- `/app/team/invite/` - Send invitation
- `/teams/invitation/<uuid>/` - Accept invitation
- `/users/profile/` - User profile
- `/users/api-keys/create/` - Create API key
- `/app/subscription/` - Billing page
- `/app/subscription/demo/` - Demo mode

### Test User Credentials
```typescript
// From tests/e2e/fixtures/test-users.ts
admin: { email: 'admin@example.com', password: 'admin123' }
```

## Skipped Tests (4 total)

1. **onboarding.spec.ts:24** - "page loads for authenticated user without team"
   - Reason: Requires creating new user which affects database state
   - Fix: Would need test-specific user fixtures

2. **onboarding.spec.ts:30** - "user with team is redirected from onboarding to app"
   - Reason: Bug in onboarding view (NoReverseMatch)
   - Fix: Fix `apps/onboarding/views.py:77`

3. **copilot.spec.ts** (1 test) - Pre-existing skip
4. **interactive.spec.ts** (1 test) - Pre-existing skip

## Commands to Verify

```bash
# Run all e2e tests
make e2e

# Run new test files only
npx playwright test onboarding.spec.ts teams.spec.ts profile.spec.ts subscription.spec.ts auth.spec.ts --project=chromium

# Run specific test suite
npx playwright test teams.spec.ts --project=chromium

# View test report
make e2e-report
```

## Bugs Fixed

Both bugs discovered during testing have been fixed and covered with unit tests.

### Bug 1: Onboarding Redirect - FIXED
- **Fix:** Changed `redirect("web_team:home", team_slug=team.slug)` to `redirect("web:home")`
- **Files Modified:**
  - `apps/onboarding/views.py` - Fixed 4 occurrences
  - `apps/teams/views/invitation_views.py` - Fixed 2 occurrences
- **Unit Tests:** `apps/onboarding/tests/test_views.py` (5 tests)
- **E2E Test:** `onboarding.spec.ts:30` - unskipped and passing

### Bug 2: Invitation UUID Validation - FIXED
- **Fix:** Added UUID format validation before database lookup
- **Files Modified:**
  - `apps/teams/views/invitation_views.py` - Added `uuid.UUID()` validation
- **Unit Tests:** `apps/teams/tests/test_invitation_views.py` (7 tests)

## Final Test Results

```
E2E Tests: 186 passed, 3 skipped (52.4s)
Unit Tests (new): 12 tests passing
```

## Next Steps (If Continuing)

1. **Add test fixtures** for new user scenarios (would enable more onboarding tests)
2. Consider adding more OAuth callback tests with mocked responses
