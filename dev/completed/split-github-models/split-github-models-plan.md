# Split GitHub Models Refactoring Plan

**Last Updated:** 2026-01-10
**Status:** PHASE 1 COMPLETE

## Executive Summary

Refactor the oversized `apps/metrics/models/github.py` (1,348 lines) into domain-specific model files to improve maintainability, readability, and adherence to the 200-300 line guideline.

## Current State (After Phase 1)

### Completed
- ✅ PullRequest extracted to `pull_requests.py` (449 lines)
- ✅ Dependent imports updated (surveys.py, deployments.py, jira.py)
- ✅ `__init__.py` re-exports preserved backward compatibility
- ✅ All 308 model tests pass
- ✅ All 2613 metrics tests pass

### Remaining in github.py (910 lines)

| Model | Lines | Domain |
|-------|-------|--------|
| `PRReview` | ~90 | Reviews |
| `PRCheckRun` | ~90 | CI/CD checks |
| `PRFile` | ~530 | File changes (large due to constants) |
| `PRComment` | ~100 | Comments |
| `Commit` | ~95 | Git commits |

## Phase 2: Optional Further Splitting

If desired, continue splitting:

```
apps/metrics/models/
├── __init__.py          # Re-exports
├── pull_requests.py     # ✅ DONE (449 lines)
├── reviews.py           # TODO: PRReview
├── check_runs.py        # TODO: PRCheckRun
├── files.py             # TODO: PRFile (530 lines)
├── comments.py          # TODO: PRComment
├── commits.py           # TODO: Commit
└── (delete github.py)   # TODO: when all extracted
```

### Import Dependencies

```
TeamMember (team.py)
    ↓
PullRequest (pull_requests.py) ← imports TeamMember ✅ DONE
    ↓
PRReview ← imports PullRequest, TeamMember
PRCheckRun ← imports PullRequest
PRFile ← imports PullRequest
PRComment ← imports PullRequest, TeamMember
Commit ← imports PullRequest, TeamMember
```

## Risk Assessment

| Risk | Status | Notes |
|------|--------|-------|
| Circular imports | ✅ Mitigated | Dependency order followed |
| Missing re-exports | ✅ Verified | `__all__` updated |
| Test failures | ✅ Passed | 308 model tests pass |
| Migration issues | ✅ N/A | No schema changes |

## Success Metrics (Phase 1)

- [x] All 177 importing files work without changes
- [x] All tests pass (no new failures)
- [x] github.py reduced from 1348 to 910 lines (32% reduction)
- [x] No circular import errors
- [x] Linting passes

## Verification Commands

```bash
# Quick verification
.venv/bin/pytest apps/metrics/tests/models/ -v --tb=short

# Full verification
make test
make ruff
make lint-team-isolation
```
