# Test Refactoring - Context & Key Information

**Last Updated:** 2024-12-30

---

## Source Documents

- **QA Review:** `dev/active/test-suite-qa-review.md`
- **Main Plan:** `dev/active/test-refactoring/test-refactoring-plan.md`
- **Tasks Checklist:** `dev/active/test-refactoring/test-refactoring-tasks.md`

---

## Key Files to Modify

### Phase 1: Foundation

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/metrics/tests/dashboard/test_deployment_metrics.py` | Deployment tests | Fix naive datetime |
| `apps/metrics/tests/test_trends_views.py` | Trends tests | Fix naive datetime |
| `apps/metrics/tests/test_seeding/test_data_generator.py` | Data gen tests | Add `@pytest.mark.slow` |
| `apps/teams/tests/test_roles.py` | Role tests | Replace `setUpClass` |
| `apps/utils/test_utils.py` | NEW | Create test utilities |

### Phase 2: Dashboard Service Coverage

| File | Purpose | Status |
|------|---------|--------|
| `apps/metrics/services/dashboard_service.py` | Source file (1,788 lines) | Untested |
| `apps/metrics/tests/dashboard/test_key_metrics.py` | NEW | TDD tests for key metrics |
| `apps/metrics/tests/dashboard/test_ai_metrics.py` | NEW | TDD tests for AI metrics |
| `apps/metrics/tests/dashboard/test_team_metrics.py` | NEW | TDD tests for team metrics |
| `apps/metrics/tests/dashboard/test_pr_metrics.py` | NEW | TDD tests for PR metrics |

### Phase 3: E2E Reliability

| File | Lines | Waits to Fix |
|------|-------|--------------|
| `tests/e2e/alpine-htmx-integration.spec.ts` | 235 | 15+ |
| `tests/e2e/analytics.spec.ts` | 1,090 | Many |
| `tests/e2e/accessibility.spec.ts` | 226 | 2 |
| `tests/e2e/smoke.spec.ts` | 60 | 1 |

### Phase 4: Auth & Models

| File | Purpose | Status |
|------|---------|--------|
| `apps/auth/views.py` | OAuth views (596 lines) | Untested |
| `apps/auth/tests/test_oauth_views.py` | NEW | TDD OAuth tests |
| `apps/metrics/models/github.py` | PR models (1,071 lines) | Untested |
| `apps/metrics/tests/models/test_pull_request_methods.py` | NEW | TDD model tests |
| `apps/integrations/views/github.py` | Webhook views | Untested |
| `apps/integrations/tests/test_views.py` | NEW | TDD view tests |

### Phase 5: Factories

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/metrics/factories.py` | Main factories | Remove `random` usage |
| `apps/integrations/factories.py` | Integration factories | Review for determinism |

---

## Key Functions to Test (Dashboard Service)

### Key Metrics (Task 2.1)
```python
get_key_metrics(team, start_date, end_date) -> dict
get_metrics_trend(team, days) -> dict
_calculate_change_and_trend(current, previous) -> tuple
_get_key_metrics_cache_key(team, start, end) -> str
```

### AI Metrics (Task 2.2)
```python
get_ai_adoption_trend(team, start_date, end_date) -> list
get_ai_tool_breakdown(team, start_date, end_date) -> dict
get_ai_quality_comparison(team, start_date, end_date) -> dict
get_ai_detective_leaderboard(team, limit=10) -> list
_calculate_ai_percentage(ai_count, total) -> float
```

### Team Metrics (Task 2.3)
```python
get_team_breakdown(team, start_date, end_date) -> list
get_copilot_by_member(team, start_date, end_date) -> list
get_copilot_metrics(team, start_date, end_date) -> dict
get_copilot_trend(team, days) -> list
```

### PR Metrics (Task 2.4)
```python
get_cycle_time_trend(team, days, granularity) -> list
get_pr_size_distribution(team, start_date, end_date) -> dict
get_pr_type_breakdown(team, start_date, end_date) -> dict
get_recent_prs(team, limit=10) -> list
get_sparkline_data(team, days) -> dict
```

---

## Test Patterns to Follow

### Factory Usage (from factories.py docstring)
```python
# GOOD - all objects share the same team (1 team created)
team = TeamFactory()
member = TeamMemberFactory(team=team)
pr = PullRequestFactory(team=team, author=member)

# BAD - each factory creates its own team (3 teams created!)
member = TeamMemberFactory()
pr = PullRequestFactory()
```

### Timezone-Aware Dates
```python
# GOOD - timezone aware
from django.utils import timezone
pr_date = timezone.make_aware(datetime(2024, 1, 15, 12, 0))
# or
pr_date = timezone.now() - timedelta(days=7)

# BAD - naive datetime
pr_date = datetime(2024, 1, 15, 12, 0)  # RuntimeWarning!
```

### E2E Wait Patterns
```typescript
// BAD - hardcoded wait
await page.waitForTimeout(2000);
await expect(element).toBeVisible();

// GOOD - conditional wait
await expect(element).toBeVisible({ timeout: 5000 });

// GOOD - wait for network
await page.waitForResponse(resp => resp.url().includes('/api/'));

// GOOD - wait for load state
await page.waitForLoadState('networkidle');
```

### Test Naming Convention
```python
def test_<function>_<scenario>_<expected_result>(self):
    """Test that <function> <does what> when <scenario>."""
```

Examples:
- `test_get_key_metrics_returns_dict_with_required_keys`
- `test_get_key_metrics_filters_by_date_range`
- `test_get_key_metrics_handles_empty_data`
- `test_get_key_metrics_calculates_trend_correctly`

---

## Current Test Counts

| Category | Count |
|----------|-------|
| Total Tests | 3,879 |
| Unit/Integration Files | 199 |
| E2E Spec Files | 22 |
| Slow Tests (>2s) | ~10 |
| Timezone Warnings | 1,635 |
| Hardcoded E2E Waits | 468 |

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| TDD mandatory | Project standard, ensures quality |
| Phase order | Foundation first, then critical coverage |
| E2E fixes parallel | Independent of Python tests |
| Factory determinism | Reproducible test runs |

---

## Dependencies

### Python Packages (already installed)
- pytest
- pytest-django
- pytest-xdist
- factory-boy
- freezegun (for time-sensitive tests)

### Node Packages (already installed)
- @playwright/test

---

## Commands Reference

```bash
# Run all tests
make test

# Run specific test file
pytest apps/metrics/tests/dashboard/test_key_metrics.py -v

# Run tests matching pattern
pytest -k "test_key_metrics" -v

# Run with coverage
make test-coverage

# Run E2E tests
make e2e

# Run single E2E file
npx playwright test tests/e2e/analytics.spec.ts

# Skip slow tests
pytest -m "not slow"

# Show slowest tests
pytest --durations=20
```

---

## Notes

- All new test files should have docstrings explaining scope
- Use factories for ALL test data creation
- Prefer `build()` over `create()` for unit tests
- Always run full test suite before committing
- E2E tests should be run 3x to verify no flakiness
