# Test Performance Optimization - Tasks

**Last Updated:** 2025-12-25

## Results Summary

### Phase 1 Complete! ✅

| Optimization | Before | After | Improvement |
|--------------|--------|-------|-------------|
| GraphQL retry tests | ~10s | 1.06s | **90% faster** |
| LLM task tests | 26.12s | 0.86s | **97% faster** |
| Full test suite | ~94s | 58.33s | **38% faster** |

**Total time saved per run: ~36 seconds**

### Phase 2 Complete! ✅

| Task | Status | Notes |
|------|--------|-------|
| Shared fixtures | ✅ | Added team_with_members, team_context, authenticated_team_client, sample_prs |
| Factory docs | ✅ | Added best practices to factories.py module docstring |
| Factory audit | ✅ | All top 5 files already use proper patterns (team= passed correctly) |

**Full test suite: 49.36s (3064 passed)**

## Phase 1: Quick Wins (~1-2 hours)

### 1.1 Mock asyncio.sleep in GraphQL Retry Tests ✅
**Effort:** S | **Impact:** ~30s saved

- [x] Add `@patch("asyncio.sleep")` class decorator to `TestRetryOnTimeout`
- [x] Add `@patch("asyncio.sleep")` class decorator to `TestTimeoutHandling`
- [x] Add `@patch("asyncio.sleep")` decorator to `test_fetch_prs_updated_since_retries_on_timeout`
- [x] Update all method signatures to accept `mock_sleep` parameter
- [x] Verify tests pass: 46 passed in 1.06s ✅

**Result:** All retry tests complete in <0.1s each (down from 3s each)

### 1.2 Mark Slow Seeding Tests ✅
**Effort:** S | **Impact:** ~10s saved (on quick runs)

- [x] Add `@pytest.mark.slow` to `TestScenarioDataGenerator` class
- [x] Add `@pytest.mark.slow` to `TestScenarioDataGeneratorWithBottleneck` class
- [x] Add `test-quick` target to Makefile
- [x] Verify markers work: 10 slow tests marked, 63 fast tests run with `-m "not slow"`

**Result:** `make test-quick` excludes 10 slow seeding tests (~10s saved)

### 1.3 Fix LLM Task Test Performance ✅
**Effort:** S | **Impact:** ~25s saved

- [x] Move task imports to module level
- [x] Add `@patch("apps.metrics.tasks.time.sleep")` to `TestRunLLMAnalysisBatchTask`
- [x] Add `@patch("apps.metrics.tasks.time.sleep")` to `TestLLMTaskDataExtraction`
- [x] Update all method signatures to accept `mock_sleep` parameter
- [x] Verify tests pass: 14 passed in 0.86s ✅

**Result:** LLM task tests run in 0.86s (down from 26.12s - **97% improvement**)

---

## Phase 2: Factory Optimization (~2-4 hours) ✅

### 2.1 Add Shared Team Fixtures to conftest.py ✅
**Effort:** M | **Impact:** Foundation for other improvements

- [x] Add `team_with_members` fixture (function-scoped, returns tuple)
- [x] Add `team_context` function-scoped fixture (sets/unsets team context)
- [x] Add `authenticated_team_client` fixture (returns client, team, user)
- [x] Add `sample_prs` fixture (10 PRs with reviews and commits)
- [x] Document fixture usage in conftest.py docstring
- [x] Add setUpTestData example for Django TestCase users

**Result:** 4 new fixtures added, all tests pass (4.77s for fixture tests)

### 2.2 Document Factory Best Practices ✅
**Effort:** S | **Impact:** Prevents future regressions

- [x] Add performance tips to `apps/metrics/factories.py` module docstring
- [x] Add inline comment to `PullRequestFactory` about passing team=
- [x] Add inline comment to `PRReviewFactory` about passing team= and pull_request=
- [x] Create examples in docstring showing good vs bad patterns

**Result:** Comprehensive documentation with 5 best practices

### 2.3 Audit Top 5 Test Files for Factory Patterns ✅
**Effort:** M | **Impact:** Already optimized!

Files audited:
- [x] `apps/metrics/tests/test_ai_detector.py` - 0 factory usage (pure unit tests)
- [x] `apps/integrations/tests/test_views.py` - 44 factories, all use team= ✅
- [x] `apps/metrics/tests/test_llm_prompts.py` - 18 factories, all use team= ✅
- [x] `apps/metrics/tests/test_chart_views.py` - uses Team/User only ✅
- [x] `apps/integrations/tests/test_models.py` - 2 factories, all use team= ✅

