# MVP E2E Testing - Task Checklist

**Last Updated: 2025-12-18**
**Status: PLANNING**

## Phase 1: Test Infrastructure (S - 2-3h)

### 1.1 Create Test Fixtures Directory
- [ ] Create `tests/e2e/fixtures/` directory
- [ ] Create `tests/e2e/fixtures/seed-helpers.ts`
- [ ] Create `tests/e2e/fixtures/test-users.ts`
- [ ] Create `tests/e2e/fixtures/test-fixtures.ts`

### 1.2 Implement Seed Helpers
- [ ] Add function to check if seed data exists
- [ ] Add function to run seed command from tests
- [ ] Add function to reset/clear seed data
- [ ] Add constants for expected seed data counts
- [ ] Export seed data validation utilities

### 1.3 Implement Test User Management
- [ ] Define test user credentials object
- [ ] Create `loginAs(page, user)` helper function
- [ ] Create `logout(page)` helper function
- [ ] Add role-based user selection

### 1.4 Update Playwright Configuration
- [ ] Add Firefox browser project
- [ ] Configure global setup for seed validation
- [ ] Add test tags configuration
- [ ] Update timeout settings for slow tests
- [ ] Add retry configuration for flaky tests

### 1.5 Create Custom Test Fixtures
- [ ] Create `authenticatedPage` fixture
- [ ] Create `dashboardPage` fixture
- [ ] Create `adminPage` fixture (for CTO dashboard)
- [ ] Export extended test function

---

## Phase 2: Expand Existing Tests (M - 4-6h)

### 2.1 Expand Smoke Tests
- [ ] Add test: authenticated user redirects from landing to app
- [ ] Add test: API health endpoint details
- [ ] Add test: static CSS loads without errors
- [ ] Add test: static JS loads without errors
- [ ] Add test: favicon loads
- [ ] Add test: robots.txt exists

### 2.2 Expand Auth Tests
- [ ] Add test: signup flow completes
- [ ] Add test: invalid email format shows error
- [ ] Add test: weak password shows error
- [ ] Add test: session persists across page refresh
- [ ] Add test: concurrent sessions allowed
- [ ] Add test: remember me functionality (if exists)
- [ ] Add test: password reset link works
- [ ] Add test: expired session redirects to login

### 2.3 Expand Dashboard Tests
- [ ] Add test: chart hover shows tooltip
- [ ] Add test: table header click sorts data
- [ ] Add test: pagination next/prev works
- [ ] Add test: empty state shows when no data
- [ ] Add test: date range "Custom" opens picker
- [ ] Add test: custom date range applies
- [ ] Add test: filter state persists on navigation
- [ ] Add test: multiple rapid filter clicks don't break UI

### 2.4 Expand Integration Tests
- [ ] Add test: GitHub card shows org name when connected
- [ ] Add test: Jira card shows site URL when connected
- [ ] Add test: Slack card shows workspace when connected
- [ ] Add test: Copilot section visible when GitHub connected
- [ ] Add test: connect buttons open OAuth (verify URL)
- [ ] Add test: disconnect shows confirmation modal

---

## Phase 3: New Integration Tests (L - 6-8h)

### 3.1 Create GitHub Integration Tests (`integrations-github.spec.ts`)
- [ ] Test: members page loads
- [ ] Test: members list displays team members
- [ ] Test: member toggle switch works
- [ ] Test: member sync button triggers refresh
- [ ] Test: sync shows loading state
- [ ] Test: sync completion shows success message
- [ ] Test: repos page loads
- [ ] Test: repos list displays repositories
- [ ] Test: repo toggle enables/disables tracking
- [ ] Test: repo sync button works
- [ ] Test: webhook status displays (if applicable)
- [ ] Test: disconnect modal appears
- [ ] Test: disconnect removes integration

### 3.2 Create Jira Integration Tests (`integrations-jira.spec.ts`)
- [ ] Test: projects page loads
- [ ] Test: projects list displays Jira projects
- [ ] Test: project toggle enables/disables tracking
- [ ] Test: site selection dropdown works
- [ ] Test: user matching page displays
- [ ] Test: disconnect removes integration

### 3.3 Create Slack Integration Tests (`integrations-slack.spec.ts`)
- [ ] Test: settings page loads
- [ ] Test: survey channel config displays
- [ ] Test: leaderboard settings display
- [ ] Test: disconnect removes integration

---

## Phase 4: Survey System Tests (M - 4-6h)

### 4.1 Create Survey Tests (`surveys.spec.ts`)
- [ ] Test: survey landing page routes correctly
- [ ] Test: author survey form displays
- [ ] Test: author "Yes" (AI-assisted) submits
- [ ] Test: author "No" (not AI-assisted) submits
- [ ] Test: author already responded shows message
- [ ] Test: reviewer survey form displays
- [ ] Test: reviewer quality rating buttons work
- [ ] Test: reviewer AI guess buttons work
- [ ] Test: reviewer form requires both inputs
- [ ] Test: reviewer submit succeeds
- [ ] Test: reveal page shows when both responded
- [ ] Test: reveal shows correct/incorrect guess
- [ ] Test: reveal shows accuracy stats
- [ ] Test: invalid token shows error page
- [ ] Test: expired token shows expiration message
- [ ] Test: completion page displays thank you

