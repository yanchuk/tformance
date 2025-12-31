# Dashboard Insights Feature - Context

**Last Updated**: 2025-12-31 (Session 2 - Actionable Links)
**Branch**: `main` (was `feature/dashboard-insights`, now merged)
**Status**: Implementation Complete + Actionable Links Added

## Overview

LLM-powered engineering insights displayed on the main dashboard. Uses Groq API with openai/gpt-oss-20b model to generate weekly/monthly summaries of team performance metrics. Now includes **actionable insight links** that let users click through to investigate specific PRs.

## Latest Session: Actionable Insight Links

### What Was Implemented

Added clickable action buttons to insights that link to filtered PR lists. For example, when an insight says "Cycle time has surged 150%", users can click "View slow PRs" to navigate to `/app/pull-requests/?days=30&issue_type=long_cycle`.

### Technical Approach

1. **LLM outputs structured actions** - `action_type` enum + `label` (not raw URLs)
2. **Backend resolves to URLs** - Safe, validated URL generation via `resolve_action_url()`
3. **Template renders buttons** - DaisyUI styled links below recommendation

### Key Code Changes This Session

**`apps/metrics/services/insight_llm.py`**:
- Added `actions` array to `INSIGHT_JSON_SCHEMA`:
  ```python
  "actions": {
      "type": "array",
      "items": {
          "type": "object",
          "properties": {
              "action_type": {"type": "string", "enum": ["view_ai_prs", "view_non_ai_prs", "view_slow_prs", "view_reverts", "view_large_prs"]},
              "label": {"type": "string"}
          },
          "required": ["action_type", "label"],
          "additionalProperties": False
      },
      "minItems": 1,
      "maxItems": 3
  }
  ```
- Added `ACTION_URL_MAP` and `resolve_action_url()` function
- Updated `INSIGHT_SYSTEM_PROMPT` with action type instructions
- Updated `_create_fallback_insight()` to include contextual actions

**`apps/metrics/views/dashboard_views.py`**:
- Added import: `from apps.metrics.services.insight_llm import resolve_action_url`
- Updated `engineering_insights()` to resolve action URLs from LLM output

**`templates/metrics/partials/engineering_insights.html`**:
- Added action buttons section after recommendation

### Tests Added

- `TestResolveActionUrl` (7 tests) - URL resolution logic
- `TestInsightJsonSchemaActions` (5 tests) - Schema validation for actions
- 3 view tests for action URL resolution

### Tests Fixed

Removed/fixed 3 outdated tests checking for `cadence` in context (was removed in earlier refactor):
- `test_default_cadence_is_weekly` - Removed
- `test_accepts_cadence_query_param` - Removed
- `test_context_contains_required_keys` - Updated to not check for `cadence`

## Implementation Summary

### Completed Phases

| Phase | Description | Tests | Commit |
|-------|-------------|-------|--------|
| Phase 1 | Data Layer (DashboardInsightService) | 10 | 9f1604c |
| Phase 2 | LLM Integration (insight_llm.py) | 19 + 41 schema | 9f1604c |
| Phase 3 | Celery Tasks | 8 | 9f1604c |
| Phase 5 | Dashboard UI | 18 view tests | acee607, c7583b5 |
| **NEW** | Actionable Insight Links | 15 tests | uncommitted |

**Total Tests**: ~110 (10 + 19 + 41 + 8 + 18 + 15)

### Deferred

- **Phase 4 (Promptfoo Testing)**: Requires external tool setup, not blocking
- **Email notifications**: Weekly/monthly insight emails deferred to future

## Key Files

### Services
- `apps/metrics/services/insight_service.py` - DashboardInsightService
- `apps/metrics/services/insight_llm.py` - LLM generation + `resolve_action_url()`
- `apps/metrics/services/insight_schema.py` - Pydantic schema (InsightResponseSchema)

### Views
- `apps/metrics/views/dashboard_views.py` - engineering_insights, refresh_insight views

### Templates
- `templates/metrics/partials/engineering_insights.html` - HTMX partial with action buttons
- `templates/web/app_home.html` - Dashboard with insights card

### URLs
- `GET /app/metrics/partials/engineering-insights/` - Fetch cached insight
- `POST /app/metrics/partials/engineering-insights/refresh/` - Regenerate on demand

### Celery Tasks
- `apps/metrics/tasks/insight_tasks.py` - generate_weekly_insights, generate_monthly_insights

