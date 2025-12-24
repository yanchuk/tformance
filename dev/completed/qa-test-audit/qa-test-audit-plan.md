# QA Test Suite Audit Plan

**Last Updated:** 2025-12-23
**Prepared By:** Senior QA Specialist Review
**Scope:** Unit Tests, E2E Tests for metrics, analytics, integrations apps

---

## Executive Summary

This audit reviews the test suite of the tformance AI Impact Analytics Platform to identify:
1. **Critical missing test coverage** - User flows and features without adequate tests
2. **Obsolete/redundant tests** - Tests that can be removed or consolidated
3. **Conditional/environment-specific tests** - Tests that should run selectively

### Current Test Inventory

| Category | Count | Lines of Code |
|----------|-------|---------------|
| Unit Tests (Total) | 2,231 | ~37,000 |
| - metrics app | 1,170 | - |
| - integrations app | 956 | - |
| - web app | ~100 | - |
| E2E Tests | 15 files | 4,285 |

---

## Current State Analysis

### Strengths

1. **Excellent metrics app coverage** - 1,170 tests covering services, views, models
2. **Strong integrations coverage** - 956 tests for GitHub, Jira, Slack, Copilot
3. **Good E2E foundation** - Tests for auth, dashboard, analytics, surveys
4. **TDD workflow enforced** - Factory-based testing patterns well established

### Critical Gaps Identified

#### Gap 1: Incomplete E2E User Flow Coverage

**User flows from PRD not fully tested:**

| User Flow | E2E Coverage | Gap |
|-----------|--------------|-----|
| Onboarding (Step 1-6) | Partial | No complete flow test |
| GitHub OAuth + Org Selection | Missing | Only basic integration page test |
| Repository Selection | Missing | No repo toggle E2E tests |
| Jira OAuth + Project Selection | Missing | No Jira flow tests |
| Slack OAuth + Bot Config | Missing | No Slack setup tests |
| PR Survey Flow (Author) | Partial | surveys.spec.ts covers some |
| PR Survey Flow (Reviewer) | Partial | Missing reveal/leaderboard |
| AI Detective Game | Missing | No leaderboard E2E |
| CTO Dashboard Navigation | Good | analytics.spec.ts covers this |
| Developer Self-Service | Missing | No team member dashboard test |

#### Gap 2: Weak E2E Integration Tests

File: `tests/e2e/integrations.spec.ts` (90 lines)
- Tests use `expect(true).toBeTruthy()` - effectively no-ops
- Tests check `typeof isVisible === 'boolean'` - always passes
- No actual integration flow testing (connect, configure, disconnect)

#### Gap 3: Missing Error State Tests

**Not covered in E2E:**
- OAuth failure handling
- API rate limit scenarios
- Network error recovery
- Invalid data validation

#### Gap 4: Missing Accessibility Tests

File: `tests/e2e/accessibility.spec.ts` exists but needs review for completeness.

### Potential Obsolete Tests

#### Candidate 1: Duplicate Dashboard Tests

Both `dashboard.spec.ts` and `analytics.spec.ts` test similar flows:
- Key metrics cards loading
- Date filter changes
- Navigation between pages

**Recommendation:** Consolidate overlapping tests

#### Candidate 2: Seeding Tests (Conditional)

Files in `apps/metrics/tests/test_seeding/`:
- `test_github_fetcher.py` - Requires network, should be marked integration
- `test_real_project_seeding.py` - Requires GitHub tokens

**Recommendation:** Mark as `@pytest.mark.integration` or `@pytest.mark.slow`

---

## Proposed Future State

### Test Pyramid Target

```
            /\
           /  \      E2E (60 tests)
          /----\     - Critical user flows
         /      \    - Cross-browser validation
        /--------\
       /          \  Integration (200 tests)
      /------------\ - API endpoints
     /              \- External service mocks
    /----------------\
   /                  \ Unit (2,000 tests)
  /--------------------\ - Business logic
 /                      \- Model validation
/________________________\
```

### Coverage Targets

| Area | Current | Target |
|------|---------|--------|
| metrics unit | 90% | 95% |
| integrations unit | 85% | 90% |
| E2E critical flows | 40% | 90% |
| E2E error handling | 10% | 70% |

---

## Implementation Phases

### Phase 1: Fix Critical E2E Gaps (Priority: HIGH)

**Effort:** L (2-3 days)

1. Rewrite `integrations.spec.ts` with real assertions
2. Add complete onboarding flow test
3. Add GitHub repo selection E2E test
4. Add PR survey complete flow test
5. Add AI Detective leaderboard test

### Phase 2: Add Error State E2E Tests (Priority: HIGH)

**Effort:** M (1-2 days)

1. OAuth error handling tests
2. API failure recovery tests
3. Form validation error tests
4. Permission denied scenarios

### Phase 3: Cleanup and Consolidation (Priority: MEDIUM)

**Effort:** S (1 day)

1. Consolidate dashboard/analytics E2E overlap
2. Mark slow tests with pytest markers
3. Add `@pytest.mark.integration` to network-dependent tests
4. Remove truly obsolete tests (if any found)

### Phase 4: Missing Unit Test Coverage (Priority: MEDIUM)

**Effort:** M (1-2 days)

1. Add chart_formatters.py tests
2. Add oauth_utils.py tests
3. Increase edge case coverage
4. Add security boundary tests

