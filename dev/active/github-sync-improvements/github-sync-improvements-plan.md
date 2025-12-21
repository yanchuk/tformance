# GitHub Sync Improvements - Implementation Plan

**Last Updated:** 2025-12-21

## Executive Summary

Improve the GitHub repository sync flow with:
1. **Rate limit monitoring** - Track and respect GitHub API rate limits
2. **Background historical sync** - Don't block UI, run in background with progress tracking
3. **Configurable sync depth** - Default 30 days, optional full history
4. **Email notification** - Notify users when sync completes and insights are ready
5. **Real-time updates** - Webhooks handle new activity after initial sync

---

## Current State Analysis

### Current Flow (Problems)

```
User tracks repo → SYNCHRONOUS sync_repository_history() → Blocks UI for minutes!
                                ↓
                    Fetches ALL PRs (no date limit)
                                ↓
                    No rate limit checking
                                ↓
                    No progress feedback
                                ↓
                    No completion notification
```

### What Exists

| Component | Status | Location |
|-----------|--------|----------|
| TrackedRepository model | ✅ | `apps/integrations/models.py` |
| sync_repository_task (Celery) | ✅ | `apps/integrations/tasks.py` |
| Webhook handler | ✅ | `apps/web/views.py` |
| sync_repository_history() | ⚠️ Needs improvement | `apps/integrations/services/github_sync.py` |
| Rate limit monitoring | ❌ Missing | - |
| Email notifications | ❌ Missing | - |
| Progress tracking | ❌ Missing | - |

---

## Proposed Future State

### New Flow

```
User tracks repo
    ↓
Create webhook (real-time updates) ← Already works
    ↓
Queue background sync task
    ↓
Show "Syncing..." status in UI
    ↓
Background task:
  1. Check rate limit (5000/hr per user)
  2. Fetch PRs from last 30 days (default) or all (user choice)
  3. Track progress (10%, 25%, 50%, 75%, 100%)
  4. Respect rate limits (pause if < 100 remaining)
  5. Update sync_status and progress
    ↓
When complete:
  1. Mark sync_status = COMPLETE
  2. Trigger insights aggregation
  3. Send email notification
    ↓
Real-time updates via webhooks
```

---

## Implementation Phases

### Phase 1: Rate Limit Monitoring
**Effort:** Medium | **Priority:** High | **Risk:** Low

Add rate limit tracking to prevent 403 errors during sync.

### Phase 2: Background Historical Sync
**Effort:** Medium | **Priority:** High | **Risk:** Medium

Move historical sync to background with progress tracking.

### Phase 3: Configurable Sync Depth
**Effort:** Small | **Priority:** Medium | **Risk:** Low

Allow user to choose 30 days (default) vs full history.

### Phase 4: Email Notifications
**Effort:** Medium | **Priority:** Medium | **Risk:** Low

Notify user when sync completes and insights are ready.

### Phase 5: UI Progress Display
**Effort:** Small | **Priority:** Medium | **Risk:** Low

Show sync progress in the dashboard/repos page.

---

## Detailed Tasks

### Phase 1: Rate Limit Monitoring

#### 1.1 Create rate limit tracking model
**Effort:** S | **File:** `apps/integrations/models.py`

Add fields to track rate limit state:

```python
class TrackedRepository(BaseTeamModel):
    # ... existing fields ...

    # Rate limit tracking
    rate_limit_remaining = models.IntegerField(
        null=True, blank=True,
        help_text="Remaining API requests for this sync"
    )
    rate_limit_reset_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When rate limit resets"
    )
```

**Acceptance Criteria:**
- [ ] Add rate_limit_remaining field to TrackedRepository
- [ ] Add rate_limit_reset_at field to TrackedRepository
- [ ] Create and run migration

#### 1.2 Create rate limit helper service
**Effort:** M | **File:** `apps/integrations/services/github_rate_limit.py`

