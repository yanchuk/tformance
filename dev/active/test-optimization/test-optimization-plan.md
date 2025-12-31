# Test Performance Optimization Plan

**Last Updated:** 2025-12-31
**Status:** ✅ COMPLETE
**Priority:** High (TDD workflow critical path)

## Final Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Full test suite | 180s | 53s | **70% faster** |
| Seeding tests | 188s | 15s | **92% faster** |
| Tests passing | 3955 | 4404 | All pass |

---

## Executive Summary

The test suite (~4000 tests) currently takes ~180 seconds to run. Analysis reveals that **10 tests consume 35% of total execution time** (188 seconds). This plan addresses the root causes:

1. **Seeding tests** regenerating full datasets per test method (188s)
2. **GraphQL tests** using TransactionTestCase unnecessarily (~110s)
3. **Slow tests** running in default CI without filtering

**Expected outcome:** Reduce test suite runtime by 60-70% (from 180s to ~60s), improving TDD feedback loops.

---

## Current State Analysis

### Test Performance Profile

| Category | Tests | Total Time | Avg/Test | Issue |
|----------|-------|------------|----------|-------|
| Seeding tests | 10 | 188s | 18.8s | Full data generation per test |
| GraphQL sync | 22 | ~110s | 5s | TransactionTestCase overhead |
| Setup overhead | ~10 | ~50s | 5s | DB initialization |
| Other | ~3900 | ~30s | 0.008s | Normal |

### Root Cause Analysis

#### 1. Seeding Tests (`test_data_generator.py`)
- Each of 10 tests calls `generator.generate(self.team)`
- Creates: 5 members × 8 weeks × 4 PRs = ~160 PRs per test
- Plus reviews, commits, weekly metrics
- **Problem:** `setUp()` recreates everything per test method

#### 2. GraphQL Tests (`test_github_graphql_sync.py`)
- 22 test classes using `TransactionTestCase`
- TransactionTestCase truncates tables (slow) vs TestCase uses transaction rollback (fast)
- Tests mock external APIs - no need for real transaction testing

#### 3. Test Configuration
- `@pytest.mark.slow` marker exists but not excluded by default
- Tests run with `-n auto` (parallel) which is good
- `--reuse-db` enabled - DB schema reused

---

## Proposed Future State

### Target Performance

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Full suite | 180s | 60s | 67% faster |
| Seeding tests | 188s | 30s | 84% faster |
| GraphQL tests | 110s | 25s | 77% faster |
| CI feedback | 3 min | 1 min | 3x faster |

### Architecture Changes

1. **Class-level fixtures** for seeding tests using `setUpTestData()`
2. **TestCase migration** for GraphQL tests (22 classes)
3. **Optional:** Exclude slow tests from default runs

---

## Implementation Phases

### Phase 1: Quick Wins (Low Effort, High Impact)
**Goal:** Immediate improvements with minimal risk

1. Convert GraphQL tests from TransactionTestCase → TestCase
2. Verify tests still pass
3. Measure performance improvement

### Phase 2: High Impact Refactoring
**Goal:** Fix the slowest tests with architectural changes

1. Refactor seeding tests to use `setUpTestData()`
2. Create shared test data that persists across test methods
3. Ensure test isolation is maintained

### Phase 3: Configuration Optimization
**Goal:** Improve default test behavior

1. Optionally exclude slow tests from default runs
2. Document slow test workflow
3. Add CI job for slow tests (if separated)

---

## Detailed Implementation

### Phase 1: GraphQL Test Migration

**File:** `apps/integrations/tests/test_github_graphql_sync.py`

**Change Pattern:**
```python
# Before
from django.test import TransactionTestCase

class TestSyncRepositoryHistory(TransactionTestCase):
    ...

# After
from django.test import TestCase

class TestSyncRepositoryHistory(TestCase):
    ...
```

