# async_to_sync Fix - Tasks

**Last Updated:** 2026-01-04

## Phase 1: TDD RED - Write Failing Test

- [x] **1.1** Create test file `apps/integrations/tests/test_async_to_sync_celery.py`
- [x] **1.2** Write test that verifies `async_to_sync` is used in `_fetch_pr_core_data_with_graphql_or_rest`
- [x] **1.3** Run test and confirm it fails with current code

## Phase 2: TDD GREEN - Fix the Bug

- [x] **2.1** Edit `apps/integrations/_task_modules/pr_data.py`:
  - Replaced `import asyncio` with `from asgiref.sync import async_to_sync`
  - Replaced `asyncio.run(fetch_pr_complete_data_graphql(...))` with `async_to_sync(fetch_pr_complete_data_graphql)(...)`
- [x] **2.2** Add comment explaining why async_to_sync is required
- [x] **2.3** Run new test - passed
- [x] **2.4** Run related test suite: 73 tests passed
- [x] **2.5** Verified no regressions

## Phase 3: Documentation & Prevention

### 3A: Update CLAUDE.md
- [x] **3A.1** Expand async warning scope to include views, signals, middleware
- [x] **3A.2** Add "Safe vs Unsafe" usage table
- [x] **3A.3** Add code review checklist item for async patterns
- [x] **3A.4** Add lint-asyncio reference in documentation

### 3B: Add Linter/Check
- [x] **3B.1** Add `lint-asyncio` target to Makefile
- [x] **3B.2** Create grep pattern to find `asyncio.run(` in non-test, non-seeding files
- [x] **3B.3** Test linter passes (after fix)
- [x] **3B.4** Add lint-asyncio to the `lint` aggregate target

## Verification Checklist

- [x] All tests pass: `make test` (new tests)
- [x] New test exists and passes: `test_async_to_sync_celery.py`
- [x] No `asyncio.run(` in Celery task modules (except comments)
- [x] CLAUDE.md updated with expanded guidelines
- [x] Linter target added to Makefile: `make lint-asyncio`

## Acceptance Criteria - ALL MET

1. **Bug Fixed**: `asyncio.run()` replaced with `async_to_sync()` in `pr_data.py` ✅
2. **Test Coverage**: New test verifies correct async pattern usage ✅
3. **Documentation**: CLAUDE.md has clear, expanded async guidelines ✅
4. **Prevention**: Linter/grep check can catch future violations ✅
