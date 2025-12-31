# E2E Test Refactor - Context

**Last Updated**: 2025-12-31

---

## Key Files

### Test Files to Modify
| File | Lines | Issue |
|------|-------|-------|
| `tests/e2e/smoke.spec.ts` | 70 | Failing, needs enhancement |
| `tests/e2e/repo-selector.spec.ts` | 653 | 29 conditional skips, 2 hardcoded waits |
| `tests/e2e/analytics.spec.ts` | 1,122 | Duplicate helpers, no fixtures |
| `tests/e2e/dashboard.spec.ts` | 181 | No fixtures |
| `tests/e2e/feedback.spec.ts` | 312 | No fixtures |
| `tests/e2e/integrations.spec.ts` | 374 | Limited coverage |

### Files to Create
| File | Purpose |
|------|---------|
| `tests/e2e/helpers/index.ts` | Export all helpers |
| `tests/e2e/helpers/htmx.ts` | HTMX wait helpers |
| `tests/e2e/helpers/alpine.ts` | Alpine.js helpers |
| `tests/e2e/helpers/charts.ts` | Chart.js helpers |
| `tests/e2e/pr-list.spec.ts` | New - PR list page tests |

### Existing Fixtures (Underused)
| File | Provides |
|------|----------|
| `tests/e2e/fixtures/test-fixtures.ts` | `authenticatedPage`, `dashboardPage`, etc. |
| `tests/e2e/fixtures/test-users.ts` | `loginAs()`, `logout()`, `TEST_USERS` |

---

## Related Worktree Tasks

### Active Worktrees
1. **dashboard-insights** (`feature/dashboard-insights`)
   - Has `get_velocity_comparison` tests in main but implementation in worktree
   - Causing 8 test failures on main
   - **Action**: Wait for merge, then delete orphaned tests if not merged

2. **code-structure-cleanup** (`code-structure-cleanup`)
   - Code organization improvements
   - May affect test imports

3. **personal-notes** (`feature/personal-notes`)
   - New feature with its own tests
   - Independent of E2E refactor

### Integration Strategy
After worktree branches merge:
1. Rebase/merge changes into main
2. Run full test suite to verify
3. Apply E2E refactor patterns to any new test files

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Exclude external scripts from asset check | PostHog failures are false positives |
| Create helpers module vs extending fixtures | Helpers are stateless, easier to share |
| Use describe.skip vs inline test.skip | More deterministic test results |
| Add PR list tests | Critical user flow missing coverage |
| Defer multi-browser CI | Separate infrastructure concern |

---

## Dependencies

### Technical
- Playwright 1.40+
- Node.js 18+
- TypeScript 5+

### Data
- Test database with seeded admin user
- Demo data for PR list tests

### Services
- Dev server running on localhost:8000

---

## Commands Reference

```bash
# Run all E2E tests (Chromium only)
make e2e

# Run smoke tests
make e2e-smoke

# Run specific test file
npx playwright test smoke.spec.ts

# Run with UI for debugging
npx playwright test --ui

# Check for anti-patterns
grep -r "waitForTimeout" tests/e2e/
grep -r "test.skip()" tests/e2e/

# Run tests with specific tag
npx playwright test --grep @smoke
```

---

## Test User Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@example.com | admin123 |

---

## Known Issues

1. **PostHog script blocked** - Causes false positive in asset check
2. **Conditional skips** - 29 in repo-selector.spec.ts based on runtime data
3. **Duplicate helpers** - `waitForHtmxComplete` defined 15 times
4. **Low fixture adoption** - Only 8/25 files use shared fixtures
5. **Orphaned tests** - `test_velocity_comparison.py` tests for unimplemented function
