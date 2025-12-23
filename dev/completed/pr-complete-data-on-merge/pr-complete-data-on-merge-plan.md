# PR Complete Data Fetch on Merge - Implementation Plan

**Last Updated:** 2025-12-22

## Executive Summary

Implement a background task that fetches complete PR data (commits, files, check runs, comments) when a PR is merged via webhook. This fills the data gap between real-time webhook events and periodic sync, ensuring iteration metrics are available immediately after merge.

## Problem Statement

### Current State
- **Webhooks** provide real-time PR state changes but only capture:
  - PullRequest basic fields (title, state, additions, deletions, timestamps)
  - PRReview records (when `pull_request_review` event fires)

- **Missing from webhooks:**
  - Commits (no `push` event subscription, hard to correlate to PRs)
  - Files changed (not in webhook payload)
  - Check runs (CI/CD status)
  - Comments (issue and review comments)
  - Iteration metrics (review_rounds, commits_after_first_review, avg_fix_response_hours, total_comments)

- **Historical sync** fetches everything but runs periodically (daily), causing delay

### Proposed Solution
When a PR is merged (webhook `action=closed` + `merged=true`), queue a background Celery task to:
1. Fetch commits via GitHub API
2. Fetch files via GitHub API
3. Fetch check runs via GitHub API
4. Fetch comments (issue + review) via GitHub API
5. Calculate iteration metrics

This gives us complete data within seconds of merge.

## Current State Analysis

### Data Flow
```
Webhook arrives → processors.py:handle_pull_request_event()
                 → Creates/updates PullRequest
                 → If merged: triggers send_pr_surveys_task + post_survey_comment_task
```

### Key Files
| File | Purpose |
|------|---------|
| `apps/metrics/processors.py` | Webhook event handlers |
| `apps/integrations/tasks.py` | Celery tasks |
| `apps/integrations/services/github_sync.py` | Sync functions for commits, files, check runs, comments |
| `apps/web/views.py` | Webhook endpoint |

### Existing Sync Functions (can be reused)
- `sync_pr_commits()` - Fetches commits for a PR
- `sync_pr_files()` - Fetches files changed in a PR
- `sync_pr_check_runs()` - Fetches CI/CD check runs
- `sync_pr_issue_comments()` - Fetches general PR comments
- `sync_pr_review_comments()` - Fetches inline code comments
- `calculate_pr_iteration_metrics()` - Calculates iteration metrics from synced data

## Proposed Future State

### Architecture
```
Webhook arrives → processors.py:handle_pull_request_event()
                 → Creates/updates PullRequest
                 → If merged:
                     → triggers send_pr_surveys_task
                     → triggers post_survey_comment_task
                     → NEW: triggers fetch_pr_complete_data_task ←
```

### New Task Flow
```
fetch_pr_complete_data_task(pr_id)
    │
    ├─→ Look up PR and TrackedRepository
    ├─→ Get access token (decrypted)
    │
    ├─→ sync_pr_commits()           → Creates Commit records
    ├─→ sync_pr_files()             → Creates PRFile records
    ├─→ sync_pr_check_runs()        → Creates PRCheckRun records
    ├─→ sync_pr_issue_comments()    → Creates PRComment (type=issue)
    ├─→ sync_pr_review_comments()   → Creates PRComment (type=review)
    │
    └─→ calculate_pr_iteration_metrics()  → Updates PR metrics
```

## Implementation Phases

### Phase 1: Create Celery Task (Effort: M)

**Location:** `apps/integrations/tasks.py`

Create new task `fetch_pr_complete_data_task`:
- Accepts `pr_id: int`
- Looks up PullRequest and associated TrackedRepository
- Gets decrypted access token
- Calls sync functions in sequence
- Handles errors gracefully (log but don't crash)
- Has retry logic with exponential backoff

### Phase 2: Integrate with Webhook Handler (Effort: S)

**Location:** `apps/metrics/processors.py`

Modify `_trigger_pr_surveys_if_merged()`:
- Add call to `fetch_pr_complete_data_task.delay(pr.id)`
- Independent of other tasks (wrapped in try/except)

### Phase 3: Add Tests (Effort: M)

**Locations:**
- `apps/integrations/tests/test_fetch_pr_complete_data.py` (new)
- `apps/metrics/tests/test_pr_processor.py` (add test cases)

Tests needed:
- Task successfully fetches all data types
- Task handles missing TrackedRepository gracefully
- Task handles API errors with retry
- Task is dispatched on PR merge
- Task NOT dispatched on PR close without merge
- Task independent of survey task failures

## Detailed Tasks

### 1. Create fetch_pr_complete_data_task

**File:** `apps/integrations/tasks.py`

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_pr_complete_data_task(self, pr_id: int) -> dict:
    """Fetch complete PR data (commits, files, check runs, comments) after merge.

    Triggered when a PR is merged via webhook to fill data gaps.
    """
```

**Acceptance Criteria:**
- [ ] Task fetches commits, files, check runs, comments
- [ ] Task calculates iteration metrics after sync
- [ ] Task handles missing TrackedRepository (logs warning, returns error dict)
- [ ] Task has retry logic (3 retries, exponential backoff)
- [ ] Task logs to Sentry on permanent failure
- [ ] Task returns dict with sync counts and errors

### 2. Wire up task in webhook processor

**File:** `apps/metrics/processors.py`

**Acceptance Criteria:**
- [ ] Task dispatched in `_trigger_pr_surveys_if_merged()` on merge
- [ ] Task dispatch wrapped in try/except (doesn't break webhook)
- [ ] Task independent of other tasks

### 3. Write unit tests for new task

**File:** `apps/integrations/tests/test_fetch_pr_complete_data.py`

**Acceptance Criteria:**
- [ ] Test task calls all sync functions
- [ ] Test task handles missing PR gracefully
- [ ] Test task handles missing TrackedRepository gracefully
- [ ] Test task retries on GitHub API error
- [ ] Test iteration metrics calculated after sync

### 4. Write integration tests for webhook dispatch

**File:** `apps/metrics/tests/test_pr_processor.py`

**Acceptance Criteria:**
- [ ] Test task dispatched on merge
- [ ] Test task NOT dispatched on close without merge
- [ ] Test task independent of survey task failures

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub rate limiting | Medium | Medium | Task has retry logic; check rate limit before processing |
| Task queue backlog during high merge volume | Low | Low | Task is lightweight (~5 API calls); use separate queue if needed |
| TrackedRepository not found | Low | Low | Graceful handling with warning log |
| Partial data fetch (some calls fail) | Medium | Low | Each sync function has its own error handling; partial data better than none |

## Success Metrics

1. **Immediate data availability:** Iteration metrics available within 60s of merge
2. **No webhook failures:** Task errors don't break webhook response
3. **High success rate:** >99% of merged PRs have complete data within 5 minutes
4. **Test coverage:** All new code has tests (TDD approach)

## Dependencies

### Internal
- `apps/integrations/services/github_sync.py` - Existing sync functions
- `apps/integrations/models.py` - TrackedRepository model
- `apps/metrics/models` - PullRequest, Commit, PRFile, PRCheckRun, PRComment

### External
- GitHub API (PyGithub library)
- Celery task queue

## API Call Breakdown

For a single merged PR, the task makes:
- 1 call to get commits (paginated if >100)
- 1 call to get files (paginated if >100)
- 1 call to get check runs for head commit
- 1 call to get issue comments
- 1 call to get review comments

Total: ~5-10 API calls per merged PR (within GitHub's limits)
