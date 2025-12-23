# PR Complete Data Fetch on Merge - Tasks

**Last Updated:** 2025-12-22

## Progress Overview

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Create Celery Task | Not Started | 0/4 |
| Phase 2: Integrate with Webhook | Not Started | 0/2 |
| Phase 3: Add Tests | Not Started | 0/6 |

**Total Progress:** 0/12 tasks complete

---

## Phase 1: Create Celery Task

**File:** `apps/integrations/tasks.py`

- [ ] **1.1** Create `fetch_pr_complete_data_task` function signature
  - Effort: S
  - Acceptance: Task accepts `pr_id: int`, returns `dict`
  - Dependencies: None

- [ ] **1.2** Implement PR and TrackedRepository lookup
  - Effort: S
  - Acceptance: Task finds PR by ID, finds matching TrackedRepository, handles missing gracefully
  - Dependencies: 1.1

- [ ] **1.3** Implement data sync calls
  - Effort: M
  - Acceptance: Task calls `sync_pr_commits`, `sync_pr_files`, `sync_pr_check_runs`, `sync_pr_issue_comments`, `sync_pr_review_comments`
  - Dependencies: 1.2

- [ ] **1.4** Implement iteration metrics calculation and error handling
  - Effort: S
  - Acceptance: Task calls `calculate_pr_iteration_metrics`, has retry logic, logs to Sentry on failure
  - Dependencies: 1.3

---

## Phase 2: Integrate with Webhook Handler

**File:** `apps/metrics/processors.py`

- [ ] **2.1** Add task import and dispatch in `_trigger_pr_surveys_if_merged()`
  - Effort: S
  - Acceptance: Task dispatched when `action=="closed"` and `is_merged==True`
  - Dependencies: 1.4

- [ ] **2.2** Wrap dispatch in try/except for independence
  - Effort: S
  - Acceptance: Task dispatch failure doesn't break webhook response or other tasks
  - Dependencies: 2.1

---

## Phase 3: Add Tests

### Unit Tests for Task

**File:** `apps/integrations/tests/test_fetch_pr_complete_data.py` (new)

- [ ] **3.1** Test task calls all sync functions with correct parameters
  - Effort: M
  - Acceptance: Mock sync functions, verify called with correct PR, access_token, repo_full_name
  - Dependencies: 1.4

- [ ] **3.2** Test task handles missing PullRequest gracefully
  - Effort: S
  - Acceptance: Returns error dict, doesn't raise exception
  - Dependencies: 1.4

- [ ] **3.3** Test task handles missing TrackedRepository gracefully
  - Effort: S
  - Acceptance: Returns error dict with "TrackedRepository not found"
  - Dependencies: 1.4

- [ ] **3.4** Test task calculates iteration metrics after sync
  - Effort: S
  - Acceptance: `calculate_pr_iteration_metrics` called after all sync functions
  - Dependencies: 1.4

### Integration Tests for Webhook Dispatch

**File:** `apps/metrics/tests/test_pr_processor.py`

- [ ] **3.5** Test task dispatched on PR merge
  - Effort: S
  - Acceptance: Mock task, verify `.delay()` called with PR ID when merged
  - Dependencies: 2.2

- [ ] **3.6** Test task NOT dispatched on PR close without merge
  - Effort: S
  - Acceptance: Mock task, verify `.delay()` NOT called when `merged=False`
  - Dependencies: 2.2

---

## Implementation Notes

### Task Structure Template

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_pr_complete_data_task(self, pr_id: int) -> dict:
    """Fetch complete PR data (commits, files, check runs, comments) after merge."""
    from apps.integrations.models import TrackedRepository
    from apps.integrations.services.github_sync import (
        calculate_pr_iteration_metrics,
        sync_pr_check_runs,
        sync_pr_commits,
        sync_pr_files,
        sync_pr_issue_comments,
        sync_pr_review_comments,
    )
    from apps.metrics.models import PullRequest

    # 1. Look up PR
    try:
        pr = PullRequest.objects.get(id=pr_id)
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pr_id} not found")
        return {"error": f"PullRequest with id {pr_id} not found"}

    # 2. Look up TrackedRepository
    tracked_repo = TrackedRepository.objects.filter(
        team=pr.team,
        full_name=pr.github_repo,
        is_active=True
    ).first()

    if not tracked_repo:
        logger.warning(f"TrackedRepository not found for {pr.github_repo}")
        return {"error": f"TrackedRepository not found for {pr.github_repo}"}

    # 3. Get access token and PR number
    access_token = tracked_repo.integration.credential.access_token
    # Note: github_pr_id is the unique ID, we need to fetch PR to get number
    # For now, use github_pr_id as number (they're same in most cases)
    # TODO: Consider adding github_pr_number field to model
    pr_number = pr.github_pr_id

    # 4. Sync all data
    errors = []
    result = {
        "commits_synced": sync_pr_commits(pr, pr_number, access_token, pr.github_repo, pr.team, errors),
        "files_synced": sync_pr_files(pr, pr_number, access_token, pr.github_repo, pr.team, errors),
        "check_runs_synced": sync_pr_check_runs(pr, pr_number, access_token, pr.github_repo, pr.team, errors),
        "issue_comments_synced": sync_pr_issue_comments(pr, pr_number, access_token, pr.github_repo, pr.team, errors),
        "review_comments_synced": sync_pr_review_comments(pr, pr_number, access_token, pr.github_repo, pr.team, errors),
        "errors": errors,
    }

    # 5. Calculate iteration metrics
    calculate_pr_iteration_metrics(pr)

    logger.info(f"Fetched complete data for PR {pr_id}: {result}")
    return result
```

### Webhook Integration Template

```python
# In _trigger_pr_surveys_if_merged()

# NEW: Fetch complete PR data in background
try:
    from apps.integrations.tasks import fetch_pr_complete_data_task

    fetch_pr_complete_data_task.delay(pr.id)
    logger.debug(f"Dispatched fetch_pr_complete_data_task for PR {pr.id}")
except Exception as e:
    # Log error but don't break webhook response
    logger.error(f"Failed to dispatch fetch_pr_complete_data_task for PR {pr.id}: {e}")
```

---

## Blockers & Questions

- [ ] **Blocker:** None currently identified
- [ ] **Question:** Should we add `github_pr_number` field to PullRequest model?
  - Current decision: No, use `github_pr_id` (works for most repos)
  - Revisit if issues arise

---

## Completion Checklist

Before marking complete:

- [ ] All tests pass (`make test`)
- [ ] Code formatted (`make ruff`)
- [ ] Manual verification: Merge a PR, check data populated within 60s
- [ ] No Sentry errors in staging
