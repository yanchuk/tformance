# Test Refactoring - Context & Key Information

**Last Updated:** 2024-12-30 (Session 4)
**Current Status:** Phase 1 ✅, Phase 2 ✅, Phase 3 IN PROGRESS

---

## Session 4 Summary (Current)

### Completed This Session

**Phase 3: E2E Reliability - IN PROGRESS**

Replaced hardcoded `waitForTimeout` calls with conditional waits:

| File | Waits Replaced | Status |
|------|----------------|--------|
| `alpine-htmx-integration.spec.ts` | 13 | ✅ Tests pass 3/3 |
| `analytics.spec.ts` | 42 | ✅ Tests pass 2/2 (500 tests) |
| Remaining files | ~123 | Pending |

### E2E Wait Helper Functions

Created reusable helpers for conditional waits:

```typescript
// Wait for Alpine.js store to be initialized
async function waitForAlpineStore(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => {
      const Alpine = (window as any).Alpine;
      return Alpine && Alpine.store && Alpine.store('dateRange') !== undefined;
    },
    { timeout }
  );
}

// Wait for HTMX request to complete
async function waitForHtmxComplete(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout }
  );
}

// Wait for chart canvas to be present
async function waitForChart(page: Page, chartId: string, timeout = 5000): Promise<void> {
  await page.waitForSelector(`#${chartId}`, { state: 'attached', timeout });
  await waitForHtmxComplete(page, timeout);
}
```

### Commits Made This Session

1. `99ce708` - Replace hardcoded waits in analytics.spec.ts

---

## Previous Sessions Summary

### Session 3: Phase 2 Dashboard Tests

Added **89 new TDD tests** for previously untested dashboard functions:

| Test File | Tests | Functions Covered |
|-----------|-------|-------------------|
| `test_sparkline_data.py` | 16 | `get_sparkline_data()` |
| `test_ai_detective_leaderboard.py` | 17 | `get_ai_detective_leaderboard()` |
| `test_trend_comparison.py` | 28 | `get_trend_comparison()`, monthly/weekly trends |
| `test_pr_type_breakdown.py` | 14 | `get_pr_type_breakdown()` |
| `test_ai_bot_reviews.py` | 14 | `get_ai_bot_review_stats()` |

**Dashboard test total: 310 tests (221 existing + 89 new)**

### Session 2: Phase 1 Foundation

1. Created `apps/utils/date_utils.py` for timezone-aware filtering
2. Fixed test isolation in `test_roles.py`
3. Marked slow tests with `@pytest.mark.slow`

---

## Database Deadlock Mitigation

When running tests in parallel, database deadlocks can occur. Solutions:

### Option 1: Run Tests Serially (Recommended for CI stability)
```bash
make test-serial  # Runs with -p no:xdist
```

### Option 2: Reduce Parallelism
```bash
pytest -n 2  # Use fewer workers instead of auto
```

### Option 3: Use pytest-django Transaction Isolation
```python
# In conftest.py or test class
@pytest.mark.django_db(transaction=True)
class TestMyFeature:
    ...
```

### Option 4: loadfile Distribution (Group tests by file)
```bash
pytest --dist=loadfile  # Tests from same file run on same worker
```

### Current Project Configuration

The project uses `pytest-xdist` with auto workers. For stability:
- Production CI should use `make test` (parallel)
- If flaky, fall back to `make test-serial`
- E2E tests run separately via Playwright

---

## E2E Wait Pattern Guidelines

### Replace These Patterns:

```typescript
// ❌ BAD: Hardcoded timeout
await page.waitForTimeout(500);

// ✅ GOOD: Wait for specific condition
await waitForAlpineStore(page);
await waitForHtmxComplete(page);
await expect(element).toBeVisible({ timeout: 5000 });
await page.waitForURL(/pattern/);
```

### When Waiting for HTMX Content:
```typescript
// Wait for element that appears after HTMX load
await expect(page.getByRole('heading', { name: 'Title' })).toBeVisible({ timeout: 10000 });
```

### When Waiting for Charts:
```typescript
// Charts need longer timeouts
await expect(page.locator('#chart-canvas')).toBeAttached({ timeout: 10000 });
```

---

## Current Test Counts

| Category | Count | Status |
|----------|-------|--------|
| Dashboard Tests | 310 | ✅ All passing |
| E2E Analytics | 500 | ✅ All passing |
| E2E Alpine-HTMX | 48 | ✅ All passing |
| Total waitForTimeout remaining | ~123 | Pending |

---

## Commands Reference

```bash
# Run all tests
make test

# Run tests serially (avoid deadlocks)
make test-serial

# Run E2E tests
make e2e

# Run specific E2E file
npx playwright test tests/e2e/analytics.spec.ts

# Check remaining waits
grep -rn "waitForTimeout" tests/e2e/*.spec.ts | wc -l
```

---

## Next Steps

1. **Phase 3.3:** Fix remaining E2E files with waitForTimeout:
   - `htmx-navigation.spec.ts` (24 waits)
   - `interactive.spec.ts` (21 waits)
   - Other files with fewer waits

2. **Phase 4:** Auth & Models TDD coverage

3. **Phase 5:** Factory & Performance optimization

---

## Handoff Notes

**Last action:** Committed analytics.spec.ts E2E fixes.

**Uncommitted changes:** None - all committed.

**To verify on restart:**
```bash
# E2E tests
npx playwright test tests/e2e/analytics.spec.ts --reporter=list | tail -5

# Dashboard tests
.venv/bin/pytest apps/metrics/tests/dashboard/ --tb=short | tail -5
```