**Result:** No anti-patterns found - codebase already follows best practices!

---

## Phase 3: Test Class Refactoring - SKIPPED ⏭️

### Analysis Results
After analyzing dashboard tests, determined that Phase 3 is **not worthwhile**:

1. **Dashboard tests already fast** (<1s per file, 0.48-0.96s each)
2. **setUpTestData would break test isolation**:
   - Tests create PRs with specific date ranges for assertions
   - Shared team would make all tests see all PRs
   - Count-based assertions would fail
3. **Effort vs. reward**: Large refactoring for minimal gains

### 3.1 Dashboard Tests - SKIPPED ⏭️
**Reason:** Already optimized (190 tests in ~8s total)

Individual timings:
- test_channel_metrics.py: 53 tests in 0.96s
- test_pr_metrics.py: 45 tests in 0.80s
- test_review_metrics.py: 23 tests in 0.83s
- test_team_breakdown.py: 17 tests in 0.68s
- (all others < 0.6s)

### 3.2 Integration Views Tests - SKIPPED ⏭️
**Reason:** Same isolation issue - tests count/filter data

### 3.3 PR List Tests - SKIPPED ⏭️
**Reason:** Same isolation issue - service tests aggregate data

---

## Phase 4: Infrastructure Improvements (~2-4 hours)

### 4.1 Add Query Count Assertions to Critical Paths
**Effort:** M | **Impact:** Prevents N+1 regressions

- [ ] Add `assertNumQueries` to `get_key_metrics` test
- [ ] Add `assertNumQueries` to `get_team_breakdown` test
- [ ] Add `assertNumQueries` to `pr_list_export` test
- [ ] Document expected query counts in comments

**Acceptance Criteria:**
- N+1 queries detected in CI
- Query counts documented

### 4.2 Add Performance CI Check
**Effort:** M | **Impact:** Catches slow tests early

- [ ] Create GitHub Action that runs `--durations=20`
- [ ] Add warning annotation for tests >1s
- [ ] Add failure for tests >5s without `@slow` marker

**Acceptance Criteria:**
- CI fails if unexpectedly slow test is added
- Developers see timing in PR checks

### 4.3 Create Test Performance Documentation
**Effort:** S | **Impact:** Team education

- [ ] Create `dev/TEST-PERFORMANCE.md`
- [ ] Document fixture patterns
- [ ] Document factory best practices
- [ ] Add examples of common anti-patterns
- [ ] Link from CLAUDE.md testing section

**Acceptance Criteria:**
- New developers can understand performance patterns
- Document reviewed by team

---

## Final Summary

### Optimization Complete! 🎉

| Phase | Status | Impact |
|-------|--------|--------|
| Phase 1: Mock sleeps | ✅ Complete | 36s saved |
| Phase 2: Factory docs | ✅ Complete | Foundation for future |
| Phase 3: setUpTestData | ⏭️ Skipped | Not needed - tests already fast |
| Phase 4: CI checks | 📋 Optional | Prevents regressions |

**Final Result: ~94s → ~50s (47% faster)**

## Verification Checklist

- [x] Run full test suite: `make test` - 3074 passed in ~50s ✅
- [x] Compare timing to baseline (was ~94s parallel) - Now ~50s ✅
- [x] Run slow tests only: `pytest -m slow -v` - 10 slow tests work ✅
- [x] Run quick tests: `make test-quick` - Excludes slow tests ✅
- [ ] Verify no flaky tests: run 3x with `--randomly-seed=<random>` (optional)
- [x] Update this document with final metrics ✅

---

## Notes

### Commands for Testing Progress

```bash
# Baseline timing
time .venv/bin/pytest --reuse-db -n auto -q

# Detailed timing report
.venv/bin/pytest --durations=50 -n 0 --tb=no -q 2>&1 | head -70

# Verify specific fix
.venv/bin/pytest apps/integrations/tests/test_github_graphql.py --durations=10 -n 0

# Run excluding slow
.venv/bin/pytest -m "not slow" --reuse-db -n auto
```

### Rollback Plan

If issues arise:
1. Each phase is independent - can revert one without affecting others
2. Keep git commits atomic per-file for easy rollback
3. Run tests after each file change before continuing
