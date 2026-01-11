# Copilot Data Flow - Context

**Last Updated: 2026-01-11**

## Key Files

### Files to Modify

| File | Purpose | Changes |
|------|---------|---------|
| `apps/teams/models.py` | Team model | Add copilot_status, copilot_last_sync_at, copilot_consecutive_failures fields |
| `tformance/settings.py` | Celery Beat | Add sync-copilot-metrics-daily schedule |
| `apps/integrations/_task_modules/copilot.py` | Sync tasks | Filter by team.copilot_status, add monitoring |
| `apps/integrations/pipeline_signals.py` | State machine | Add syncing_copilot state (optional) |

### Files to Reference (Read-Only)

| File | Purpose |
|------|---------|
| `apps/integrations/services/copilot_metrics.py` | API client |
| `apps/integrations/services/integration_flags.py` | Feature flags |
| `apps/metrics/models/aggregations.py` | AIUsageDaily, CopilotSeatSnapshot |
| `apps/metrics/services/insight_llm.py` | LLM insight generation |

### Test Files

| File | Status |
|------|--------|
| `apps/teams/tests/test_copilot_status.py` | ✅ TDD RED complete (12 tests) |
| `apps/integrations/tests/test_copilot_sync.py` | Existing (needs update) |

## Key Decisions

### Decision 1: copilot_status (Choice) vs copilot_enabled (Boolean)

**Choice:** Use `copilot_status` CharField with choices, derive `copilot_enabled` as property.

**Rationale:**
- Rich state machine enables better UX messaging
- Four states: disabled, connected, insufficient_licenses, token_revoked
- Property provides backward compatibility

```python
COPILOT_STATUS_CHOICES = [
    ("disabled", "Not Connected"),
    ("connected", "Connected"),
    ("insufficient_licenses", "Awaiting Data"),
    ("token_revoked", "Reconnection Required"),
]

@property
def copilot_enabled(self) -> bool:
    return self.copilot_status == "connected"
```

### Decision 2: Nightly Sync Schedule

**Choice:** 4:45 AM UTC

**Rationale:**
- After GitHub member sync (4:15 AM)
- After Jira sync (4:30 AM)
- Before LLM analysis (5:00 AM)
- Ensures fresh Copilot data for morning insights

### Decision 3: Team Filtering Logic

**Choice:** Only sync teams where `copilot_status == "connected"`

**Rationale:**
- Don't waste API calls on teams that skipped Copilot
- Don't sync teams with insufficient licenses (would 403)
- Don't sync teams with revoked tokens (would 401)

## Dependencies

### Required Before Implementation

1. Feature flag `integration_copilot_enabled` exists ✅
2. `sync_copilot_metrics_task` exists ✅
3. `sync_all_copilot_metrics` exists ✅
4. AIUsageDaily model exists ✅

### External Dependencies

1. GitHub Copilot Metrics API requires 5+ licenses
2. OAuth scope `manage_billing:copilot` must be granted

## Edge Cases

### 403 Error (< 5 licenses)

```python
# In sync_copilot_metrics_task
if "403" in str(exc):
    team.copilot_status = "insufficient_licenses"
    team.save(update_fields=["copilot_status"])
    return {"status": "skipped", "reason": "insufficient_licenses"}
```

### 401 Error (Token revoked)

```python
# In sync_copilot_metrics_task
if "401" in str(exc):
    team.copilot_status = "token_revoked"
    team.save(update_fields=["copilot_status"])
    credential.is_revoked = True
    credential.save(update_fields=["is_revoked"])
```

### License Count Changes

Track consecutive failures:
```python
if sync_failed:
    team.copilot_consecutive_failures += 1
    if team.copilot_consecutive_failures >= 3:
        team.copilot_status = "insufficient_licenses"
else:
    team.copilot_consecutive_failures = 0
    team.copilot_last_sync_at = timezone.now()
```

## Code Snippets

### Team Model Fields

```python
# apps/teams/models.py

COPILOT_STATUS_CHOICES = [
    ("disabled", "Not Connected"),
    ("connected", "Connected"),
    ("insufficient_licenses", "Awaiting Data"),
    ("token_revoked", "Reconnection Required"),
]

class Team(SubscriptionModelBase, BaseModel):
    # ... existing fields ...

    # Copilot integration
    copilot_status = models.CharField(
        max_length=30,
        choices=COPILOT_STATUS_CHOICES,
        default="disabled",
        help_text="Current Copilot integration status",
    )
    copilot_last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful Copilot data sync",
    )
    copilot_consecutive_failures = models.PositiveIntegerField(
        default=0,
        help_text="Count of consecutive sync failures (reset on success)",
    )

    @property
    def copilot_enabled(self) -> bool:
        """Backward-compatible property for checking Copilot connectivity."""
        return self.copilot_status == "connected"
```

### Celery Beat Schedule

```python
# tformance/settings.py

SCHEDULED_TASKS = {
    # ... existing tasks ...

    "sync-copilot-metrics-daily": {
        "task": "apps.integrations.tasks.sync_all_copilot_metrics",
        "schedule": schedules.crontab(minute=45, hour=4),
        "options": {"expire_seconds": 60 * 60 * 2},  # 2 hour expiry
    },
}
```

### Sync Task Filtering

```python
# apps/integrations/_task_modules/copilot.py

@shared_task
def sync_all_copilot_metrics() -> dict:
    import time
    start_time = time.time()

    if not is_copilot_sync_globally_enabled():
        return {"status": "skipped", "reason": "flag_disabled"}

    # Only sync teams with connected status
    teams = Team.objects.filter(copilot_status="connected")

    teams_dispatched = 0
    teams_skipped = 0

    for team in teams:
        try:
            integration = GitHubIntegration.objects.get(team=team)
            if integration.organization_slug:
                sync_copilot_metrics_task.delay(team.id)
                teams_dispatched += 1
            else:
                teams_skipped += 1
        except GitHubIntegration.DoesNotExist:
            teams_skipped += 1

    duration = time.time() - start_time
    logger.info(
        f"Copilot sync: dispatched={teams_dispatched}, "
        f"skipped={teams_skipped}, duration={duration:.1f}s"
    )

    return {
        "teams_dispatched": teams_dispatched,
        "teams_skipped": teams_skipped,
        "duration_seconds": duration,
    }
```
