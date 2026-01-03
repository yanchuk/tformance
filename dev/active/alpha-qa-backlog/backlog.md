# Alpha QA Backlog - Open Issues

Tracking issues found during alpha version QA testing.

**Scope:** GitHub integration, 90-day data sync, LLM PR analysis, LLM dashboard insights.
**Out of scope:** Slack, Copilot, Jira connections.

**Sprint Documentation:** See `dev/active/alpha-qa-sprint-2/` for detailed plan and context.
**Resolved Issues:** Archived to `dev/archive/alpha-qa-resolved.md`

---

## Summary

**0 open issues** (27 resolved - see archive)

| ID | Priority | Type | Title | Status |
|----|----------|------|-------|--------|
| A-027 | P0 | Bug | Sync completes but LLM processing doesn't run | ✅ Fixed (test updated) |
| A-020 | P1 | Bug | Sync page main progress bar shows 0% | ✅ Fixed (celery-progress) |
| A-022 | P1 | Bug | "Sync May Have Stalled" warning appears incorrectly | ✅ Fixed (was caused by A-020) |
| A-024 | P1 | Investigation | PRs not appearing during sync | ✅ Working as designed |
| A-025 | P1 | Bug | Team Members not synced during onboarding | ✅ Fixed (pipeline task) |
| A-023 | P2 | Enhancement | Sync widget only updates on page refresh | ✅ Fixed (HTMX polling) |

**Recently Resolved (Session 2):**
- A-021: "Continue to Jira" button when Jira disabled ✅
- A-026: "Enhance your insights" banner when Jira/Slack disabled ✅
- A-020: Main progress bar now uses celery-progress ✅
- A-022: Stall detection fixed by A-020 ✅
- A-023: Sync widget HTMX polling added ✅
- A-025: Member sync added to onboarding pipeline ✅
- A-024: Investigated - working as designed (date filter mismatch) ✅

---

## A-027: Sync completes but LLM processing doesn't run (pipeline breaks)

| Field | Value |
|-------|-------|
| **Priority** | P0 (Blocker) |
| **Type** | Bug |
| **Status** | ✅ Fixed |
| **Reporter** | Manual QA testing |

### Description
After sync completes, the pipeline gets stuck at `llm_processing` status. The LLM analysis task is dispatched as part of the Celery chain but never executes or completes.

### Root Cause
LLM task returned error dict instead of raising exception, which doesn't fail Celery chains.

### Fix Applied
- `apps/metrics/tasks.py:121-132` - Now raises ValueError
- `apps/metrics/tests/test_llm_tasks.py:171-177` - Test expects ValueError

---

## A-020: Sync page main progress bar shows 0% (UI not reading updated fields)

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Bug |
| **Status** | 🟡 Root Cause Found |
| **Reporter** | Manual QA testing |

### Description
On `/onboarding/sync/` page, the main progress bar at the top shows "0%" even though:
- Per-repo badge correctly shows progress (e.g., "2%", "10%")
- PRs are being synced (text shows "10 PRs synced")
- Backend is updating `sync_progress` field correctly

### Root Cause (FOUND)
Two separate data sources:
1. **Main bar:** Polls `/celery-progress/<task_id>/` (reads from Celery result backend)
2. **Per-repo:** Polls `/onboarding/sync-status/` (reads from database)

Task updates DB but doesn't call `self.update_state()` to report to Celery backend.

### Fix Required
Add `self.update_state()` calls to `apps/integrations/tasks.py:sync_historical_data_task` around line 2254.

---

## A-022: "Sync May Have Stalled" warning appears during active sync

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Bug |
| **Status** | 🔴 Open |
| **Reporter** | Manual QA testing |

### Description
The "Sync May Have Stalled - No progress in 45 seconds" warning appears even when sync is actively working and making progress.

### Root Cause
The stall detection logic checks if 45 seconds passed since page load, but doesn't reset when progress changes.

