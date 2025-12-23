# GitHub Sync Improvements - Context

**Last Updated:** 2025-12-22 (Session Complete)
**Status:** ✅ All 5 phases implemented with TDD (45 tests)

## Key Files

### Models
| File | Purpose | Status |
|------|---------|--------|
| `apps/integrations/models.py` | TrackedRepository model - added rate limit & progress fields | Modified |
| `apps/integrations/constants.py` | SyncStatus enum | Existing |
| `apps/integrations/migrations/0014_add_rate_limit_and_progress_tracking.py` | Migration for new fields | Created |

### Services (Created)
| File | Purpose | Tests |
|------|---------|-------|
| `apps/integrations/services/github_rate_limit.py` | Rate limit checking utilities | 11 tests |
| `apps/integrations/tests/test_github_rate_limit.py` | Rate limit service tests | Pass |
| `apps/integrations/tests/test_github_sync_rate_limit.py` | Rate limit integration tests | 5 tests |

### Services (Existing - Modified)
| File | Purpose |
|------|---------|
| `apps/integrations/services/github_sync.py` | sync_repository_history() - added rate limit integration |
| `apps/integrations/services/github_oauth.py` | OAuth token management |

### Tasks
| File | Purpose | Status |
|------|---------|--------|
| `apps/integrations/tasks.py` | Added sync_repository_initial_task | Modified |
| `apps/integrations/tests/test_sync_repository_initial_task.py` | Task tests | 8 tests |

### Views
| File | Purpose | Status |
|------|---------|--------|
| `apps/integrations/views/github.py` | github_repo_toggle - now uses async task | Modified |
| `apps/integrations/tests/test_github_repo_toggle_async.py` | Async view tests | 4 tests |

### Templates (Created)
| File | Purpose |
|------|---------|
| `apps/integrations/templates/integrations/partials/sync_progress.html` | Progress UI partial for HTMX |
| `apps/integrations/templates/integrations/components/repo_card.html` | Updated with HTMX polling + progress bar |

### Services (Created - Phase 4+5)
| File | Purpose | Tests |
|------|---------|-------|
| `apps/integrations/services/sync_notifications.py` | Email notification on sync complete | 5 tests |
| `apps/integrations/tests/test_sync_notifications.py` | Notification service tests | Pass |
| `apps/integrations/tests/test_github_repo_toggle_sync_depth.py` | Sync depth parameter tests | 6 tests |
| `apps/integrations/tests/test_github_repo_progress.py` | Progress endpoint tests | 4 tests |

## New Model Fields

### TrackedRepository (added)
```python
# Rate limit tracking (Phase 1)
rate_limit_remaining = models.IntegerField(null=True, blank=True)
rate_limit_reset_at = models.DateTimeField(null=True, blank=True)

# Progress tracking (Phase 2)
sync_progress = models.IntegerField(default=0)
sync_prs_total = models.IntegerField(null=True, blank=True)
sync_prs_completed = models.IntegerField(default=0)
sync_started_at = models.DateTimeField(null=True, blank=True)
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rate limit threshold | 100 remaining | Leaves buffer for webhook events |
| Default sync depth | 30 days | Balances data value vs sync time |
| Progress storage | Model fields | Simple, no Redis dependency |
| Email delivery | Django send_mail | Already configured |
| Progress polling | HTMX | Already used throughout app |
| Sync behavior | Non-blocking | Queue task and return immediately |

## Dependencies

### Already Available
- Celery for background tasks
- Django email backend (configured)
- HTMX for frontend interactivity
- PyGithub for GitHub API

### Rate Limit Info
- GitHub OAuth tokens: 5,000 requests/hour
- Rate limit headers available on every response
- PyGithub provides `get_rate_limit()` method

## Current Flow (All Phases Complete)

```
github_repo_toggle()
    → create_webhook()
    → TrackedRepository.objects.create(sync_status=PENDING)
    → sync_repository_initial_task.delay(repo.id, days_back=X)  ← ASYNC
    → return response (immediate)

sync_repository_initial_task()
    → set sync_status=SYNCING, sync_started_at=now()
    → sync_repository_history(tracked_repo, days_back=days_back)
        → _process_prs() with rate limit checking
            → after each PR: check rate limit
            → if remaining < 100: stop and return rate_limited=True
    → set sync_status=COMPLETE
    → aggregate_team_weekly_metrics_task.delay()
    → send_sync_complete_notification(tracked_repo, stats)

UI Progress (during sync)
    → repo_card.html polls github_repo_sync_progress every 5s
    → Returns sync_progress partial with status + progress bar
```

## Test Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_github_rate_limit.py` | 11 | Pass |
| `test_github_sync_rate_limit.py` | 5 | Pass |
| `test_sync_repository_initial_task.py` | 10 | Pass |
| `test_github_repo_toggle_async.py` | 4 | Pass |
| `test_github_repo_toggle_sync_depth.py` | 6 | Pass |
| `test_sync_notifications.py` | 5 | Pass |
| `test_github_repo_progress.py` | 4 | Pass |
| **Total New Tests** | **45** | **All Pass** |

## Related Features

- Multi-token pool (completed) - `apps/metrics/seeding/github_token_pool.py`
- Webhook handling - `apps/web/views.py::github_webhook()`
- Insights aggregation - `apps/metrics/processors.py`

## Implementation Complete

All 5 phases have been implemented with TDD:

### Phase 3: Configurable Sync Depth ✓
- UI dropdown in repo_card.html (30 days, 60 days, 90 days, Full history)
- Parameter passed through to task via `days_back`

### Phase 4: Email Notifications ✓
- `send_sync_complete_notification()` service
- Integrated into sync task
- Sends on sync completion with stats

### Phase 5: UI Progress Display ✓
- Progress bar with percentage in repo_card.html
- HTMX polling every 5s during sync
- `github_repo_sync_progress` API endpoint
- `sync_progress.html` partial template
