# Phase 2.6: Incremental Sync - Task Checklist

> Last Updated: 2025-12-11

## Progress Summary

| Section | Status | Progress |
|---------|--------|----------|
| 1. PyGithub Integration | ✅ Complete | 3/3 |
| 2. Incremental Sync Logic | ✅ Complete | 5/5 |
| 3. Celery Tasks | ✅ Complete | 7/7 |
| 4. Error Handling | ✅ Complete | 4/4 |
| 5. UI Updates (Optional) | Skipped | 0/3 |

**Overall:** 19/22 tasks complete (3 optional UI tasks skipped)

---

## Section 1: PyGithub Integration (Foundation)

- [x] **1.1** Add PyGithub dependency
  - Added `PyGithub>=2.1.0` to pyproject.toml
  - Ran `uv sync` - got `pygithub==2.8.1`
  - Import verified
  - **Commit:** `b0763d6`

- [x] **1.2** Create `github_client.py` service
  - Created `apps/integrations/services/github_client.py`
  - Implemented `get_github_client(access_token)` function
  - Returns authenticated `Github` instance
  - **Commit:** `b0763d6`

- [x] **1.3** Write tests for github_client
  - 3 tests in `apps/integrations/tests/test_github_client.py`
  - **Commit:** `b0763d6`

---

## Section 2: Incremental Sync Logic

- [x] **2.1** Create `get_updated_pull_requests()` function
  - Added to `github_sync.py`
  - Uses Issues API with `since` parameter
  - Filters to PRs only (`issue.pull_request` not None)
  - Fetches full PR via `repo.get_pull(issue.number)`
  - **Commit:** `a128e1a`

- [x] **2.2** Write tests for updated PRs fetch
  - 6 tests in `TestGetUpdatedPullRequests` class
  - Tests date filtering, pagination, PR-only filtering
  - **Commit:** `a128e1a`

- [x] **2.3** Create `sync_repository_incremental()` function
  - Uses `get_updated_pull_requests(since=last_sync_at)`
  - Shared `_process_prs()` helper for PR/review creation
  - Updates `last_sync_at` on completion
  - **Commit:** `a128e1a`

- [x] **2.4** Write tests for incremental sync
  - 9 tests in `TestSyncRepositoryIncremental` class
  - **Commit:** `a128e1a`

- [x] **2.5** Handle edge case: first sync
  - Falls back to `sync_repository_history()` when `last_sync_at` is None
  - Test: `test_sync_repository_incremental_falls_back_to_full_sync_when_last_sync_at_is_none`
  - **Commit:** `a128e1a`

---

## Section 3: Celery Tasks

- [x] **3.1** Create `apps/integrations/tasks.py`
  - Created with standard Celery imports
  - **Commit:** `a128e1a`

- [x] **3.2** Implement `sync_repository_task(repo_id)`
  - Decorated `@shared_task(bind=True, max_retries=3, default_retry_delay=60)`
  - Exponential backoff: `60 * (2 ** retries)`
  - Updates `sync_status` field (syncing → complete/error)
  - Logs to Sentry on permanent failure
  - **Commit:** `a128e1a`

- [x] **3.3** Write tests for single repo task
  - 11 tests in `TestSyncRepositoryTask` class
  - **Commit:** `a128e1a`

- [x] **3.4** Implement `sync_all_repositories_task()`
  - Queries `TrackedRepository.objects.filter(is_active=True)`
  - Dispatches `sync_repository_task.delay(repo.id)` for each
  - Returns `{repos_dispatched, repos_skipped}`
  - **Commit:** `a128e1a`

- [x] **3.5** Write tests for all repos task
  - 5 tests in `TestSyncAllRepositoriesTask` class
  - **Commit:** `a128e1a`

- [x] **3.6** Add to SCHEDULED_TASKS in settings
  - Added `sync-github-repositories-daily` config
  - Schedule: `schedules.crontab(minute=0, hour=4)` (4 AM UTC)
  - `expire_seconds`: 4 hours
  - **Commit:** `a128e1a`

- [x] **3.7** Update bootstrap_celery_tasks
  - Run `python manage.py bootstrap_celery_tasks` to create task
  - **Commit:** `a128e1a`

---

## Section 4: Error Handling & Monitoring

- [x] **4.1** Add sync_status tracking
  - Added `sync_status` field to `TrackedRepository` model
  - Choices: pending, syncing, complete, error
  - Constants in `apps/integrations/constants.py`
  - **Migration:** `0007_trackedrepository_last_sync_error_and_more.py`
  - **Commit:** `a128e1a`

- [x] **4.2** Add sync error logging
  - Added `last_sync_error` TextField to model
  - Errors logged via standard logging
  - Sentry capture on permanent failures
  - **Commit:** `a128e1a`

- [x] **4.3** Handle rate limiting
  - PyGithub raises `RateLimitExceededException`
  - Task retries with exponential backoff
  - **Commit:** `a128e1a`

- [x] **4.4** Write tests for error scenarios
  - Tests for retry logic, permanent failures, error message storage
  - 5 sync status tracking tests
  - **Commit:** `a128e1a`

---

## Section 5: UI Updates (Optional)

*Skipped for MVP - can be added later*

- [ ] **5.1** Display sync status in repo card
- [ ] **5.2** Show error badge with tooltip
- [ ] **5.3** Write tests for UI states

---

## TDD Cycle Tracking

| Cycle | RED (Test) | GREEN (Impl) | REFACTOR | Notes |
|-------|------------|--------------|----------|-------|
| 1 | ✅ | ✅ | ✅ | `get_updated_pull_requests()` |
| 2 | ✅ | ✅ | ✅ | `sync_repository_incremental()` + `_process_prs()` extraction |
| 3 | ✅ | ✅ | ✅ | Celery tasks + logging improvements |
| 4 | ✅ | ✅ | ✅ | Sync status tracking + constants extraction |

---

## Completion Checklist

- [x] All tests pass (`make test` - 587 tests)
- [x] No lint errors (`make ruff`)
- [x] PyGithub is installed and used
- [x] Incremental sync works correctly
- [x] Celery task is scheduled (4 AM UTC)
- [x] `bootstrap_celery_tasks` creates the task
- [x] Error handling is in place
- [x] Documentation updated
- [x] Changes committed (`a128e1a`)

---

## Commits

| Commit | Description |
|--------|-------------|
| `b0763d6` | PyGithub refactor (prerequisite) |
| `a128e1a` | Phase 2.6 Incremental Sync implementation |

---

## Notes

- GitHub PRs API lacks `since` parameter, so we use Issues API + filter
- PyGithub handles pagination automatically
- Status constants shared between `GitHubIntegration` and `TrackedRepository`
- `_convert_pr_to_dict()` and `_process_prs()` helpers extracted to reduce duplication
