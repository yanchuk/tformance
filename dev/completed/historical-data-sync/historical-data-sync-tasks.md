# Phase 2.5: Historical Data Sync - Task Checklist

> Last Updated: 2025-12-11

## Overview

Total tasks: 32
Estimated effort: Medium (Phase complexity: M)

---

## 2.5.1 GitHub API Functions for Historical Data [Effort: M]

### PR List Endpoint
- [ ] Create `apps/integrations/services/github_sync.py`
- [ ] Add `get_repository_pull_requests(access_token, repo_full_name, state, since, per_page)` function
- [ ] Use paginated request helper from github_oauth.py
- [ ] Support `state` parameter ("all", "open", "closed")
- [ ] Support `since` parameter for date filtering (via `updated` sort + client-side filter)
- [ ] Return list of PR dictionaries

### PR Reviews Endpoint
- [ ] Add `get_pull_request_reviews(access_token, repo_full_name, pr_number)` function
- [ ] Handle pagination for repos with many reviews per PR
- [ ] Return list of review dictionaries

### Tests
- [ ] Test `get_repository_pull_requests` returns paginated results
- [ ] Test `get_repository_pull_requests` filters by state
- [ ] Test `get_pull_request_reviews` returns reviews for PR
- [ ] Test API error handling (403, 404, rate limit)

---

## 2.5.2 Historical Sync Service [Effort: M]

### Main Sync Function
- [ ] Add `sync_repository_history(tracked_repo, days_back=90)` function
- [ ] Get access token from integration credential (decrypt)
- [ ] Fetch PRs updated in last N days
- [ ] Filter out PRs created before cutoff date (API returns by updated, we want created)

### PR Processing
- [ ] For each PR, create/update PullRequest record using `update_or_create`
- [ ] Map GitHub API fields to PullRequest model fields
- [ ] Look up author by github_id, handle missing author gracefully
- [ ] Calculate cycle_time_hours for merged PRs
- [ ] Detect is_revert and is_hotfix from title

### Review Processing
- [ ] For each PR, fetch reviews from API
- [ ] Create/update PRReview records
- [ ] Look up reviewer by github_id
- [ ] Map review state (APPROVED → approved, etc.)
- [ ] Update PR's first_review_at if earlier than existing

### Calculate Review Time
- [ ] After processing reviews, calculate review_time_hours
- [ ] Only calculate if first_review_at exists
- [ ] Update PullRequest record

### Sync Status Updates
- [ ] Update `TrackedRepository.last_sync_at` after successful sync
- [ ] Update `GitHubIntegration.sync_status` to "syncing" at start
- [ ] Update `GitHubIntegration.sync_status` to "complete" on success
- [ ] Update `GitHubIntegration.sync_status` to "error" on failure

### Error Handling
- [ ] Continue processing if individual PR fails
- [ ] Collect errors and return in result dict
- [ ] Log errors for debugging

### Tests
- [ ] Test sync creates PullRequest records
- [ ] Test sync creates PRReview records
- [ ] Test sync calculates cycle_time_hours correctly
- [ ] Test sync calculates review_time_hours correctly
- [ ] Test sync updates first_review_at
- [ ] Test sync continues on individual PR error
- [ ] Test sync updates last_sync_at
- [ ] Test sync updates sync_status

---

## 2.5.3 Sync Trigger Integration [Effort: S]

### Auto-Trigger on Track
- [ ] Modify `github_repo_toggle` to trigger sync after tracking
- [ ] Call sync function after webhook registration
- [ ] Handle sync errors gracefully (don't fail toggle)

### Manual Sync View
- [ ] Create `github_repo_sync` view function
- [ ] Accept POST requests only
- [ ] Verify user has permission (team admin)
- [ ] Find TrackedRepository by repo_id and team
- [ ] Call sync function
- [ ] Return success/error response

### URL Configuration
- [ ] Add URL pattern: `github/repos/<int:repo_id>/sync/`
- [ ] Use `@login_and_team_required` decorator

### Tests
- [ ] Test toggle triggers sync
- [ ] Test manual sync endpoint requires authentication
- [ ] Test manual sync returns success
- [ ] Test manual sync handles errors gracefully

---

## 2.5.4 UI Updates [Effort: S]

### Repo Card Enhancement
- [ ] Add sync status indicator (synced/not synced)
- [ ] Show last_sync_at timestamp on hover
- [ ] Add "Sync" button with refresh icon
- [ ] Use HTMX for async sync trigger

### Sync Feedback
- [ ] Show loading state while syncing
- [ ] Show success message after sync
- [ ] Show error message if sync fails

---

## 2.5.5 Celery Task (Optional/Deferred) [Effort: S]

### Background Task
- [ ] Create `apps/integrations/tasks.py`
- [ ] Add `sync_repository_history_task(tracked_repo_id)` task
- [ ] Add `sync_all_pending_repositories_task()` for batch sync
- [ ] Handle task errors and retries

### Integration
- [ ] Update views to use async task instead of sync call
- [ ] Add task status tracking if needed

---

## Post-Implementation

### Documentation
- [ ] Update historical-data-sync-tasks.md to mark complete
- [ ] Update historical-data-sync-context.md with implementation notes
- [ ] Document any configuration options added

### Cleanup
- [ ] Run ruff format and lint
- [ ] Ensure all tests pass
- [ ] Remove any debug logging

---

## Completion Criteria

Phase 2.5 is complete when:
1. [ ] Tracking a repo automatically syncs historical PRs
2. [ ] Manual "Sync" button works for re-sync
3. [ ] PRs from last 90 days appear in database
4. [ ] Reviews are linked to PRs
5. [ ] cycle_time_hours and review_time_hours calculated
6. [ ] last_sync_at updated on TrackedRepository
7. [ ] All tests pass
8. [ ] Code reviewed and merged

---

## Quick Reference

### New URLs to implement:
```
/a/{team}/integrations/github/repos/{repo_id}/sync/  → github_repo_sync
```

### New files to create:
```
apps/integrations/services/github_sync.py      → Sync API functions & service
apps/integrations/tests/test_github_sync.py    → Sync tests
apps/integrations/tasks.py                     → Celery tasks (optional)
```

### Key imports:
```python
from apps.integrations.models import GitHubIntegration, TrackedRepository
from apps.integrations.services.encryption import decrypt
from apps.integrations.services.github_sync import (
    get_repository_pull_requests,
    get_pull_request_reviews,
    sync_repository_history,
)
from apps.metrics.models import PullRequest, PRReview, TeamMember
from apps.metrics.processors import (
    _parse_github_timestamp,
    _determine_pr_state,
    _calculate_cycle_time_hours,
    _calculate_time_diff_hours,
    _get_team_member_by_github_id,
)
```

### TDD Reminder:
Follow Red-Green-Refactor cycle for each feature:
1. Write failing test
2. Implement minimum code to pass
3. Refactor while keeping tests green
