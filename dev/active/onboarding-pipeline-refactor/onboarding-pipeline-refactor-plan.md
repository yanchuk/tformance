# Onboarding Pipeline Refactor - Implementation Plan

**Last Updated:** 2025-12-29

## Executive Summary

Refactor the onboarding data processing flow to use Celery task chains for reliable, sequential execution of:
1. Historical PR sync
2. LLM AI detection analysis
3. Weekly metrics aggregation
4. Insights computation
5. Email notification

This addresses critical gaps where signals are defined but not connected, tasks aren't triggered when they should be, and users wait 24+ hours for AI detection results.

---

## Current State Analysis

### Problems Identified

| Issue | Impact | Location |
|-------|--------|----------|
| Signals defined but no receivers | `onboarding_sync_completed` fires but nothing listens | `apps/integrations/signals.py`, `apps/integrations/apps.py` |
| Orphaned email function | `send_sync_complete_email()` never called | `apps/onboarding/services/notifications.py:63` |
| Missing task triggers | Historical sync doesn't trigger metrics/LLM | `apps/integrations/tasks.py:2043` |
| 24-hour LLM delay | Users wait until nightly batch | Celery beat schedule |
| No completion tracking | No way to know when pipeline finishes | Team model |

### Current Task Flow (Broken)

```
sync_historical_data_task()
  └─ Sends onboarding_sync_completed signal (NO LISTENERS!)
  └─ Does NOT trigger: aggregate_team_weekly_metrics_task
  └─ Does NOT trigger: run_llm_analysis_batch
  └─ Does NOT send: completion email
```

---

## Proposed Future State

### Architecture Decision: Celery Chains + Signals Hybrid

**Why Celery Chains (not just signals)?**

| Approach | Pros | Cons | Use Case |
|----------|------|------|----------|
| **Signals** | Decoupled, extensible | Hidden deps, no ordering guarantee, hard to debug | Side effects, logging, analytics |
| **Celery Chains** | Explicit deps, error handling, progress tracking, retry logic | Tighter coupling | Sequential workflows |
| **Hybrid (Recommended)** | Best of both | Slight complexity | Our use case |

**Decision:** Use Celery chains for pipeline orchestration, keep signals for optional hooks.

### Target Architecture

```
start_onboarding_pipeline(team_id, repo_ids)
│
├─ [CHAIN] Main Pipeline (sequential, guaranteed order)
│   ├─ sync_historical_data_task
│   ├─ run_llm_analysis_batch (limit=100 for onboarding)
│   ├─ aggregate_team_weekly_metrics_task
│   ├─ compute_team_insights
│   └─ send_onboarding_complete_email
│
└─ [SIGNALS] Optional Hooks (fire after chain stages)
    ├─ onboarding_sync_completed → Analytics, external webhooks
    └─ repository_sync_completed → Per-repo logging
```

---

## Implementation Phases

### Phase 1: Foundation (Model + Signal Infrastructure)
- Add pipeline tracking fields to Team model
- Connect signal receivers via `IntegrationsConfig.ready()`
- Create `apps/integrations/receivers.py`

### Phase 2: Task Chain Orchestration
- Create `apps/integrations/tasks/onboarding_pipeline.py`
- Implement `start_onboarding_pipeline()` function
- Add error handling with `link_error` callbacks

### Phase 3: Progress Tracking
- Create `update_onboarding_progress_task`
- Modify each pipeline task to update Team status
- Enhance `sync_status()` API endpoint

### Phase 4: Email Notification
- Create new task `send_onboarding_complete_email`
- Update email template with rich statistics
- Wire into pipeline chain as final step

### Phase 5: View Integration
- Update `select_repositories()` to use new pipeline
- Update progress polling to show pipeline stages
- Handle edge cases (empty repos, failed stages)

### Phase 6: Testing & Documentation
- TDD: Write tests BEFORE implementation for each phase
- Integration tests for full pipeline
- Update CLAUDE.md with new patterns

---

## Technical Design

### Model Changes (Team)

```python
# apps/teams/models.py
class Team(BaseModel):
    # Existing fields...

    # NEW: Pipeline tracking
    PIPELINE_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('syncing', 'Syncing PRs'),
        ('llm_processing', 'Analyzing with AI'),
        ('computing_metrics', 'Computing Metrics'),
        ('computing_insights', 'Computing Insights'),
        ('complete', 'Complete'),
        ('failed', 'Failed'),
    ]

    onboarding_pipeline_status = models.CharField(
        max_length=50,
        choices=PIPELINE_STATUS_CHOICES,
        default='not_started',
    )
    onboarding_pipeline_error = models.TextField(blank=True, null=True)
    onboarding_pipeline_started_at = models.DateTimeField(null=True)
    onboarding_pipeline_completed_at = models.DateTimeField(null=True)
```

