# Test Suite Refactoring & Improvement Plan

**Last Updated:** 2024-12-30
**Status:** Planning
**Methodology:** Strict TDD (Red-Green-Refactor)

---

## Executive Summary

This plan addresses the findings from the QA review to improve test coverage, reduce flakiness, and establish better testing patterns. All work follows strict TDD methodology.

### Goals
1. **Fill critical coverage gaps** (~200 new tests)
2. **Eliminate E2E flakiness** (468 hardcoded waits → 0)
3. **Improve test reliability** (deterministic factories, timezone fixes)
4. **Optimize test performance** (slow test markers, build vs create)

### Success Metrics
| Metric | Current | Target |
|--------|---------|--------|
| Test Count | 3,879 | 4,100+ |
| Coverage Gaps (critical) | 4 files | 0 files |
| E2E Hardcoded Waits | 468 | <50 |
| Timezone Warnings | 1,635 | 0 |
| Average Test Time | 52s | <60s (maintained) |

---

## Current State Analysis

### Critical Coverage Gaps (from QA Review)

| Priority | File | Lines | Tests Needed |
|----------|------|-------|--------------|
| P0 | `dashboard_service.py` | 1,788 | ~25 |
| P0 | `auth/views.py` | 596 | ~15 |
| P1 | `models/github.py` | 1,071 | ~20 |
| P1 | `views/github.py` | 354 | ~10 |
| P1 | `insight_service.py` | 280 | ~8 |
| P1 | `ai_patterns.py` | 203 | ~10 |

### Existing Issues

1. **E2E Flakiness** - 468 `waitForTimeout` calls
2. **Non-deterministic Factories** - `random` module usage
3. **Timezone Warnings** - 1,635 naive datetime issues
4. **Slow Tests** - Data generation tests taking 4+ seconds
5. **Shared State** - `setUpClass` usage in `test_roles.py`

---

## Implementation Phases

### Phase 1: Quick Wins & Foundation (Day 1-2)
Low-risk improvements that establish patterns for future work.

**Goals:**
- Fix technical debt (warnings, slow markers)
- Establish TDD patterns for coverage work
- Quick reliability improvements

### Phase 2: Critical Coverage - Dashboard Service (Day 3-5)
TDD implementation of tests for `dashboard_service.py`.

**Goals:**
- Cover key metrics functions
- Cover AI metrics functions
- Cover trend calculation functions

### Phase 3: E2E Reliability (Day 6-7)
Eliminate hardcoded waits in E2E tests.

**Goals:**
- Replace `waitForTimeout` with conditional waits
- Improve E2E test stability
- Document E2E best practices

### Phase 4: Coverage - Auth & Models (Day 8-10)
TDD implementation for auth views and model tests.

**Goals:**
- OAuth flow coverage
- Model method coverage
- Integration view coverage

### Phase 5: Factory & Performance Optimization (Day 11-12)
Improve test data patterns and performance.

**Goals:**
- Deterministic factories
- `build()` vs `create()` optimization
- Slow test optimization

---

## Phase 1: Quick Wins & Foundation

### Task 1.1: Fix Timezone Warnings [S]
**Effort:** 2h
**Risk:** Low

Fix naive datetime warnings in tests.

**Acceptance Criteria:**
- [ ] All tests use `timezone.make_aware()` or `timezone.now()`
- [ ] Zero `RuntimeWarning` about naive datetimes in test output
- [ ] Run `make test` with no timezone warnings

**Files to Modify:**
- `apps/metrics/tests/dashboard/test_deployment_metrics.py`
- `apps/metrics/tests/test_trends_views.py`
- Factory files using `datetime()` directly

### Task 1.2: Mark Slow Tests [S]
**Effort:** 1h
**Risk:** Low

Add `@pytest.mark.slow` to data generation tests.

**Acceptance Criteria:**
- [ ] All tests >2s marked with `@pytest.mark.slow`
- [ ] CI can skip slow tests with `-m "not slow"`
- [ ] Document slow test handling in CLAUDE.md

**Files to Modify:**
- `apps/metrics/tests/test_seeding/test_data_generator.py`

### Task 1.3: Fix Shared State in test_roles.py [S]
**Effort:** 30m
**Risk:** Low

Replace `setUpClass` with `setUp` for proper test isolation.

**Acceptance Criteria:**
- [ ] `test_roles.py` uses `setUp` instead of `setUpClass`
- [ ] Uses factories instead of manual object creation
- [ ] All tests still pass

### Task 1.4: Create Test Utilities Module [M]
**Effort:** 2h
**Risk:** Low

Create shared test utilities for common patterns.

**Acceptance Criteria:**
- [ ] Create `apps/utils/test_utils.py`
- [ ] Add timezone helpers
- [ ] Add common assertion helpers
- [ ] Document usage in CLAUDE.md

---

