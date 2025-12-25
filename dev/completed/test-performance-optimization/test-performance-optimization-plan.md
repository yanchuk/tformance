# Test Performance Optimization Plan

**Last Updated:** 2025-12-25

## Executive Summary

Optimize the test suite to reduce execution time while maintaining test coverage and reliability. Current analysis identified ~40-50 seconds of unnecessary delays and significant factory overhead that can be eliminated through targeted fixes.

### Key Metrics
- **Current Tests:** 3,051 tests across 161 files
- **Current Runtime:** ~94s parallel, ~180s+ serial
- **Target Improvement:** 30-40% reduction in test runtime
- **Estimated Savings:** 30-50 seconds per run

## Current State Analysis

### Performance Bottlenecks Identified

| Issue | Location | Impact | Root Cause |
|-------|----------|--------|------------|
| Real async sleeps in retry tests | `test_github_graphql.py` | ~30s | `asyncio.sleep` not mocked |
| LLM task test delays | `test_llm_tasks.py` | ~15s | Import timing + mock setup |
| Factory SubFactory cascades | All factories | ~15-20% overhead | Unnecessary nested object creation |
| Missing setUpTestData | 98% of test classes | ~20% overhead | setUp runs per-method instead of per-class |
| Seeding tests with real data | `test_seeding/` | ~10s | Full pipeline execution |

### Test Suite Composition

```
apps/metrics/tests/          - 60+ test files, ~1500 tests
apps/integrations/tests/     - 40+ test files, ~800 tests
apps/web/tests/              - 15 test files, ~300 tests
apps/teams/tests/            - 10 test files, ~150 tests
Other apps                   - ~300 tests
```

## Proposed Future State

### Target Architecture

1. **All async operations properly mocked** - No real network waits or sleeps
2. **Efficient fixture patterns** - `setUpTestData` for class-level data
3. **Smart factory usage** - Explicit object passing to avoid cascades
4. **Slow test isolation** - Marked and optionally excluded from quick runs
5. **Shared fixtures in conftest.py** - Reusable across test modules

### Expected Outcomes

- Test suite runs in ~60s parallel (down from ~94s)
- Developer feedback loop improved by 30+ seconds
- CI/CD pipeline ~2-3 minutes faster per run
- No reduction in test coverage or reliability

## Implementation Phases

### Phase 1: Quick Wins (Immediate)
**Effort:** Small | **Impact:** High | **Risk:** Low

Focus on fixes that require minimal code changes but provide immediate benefits.

### Phase 2: Factory Optimization (Short-term)
**Effort:** Medium | **Impact:** Medium | **Risk:** Low

Reduce database operations through smarter factory patterns.

### Phase 3: Test Class Refactoring (Medium-term)
**Effort:** Large | **Impact:** High | **Risk:** Medium

Convert high-value test classes to use class-level fixtures.

### Phase 4: Infrastructure Improvements (Ongoing)
**Effort:** Medium | **Impact:** Medium | **Risk:** Low

Add tooling and patterns to prevent future regressions.

## Detailed Implementation

### Phase 1: Quick Wins

#### 1.1 Mock asyncio.sleep in GraphQL Retry Tests
**File:** `apps/integrations/tests/test_github_graphql.py`
**Effort:** S

Add mock decorator to all retry-related tests:
```python
@patch("apps.integrations.services.github_graphql.asyncio.sleep", new_callable=AsyncMock)
def test_fetch_prs_bulk_fails_after_max_retries(self, mock_sleep, ...):
```

Affected test classes:
- `TestRetryOnTimeout` (6 tests)
- `TestTimeoutHandling` (3 tests)
- `TestFetchPRsUpdatedSince` (1 test)

#### 1.2 Mark Slow Seeding Tests
**Files:** `apps/metrics/tests/test_seeding/*.py`
**Effort:** S

Add `@pytest.mark.slow` to all seeding tests:
```python
@pytest.mark.slow
class TestScenarioDataGenerator(TestCase):
```

Update Makefile with quick test target:
```makefile
test-quick:
    pytest -m "not slow" --reuse-db -n auto
```

#### 1.3 Fix LLM Task Import Patterns
**File:** `apps/metrics/tests/test_llm_tasks.py`
**Effort:** S