```python
def check_rate_limit(access_token: str) -> dict:
    """Check current rate limit status."""
    github = Github(access_token)
    rate = github.get_rate_limit().rate
    return {
        "remaining": rate.remaining,
        "limit": rate.limit,
        "reset_at": rate.reset,
    }

def should_pause_for_rate_limit(remaining: int, threshold: int = 100) -> bool:
    """Check if we should pause sync due to low rate limit."""
    return remaining < threshold

def wait_for_rate_limit_reset(reset_at: datetime) -> None:
    """Wait until rate limit resets."""
    wait_seconds = (reset_at - datetime.now(UTC)).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds + 1)
```

**Acceptance Criteria:**
- [ ] Create github_rate_limit.py service
- [ ] Implement check_rate_limit() function
- [ ] Implement should_pause_for_rate_limit() function
- [ ] Implement wait_for_rate_limit_reset() function
- [ ] Add TDD tests

#### 1.3 Integrate rate limit into sync
**Effort:** M | **File:** `apps/integrations/services/github_sync.py`

Modify `_process_prs()` to check rate limit after each PR:

**Acceptance Criteria:**
- [ ] Check rate limit after each PR sync
- [ ] Update TrackedRepository.rate_limit_remaining
- [ ] Pause sync if remaining < 100
- [ ] Log rate limit status

### Phase 2: Background Historical Sync

#### 2.1 Add progress tracking fields
**Effort:** S | **File:** `apps/integrations/models.py`

```python
class TrackedRepository(BaseTeamModel):
    # ... existing fields ...

    # Progress tracking
    sync_progress = models.IntegerField(
        default=0,
        help_text="Sync progress percentage (0-100)"
    )
    sync_prs_total = models.IntegerField(
        null=True, blank=True,
        help_text="Total PRs to sync"
    )
    sync_prs_completed = models.IntegerField(
        default=0,
        help_text="PRs synced so far"
    )
    sync_started_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When sync started"
    )
```

**Acceptance Criteria:**
- [ ] Add sync_progress field (0-100)
- [ ] Add sync_prs_total field
- [ ] Add sync_prs_completed field
- [ ] Add sync_started_at field
- [ ] Create and run migration

#### 2.2 Create initial historical sync task
**Effort:** M | **File:** `apps/integrations/tasks.py`

```python
@shared_task(bind=True, max_retries=3)
def sync_repository_initial_task(self, repo_id: int, days_back: int = 30) -> dict:
    """Sync historical data for a newly tracked repository."""
    # 1. Get repo and set status to SYNCING
    # 2. Fetch PR count first (for progress tracking)
    # 3. Sync PRs with progress updates
    # 4. On complete: trigger insights aggregation
    # 5. Send email notification
    pass
```

**Acceptance Criteria:**
- [ ] Create sync_repository_initial_task
- [ ] Accept days_back parameter (default 30)
- [ ] Track progress during sync
- [ ] Handle rate limits gracefully
- [ ] Trigger post-sync jobs on completion

#### 2.3 Update repo tracking view
**Effort:** S | **File:** `apps/integrations/views/github.py`

Change `github_repo_toggle` to queue background task instead of sync:

```python
def github_repo_toggle(request, team_slug, repo_id):
    # ... create webhook ...
    # ... create TrackedRepository ...

    # Queue background sync instead of blocking
    sync_repository_initial_task.delay(tracked_repo.id, days_back=30)

    # Return immediately with "syncing" status
```

**Acceptance Criteria:**
- [ ] Remove synchronous sync_repository_history() call
- [ ] Queue sync_repository_initial_task.delay()
- [ ] Return immediately to user
- [ ] Show "syncing" status in response

### Phase 3: Configurable Sync Depth

#### 3.1 Add sync options to UI
**Effort:** S | **File:** `apps/integrations/templates/integrations/partials/github_repo_card.html`

Add checkbox or dropdown for sync depth:
- Default: Last 30 days
- Optional: Full history (may take longer)

**Acceptance Criteria:**
- [ ] Add sync depth selector to repo card
- [ ] Default to 30 days
- [ ] Pass selection to toggle endpoint

#### 3.2 Update toggle endpoint
**Effort:** S | **File:** `apps/integrations/views/github.py`

Accept and use sync_depth parameter:

