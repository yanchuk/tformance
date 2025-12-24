# E2E Rate Limit Fix - Tasks

**Last Updated:** 2025-12-24
**Status:** Fix implemented, awaiting verification

---

## Investigation Phase - COMPLETE

- [x] Identify failing tests (analytics.spec.ts with 4 workers)
- [x] Check git status for recent changes
- [x] View screenshot from failed test
- [x] Find 429 Too Many Requests error
- [x] Identify allauth rate limits (`login: '30/m/ip'`)
- [x] Identify django-ratelimit on insights views
- [x] Discover `ACCOUNT_RATE_LIMITS = False` (not `{}`) is required

---

## Implementation Phase - COMPLETE

- [x] Add `ACCOUNT_RATE_LIMITS = False` to settings.py for DEBUG mode
- [x] Add `RATELIMIT_ENABLE = False` to settings.py for DEBUG mode
- [x] Clear Redis cache with `FLUSHALL`
- [x] Restart dev server

---

## Verification Phase - IN PROGRESS

- [ ] Verify allauth rate limits show `{}` at runtime
- [ ] Run analytics.spec.ts with 4 workers - expect 60 passed
- [ ] Run full E2E suite with 4 workers
- [ ] Run full E2E suite with all browsers (Chrome, Firefox, Safari)

---

## Cleanup Phase - PENDING

- [ ] Commit settings.py change
- [ ] Update QA test audit tasks file
- [ ] Document rate limit behavior in CLAUDE.md or dev docs

---

## Notes

### Why tests were passing before
The user reported tests worked before. Possible reasons:
1. Rate limit counters reset after time passed
2. Less tests were running (fewer login attempts)
3. Running with 1 worker (sequential)

### Production Safety
These settings only apply when `DEBUG=True`, so production is unaffected.
