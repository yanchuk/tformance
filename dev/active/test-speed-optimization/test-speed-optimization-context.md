# Test Speed Optimization Context

**Last Updated: 2025-12-21**

## Key Files

### Configuration Files
| File | Purpose |
|------|---------|
| `Makefile` | Test commands (test, test-parallel) |
| `pyproject.toml` | Dependencies, will add pytest config |
| `tformance/settings.py` | Django settings |

### Factory Files
| File | Purpose |
|------|---------|
| `apps/metrics/factories.py` | TeamFactory, TeamMemberFactory, PullRequestFactory, etc. |
| `apps/integrations/factories.py` | UserFactory, GitHubIntegrationFactory, etc. |
| `apps/teams/factories.py` | Team-related factories |

### Problem Files (Need Fixing)
| File | Issue |
|------|-------|
| `apps/utils/tests/test_fields.py` | Creates/drops table in setUpClass - breaks parallel |
| `apps/metrics/factories.py:66-67` | Faker("name") causes email collisions |

### High-Impact Test Files (setUpTestData candidates)
1. `apps/integrations/tests/test_views.py` (111 factory calls, 15 classes)
2. `apps/integrations/tests/test_models.py` (118 factory calls, 6 classes)
3. `apps/metrics/tests/test_quick_stats.py` (110 factory calls, 1 class)
4. `apps/metrics/tests/test_insight_rules.py` (77 factory calls, 7 classes)
5. `apps/metrics/tests/test_chart_views.py` (36 factory calls, 9 classes)

## Key Decisions

### Decision 1: Fix Parallel First vs Pytest Migration
**Chosen**: Fix Django parallel first (Phase 2), then migrate to pytest (Phase 4)
**Rationale**: Lower risk, faster wins, validates test isolation before migration

### Decision 2: TeamMemberFactory Fix Approach
**Chosen**: Use factory.Sequence for display_name and email
**Rationale**: Guaranteed unique, deterministic, no Faker randomness

```python
# Before
display_name = factory.Faker("name")
email = factory.LazyAttribute(lambda o: f"{o.display_name.lower()...}")

# After
display_name = factory.Sequence(lambda n: f"Developer {n}")
email = factory.Sequence(lambda n: f"developer{n}@example.com")
```

### Decision 3: test_fields.py Parallel Fix
**Options Considered**:
- A) Use in-memory SQLite for this test only
- B) Create model via proper migration
- C) Use TransactionTestCase with isolated DB

**Chosen**: Option A - least invasive, isolated change

### Decision 4: setUpTestData Conversion Strategy
**Approach**: Convert only when tests don't mutate shared data
**Priority**: Files with >50 factory calls first

## Dependencies

### Current Test Dependencies
- `factory-boy>=3.3.3` (in pyproject.toml)
- Django's built-in test framework

### New Dependencies (to add)
```toml
[dependency-groups]
dev = [
    "tblib>=3.0.0",      # Phase 1: Traceback serialization
    "pytest>=8.0",        # Phase 4: Modern test runner
    "pytest-django>=4.8", # Phase 4: Django integration
    "pytest-xdist>=3.5",  # Phase 4: Parallel execution
    "pytest-randomly>=3.15", # Phase 4: Test order randomization
]
```

## Patterns to Follow

### setUp vs setUpTestData Pattern
```python
# setUp - runs before EACH test method (slow)
class MyTest(TestCase):
    def setUp(self):
        self.team = TeamFactory()  # Created N times for N tests

# setUpTestData - runs ONCE per class (fast)
class MyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()  # Created 1 time, shared
```

### Factory Best Practices
```python
# Use Sequence for unique fields
email = factory.Sequence(lambda n: f"user{n}@example.com")
github_id = factory.Sequence(lambda n: str(10000 + n))

# Use SubFactory with team reference
author = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
```

## Test Commands Reference

```bash
# Current
make test                           # Full run, creates new DB
make test ARGS='--keepdb'          # Reuse DB (faster)
make test-parallel ARGS='--keepdb' # Parallel (broken until Phase 2)

# Specific tests
.venv/bin/python manage.py test apps.module --keepdb -v0
.venv/bin/python manage.py test apps.module.tests.test_file::TestClass -v2

# Future (after Phase 4)
pytest -n auto --reuse-db
pytest apps/module -n 4
```

## Related Documentation

- [Django Testing docs](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [Factory Boy docs](https://factoryboy.readthedocs.io/)
- [pytest-django FAQ](https://pytest-django.readthedocs.io/en/latest/faq.html)
- [pytest-xdist docs](https://pytest-xdist.readthedocs.io/)
