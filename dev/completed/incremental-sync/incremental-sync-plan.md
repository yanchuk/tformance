# Phase 2.6: Incremental Sync - Implementation Plan

> Last Updated: 2025-12-11

## Prerequisites

**IMPORTANT:** Complete the PyGithub Refactor before starting this phase.
- See: `dev/active/pygithub-refactor/`
- The refactor converts all direct API calls to use PyGithub library
- This phase builds on top of that foundation

## Executive Summary

Implement a daily Celery task that performs incremental (delta) sync of GitHub PR data for all active tracked repositories. This replaces the current full-sync approach with an efficient system that only fetches PRs updated since the last sync.

**Goal:** Automate daily sync to keep metrics current without manual intervention or redundant API calls.

---

## Current State Analysis

### What Exists

1. **Full Sync Service** (`apps/integrations/services/github_sync.py`)
   - `sync_repository_history()` fetches ALL PRs from a repo
   - Updates `TrackedRepository.last_sync_at` on completion
   - Handles PR creation/update and review sync
   - No date filtering - always fetches everything

2. **Manual Triggers**
   - Auto-sync on repo track (in `github_repo_toggle`)
   - Manual sync button via `github_repo_sync` endpoint

3. **Celery Infrastructure**
   - Configured in `tformance/celery.py`
   - `SCHEDULED_TASKS` dict in settings for periodic tasks
   - `bootstrap_celery_tasks` management command
   - Uses `django-celery-beat` for scheduling

4. **GitHub API Usage**
   - Direct `requests` calls to REST API
   - No official GitHub library installed

### Gaps to Address

1. **No incremental sync** - Always fetches all PRs (inefficient for large repos)
2. **No scheduled sync** - Only manual/on-track triggers
3. **No library abstraction** - Direct API calls harder to maintain
4. **No rate limit handling** - Could hit GitHub API limits with many repos

---

## Proposed Future State

### Architecture

