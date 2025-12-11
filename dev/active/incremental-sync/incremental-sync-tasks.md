# Phase 2.6: Incremental Sync - Task Checklist

> Last Updated: 2025-12-11

## Progress Summary

| Section | Status | Progress |
|---------|--------|----------|
| 1. PyGithub Integration | Not Started | 0/3 |
| 2. Incremental Sync Logic | Not Started | 0/5 |
| 3. Celery Tasks | Not Started | 0/7 |
| 4. Error Handling | Not Started | 0/4 |
| 5. UI Updates (Optional) | Not Started | 0/3 |

**Overall:** 0/22 tasks complete

---

## Section 1: PyGithub Integration (Foundation)

- [ ] **1.1** Add PyGithub dependency
  - Add `PyGithub>=2.1.0` to pyproject.toml
  - Run `uv sync`
  - Verify import works
  - **Effort:** S

- [ ] **1.2** Create `github_client.py` service
  - Create `apps/integrations/services/github_client.py`
  - Implement `get_github_client(tracked_repo)` function
  - Handle token decryption
  - Return authenticated `Github` instance
  - **Effort:** S
  - **Depends on:** 1.1

- [ ] **1.3** Write tests for github_client
  - Test client creation with valid token
  - Test client returns authenticated instance
  - Mock `decrypt()` and `Github` class
  - **Effort:** S
  - **Depends on:** 1.2

---

## Section 2: Incremental Sync Logic

- [ ] **2.1** Create `get_updated_pull_requests()` function
  - Add to `github_sync.py` or new module
  - Use Issues API with `since` parameter
  - Filter to PRs only (`issue.pull_request` not None)
  - Convert issues to full PR objects
  - Handle pagination automatically
  - **Effort:** M
  - **Depends on:** 1.2

- [ ] **2.2** Write tests for updated PRs fetch
  - Test date filtering works correctly
  - Test pagination handling
  - Test PR-only filtering (excludes regular issues)
  - Test empty result when no updates
  - Mock PyGithub responses
  - **Effort:** M
  - **Depends on:** 2.1

- [ ] **2.3** Create `sync_repository_incremental()` function
  - Similar to `sync_repository_history()` but uses `since`
  - Calculate `since` from `tracked_repo.last_sync_at`
  - Process only updated PRs
  - Update reviews for updated PRs
  - Update `last_sync_at` on completion
  - **Effort:** M
  - **Depends on:** 2.1

- [ ] **2.4** Write tests for incremental sync
  - Test only updated PRs are synced
  - Test PR update (not just create)
  - Test reviews are synced for updated PRs
  - Test `last_sync_at` is updated
  - **Effort:** M
  - **Depends on:** 2.3

- [ ] **2.5** Handle edge case: first sync
  - If `last_sync_at` is None, call full sync instead
  - Add test for fallback behavior
  - **Effort:** S
  - **Depends on:** 2.3

---

## Section 3: Celery Tasks

- [ ] **3.1** Create `apps/integrations/tasks.py`
  - Create new file with standard imports
  - Import `shared_task` from Celery
  - **Effort:** S

- [ ] **3.2** Implement `sync_repository_task(repo_id)`
  - Single repo sync as Celery task
  - Add retry decorator with exponential backoff
  - Handle exceptions gracefully
  - Log sync results
  - **Effort:** M
  - **Depends on:** 2.3, 3.1

- [ ] **3.3** Write tests for single repo task
  - Test successful sync
  - Test retry on transient failure
  - Test task doesn't retry on permanent failure (e.g., auth)
  - Test with missing repo_id
  - **Effort:** M
  - **Depends on:** 3.2

- [ ] **3.4** Implement `sync_all_repositories_task()`
  - Query all active `TrackedRepository` instances
  - Dispatch `sync_repository_task` for each
  - Use `.delay()` to run async
  - **Effort:** M
  - **Depends on:** 3.2

- [ ] **3.5** Write tests for all repos task
  - Test dispatches correct number of tasks
  - Test only active repos are synced
  - Test handles empty repo list
  - **Effort:** M
  - **Depends on:** 3.4

- [ ] **3.6** Add to SCHEDULED_TASKS in settings
  - Add `sync-github-repositories-daily` config
  - Schedule: `crontab(minute=0, hour=4)` (4 AM UTC)
  - Set appropriate `expire_seconds`
  - **Effort:** S
  - **Depends on:** 3.4

- [ ] **3.7** Update bootstrap_celery_tasks
  - Run `python manage.py bootstrap_celery_tasks`
  - Verify task is created in database
  - **Effort:** S
  - **Depends on:** 3.6

---

## Section 4: Error Handling & Monitoring

- [ ] **4.1** Add sync_status tracking
  - Update `TrackedRepository` model if needed
  - Set status to "syncing" at start
  - Set status to "complete" or "error" at end
  - **Effort:** S
  - **Depends on:** 2.3

- [ ] **4.2** Add sync error logging
  - Log errors to standard logging
  - Capture exceptions to Sentry
  - Store last error message on model (optional)
  - **Effort:** M
  - **Depends on:** 3.2

- [ ] **4.3** Handle rate limiting
  - Catch `RateLimitExceededException` from PyGithub
  - Get rate limit reset time
  - Schedule task retry after reset
  - **Effort:** M
  - **Depends on:** 2.1

- [ ] **4.4** Write tests for error scenarios
  - Test rate limit handling and retry
  - Test auth failure handling
  - Test network error handling
  - **Effort:** M
  - **Depends on:** 4.3

---

## Section 5: UI Updates (Optional)

*These tasks are optional for MVP but improve user experience.*

- [ ] **5.1** Add sync_error field to TrackedRepository
  - Add `last_sync_error = CharField(blank=True)`
  - Create and apply migration
  - **Effort:** S
  - **Depends on:** 4.2

- [ ] **5.2** Display sync status in repo card
  - Show "Syncing..." spinner when syncing
  - Show "Error" badge with tooltip when failed
  - Show "Synced" badge with timestamp when complete
  - **Effort:** S
  - **Depends on:** 5.1

- [ ] **5.3** Write tests for UI states
  - Test badge rendering for "syncing" status
  - Test badge rendering for "error" status
  - Test badge rendering for "complete" status
  - **Effort:** S
  - **Depends on:** 5.2

---

## TDD Cycle Tracking

Use this section to track RED-GREEN-REFACTOR cycles during implementation.

| Cycle | RED (Test) | GREEN (Impl) | REFACTOR | Notes |
|-------|------------|--------------|----------|-------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |
| 10 | | | | |

---

## Completion Checklist

Before marking Phase 2.6 complete:

- [ ] All tests pass (`make test`)
- [ ] No lint errors (`make ruff`)
- [ ] PyGithub is installed and used
- [ ] Incremental sync works correctly
- [ ] Celery task is scheduled
- [ ] `bootstrap_celery_tasks` creates the task
- [ ] Error handling is in place
- [ ] Documentation updated
- [ ] Changes committed

---

## Notes

*Add implementation notes here as you work:*

-
