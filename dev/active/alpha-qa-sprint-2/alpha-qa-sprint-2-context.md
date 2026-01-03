# Alpha QA Sprint 2 - Context

**Last Updated:** 2026-01-03 (Session 2)

## Session Summary

**Completed this session:**
- A-027: LLM task test updated to expect ValueError ✅
- A-021: Fixed "Continue to Jira" button feature flags ✅
- A-026: Fixed "Enhance your insights" banner feature flags ✅
- A-020: Root cause found (needs implementation)

**Currently working on:**
- A-020: Main progress bar shows 0%

---

## Key Files

### Pipeline & Tasks

| File | Purpose | Issues |
|------|---------|--------|
| `apps/integrations/onboarding_pipeline.py` | Celery chain orchestration | A-027 |
| `apps/metrics/tasks.py` | LLM analysis batch task | A-027 ✅ |
| `apps/metrics/tests/test_llm_tasks.py` | LLM task tests | A-027 ✅ |
| `apps/integrations/tasks.py:2132-2363` | sync_historical_data_task | A-020 🟡 |
| `apps/integrations/services/github_graphql_sync.py` | GraphQL sync logic | A-024 |

### Templates (Feature Flags)

| File | Purpose | Issues |
|------|---------|--------|
| `templates/onboarding/sync_progress.html` | Sync progress page | A-020, A-021 ✅, A-022 |
| `templates/web/components/setup_prompt.html` | Jira/Slack banner | A-026 ✅ |
| `templates/onboarding/base.html` | Onboarding stepper | - |
| `templates/dashboard/components/sync_indicator.html` | Sync widget | A-023 |

### Views & APIs

| File | Purpose | Issues |
|------|---------|--------|
| `apps/onboarding/views.py:564-614` | sync_status endpoint | A-020 |
| `apps/dashboard/views.py` | Dashboard views | - |
| `apps/integrations/views/github.py` | GitHub OAuth callback | A-025 |

---

## A-020 Investigation (CURRENT WORK)

### Root Cause Found

**Problem:** Main progress bar shows 0% while per-repo badges show correct progress.

**Two separate data sources:**
1. **Main progress bar:** Polls `/celery-progress/<task_id>/` (celery_progress library)
2. **Per-repo badges:** Polls `/onboarding/sync-status/` (DB query)

**The disconnect:**
- `sync_historical_data_task` updates the database with `repo.sync_progress`, `repo.sync_prs_completed`, etc.
- BUT it never calls `self.update_state()` to report progress to Celery's result backend
- The `/celery-progress/` endpoint reads from Celery's result backend, NOT the database
- So celery-progress has no data → main bar shows 0%

### Fix Required

Add `self.update_state()` calls in `apps/integrations/tasks.py` at these locations:

1. **Line ~2254** (after updating repo status to syncing):
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

2. **Inside progress_callback** (line ~2269, after DB update):
```python
# Also report to celery-progress for real-time main bar updates
# Need to capture self reference
```

**Alternative approach:** Modify the frontend JS to use DB-based progress instead of celery-progress.

---

## Key Decisions

### D-001: LLM Task Error Handling ✅
**Decision:** Raise ValueError instead of returning error dict
**Rationale:** Celery chains only fail on exceptions, not return values
**Impact:** Pipeline properly fails and triggers error handler
**Implemented:** `apps/metrics/tasks.py:121-132`

### D-002: Single Celery Worker
**Decision:** Use one worker with `--pool=threads`
**Rationale:** Multiple workers with different pools cause task routing issues
**Impact:** Need to document in dev setup guide
**Status:** Not yet documented

### D-003: Feature Flag Context Function ✅
**Decision:** Use `_get_onboarding_flags_context()` for all flag checks
**Rationale:** Centralized logic, consistent across templates
**Impact:** All templates must include flag context
**Implemented:** Already in views.py

---

## Feature Flags

| Flag | Setting | Effect |
|------|---------|--------|
| `ENABLE_JIRA_INTEGRATION` | `False` | Hide all Jira UI |
| `ENABLE_SLACK_INTEGRATION` | `False` | Hide all Slack UI |
| `ENABLE_API_KEYS` | `False` | Hide API Keys section |

