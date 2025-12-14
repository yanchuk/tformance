# E2E Testing Plan - Main User Flows

**Last Updated:** 2025-12-13
**Priority:** HIGH
**Status:** Planning Complete - Ready for Implementation

---

## Executive Summary

Implement comprehensive E2E testing using Playwright MCP to verify all main user flows work correctly. The project has Playwright installed but no E2E tests exist. This plan covers testing critical user journeys, identifying failures, and preparing fixes.

---

## Current State Analysis

### Test Infrastructure
| Component | Status |
|-----------|--------|
| Playwright | Installed (`@playwright/test@^1.57.0`) but unconfigured |
| Django Tests | 61 test files, comprehensive backend coverage |
| Factory Boy | Configured with all model factories |
| E2E Tests | **None exist** |
| Playwright MCP | Available for browser automation |

### Application Stack
- **Backend:** Django 5.2+ on `localhost:8000`
- **Frontend:** HTMX + Alpine.js + Chart.js
- **Database:** PostgreSQL on `localhost:5432`
- **Cache:** Redis on `localhost:6379`
- **Auth:** django-allauth (email/password, Google OAuth)

---

## Testing Strategy

### Approach: MCP-Driven E2E Testing
Use Playwright MCP tools for interactive testing:
1. Navigate to pages
2. Take snapshots for element discovery
3. Fill forms and click buttons
4. Verify outcomes via screenshots and assertions
5. Document failures for fix planning

### Test Categories

| Priority | Category | Tests |
|----------|----------|-------|
| P0 | Authentication | Login, Signup, Logout |
| P0 | Onboarding | Complete flow (GitHub → Dashboard) |
| P0 | Dashboard | CTO overview, Team dashboard |
| P1 | Integrations | GitHub, Jira, Slack setup |
| P1 | Surveys | Author/Reviewer flows |
| P2 | Team Management | Invite, roles, settings |
| P2 | User Profile | Profile editing, API keys |

---

## Phase 1: Environment Setup & Smoke Tests

### 1.1 Verify Dev Server Running
```bash
make start-bg  # Start PostgreSQL + Redis
make dev       # Start Django + Vite
```

**Verification:**
- `curl localhost:8000/health/` returns 200
- Homepage loads without errors

### 1.2 Create Test User
Using Django shell or existing superuser:
```bash
make manage ARGS='createsuperuser'
# Or use seed data
python manage.py seed_demo_data
```

### 1.3 Smoke Test Checklist
- [ ] Homepage loads (`/`)
- [ ] Login page loads (`/accounts/login/`)
- [ ] Signup page loads (`/accounts/signup/`)
- [ ] Health endpoint returns 200 (`/health/`)
- [ ] Static assets load (CSS, JS)

---

## Phase 2: Authentication Flow Testing

### 2.1 Login Flow
**URL:** `/accounts/login/`

**Steps:**
1. Navigate to login page
2. Snapshot to find form elements
3. Fill email and password
4. Submit form
5. Verify redirect to dashboard or onboarding

**Expected Outcomes:**
- Valid credentials → Redirect to `/app/` or `/onboarding/`
- Invalid credentials → Error message displayed
- Empty fields → Validation errors

### 2.2 Signup Flow
**URL:** `/accounts/signup/`

**Steps:**
1. Navigate to signup page
2. Fill registration form (email, password, confirm)
3. Submit form
4. Verify account created and redirected

**Expected Outcomes:**
- Valid signup → Redirect to onboarding
- Duplicate email → Error message
- Password mismatch → Validation error

### 2.3 Logout Flow
**Steps:**
1. Login first
2. Navigate to logout or click logout button
3. Verify session cleared
4. Verify redirect to homepage

---

## Phase 3: Onboarding Flow Testing

### 3.1 Complete Onboarding Journey

**Flow:** Start → GitHub → Org → Repos → Jira (Skip) → Slack (Skip) → Complete

| Step | URL | Actions |
|------|-----|---------|
| 1. Start | `/onboarding/` | Click "Connect GitHub" |
| 2. GitHub OAuth | External | Simulate or mock OAuth |
| 3. Select Org | `/onboarding/org/` | Select from dropdown |
| 4. Select Repos | `/onboarding/repos/` | Check repos, submit |
| 5. Jira | `/onboarding/jira/` | Click "Skip" |
| 6. Slack | `/onboarding/slack/` | Click "Skip" |
| 7. Complete | `/onboarding/complete/` | Click "View Dashboard" |

**Testing Approach:**
- Use pre-seeded team with existing GitHub integration (bypass OAuth)
- Or test with already-connected user

### 3.2 OAuth Testing Considerations

OAuth flows require external service interaction. Options:
1. **Mock OAuth:** Use Django test settings to bypass OAuth
2. **Pre-seeded Data:** Create team with integration already connected
3. **Manual OAuth:** Complete OAuth once, then test subsequent flows

---

## Phase 4: Dashboard Testing

### 4.1 CTO Dashboard
**URL:** `/app/<team_slug>/metrics/dashboard/cto/`
**Requires:** Admin role