**22 classes to convert:**
- TestSyncRepositoryHistoryGraphQLBasicFunctionality
- TestSyncRepositoryHistoryGraphQLDataUpdateBehavior
- TestSyncRepositoryHistoryGraphQLErrorHandling
- TestSyncRepositoryHistoryGraphQLPagination
- TestSyncRepositoryHistoryGraphQLProgressTracking
- TestSyncGitHubMembersGraphQLBasic
- TestSyncGitHubMembersGraphQLDataProcessing
- TestSyncGitHubMembersGraphQLErrorHandling
- TestSyncRepositoryIncrementalGraphQLBasicFunctionality
- TestSyncRepositoryIncrementalGraphQLStatusTracking
- TestSyncRepositoryIncrementalGraphQLErrorHandling
- TestGraphQLSyncAIDetectionInitialSync
- TestGraphQLSyncAIDetectionIncrementalSync
- TestFetchPRCompleteDataGraphQLDataProcessing
- (+ 8 more)

**Verification:**
```bash
pytest apps/integrations/tests/test_github_graphql_sync.py -v --durations=30
```

---

### Phase 2: Seeding Test Optimization

**File:** `apps/metrics/tests/test_seeding/test_data_generator.py`

**Current Structure:**
```python
class TestScenarioDataGenerator(TestCase):
    def setUp(self):
        self.team = Team.objects.create(...)
        self.scenario = get_scenario("ai-success")

    def tearDown(self):
        # Manual cleanup...

    def test_generator_creates_team_members(self):
        generator = ScenarioDataGenerator(...)
        stats = generator.generate(self.team)  # 20s per call!
        ...
```

**Optimized Structure:**
```python
@pytest.mark.slow
class TestScenarioDataGenerator(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Generate test data ONCE for all test methods."""
        cls.team = Team.objects.create(name="Test Team", slug="test-team")
        cls.scenario = get_scenario("ai-success")
        cls.generator = ScenarioDataGenerator(
            scenario=cls.scenario,
            seed=42,
            fetch_github=False,
        )
        cls.stats = cls.generator.generate(cls.team)

    # No tearDown needed - Django TestCase uses transactions

    def test_generator_creates_team_members(self):
        """Test passes because data already exists from setUpTestData."""
        self.assertEqual(self.stats.team_members_created, 5)
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 5)

    def test_generator_creates_prs(self):
        """Uses same data - no regeneration!"""
        self.assertGreater(self.stats.prs_created, 0)
```

**Key Changes:**
1. Move `generator.generate()` to `setUpTestData()` (runs once per class)
2. Remove manual `tearDown()` cleanup (TestCase handles via transactions)
3. Tests become read-only validations of pre-generated data

**Handling Tests That Need Different Data:**
- `test_same_seed_produces_same_counts` - needs 2 runs → separate test class
- `test_different_seed_produces_different_results` - needs 2 runs → separate test class
- `test_bottleneck_reviewer_gets_more_reviews` - needs different scenario → already separate class

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| TestCase migration breaks tests | Medium | Low | Tests are mocked - no real transactions |
| setUpTestData isolation failure | High | Low | Tests should be read-only; add assertions |
| Parallel test interference | Medium | Low | setUpTestData is per-worker isolated |
| Regression in CI | High | Low | Run full suite before/after changes |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| GraphQL test duration | < 30s | `pytest --durations=30` |
| Seeding test duration | < 35s | `pytest --durations=30` |
| Full suite duration | < 80s | `make test` |
| All tests pass | 100% | CI green |

---

## Dependencies

- **pytest-django:** Already configured with `--reuse-db`
- **Django TestCase:** Supports `setUpTestData()` natively
- **No external dependencies required**

---

## Verification Commands

```bash
# Baseline measurement (before changes)
DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/pytest --durations=30 -q 2>&1 | tail -50

# Run specific test files after changes
pytest apps/integrations/tests/test_github_graphql_sync.py -v --durations=10
pytest apps/metrics/tests/test_seeding/test_data_generator.py -v --durations=10

# Full suite verification
make test

# Compare durations
pytest --durations=30 -q 2>&1 | grep -E "^\d+\.\d+s"
```