## Phase 2: Dashboard Service Coverage (TDD)

### Task 2.1: Key Metrics Tests [L]
**Effort:** 4h
**Risk:** Medium

TDD tests for `get_key_metrics()` and related functions.

**RED Phase - Write Failing Tests:**
```python
class TestGetKeyMetrics(TestCase):
    def test_returns_dict_with_required_keys(self): ...
    def test_calculates_prs_merged_count(self): ...
    def test_calculates_avg_cycle_time(self): ...
    def test_filters_by_date_range(self): ...
    def test_filters_by_team(self): ...
    def test_handles_empty_data(self): ...
    def test_calculates_trend_vs_previous_period(self): ...
```

**Acceptance Criteria:**
- [ ] Test file: `apps/metrics/tests/dashboard/test_key_metrics.py`
- [ ] At least 8 tests covering happy path and edge cases
- [ ] Tests written BEFORE implementation verification
- [ ] All tests pass with existing implementation

### Task 2.2: AI Metrics Tests [L]
**Effort:** 4h
**Risk:** Medium

TDD tests for AI adoption and detection functions.

**RED Phase - Write Failing Tests:**
```python
class TestGetAIAdoptionTrend(TestCase):
    def test_returns_monthly_adoption_data(self): ...
    def test_calculates_ai_percentage(self): ...
    def test_handles_no_ai_assisted_prs(self): ...
    def test_groups_by_tool(self): ...
```

**Acceptance Criteria:**
- [ ] Test file: `apps/metrics/tests/dashboard/test_ai_metrics.py`
- [ ] At least 10 tests for AI-related functions
- [ ] Cover tool breakdown, adoption trends, quality comparison
- [ ] Edge cases: no data, all AI, no AI

### Task 2.3: Team Metrics Tests [M]
**Effort:** 3h
**Risk:** Medium

TDD tests for team breakdown functions.

**Acceptance Criteria:**
- [ ] Test file: `apps/metrics/tests/dashboard/test_team_metrics.py`
- [ ] Tests for `get_team_breakdown()`, `get_copilot_by_member()`
- [ ] At least 6 tests per function

### Task 2.4: PR Metrics Tests [M]
**Effort:** 3h
**Risk:** Medium

TDD tests for PR cycle time and size functions.

**Acceptance Criteria:**
- [ ] Test file: `apps/metrics/tests/dashboard/test_pr_metrics.py`
- [ ] Tests for cycle time, PR size distribution, type breakdown
- [ ] At least 8 tests total

---

## Phase 3: E2E Reliability

### Task 3.1: Audit waitForTimeout Usage [S]
**Effort:** 1h
**Risk:** Low

Document all hardcoded waits and categorize by priority.

**Acceptance Criteria:**
- [ ] List all 468 `waitForTimeout` calls with file:line
- [ ] Categorize: Required (network), Avoidable (UI), Unnecessary
- [ ] Prioritize top 50 for replacement

### Task 3.2: Fix alpine-htmx-integration.spec.ts [M]
**Effort:** 2h
**Risk:** Medium

Replace hardcoded waits with conditional waits.

**Pattern to Apply:**
```typescript
// BEFORE
await page.waitForTimeout(2000);
await expect(element).toBeVisible();

// AFTER
await expect(element).toBeVisible({ timeout: 5000 });
```

**Acceptance Criteria:**
- [ ] All `waitForTimeout` replaced in this file
- [ ] Tests still pass reliably (run 3x)
- [ ] No increase in test duration

### Task 3.3: Fix analytics.spec.ts [L]
**Effort:** 3h
**Risk:** Medium

Replace hardcoded waits in largest E2E file.

**Acceptance Criteria:**
- [ ] All avoidable `waitForTimeout` replaced
- [ ] Tests pass reliably (run 3x)
- [ ] Document any required waits with comments

### Task 3.4: Create E2E Best Practices Guide [S]
**Effort:** 1h
**Risk:** Low

Document E2E testing patterns for the project.

**Acceptance Criteria:**
- [ ] Add E2E section to CLAUDE.md or separate guide
- [ ] Include wait patterns, selectors, reliability tips
- [ ] Include examples from fixed tests

---

## Phase 4: Auth & Model Coverage (TDD)

### Task 4.1: OAuth Flow Tests [L]
**Effort:** 6h
**Risk:** Medium-High

TDD tests for OAuth callback views.

**RED Phase - Write Failing Tests:**
```python
class TestGitHubOAuthCallback(TestCase):
    def test_successful_oauth_creates_connection(self): ...
    def test_invalid_state_returns_error(self): ...
    def test_oauth_error_displays_message(self): ...
    def test_existing_connection_updates_token(self): ...
```

**Acceptance Criteria:**
- [ ] Test file: `apps/auth/tests/test_oauth_views.py`
- [ ] Cover GitHub, Jira, Slack OAuth flows
- [ ] At least 5 tests per integration
- [ ] Mock external API calls properly

