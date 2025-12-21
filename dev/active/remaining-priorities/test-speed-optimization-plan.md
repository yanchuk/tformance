# Test Speed Optimization Plan

## Current State Analysis

| Metric | Value |
|--------|-------|
| Total tests | 1,942 |
| Execution time | ~125s (2 min 5s) |
| Avg per test | ~64ms |
| Test classes | 342 |
| setUp methods | 194 |
| Test files | 127 |
| Lines of test code | ~69,268 |

### Startup Overhead
- Django startup: ~2s per test command invocation
- Database connection: Using `--keepdb` saves ~5-10s
- **Current state: `--keepdb` is NOT the default** - each full run recreates DB

### Parallel Execution Status
Django's built-in `--parallel` mode **fails immediately** with:
```
TypeError: cannot serialize 'traceback' object
```

Root causes identified:
1. **`apps/utils/tests/test_fields.py`**: Creates/drops DB table in setUpClass/tearDownClass - not safe for parallel
2. **Transaction errors**: Some tests share database state improperly
3. **Missing tblib**: Error tracebacks can't be serialized without this library

## Key Bottlenecks Identified

### 1. Factory Usage (High Impact)
Heavy factory usage in setUp() creates DB overhead per test method:

| File | Factory Calls |
|------|---------------|
| test_models.py (integrations) | 118 |
| test_views.py (integrations) | 111 |
| test_quick_stats.py | 110 |
| test_insight_rules.py | 77 |
| test_tasks.py | 55 |

**Problem**: Each test method re-creates Team + User + Members + Objects in setUp().

### 2. Missing setUpTestData Usage (High Impact)
Only **3 test classes** use `setUpTestData()` vs **194 setUp()** calls.

`setUpTestData()` runs once per class vs setUp() running per test method.

### 3. Flaky Tests (Factory Collisions)
Test failure observed: `test_get_reviewer_workload_classifies_normal_workload`
```
IntegrityError: duplicate key value violates unique constraint "unique_team_email"
Key (team_id, email)=(89505, robert.keith@example.com) already exists.
```

**Root cause**: `TeamMemberFactory` uses `Faker("name")` for display_name, then derives email from it. Faker can repeat names across tests, causing collisions.

### 4. Large Test Files
| File | Lines | Tests |
|------|-------|-------|
| test_views.py | 2,086 | ~85 |
| test_models.py | 1,349 | ~50 |
| test_github_oauth.py | 1,187 | 48 |
| test_insight_rules.py | 1,093 | ~40 |
| test_quick_stats.py | 1,066 | ~40 |

## Optimization Strategies

### Phase 1: Quick Wins (Est. 30-40% speedup, Low risk)

#### 1.1 Make --keepdb the default
**Scope**: Modify Makefile test target
**Effort**: 5 minutes
**Impact**: Saves ~5-10s per run

```makefile
test: ## Run Django tests
	@uv run manage.py test --keepdb ${ARGS}
```

#### 1.2 Install tblib for better parallel debugging
**Scope**: Add to pyproject.toml
**Effort**: 5 minutes
**Impact**: Enables parallel test debugging

```toml
[dependency-groups]
dev = [
    # ... existing ...
    "tblib>=3.0.0",
]
```

#### 1.3 Fix TeamMemberFactory to use unique emails
**Scope**: apps/metrics/factories.py
**Effort**: 10 minutes
**Impact**: Eliminates random test failures

```python
class TeamMemberFactory(DjangoModelFactory):
    display_name = factory.Sequence(lambda n: f"Developer {n}")
    email = factory.Sequence(lambda n: f"developer{n}@example.com")
```

### Phase 2: Enable Parallel Execution (Est. 50-70% speedup, Medium risk)

#### 2.1 Fix test_fields.py for parallel compatibility
**Scope**: apps/utils/tests/test_fields.py
**Effort**: 30 minutes
**Options**:
- A) Use `@override_settings` with in-memory SQLite for this specific test
- B) Use pytest fixtures with database isolation
- C) Create the model through proper migration (adds complexity)

