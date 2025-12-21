# E2E Critical Flows Test Coverage Plan

**Last Updated:** 2025-12-18

## Executive Summary

This plan addresses missing e2e test coverage for critical user flows in the tformance MVP. Analysis of URL patterns, PRD documentation, and existing test files reveals significant gaps in:
1. **Onboarding Flow** - Zero tests for the 6-step new user journey
2. **Team Management** - No tests for team settings, member management, invitations
3. **User Profile** - No tests for profile editing, API keys
4. **Subscription/Billing** - No tests for Stripe checkout, billing portal
5. **Authentication Gaps** - Missing signup flow, password reset/change tests

## Current State Analysis

### Existing E2E Test Coverage

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `smoke.spec.ts` | 6 | Basic page loads, health check |
| `auth.spec.ts` | 5 | Login, logout, access control |
| `dashboard.spec.ts` | 25 | Team/CTO dashboards, filters, charts |
| `integrations.spec.ts` | 5 | Integration status page |
| `surveys.spec.ts` | 17 | Survey token validation, page structure |
| `copilot.spec.ts` | 15 | Copilot metrics on CTO dashboard |
| `interactive.spec.ts` | 35 | Buttons, forms, modals, HTMX |
| `accessibility.spec.ts` | 6 | Basic a11y checks |
| **Total** | **114** | |

### Critical Gaps Identified

#### 1. Onboarding Flow (CRITICAL - Zero Coverage)

**PRD Reference:** `prd/ONBOARDING.md`
**URLs:** `/onboarding/*`

| Step | URL | Status |
|------|-----|--------|
| Start | `/onboarding/` | NOT TESTED |
| GitHub Connect | `/onboarding/github/` | NOT TESTED |
| GitHub Callback | `/onboarding/github/callback/` | NOT TESTED |
| Org Selection | `/onboarding/org/` | NOT TESTED |
| Repo Selection | `/onboarding/repos/` | NOT TESTED |
| Jira (Optional) | `/onboarding/jira/` | NOT TESTED |
| Slack (Optional) | `/onboarding/slack/` | NOT TESTED |
| Complete | `/onboarding/complete/` | NOT TESTED |

**Impact:** New users cannot be verified to successfully complete onboarding.

#### 2. Team Management (CRITICAL - Zero Coverage)

**URLs:** `/app/team/*`

| Feature | URL | Status |
|---------|-----|--------|
| Team Settings | `/app/team/` | NOT TESTED |
| Delete Team | `/app/team/delete` | NOT TESTED |
| Member Details | `/app/team/members/<id>/` | NOT TESTED |
| Remove Member | `/app/team/members/<id>/remove/` | NOT TESTED |
| Send Invitation | `/app/team/invite/` | NOT TESTED |
| Cancel Invitation | `/app/team/invite/cancel/<id>/` | NOT TESTED |
| Resend Invitation | `/app/team/invite/<id>/` | NOT TESTED |

**Public URLs:**
| Feature | URL | Status |
|---------|-----|--------|
| Accept Invitation | `/teams/invitation/<id>/` | NOT TESTED |
| Signup via Invite | `/teams/invitation/<id>/signup/` | NOT TESTED |
| Manage Teams | `/teams/` | NOT TESTED |

**Impact:** Team administration flows completely unverified.

#### 3. User Profile (HIGH - Zero Coverage)

**URLs:** `/users/*`

| Feature | URL | Status |
|---------|-----|--------|
| Profile Page | `/users/profile/` | NOT TESTED |
| Upload Avatar | `/users/profile/upload-image/` | NOT TESTED |
| Create API Key | `/users/api-keys/create/` | NOT TESTED |
| Revoke API Key | `/users/api-keys/revoke/` | NOT TESTED |

**Impact:** User self-service profile management unverified.

#### 4. Authentication Gaps (HIGH - Partial Coverage)

**URLs:** `/accounts/*`

| Feature | URL | Status |
|---------|-----|--------|
| Login | `/accounts/login/` | TESTED |
| Logout | `/accounts/logout/` | TESTED |
| **Signup** | `/accounts/signup/` | **NOT TESTED** |
| **Password Change** | `/accounts/password/change/` | **NOT TESTED** |
| **Password Reset** | `/accounts/password/reset/` | **NOT TESTED** |
| **Email Confirmation** | `/accounts/confirm-email/*` | **NOT TESTED** |

**Impact:** Cannot verify new user registration works.

#### 5. Subscription/Billing (MEDIUM - Zero Coverage)

**URLs:** `/app/subscription/*`

| Feature | URL | Status |
|---------|-----|--------|
| Subscription Page | `/app/subscription/` | NOT TESTED |
| Checkout Canceled | `/app/subscription/checkout-canceled/` | NOT TESTED |
| Stripe Portal | `/app/subscription/stripe/portal/` | NOT TESTED |
| Create Checkout | `/app/subscription/stripe/api/create-checkout-session/` | NOT TESTED |

**Impact:** Billing flows unverified (though Stripe handles actual payments).

---

## Implementation Plan

### Phase 1: Onboarding Flow Tests (Critical)
**Priority:** P0 - Blocking
**Effort:** L (Large)

Tests for the complete onboarding journey per `ONBOARDING.md`.

### Phase 2: Team Management Tests (Critical)
**Priority:** P0 - Blocking
**Effort:** M (Medium)

Tests for team settings, member management, and invitation flows.

### Phase 3: Authentication Completion (High)
**Priority:** P1 - High
**Effort:** S (Small)

Complete auth coverage with signup, password flows.

### Phase 4: User Profile Tests (High)
**Priority:** P1 - High
**Effort:** S (Small)

Profile editing, avatar upload, API key management.

### Phase 5: Subscription Page Tests (Medium)
**Priority:** P2 - Medium
**Effort:** S (Small)

Subscription page load, upgrade prompts (skip actual Stripe flows).

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Total E2E Tests | 114 | 170+ |
| Critical Flow Coverage | 40% | 95% |
| Onboarding Coverage | 0% | 100% |
| Team Management Coverage | 0% | 90% |
| Auth Coverage | 60% | 100% |

---

## Risk Assessment

### High Risks
1. **OAuth mocking complexity** - GitHub/Jira/Slack OAuth in tests
   - Mitigation: Test up to OAuth redirect, verify callback handling separately

2. **Stripe checkout testing** - External payment provider
   - Mitigation: Test page loads and demo mode only, skip actual Stripe flows

### Medium Risks
1. **Test data setup** - Need proper seed data for all flows
   - Mitigation: Use existing `seed_demo_data` command, extend fixtures

2. **HTMX timing issues** - Dynamic content loading
   - Mitigation: Use `waitForLoadState('domcontentloaded')` pattern from existing tests

---

## Dependencies

- Existing test fixtures in `tests/e2e/fixtures/`
- Dev server running with seed data
- Django session handling for authentication
