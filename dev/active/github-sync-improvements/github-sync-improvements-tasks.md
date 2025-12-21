# GitHub Sync Improvements - Tasks

**Last Updated:** 2025-12-22

## Phase 1: Rate Limit Monitoring

### 1.1 Add rate limit fields to TrackedRepository
- [x] Add `rate_limit_remaining` field (IntegerField, null=True)
- [x] Add `rate_limit_reset_at` field (DateTimeField, null=True)
- [x] Create migration
- [x] Run migration

### 1.2 Create rate limit helper service
- [x] RED: Write tests for `check_rate_limit()`
- [x] RED: Write tests for `should_pause_for_rate_limit()`
- [x] RED: Write tests for `wait_for_rate_limit_reset()`
- [x] GREEN: Implement `apps/integrations/services/github_rate_limit.py`
- [x] REFACTOR: Clean up if needed

### 1.3 Integrate rate limit into sync
- [x] RED: Write tests for rate limit checking during sync
- [x] GREEN: Modify `_process_prs()` to check rate limit
- [x] GREEN: Update TrackedRepository.rate_limit_remaining after each PR
- [x] GREEN: Pause sync if remaining < 100
- [x] REFACTOR: Clean up if needed

---

## Phase 2: Background Historical Sync

### 2.1 Add progress tracking fields
- [x] Add `sync_progress` field (IntegerField, default=0)
- [x] Add `sync_prs_total` field (IntegerField, null=True)
- [x] Add `sync_prs_completed` field (IntegerField, default=0)
- [x] Add `sync_started_at` field (DateTimeField, null=True)
- [x] Create migration
- [x] Run migration

### 2.2 Create initial historical sync task
- [x] RED: Write tests for `sync_repository_initial_task`
- [x] RED: Test accepts `days_back` parameter
- [x] RED: Test tracks progress during sync
- [x] RED: Test handles rate limits gracefully
- [x] GREEN: Implement `sync_repository_initial_task` in tasks.py
- [x] REFACTOR: Clean up if needed

### 2.3 Update repo tracking view
- [x] RED: Write tests for async toggle behavior
- [x] GREEN: Remove synchronous `sync_repository_history()` call
- [x] GREEN: Queue `sync_repository_initial_task.delay()`
- [x] GREEN: Return immediate response with "syncing" status
- [x] REFACTOR: Clean up if needed

---

## Phase 3: Configurable Sync Depth

### 3.1 Add sync options to UI
- [x] Add sync depth selector to github_repo_card.html
- [x] Default to 30 days
- [x] Include "Full history" option

### 3.2 Update toggle endpoint
- [x] RED: Write tests for sync_depth parameter
- [x] GREEN: Accept sync_depth in github_repo_toggle
- [x] GREEN: Pass to sync_repository_initial_task
- [x] REFACTOR: Clean up if needed

---

## Phase 4: Email Notifications

### 4.1 Create sync notification template
- [x] Create email template (using send_mail with text)
- [x] Include repo name and sync summary
- [x] Include link to dashboard
- [x] Test email rendering

### 4.2 Create notification service
- [x] RED: Write tests for `send_sync_complete_notification()`
- [x] RED: Test handles missing email gracefully
- [x] GREEN: Implement `apps/integrations/services/sync_notifications.py`
- [x] REFACTOR: Clean up if needed

### 4.3 Integrate notification into sync task
- [x] RED: Write tests for notification after sync
- [x] GREEN: Call `send_sync_complete_notification()` after successful sync
- [x] GREEN: Include stats in notification
- [x] REFACTOR: Clean up if needed

---

## Phase 5: UI Progress Display

### 5.1 Add progress indicator to repo list
- [x] Update repo_card.html to show progress for syncing repos
- [x] Display progress bar (0-100%)
- [x] Show "Syncing X/Y PRs..."
- [x] Add HTMX polling for auto-refresh (every 5s)

### 5.2 Create progress API endpoint
- [x] RED: Write tests for progress endpoint
- [x] GREEN: Create `github_repo_sync_progress()` view
- [x] GREEN: Return progress partial for HTMX
- [x] GREEN: Add URL pattern
- [x] REFACTOR: Clean up if needed

---

## Verification

### All Phases Complete
- [x] All unit tests pass: `make test` (45 new tests)
- [ ] E2E smoke tests pass: `make e2e-smoke`
- [ ] Manual test: Track a new repo, verify background sync
- [ ] Manual test: Check email notification received
- [ ] Manual test: Verify progress updates in UI

---

## Progress Log

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| 2025-12-21 | Plan | Complete | Created plan, context, tasks docs |
| 2025-12-22 | Phase 1 | Complete | Rate limit monitoring with TDD (11 tests) |
| 2025-12-22 | Phase 2 | Complete | Background sync task + async view (12 tests) |
| 2025-12-22 | Phase 3 | Complete | Configurable sync depth (6 tests) |
| 2025-12-22 | Phase 4 | Complete | Email notifications (5 tests) |
| 2025-12-22 | Phase 5 | Complete | UI progress display (4 tests) |
