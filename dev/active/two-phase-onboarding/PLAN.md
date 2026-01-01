# Two-Phase Onboarding Pipeline - Implementation Plan

**Created**: 2026-01-01
**Status**: Planning
**Branch**: `feature/two-phase-onboarding`

## Problem Statement

Current onboarding processes only **100 PRs** with LLM analysis during initial sync, leaving 80%+ of historical data unanalyzed until the nightly batch job (5 AM UTC). This means:

1. New users wait up to 24 hours for complete AI detection data
2. Initial insights are based on incomplete information
3. Dashboard metrics may shift significantly after nightly processing

## Solution: Two-Phase Quick Start (Option C)

### Phase 1: Quick Start (~5 minutes)
- Sync **last 30 days** only (fast)
- LLM analyze **ALL synced PRs** (~150 typical)
- Compute insights immediately
- User can access dashboard

### Phase 2: Background Completion (~1-2 hours)
- Continue syncing **remaining 60 days**
- LLM analyze in batches (rate limited)
- Update insights when complete
- Show progress banner in UI

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER ONBOARDING FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

User connects GitHub repo
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: QUICK START (5 min)                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ Sync 30 days │───▶│ LLM all PRs  │───▶│  Insights    │───▶ Dashboard│
│  │   (~150 PRs) │    │   (100%)     │    │   ready!     │     access   │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
│  Status: syncing → llm_processing → computing → phase1_complete         │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │ (runs in parallel after phase1_complete)
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: BACKGROUND COMPLETION (1-2 hours)                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ Sync 31-90d  │───▶│ LLM batches  │───▶│ Update       │───▶ Complete │
│  │   (~350 PRs) │    │ (30/min)     │    │ insights     │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
│  Status: background_syncing → background_llm → background_complete      │
│                                                                         │
│  UI: "⏳ Analyzing 60 more days of history... 45% complete"             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. New Pipeline Status Values

Add to `Team.PIPELINE_STATUS_CHOICES`:

```python
PIPELINE_STATUS_CHOICES = [
    ("not_started", "Not Started"),
    ("syncing", "Syncing PRs"),                    # Phase 1: sync
    ("llm_processing", "Analyzing with AI"),       # Phase 1: LLM
    ("computing_metrics", "Computing Metrics"),    # Phase 1: metrics
    ("computing_insights", "Computing Insights"),  # Phase 1: insights
    ("phase1_complete", "Dashboard Ready"),        # NEW: Phase 1 done
    ("background_syncing", "Background: Syncing"), # NEW: Phase 2 sync
    ("background_llm", "Background: Analyzing"),   # NEW: Phase 2 LLM
    ("complete", "Complete"),
    ("failed", "Failed"),
]
```

### 2. New Fields on Team Model

```python
# Progress tracking for Phase 2
background_sync_progress = models.IntegerField(default=0)  # 0-100%
background_llm_progress = models.IntegerField(default=0)   # 0-100%
```

### 3. Modified Onboarding Pipeline

```python
def start_onboarding_pipeline(team_id: int, repo_ids: list[int]) -> AsyncResult:
    """Two-phase onboarding pipeline."""

    # PHASE 1: Quick Start (30 days)
    phase1 = chain(
        update_pipeline_status.si(team_id, "syncing"),
        sync_historical_data_task.si(team_id, repo_ids, days_back=30),  # Only 30 days
        update_pipeline_status.si(team_id, "llm_processing"),
        run_llm_analysis_batch.si(team_id, limit=None),  # ALL PRs (no limit)
        update_pipeline_status.si(team_id, "computing_metrics"),
        aggregate_team_weekly_metrics_task.si(team_id),
        update_pipeline_status.si(team_id, "computing_insights"),
        compute_team_insights.si(team_id),
        update_pipeline_status.si(team_id, "phase1_complete"),
        send_onboarding_complete_email.si(team_id),
        # Dispatch Phase 2 as separate task
        dispatch_phase2_pipeline.si(team_id, repo_ids),
    )

    return phase1.apply_async()
```

### 4. Phase 2 Background Pipeline

```python
@shared_task(bind=True)
def run_phase2_pipeline(self, team_id: int, repo_ids: list[int]) -> dict:
    """
    Background completion of historical data.
    Syncs days 31-90 and processes with LLM.
    """
    phase2 = chain(
        update_pipeline_status.si(team_id, "background_syncing"),
        sync_historical_data_task.si(team_id, repo_ids, days_back=90, skip_recent=30),
        update_pipeline_status.si(team_id, "background_llm"),
        run_llm_analysis_batch.si(team_id, limit=None, rate_limit_delay=2.1),
        update_pipeline_status.si(team_id, "complete"),
        # Recompute insights with full data
        aggregate_team_weekly_metrics_task.si(team_id),
        compute_team_insights.si(team_id),
    )
    return phase2.apply_async()
```

### 5. UI Progress Banner

In `templates/metrics/dashboard.html`:

```html
{% if team.onboarding_pipeline_status in 'background_syncing,background_llm' %}
<div class="alert alert-info">
  <svg class="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">...</svg>
  <span>
    Analyzing {{ team.background_sync_progress }}% more history...
    Your dashboard is ready, but numbers may update when complete.
  </span>
</div>
{% endif %}
```

## API Changes

### Modified: `sync_historical_data_task`

Add new parameters:

```python
@shared_task
def sync_historical_data_task(
    team_id: int,
    repo_ids: list[int],
    days_back: int = 90,      # Default: full history
    skip_recent: int = 0,     # NEW: Skip most recent N days (for Phase 2)
) -> dict:
```

### Modified: `run_llm_analysis_batch`

```python
@shared_task
def run_llm_analysis_batch(
    team_id: int,
    limit: int | None = 50,   # None = process all
    rate_limit_delay: float = 2.1,
) -> dict:
```

## Migration Plan

1. Add new status choices (no migration needed - CharField)
2. Add progress tracking fields (requires migration)
3. Update existing code to use new pipeline
4. Add UI components for progress display

## Testing Strategy (TDD)

### Unit Tests
- [ ] Test Phase 1 completes within 5 minutes for typical team
- [ ] Test Phase 2 dispatches after Phase 1 complete
- [ ] Test progress tracking updates correctly
- [ ] Test sync with `skip_recent` parameter
- [ ] Test LLM batch with `limit=None`

### Integration Tests
- [ ] Full onboarding flow with two phases
- [ ] Error handling in Phase 2 doesn't affect Phase 1
- [ ] Concurrent Phase 2 runs are prevented

### E2E Tests
- [ ] Progress banner displays correctly
- [ ] Dashboard accessible after Phase 1
- [ ] Banner dismisses after Phase 2 complete

## Rollout Plan

1. **Feature flag**: `waffle.flag.is_active('two_phase_onboarding')`
2. **Gradual rollout**: 10% → 50% → 100%
3. **Monitoring**: Track Phase 1 completion times
4. **Rollback**: Fall back to single-phase if issues

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Time to dashboard access | ~15 min | ~5 min |
| Initial insight accuracy | ~20% data | 100% (30d) |
| Complete data availability | ~24h | ~2h |
