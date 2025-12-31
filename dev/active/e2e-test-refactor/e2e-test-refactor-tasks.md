# E2E Test Refactor - Task Checklist

**Last Updated**: 2025-12-31
**Branch**: `refactor/e2e-tests`
**Status**: Ready to Start

---

## Phase 1: Critical Fixes ⏳

### 1.1 Fix Smoke Test Asset Check [S]
- [ ] Edit `smoke.spec.ts` line 56
- [ ] Exclude external analytics scripts (posthog, analytics)
- [ ] Only check same-origin assets
- [ ] Run: `npx playwright test smoke.spec.ts`
- [ ] Verify: All 6 smoke tests pass

### 1.2 Enhance Smoke Tests [M]
- [ ] Add test: Login with valid credentials succeeds
- [ ] Add test: Dashboard loads after authentication
- [ ] Add test: No console errors on dashboard page
- [ ] Add test: Sidebar navigation to Analytics works
- [ ] Run: `make e2e-smoke`
- [ ] Verify: Total time < 30 seconds

### 1.3 Remove Hardcoded Waits [S]
- [ ] Fix `repo-selector.spec.ts:30` - Replace `waitForTimeout(200)`
- [ ] Fix `repo-selector.spec.ts:540` - Replace `waitForTimeout(500)`
- [ ] Run: `grep -r "waitForTimeout" tests/e2e/`
- [ ] Verify: Returns empty (no hardcoded waits)

**Phase 1 Checkpoint**:
- [ ] All smoke tests pass
- [ ] No hardcoded waits remain
- [ ] `make e2e-smoke` completes successfully

---

## Phase 2: Helper Consolidation ⏳

### 2.1 Create Helpers Directory Structure [S]
- [ ] Create `tests/e2e/helpers/` directory
- [ ] Create `tests/e2e/helpers/htmx.ts`
- [ ] Create `tests/e2e/helpers/alpine.ts`
- [ ] Create `tests/e2e/helpers/charts.ts`
- [ ] Create `tests/e2e/helpers/index.ts`

### 2.2 Implement HTMX Helpers [S]
- [ ] Add `waitForHtmxComplete(page, timeout)`
- [ ] Add `waitForHtmxSwap(page, selector, timeout)`
- [ ] Add JSDoc comments
- [ ] Export from index.ts

### 2.3 Implement Alpine Helpers [S]
- [ ] Add `waitForAlpine(page, timeout)`
- [ ] Add `waitForAlpineStore(page, storeName, timeout)`
- [ ] Add JSDoc comments
- [ ] Export from index.ts

### 2.4 Implement Chart Helpers [S]
- [ ] Add `waitForChart(page, chartId, timeout)`
- [ ] Add `chartHasData(page, chartId)`
- [ ] Add JSDoc comments
- [ ] Export from index.ts

### 2.5 Migrate Test Files to Use Shared Helpers [L]
Files to update (remove local helper definitions, import from helpers):
- [ ] `analytics.spec.ts`
- [ ] `alpine-htmx-integration.spec.ts`
- [ ] `copilot.spec.ts`
- [ ] `dashboard-data-consistency.spec.ts`
- [ ] `dashboard.spec.ts`
- [ ] `feedback.spec.ts`
- [ ] `htmx-navigation.spec.ts`
- [ ] `insights.spec.ts`
- [ ] `interactive.spec.ts`
- [ ] `leaderboard.spec.ts`
- [ ] `metric-toggle.spec.ts`
- [ ] `repo-selector.spec.ts`
- [ ] `trends-charts.spec.ts`
- [ ] Run: `npx playwright test` after each file
- [ ] Verify: All tests still pass

**Phase 2 Checkpoint**:
- [ ] All helper functions in shared module
- [ ] No duplicate function definitions
- [ ] All tests pass
- [ ] Run: `make e2e`

---

## Phase 3: Fixture Migration ⏳

### 3.1 Extend Test Fixtures [S]
- [ ] Add `analyticsPage` fixture to `test-fixtures.ts`
- [ ] Add `prListPage` fixture to `test-fixtures.ts`
- [ ] Add `trendsPage` fixture to `test-fixtures.ts`
- [ ] Update TypeScript types for new fixtures

### 3.2 Migrate Files to Use Fixtures [L]
Files to update (replace beforeEach login with fixture):
- [ ] `analytics.spec.ts` → use `authenticatedPage`
- [ ] `alpine-htmx-integration.spec.ts` → use `authenticatedPage`
- [ ] `copilot.spec.ts` → use `dashboardPage`
- [ ] `dashboard-data-consistency.spec.ts` → use `dashboardPage`
- [ ] `dashboard.spec.ts` → use `dashboardPage`
- [ ] `feedback.spec.ts` → use `authenticatedPage`
- [ ] `htmx-navigation.spec.ts` → use `authenticatedPage`
- [ ] `insights.spec.ts` → use `dashboardPage`
- [ ] `integrations.spec.ts` → use `integrationsPage`
- [ ] `interactive.spec.ts` → use `authenticatedPage`
- [ ] `leaderboard.spec.ts` → use `dashboardPage`
- [ ] `metric-toggle.spec.ts` → use `analyticsPage`
- [ ] `repo-selector.spec.ts` → use `analyticsPage`
- [ ] `trends-charts.spec.ts` → use `trendsPage`
- [ ] Run: `npx playwright test` after each file
- [ ] Verify: All tests pass