**Test Cases:**
- [ ] Dashboard loads without errors
- [ ] Charts render (AI Adoption, AI vs Quality)
- [ ] Stats cards display (PRs Merged, Cycle Time, etc.)
- [ ] Team breakdown table loads
- [ ] Leaderboard table loads
- [ ] Date range filter works

### 4.2 Team Dashboard
**URL:** `/app/<team_slug>/metrics/dashboard/team/`
**Requires:** Any team member

**Test Cases:**
- [ ] Dashboard loads for regular members
- [ ] Cycle time chart renders
- [ ] Leaderboard visible
- [ ] HTMX lazy loading works

### 4.3 Chart Verification
Check individual chart endpoints:
- `/app/<slug>/metrics/charts/ai-adoption/`
- `/app/<slug>/metrics/charts/ai-quality/`
- `/app/<slug>/metrics/charts/cycle-time/`

---

## Phase 5: Integration Testing

### 5.1 Integrations Home
**URL:** `/app/<team_slug>/integrations/`

**Test Cases:**
- [ ] Page loads with integration status
- [ ] GitHub status shows connected/disconnected
- [ ] Jira status shows connected/disconnected
- [ ] Slack status shows connected/disconnected

### 5.2 GitHub Integration
**Test Cases:**
- [ ] Members list loads (`/integrations/github/members/`)
- [ ] Repos list loads (`/integrations/github/repos/`)
- [ ] Toggle repo tracking works
- [ ] Manual sync triggers correctly

### 5.3 Jira Integration
**Test Cases:**
- [ ] Projects list loads (`/integrations/jira/projects/`)
- [ ] Toggle project tracking works

### 5.4 Slack Integration
**Test Cases:**
- [ ] Settings page loads (`/integrations/slack/settings/`)
- [ ] Channel configuration saves
- [ ] Feature toggles work (surveys, reveals)

---

## Phase 6: Survey Flow Testing

### 6.1 Author Survey
**URL:** `/survey/<token>/author/`

**Test Cases:**
- [ ] Survey page loads with valid token
- [ ] AI assistance question displays
- [ ] Yes/No buttons work
- [ ] Submission redirects to complete

### 6.2 Reviewer Survey
**URL:** `/survey/<token>/reviewer/`

**Test Cases:**
- [ ] Survey page loads with valid token
- [ ] Quality rating options display
- [ ] AI guess options display
- [ ] Submission works
- [ ] Reveal shows if author responded

### 6.3 Token Validation
- [ ] Invalid token shows 404
- [ ] Expired token shows 410 (Gone)
- [ ] Already-responded survey shows completion page

---

## Phase 7: Error Handling & Edge Cases

### 7.1 Access Control
- [ ] Unauthenticated user redirected to login
- [ ] Non-admin can't access CTO dashboard
- [ ] Team member can't access other team's data
- [ ] Rate limiting works (10/min for OAuth)

### 7.2 Error Pages
- [ ] 404 page renders correctly
- [ ] 403 page renders correctly
- [ ] 500 page renders correctly (test mode)

### 7.3 Form Validation
- [ ] Empty required fields show errors
- [ ] Invalid email format rejected
- [ ] XSS input sanitized

---

## Fix Strategy

### When Tests Fail

1. **Screenshot the failure** - Use `browser_take_screenshot`
2. **Check console errors** - Use `browser_console_messages`
3. **Check network requests** - Use `browser_network_requests`
4. **Document the issue** in `e2e-testing-fixes.md`

### Common Fix Categories

| Issue Type | Investigation | Fix Approach |
|------------|---------------|--------------|
| Page not loading | Check server logs | Fix view/URL |
| Element not found | Check template | Fix selector/HTML |
| Form not submitting | Check JS console | Fix HTMX/Alpine |
| Auth redirect loop | Check middleware | Fix auth flow |
| Data not displaying | Check API response | Fix serializer/view |
| HTMX not working | Check network tab | Fix hx-* attributes |

### Fix Documentation Template

```markdown
## Issue: [Brief Description]

**URL:** /path/to/page
**Test:** [Test name]
**Screenshot:** [Link to screenshot]

### Symptoms
- What happened

### Root Cause
- Why it happened

### Fix
- File: path/to/file.py
- Change: Description of change

### Verification
- How to verify the fix works
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Critical flows passing | 100% |
| Page load time | < 3s |
| JavaScript errors | 0 |
| Console warnings | Documented |
| Screenshot coverage | All pages |

---

## Test Execution Order

1. **Environment Setup** - Verify server running
2. **Smoke Tests** - Basic page loads
3. **Auth Tests** - Login/Signup/Logout
4. **Dashboard Tests** - Main views
5. **Integration Tests** - Settings pages
6. **Survey Tests** - Token-based flows
7. **Edge Cases** - Errors and validation

---

## Dependencies

| Dependency | Required For |
|------------|--------------|
| Running dev server | All tests |
| Test user account | Auth tests |
| Pre-seeded team | Dashboard tests |
| GitHub integration | Integration tests |
| Survey tokens | Survey tests |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| OAuth flows can't be tested | High | Use pre-seeded data |
| HTMX timing issues | Medium | Add explicit waits |
| Data isolation failures | High | Use unique test data |
| Flaky tests | Medium | Retry logic, screenshots |
