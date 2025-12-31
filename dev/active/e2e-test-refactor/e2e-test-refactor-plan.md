# E2E Test Suite Refactoring Plan

**Last Updated**: 2025-12-31
**Status**: Planning
**Priority**: High - Improves CI reliability and developer experience

---

## Executive Summary

Refactor the Playwright E2E test suite to improve reliability, reduce code duplication, and enhance test coverage. The audit identified critical issues including a failing smoke test, 29 conditional test skips, duplicate helper functions across 15 files, and underutilization of shared fixtures.

### Goals
1. Fix failing smoke test and enhance smoke coverage
2. Consolidate duplicate helper functions into shared module
3. Migrate all test files to use shared fixtures
4. Remove remaining hardcoded waits
5. Add missing E2E coverage for critical flows

### Out of Scope
- Adding multi-browser CI job (recommendation #9 - deferred)

---

## Current State Analysis

### Test Suite Metrics
| Metric | Current Value |
|--------|---------------|
| Total test files | 25 |
| Total tests (Chromium) | 485 |
| Lines of test code | 8,514 |
| Files using fixtures | 8/25 (32%) |
| Duplicate helper functions | 15+ instances |
| Hardcoded waits remaining | 2 |
| Conditional skips | 29 |

### Critical Issues
1. **Failing smoke test** - PostHog script failure causes false positive
2. **Minimal smoke coverage** - No login/dashboard verification
3. **Code duplication** - `waitForHtmxComplete` defined 15 times
4. **Low fixture adoption** - Only 8/25 files use shared fixtures
5. **Data-dependent skips** - 29 tests skip based on runtime data

### File Structure
```
tests/e2e/
├── fixtures/
│   ├── index.ts
│   ├── seed-helpers.ts
│   ├── test-fixtures.ts    # Existing fixtures (underused)
│   └── test-users.ts
├── smoke.spec.ts           # 70 lines - needs enhancement
├── analytics.spec.ts       # 1,122 lines - largest
├── repo-selector.spec.ts   # 653 lines - 29 conditional skips
└── ... (22 more test files)
```

---

## Proposed Future State

### Target Metrics
| Metric | Target Value |
|--------|--------------|
| Files using fixtures | 25/25 (100%) |
| Duplicate helper functions | 0 |
| Hardcoded waits | 0 |
| Conditional skips | 0 (use mock data) |
| Smoke test coverage | Login + Dashboard + Navigation |

### New File Structure
```
tests/e2e/
├── helpers/
│   ├── index.ts            # Re-exports all helpers
│   ├── htmx.ts             # HTMX wait helpers
│   ├── alpine.ts           # Alpine.js helpers
│   ├── charts.ts           # Chart.js helpers
│   └── navigation.ts       # Page navigation helpers
├── fixtures/
│   ├── index.ts
│   ├── test-fixtures.ts    # Extended with more fixtures
│   └── test-users.ts
├── smoke.spec.ts           # Enhanced with critical path tests
└── ... (other test files - refactored)
```

---

## Implementation Phases

### Phase 1: Critical Fixes (Day 1)
Fix immediate issues blocking CI and smoke tests.

### Phase 2: Helper Consolidation (Day 1-2)
Create shared helper module and eliminate duplicates.

### Phase 3: Fixture Migration (Day 2-3)
Migrate all test files to use shared fixtures.

### Phase 4: Conditional Skip Elimination (Day 3)
Refactor repo-selector tests to use mock data.

### Phase 5: Coverage Enhancement (Day 3-4)
Add missing E2E tests for critical flows.

### Phase 6: Verification (Day 4)
Run full test suite and validate all changes.

---

## Detailed Implementation

### Phase 1: Critical Fixes

#### 1.1 Fix Smoke Test Asset Check
**Effort**: S | **Priority**: P0

**Problem**: Test fails when PostHog script is blocked/unavailable.

**Solution**: Exclude external analytics scripts from critical asset check.

```typescript
// Before
if ((url.includes('.js') || url.includes('.css')) && !url.includes('favicon')) {
  failedRequests.push(url);
}

// After
if (
  (url.includes('.js') || url.includes('.css')) &&
  !url.includes('favicon') &&
  !url.includes('posthog') &&
  !url.includes('analytics') &&
  url.startsWith(page.url().split('/').slice(0, 3).join('/'))  // Same origin only
) {
  failedRequests.push(url);
}
```

**Acceptance Criteria**:
- [ ] Smoke test passes when PostHog is blocked
- [ ] Smoke test still catches missing local assets
- [ ] `make e2e-smoke` completes successfully

#### 1.2 Enhance Smoke Tests with Login Flow
**Effort**: M | **Priority**: P0

**Add tests**:
1. Login with valid credentials succeeds
2. Dashboard loads after login
3. No console errors on critical pages
4. Sidebar navigation works

**Acceptance Criteria**:
- [ ] Smoke tests verify actual login works
- [ ] Smoke tests verify dashboard renders
- [ ] Smoke tests check for JS errors
- [ ] Total smoke test time < 30 seconds

#### 1.3 Remove Remaining Hardcoded Waits
**Effort**: S | **Priority**: P1

**Files**: `repo-selector.spec.ts` lines 30 and 540

**Replace with**:
```typescript
// Instead of: await page.waitForTimeout(200)
await page.waitForFunction(
  () => {
    const Alpine = (window as any).Alpine;
    return Alpine && Alpine.store && Alpine.store('dateRange') !== undefined;
  },
  { timeout: 5000 }
);
```

**Acceptance Criteria**:
- [ ] No `waitForTimeout` calls in codebase
- [ ] Tests still pass reliably
- [ ] Grep confirms: `grep -r "waitForTimeout" tests/e2e/` returns empty

---

### Phase 2: Helper Consolidation

#### 2.1 Create Shared Helpers Module
**Effort**: M | **Priority**: P1

**Create** `tests/e2e/helpers/` with:

**`htmx.ts`**:
```typescript
export async function waitForHtmxComplete(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout }
  );
}

export async function waitForHtmxSwap(page: Page, selector: string, timeout = 5000): Promise<void> {
  await page.waitForSelector(selector, { state: 'attached', timeout });
  await waitForHtmxComplete(page, timeout);
}
```

**`alpine.ts`**:
```typescript
export async function waitForAlpineStore(
  page: Page,
  storeName: string = 'dateRange',
  timeout = 5000
): Promise<void> {
  await page.waitForFunction(
    (name) => {
      const Alpine = (window as any).Alpine;
      return Alpine && Alpine.store && Alpine.store(name) !== undefined;
    },
    storeName,
    { timeout }
  );
}

export async function waitForAlpine(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => typeof (window as any).Alpine !== 'undefined',
    { timeout }
  );
}
```

**`charts.ts`**:
```typescript
export async function waitForChart(
  page: Page,
  chartId: string,
  timeout = 5000
): Promise<void> {
  await page.waitForSelector(`#${chartId}`, { state: 'attached', timeout });
  await waitForHtmxComplete(page, timeout);
}