**Phase 3 Checkpoint**:
- [ ] All applicable files use fixtures
- [ ] Login code not duplicated (check with grep)
- [ ] `make e2e` passes

---

## Phase 4: Conditional Skip Elimination ⏳

### 4.1 Refactor repo-selector.spec.ts [M]
- [ ] Move `hasRepoSelector` check to `beforeAll`
- [ ] Use `test.describe.configure({ mode: 'serial' })` if needed
- [ ] Skip entire describe blocks instead of individual tests
- [ ] Remove all inline `if (!hasSelector) { test.skip(); return; }`
- [ ] Run: `npx playwright test repo-selector.spec.ts`
- [ ] Verify: Tests either all run or all skip (deterministic)

### 4.2 Review Other Conditional Skips [S]
- [ ] Check `surveys.spec.ts` skip patterns
- [ ] Check `dashboard-data-consistency.spec.ts` skip patterns
- [ ] Check `accessibility.spec.ts` skip patterns
- [ ] Document any remaining necessary skips

**Phase 4 Checkpoint**:
- [ ] No inline `test.skip()` calls
- [ ] Run: `grep -r "test.skip()" tests/e2e/ | wc -l`
- [ ] Target: < 10 skips (only necessary ones)

---

## Phase 5: Coverage Enhancement ⏳

### 5.1 Create PR List Page Tests [M]
- [ ] Create `tests/e2e/pr-list.spec.ts`
- [ ] Add test: PR list page loads with table
- [ ] Add test: Table shows correct columns (Title, Author, Status, etc.)
- [ ] Add test: Filtering by AI-assisted works
- [ ] Add test: Date range filter updates list
- [ ] Add test: Clicking PR row navigates correctly
- [ ] Add test: No console errors on PR list page
- [ ] Run: `npx playwright test pr-list.spec.ts`

### 5.2 Enhance Integration Flow Tests [M]
- [ ] Add test: GitHub OAuth redirect initiates correctly
- [ ] Add test: Jira OAuth redirect initiates correctly
- [ ] Add test: Disconnect confirmation modal appears
- [ ] Add test: Repo list loads after GitHub status check
- [ ] Run: `npx playwright test integrations.spec.ts`

**Phase 5 Checkpoint**:
- [ ] PR list page has coverage
- [ ] Integration flows tested beyond static UI
- [ ] `make e2e` passes

---

## Phase 6: Verification ⏳

### 6.1 Full Test Suite Run [S]
- [ ] Run: `make e2e`
- [ ] All tests pass
- [ ] Note total execution time

### 6.2 Anti-Pattern Check [S]
- [ ] Run: `grep -r "waitForTimeout" tests/e2e/` → empty
- [ ] Run: `grep -r "admin@example.com" tests/e2e/ | wc -l` → minimal
- [ ] Run: `grep -l "from.*fixtures" tests/e2e/*.spec.ts | wc -l` → 20+

### 6.3 Update Documentation [S]
- [ ] Update CLAUDE.md E2E section
- [ ] Document helper usage patterns
- [ ] Document fixture patterns
- [ ] Document test tagging conventions

**Phase 6 Checkpoint**:
- [ ] All E2E tests pass
- [ ] Documentation updated
- [ ] Ready for commit

---

## Phase 7: Worktree Integration ⏳

### 7.1 Wait for Worktree Merges
Active worktrees that may affect tests:
- [ ] `feature/dashboard-insights` - Has velocity comparison tests
- [ ] `code-structure-cleanup` - May affect imports
- [ ] `feature/personal-notes` - New feature tests

### 7.2 Post-Merge Integration
After each worktree merges to main:
- [ ] Pull latest main
- [ ] Run full test suite: `make test && make e2e`
- [ ] Apply E2E patterns to any new test files
- [ ] Remove orphaned tests (if feature tests exist without implementation)

### 7.3 Resolve velocity_comparison Test Failures
Currently 8 tests fail because `get_velocity_comparison` is in worktree:
- [ ] Wait for `feature/dashboard-insights` to merge
- [ ] OR: Temporarily skip with `@pytest.mark.skip(reason="WIP: dashboard-insights")`
- [ ] After merge: Remove skip markers

**Phase 7 Checkpoint**:
- [ ] All worktree changes merged
- [ ] No orphaned tests
- [ ] Full test suite passes: `make test && make e2e`

---

## Final Checklist

- [ ] All E2E tests pass: `make e2e`
- [ ] All unit tests pass: `make test`
- [ ] No hardcoded waits
- [ ] No duplicate helper functions
- [ ] All files use shared fixtures (where applicable)
- [ ] Documentation updated
- [ ] Commit changes
- [ ] Create PR from `refactor/e2e-tests`

---

## Quick Reference

```bash
# Run E2E tests
make e2e                 # All tests (Chromium)
make e2e-smoke           # Smoke tests only
make e2e-ui              # Interactive UI mode

# Run specific tests
npx playwright test smoke.spec.ts
npx playwright test --grep @dashboard

# Check for anti-patterns
grep -r "waitForTimeout" tests/e2e/
grep -r "test.skip()" tests/e2e/
grep -l "from.*fixtures" tests/e2e/*.spec.ts

# Unit tests
make test                # All tests
make test-fresh          # With fresh DB
```
