# Fix GitHub Actions code-style Job

**Last Updated:** 2025-12-13

## Executive Summary

The GitHub Actions `code-style` job in the `tests.yml` workflow is failing due to ruff linting errors. This job runs pre-commit hooks which include `ruff check` and `ruff format`. The failures prevent PRs from being merged and indicate code quality issues that should be resolved.

## Current State Analysis

### Failing Job
- **Workflow:** `Run Django Tests` (`tests.yml`)
- **Job:** `code-style`
- **Step:** `Run pre-commit hooks`
- **Exit Code:** 1 (16 errors found)

### Error Categories

| Code | Count | Description | Severity |
|------|-------|-------------|----------|
| F841 | 3 | Unused variable assignments | Medium |
| E402 | 3 | Module imports not at top of file | Low |
| B904 | 3 | Missing `raise ... from` in except | Medium |
| SIM117 | 3 | Nested `with` statements | Low |
| SIM103 | 1 | Can simplify return condition | Low |
| E501 | 3 | Line too long (>120 chars) | Low |

### Affected Files

1. `apps/metrics/tests/test_survey_tokens.py` - F841 (unused `survey`)
2. `apps/metrics/tests/test_security_isolation.py` - F841 (unused `all_avg`)
3. `apps/integrations/tests/test_github_comments.py` - F841 (unused `result`)
4. `apps/utils/middleware.py` - E501 (3 long lines)
5. `apps/web/decorators.py` - B904 (2x), SIM103
6. `apps/metrics/services/survey_tokens.py` - B904
7. `apps/integrations/webhooks/slack_interactions.py` - E402 (3x)
8. `apps/metrics/tests/test_pr_processor.py` - SIM117 (3x)

## Proposed Solution

Fix all ruff lint errors by:
1. Removing unused variable assignments or using `_` prefix
2. Reordering imports to top of file
3. Adding `from err` or `from None` to exception raises
4. Combining nested `with` statements
5. Simplifying return conditions
6. Breaking long lines

## Implementation Plan

### Phase 1: Already Fixed (in working directory)
- [x] `apps/metrics/tests/test_survey_tokens.py:403` - Remove `survey =`
- [x] `apps/utils/middleware.py:53,54,57` - Break into multiple lines
- [x] `apps/web/decorators.py:45,53` - Add `from e`
- [x] `apps/web/decorators.py:79-81` - Simplify return

### Phase 2: Remaining Fixes
1. `apps/integrations/tests/test_github_comments.py:155` - Remove `result =`
2. `apps/metrics/tests/test_security_isolation.py:288` - Remove `all_avg =`
3. `apps/metrics/services/survey_tokens.py:91` - Add `from None`
4. `apps/integrations/webhooks/slack_interactions.py:22-32` - Reorder imports
5. `apps/metrics/tests/test_pr_processor.py:349,371,394` - Combine `with` statements

### Phase 3: Verification
1. Run `make ruff` locally
2. Run `pre-commit run --all-files`
3. Commit and push
4. Verify GitHub Actions passes

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tests fail after changes | High | Run test suite before commit |
| Import reordering breaks circular imports | Medium | Check import dependencies |
| Logic change in return simplification | Low | Already tested locally |

## Success Metrics

- [ ] `make ruff` passes locally
- [ ] `pre-commit run --all-files` passes
- [ ] GitHub Actions `code-style` job passes
- [ ] All tests still pass
