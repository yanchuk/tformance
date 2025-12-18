# Copilot Integration Context

**Last Updated: 2025-12-18**
**Status: IMPLEMENTATION COMPLETE**

## Files Created/Modified This Session

### New Files Created

| File | Purpose |
|------|---------|
| `apps/integrations/services/copilot_metrics.py` | Copilot API client service |
| `apps/integrations/tests/test_copilot_metrics.py` | Unit tests for service (18 tests) |
| `apps/integrations/tests/test_copilot_sync.py` | Unit tests for sync tasks (10 tests) |

### Files Modified

| File | Changes |
|------|---------|
| `apps/integrations/services/github_oauth.py` | Added `manage_billing:copilot` scope, refactored to list format |
| `apps/integrations/tasks.py` | Added `sync_copilot_metrics_task` and `sync_all_copilot_metrics` |
| `apps/integrations/views.py` | Added `copilot_sync` view, updated `integrations_home` context |
| `apps/integrations/urls.py` | Added `copilot/sync/` URL pattern |
| `apps/metrics/services/dashboard_service.py` | Added 3 Copilot dashboard functions |
| `apps/integrations/tests/test_github_oauth.py` | Added scope tests |
| `apps/integrations/tests/test_views.py` | Added `TestCopilotSettings` class |
| `apps/metrics/tests/test_dashboard_service.py` | Added `TestCopilotDashboardService` class |

## Key Implementation Details

### Copilot Metrics Service (`copilot_metrics.py`)

```python
# Functions implemented:
check_copilot_availability(access_token, org_slug) -> bool
fetch_copilot_metrics(access_token, org_slug, since=None, until=None) -> list
parse_metrics_response(data) -> list[dict]
map_copilot_to_ai_usage(parsed_day_data) -> dict

# Exception class:
CopilotMetricsError - raised on API errors
```

### Celery Tasks (`tasks.py`)

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_copilot_metrics_task(self, team_id: int) -> dict
    # Syncs Copilot metrics for a single team
    # Handles 403 (Copilot unavailable) without retry
    # Retries other errors with exponential backoff

@shared_task
def sync_all_copilot_metrics() -> dict
    # Dispatches sync tasks for all teams with GitHub integration
```

### Dashboard Service Functions (`dashboard_service.py`)

```python
get_copilot_metrics(team, start_date, end_date) -> dict
    # Returns: total_suggestions, total_accepted, acceptance_rate, active_users

get_copilot_trend(team, start_date, end_date) -> list[dict]
    # Returns weekly acceptance rate trend

get_copilot_by_member(team, start_date, end_date) -> list[dict]
    # Returns per-member breakdown
```

### View Context (`views.py` - integrations_home)

```python
# Added to context:
copilot_available = github_integration is not None
copilot_last_sync = AIUsageDaily.objects.filter(
    team=team, source='copilot'
).order_by('-created_at').first()
```

## Data Flow

```
GitHub Copilot API
    │
    ▼
copilot_metrics.py (fetch_copilot_metrics)
    │
    ▼
copilot_metrics.py (parse_metrics_response)
    │
    ▼
copilot_metrics.py (map_copilot_to_ai_usage)
    │
    ▼
tasks.py (sync_copilot_metrics_task)
    │
    ▼
AIUsageDaily model (source='copilot')
    │
    ▼
dashboard_service.py (get_copilot_*)
    │
    ▼
Dashboard views/templates
```

## API Reference

### GitHub Copilot Metrics API

**Endpoint:** `GET /orgs/{org}/copilot/metrics`

**Headers:**
```
Authorization: Bearer {token}
Accept: application/vnd.github+json
```

**Query Params:** `since`, `until` (YYYY-MM-DD format)

**Response:** Array of daily metrics objects

**Error Codes:**
- 403: Org has <5 Copilot licenses or insufficient permissions
- 404: Org not found
- 422: Copilot metrics disabled

## Key Decisions Made

1. **PyGithub doesn't support Copilot metrics API** - Used direct `requests` calls
2. **No model migration needed** - Existing `AIUsageDaily` model sufficient
3. **Acceptance rate calculation** - `(accepted / suggestions) * 100` with Decimal precision
4. **Error handling** - 403 returns gracefully, other errors retry with backoff
5. **TDD approach** - All phases implemented with Red-Green-Refactor cycle

## Test Coverage

| Test Module | Tests | Status |
|-------------|-------|--------|
| test_github_oauth.py | 48 | Passing |
| test_copilot_metrics.py | 18 | Passing |
| test_copilot_sync.py | 10 | Passing |
| test_dashboard_service.py (Copilot) | 4 | Passing |
| test_views.py (Copilot) | 3 | Passing |

## Commands to Verify

```bash
# Run all Copilot-related tests
.venv/bin/python manage.py test apps.integrations.tests.test_copilot_metrics --keepdb
.venv/bin/python manage.py test apps.integrations.tests.test_copilot_sync --keepdb
.venv/bin/python manage.py test apps.integrations.tests.test_views.TestCopilotSettings --keepdb
.venv/bin/python manage.py test apps.metrics.tests.test_dashboard_service.TestCopilotDashboardService --keepdb

# Run full test suite
make test ARGS='--keepdb'

# Check for missing migrations
make migrations
```

## Remaining Work (Future Enhancement)

1. **Celery Beat Schedule** - Add to `CELERY_BEAT_SCHEDULE` in settings
2. **Frontend Templates** - Add Copilot section to integrations home
3. **Dashboard Charts** - Visualize Copilot data with Chart.js
4. **CLAUDE.md Update** - Document Copilot integration

## Dependencies

- `requests` library (already installed)
- GitHub OAuth with `manage_billing:copilot` scope
- Celery for background tasks
- Sentry for error logging
