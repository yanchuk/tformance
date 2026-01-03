# Alpha QA Fixes - Context

## Key Files Reference

### Core Files to Modify

| File | Issues | Lines of Interest |
|------|--------|-------------------|
| `apps/metrics/services/dashboard_service.py` | A-001 | 42 (MIN_SPARKLINE_SAMPLE_SIZE), 2216-2280 (_calculate_change_and_trend) |
| `apps/integrations/services/integration_flags.py` | A-002 | Full file - flag helpers |
| `templates/onboarding/base.html` | A-002 | 34-76 (stepper), 81-125 (sync indicator) |
| `templates/onboarding/start.html` | A-003, A-004 | 41-45 (Copilot), 61-66 (privacy) |
| `templates/onboarding/complete.html` | A-002 | 38-55 (Setup Summary), 65 (footer) |
| `templates/onboarding/sync_progress.html` | A-002 | Continue button |
| `templates/account/profile.html` | A-013, A-015 | 12 (api_keys include) |
| `templates/account/components/api_keys.html` | A-015 | Full file |
| `templates/account/components/social/social_accounts.html` | A-014 | GitHub logo |
| `templates/teams/manage_team.html` | A-012 | 85 (Delete Team button) |
| `templates/metrics/cto_dashboard.html` | A-002, A-009-011 | Enhance insights banner, sync banner |

### Test Files

| File | Purpose |
|------|---------|
| `apps/metrics/tests/dashboard/test_sparkline_data.py` | Trend calculation tests |
| `apps/onboarding/tests/test_flag_skip.py` | Feature flag skip tests |
| `apps/integrations/tests/test_integration_flags.py` | Flag service tests |
| `tests/e2e/integration-flags.spec.ts` | E2E flag tests |

### Views

| File | Issues |
|------|--------|
| `apps/onboarding/views.py` | A-002, A-006, A-007 |
| `apps/integrations/views/status.py` | A-002 (dashboard banner) |
| `apps/users/views.py` | A-016 (new delete account) |

---

## Feature Flag System

### Current Flags

```python
# apps/integrations/services/integration_flags.py
FLAG_JIRA = "integration_jira_enabled"
FLAG_COPILOT = "integration_copilot_enabled"
FLAG_SLACK = "integration_slack_enabled"
FLAG_GOOGLE_WORKSPACE = "integration_google_workspace_enabled"
```

### Usage Pattern

```python
from apps.integrations.services.integration_flags import is_integration_enabled

# In views
jira_enabled = is_integration_enabled(request, 'jira')
slack_enabled = is_integration_enabled(request, 'slack')
```

### In Templates (with django-waffle)

```django
{% load waffle_tags %}
{% flag "integration_jira_enabled" %}
  {# Show Jira content #}
{% endflag %}
```

Or pass from view:
```django
{% if jira_enabled %}
  {# Show Jira content #}
{% endif %}
```

---

## Sync System Architecture

### Task Flow

```
select_repositories (POST)
  ↓
start_onboarding_pipeline(team_id, repo_ids)
  ↓
Celery Task: onboarding_pipeline_task
  ↓
sync_repository_task (per repo)
  ↓
run_llm_batch_analysis_task
  ↓
calculate_metrics_task
  ↓
generate_daily_insight_task
```

### Progress Polling

```
Frontend polls: /celery-progress/{task_id}/
  ↓
Returns: { complete: bool, progress: { current, total } }
```

### Database Status

```python
# TrackedRepository.sync_status values
SYNC_STATUS_PENDING = "pending"
SYNC_STATUS_SYNCING = "syncing"
SYNC_STATUS_COMPLETE = "complete"
SYNC_STATUS_ERROR = "error"
```

---

## Trend Calculation Logic

### Current Implementation (dashboard_service.py:2216)

```python
def _calculate_change_and_trend(
    values: list,
    sample_sizes: list | None = None,
    min_sample_size: int = MIN_SPARKLINE_SAMPLE_SIZE,  # Currently 3
) -> tuple[int, str]:
    # Find first/last valid week (>= min_sample_size PRs)
    # Calculate percentage change
    # Return (change_pct, trend_direction)
```

### Problem

- `MIN_SPARKLINE_SAMPLE_SIZE = 3` is too low
- First week with 3 PRs and 0.04h review time → baseline too small
- Comparing to current week → extreme percentages (+3100%, +12096%)
- No cap on maximum percentage displayed

### Fix Required

```python
MIN_SPARKLINE_SAMPLE_SIZE = 10  # More reliable baseline
MAX_TREND_PERCENTAGE = 500  # Cap extreme values

# In _calculate_change_and_trend():
change_pct = max(-MAX_TREND_PERCENTAGE, min(MAX_TREND_PERCENTAGE, change_pct))
```

---

## UI Class Mappings

### Pegasus to DaisyUI Migration

