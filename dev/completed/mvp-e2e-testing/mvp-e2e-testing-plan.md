# MVP E2E Testing - Comprehensive Plan

**Last Updated: 2025-12-18**
**Status: PLANNING**

## Executive Summary

This plan outlines a comprehensive end-to-end testing strategy for the AI Impact Analytics MVP. The goal is to ensure all user-facing features are tested through Playwright, with a focus on interactive elements, user flows, and data-driven scenarios using seeded demo data.

**Current State:**
- 5 e2e test files with ~78 tests
- Good dashboard coverage (62 tests)
- Major gaps in integration flows, surveys, and interactive elements
- Seed system exists but not integrated into test setup

**Proposed State:**
- 12+ test files with ~200+ tests
- Complete coverage of all MVP features
- Automated seed data setup per test suite
- Interactive element testing (buttons, forms, filters)
- Cross-browser validation (Chrome + Firefox)

## Current State Analysis

### Existing E2E Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `smoke.spec.ts` | 6 | Homepage, login, signup, health, 404, static assets |
| `auth.spec.ts` | 6 | Login/logout, access control, redirects |
| `dashboard.spec.ts` | 62 | App home, team dashboard, CTO dashboard, navigation |
| `accessibility.spec.ts` | 6 | WCAG 2.1 AA compliance (axe-core) |
| `integrations.spec.ts` | 4 | Integration hub overview only |
| **Total** | **~78** | |

### Coverage Gaps Identified

1. **Integration Connection Flows** (CRITICAL)
   - No OAuth flow testing (GitHub, Jira, Slack)
   - No repository/project selection workflows
   - No member sync verification
   - No disconnect/reconnect scenarios

2. **Survey System** (HIGH)
   - No author survey response flow
   - No reviewer survey + quality rating
   - No survey reveal/accuracy display
   - No token expiration handling

3. **Interactive Elements** (HIGH)
   - Filter buttons tested minimally
   - No toggle switch testing
   - No modal interactions
   - No form submission flows

4. **Copilot Metrics** (MEDIUM)
   - No Copilot dashboard section tests
   - No sync button interaction
   - No Copilot member table tests

5. **Team Management** (MEDIUM)
   - No team settings modification
   - No member role changes
   - No invitation flow

6. **Error States** (LOW)
   - No empty state tests
   - No error page handling
   - No API failure scenarios

## Proposed Test Architecture

### Test File Structure

```
tests/e2e/
├── smoke.spec.ts          # Basic health checks (existing)
├── auth.spec.ts           # Authentication flows (existing, expand)
├── dashboard.spec.ts      # Dashboard views (existing, expand)
├── accessibility.spec.ts  # WCAG compliance (existing)
├── integrations.spec.ts   # Integration hub (existing, expand)
├── integrations-github.spec.ts   # NEW: GitHub-specific flows
├── integrations-jira.spec.ts     # NEW: Jira-specific flows
├── integrations-slack.spec.ts    # NEW: Slack-specific flows
├── surveys.spec.ts        # NEW: Survey response flows
├── team-management.spec.ts # NEW: Team/member management
├── copilot.spec.ts        # NEW: Copilot metrics section
├── interactive.spec.ts    # NEW: All clickable elements
├── data-driven.spec.ts    # NEW: Verify metrics with seed data
└── fixtures/
    ├── seed-helpers.ts    # NEW: Seed data management
    └── test-users.ts      # NEW: Test user credentials
```

### Test Categories

| Category | Priority | Test Count | Description |
|----------|----------|------------|-------------|
| Smoke | P0 | 10 | Critical path health checks |
| Auth | P0 | 15 | Login, logout, session, access control |
| Dashboard Core | P0 | 40 | Page loads, cards, charts render |
| Dashboard Interactive | P1 | 30 | Filters, tabs, pagination |
| Integrations Overview | P1 | 15 | Hub, status cards, connect buttons |
| GitHub Integration | P1 | 20 | Members, repos, sync flows |
| Jira Integration | P2 | 15 | Projects, user matching |
| Slack Integration | P2 | 10 | Settings, connection |
| Surveys | P1 | 25 | Author, reviewer, reveal flows |
| Copilot | P1 | 15 | Metrics cards, trends, tables |
| Team Management | P2 | 20 | Settings, members, invites |
| Interactive Elements | P1 | 30 | All buttons, toggles, forms |
| Data Validation | P2 | 15 | Verify calculated metrics |
| **Total** | | **~260** | |