---

## Detailed Task Breakdown

### Phase 1 Tasks

#### P1.1: Rewrite integrations.spec.ts
**Effort:** M | **Priority:** Critical

Current state: 90 lines with fake assertions
Target state: 250+ lines with real user flow tests

Tests to add:
- [ ] GitHub integration status card shows correct state
- [ ] Clicking "Connect GitHub" navigates to OAuth
- [ ] Repositories page shows synced repos
- [ ] Repo toggle enables/disables sync
- [ ] Members page shows imported users
- [ ] Disconnect confirmation flow
- [ ] Jira integration connect flow
- [ ] Slack integration connect flow

#### P1.2: Add onboarding flow E2E test
**Effort:** L | **Priority:** Critical

Create `onboarding-flow.spec.ts`:
- [ ] New user signup completes
- [ ] GitHub OAuth redirect works
- [ ] Org selection shows available orgs
- [ ] Repo selection saves correctly
- [ ] Skip Jira flow works
- [ ] Skip Slack flow works
- [ ] Dashboard loads after onboarding

#### P1.3: Add PR survey complete flow test
**Effort:** M | **Priority:** High

Extend `surveys.spec.ts`:
- [ ] Author survey shows after PR merge
- [ ] Reviewer survey shows with AI guess option
- [ ] Survey responses save correctly
- [ ] Reveal shows correct answer
- [ ] Leaderboard updates after response

#### P1.4: Add AI Detective tests
**Effort:** S | **Priority:** High

Create or extend leaderboard tests:
- [ ] Weekly leaderboard displays
- [ ] Correct/incorrect guess counts
- [ ] Ranking calculation
- [ ] Time period filtering

### Phase 2 Tasks

#### P2.1: OAuth error handling E2E
**Effort:** S | **Priority:** High

- [ ] GitHub OAuth denied shows error message
- [ ] GitHub OAuth with no orgs shows guidance
- [ ] Jira OAuth failure shows skip option
- [ ] Slack OAuth failure shows skip option

#### P2.2: API error recovery E2E
**Effort:** M | **Priority:** Medium

- [ ] Network timeout shows retry option
- [ ] Rate limit shows wait message
- [ ] Server error shows support contact

### Phase 3 Tasks

#### P3.1: Consolidate E2E overlaps
**Effort:** S | **Priority:** Medium

- [ ] Identify duplicate tests in dashboard.spec.ts and analytics.spec.ts
- [ ] Remove duplicates, keep most comprehensive version
- [ ] Update test documentation

#### P3.2: Add pytest markers for slow tests
**Effort:** S | **Priority:** Medium

- [ ] Add `@pytest.mark.slow` to seeding tests
- [ ] Add `@pytest.mark.integration` to network tests
- [ ] Update pytest.ini with marker definitions
- [ ] Update CI to run markers separately

### Phase 4 Tasks

#### P4.1: Missing service test coverage
**Effort:** M | **Priority:** Medium

- [ ] chart_formatters.py - 0 tests currently
- [ ] oauth_utils.py - 0 tests currently
- [ ] sync_notifications.py - limited tests

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| E2E tests flaky in CI | Medium | High | Add retry logic, explicit waits |
| Test data dependencies | Medium | Medium | Use factories, isolated test DB |
| OAuth tests hard to automate | High | Medium | Mock OAuth responses |
| Time to implement all phases | Medium | Low | Prioritize Phase 1 first |

---

## Success Metrics

1. **E2E test pass rate:** >95% on all browsers
2. **Critical flow coverage:** 100% of PRD user stories
3. **Test execution time:** <5 minutes for unit tests, <10 minutes for E2E
4. **No false positives:** 0 tests that "always pass"
5. **Maintainability:** All tests have clear descriptions

---

## Required Resources

- 1 QA Engineer: 5-7 days total
- Test environment with demo data
- CI pipeline access for multi-browser testing
- OAuth test accounts (or mock infrastructure)

---

## Appendix: Test Files Inventory

### E2E Tests (tests/e2e/)

| File | Lines | Status | Notes |
|------|-------|--------|-------|
| accessibility.spec.ts | 226 | Review | Check completeness |
| analytics.spec.ts | 573 | Good | Recently updated |
| auth.spec.ts | 322 | Good | Comprehensive |
| copilot.spec.ts | 259 | Review | Check real assertions |
| dashboard.spec.ts | 396 | Review | Potential overlap with analytics |
| feedback.spec.ts | 287 | Good | - |
| insights.spec.ts | 242 | Good | - |
| integrations.spec.ts | 90 | **REWRITE** | Fake assertions |
| interactive.spec.ts | 578 | Review | Large, check scope |
| onboarding.spec.ts | 277 | Review | Check flow completeness |
| profile.spec.ts | 191 | Good | - |
| smoke.spec.ts | 60 | Good | Quick checks |
| subscription.spec.ts | 191 | Good | - |
| surveys.spec.ts | 272 | Extend | Add complete flow |
| teams.spec.ts | 321 | Good | - |

### Unit Tests Needing Attention

| File | Issue |
|------|-------|
| test_seeding/*.py | Mark as slow/integration |
| test_real_project_seeding.py | Requires network |
| test_github_authenticated_fetcher.py | Requires tokens |