export async function chartHasData(page: Page, chartId: string): Promise<boolean> {
  const canvas = page.locator(`#${chartId} canvas`);
  return canvas.isVisible();
}
```

**`index.ts`**:
```typescript
export * from './htmx';
export * from './alpine';
export * from './charts';
```

**Acceptance Criteria**:
- [ ] Helpers module created with all common functions
- [ ] Functions are typed with JSDoc comments
- [ ] Module exports work correctly

#### 2.2 Update Test Files to Use Shared Helpers
**Effort**: L | **Priority**: P1

**Files to update** (remove local helper definitions):
1. analytics.spec.ts
2. alpine-htmx-integration.spec.ts
3. copilot.spec.ts
4. dashboard-data-consistency.spec.ts
5. dashboard.spec.ts
6. feedback.spec.ts
7. htmx-navigation.spec.ts
8. insights.spec.ts
9. interactive.spec.ts
10. leaderboard.spec.ts
11. metric-toggle.spec.ts
12. repo-selector.spec.ts
13. trends-charts.spec.ts

**Pattern**:
```typescript
// Before (in each file)
async function waitForHtmxComplete(page: Page, timeout = 5000): Promise<void> {
  // ... duplicated implementation
}

// After
import { waitForHtmxComplete, waitForAlpineStore, waitForChart } from './helpers';
```

**Acceptance Criteria**:
- [ ] All files import from shared helpers
- [ ] No duplicate function definitions
- [ ] All tests still pass
- [ ] Lines of code reduced by ~200+

---

### Phase 3: Fixture Migration

#### 3.1 Extend Test Fixtures
**Effort**: S | **Priority**: P2

**Add to** `test-fixtures.ts`:
```typescript
// Analytics page fixture
analyticsPage: async ({ page }, use) => {
  await loginAs(page, 'admin');
  await page.goto('/app/metrics/analytics/');
  await waitForHtmxComplete(page);
  await use(page);
},

// PR list page fixture
prListPage: async ({ page }, use) => {
  await loginAs(page, 'admin');
  await page.goto('/app/metrics/pull-requests/');
  await waitForHtmxComplete(page);
  await use(page);
},
```

**Acceptance Criteria**:
- [ ] New fixtures added for common page states
- [ ] Fixtures handle HTMX loading automatically
- [ ] Types updated for new fixtures

#### 3.2 Migrate Files to Use Fixtures
**Effort**: L | **Priority**: P2

**Files to migrate** (17 files not using fixtures):
1. accessibility.spec.ts
2. alpine-htmx-integration.spec.ts
3. analytics.spec.ts
4. auth-mode.spec.ts
5. auth.spec.ts (keep some non-fixture tests for auth flows)
6. dashboard-data-consistency.spec.ts
7. dashboard.spec.ts
8. feedback.spec.ts
9. htmx-error-handling.spec.ts
10. htmx-navigation.spec.ts
11. insights.spec.ts
12. integrations.spec.ts
13. metric-toggle.spec.ts
14. onboarding.spec.ts (keep some for non-auth flows)
15. repo-selector.spec.ts
16. smoke.spec.ts (keep minimal for smoke tests)
17. surveys.spec.ts

**Pattern**:
```typescript
// Before
test.beforeEach(async ({ page }) => {
  await page.goto('/accounts/login/');
  await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
  await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/app/);
});