### Task 4.2: Model Method Tests [L]
**Effort:** 4h
**Risk:** Low

TDD tests for model computed properties and methods.

**Acceptance Criteria:**
- [ ] Test file: `apps/metrics/tests/models/test_pull_request_methods.py`
- [ ] Cover `effective_*` properties
- [ ] Cover computed fields (cycle_time, review_time)
- [ ] At least 15 tests total

### Task 4.3: Integration View Tests [M]
**Effort:** 3h
**Risk:** Medium

TDD tests for integration status and webhook views.

**Acceptance Criteria:**
- [ ] Test file: `apps/integrations/tests/test_views.py`
- [ ] Cover webhook signature verification
- [ ] Cover integration status endpoints
- [ ] At least 10 tests total

---

## Phase 5: Factory & Performance

### Task 5.1: Deterministic Factories [M]
**Effort:** 2h
**Risk:** Low

Replace `random` module with deterministic alternatives.

**Pattern to Apply:**
```python
# BEFORE
pr_created_at = factory.LazyFunction(
    lambda: timezone.now() - timedelta(days=random.randint(1, 30))
)

# AFTER
pr_created_at = factory.LazyAttribute(
    lambda o: timezone.now() - timedelta(days=(o.github_pr_id % 30) + 1)
)
```

**Acceptance Criteria:**
- [ ] No `random` module imports in factories
- [ ] Tests produce same results with `--randomly-seed=12345`
- [ ] Document determinism approach in factory docstrings

### Task 5.2: Optimize Factory Usage [M]
**Effort:** 2h
**Risk:** Low

Replace `create()` with `build()` where DB not needed.

**Acceptance Criteria:**
- [ ] Audit test files for unnecessary `create()` calls
- [ ] Replace with `build()` where appropriate
- [ ] No increase in test failures
- [ ] Document pattern in factories docstring

### Task 5.3: Slow Test Optimization [M]
**Effort:** 2h
**Risk:** Low

Optimize slowest tests without breaking functionality.

**Acceptance Criteria:**
- [ ] Top 10 slow tests reviewed for optimization opportunities
- [ ] Use `build()` instead of `create()` where possible
- [ ] Use smaller batch sizes in data generation tests
- [ ] No test takes >3s (down from 4.5s)

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | Medium | High | Run full suite after each change |
| E2E flakiness during transition | Medium | Medium | Run tests 3x to verify stability |
| Coverage gaps harder than expected | Low | Medium | Start with simplest functions |
| Performance regression | Low | Low | Monitor test duration |

### Mitigation Strategies

1. **Incremental Changes** - Small PRs, frequent commits
2. **TDD Discipline** - Write tests before verifying implementation
3. **CI Validation** - All changes must pass CI before merge
4. **Rollback Ready** - Each phase can be reverted independently

---

## Dependencies

### External Dependencies
- None (all internal test improvements)

### Internal Dependencies
- Phase 2 depends on Phase 1 (foundation work)
- Phase 3 independent (can run parallel)
- Phase 4 depends on Phase 1 (test utilities)
- Phase 5 depends on Phase 2 (factory patterns established)

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Zero timezone warnings in test output
- [ ] Slow tests marked and skippable
- [ ] `test_roles.py` uses proper isolation
- [ ] Test utilities module exists

### Phase 2 Complete When:
- [ ] `dashboard_service.py` has 25+ tests
- [ ] All key functions have test coverage
- [ ] Tests follow TDD patterns

### Phase 3 Complete When:
- [ ] <50 hardcoded waits remain (from 468)
- [ ] E2E tests pass 3/3 times consistently
- [ ] E2E best practices documented

### Phase 4 Complete When:
- [ ] OAuth flows have 15+ tests
- [ ] Model methods have 15+ tests
- [ ] Integration views have 10+ tests

### Phase 5 Complete When:
- [ ] No `random` imports in factories
- [ ] Tests deterministic with seed
- [ ] No test >3s duration

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | 2 days | None |
| Phase 2 | 3 days | Phase 1 |
| Phase 3 | 2 days | None (parallel) |
| Phase 4 | 3 days | Phase 1 |
| Phase 5 | 2 days | Phase 2 |

**Total Estimated Duration:** 10-12 days (with parallel execution)

---

## TDD Workflow Reminder

For ALL new tests in this plan:

### 🔴 RED Phase
1. Write the test FIRST
2. Run it - it MUST fail
3. Verify failure is for the right reason

### 🟢 GREEN Phase
1. Write MINIMUM code to pass
2. Run test - it MUST pass
3. No extra features or refactoring

### 🔵 REFACTOR Phase
1. Clean up implementation
2. Improve naming, remove duplication
3. Run tests after EACH change

**Never skip a phase. Never write implementation before tests.**