**Recommended**: Option A - least invasive

#### 2.2 Add tblib and verify parallel works
After fixing above:
```bash
make test-parallel ARGS='--keepdb'
```

Expected reduction: 125s → ~40-50s (with 4+ cores)

### Phase 3: Optimize Test Data Setup (Est. 20-30% additional speedup, Medium effort)

#### 3.1 Convert heavy setUp() to setUpTestData()
**Priority targets** (most Factory calls in setUp):
1. `test_views.py` (integrations) - 15 test classes
2. `test_quick_stats.py` - 1 class, many tests
3. `test_insight_rules.py` - 7 test classes
4. `test_chart_views.py` - 9 test classes

**Pattern transformation**:
```python
# Before
class TestViews(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, ...)

# After
class TestViews(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.admin = UserFactory()
        cls.team.members.add(cls.admin, ...)
```

**Important**: Only works when tests don't mutate shared data.

**Effort**: 2-4 hours for top priority files
**Impact**: Reduce redundant DB inserts by ~80% in those files

### Phase 4: Migrate to pytest-django (Est. 30-50% additional speedup, High effort)

#### Benefits:
- Better parallel execution with pytest-xdist (`-n auto`)
- `--reuse-db` flag for development
- Better fixture scoping (session, module, class, function)
- Better error reporting
- pytest-randomly for detecting test order dependencies

#### Requirements:
```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-django>=4.8",
    "pytest-xdist>=3.5",
    "pytest-randomly>=3.15",
    "tblib>=3.0.0",
]
```

#### Configuration (pyproject.toml):
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "tformance.settings"
python_files = ["test_*.py"]
addopts = [
    "--reuse-db",
    "-n", "auto",
    "--dist", "loadscope",
]
```

#### Migration Strategy:
Tests using `django.test.TestCase` work with pytest-django without changes.

Main changes needed:
- Add `conftest.py` with fixtures
- Replace `setUpTestData` with `@pytest.fixture(scope="class")`
- Handle any `self.client` → `client` fixture migrations

**Effort**: 1-2 days for full migration
**Risk**: Medium - some tests may need adjustment

## Recommended Execution Order

| Phase | Action | Time | Expected Speedup |
|-------|--------|------|------------------|
| 1.1 | Add --keepdb default | 5 min | 5-8% |
| 1.2 | Install tblib | 5 min | 0% (enables debugging) |
| 1.3 | Fix TeamMemberFactory | 10 min | Eliminates flakiness |
| 2.1 | Fix test_fields.py | 30 min | Enables parallel |
| 2.2 | Test parallel mode | 30 min | 50-70% |
| 3.1 | Convert to setUpTestData | 2-4 hrs | 10-20% additional |
| 4 | Migrate to pytest | 1-2 days | 10-30% additional |

## Expected Final State

| Metric | Current | After Phase 2 | After Phase 4 |
|--------|---------|---------------|---------------|
| Full suite time | 125s | ~45-60s | ~30-40s |
| With -n auto | N/A | ~30-40s | ~20-30s |
| Flaky tests | 1+ | 0 | 0 |

## Quick Test Commands

```bash
# Current (slow)
make test

# With keepdb (faster)
make test ARGS='--keepdb'

# Parallel (after fixes)
make test-parallel ARGS='--keepdb'

# Specific module (fast iteration)
.venv/bin/python manage.py test apps.module --keepdb -v0

# Future pytest
pytest -n auto --reuse-db
```

## References

- [Faster parallel pytest-django](https://iurisilv.io/2021/03/faster-parallel-pytest-django.html)
- [Making Django Tests Faster](https://schegel.net/posts/making-your-django-tests-faster/)
- [pytest-xdist documentation](https://pytest-with-eric.com/plugins/pytest-xdist/)
- [Django Test Optimization Tips](https://gauravvjn.medium.com/11-tips-for-lightning-fast-tests-in-django-effa87383040)
