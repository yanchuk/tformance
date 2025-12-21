# Fix code-style Tasks

**Last Updated:** 2025-12-21
**Status:** ✅ COMPLETE

## Summary

All lint issues have been fixed. `make ruff` passes with no errors.

## Completed Fixes

- [x] Remove unused `survey` variable in `test_survey_tokens.py:403`
- [x] Break long CSP lines in `middleware.py:53,54,57`
- [x] Add `from e` to raises in `decorators.py:45,53`
- [x] Simplify return in `decorators.py:79-81`
- [x] Remove `result =` in `apps/integrations/tests/test_github_comments.py:155`
- [x] Remove `all_avg =` in `apps/metrics/tests/test_security_isolation.py:288`
- [x] Add `from None` in `apps/metrics/services/survey_tokens.py:91`
- [x] Reorder imports in `apps/integrations/webhooks/slack_interactions.py:22-32`
- [x] Combine `with` at `apps/metrics/tests/test_pr_processor.py:349`
- [x] Combine `with` at `apps/metrics/tests/test_pr_processor.py:371`
- [x] Combine `with` at `apps/metrics/tests/test_pr_processor.py:394`

## Verification

```bash
make ruff              # ✅ All checks passed
make test ARGS='--keepdb'  # ✅ 1826 tests pass
```
