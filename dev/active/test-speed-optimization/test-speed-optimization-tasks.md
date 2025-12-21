# Test Speed Optimization Tasks

**Last Updated: 2025-12-21**

## Phase 1: Quick Wins [Day 1]

### 1.1 Make --keepdb the default
- [ ] Edit `Makefile` test target to include `--keepdb`
- [ ] Verify test run uses existing database
- [ ] Update documentation in CLAUDE.md if needed

**Effort**: S | **Priority**: P0 | **Dependencies**: None

### 1.2 Install tblib
- [ ] Add `tblib>=3.0.0` to dev dependencies in pyproject.toml
- [ ] Run `uv sync`
- [ ] Verify import works: `python -c "import tblib"`

**Effort**: S | **Priority**: P0 | **Dependencies**: None

### 1.3 Fix TeamMemberFactory unique constraint
- [ ] Open `apps/metrics/factories.py`
- [ ] Change line 66: `display_name = factory.Sequence(lambda n: f"Developer {n}")`
- [ ] Change line 67: `email = factory.Sequence(lambda n: f"developer{n}@example.com")`
- [ ] Also fix github_username to use Sequence if not already
- [ ] Run tests to verify no more flaky failures

**Effort**: S | **Priority**: P0 | **Dependencies**: None

### 1.4 Verify Phase 1 complete
- [ ] Run `make test ARGS='--keepdb'` - should pass, no flaky tests
- [ ] Time the run and document baseline

**Effort**: S | **Priority**: P0 | **Dependencies**: 1.1, 1.2, 1.3

---

## Phase 2: Enable Parallel Execution [Day 1-2]

### 2.1 Fix test_fields.py for parallel safety
- [ ] Open `apps/utils/tests/test_fields.py`
- [ ] Option A: Convert to use TransactionTestCase with separate DB
- [ ] Option B: Create TestModel via proper migration (if preferred)
- [ ] Remove setUpClass/tearDownClass table manipulation
- [ ] Verify test still passes individually

**Effort**: M | **Priority**: P0 | **Dependencies**: 1.4

### 2.2 Test parallel execution on subsets
- [ ] Run: `make test-parallel ARGS='apps.metrics --keepdb'`
- [ ] Run: `make test-parallel ARGS='apps.integrations --keepdb'`
- [ ] Run: `make test-parallel ARGS='apps.teams --keepdb'`
- [ ] Document any additional failures

**Effort**: M | **Priority**: P1 | **Dependencies**: 2.1

### 2.3 Fix any remaining parallel issues
- [ ] Address transaction errors if any
- [ ] Fix any test isolation issues discovered
- [ ] Document patterns that break parallel execution

**Effort**: M-L | **Priority**: P1 | **Dependencies**: 2.2

### 2.4 Full parallel test run
- [ ] Run: `make test-parallel ARGS='--keepdb'`
- [ ] All 1,942 tests should pass
- [ ] Time the run and compare to sequential

**Effort**: S | **Priority**: P0 | **Dependencies**: 2.3

### 2.5 Update Makefile with optimized commands
- [ ] Update `test-parallel` to include `--keepdb` by default
- [ ] Add number of workers option (e.g., `--parallel=auto`)
- [ ] Document in Makefile help

**Effort**: S | **Priority**: P1 | **Dependencies**: 2.4

---

## Phase 3: Test Data Optimization [Week 1]