---

## Phase 5: Interactive Elements Tests (L - 6-8h)

### 5.1 Create Interactive Tests (`interactive.spec.ts`)

#### Navigation Clicks
- [ ] Test: logo navigates to app home
- [ ] Test: Dashboard nav link works
- [ ] Test: Integrations nav link works
- [ ] Test: Settings dropdown opens
- [ ] Test: Profile link in dropdown works
- [ ] Test: Logout in dropdown works
- [ ] Test: breadcrumb links navigate correctly

#### Dashboard Buttons
- [ ] Test: 7d filter button activates
- [ ] Test: 30d filter button activates
- [ ] Test: 90d filter button activates
- [ ] Test: Custom filter button opens picker
- [ ] Test: View Analytics button (app home) navigates
- [ ] Test: Manage Integrations button navigates
- [ ] Test: chart section collapse/expand (if exists)

#### Integration Buttons
- [ ] Test: Connect GitHub button visible
- [ ] Test: Connect Jira button visible
- [ ] Test: Connect Slack button visible
- [ ] Test: Sync Now buttons clickable
- [ ] Test: member toggle switches work
- [ ] Test: repo toggle switches work
- [ ] Test: project toggle switches work

#### Forms
- [ ] Test: login form tab order correct
- [ ] Test: login form enter key submits
- [ ] Test: team settings form saves
- [ ] Test: profile form saves

#### Modals
- [ ] Test: disconnect confirmation opens
- [ ] Test: disconnect cancel closes modal
- [ ] Test: delete team confirmation opens
- [ ] Test: modal escape key closes

---

## Phase 6: Copilot & Team Management (M - 4-6h)

### 6.1 Create Copilot Tests (`copilot.spec.ts`)
- [ ] Test: Copilot section visible on CTO dashboard
- [ ] Test: Copilot metrics cards render (4 cards)
- [ ] Test: Suggestions count displays number
- [ ] Test: Acceptance rate displays percentage
- [ ] Test: Active users displays count
- [ ] Test: Cost estimate displays currency
- [ ] Test: Copilot trend chart renders
- [ ] Test: Copilot members table loads
- [ ] Test: Copilot sync button works (integrations page)
- [ ] Test: Copilot disabled shows enable message

### 6.2 Create Team Management Tests (`team-management.spec.ts`)
- [ ] Test: team settings page loads
- [ ] Test: team name field editable
- [ ] Test: team name save works
- [ ] Test: member list displays all members
- [ ] Test: member role dropdown works
- [ ] Test: member role change saves
- [ ] Test: remove member button shows confirmation
- [ ] Test: remove member confirmed removes
- [ ] Test: invite member button works
- [ ] Test: invite form validates email
- [ ] Test: invite sent shows success message
- [ ] Test: pending invites list displays
- [ ] Test: cancel invite works
- [ ] Test: delete team shows confirmation
- [ ] Test: delete team disabled for last admin

---

## Phase 7: Data Validation Tests (M - 4-6h)

### 7.1 Create Data-Driven Tests (`data-driven.spec.ts`)
- [ ] Test: PR count card shows valid number
- [ ] Test: cycle time card shows hours value
- [ ] Test: quality rating card shows 1-3 scale
- [ ] Test: AI-assisted % card shows percentage
- [ ] Test: team breakdown table has expected rows
- [ ] Test: leaderboard has ranked members
- [ ] Test: recent PRs table shows PR titles
- [ ] Test: filter change updates displayed values
- [ ] Test: 7d filter shows fewer PRs than 30d
- [ ] Test: chart data points exist
- [ ] Test: empty date range shows no data message

---

## Phase 8: CI Integration & Documentation (S - 2-3h)

### 8.1 CI Pipeline Updates
- [ ] Add e2e tests to GitHub Actions workflow
- [ ] Configure test parallelization
- [ ] Add test result artifacts (screenshots, traces)
- [ ] Add test report generation
- [ ] Configure retry for flaky tests

### 8.2 Documentation
- [ ] Update CLAUDE.md with new test commands
- [ ] Document test fixtures usage
- [ ] Add troubleshooting guide for common failures
- [ ] Document how to add new tests

---

## Test Commands Reference

```bash
# Run all e2e tests
make e2e

# Run specific test file
make e2e ARGS='surveys.spec.ts'

# Run tests with specific tag
make e2e ARGS='--grep @smoke'

# Run in headed mode (see browser)
make e2e-headed

# Run in UI mode (interactive)
make e2e-ui

# View test report
make e2e-report

# Run specific test
npx playwright test -g "survey author form"
```

---

## Definition of Done

### Per Phase
- [ ] All tests in phase are implemented
- [ ] All tests pass locally
- [ ] Tests pass in CI (Chrome + Firefox)
- [ ] No flaky tests (retry rate < 2%)
- [ ] Code reviewed (if applicable)

### Overall
- [ ] 200+ e2e tests total
- [ ] All MVP features covered
- [ ] Test execution time < 5 minutes
- [ ] Documentation updated
- [ ] CI pipeline configured
