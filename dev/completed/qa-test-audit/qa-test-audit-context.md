# QA Test Audit - Context

**Last Updated:** 2025-12-23
**Status:** Planning Complete, Ready for Implementation

---

## Key Files Reference

### E2E Test Files

| File | Purpose | Priority |
|------|---------|----------|
| `tests/e2e/integrations.spec.ts` | **CRITICAL REWRITE** - Integration page flows | P1 |
| `tests/e2e/onboarding.spec.ts` | Onboarding flow - needs review | P1 |
| `tests/e2e/surveys.spec.ts` | PR survey flows - extend | P1 |
| `tests/e2e/analytics.spec.ts` | Analytics pages - good | - |
| `tests/e2e/dashboard.spec.ts` | Dashboard - potential overlap | P3 |

### Unit Test Directories

| Directory | Tests | Notes |
|-----------|-------|-------|
| `apps/metrics/tests/` | 1,170 | Well covered |
| `apps/metrics/tests/dashboard/` | ~200 | Service tests |
| `apps/metrics/tests/models/` | ~100 | Model tests |
| `apps/metrics/tests/test_seeding/` | ~50 | Mark as slow |
| `apps/integrations/tests/` | 956 | Well covered |
| `apps/integrations/tests/github_sync/` | ~100 | Sync logic |

### PRD User Flows Reference

| Flow | PRD Location | Test Coverage |
|------|--------------|---------------|
| Sign Up | ONBOARDING.md Step 1 | auth.spec.ts |
| GitHub Connect | ONBOARDING.md Step 2 | **MISSING** |
| Repo Selection | ONBOARDING.md Step 3 | **MISSING** |
| Jira Connect | ONBOARDING.md Step 4 | **MISSING** |
| Slack Connect | ONBOARDING.md Step 5 | **MISSING** |
| Initial Sync | ONBOARDING.md Step 6 | **MISSING** |
| CTO Dashboard | PRD-MVP.md Section 6 | analytics.spec.ts |
| Developer View | PRD-MVP.md Section 6 | **PARTIAL** |
| Reviewer Survey | PRD-MVP.md Section 6 | surveys.spec.ts |
| AI Detective | PRD-MVP.md Section 6 | **MISSING** |

---

## Key Decisions

### D1: E2E Test Rewrite Priority
**Decision:** Rewrite `integrations.spec.ts` as highest priority
**Rationale:** Current tests have fake assertions (`expect(true).toBeTruthy()`)
**Impact:** 90 lines → 250+ lines of real tests

### D2: Slow Test Markers
**Decision:** Use `@pytest.mark.slow` and `@pytest.mark.integration` markers
**Rationale:** Speed up default test runs, run slow tests separately in CI
**Impact:** Test run time reduced by ~30%

### D3: E2E Overlap Consolidation
**Decision:** Keep analytics.spec.ts as primary, remove duplicates from dashboard.spec.ts
**Rationale:** analytics.spec.ts is newer and more comprehensive
**Impact:** Reduce test maintenance burden

### D4: OAuth Testing Strategy
**Decision:** Use mocked OAuth responses for E2E tests
**Rationale:** Real OAuth requires manual intervention
**Impact:** Tests can run in CI without manual steps

---

## Test Patterns to Follow

### Factory Usage (Unit Tests)
```python
from apps.metrics.factories import PullRequestFactory, TeamMemberFactory

class TestFeature(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_something(self):
        pr = PullRequestFactory(team=self.team, author=self.member)
        # assertions...
```

### E2E Test Pattern
```typescript
test.describe('Feature Tests @feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test('user can do action', async ({ page }) => {
    await page.goto('/app/feature/');
    await expect(page.getByRole('heading', { name: 'Feature' })).toBeVisible();
    // Real assertions, not typeof checks
  });
});
```

### Slow Test Marker
```python
import pytest

@pytest.mark.slow
class TestRealProjectSeeding(TestCase):
    """Tests that require network access or significant time."""
    pass
```

---

## Commands

```bash
# Run all unit tests
make test

# Run specific app tests
.venv/bin/pytest apps/metrics/tests/ -v

# Run E2E tests (all browsers)
npx playwright test

# Run E2E tests (chromium only, fast)
npx playwright test --project=chromium

# Run specific E2E file
npx playwright test tests/e2e/integrations.spec.ts

# Run with coverage
make test-coverage

# Find tests without real assertions (E2E)
grep -r "expect(true)" tests/e2e/

# Find skipped tests
grep -r "@pytest.mark.skip" apps/*/tests/
```

---

## Dependencies

### For E2E Tests
- Dev server running on localhost:8000
- Demo data seeded
- Test user credentials: admin@example.com / admin123

### For OAuth E2E Tests (if implemented)
- Mock server or OAuth bypass mechanism
- Test OAuth app credentials (dev environment only)

---

## Related Documentation

- `prd/PRD-MVP.md` - User stories and features
- `prd/ONBOARDING.md` - Complete onboarding flow
- `prd/DASHBOARDS.md` - Dashboard specifications
- `CLAUDE.md` - TDD workflow and testing guidelines
