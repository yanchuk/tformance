# Alpha QA Backlog - Open Issues

Tracking issues found during alpha version QA testing.

**Scope:** GitHub integration, 90-day data sync, LLM PR analysis, LLM dashboard insights.
**Out of scope:** Slack, Copilot, Jira connections.

**Sprint Documentation:** See `dev/active/alpha-qa-sprint-2/` for detailed plan and context.
**Resolved Issues:** Archived to `dev/archive/alpha-qa-resolved.md`

---

## Summary

**6 open issues** (21 resolved - see archive)

| ID | Priority | Type | Title | Status |
|----|----------|------|-------|--------|
| A-027 | P0 | Bug | Sync completes but LLM processing doesn't run | ✅ Fixed (test updated) |
| A-020 | P1 | Bug | Sync page main progress bar shows 0% | 🟡 Root cause found |
| A-022 | P1 | Bug | "Sync May Have Stalled" warning appears incorrectly | 🔴 Open |
| A-024 | P1 | Investigation | PRs not appearing during sync | 🔴 Open |
| A-025 | P1 | Bug | Team Members not synced during onboarding | 🔴 Open |
| A-023 | P2 | Enhancement | Sync widget only updates on page refresh | 🔴 Open |

**Recently Resolved (Session 2):**
- A-021: "Continue to Jira" button when Jira disabled ✅
- A-026: "Enhance your insights" banner when Jira/Slack disabled ✅

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

## A-024: PRs not appearing during sync (needs investigation)

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Investigation |
| **Status** | 🔴 Open |
| **Reporter** | Manual QA testing |

### Description
During sync, PR count in the Pull Requests page stays the same even though Celery shows sync progress.

### Possible Causes
1. **Date range filter**: Default view shows 30 days - Phase 2 PRs won't show
2. **Two-phase design**: Phase 1 syncs 30 days first, Phase 2 adds days 31-90
3. **Cutoff date filtering**: PRs older than `cutoff_date` are skipped

### Acceptance Criteria
- [ ] Investigate and document findings
- [ ] Fix if PRs exist but don't show
- [ ] Add test for PR visibility

---

## A-025: Team Members not synced during onboarding

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Bug |
| **Status** | 🔴 Open |
| **Reporter** | Manual QA testing |

### Description
Team Members count remains 0 after GitHub sync. Members should be imported from GitHub organization.

### Root Cause Analysis
**Member sync is NOT included in the onboarding pipeline!**

Member sync happens via `_sync_github_members_after_connection()` during OAuth callback, NOT during the onboarding sync pipeline.

### Acceptance Criteria
- [ ] Team Members populated after GitHub OAuth
- [ ] Or: Member sync included in onboarding pipeline
- [ ] Integration Status shows correct member count

---

*Last updated: 2026-01-03 (Session 2)*