### Tests
- `apps/metrics/tests/services/test_insight_llm.py` - 31 LLM service tests (19 original + 12 new)
- `apps/metrics/tests/services/test_insight_tasks.py` - 8 Celery task tests
- `apps/metrics/tests/views/test_dashboard_views.py` - 21 view tests (18 original + 3 new)

## Key Decisions

1. **Model**: openai/gpt-oss-20b via Groq API (fast, cheap ~$0.04/1M input, good JSON reliability)
   - Fallback: llama-3.3-70b-versatile (proven reliable, better reasoning)
   - Uses json_schema response format with strict validation for OSS models
   - Uses json_object format for llama models
2. **Caching**: DailyInsight model with category="llm_insight" and comparison_period
3. **Cadence**: Weekly (Monday) and Monthly (1st) via Celery Beat
4. **UI**: Accessible to all team members (not admin-only)
5. **Fallback**: Graceful fallback response if LLM fails (includes contextual actions)
6. **Action URLs**: Backend-resolved from enum-based action_type (type-safe, maintainable)

## Data Flow

1. Celery task calls `gather_insight_data()` → aggregates metrics from service layer
2. `build_insight_prompt()` renders Jinja2 template with data
3. `generate_insight()` calls Groq API → parses JSON response (includes actions)
4. `cache_insight()` stores in DailyInsight with metric_value=JSON
5. View fetches cached insight, resolves action URLs via `resolve_action_url()`
6. Template renders headline/detail/recommendation/metric_cards/action buttons

## Schema (InsightResponseSchema + Actions)

```json
{
  "headline": "AI-Assisted PRs Show 23% Faster Review Times",
  "detail": "Teams using Copilot...",
  "recommendation": "Consider expanding...",
  "metric_cards": [
    {"label": "AI Adoption", "value": "67%", "trend": "positive"}
  ],
  "actions": [
    {"action_type": "view_ai_prs", "label": "View AI-assisted PRs"},
    {"action_type": "view_slow_prs", "label": "View slow PRs"}
  ],
  "is_fallback": false
}
```

## Action Types

| action_type | URL Params | Use Case |
|-------------|------------|----------|
| `view_ai_prs` | `ai=yes` | When discussing AI adoption or impact |
| `view_non_ai_prs` | `ai=no` | When comparing AI vs non-AI PRs |
| `view_slow_prs` | `issue_type=long_cycle` | When cycle time is a concern |
| `view_reverts` | `issue_type=revert` | When quality/revert rate is highlighted |
| `view_large_prs` | `issue_type=large_pr` | When PR size is mentioned |

## Remaining Work

**Uncommitted changes** - needs commit after session:
- `apps/metrics/services/insight_llm.py` - ACTION_URL_MAP, resolve_action_url(), updated schema/prompt
- `apps/metrics/views/dashboard_views.py` - Import and use resolve_action_url()
- `templates/metrics/partials/engineering_insights.html` - Action buttons HTML
- `apps/metrics/tests/services/test_insight_llm.py` - 12 new tests
- `apps/metrics/tests/views/test_dashboard_views.py` - 3 new tests, 3 fixed tests

## Commands

```bash
# Verify all tests pass
DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/pytest apps/metrics/tests/services/test_insight_llm.py apps/metrics/tests/views/test_dashboard_views.py::TestEngineeringInsightsView -v

# Generate insight for Antiwork team (for testing)
DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/python manage.py shell -c "
from apps.teams.models import Team
from apps.metrics.services.insight_llm import gather_insight_data, generate_insight, cache_insight
from datetime import date, timedelta

team = Team.objects.get(slug='antiwork')
end_date = date.today()
start_date = end_date - timedelta(days=30)

data = gather_insight_data(team, start_date, end_date)
insight = generate_insight(data)
cache_insight(team, insight, end_date, cadence='30')
print('Headline:', insight.get('headline'))
print('Actions:', insight.get('actions'))
"

# Commit the changes
git add -A && git commit -m "feat(insights): add actionable insight links with TDD

- Add actions array to JSON schema (enum-based action types)
- Add resolve_action_url() for backend URL resolution
- Update system prompt with action type instructions
- Add action buttons to insight template
- Update fallback insight to include contextual actions
- Add 15 tests for URL resolution and schema validation
- Fix 3 outdated tests checking for removed cadence context

Action types: view_ai_prs, view_non_ai_prs, view_slow_prs, view_reverts, view_large_prs"
```
