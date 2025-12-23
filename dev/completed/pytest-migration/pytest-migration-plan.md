# pytest Migration Plan

**Last Updated: 2025-12-22**

## Executive Summary

Migrate from Django's built-in test runner to pytest with pytest-django for improved tooling, better developer experience, and enhanced test efficiency insights. This builds on the recent test speed optimization work that enabled parallel execution.

### Goals
1. **Per-test timing visibility** - Identify slow tests with `--durations`
2. **Better fixtures** - Cleaner, reusable test setup with pytest fixtures
3. **Improved parallelization** - pytest-xdist for finer control
4. **Test randomization** - pytest-randomly to catch order-dependent tests
5. **Rich plugin ecosystem** - Access to 1000+ pytest plugins
6. **Backward compatibility** - Django TestCase classes continue to work

### Non-Goals
- Rewriting all existing tests to pytest style (gradual migration)
- Removing Django TestCase support (keep both working)

---

## Current State Analysis

### Test Infrastructure
| Metric | Value |
|--------|-------|
| Test files | 264 (110 + 154 nested) |
| Test classes | 647 |
| Total tests | 2,018 |
| Current runner | Django unittest |
| Parallel support | Django `--parallel` (working) |
| Time (sequential) | ~75s |
| Time (parallel) | ~30-55s |

### Current Test Patterns
- All tests use `django.test.TestCase`
- Factory Boy for test data (`apps/*/factories.py`)
- setUp/tearDown methods (few use setUpTestData)
- No pytest fixtures or conftest.py
- Some __pycache__ shows prior pytest experimentation

### Pain Points
1. No per-test timing (can't identify slow tests)
2. Verbose assertion messages (Django vs pytest)
3. No test order randomization
4. Limited fixture reuse across test classes
5. No coverage integration in test command

---

## Proposed Future State

### Architecture
```
tformance/
├── conftest.py              # Root fixtures (db, client, team, user)
├── pytest.ini               # OR pyproject.toml [tool.pytest]
├── apps/
│   ├── metrics/
│   │   ├── conftest.py      # App-specific fixtures
│   │   └── tests/
│   │       └── conftest.py  # Test-specific fixtures (optional)
│   └── integrations/
│       ├── conftest.py
│       └── tests/
```

### Test Commands
```bash
make test                    # pytest (default)
make test-parallel           # pytest -n auto
make test-slow               # pytest --durations=20
make test-coverage           # pytest --cov=apps
make test-watch              # pytest-watch for TDD
make test-django             # Legacy Django runner (fallback)
```

### Expected Improvements
| Metric | Current | Expected |
|--------|---------|----------|
| Slow test visibility | None | `--durations=N` |
| Parallel control | 8 workers fixed | `-n auto` or `-n 4` |
| Assertion readability | Basic | Rich diffs |
| Fixture reuse | Manual | Automatic scoping |
| Coverage integration | Separate | Built-in |

---

## Implementation Phases

### Phase 1: Foundation [Day 1]
Install pytest and configure for Django compatibility.

**Effort**: S | **Risk**: Low

### Phase 2: Root Fixtures [Day 1-2]
Create conftest.py with common fixtures.

**Effort**: M | **Risk**: Low

### Phase 3: Validation [Day 2]
Run all tests with pytest, fix any issues.

**Effort**: M | **Risk**: Medium

### Phase 4: Enhanced Tooling [Day 3]
Add parallelization, coverage, and timing.

**Effort**: S | **Risk**: Low

### Phase 5: Documentation & CI [Day 3]
Update docs and CI/CD pipelines.

**Effort**: S | **Risk**: Low

---

## Risk Assessment

### Risk 1: Test Compatibility
**Risk**: Some Django tests may fail with pytest
**Probability**: Medium
**Impact**: Low (isolated failures)
**Mitigation**: Run full suite early, fix issues incrementally

### Risk 2: Parallel Race Conditions
**Risk**: Tests that pass sequentially may fail in parallel
**Probability**: Low (already fixed for Django --parallel)
**Impact**: Low
**Mitigation**: Use pytest-randomly to catch order dependencies

### Risk 3: CI/CD Breaking Changes
**Risk**: GitHub Actions may need updates
**Probability**: Low
**Impact**: Medium
**Mitigation**: Keep Django runner as fallback, update CI incrementally

---

## Success Metrics

1. **All 2018 tests pass** with pytest
2. **Per-test timing** available via `--durations`
3. **Parallel execution** works with pytest-xdist
4. **No regression** in test speed (still ~30-55s parallel)
5. **Documentation** updated in CLAUDE.md
6. **CI/CD** using pytest

---

## Dependencies

### New Packages
```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-django>=4.8",
    "pytest-xdist>=3.5",
    "pytest-randomly>=3.15",
    "pytest-cov>=4.1",
]
```

### Configuration Requirements
- DJANGO_SETTINGS_MODULE must be set
- Database must be available for tests
- Existing factories continue to work

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1 | 1 hour | pytest installed, basic config |
| Phase 2 | 2 hours | conftest.py with fixtures |
| Phase 3 | 2-4 hours | All tests passing |
| Phase 4 | 1 hour | xdist, coverage, timing |
| Phase 5 | 1 hour | Docs and CI updated |

**Total**: ~1 day of focused work
