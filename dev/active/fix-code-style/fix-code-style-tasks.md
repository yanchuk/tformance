# Fix code-style Tasks

**Last Updated:** 2025-12-13

## Progress Summary

- Total Tasks: 12
- Completed: 4
- Remaining: 8

## Phase 1: Already Fixed

- [x] Remove unused `survey` variable in `test_survey_tokens.py:403`
- [x] Break long CSP lines in `middleware.py:53,54,57`
- [x] Add `from e` to raises in `decorators.py:45,53`
- [x] Simplify return in `decorators.py:79-81`

## Phase 2: Remaining Lint Fixes

### F841 - Unused Variables
- [ ] Remove `result =` in `apps/integrations/tests/test_github_comments.py:155`
- [ ] Remove `all_avg =` in `apps/metrics/tests/test_security_isolation.py:288`

### B904 - Exception Chaining
- [ ] Add `from None` in `apps/metrics/services/survey_tokens.py:91`

### E402 - Import Order
- [ ] Reorder imports in `apps/integrations/webhooks/slack_interactions.py:22-32`

### SIM117 - Nested With Statements
- [ ] Combine `with` at `apps/metrics/tests/test_pr_processor.py:349`
- [ ] Combine `with` at `apps/metrics/tests/test_pr_processor.py:371`
- [ ] Combine `with` at `apps/metrics/tests/test_pr_processor.py:394`

## Phase 3: Verification

- [ ] Run `make ruff` - passes
- [ ] Run `pre-commit run --all-files` - passes
- [ ] Run `make test ARGS='--keepdb'` - passes
- [ ] Commit and push
- [ ] GitHub Actions `code-style` job passes

## Notes

- The E402 fix requires careful handling to avoid circular imports
- SIM117 fixes are purely stylistic and safe
- F841 fixes in tests just remove unused assignments
