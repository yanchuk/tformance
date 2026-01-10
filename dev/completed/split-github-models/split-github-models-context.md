# Split GitHub Models - Context

**Last Updated:** 2026-01-10
**Status:** PHASE 1 COMPLETE - PullRequest extracted

## Current Implementation State

### Completed Work
1. **PullRequest model extracted** to `apps/metrics/models/pull_requests.py` (449 lines)
2. **Dependent imports updated** in surveys.py, deployments.py, jira.py
3. **`__init__.py` updated** with new import paths and docstring
4. **All tests passing** - 308 model tests, 2613 total metrics tests

### File Status After Refactoring

| File | Lines | Status |
|------|-------|--------|
| `pull_requests.py` | 449 | NEW - PullRequest model |
| `github.py` | 910 | MODIFIED - 5 models remain |
| `__init__.py` | 64 | MODIFIED - updated imports |
| `surveys.py` | 211 | MODIFIED - import path |
| `deployments.py` | 98 | MODIFIED - import path |
| `jira.py` | 161 | MODIFIED - import path |

## Key Decisions Made This Session

1. **Partial extraction approach**: Only extracted PullRequest first since it's the core entity all other models depend on via ForeignKey

2. **Keep remaining models in github.py**: PRReview, PRCheckRun, PRFile, PRComment, Commit remain in `github.py` (910 lines). Further splitting is optional future work.

3. **No migrations needed**: Pure Python refactoring - no schema changes, no migrations required

4. **Import via __init__.py**: All external imports use `from apps.metrics.models import PullRequest` which is preserved through `__init__.py` re-exports

## Critical Import Pattern

```python
# Inside models/ directory - use relative imports
from .pull_requests import PullRequest  # For other model files
from .team import TeamMember

# Outside models/ directory - use __init__.py re-exports
from apps.metrics.models import PullRequest  # Works unchanged
```

## Files That Import Directly from github.py

These were updated:
- `apps/metrics/models/surveys.py:7` → changed to `.pull_requests`
- `apps/metrics/models/deployments.py:7` → changed to `.pull_requests`
- `apps/metrics/models/jira.py:158` → changed to `.pull_requests` (deferred import in method)

## Test Verification Commands

```bash
# Verify model tests pass
.venv/bin/pytest apps/metrics/tests/models/ -v --tb=short

# Verify no circular imports
.venv/bin/python manage.py shell -c "from apps.metrics.models import PullRequest, PRReview, PRCheckRun, PRFile, PRComment, Commit; print('OK')"

# Run broader metrics tests
.venv/bin/pytest apps/metrics/tests/ -v -q
```

## Next Steps (Future Optimization)

If continuing the split:
1. Extract `files.py` - PRFile model (~530 lines with constants)
2. Extract `reviews.py` - PRReview model (~90 lines)
3. Extract `check_runs.py` - PRCheckRun (~90 lines)
4. Extract `comments.py` - PRComment (~100 lines)
5. Extract `commits.py` - Commit (~95 lines)
6. Delete `github.py` entirely

## Broader Project Improvements Identified

From the initial analysis (see `/Users/yanchuk/.claude/plans/wild-drifting-flute.md`):

### LLM Accuracy Issues (High Priority)
1. ✅ **Schema validation not called** - FIXED 2026-01-10 - Added `validate_insight_response()` call
2. **Dual prompt representations** - hardcoded string vs Jinja2 templates can drift
3. **No token counting** - uses heuristic limits, not actual token counts

### Code Quality Issues
1. ✅ **github.py oversized** - DONE (partially, reduced from 1348 to 910)
2. `integrations/models.py` (809 lines) - needs splitting
3. N+1 queries in `tasks.py:8-10`

### Testing Issues
1. CI tests disabled in `.github/workflows/tests.yml`
2. Missing tests for `apps/content/` and `apps/pullrequests/`

## No Uncommitted Changes Warning

All changes from this session are saved to disk but NOT committed. Run:
```bash
git status  # See changes
git diff    # Review changes
```

To commit:
```bash
git add apps/metrics/models/
git commit -m "refactor(models): extract PullRequest to separate file

Split oversized github.py (1348 lines) into:
- pull_requests.py (449 lines) - PullRequest model
- github.py (910 lines) - remaining models

No schema changes, no migrations needed.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