### Pipeline Orchestration

```python
# apps/integrations/tasks/onboarding_pipeline.py
from celery import chain

def start_onboarding_pipeline(team_id: int, repo_ids: list[int]) -> AsyncResult:
    """
    Orchestrate complete onboarding using Celery chain.

    Guarantees sequential execution with error propagation.
    """
    pipeline = chain(
        update_pipeline_status.si(team_id, 'syncing'),
        sync_historical_data_task.si(team_id, repo_ids),
        update_pipeline_status.si(team_id, 'llm_processing'),
        run_llm_analysis_batch.si(team_id, limit=100),
        update_pipeline_status.si(team_id, 'computing_metrics'),
        aggregate_team_weekly_metrics_task.si(team_id),
        update_pipeline_status.si(team_id, 'computing_insights'),
        compute_team_insights.si(team_id),
        update_pipeline_status.si(team_id, 'complete'),
        send_onboarding_complete_email.si(team_id),
    )

    # Error handler
    return pipeline.on_error(handle_pipeline_failure.s(team_id)).apply_async()
```

### Signal Receivers (Lightweight Operations Only)

```python
# apps/integrations/receivers.py
from django.dispatch import receiver
from apps.integrations.signals import onboarding_sync_completed

@receiver(onboarding_sync_completed)
def log_sync_completion(sender, team_id, repos_synced, total_prs, **kwargs):
    """Log sync completion for analytics (non-blocking)."""
    logger.info(f"Team {team_id}: Synced {repos_synced} repos, {total_prs} PRs")
    # PostHog tracking, etc.
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Chain task failure blocks pipeline | Medium | High | Add error handler, status tracking, retry logic |
| LLM rate limiting | High | Medium | Respect rate limits (2.1s delay), process in batches |
| Long-running sync blocks worker | Low | Medium | Use dedicated `sync` queue with gevent |
| Email delivery failure | Low | Low | Fail silently, log error, don't break pipeline |
| Migration issues on existing teams | Low | Medium | Default `not_started`, don't affect existing flows |

---

## Success Metrics

- [ ] New users receive "insights ready" email within 30 minutes of completing onboarding
- [ ] LLM analysis runs immediately after sync (not 24h later)
- [ ] Pipeline status visible in UI during onboarding
- [ ] Zero regression in existing nightly batch processing
- [ ] All tests pass with >90% coverage on new code

---

## Required Resources

### Files to Create
| File | Purpose |
|------|---------|
| `apps/integrations/receivers.py` | Signal receivers |
| `apps/integrations/tasks/onboarding_pipeline.py` | Pipeline orchestration |
| `apps/integrations/tasks/__init__.py` | Package exports |
| `templates/onboarding/email/pipeline_complete.html` | HTML email |
| `templates/onboarding/email/pipeline_complete.txt` | Plain text email |
| `apps/integrations/tests/test_onboarding_pipeline.py` | Pipeline tests |
| `apps/integrations/tests/test_receivers.py` | Receiver tests |

### Files to Modify
| File | Changes |
|------|---------|
| `apps/integrations/apps.py` | Add `ready()` method |
| `apps/teams/models.py` | Add pipeline tracking fields |
| `apps/onboarding/views.py` | Use pipeline, enhance status API |
| `apps/onboarding/services/notifications.py` | Update email function |
| `apps/metrics/tasks.py` | Ensure tasks return chain-compatible data |

### Dependencies
- Celery chains (already available)
- Django signals (already configured)
- Email backend (already configured)

---

## Git Worktree Strategy

```bash
# Create worktree for this feature
git worktree add ../tformance-onboarding-pipeline feature/onboarding-pipeline-refactor

# Work in isolated branch, merge when complete
```

---

## TDD Workflow Per Phase

For each implementation phase:

1. **RED**: Write failing tests first
   - Test expected behavior
   - Test error cases
   - Test edge cases

2. **GREEN**: Implement minimum code to pass tests

3. **REFACTOR**: Clean up while keeping tests green

Example for Phase 1:
```python
# RED: apps/teams/tests/test_pipeline_tracking.py
class TestPipelineTracking(TestCase):
    def test_team_has_pipeline_status_field(self):
        team = TeamFactory()
        self.assertEqual(team.onboarding_pipeline_status, 'not_started')

    def test_pipeline_status_choices_valid(self):
        team = TeamFactory()
        team.onboarding_pipeline_status = 'syncing'
        team.full_clean()  # Should not raise
```