### Acceptance Criteria
- [ ] Stall warning only appears if progress hasn't changed in 45+ seconds
- [ ] Reset stall timer when progress increases
- [ ] Don't show stall warning while sync is actively progressing

---

## A-023: Sync widget only updates on page refresh

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | Enhancement |
| **Status** | 🔴 Open |
| **Reporter** | Manual QA testing |

### Description
The sync progress widget in the bottom-right corner of the dashboard only updates when the page is refreshed.

### Acceptance Criteria
- [ ] Widget auto-polls during sync (HTMX polling, 3s interval)
- [ ] Shows PR count: "X of Y PRs synced"
- [ ] Shows current phase: "Phase 1: Last 30 days" or "Phase 2: Days 31-90"
- [ ] Stops polling when sync completes

---

## A-024: PRs not appearing during sync (investigation complete)

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Investigation |
| **Status** | ✅ Investigated (Working as Designed) |
| **Reporter** | Manual QA testing |

### Description
During sync, PR count in the Pull Requests page stays the same even though Celery shows sync progress.

### Root Cause (Investigated)

**This is expected behavior due to date filter mismatch:**

1. **Sync filters by `createdAt`**: Phase 1 syncs PRs *created* in the last 30 days
2. **PR list filters by `merged_at`**: Default view shows PRs *merged* in the last 30 days

**Mismatch scenario:**
- PR created 45 days ago, merged 25 days ago
- Phase 1 (30 days): Would NOT sync this PR (created > 30 days ago)
- Phase 2 (90 days): WILL sync this PR
- PR List (30 days): Would SHOW this PR once synced (merged < 30 days ago)

**Additional factors:**
- PR list has a default 30-day date filter (`apps/metrics/views/pr_list_views.py:94-98`)
- User must refresh page to see newly synced PRs
- Open PRs filter by `pr_created_at` instead of `merged_at`

### Resolution
This is **working as designed**. The two-phase approach prioritizes recently created PRs for faster time-to-dashboard. PRs with older creation dates but recent merge dates will appear after Phase 2 completes.

### Recommendation
Consider adding a "PRs synced: X" counter to the sync progress UI so users know data is arriving, even if the PR list view is filtered.

### Acceptance Criteria
- [x] Investigate and document findings
- [ ] ~~Fix if PRs exist but don't show~~ (N/A - working as designed)
- [ ] ~~Add test for PR visibility~~ (N/A - behavior is documented)

---

## A-025: Team Members not synced during onboarding

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Bug |
| **Status** | ✅ Fixed |
| **Reporter** | Manual QA testing |

### Description
Team Members count remains 0 after GitHub sync. Members should be imported from GitHub organization.

### Root Cause Analysis
**Member sync was NOT included in the onboarding pipeline!**

Member sync happens via `_sync_github_members_after_connection()` during OAuth callback using `.delay()`, but this doesn't guarantee completion before the user sees the dashboard.

### Solution (A-025)
Added member sync to the onboarding pipeline:

1. **New task**: `sync_github_members_pipeline_task` in `apps/integrations/onboarding_pipeline.py:422-473`
   - Takes `team_id`, looks up integration (OAuth or App)
   - Runs member sync synchronously (not `.delay()`)
   - Ensures members are synced before PR sync starts

2. **Pipeline update**: Added to Phase 1 pipeline before PR sync
   - New status `syncing_members` added to Team model
   - Member sync runs as Stage 0, before `sync_historical_data_task`

3. **Team model**: Added `syncing_members` to `PIPELINE_STATUS_CHOICES` and `pipeline_in_progress`

### Files Modified
- `apps/integrations/onboarding_pipeline.py`
- `apps/teams/models.py`
- `apps/integrations/tests/test_onboarding_pipeline.py`

### Acceptance Criteria
- [x] Team Members populated after GitHub OAuth
- [x] Member sync included in onboarding pipeline
- [x] Integration Status shows correct member count

---

*Last updated: 2026-01-03 (Session 2)*
