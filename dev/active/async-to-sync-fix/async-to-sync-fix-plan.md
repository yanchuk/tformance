# async_to_sync Fix Implementation Plan

**Last Updated:** 2026-01-04

## Executive Summary

Fix incorrect `asyncio.run()` usage in Celery task modules and prevent future occurrences through documentation and automated linting. The bug causes silent database operation failures due to broken thread-local storage when `asyncio.run()` creates a new event loop.

## Problem Statement

**Root Cause:** `asyncio.run()` creates a new event loop which breaks Django's `@sync_to_async(thread_sensitive=True)` decorators' thread handling, causing database operations to **silently fail** (no errors, but data not saved) in:
- Celery workers
- Django views calling async code
- Signal handlers
- Middleware

**Current Bug Location:**
- `apps/integrations/_task_modules/pr_data.py:60` - Uses `asyncio.run()` instead of `async_to_sync()`

## Current State Analysis

### Correct Usage (Reference Pattern)
File: `apps/integrations/_task_modules/github_sync.py`
```python
from asgiref.sync import async_to_sync

# Run async function in sync context using async_to_sync (NOT asyncio.run!)
result = async_to_sync(sync_repository_history_graphql)(
    tracked_repo, days_back=days_back, skip_recent=skip_recent
)
```

### Incorrect Usage (Bug)
File: `apps/integrations/_task_modules/pr_data.py:60`
```python
import asyncio

# WRONG - breaks thread-local storage
result = asyncio.run(fetch_pr_complete_data_graphql(pr, tracked_repo))
```

### Safe Usages (No Fix Needed)
| Location | Context | Why Safe |
|----------|---------|----------|
| `apps/integrations/tests/test_github_graphql*.py` | Test code | Fresh process, isolated event loop |
| `apps/metrics/seeding/github_graphql_fetcher.py` | Seeding utility | Management command, fresh process |
| `apps/metrics/tests/test_github_graphql_fetcher.py` | Test code | Fresh process, isolated event loop |

## Implementation Phases

### Phase 1: TDD RED - Write Failing Test
**Objective:** Create a test that fails with current `asyncio.run()` usage

1. Create test file: `apps/integrations/tests/test_async_to_sync_celery.py`
2. Mock Celery task execution context
3. Verify `async_to_sync()` is used (not `asyncio.run()`)
4. Test should fail until fix is applied

### Phase 2: TDD GREEN - Fix the Bug
**Objective:** Minimal code change to make test pass

1. Edit `apps/integrations/_task_modules/pr_data.py`:
   - Replace `import asyncio` with `from asgiref.sync import async_to_sync`
   - Replace `asyncio.run(fetch_pr_complete_data_graphql(...))` with `async_to_sync(fetch_pr_complete_data_graphql)(...)`
2. Run test to confirm fix
3. Run full test suite to ensure no regressions

### Phase 3: TDD REFACTOR - Documentation & Prevention
**Objective:** Prevent this from happening again

1. Update CLAUDE.md:
   - Expand async warning scope (Celery, views, signals, middleware)
   - Add "Safe vs Unsafe" usage table
   - Add code review checklist item

2. Add pre-commit linter rule:
   - Create custom ruff rule or grep check
   - Flag `asyncio.run(` in `apps/**/*.py` (excluding tests and seeding)
   - Add to Makefile

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Silent failures in production | High (bug exists) | High | Fix immediately |
| Test doesn't catch pattern | Low | Medium | Use code inspection approach |
| Linter false positives | Medium | Low | Exclude safe directories |

## Success Metrics

1. **Bug Fixed:** `asyncio.run()` removed from all Celery task code paths
2. **Tests Pass:** All existing tests pass + new test for async pattern
3. **Documentation Updated:** CLAUDE.md has expanded guidelines
4. **Prevention Added:** Pre-commit check or linter rule catches future violations

## Critical Files

| File | Action |
|------|--------|
| `apps/integrations/_task_modules/pr_data.py` | FIX - Replace asyncio.run |
| `apps/integrations/_task_modules/github_sync.py` | REFERENCE - Correct pattern |
| `apps/integrations/tests/test_async_to_sync_celery.py` | CREATE - New test |
| `CLAUDE.md` | UPDATE - Expand async guidelines |
| `Makefile` | UPDATE - Add linter target |
