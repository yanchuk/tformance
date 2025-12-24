# Test Speed Optimization Plan

**Last Updated: 2025-12-21**

## Executive Summary

Optimize Django test suite execution from ~125s (1,942 tests) to ~30-40s through parallel execution enablement, test data setup optimization, and eventual pytest migration. This enables faster TDD cycles and CI/CD feedback loops.

## Current State Analysis

### Metrics
| Metric | Value |
|--------|-------|
| Total tests | 1,942 |
| Execution time | ~125s (2 min 5s) |
| Avg per test | ~64ms |
| Test classes | 342 |
| setUp methods | 194 |
| setUpTestData usage | 3 (1.5%) |
| Test files | 127 |

### Identified Issues

1. **Parallel execution broken**: Django `--parallel` fails with serialization errors
   - Root cause: `apps/utils/tests/test_fields.py` creates/drops tables in setUpClass
   - Missing tblib package for traceback serialization

2. **Flaky tests**: Factory collisions on unique constraints
   - `TeamMemberFactory` uses `Faker("name")` which can repeat
   - Causes `IntegrityError: duplicate key value violates unique constraint "unique_team_email"`

3. **Inefficient test data setup**: 194 setUp() vs 3 setUpTestData()
   - Each test method recreates Team + User + Members
   - Heavy factory usage (100+ calls per file in top files)

4. **No --keepdb default**: Test database recreated on each full run

### Files with Highest Factory Usage
| File | Factory Calls |
|------|---------------|
| apps/integrations/tests/test_models.py | 118 |
| apps/integrations/tests/test_views.py | 111 |
| apps/metrics/tests/test_quick_stats.py | 110 |
| apps/metrics/tests/test_insight_rules.py | 77 |
| apps/integrations/tests/test_tasks.py | 55 |

## Proposed Future State

### Target Metrics
| Metric | Current | Target |
|--------|---------|--------|
| Full suite time | 125s | 30-40s |
| Parallel execution | Broken | Working |
| Flaky tests | Yes | No |
| Developer iteration | 2+ min | <45s |

### Architecture Changes
- Enable Django parallel test runner (Phase 2)
- Migrate to pytest-django with xdist (Phase 4)
- Standardize on setUpTestData for shared fixtures

## Implementation Phases

### Phase 1: Quick Wins (Day 1)
**Goal**: Immediate improvements with minimal risk

1. Make `--keepdb` the default in Makefile
2. Install tblib for parallel debugging
3. Fix TeamMemberFactory unique constraint issue
4. Add factory sequence for other potentially colliding fields

**Expected Outcome**: Flaky tests fixed, faster individual runs

### Phase 2: Enable Parallel Execution (Day 1-2)
**Goal**: Unlock Django's built-in parallel testing

1. Fix test_fields.py to be parallel-safe
2. Identify and fix any transaction-related test issues
3. Verify parallel execution works across all apps
4. Update Makefile with optimized parallel command

**Expected Outcome**: 50-70% reduction in test time

### Phase 3: Test Data Optimization (Week 1)
**Goal**: Reduce redundant database operations

1. Audit tests for setUp → setUpTestData candidates
2. Convert high-impact test classes (top 10 by factory usage)
3. Create shared fixtures for common patterns
4. Document best practices

**Expected Outcome**: 10-20% additional time reduction

### Phase 4: pytest Migration (Week 2-3)
**Goal**: Modern test infrastructure with advanced features

1. Add pytest-django, pytest-xdist dependencies
2. Create conftest.py with reusable fixtures
3. Configure pytest in pyproject.toml
4. Validate all tests pass with pytest runner
5. Update CI/CD configuration

**Expected Outcome**: Best-in-class test performance, better DX

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Parallel tests expose hidden dependencies | High | Medium | Run pytest-randomly, fix incrementally |
| setUpTestData breaks tests that mutate data | Medium | Medium | Audit before conversion |
| pytest migration breaks existing tests | High | Low | Run both runners during migration |
| CI/CD integration issues | Medium | Low | Test locally first, gradual rollout |

## Success Metrics

1. **Test execution time**: Target <45s for full suite
2. **Flaky test rate**: Zero random failures in CI
3. **Developer satisfaction**: Faster feedback loops
4. **CI pipeline time**: Reduced by proportional amount

## Required Resources

### Dependencies to Add
```toml
[dependency-groups]
dev = [
    # Existing...
    "tblib>=3.0.0",
    # Phase 4
    "pytest>=8.0",
    "pytest-django>=4.8",
    "pytest-xdist>=3.5",
    "pytest-randomly>=3.15",
]
```

### Files to Modify
- `Makefile` - Test commands
- `pyproject.toml` - Dependencies and pytest config
- `apps/metrics/factories.py` - Fix TeamMemberFactory
- `apps/utils/tests/test_fields.py` - Parallel-safe table creation
- Multiple test files for setUpTestData conversion