**Check in views:**
```python
from django.conf import settings

context = {
    'enable_jira_integration': settings.ENABLE_JIRA_INTEGRATION,
    'enable_slack_integration': settings.ENABLE_SLACK_INTEGRATION,
}
```

**Check in templates:**
```django
{% if enable_jira_integration %}
  {# Jira content #}
{% endif %}
```

---

## Pipeline Flow

```
start_phase1_pipeline(team_id, repo_ids)
    │
    ├─> update_pipeline_status("syncing")
    ├─> sync_historical_data_task(days_back=30)  ← A-020: needs update_state()
    ├─> update_pipeline_status("llm_processing")
    ├─> run_llm_analysis_batch(limit=None)  ← A-027: now raises ValueError ✅
    ├─> update_pipeline_status("computing_metrics")
    ├─> aggregate_team_weekly_metrics_task()
    ├─> update_pipeline_status("computing_insights")
    ├─> compute_team_insights()
    ├─> update_pipeline_status("phase1_complete")
    └─> dispatch_phase2_pipeline()
```

---

## Database Fields (TrackedRepository)

| Field | Type | Purpose |
|-------|------|---------|
| `sync_status` | VARCHAR(20) | pending, syncing, completed, error |
| `sync_progress` | INTEGER | 0-100 percentage |
| `sync_prs_completed` | INTEGER | PRs synced so far |
| `sync_prs_total` | INTEGER | Total PRs to sync |

---

## API Endpoints

### GET /onboarding/sync-status/
Returns sync status from DB for current team:
```json
{
  "status": "syncing",
  "repos": [
    {
      "id": 123,
      "full_name": "org/repo",
      "sync_status": "syncing",
      "sync_progress": 45,
      "last_sync_at": null,
      "last_sync_error": null
    }
  ],
  "prs_synced": 27
}
```

### GET /celery-progress/<task_id>/
Returns Celery task progress (currently missing data for A-020):
```json
{
  "state": "PROGRESS",
  "complete": false,
  "progress": {
    "current": 1,
    "total": 3,
    "description": "Syncing org/repo..."
  }
}
```

---

## Test Commands

```bash
# Run LLM task tests
.venv/bin/pytest apps/metrics/tests/test_llm_tasks.py -v

# Run onboarding tests
.venv/bin/pytest apps/onboarding/tests/ -v

# Run sync tests
.venv/bin/pytest apps/integrations/tests/test_github_graphql_sync.py -v

# Run E2E onboarding tests
make e2e-smoke

# Check specific test
.venv/bin/pytest -k "test_raises_error_without_api_key" -v
```

---

## Handoff Notes (IMPORTANT)

### Current State
1. **A-021, A-026 complete** - Feature flag fixes implemented and tested
2. **A-020 investigation complete** - Root cause identified
3. **A-020 implementation NOT started** - Need to add `self.update_state()` calls

### Exact Next Steps for A-020

1. Open `apps/integrations/tasks.py`
2. Go to line ~2254 (in the `for idx, repo in enumerate(sorted_repos, 1):` loop)
3. Add after `repo.save(update_fields=["sync_status", "sync_started_at"])`:
```python
# Report overall progress to celery-progress endpoint (A-020 fix)
self.update_state(
    state='PROGRESS',
    meta={
        'current': idx,
        'total': total_repos,
        'description': f'Syncing {repo.full_name}...'
    }
)
```

4. Optionally update `progress_callback` to also call `self.update_state()` for PR-level progress

### Commands to Verify

```bash
# After making changes, run tests
.venv/bin/pytest apps/integrations/tests/ -v -x

# Start dev server for manual testing
make dev

# Start Celery worker
make celery
```

### Uncommitted Changes

Files modified this session (should be committed):
- `apps/metrics/tasks.py` - ValueError change
- `apps/metrics/tests/test_llm_tasks.py` - Test update
- `templates/onboarding/sync_progress.html` - Feature flag buttons
- `templates/web/components/setup_prompt.html` - Feature flag banner

---

## Related Issues (Resolved)

- A-019: GraphQL sync now updates progress fields ✅
- A-006: Celery sync stalls fixed ✅
- A-002: Onboarding feature flag compliance ✅