| Pegasus Class | DaisyUI Equivalent |
|--------------|-------------------|
| `pg-button-primary` | `btn btn-primary` |
| `pg-button-secondary` | `btn btn-secondary` |
| `pg-button-danger` | `btn btn-error` |
| `pg-text-success` | `text-success` |
| `pg-text-danger` | `text-error` |
| `pg-table` | `table` |
| `pg-subtitle` | Custom or `text-xl font-semibold` |

### App-Specific Classes

```css
/* assets/styles/app/tailwind/design-system.css */
.app-card { /* Card container */ }
.app-btn-primary { /* Primary button */ }
.app-btn-secondary { /* Secondary button */ }
.app-status-connected { /* Success status */ }
.app-status-error { /* Error status */ }
```

---

## Dependencies

### Python Packages
- `django-waffle` - Feature flags
- `celery` - Background tasks
- `celery-progress` - Task progress tracking

### NPM Packages
- `@playwright/test` - E2E testing

### External Services
- Redis (Celery broker + cache)
- PostgreSQL (database)
- GitHub API (OAuth + data sync)

---

## Test Commands

```bash
# Unit tests
make test ARGS='apps.metrics.tests.dashboard.test_sparkline_data'
make test ARGS='apps.onboarding.tests.test_flag_skip'

# E2E tests
make e2e                    # All E2E
make e2e-smoke              # Smoke only
npx playwright test integration-flags.spec.ts  # Specific

# Coverage
make test-coverage
```

---

## Database Queries for Investigation

### Check Sync Status
```sql
SELECT id, full_name, sync_status, sync_progress, last_sync_at
FROM integrations_trackedrepository
WHERE team_id = <team_id>;
```

### Check Team Members
```sql
SELECT COUNT(*) FROM metrics_teammember WHERE team_id = <team_id>;
```

### Check PR Count for Trends
```sql
SELECT date_trunc('week', merged_at) as week, COUNT(*)
FROM metrics_pullrequest
WHERE team_id = <team_id> AND state = 'merged'
GROUP BY 1 ORDER BY 1;
```

---

## Member Sync Architecture (A-007 Fix)

### Problem

The onboarding views were calling `member_sync.sync_github_members(team)` with only 1 argument, but the function requires 3 arguments (`team`, `access_token`, `org_slug`). This caused a silent TypeError that was caught and logged but not fixed.

### Two GitHub Connection Flows

| Flow | Model Created | Task |
|------|---------------|------|
| OAuth (select_organization) | `GitHubIntegration` | `sync_github_members_task` |
| GitHub App (github_app_callback) | `GitHubAppInstallation` | `sync_github_app_members_task` (NEW) |

### Solution

1. **Created new task** `sync_github_app_members_task(installation_id)` in `apps/integrations/tasks.py:598`
   - Gets installation token via `get_installation_token(installation.installation_id)`
   - Calls `sync_github_members(team, access_token, org_slug)`

2. **Updated helper** `_sync_github_members_after_connection(team)` in `apps/integrations/views/helpers.py:152`
   - Tries GitHubIntegration first (OAuth flow)
   - Falls back to GitHubAppInstallation (App flow)
   - Returns False only if neither exists

3. **Updated onboarding views** to use the helper instead of direct (broken) call

### Key Files Modified

| File | Change |
|------|--------|
| `apps/integrations/tasks.py` | Added `sync_github_app_members_task` |
| `apps/integrations/views/helpers.py` | Updated helper to handle both flows |
| `apps/onboarding/views.py` | Use helper instead of direct call |
| `apps/onboarding/tests/test_github_app_views.py` | Updated test for correct task |

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sample size threshold | 10 PRs | More statistically reliable than 3 |
| Percentage cap | ±500% | Beyond this is not meaningful |
| Stepper rendering | Backend context | Simpler than Alpine.js dynamic numbering |
| Sync indicator location | Bottom-right widget | Less intrusive, persistent |
| API Keys hiding | Comment out include | Quick fix, no flag overhead |
| Delete account | New feature | GDPR compliance important |
| Member sync dual-path | Separate tasks per flow | Clean separation, no adapter complexity |

---

## Session Progress (2026-01-03)

### Completed Issues

| Issue | PR | Status |
|-------|-----|--------|
| A-001 | Trend percentages capped at ±500% | ✅ Tests passing |
| A-002 | Jira/Slack hidden when flags disabled | ✅ Tests passing |
| A-003 | Privacy callout box styled | ✅ Visual |
| A-004 | Copilot "coming soon" label | ✅ Visual |
| A-007 | Team members sync fixed | ✅ 17/17 tests passing |
| A-015 | API Keys section hidden | ✅ Visual |

### Remaining Issues

| Issue | Priority | Status |
|-------|----------|--------|
| A-006 | P0 | Investigation needed |
| A-005, A-008-018 | P2/P3 | Not started |

---

*Last Updated: 2026-01-03*