**Acceptance Criteria:**
- [ ] Accept sync_depth parameter (30 or None for all)
- [ ] Pass to sync_repository_initial_task

### Phase 4: Email Notifications

#### 4.1 Create sync notification template
**Effort:** S | **File:** `templates/emails/sync_complete.html`

Email template for sync completion:
- "Your repository {repo_name} is now synced"
- Link to dashboard
- Summary of data imported (X PRs, Y reviews)

**Acceptance Criteria:**
- [ ] Create HTML email template
- [ ] Include repo name and sync summary
- [ ] Include link to dashboard

#### 4.2 Create notification service
**Effort:** M | **File:** `apps/integrations/services/sync_notifications.py`

```python
def send_sync_complete_notification(tracked_repo: TrackedRepository, stats: dict) -> None:
    """Send email notification when sync completes."""
    user = tracked_repo.integration.credential.connected_by
    if not user or not user.email:
        return

    send_mail(
        subject=f"Your repository {tracked_repo.full_name} is ready",
        message="...",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=render_to_string("emails/sync_complete.html", {...}),
    )
```

**Acceptance Criteria:**
- [ ] Create send_sync_complete_notification function
- [ ] Send to user who connected the integration
- [ ] Include sync stats
- [ ] Handle missing email gracefully

#### 4.3 Integrate notification into sync task
**Effort:** S | **File:** `apps/integrations/tasks.py`

Call notification service when sync completes:

**Acceptance Criteria:**
- [ ] Call send_sync_complete_notification after successful sync
- [ ] Include stats in notification

### Phase 5: UI Progress Display

#### 5.1 Add progress indicator to repo list
**Effort:** S | **File:** `apps/integrations/templates/integrations/github_repos.html`

Show sync progress when status is SYNCING:
- Progress bar (0-100%)
- "Syncing 45/100 PRs..."

**Acceptance Criteria:**
- [ ] Display progress bar for syncing repos
- [ ] Show PR count progress
- [ ] Auto-refresh or use HTMX polling

#### 5.2 Create progress API endpoint
**Effort:** S | **File:** `apps/integrations/views/github.py`

```python
def github_repo_sync_progress(request, team_slug, repo_id):
    """Return sync progress for HTMX polling."""
    repo = get_object_or_404(TrackedRepository, id=repo_id)
    return render(request, "integrations/partials/sync_progress.html", {
        "repo": repo,
    })
```

**Acceptance Criteria:**
- [ ] Create progress endpoint
- [ ] Return progress partial for HTMX
- [ ] Include sync_progress, sync_prs_completed, sync_prs_total

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Rate limit hits during large syncs | High | Medium | Implement rate limit tracking and pausing |
| Long sync times for large repos | Medium | Medium | Background processing, progress feedback |
| Email delivery failures | Low | Low | Use reliable email service, log failures |
| User confusion about sync status | Medium | Medium | Clear UI progress indicators |

---

## Success Metrics

1. **Zero rate limit errors** - No 403 errors during sync
2. **Sub-second repo tracking** - UI responds instantly when tracking repo
3. **Email notification delivery** - >95% delivery rate
4. **Progress visibility** - Users can see sync progress

---

## Required Resources

### Dependencies
- Django email backend configured (already exists)
- Celery for background tasks (already exists)
- HTMX for progress polling (already exists)

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `apps/integrations/models.py` | Modify | Add rate limit and progress fields |
| `apps/integrations/services/github_rate_limit.py` | Create | Rate limit utilities |
| `apps/integrations/services/sync_notifications.py` | Create | Email notifications |
| `apps/integrations/tasks.py` | Modify | Add initial sync task |
| `apps/integrations/views/github.py` | Modify | Queue background sync |
| `templates/emails/sync_complete.html` | Create | Email template |
| `apps/integrations/templates/integrations/partials/sync_progress.html` | Create | Progress UI |

---

## Migration Strategy

1. Add new fields with null=True, blank=True
2. Deploy code changes
3. Existing repos continue to work
4. New repos use improved flow
5. Backfill progress fields for existing repos (optional)
