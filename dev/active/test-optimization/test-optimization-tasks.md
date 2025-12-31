# Test Optimization Tasks

**Last Updated:** 2025-12-31

---

## Phase 1: GraphQL Test Migration (Quick Win)

**Effort:** Small | **Risk:** Low | **Impact:** High (~80s savings)

### Tasks

- [ ] **1.1** Baseline measurement of GraphQL test performance
  ```bash
  pytest apps/integrations/tests/test_github_graphql_sync.py --durations=30 -q
  ```
  - Acceptance: Record total time and per-test times

- [ ] **1.2** Replace TransactionTestCase with TestCase (22 classes)
  - File: `apps/integrations/tests/test_github_graphql_sync.py`
  - Change: `from django.test import TransactionTestCase` → `from django.test import TestCase`
  - Change: All class declarations
  - Acceptance: All 22 classes updated

- [ ] **1.3** Run tests to verify no failures
  ```bash
  pytest apps/integrations/tests/test_github_graphql_sync.py -v
  ```
  - Acceptance: All tests pass (0 failures)

- [ ] **1.4** Measure performance improvement
  ```bash
  pytest apps/integrations/tests/test_github_graphql_sync.py --durations=30 -q
  ```
  - Acceptance: Average test time reduced from ~5s to <1s

---

## Phase 2: Seeding Test Optimization (High Impact)

**Effort:** Medium | **Risk:** Low | **Impact:** Very High (~160s savings)

### Tasks

- [ ] **2.1** Baseline measurement of seeding test performance
  ```bash
  pytest apps/metrics/tests/test_seeding/test_data_generator.py --durations=30 -v
  ```
  - Acceptance: Record total time (~188s expected)

- [ ] **2.2** Refactor TestScenarioDataGenerator to use setUpTestData
  - Move team creation to `setUpTestData()`
  - Move scenario/generator initialization to `setUpTestData()`
  - Move `generator.generate()` call to `setUpTestData()`
  - Store stats as class attribute
  - Remove manual `tearDown()` cleanup
  - Acceptance: Single `generator.generate()` call for all tests

- [ ] **2.3** Update test methods to use class data
  - Change assertions to use `self.stats` (pre-computed)
  - Remove per-test generator calls
  - Ensure tests are read-only
  - Acceptance: No test modifies shared data

- [ ] **2.4** Extract reproducibility tests to separate class
  - Create `TestScenarioDataGeneratorReproducibility` class
  - Move `test_same_seed_produces_same_counts`
  - Move `test_different_seed_produces_different_results`
  - These tests need multiple generator runs
  - Acceptance: 2 tests in new class with own setup

- [ ] **2.5** Refactor TestScenarioDataGeneratorWithBottleneck
  - Apply same setUpTestData pattern
  - Different scenario (review-bottleneck)
  - Acceptance: Single generate() call for class

- [ ] **2.6** Run all seeding tests to verify
  ```bash
  pytest apps/metrics/tests/test_seeding/test_data_generator.py -v
  ```
  - Acceptance: All tests pass (0 failures)

- [ ] **2.7** Measure performance improvement
  ```bash
  pytest apps/metrics/tests/test_seeding/test_data_generator.py --durations=30 -v
  ```
  - Acceptance: Total time < 40s (was ~188s)

---

## Phase 3: Full Suite Verification

**Effort:** Small | **Risk:** Low | **Impact:** Validation

### Tasks

- [ ] **3.1** Run full test suite
  ```bash
  make test
  ```
  - Acceptance: All tests pass, no regressions

- [ ] **3.2** Measure total suite performance
  ```bash
  pytest --durations=30 -q 2>&1 | tail -50
  ```
  - Acceptance: Total time < 80s (was ~180s)

- [ ] **3.3** Document final results
  - Update context.md with final performance numbers
  - Acceptance: Before/after comparison documented

---

## Phase 4: Optional Improvements

**Effort:** Small | **Risk:** Low | **Impact:** Medium

### Tasks

- [ ] **4.1** Consider excluding slow tests from default runs
  - Decision needed: Is 60-80s fast enough?
  - If needed, add `-m "not slow"` to addopts
  - Acceptance: Decision documented

- [ ] **4.2** Review other TransactionTestCase usage
  ```bash
  grep -r "TransactionTestCase" apps/ --include="*.py" | wc -l
  ```
  - Acceptance: Identify any other optimization candidates

- [ ] **4.3** Update CLAUDE.md with test performance guidelines
  - Document setUpTestData pattern
  - Document when to use TestCase vs TransactionTestCase
  - Acceptance: Guidelines added to test section

---

## Verification Commands

```bash
# Quick test of specific files
pytest apps/integrations/tests/test_github_graphql_sync.py -v --durations=10
pytest apps/metrics/tests/test_seeding/test_data_generator.py -v --durations=10

# Full suite with timing
make test

# Check slowest tests
pytest --durations=30 -q 2>&1 | grep -E "^\d+\.\d+s" | head -20

# Run only non-slow tests (if configured)
pytest -m "not slow"
```

---

## Progress Summary

| Phase | Status | Tasks Done | Actual Savings |
|-------|--------|------------|----------------|
| Phase 1 | SKIPPED | N/A | Async requires TransactionTestCase |
| Phase 2 | ✅ COMPLETE | 7/7 | ~173s (92% faster) |
| Phase 3 | ✅ COMPLETE | 3/3 | Verified - 4404 tests pass |
| Phase 4 | Not Needed | - | - |

**Actual Result:** 180s → 53s (**70% improvement**)

## Completed (2025-12-31)

### Phase 2 Changes Made:
- [x] Refactored `TestScenarioDataGenerator` to use `setUpTestData()`
- [x] Created `TestScenarioDataGeneratorReproducibility` for multi-run tests
- [x] Created `TestScenarioDataGeneratorGitHubIntegration` for mock-specific tests
- [x] Refactored `TestScenarioDataGeneratorWithBottleneck` to use `setUpTestData()`
- [x] All 12 seeding tests pass
- [x] Full suite (4404 tests) passes in 53.18s

### Key Learning:
GraphQL tests using `asyncio.run()` **must** use TransactionTestCase because async
code runs in a separate thread that cannot see uncommitted transaction data from
TestCase's wrapped transaction.
