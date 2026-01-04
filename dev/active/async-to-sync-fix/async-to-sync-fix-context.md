# async_to_sync Fix - Context

**Last Updated:** 2026-01-04

## Key Files

### Files to Modify
- `apps/integrations/_task_modules/pr_data.py:60` - Bug location
- `CLAUDE.md` (lines 377-391) - Expand async warning
- `Makefile` - Add linter target

### Reference Files (Correct Pattern)
- `apps/integrations/_task_modules/github_sync.py` - Lines 48, 67, 74, 111, 126, 160, 175
- `apps/integrations/services/onboarding_sync.py` - Lines 13, 99-113

### Test Files (Safe asyncio.run)
- `apps/integrations/tests/test_github_graphql.py`
- `apps/integrations/tests/test_github_graphql_sync.py`
- `apps/integrations/tests/test_github_rate_limit.py`
- `apps/metrics/tests/test_github_graphql_fetcher.py`

### Seeding Utilities (Safe asyncio.run)
- `apps/metrics/seeding/github_graphql_fetcher.py`

## Technical Context

### Why asyncio.run() Fails in Celery

1. Django uses **thread-local storage** for database connections
2. `asyncio.run()` creates a **new event loop** in a potentially different thread context
3. `@sync_to_async(thread_sensitive=True)` expects the same thread context
4. Result: Database operations run but **don't commit** (no error thrown!)

### Why async_to_sync() Works

1. From `asgiref` (Django's async library)
2. Reuses or properly manages the existing event loop context
3. Respects thread-sensitive operations
4. Used by Django's ASGI layer for production async view support

## Related Decisions

| Decision | Rationale |
|----------|-----------|
| Use async_to_sync in Celery | Django's thread-local DB connections |
| asyncio.run OK in tests | Fresh process, no thread-local issues |
| asyncio.run OK in management commands | Same as tests |
| Expand docs scope | Prevent same bug in views/signals |

## Dependencies

- `asgiref` - Already installed (Django dependency)
- No new packages needed

## Code Snippets

### Correct Pattern (from github_sync.py)
```python
from asgiref.sync import async_to_sync

# Inside a Celery task or sync Django code:
result = async_to_sync(sync_repository_history_graphql)(
    tracked_repo, days_back=days_back, skip_recent=skip_recent
)
```

### Bug to Fix (pr_data.py:60)
```python
# BEFORE (wrong):
import asyncio
result = asyncio.run(fetch_pr_complete_data_graphql(pr, tracked_repo))

# AFTER (correct):
from asgiref.sync import async_to_sync
result = async_to_sync(fetch_pr_complete_data_graphql)(pr, tracked_repo)
```

### Documentation Comment Pattern
```python
# NOTE: Using async_to_sync instead of asyncio.run() is critical!
# asyncio.run() creates a new event loop which breaks @sync_to_async
# decorators' thread handling, causing DB operations to silently fail
# in Celery workers. async_to_sync properly manages the event loop
# and thread context for Django's database connections.
```
