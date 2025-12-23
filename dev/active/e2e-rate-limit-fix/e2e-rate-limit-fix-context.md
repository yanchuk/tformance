# E2E Rate Limit Fix - Context

**Last Updated:** 2025-12-24
**Status:** IN PROGRESS - Fix identified, needs verification
**Branch:** `github-graphql-api` (uncommitted changes)

---

## Problem Statement

E2E tests fail with 4 workers due to **429 Too Many Requests** rate limiting.

### Root Cause

When Playwright runs with multiple workers, each worker performs a login in `beforeEach`. With 4 workers running 60 tests, that's ~240 login attempts in quick succession, hitting rate limits:

1. **allauth rate limits**: `login: '30/m/ip'` - 30 logins per minute per IP
2. **django-ratelimit**: `@ratelimit(key="user", rate="10/m")` on insights views

### Evidence

Screenshot from failed test shows **429 Too Many Requests** page:
- `test-results/analytics-Analytics-Pages--1789f--Team-page-loads-with-title-chromium/test-failed-1.png`

Server logs showed:
```
django_ratelimit.exceptions.Ratelimited
```

---

## Solution Implemented

**File:** `tformance/settings.py` (lines 293-296)

```python
# Disable rate limits in DEBUG mode for E2E testing (Playwright runs multiple workers)
if DEBUG:
    ACCOUNT_RATE_LIMITS = False  # Disable allauth rate limits (must be False, not {})
    RATELIMIT_ENABLE = False  # Disable django-ratelimit
```

### Key Discovery

- `ACCOUNT_RATE_LIMITS = {}` does NOT work - allauth checks `if rls is False`
- `ACCOUNT_RATE_LIMITS = False` correctly disables all allauth rate limits
- `RATELIMIT_ENABLE = False` disables django-ratelimit package

---

## Files Modified

| File | Change | Status |
|------|--------|--------|
| `tformance/settings.py` | Added rate limit disable for DEBUG | Uncommitted |

---

## Verification Steps

After fix, run:

```bash
# 1. Clear Redis cache (rate limits are cached)
docker exec tformance-redis-1 redis-cli FLUSHALL

# 2. Restart dev server with DEBUG=True
pkill -f "manage.py runserver"
DEBUG=True .venv/bin/python manage.py runserver &

# 3. Verify rate limits are disabled
DEBUG=True DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/python -c "
from allauth.account import app_settings
print('RATE_LIMITS:', app_settings.RATE_LIMITS)  # Should be {}
"

# 4. Run analytics tests with 4 workers
npx playwright test tests/e2e/analytics.spec.ts --project=chromium --workers=4

# 5. If passing, run full E2E suite
npx playwright test --project=chromium --workers=4
```

---

## Current State (Session End)

- Fix is implemented in settings.py (uncommitted)
- Redis cache was cleared
- Server was restarted
- Test run was interrupted before completion
- **Need to verify tests pass with 4 workers**

---

## Related Files

- `tests/e2e/analytics.spec.ts` - 60 tests for analytics pages
- `apps/insights/views.py` - Has `@ratelimit(key="user", rate="10/m")` decorators
- `apps/onboarding/views.py` - Has `@ratelimit(key="ip", rate="10/m")` decorators

---

## Commands Reference

```bash
# Check rate limit settings
DEBUG=True DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/python -c "
from django.conf import settings
from allauth.account import app_settings
print('RATELIMIT_ENABLE:', getattr(settings, 'RATELIMIT_ENABLE', 'NOT SET'))
print('allauth RATE_LIMITS:', app_settings.RATE_LIMITS)
"

# Clear Redis
docker exec tformance-redis-1 redis-cli FLUSHALL

# Run E2E tests
npx playwright test --project=chromium --workers=4
```