## Implementation Phases

### Phase 1: Test Infrastructure (S - 2-3h)

**Goal:** Set up proper test infrastructure with seed data helpers

**Tasks:**
1. Create seed helper module (`fixtures/seed-helpers.ts`)
2. Add test user management (`fixtures/test-users.ts`)
3. Update `playwright.config.ts` for multi-browser
4. Create global setup for seed data verification
5. Add custom test fixtures for common patterns

**Deliverables:**
- Reusable seed data helpers
- Multi-browser configuration (Chrome + Firefox)
- Global beforeAll/afterAll hooks

### Phase 2: Expand Existing Tests (M - 4-6h)

**Goal:** Fill gaps in existing test files

**Tasks:**
1. Expand `smoke.spec.ts`:
   - Add tests for all public pages
   - Add API endpoint health checks
   - Test redirect logic for authenticated users

2. Expand `auth.spec.ts`:
   - Add signup flow test
   - Add password reset flow
   - Add session timeout handling
   - Add multi-tab session test

3. Expand `dashboard.spec.ts`:
   - Test all chart interactions (hover, click)
   - Test table sorting and pagination
   - Test empty state displays
   - Verify data matches seed values

4. Expand `integrations.spec.ts`:
   - Test all integration card states
   - Test connect button visibility logic
   - Test integration status badges

### Phase 3: New Integration Tests (L - 6-8h)

**Goal:** Complete integration flow coverage

**Tasks:**
1. Create `integrations-github.spec.ts`:
   - Test member list display
   - Test member toggle (include/exclude)
   - Test member sync button
   - Test repository list display
   - Test repository toggle (track/untrack)
   - Test repository sync button
   - Test disconnect confirmation modal

2. Create `integrations-jira.spec.ts`:
   - Test project list display
   - Test project toggle
   - Test user matching display
   - Test disconnect flow

3. Create `integrations-slack.spec.ts`:
   - Test settings page display
   - Test survey channel configuration
   - Test disconnect flow

### Phase 4: Survey System Tests (M - 4-6h)

**Goal:** Complete survey flow coverage

**Tasks:**
1. Create `surveys.spec.ts`:
   - Test survey landing page routing
   - Test author survey form
   - Test author survey submission
   - Test reviewer survey form (quality + guess)
   - Test reviewer survey submission
   - Test reveal page display
   - Test accuracy calculation display
   - Test expired token handling
   - Test invalid token handling
   - Test survey completion redirect

### Phase 5: Interactive Elements (L - 6-8h)

**Goal:** Test all clickable UI elements

**Tasks:**
1. Create `interactive.spec.ts`:
   - Test all navigation links
   - Test all button clicks
   - Test all toggle switches
   - Test all dropdown menus
   - Test all modal open/close
   - Test all form submissions
   - Test all date range filter buttons
   - Test all HTMX-loaded content
   - Test all expandable sections
   - Test all tab navigation

### Phase 6: Copilot & Team Management (M - 4-6h)

**Goal:** Cover remaining MVP features

**Tasks:**
1. Create `copilot.spec.ts`:
   - Test Copilot section visibility (CTO dashboard)
   - Test Copilot metrics cards render
   - Test Copilot trend chart
   - Test Copilot member table
   - Test sync button interaction

2. Create `team-management.spec.ts`:
   - Test team settings page load
   - Test team name/slug edit
   - Test member list display
   - Test member role dropdown
   - Test member removal flow
   - Test invitation sending
   - Test invitation acceptance

### Phase 7: Data Validation Tests (M - 4-6h)

**Goal:** Verify displayed metrics match seed data

**Tasks:**
1. Create `data-driven.spec.ts`:
   - Query seed data values via API/DB
   - Compare dashboard displayed values
   - Verify PR counts match seed
   - Verify cycle time calculations
   - Verify AI adoption percentages
   - Test filter changes update values correctly

