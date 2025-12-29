# Onboarding Sync & UX Fixes Implementation Plan

**Last Updated: 2025-12-29**

## Executive Summary

Fix two critical issues in the onboarding flow:
1. **Celery tasks not executing** - Sync tasks are queued but fail silently
2. **Missing loading states** - No feedback when fetching repos (takes several seconds)

These issues cause user confusion when the UI shows "Sync Complete" but no data is actually synced.

## Current State Analysis

### Issue 1: Celery Task Execution Problems

**Observed Symptoms:**
- Member sync task queued but didn't run
- PR sync status remains `pending`
- Manual execution works (`sync_github_members(team)` succeeds)
- Celery workers are running (9 processes visible)

**Root Cause Investigation:**
The sync works when called directly but fails via Celery. Potential causes:
1. Task serialization issues with model objects
2. Token encryption/decryption in task context
3. Celery task routing or queue configuration
4. Task timeouts or memory issues

**Key Finding from `apps/integrations/tasks.py`:**
```python
# Line 2093 - Token retrieved in task context
github_token = integration.credential.access_token
```

The `EncryptedTextField` descriptor should auto-decrypt, but in Celery task context this might behave differently due to lazy loading or Django model state.

### Issue 2: Missing Loading States in Onboarding

**Current Flow (`select_repos.html`):**
1. User arrives at page
2. `get_organization_repositories()` called synchronously (lines 289-293)
3. Takes 2-5 seconds for large orgs
4. No loading indicator - page appears frozen

**Current Flow (`sync_progress.html`):**
1. Shows "Syncing Your Data" with progress bar
2. Calls `start_sync` API which queues Celery task
3. Polls `/celery-progress/{task_id}/` for status
4. If task fails silently, UI shows "complete" without data

## Proposed Future State

### Goal 1: Reliable Sync Execution
- Sync tasks complete successfully when triggered
- Progress accurately reflects actual sync state
- Errors are captured and displayed to users

### Goal 2: Responsive Loading States
- Loading spinner when fetching repos
- Accurate sync status with error handling
- Clear feedback on what's happening

## Implementation Phases

### Phase 1: Debug & Fix Celery Task Execution (Priority: P0, Effort: M)

**Objective:** Ensure sync tasks execute reliably via Celery

**Tasks:**

1.1 **Add comprehensive logging to sync tasks**
- Log task start, progress, completion, errors
- Track token access in task context
- File: `apps/integrations/tasks.py`

1.2 **Add error handling for token access in tasks**
- Verify token is accessible in Celery context
- Add explicit try/catch around credential access
- Log decryption status

1.3 **Add fallback sync mechanism**
- If Celery task fails, provide sync button to retry
- Add manual sync endpoint for debugging
- File: `apps/onboarding/views.py`

1.4 **Test sync task in isolation**
- Create test that runs sync task synchronously
- Verify token handling works in test context

### Phase 2: Add Loading States to Onboarding (Priority: P1, Effort: S)

**Objective:** Show loading indicators during async operations

**Tasks:**

2.1 **Add loading state to select_repos page**
- Show spinner while fetching repos from GitHub API
- Use HTMX to load repos asynchronously
- Files: `templates/onboarding/select_repos.html`, `apps/onboarding/views.py`

2.2 **Improve sync_progress error handling**
- Detect failed/stuck sync tasks
- Show error state with retry option
- Files: `templates/onboarding/sync_progress.html`, `apps/onboarding/views.py`

2.3 **Add sync status polling endpoint**
- Create endpoint to check actual sync status from DB
- Compare DB state vs Celery task state
- File: `apps/onboarding/views.py`

### Phase 3: Integration Tests (Priority: P1, Effort: S)

**Objective:** Prevent regression

**Tasks:**

3.1 **Test Celery task execution**
- Test `sync_historical_data_task` with real data
- Verify progress reporting works

3.2 **Test loading states**
- Verify spinner appears during repo fetch
- Test error handling displays

## Detailed Tasks

### Task 1.1: Add Comprehensive Logging
**File:** `apps/integrations/tasks.py`
**Effort:** S
**Acceptance Criteria:**
- [ ] Log at task entry with team_id and repo_ids
- [ ] Log token access success/failure
- [ ] Log each repo sync start/complete
- [ ] Log final result with PR counts

### Task 1.2: Fix Token Access in Celery Context
**File:** `apps/integrations/tasks.py`
**Effort:** M
**Acceptance Criteria:**
- [ ] Explicit token decryption in task
- [ ] Clear error if token unavailable
- [ ] Task fails gracefully with useful error message

### Task 2.1: Add Loading State to Repos Page
**Files:**
- `apps/onboarding/views.py`
- `templates/onboarding/select_repos.html`
**Effort:** M
**Acceptance Criteria:**
- [ ] Show loading spinner on page load
- [ ] Fetch repos asynchronously via HTMX
- [ ] Display repos when loaded
- [ ] Show error if fetch fails

### Task 2.2: Improve Sync Progress Error Handling
**Files:**
- `templates/onboarding/sync_progress.html`
- `apps/onboarding/views.py`
**Effort:** S
**Acceptance Criteria:**
- [ ] Detect stuck/failed sync (no progress for 30s)
- [ ] Show error message with retry button
- [ ] Allow manual sync trigger

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token encryption issues in Celery | Medium | High | Add explicit decrypt call with logging |
| Redis connection issues | Low | High | Add Redis health check, fallback to sync execution |
| Long-running sync timeouts | Medium | Medium | Add progress checkpoints, allow resume |
| Breaking existing sync flow | Low | High | Maintain backward compatibility, feature flag |

## Success Metrics

1. **Sync Success Rate**: 95%+ of syncs complete successfully
2. **Loading UX**: Zero "frozen page" reports during onboarding
3. **Error Visibility**: 100% of sync failures show user-friendly error
4. **Time to First Insight**: <30s from sync start to first PR visible

## Required Resources

### Dependencies
- Celery with Redis broker (already configured)
- celery-progress package (already installed)
- HTMX (already available)

### Key Files
| File | Purpose |
|------|---------|
| `apps/integrations/tasks.py` | Celery sync tasks |
| `apps/onboarding/views.py` | Onboarding views |
| `templates/onboarding/select_repos.html` | Repo selection page |
| `templates/onboarding/sync_progress.html` | Sync status page |
| `apps/integrations/services/github_sync.py` | Sync service |