### 3.1 Audit high-impact test files
- [ ] Review `apps/integrations/tests/test_views.py` - 15 classes
- [ ] Review `apps/metrics/tests/test_quick_stats.py` - 1 class
- [ ] Review `apps/metrics/tests/test_insight_rules.py` - 7 classes
- [ ] Review `apps/metrics/tests/test_chart_views.py` - 9 classes
- [ ] Identify which classes can use setUpTestData (don't mutate data)

**Effort**: M | **Priority**: P1 | **Dependencies**: 2.4

### 3.2 Convert test_quick_stats.py
- [ ] Change setUp to setUpTestData
- [ ] Change self.X to cls.X in class method
- [ ] Verify all tests still pass
- [ ] Time improvement for this file

**Effort**: M | **Priority**: P1 | **Dependencies**: 3.1

### 3.3 Convert test_insight_rules.py (7 classes)
- [ ] Convert each class one at a time
- [ ] Verify tests pass after each conversion
- [ ] Skip any classes that mutate shared data

**Effort**: M | **Priority**: P2 | **Dependencies**: 3.1

### 3.4 Convert test_chart_views.py (9 classes)
- [ ] Convert each class one at a time
- [ ] Verify tests pass after each conversion
- [ ] Skip any classes that mutate shared data

**Effort**: M | **Priority**: P2 | **Dependencies**: 3.1

### 3.5 Convert test_views.py (15 classes)
- [ ] Convert each class one at a time
- [ ] Verify tests pass after each conversion
- [ ] This is the largest file, may need to split into sessions

**Effort**: L | **Priority**: P2 | **Dependencies**: 3.1

### 3.6 Document best practices
- [ ] Add section to CLAUDE.md about setUpTestData vs setUp
- [ ] Include when to use each
- [ ] Add examples

**Effort**: S | **Priority**: P2 | **Dependencies**: 3.2

---

## Phase 4: pytest Migration [Week 2-3]

### 4.1 Add pytest dependencies
- [ ] Add to pyproject.toml:
  - pytest>=8.0
  - pytest-django>=4.8
  - pytest-xdist>=3.5
  - pytest-randomly>=3.15
- [ ] Run `uv sync`
- [ ] Verify pytest runs: `pytest --version`

**Effort**: S | **Priority**: P1 | **Dependencies**: Phase 3 complete

### 4.2 Create pytest configuration
- [ ] Add `[tool.pytest.ini_options]` section to pyproject.toml
- [ ] Set DJANGO_SETTINGS_MODULE
- [ ] Configure python_files pattern
- [ ] Add default addopts (--reuse-db, etc.)

**Effort**: S | **Priority**: P1 | **Dependencies**: 4.1

### 4.3 Create conftest.py
- [ ] Create root `conftest.py`
- [ ] Add `@pytest.fixture` for db access
- [ ] Add common fixtures (team, admin_user, etc.)
- [ ] Configure pytest-django settings

**Effort**: M | **Priority**: P1 | **Dependencies**: 4.2

### 4.4 Run pytest on subset
- [ ] Run: `pytest apps/utils -v`
- [ ] Run: `pytest apps/teams -v`
- [ ] Fix any compatibility issues
- [ ] Document patterns that need adjustment

**Effort**: M | **Priority**: P1 | **Dependencies**: 4.3

### 4.5 Run full pytest suite
- [ ] Run: `pytest`
- [ ] All tests should pass
- [ ] Compare time to Django test runner

**Effort**: M | **Priority**: P1 | **Dependencies**: 4.4

### 4.6 Enable parallel execution
- [ ] Run: `pytest -n auto`
- [ ] Verify all tests pass
- [ ] Fine-tune worker count for best performance
- [ ] Document optimal settings

**Effort**: M | **Priority**: P1 | **Dependencies**: 4.5

### 4.7 Update Makefile
- [ ] Add `pytest` target
- [ ] Add `pytest-parallel` target
- [ ] Keep Django runner as fallback
- [ ] Update help text

**Effort**: S | **Priority**: P2 | **Dependencies**: 4.6

### 4.8 Update CI/CD
- [ ] Update GitHub Actions workflow
- [ ] Use pytest with xdist
- [ ] Verify CI passes

**Effort**: M | **Priority**: P1 | **Dependencies**: 4.7

### 4.9 Final documentation
- [ ] Update CLAUDE.md test section
- [ ] Document pytest commands
- [ ] Remove references to old patterns if obsolete

**Effort**: S | **Priority**: P2 | **Dependencies**: 4.8

---

## Progress Summary

| Phase | Status | Tasks Done | Tasks Total |
|-------|--------|------------|-------------|
| Phase 1: Quick Wins | Not Started | 0 | 4 |
| Phase 2: Parallel | Not Started | 0 | 5 |
| Phase 3: Optimization | Not Started | 0 | 6 |
| Phase 4: pytest | Not Started | 0 | 9 |
| **Total** | **Not Started** | **0** | **24** |

## Notes

- Start with Phase 1 - can be done in 20 minutes
- Phase 2 is the biggest bang for buck (50-70% speedup)
- Phase 3 and 4 can be done incrementally
- Always verify tests pass after each change
