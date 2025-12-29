# Onboarding Pipeline Refactor - Context

**Last Updated:** 2025-12-29

## Key Decision: Celery Chains Over Pure Signals

### Why Not Pure Signals?

Django signals have these limitations for sequential workflows:

1. **No ordering guarantee** - Multiple receivers execute in undefined order
2. **Hidden dependencies** - Hard to trace what happens when signal fires
3. **No error propagation** - One receiver failing doesn't affect others
4. **No progress tracking** - Can't know which step is running

### Why Celery Chains?

```python
# Chain guarantees: Task 1 → Task 2 → Task 3 (sequential)
chain(task1.si(), task2.si(), task3.si())

# If task2 fails, task3 never runs (desired behavior)
# Can add error handler: .on_error(handle_failure.s())
```

### Hybrid Approach

- **Celery chains**: Main pipeline orchestration (required, sequential)
- **Signals**: Optional hooks for logging, analytics, external integrations (fire-and-forget)

---

## Critical Files Reference

### Signals Infrastructure (Existing)

**`apps/integrations/signals.py`**
```python
# Lines 1-18 - Signal definitions (EXIST)
onboarding_sync_started = Signal()      # Args: team_id, repo_ids
onboarding_sync_completed = Signal()    # Args: team_id, repos_synced, total_prs, failed_repos
repository_sync_completed = Signal()    # Args: team_id, repo_id, prs_synced
```

**`apps/integrations/apps.py`** (NEEDS `ready()`)
```python
# Line 1-7 - Current state (MISSING ready() method)
class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations"
    verbose_name = "Integrations"
    # NO ready() method - signals never connected!
```

### Task Definitions

