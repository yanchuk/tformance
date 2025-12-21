# GitHub Sync Improvements - Tasks

**Last Updated:** 2025-12-21

## Phase 1: Rate Limit Monitoring

### 1.1 Add rate limit fields to TrackedRepository
- [ ] Add `rate_limit_remaining` field (IntegerField, null=True)
- [ ] Add `rate_limit_reset_at` field (DateTimeField, null=True)
- [ ] Create migration
- [ ] Run migration

### 1.2 Create rate limit helper service
- [ ] RED: Write tests for `check_rate_limit()`
- [ ] RED: Write tests for `should_pause_for_rate_limit()`
- [ ] RED: Write tests for `wait_for_rate_limit_reset()`
- [ ] GREEN: Implement `apps/integrations/services/github_rate_limit.py`
- [ ] REFACTOR: Clean up if needed

### 1.3 Integrate rate limit into sync
- [ ] RED: Write tests for rate limit checking during sync
- [ ] GREEN: Modify `_process_prs()` to check rate limit
- [ ] GREEN: Update TrackedRepository.rate_limit_remaining after each PR
- [ ] GREEN: Pause sync if remaining < 100
- [ ] REFACTOR: Clean up if needed

---

## Phase 2: Background Historical Sync

### 2.1 Add progress tracking fields
- [ ] Add `sync_progress` field (IntegerField, default=0)
- [ ] Add `sync_prs_total` field (IntegerField, null=True)
- [ ] Add `sync_prs_completed` field (IntegerField, default=0)
- [ ] Add `sync_started_at` field (DateTimeField, null=True)
- [ ] Create migration
- [ ] Run migration

### 2.2 Create initial historical sync task
- [ ] RED: Write tests for `sync_repository_initial_task`
- [ ] RED: Test accepts `days_back` parameter
- [ ] RED: Test tracks progress during sync
- [ ] RED: Test handles rate limits gracefully
- [ ] GREEN: Implement `sync_repository_initial_task` in tasks.py
- [ ] REFACTOR: Clean up if needed

### 2.3 Update repo tracking view
- [ ] RED: Write tests for async toggle behavior
- [ ] GREEN: Remove synchronous `sync_repository_history()` call
- [ ] GREEN: Queue `sync_repository_initial_task.delay()`
- [ ] GREEN: Return immediate response with "syncing" status
- [ ] REFACTOR: Clean up if needed

---

## Phase 3: Configurable Sync Depth

### 3.1 Add sync options to UI
- [ ] Add sync depth selector to github_repo_card.html
- [ ] Default to 30 days
- [ ] Include "Full history" option

### 3.2 Update toggle endpoint
- [ ] RED: Write tests for sync_depth parameter
- [ ] GREEN: Accept sync_depth in github_repo_toggle
- [ ] GREEN: Pass to sync_repository_initial_task
- [ ] REFACTOR: Clean up if needed

---

## Phase 4: Email Notifications

### 4.1 Create sync notification template
- [ ] Create `templates/emails/sync_complete.html`
- [ ] Include repo name and sync summary
- [ ] Include link to dashboard
- [ ] Test email rendering

### 4.2 Create notification service
- [ ] RED: Write tests for `send_sync_complete_notification()`
- [ ] RED: Test handles missing email gracefully
- [ ] GREEN: Implement `apps/integrations/services/sync_notifications.py`
- [ ] REFACTOR: Clean up if needed

### 4.3 Integrate notification into sync task
- [ ] RED: Write tests for notification after sync
- [ ] GREEN: Call `send_sync_complete_notification()` after successful sync
- [ ] GREEN: Include stats in notification
- [ ] REFACTOR: Clean up if needed

---

## Phase 5: UI Progress Display

### 5.1 Add progress indicator to repo list
- [ ] Update github_repos.html to show progress for syncing repos
- [ ] Display progress bar (0-100%)
- [ ] Show "Syncing X/Y PRs..."
- [ ] Add HTMX polling for auto-refresh

### 5.2 Create progress API endpoint
- [ ] RED: Write tests for progress endpoint
- [ ] GREEN: Create `github_repo_sync_progress()` view
- [ ] GREEN: Return progress partial for HTMX
- [ ] GREEN: Add URL pattern
- [ ] REFACTOR: Clean up if needed

---

## Verification

### All Phases Complete
- [ ] All unit tests pass: `make test`
- [ ] E2E smoke tests pass: `make e2e-smoke`
- [ ] Manual test: Track a new repo, verify background sync
- [ ] Manual test: Check email notification received
- [ ] Manual test: Verify progress updates in UI

---

## Progress Log

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| 2025-12-21 | Plan | Complete | Created plan, context, tasks docs |
| | Phase 1 | Not Started | |
| | Phase 2 | Not Started | |
| | Phase 3 | Not Started | |
| | Phase 4 | Not Started | |
| | Phase 5 | Not Started | |