## Technical Specifications

### Seed Data Integration

```typescript
// fixtures/seed-helpers.ts
export async function ensureSeedData(): Promise<void> {
  // Check if seed data exists
  // If not, run seed command
  // Return when ready
}

export async function resetSeedData(): Promise<void> {
  // Clear and reseed for clean state
}

export const SEED_DATA = {
  teams: 1,
  members: 5,
  prs: 50,
  surveys: 30,
  reviews: 60,
};
```

### Test User Management

```typescript
// fixtures/test-users.ts
export const TEST_USERS = {
  admin: {
    email: 'admin@example.com',
    password: 'admin123',
    role: 'admin',
  },
  lead: {
    email: 'lead@example.com',
    password: 'lead123',
    role: 'lead',
  },
  developer: {
    email: 'dev@example.com',
    password: 'dev123',
    role: 'developer',
  },
};

export async function loginAs(page: Page, user: keyof typeof TEST_USERS): Promise<void> {
  const { email, password } = TEST_USERS[user];
  await page.goto('/accounts/login/');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL(/\/(app|onboarding)/);
}
```

### Multi-Browser Configuration

```typescript
// playwright.config.ts additions
projects: [
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'] },
  },
  {
    name: 'firefox',
    use: { ...devices['Desktop Firefox'] },
  },
],
```

### Custom Test Fixtures

```typescript
// fixtures/test-fixtures.ts
import { test as base } from '@playwright/test';

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    await loginAs(page, 'admin');
    await use(page);
  },
  dashboardPage: async ({ page }, use) => {
    await loginAs(page, 'admin');
    await page.goto('/app/metrics/dashboard/team/');
    await use(page);
  },
});
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Flaky tests due to HTMX timing | High | Medium | Add explicit waits, use `waitForResponse` |
| Seed data inconsistency | Medium | High | Add seed validation before test runs |
| OAuth flows hard to test | High | Medium | Mock OAuth or use test credentials |
| Test parallelization conflicts | Medium | Medium | Use test isolation, unique data per test |
| Browser-specific failures | Low | Medium | Run cross-browser in CI |

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test count | 200+ | `npm test -- --list` |
| Line coverage proxy | 80%+ | Features with tests / Total features |
| Pass rate | 99%+ | CI success rate |
| Execution time | <5 min | CI pipeline duration |
| Flaky test rate | <2% | Failed tests that pass on retry |

## Required Resources

### Dependencies
- `@playwright/test` (existing)
- `@axe-core/playwright` (existing)
- No new dependencies required

### Development Time
| Phase | Effort | Duration |
|-------|--------|----------|
| Phase 1: Infrastructure | S | 2-3h |
| Phase 2: Expand Existing | M | 4-6h |
| Phase 3: Integration Tests | L | 6-8h |
| Phase 4: Survey Tests | M | 4-6h |
| Phase 5: Interactive Tests | L | 6-8h |
| Phase 6: Copilot & Team | M | 4-6h |
| Phase 7: Data Validation | M | 4-6h |
| **Total** | | **30-43h** |

### Team Requirements
- 1 developer with Playwright experience
- Access to test environment with seed data
- CI pipeline for automated runs

## Appendix: Interactive Elements Inventory

### Navigation Elements
- Logo (home link)
- Dashboard link
- Integrations link
- Team Settings link
- Profile dropdown
- Logout button
- Breadcrumb links

### Dashboard Buttons
- Date range: 7d, 30d, 90d, Custom
- View Analytics (app home)
- Manage Integrations
- Chart expand/collapse
- Table pagination (prev/next)
- Table sorting headers

### Integration Buttons
- Connect GitHub
- Connect Jira
- Connect Slack
- Disconnect (each)
- Sync Now (each)
- Toggle member (each)
- Toggle repository (each)
- Toggle project (each)

### Form Elements
- Login form (email, password, submit)
- Signup form
- Team settings form
- Survey forms (radio, buttons)
- Date picker (custom range)

### Modal Interactions
- Disconnect confirmation
- Delete confirmation
- Invite member
- Role change
