# Phase 2.6: Incremental Sync - Context Reference

> Last Updated: 2025-12-11

## Implementation Status

**Status:** ✅ COMPLETE

All 587 tests pass. Lint passes. Committed as `a128e1a`.

---

## What Was Implemented

### New Files Created

| File | Purpose |
|------|---------|
| `apps/integrations/tasks.py` | Celery tasks: `sync_repository_task`, `sync_all_repositories_task` |
| `apps/integrations/constants.py` | Shared sync status constants |
| `apps/integrations/tests/test_tasks.py` | 16 tests for Celery tasks |
| `apps/integrations/migrations/0007_*.py` | Adds sync_status, last_sync_error to TrackedRepository |

### Modified Files

| File | Changes |
|------|---------|
| `apps/integrations/services/github_sync.py` | Added `get_updated_pull_requests()`, `sync_repository_incremental()`, `_convert_pr_to_dict()`, `_process_prs()` |
| `apps/integrations/models.py` | Added `sync_status`, `last_sync_error` fields to TrackedRepository |
| `apps/integrations/factories.py` | Added `sync_status`, `last_sync_error` defaults |
| `tformance/settings.py` | Added `sync-github-repositories-daily` scheduled task (4 AM UTC) |

---

## Key Functions Implemented

### `get_updated_pull_requests(access_token, repo_full_name, since)`
- Uses GitHub Issues API with `since` parameter (PRs API lacks this)
- Filters to only issues with `pull_request` attribute
- Fetches full PR details via `repo.get_pull(issue.number)`
- Returns list of PR dicts in same format as `get_repository_pull_requests()`

### `sync_repository_incremental(tracked_repo)`
- If `last_sync_at` is None, falls back to `sync_repository_history()` (full sync)
- Otherwise calls `get_updated_pull_requests(since=last_sync_at)`
- Uses shared `_process_prs()` helper for PR/review creation
- Updates `last_sync_at` on completion
- Returns `{prs_synced, reviews_synced, errors}`

### `sync_repository_task(repo_id)` - Celery Task
- Decorated with `@shared_task(bind=True, max_retries=3, default_retry_delay=60)`
- Sets `sync_status` to "syncing" before sync
- Sets `sync_status` to "complete" and clears `last_sync_error` on success
- Sets `sync_status` to "error" and saves error message on permanent failure
- Retries with exponential backoff: `60 * (2 ** retries)`
- Logs to Sentry on max retries exceeded

### `sync_all_repositories_task()` - Celery Task
- Queries `TrackedRepository.objects.filter(is_active=True)`
- Dispatches `sync_repository_task.delay(repo.id)` for each
- Continues on individual dispatch errors
- Returns `{repos_dispatched, repos_skipped}`

---

## Model Changes

### TrackedRepository (new fields)

```python
SYNC_STATUS_PENDING = "pending"
SYNC_STATUS_SYNCING = "syncing"
SYNC_STATUS_COMPLETE = "complete"
SYNC_STATUS_ERROR = "error"

sync_status = CharField(choices=SYNC_STATUS_CHOICES, default="pending")
last_sync_error = TextField(null=True, blank=True)
```

Constants are shared via `apps/integrations/constants.py`.

---

## Scheduled Task Configuration

```python
# tformance/settings.py
"sync-github-repositories-daily": {
    "task": "apps.integrations.tasks.sync_all_repositories_task",
    "schedule": schedules.crontab(minute=0, hour=4),  # 4 AM UTC
    "expire_seconds": 60 * 60 * 4,  # 4 hour expiry
},
```

---

## Testing

### Test Coverage (35 new tests)

- `test_github_sync.py`: 6 tests for `get_updated_pull_requests()`, 9 tests for `sync_repository_incremental()`
- `test_tasks.py`: 16 tests for Celery tasks
- `test_models.py`: 4 tests for sync_status/last_sync_error fields

### Commands

```bash
make test ARGS='apps.integrations --keepdb'  # 300 tests
make test ARGS='--keepdb'                    # 587 tests total
```

---

## Architecture

```
[Celery Beat - 4 AM UTC]
        │
        ▼
[sync_all_repositories_task]
        │
        ├─► [sync_repository_task(repo_1)]
        ├─► [sync_repository_task(repo_2)]
        └─► [sync_repository_task(repo_n)]
                │
                ▼ (since=last_sync_at)
        [GitHub Issues API → PRs]
                │
                ▼
        [PullRequest / PRReview models]
```

---

## Verification Commands

```bash
# Apply migration
make migrate

# Run tests
make test ARGS='apps.integrations --keepdb'

# Lint check
make ruff

# Run Celery worker (for manual testing)
celery -A tformance worker -l info

# Run Celery beat (for scheduled tasks)
celery -A tformance beat -l info

# Trigger task manually
python manage.py shell
>>> from apps.integrations.tasks import sync_all_repositories_task
>>> sync_all_repositories_task.delay()

# Bootstrap scheduled task
python manage.py bootstrap_celery_tasks
```

---

## Prerequisites Completed

The PyGithub refactor was completed first (commit `b0763d6`):
- All GitHub API calls now use PyGithub library
- 9 functions refactored across 3 service files
- ~200 lines of manual HTTP code removed
- `apps/integrations/services/github_client.py` created
