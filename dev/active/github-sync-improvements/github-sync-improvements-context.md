# GitHub Sync Improvements - Context

**Last Updated:** 2025-12-21

## Key Files

### Models
| File | Purpose |
|------|---------|
| `apps/integrations/models.py` | TrackedRepository model - needs rate limit & progress fields |
| `apps/integrations/constants.py` | SyncStatus enum |

### Services (Existing)
| File | Purpose |
|------|---------|
| `apps/integrations/services/github_sync.py` | sync_repository_history() - main sync logic |
| `apps/integrations/services/github_oauth.py` | OAuth token management |

### Services (To Create)
| File | Purpose |
|------|---------|
| `apps/integrations/services/github_rate_limit.py` | Rate limit checking utilities |
| `apps/integrations/services/sync_notifications.py` | Email notifications |

### Tasks
| File | Purpose |
|------|---------|
| `apps/integrations/tasks.py` | Celery tasks - needs new initial sync task |

### Views
| File | Purpose |
|------|---------|
| `apps/integrations/views/github.py` | github_repo_toggle - needs to queue background sync |

### Templates
| File | Purpose |
|------|---------|
| `apps/integrations/templates/integrations/github_repos.html` | Repo list |
| `apps/integrations/templates/integrations/partials/github_repo_card.html` | Repo card |
| `templates/emails/sync_complete.html` | Email template (to create) |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rate limit threshold | 100 remaining | Leaves buffer for webhook events |
| Default sync depth | 30 days | Balances data value vs sync time |
| Progress storage | Model fields | Simple, no Redis dependency |
| Email delivery | Django send_mail | Already configured |
| Progress polling | HTMX | Already used throughout app |

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

## Current Flow (Before)

```
github_repo_toggle()
    → create_webhook()
    → TrackedRepository.objects.create()
    → sync_repository_history()  ← BLOCKS UI!
    → return response
```

## Target Flow (After)

```
github_repo_toggle()
    → create_webhook()
    → TrackedRepository.objects.create(sync_status=PENDING)
    → sync_repository_initial_task.delay()  ← ASYNC
    → return response (immediate)

sync_repository_initial_task()
    → set sync_status=SYNCING
    → check_rate_limit()
    → fetch PRs with progress tracking
    → pause if rate_limit_remaining < 100
    → set sync_status=COMPLETE
    → trigger insights aggregation
    → send_sync_complete_notification()
```

## Testing Strategy

All phases use TDD with these test categories:
1. Unit tests for rate limit utilities
2. Unit tests for notification service
3. Integration tests for Celery tasks
4. View tests for async behavior

## Related Features

- Multi-token pool (completed) - `apps/metrics/seeding/github_token_pool.py`
- Webhook handling - `apps/web/views.py::github_webhook()`
- Insights aggregation - `apps/metrics/processors.py`
