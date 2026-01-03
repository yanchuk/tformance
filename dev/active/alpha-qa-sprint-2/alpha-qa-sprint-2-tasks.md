# Alpha QA Sprint 2 - Task Checklist

**Last Updated:** 2026-01-03 (Session 2)

## Overview

| Phase | Issues | Status |
|-------|--------|--------|
| Phase 1: Pipeline Fix | A-027 | ✅ Done (test updated) |
| Phase 2: Feature Flags | A-021, A-026 | ✅ Done |
| Phase 3: Sync Progress | A-020, A-022, A-023 | 🟡 A-020 In Progress |
| Phase 4: Member Sync | A-025 | ⬜ Not Started |
| Phase 5: Investigation | A-024 | ⬜ Not Started |

---

## Phase 1: Critical Pipeline Fix (A-027)

### 1.1 Fix LLM Task Error Handling
- [x] Update `apps/metrics/tasks.py` to raise ValueError on missing GROQ_API_KEY
- [x] Update test to expect ValueError instead of error dict
- [x] Run tests: `.venv/bin/pytest apps/metrics/tests/test_llm_tasks.py -v`
- [x] Verify test passes

### 1.2 Document Celery Configuration
- [ ] Kill any extra Celery workers
- [ ] Add note to `dev/guides/` about single worker requirement
- [ ] Update Makefile if needed

### 1.3 Add Pipeline Stuck Detection (Optional)
- [ ] Add 15-minute timeout check in `onboarding_pipeline.py`
- [ ] If stuck, set status to "failed"
- [ ] Add test for timeout behavior

---

## Phase 2: Feature Flag Compliance (A-021, A-026)

### 2.1 Fix "Continue to Jira" Button (A-021) ✅ DONE
- [x] Find button in `templates/onboarding/sync_progress.html` (NOT sync.html)
- [x] Add `{% if enable_jira_integration %}` conditional to actions section (lines 70-84)
- [x] Add conditional to completion section (lines 86-106)
- [x] Add conditional to error/stalled section (lines 118-132)
- [x] Run tests: onboarding tests passing

### 2.2 Fix "Enhance Your Insights" Banner (A-026) ✅ DONE
- [x] Find banner in `templates/web/components/setup_prompt.html`
- [x] Add `{% with show_jira=enable_jira_integration %}` wrapper
- [x] Update all conditions to check both enabled AND not connected
- [x] Run tests: passing

---

## Phase 3: Sync Progress UI (A-020, A-022, A-023)

### 3.1 Fix Main Progress Bar (A-020) 🟡 ROOT CAUSE FOUND
- [x] Inspect `templates/onboarding/sync_progress.html` for progress bar binding
- [x] Check JS code - main bar polls `/celery-progress/<task_id>/`
- [x] Check `sync_status` endpoint - returns DB data for per-repo badges
- [x] **ROOT CAUSE:** Task updates DB but doesn't call `self.update_state()` for celery-progress
- [ ] **FIX NEEDED:** Add `self.update_state()` calls to `apps/integrations/tasks.py:sync_historical_data_task`
- [ ] Run test and verify

**Next Step:** Add this code to sync_historical_data_task around line 2237 (in repo loop):
```python
# Report overall progress to celery-progress endpoint
self.update_state(
    state='PROGRESS',
    meta={
        'current': idx,
        'total': total_repos,
        'description': f'Syncing {repo.full_name}...'
    }
)
```

### 3.2 Fix Stall Detection (A-022)
- [x] Find stall detection JavaScript in sync_progress.html (lines 157-161, 431-440)
- [x] Confirmed: `lastProgressTime` and `lastProgressPercent` variables exist
- [x] Stall logic at line 437 checks if progress hasn't changed
- [ ] **VERIFY:** Test if stall detection resets properly (may already be working)
- [ ] Run manual test to confirm

### 3.3 Add HTMX Polling to Sync Widget (A-023)
- [ ] Find sync widget template
- [ ] Add `hx-trigger="every 3s"` to widget container
- [ ] Add `hx-get` pointing to sync status endpoint
- [ ] Test auto-update behavior
- [ ] Stop polling when sync complete

---

## Phase 4: Member Sync (A-025)

### 4.1 Debug OAuth Callback
- [ ] Check `apps/integrations/views/github.py` for member sync call
- [ ] Add logging to `_sync_github_members_after_connection`
- [ ] Verify task is queued
- [ ] Check task execution

### 4.2 Add Member Sync to Pipeline (if needed)
- [ ] If OAuth callback doesn't trigger sync, add to pipeline
- [ ] Add `sync_github_members_task` after `sync_historical_data_task`
- [ ] Test member count after sync
- [ ] Verify Integration Status shows correct count

---

## Phase 5: Investigation (A-024)

### 5.1 Investigate PR Visibility
- [ ] Query database for PR count by team
- [ ] Check default date filter (30 days)
- [ ] Try 90-day filter on PR list
- [ ] Document findings

### 5.2 Fix if Needed
- [ ] If PRs exist but don't show, fix filter logic
- [ ] If PRs not syncing, fix sync logic
- [ ] Add test for PR visibility

---

## Testing Checklist

### Unit Tests
- [x] `apps/metrics/tests/test_llm_tasks.py` - All pass
- [x] `apps/onboarding/tests/` - All pass (verified during A-021)
- [ ] `apps/integrations/tests/` - Pending verification

### E2E Tests
- [ ] `make e2e-smoke` - Pass
- [ ] `make e2e` - Full suite pass

### Manual QA
- [ ] Complete onboarding flow with fresh team
- [ ] Verify LLM processing completes
- [x] Verify no Jira/Slack references appear (fixed in A-021, A-026)
- [ ] Verify progress bar updates correctly (A-020 in progress)
- [ ] Verify no false stall warnings (A-022 needs verification)
- [ ] Verify team members synced

---

## Files Modified This Session

| File | Change | Issue |
|------|--------|-------|
| `apps/metrics/tasks.py:121-132` | Raise ValueError instead of return error dict | A-027 |
| `apps/metrics/tests/test_llm_tasks.py:171-177` | Test expects ValueError | A-027 |
| `templates/onboarding/sync_progress.html:70-132` | Feature flag conditionals | A-021 |
| `templates/web/components/setup_prompt.html` | Full rewrite with flag checks | A-026 |

---

## Commands Reference

```bash
# Run all tests
make test

# Run specific test file
.venv/bin/pytest apps/metrics/tests/test_llm_tasks.py -v

# Run E2E tests
make e2e-smoke

# Start dev server
make dev

# Start Celery worker (single instance)
make celery

# Check Celery tasks
curl http://localhost:5555/api/tasks
```
