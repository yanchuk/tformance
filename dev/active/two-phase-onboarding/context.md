# Two-Phase Onboarding - Context

**Last Updated**: 2026-01-01
**Status**: Core Implementation Complete & Pushed to Main
**Branch**: `main`

## Overview

Implementing Option C (Two-Phase Quick Start) for onboarding pipeline to reduce time-to-dashboard from ~15 minutes to ~5 minutes while ensuring all historical data is eventually processed.

## Implementation Progress

### ✅ Completed

**Team Model Changes** (`apps/teams/models.py`):
- Added new pipeline status choices: `phase1_complete`, `background_syncing`, `background_llm`
- Added progress fields: `background_sync_progress`, `background_llm_progress`
- Added properties: `dashboard_accessible`, `background_in_progress`
- Added method: `update_background_progress()`
- Migration: `0006_add_two_phase_onboarding_fields`

**Sync Task Changes** (`apps/integrations/tasks.py`):
- Added `days_back` parameter to `sync_historical_data_task` (default: 90)
- Added `skip_recent` parameter (default: 0)
- Parameters passed through to `OnboardingSyncService.sync_repository()`

**Sync Service Changes** (`apps/integrations/services/onboarding_sync.py`):
- Added `days_back` and `skip_recent` parameters to `sync_repository()`
- Parameters passed through to GraphQL sync function

**GraphQL Sync Changes** (`apps/integrations/services/github_graphql_sync.py`):
- Added `skip_recent` parameter to `sync_repository_history_graphql()`
- Added `skip_before_date` filtering to `_process_pr()` for Phase 2 date range

**LLM Batch Changes** (`apps/metrics/tasks.py`):
- Updated type signature: `limit: int | None = 50`
- Added Two-Phase Onboarding documentation to docstring
- `limit=None` processes ALL PRs (for Phase 1)

**Pipeline Orchestration** (`apps/integrations/onboarding_pipeline.py`):
- Added `start_phase1_pipeline()` - syncs 30 days, LLM ALL PRs, ends with `phase1_complete`
- Added `dispatch_phase2_pipeline()` - Celery task to start Phase 2 async
- Added `run_phase2_pipeline()` - syncs 31-90 days, ends with `complete`
- Updated `start_onboarding_pipeline()` to delegate to `start_phase1_pipeline()`

**UI Progress Banner** (`templates/metrics/partials/background_progress_banner.html`):
- Shows during `background_syncing` and `background_llm` statuses
- Displays progress percentage with animated progress bar
- Uses HTMX polling (every 10s) for live updates
- Auto-dismisses with success message when complete
- Included in cto_overview.html and analytics/overview.html

**Background Progress View** (`apps/metrics/views/dashboard_views.py`):
- Added `background_progress()` endpoint for HTMX polling
- URL: `/app/metrics/partials/background-progress/`
- Tests: 8 new tests in test_dashboard_views.py

**Error Handling** (`apps/integrations/onboarding_pipeline.py`):
- Added `handle_phase2_failure()` - graceful error handler for Phase 2
- Phase 1 failure: Sets status to `failed`, blocks dashboard
- Phase 2 failure: Reverts to `phase1_complete`, dashboard stays accessible
- Tests: 7 new tests in test_two_phase_pipeline.py

**Dashboard Access Control** (`apps/metrics/views/`):
- Added access check to `cto_overview` and `analytics_overview` views
- Redirects to `onboarding:sync_progress` when `dashboard_accessible` is False
- Statuses that block: `syncing`, `llm_processing`, `computing_metrics`, `computing_insights`, `failed`
- Statuses that allow: `phase1_complete`, `background_syncing`, `background_llm`, `complete`
- Tests: 9 new tests in test_dashboard_views.py

### 📋 Pending

- Add progress tracking to sync and LLM tasks (optional enhancement)
- Integration tests (Phase 6) - optional
- Feature flag for rollout (Phase 7) - optional

## Current Architecture

### Onboarding Pipeline (`apps/integrations/onboarding_pipeline.py`)

Current flow (single-phase):
```
syncing → llm_processing → computing_metrics → computing_insights → complete
```

Key limitation at line 185:
```python
run_llm_analysis_batch.si(team_id, limit=100),  # Only 100 PRs
```

### Sync Task (`apps/integrations/tasks.py`)

`sync_historical_data_task` syncs 90 days of data:
- Fetches PRs via GitHub API/GraphQL
- Creates PullRequest, PRFile, Commit, PRReview records
- No `days_back` parameter (always 90 days)

### LLM Analysis Task (`apps/metrics/tasks.py`)

`run_llm_analysis_batch`:
- Rate limited at 30 req/min (2.1s delay)
- Processes PRs without `llm_summary` or with outdated version
- Uses Groq API with `openai/gpt-oss-120b` model

### Nightly Batch Schedule (`tformance/settings.py`)

```python
"run-llm-analysis": {
    "task": "apps.metrics.tasks.run_all_teams_llm_analysis",
    "schedule": crontab(hour=5, minute=0),  # 5:00 AM UTC daily
}
```

## Key Files

| File | Purpose |
|------|---------|
| `apps/integrations/onboarding_pipeline.py` | Pipeline orchestration |
| `apps/integrations/tasks.py` | Sync tasks (GitHub, Jira) |
| `apps/metrics/tasks.py` | LLM analysis tasks |
| `apps/teams/models.py` | Team model with pipeline status |
| `tformance/settings.py` | Celery beat schedule |

## Design Decisions

### Why Two Phases?

1. **User psychology**: Getting to dashboard quickly is more important than complete data
2. **Rate limits**: Groq API at 30 req/min means 500 PRs = 17 minutes
3. **Incremental value**: 30 days provides actionable insights for most teams

### Why 30 Days for Phase 1?

- Covers most active work
- Typical team has ~5 PRs/day = 150 PRs in 30 days
- At 30 req/min, 150 PRs = 5 minutes
- Provides enough data for meaningful insights

### Why Background for Phase 2?

- User can start using dashboard immediately
- Historical data arrives without blocking
- Progress banner keeps user informed
- No urgency for 60-90 day old data

## Considerations

### Rate Limiting

Groq API: 30 requests/minute = 2.1s between calls
- Phase 1 (150 PRs): ~5 minutes
- Phase 2 (350 PRs): ~12 minutes

### Error Handling

- Phase 1 failure: Block dashboard access, show error
- Phase 2 failure: Don't affect dashboard, retry in nightly batch

### Idempotency

- Sync tasks must be idempotent (upsert on github_pr_id)
- LLM analysis skips already-processed PRs
- Multiple Phase 2 runs safe

## Dependencies

- Celery for task orchestration
- Redis for message broker
- Groq API for LLM analysis
- GitHub API for PR sync

## Risks

| Risk | Mitigation |
|------|------------|
| Phase 2 never completes | Nightly batch as fallback |
| User confusion about partial data | Clear progress banner |
| Rate limit changes | Configurable delay parameter |
| GitHub API timeouts | Retry logic in sync tasks |