Move task imports to module level and ensure proper mock targets.

### Phase 2: Factory Optimization

#### 2.1 Add Shared Team Fixtures
**File:** `conftest.py`
**Effort:** M

```python
@pytest.fixture(scope="class")
def team_with_members(db):
    team = TeamFactory()
    members = TeamMemberFactory.create_batch(3, team=team)
    return team, members

@pytest.fixture
def team_context(team):
    from apps.teams.context import set_current_team, unset_current_team
    set_current_team(team)
    yield team
    unset_current_team()
```

#### 2.2 Document Factory Best Practices
**File:** `apps/metrics/factories.py`
**Effort:** S

Add docstring guidance:
```python
"""
Performance Tips:
- Always pass team= to avoid creating new Team per object
- Pass author= to PullRequestFactory to reuse TeamMember
- Use Factory.build() for unit tests not requiring DB
"""
```

#### 2.3 Audit High-Volume Test Files
**Files:** Top 10 largest test files
**Effort:** M

Review and fix factory patterns in:
- `test_ai_detector.py` (117 tests)
- `test_views.py` (111 tests)
- `test_llm_prompts.py` (101 tests)
- `test_chart_views.py` (97 tests)
- `test_models.py` (69 tests)

### Phase 3: Test Class Refactoring

#### 3.1 Convert Dashboard Tests to setUpTestData
**Files:** `apps/metrics/tests/dashboard/*.py`
**Effort:** L

Target classes (20+ tests each):
- `TestGetKeyMetrics`
- `TestGetTeamBreakdown`
- `TestGetChannelMetrics`
- `TestGetPRMetrics`

Pattern:
```python
class TestGetKeyMetrics(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.author = TeamMemberFactory(team=cls.team)
        # Base PRs for all tests
        cls.base_prs = PullRequestFactory.create_batch(
            5, team=cls.team, author=cls.author
        )
```

#### 3.2 Convert View Tests to setUpTestData
**Files:** `apps/integrations/tests/test_views.py`
**Effort:** L

This file has 111 tests sharing similar authentication setup.

#### 3.3 Convert Service Tests to setUpTestData
**Files:** `apps/metrics/tests/test_pr_list_service.py`
**Effort:** M

43 tests that can share common PR fixtures.

### Phase 4: Infrastructure Improvements

#### 4.1 Add Query Count Assertions
**Effort:** M

Add `assertNumQueries` to critical service tests:
```python
def test_get_key_metrics_query_count(self):
    with self.assertNumQueries(5):  # Document expected count
        get_key_metrics(self.team, self.start_date, self.end_date)
```

#### 4.2 Add Performance CI Check
**Effort:** M

Create GitHub Action to run `pytest --durations=20` and flag slow tests.

#### 4.3 Create Test Performance Documentation
**File:** `dev/TEST-PERFORMANCE.md`
**Effort:** S

Document patterns and anti-patterns for team reference.

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| setUpTestData causes test pollution | Low | High | Use `@classmethod` carefully, don't mutate class data |
| Mocking too much hides real bugs | Medium | Medium | Keep integration tests that exercise real code paths |
| Parallel test failures after changes | Low | Medium | Run tests serially after major changes |
| Factory changes break existing tests | Low | High | Make changes incrementally, run full suite after each |

## Success Metrics

### Quantitative
- [ ] Test suite < 70s parallel execution
- [ ] Zero slow tests (>3s) without `@slow` marker
- [ ] No tests hitting real network endpoints
- [ ] >50% of large test classes using setUpTestData

### Qualitative
- [ ] Developer satisfaction with test feedback loop
- [ ] CI pipeline time reduction noticeable
- [ ] No increase in flaky test rate

## Dependencies

### Required Knowledge
- pytest fixtures and scoping
- Django TestCase vs TransactionTestCase
- Factory Boy patterns
- asyncio mocking

### External Dependencies
None - all changes are internal to the test suite.

## Timeline Estimate

| Phase | Duration | Prerequisites |
|-------|----------|---------------|
| Phase 1 | 1-2 hours | None |
| Phase 2 | 2-4 hours | Phase 1 |
| Phase 3 | 4-8 hours | Phase 2 |
| Phase 4 | 2-4 hours | Phase 3 |

**Total:** 9-18 hours of focused work
