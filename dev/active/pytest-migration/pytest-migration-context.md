# pytest Migration Context

**Last Updated: 2025-12-22**

## Key Files

### Configuration Files
| File | Purpose |
|------|---------|
| `pyproject.toml` | Add pytest config and dependencies |
| `conftest.py` (new) | Root-level pytest fixtures |
| `Makefile` | Update test commands |
| `CLAUDE.md` | Update testing documentation |
| `.github/workflows/` | Update CI to use pytest |

### Test Files (no changes needed)
| Location | Count | Notes |
|----------|-------|-------|
| `apps/*/tests/*.py` | 110 | Django TestCase - works with pytest |
| `apps/*/tests/**/*.py` | 154 | Nested tests - works with pytest |

### Factory Files (no changes needed)
| File | Purpose |
|------|---------|
| `apps/metrics/factories.py` | Main factories |
| `apps/integrations/factories.py` | Integration factories |
| `apps/teams/factories.py` | Team factories |

## Key Decisions

### Decision 1: Configuration Location
**Chosen**: `pyproject.toml` with `[tool.pytest.ini_options]`
**Rationale**: Single config file, modern standard, already exists

### Decision 2: Fixture Strategy
**Chosen**: Gradual migration - create fixtures but don't require them
**Rationale**: Existing setUp methods continue to work

### Decision 3: Parallel Backend
**Chosen**: pytest-xdist with `-n auto`
**Rationale**: Automatically uses available CPU cores

### Decision 4: Keep Django Runner
**Chosen**: Keep `make test-django` as fallback
**Rationale**: Safety net during migration, TDD skills may use it

## Dependencies

### New Packages
```toml
[dependency-groups]
dev = [
    # Existing
    "channels[daphne]",
    "pre-commit",
    "ruff>=0.13.1",
    "pegasus-cli>=0.8",
    "tblib>=3.0.0",
    # New for pytest
    "pytest>=8.0",
    "pytest-django>=4.8",
    "pytest-xdist>=3.5",
    "pytest-randomly>=3.15",
    "pytest-cov>=4.1",
]
```

## Patterns to Follow

### pytest Configuration (pyproject.toml)
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "tformance.settings"
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--reuse-db",
    "--tb=short",
    "-ra",
]
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

### Root conftest.py
```python
import pytest
from django.test import Client

@pytest.fixture
def client():
    """Django test client."""
    return Client()

@pytest.fixture
def admin_client(admin_user):
    """Logged-in admin client."""
    client = Client()
    client.force_login(admin_user)
    return client

@pytest.fixture
def team(db):
    """Create a team for testing."""
    from apps.teams.factories import TeamFactory
    return TeamFactory()

@pytest.fixture
def user(db):
    """Create a user for testing."""
    from apps.integrations.factories import UserFactory
    return UserFactory()

@pytest.fixture
def team_member(team, user):
    """Create a team member."""
    from apps.metrics.factories import TeamMemberFactory
    return TeamMemberFactory(team=team)
```

### Makefile Commands
```makefile
test: ## Run tests with pytest
	@pytest ${ARGS}

test-parallel: ## Run tests in parallel
	@pytest -n auto ${ARGS}

test-slow: ## Show slowest tests
	@pytest --durations=20 ${ARGS}

test-coverage: ## Run with coverage
	@pytest --cov=apps --cov-report=term-missing ${ARGS}

test-django: ## Fallback to Django runner
	@uv run manage.py test --keepdb ${ARGS}
```

## Test Commands Reference

```bash
# Basic
pytest                           # Run all tests
pytest apps/metrics              # Run one app
pytest -k "test_quick"           # Run matching tests
pytest -x                        # Stop on first failure

# Parallelization
pytest -n auto                   # Auto-detect workers
pytest -n 4                      # Use 4 workers

# Timing and debugging
pytest --durations=10            # Show 10 slowest
pytest -v                        # Verbose output
pytest --tb=long                 # Full tracebacks
pytest --lf                      # Run last failed

# Coverage
pytest --cov=apps                # With coverage
pytest --cov-report=html         # HTML report

# Randomization
pytest -p randomly               # Random order
pytest -p randomly --randomly-seed=12345  # Reproducible
```

## Related Documentation

- [pytest-django docs](https://pytest-django.readthedocs.io/)
- [pytest-xdist docs](https://pytest-xdist.readthedocs.io/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Factory Boy + pytest](https://factoryboy.readthedocs.io/en/stable/recipes.html#using-factories-with-pytest)