```
[Celery Beat Scheduler]
        │
        ▼ (Daily at 4 AM UTC)
[sync_all_repositories_task]
        │
        ├─► [sync_repository_incremental(repo_1)]
        ├─► [sync_repository_incremental(repo_2)]
        └─► [sync_repository_incremental(repo_n)]
                │
                ▼
        [GitHub API via PyGithub]
        (since=last_sync_at filter)
                │
                ▼
        [PullRequest / PRReview models]
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| GitHub Library | **PyGithub** | Most popular, well-maintained, good docs, supports pagination |
| Incremental Strategy | Use Issues API with `since` | PRs API lacks `since`; Issues API returns PRs too |
| Task Granularity | One task per repo | Isolates failures, enables retry per repo |
| Schedule | Daily at 4 AM UTC | Low-traffic time, after midnight US |
| Retry Policy | 3 retries with exponential backoff | Handle transient failures gracefully |

---

## Implementation Phases

### Section 1: PyGithub Integration (Foundation)

Replace direct API calls with PyGithub library for better maintainability.

| # | Task | Acceptance Criteria | Effort | Dependencies |
|---|------|---------------------|--------|--------------|
| 1.1 | Add PyGithub dependency | `PyGithub` in pyproject.toml, `uv sync` passes | S | None |
| 1.2 | Create `github_client.py` service | Helper to get authenticated PyGithub client from TrackedRepository | S | 1.1 |
| 1.3 | Write tests for github_client | Test client creation, token decryption | S | 1.2 |

### Section 2: Incremental Sync Logic

Build the delta sync capability using `since` parameter.

| # | Task | Acceptance Criteria | Effort | Dependencies |
|---|------|---------------------|--------|--------------|
| 2.1 | Create `get_updated_pull_requests()` | Fetch PRs updated since a given datetime using Issues API | M | 1.2 |
| 2.2 | Write tests for updated PRs fetch | Test date filtering, pagination, PR-only filtering | M | 2.1 |
| 2.3 | Create `sync_repository_incremental()` | Like `sync_repository_history()` but with `since` filter | M | 2.1 |
| 2.4 | Write tests for incremental sync | Test that only updated PRs are synced | M | 2.3 |
| 2.5 | Handle edge case: first sync | If `last_sync_at` is None, fall back to full sync | S | 2.3 |

### Section 3: Celery Tasks

Create the scheduled task infrastructure.

| # | Task | Acceptance Criteria | Effort | Dependencies |
|---|------|---------------------|--------|--------------|
| 3.1 | Create `apps/integrations/tasks.py` | File with task structure | S | None |
| 3.2 | Implement `sync_repository_task(repo_id)` | Single repo sync as Celery task with retry | M | 2.3, 3.1 |
| 3.3 | Write tests for single repo task | Test success, failure, retry behavior | M | 3.2 |
| 3.4 | Implement `sync_all_repositories_task()` | Dispatch `sync_repository_task` for each active repo | M | 3.2 |
| 3.5 | Write tests for all repos task | Test dispatch, error isolation | M | 3.4 |
| 3.6 | Add to SCHEDULED_TASKS in settings | Configure daily 4 AM UTC schedule | S | 3.4 |
| 3.7 | Update bootstrap_celery_tasks | Ensure task is created on bootstrap | S | 3.6 |

### Section 4: Error Handling & Monitoring

Improve resilience and observability.

| # | Task | Acceptance Criteria | Effort | Dependencies |
|---|------|---------------------|--------|--------------|
| 4.1 | Add sync_status tracking | Update `TrackedRepository.sync_status` during sync | S | 2.3 |
| 4.2 | Add sync error logging | Log errors to Sentry, store last_error on model | M | 3.2 |
| 4.3 | Handle rate limiting | Detect 403/rate limit, backoff appropriately | M | 2.1 |
| 4.4 | Write tests for error scenarios | Test rate limit handling, auth failures | M | 4.3 |

### Section 5: UI Updates (Optional)

Show sync status in the UI.

| # | Task | Acceptance Criteria | Effort | Dependencies |
|---|------|---------------------|--------|--------------|
| 5.1 | Add sync_error field to TrackedRepository | Migration for `last_sync_error` CharField | S | 4.2 |
| 5.2 | Display sync status in repo card | Show "Syncing...", "Error", "Synced" badges | S | 5.1 |
| 5.3 | Write tests for UI states | Test badge rendering for each status | S | 5.2 |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub rate limiting | Medium | High | Implement exponential backoff, spread repos over time |
| Large repos overwhelming sync | Low | Medium | Add pagination limits, async processing |
| Token expiration during sync | Low | Medium | Refresh token before sync, handle auth errors gracefully |
| Celery worker failure | Low | High | Use persistent queue (Redis), retry policy |
| Time zone issues with `since` | Low | Low | Always use UTC, store `last_sync_at` as timezone-aware |

---

## Success Metrics

1. **Efficiency**: PRs synced per API call increases (fewer redundant fetches)
2. **Freshness**: Data is never more than 24 hours stale
3. **Reliability**: 99%+ success rate on daily syncs
4. **Performance**: Sync completes within 1 hour for typical team (50 repos)

---

## Required Resources

### Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    "PyGithub>=2.1.0",  # GitHub API client
]
```

### Configuration Required

```python
# settings.py SCHEDULED_TASKS addition
"sync-github-repositories-daily": {
    "task": "apps.integrations.tasks.sync_all_repositories_task",
    "schedule": schedules.crontab(minute=0, hour=4),  # 4 AM UTC
    "expire_seconds": 60 * 60 * 4,  # 4 hour expiry
},
```

---

## Out of Scope

- Real-time webhook sync (already implemented in Phase 2.5)
- Jira integration (Phase 3)
- Slack notifications for sync status
- Admin dashboard for sync monitoring

---

## Estimated Total Effort

| Section | Effort | TDD Cycles |
|---------|--------|------------|
| 1. PyGithub Integration | Small | 1-2 |
| 2. Incremental Sync Logic | Medium | 3-4 |
| 3. Celery Tasks | Medium | 3-4 |
| 4. Error Handling | Medium | 2-3 |
| 5. UI Updates (Optional) | Small | 1-2 |
| **Total** | **Medium-Large** | **10-15** |