// After
import { test, expect } from './fixtures/test-fixtures';

// No beforeEach needed - use authenticatedPage fixture
test('my test', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/app/metrics/analytics/');
});
```

**Acceptance Criteria**:
- [ ] All applicable files use shared fixtures
- [ ] Login code not duplicated
- [ ] Test setup time reduced
- [ ] All tests pass

---

### Phase 4: Conditional Skip Elimination

#### 4.1 Refactor repo-selector.spec.ts
**Effort**: M | **Priority**: P2

**Problem**: 29 `test.skip()` calls based on whether team has repos.

**Solution**: Use test annotations and describe.skip for entire groups.

```typescript
// Before
test('clicking repo selector opens dropdown menu', async ({ page }) => {
  await page.goto('/app/metrics/analytics/');
  await waitForPageReady(page);

  const hasSelector = await hasRepoSelector(page);
  if (!hasSelector) {
    test.skip();
    return;
  }
  // ... test body
});

// After - Skip entire describe block if no repos
test.describe('Dropdown Interaction', () => {
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    await loginAs(page, 'admin');
    await page.goto('/app/metrics/analytics/');
    const hasSelector = await hasRepoSelector(page);
    await page.close();

    if (!hasSelector) {
      test.skip('Team does not have multiple repositories');
    }
  });

  test('clicking repo selector opens dropdown menu', async ({ authenticatedPage }) => {
    // Test body without skip check
  });
});
```

**Alternative**: Use test tags and run conditionally:
```bash
# Only run repo-selector tests when data exists
npx playwright test --grep @repo-selector --grep-invert @requires-multi-repo
```

**Acceptance Criteria**:
- [ ] No `test.skip()` inside test bodies
- [ ] Tests either run fully or skip as group
- [ ] Test results are deterministic

---

### Phase 5: Coverage Enhancement

#### 5.1 Add PR List Page Tests
**Effort**: M | **Priority**: P2

**Create** `tests/e2e/pr-list.spec.ts`:

**Tests to add**:
1. PR list page loads with table
2. PR table shows correct columns
3. Filtering by AI-assisted works
4. Sorting by date works
5. Pagination works
6. Date range filter updates list
7. Export CSV button works (if available)
8. Clicking PR opens details/GitHub

**Acceptance Criteria**:
- [ ] PR list page has E2E coverage
- [ ] Tests verify data filtering
- [ ] Tests verify table structure

#### 5.2 Add Integration Flow Tests
**Effort**: M | **Priority**: P3

**Enhance** `integrations.spec.ts`:

**Tests to add**:
1. GitHub connect button shows OAuth redirect
2. Jira connect button shows OAuth redirect
3. Slack connect button shows OAuth redirect
4. Disconnect confirmation modal works
5. Repo list loads after GitHub connected
6. Member list loads after GitHub connected

**Acceptance Criteria**:
- [ ] Integration pages tested beyond static structure
- [ ] OAuth initiation verified (without completing flow)
- [ ] Disconnect flow tested

---

### Phase 6: Verification

#### 6.1 Run Full Test Suite
**Effort**: S | **Priority**: P0

```bash
# Run all E2E tests
make e2e

# Run smoke tests specifically
make e2e-smoke

# Check for any remaining anti-patterns
grep -r "waitForTimeout" tests/e2e/
grep -r "test.skip()" tests/e2e/
```

**Acceptance Criteria**:
- [ ] All E2E tests pass
- [ ] Smoke tests complete in < 30s
- [ ] No hardcoded waits
- [ ] No inline test.skip() calls

#### 6.2 Update Documentation
**Effort**: S | **Priority**: P2

**Update** `CLAUDE.md` E2E section with:
- New helper module usage
- Fixture patterns
- Test tagging conventions

**Acceptance Criteria**:
- [ ] Documentation updated
- [ ] Examples provided for new patterns

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests break during refactor | Medium | High | Run tests after each file change |
| Helper import paths break | Low | Medium | Use consistent relative imports |
| Fixture changes break existing tests | Medium | Medium | Test fixtures in isolation first |
| CI time increases | Low | Low | Monitor test duration |

---

## Success Metrics

1. **Zero test failures** after refactoring
2. **100% fixture adoption** for auth-required tests
3. **Zero duplicate helpers** - single source of truth
4. **Smoke tests < 30s** execution time
5. **Zero hardcoded waits** in codebase
6. **~200+ lines removed** through deduplication

---

## Dependencies

- Node.js 18+
- Playwright installed
- Dev server running for E2E tests
- Test database with seeded data

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Critical Fixes | 2-3 hours | None |
| Phase 2: Helper Consolidation | 3-4 hours | Phase 1 |
| Phase 3: Fixture Migration | 4-5 hours | Phase 2 |
| Phase 4: Skip Elimination | 2-3 hours | Phase 3 |
| Phase 5: Coverage Enhancement | 3-4 hours | Phase 3 |
| Phase 6: Verification | 1-2 hours | All phases |

**Total Estimated Effort**: 15-21 hours (2-3 days)