**`apps/integrations/tasks.py`**
- Line 2043: `sync_historical_data_task()` - Main historical sync
- Line 315: `sync_repository_initial_task()` - Triggers metrics (we're missing this)
- Line 1437: `aggregate_team_weekly_metrics_task()` - Metrics aggregation
- Line 2120-2185: Signal sending (signals ARE sent, just not received)

**`apps/metrics/tasks.py`**
- Line 49: `compute_team_insights()` - Insights computation
- Line 96: `run_llm_analysis_batch()` - LLM processing

### Email Functions

**`apps/onboarding/services/notifications.py`**
- Line 10: `send_welcome_email()` - USED (works)
- Line 63: `send_sync_complete_email()` - ORPHANED (never called)

### Onboarding Views

**`apps/onboarding/views.py`**
- Line 273: `sync_historical_data_task.delay()` - Current (broken) trigger point
- Line 381: Alternative trigger point
- Line 387-442: `sync_status()` - Status API endpoint (needs enhancement)

### Team Model

**`apps/teams/models.py`**
- Needs new fields: `onboarding_pipeline_status`, `onboarding_pipeline_error`, etc.

---

## Existing Patterns to Follow

### Task with Status Updates (from `sync_repository_initial_task`)

```python
# apps/integrations/tasks.py:268-320
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_repository_initial_task(self, repo_id, days_back=30):
    # Update status at start
    tracked_repo.sync_status = "syncing"
    tracked_repo.save()

    try:
        # ... do work ...

        # Success: trigger dependent task
        aggregate_team_weekly_metrics_task.delay(tracked_repo.team_id)

        # Update status on success
        tracked_repo.sync_status = "complete"
        tracked_repo.save()

    except Exception as exc:
        # Update status on failure
        tracked_repo.sync_status = "error"
        tracked_repo.last_sync_error = str(exc)
        tracked_repo.save()
        raise
```

### Signal Receiver Pattern (from `apps/users/signals.py`)

```python
# apps/users/signals.py:12-60
from django.dispatch import receiver
from allauth.account.signals import user_signed_up

@receiver(user_signed_up)
def handle_user_signed_up(request, user, **kwargs):
    """Handle post-signup actions."""
    # Lightweight operations only
    mail_admins(subject, message, fail_silently=True)
```

### App Config with ready() (from `apps/teams/apps.py`)

```python
# apps/teams/apps.py
class TeamsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.teams"

    def ready(self):
        from apps.teams import signals  # noqa: F401
```

---

## Dependencies Between Tasks

```
sync_historical_data_task
    ↓ (must complete first - creates PRs)
run_llm_analysis_batch
    ↓ (needs PRs to exist)
aggregate_team_weekly_metrics_task
    ↓ (needs PR data + LLM summaries)
compute_team_insights
    ↓ (needs metrics)
send_onboarding_complete_email
```

**Key Insight**: This is a linear chain - perfect for Celery `chain()`.

---

## Configuration Values

### Celery Queue Routing (from `settings.py:574-594`)

```python
CELERY_TASK_ROUTES = {
    'apps.integrations.tasks.sync_*': {'queue': 'sync'},
    'apps.metrics.tasks.run_llm_*': {'queue': 'llm'},
    'apps.metrics.tasks.compute_*': {'queue': 'compute'},
}
```

### Rate Limits

- LLM batch: 2.1s delay between calls (~30 req/min for Groq)
- GitHub API: Handled by existing sync code

### Historical Sync Config (from `settings.py`)

```python
HISTORICAL_SYNC_CONFIG = {
    'HISTORY_MONTHS': 12,  # Sync 12 months back
    'LLM_BATCH_SIZE': 100,
    'GRAPHQL_PAGE_SIZE': 25,
}
```

---

## Testing Fixtures Available

### Factories (from `apps/metrics/factories.py`)

```python
TeamFactory
TeamMemberFactory
PullRequestFactory
PRReviewFactory
CommitFactory
WeeklyMetricsFactory
```

### Test Patterns (from `apps/integrations/tests/test_historical_sync.py`)

```python
# Signal testing pattern (lines 505-532)
def test_signal_sent(self):
    from apps.integrations.signals import onboarding_sync_completed

    handler = MagicMock()
    onboarding_sync_completed.connect(handler)

    try:
        # Trigger signal
        sync_historical_data_task(team_id=self.team.id, repo_ids=[repo.id])

        # Verify
        handler.assert_called_once()
        kwargs = handler.call_args.kwargs
        self.assertEqual(kwargs['team_id'], self.team.id)
    finally:
        onboarding_sync_completed.disconnect(handler)
```

---

## Environment Variables Required

- `GROQ_API_KEY` - For LLM analysis (already configured)
- Email settings (already configured via `settings.py`)

---

## Migration Notes

### Adding Fields to Team Model

```python
# Migration will need:
operations = [
    migrations.AddField(
        model_name='team',
        name='onboarding_pipeline_status',
        field=models.CharField(
            choices=[...],
            default='not_started',
            max_length=50,
        ),
    ),
    migrations.AddField(
        model_name='team',
        name='onboarding_pipeline_error',
        field=models.TextField(blank=True, null=True),
    ),
    migrations.AddField(
        model_name='team',
        name='onboarding_pipeline_started_at',
        field=models.DateTimeField(null=True),
    ),
    migrations.AddField(
        model_name='team',
        name='onboarding_pipeline_completed_at',
        field=models.DateTimeField(null=True),
    ),
]
```

### Backward Compatibility

- Existing teams: `onboarding_pipeline_status = 'not_started'`
- Nightly batch: Continues to work (signals are additive)
- No breaking changes to existing endpoints

---

## Related PRDs

- `prd/ONBOARDING.md` - User onboarding flow
- `prd/IMPLEMENTATION-PLAN.md` - Implementation phases
- `prd/ARCHITECTURE.md` - System architecture

---

## Contact Points

If questions arise about:
- **Celery patterns**: Check `tformance/celery.py`, `settings.py:540-650`
- **Signal patterns**: Check `apps/users/signals.py`, `apps/teams/signals.py`
- **Email templates**: Check `templates/teams/email/`
- **Onboarding flow**: Check `apps/onboarding/views.py`
