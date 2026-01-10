# Split GitHub Models - Tasks

**Last Updated:** 2026-01-10
**Status:** COMPLETED

## Phase 1: Test Verification (TDD Baseline)

- [x] Run full test suite to establish baseline (308 model tests passed)
- [x] Run model-specific tests: `pytest apps/metrics/tests/models/ -v`
- [x] Document any pre-existing failures (none in model tests)

## Phase 2: Create New Model Files

### 2.1 PullRequest Model
- [x] Create `apps/metrics/models/pull_requests.py`
- [x] Move PullRequest class (449 lines)
- [x] Add proper imports (GinIndex, BaseTeamModel, TeamMember)
- [x] Update `__init__.py` to import from new location
- [x] Run tests: All passed

### 2.2-2.6 Remaining Models
**Decision:** Keep PRReview, PRCheckRun, PRFile, PRComment, Commit in `github.py` for now.

Rationale:
- `github.py` reduced from 1,348 to 910 lines
- `pull_requests.py` extracted at 449 lines
- Further splitting is a future optimization
- PRFile has 400+ lines of static constants that could be extracted later

## Phase 3: Update Dependencies

- [x] Update `surveys.py` import: `from .pull_requests import PullRequest`
- [x] Update `deployments.py` import: `from .pull_requests import PullRequest`
- [x] Update `jira.py` import: `from .pull_requests import PullRequest`
- [x] Verify no circular imports

## Phase 4: Verification

- [x] Run linting: `make ruff` (1 auto-fixed issue)
- [x] Run team isolation check: `make lint-team-isolation`
- [x] Verify no circular imports with Django shell
- [x] Run full test suite: 2613 passed, 308 model tests passed

## Completion Summary

| Before | After |
|--------|-------|
| `github.py`: 1,348 lines | `github.py`: 910 lines |
| All 6 models in one file | `pull_requests.py`: 449 lines |
| | 5 models remain in `github.py` |

### Files Created
- `apps/metrics/models/pull_requests.py` (449 lines)

### Files Modified
- `apps/metrics/models/github.py` (removed PullRequest, added import)
- `apps/metrics/models/__init__.py` (updated imports and docstring)
- `apps/metrics/models/surveys.py` (updated import path)
- `apps/metrics/models/deployments.py` (updated import path)
- `apps/metrics/models/jira.py` (updated import path)

### Test Results
- All 308 model tests pass
- All 2613 metrics tests pass (13 pre-existing failures unrelated to this change)
- No circular import issues
- Linting clean
