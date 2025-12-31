# Dashboard Insights Feature - Context

**Last Updated**: 2026-01-01 (Session 3 - @Mentions Linking)
**Branch**: `main`
**Status**: ✅ Complete - Actionable Links + @Mentions Implemented

## Overview

LLM-powered engineering insights displayed on the main dashboard. Uses Groq API with openai/gpt-oss-20b model to generate weekly/monthly summaries of team performance metrics. Now includes:
- **Actionable insight buttons** - Click "View slow PRs" to filter PR list
- **Clickable @mentions** - @username links open filtered PR list for that user

## Latest Session: @Mentions Linking (2026-01-01)

### What Was Implemented

1. **Clickable @username mentions** - When insights reference contributors like @MrChaker, clicking opens a new tab with PRs filtered to that author
2. **github_name filter for PR list** - Secure endpoint filter `?github_name=@username` (team-scoped)
3. **Enhanced user prompt** - Added Top Contributors, Attention PRs, Issue Ownership sections for more actionable recommendations
4. **linkify_mentions template filter** - Converts @username text to clickable links

### Verified Working

- Generated insight for activepieces-demo team with @MrChaker mention
- Clicking @MrChaker opened new tab with 33 PRs filtered correctly by Chaker Atallah
- Email addresses like user@example.com are NOT treated as mentions (negative lookbehind regex)

## Previous Session: Actionable Insight Links

### What Was Implemented

Added clickable action buttons to insights that link to filtered PR lists. For example, when an insight says "Cycle time has surged 150%", users can click "View slow PRs" to navigate to `/app/pull-requests/?days=30&issue_type=long_cycle`.

### Technical Approach

1. **LLM outputs structured actions** - `action_type` enum + `label` (not raw URLs)
2. **Backend resolves to URLs** - Safe, validated URL generation via `resolve_action_url()`
3. **Template renders buttons** - DaisyUI styled links below recommendation

### Key Code Changes - @Mentions Session

**`apps/metrics/templatetags/pr_list_tags.py`**:
- Added `linkify_mentions` template filter with regex for @usernames:
  ```python
  MENTION_PATTERN = re.compile(r"(?<![a-zA-Z0-9])@([a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)")

  @register.filter
  def linkify_mentions(text: str | None, days: int = 30) -> str:
      # Converts @username to clickable link, escapes HTML, opens in new tab
  ```

**`apps/metrics/services/pr_list_service.py`**:
- Added `github_name` filter to `get_prs_queryset()` - team-scoped lookup

**`apps/metrics/prompts/templates/insight/user.jinja2`**:
- Added ACTIONABLE DATA section with Top Contributors, Attention PRs, Issue Ownership

**`templates/metrics/partials/engineering_insights.html`**:
- Applied `linkify_mentions:days` filter to detail, recommendation, possible_causes

### Key Code Changes - Actionable Links Session

**`apps/metrics/services/insight_llm.py`**:
- Added `actions` array to `INSIGHT_JSON_SCHEMA` with enum types
- Added `ACTION_URL_MAP` and `resolve_action_url()` function
- Updated `INSIGHT_SYSTEM_PROMPT` with @username format instructions
- Added `_build_issue_by_person()` helper for issue aggregation

**`apps/metrics/views/dashboard_views.py`**:
- Import and use `resolve_action_url()` for action URL resolution

**`templates/metrics/partials/engineering_insights.html`**:
- Added action buttons section after recommendation

### Tests Added

**@Mentions Tests:**
- `TestLinkifyMentionsFilter` (8 tests) - Mention rendering, XSS, emails, hyphens
- `github_name` filter tests (4 tests) - Team-scoped security, case insensitivity

**Actionable Links Tests:**
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
| `view_contributors` | `view=contributors` | When work distribution is discussed |
| `view_review_bottlenecks` | `view=reviews&sort=pending` | When review delays are highlighted |

## @Mentions URL Format

`?github_name=@username&days=30` - Opens PR list filtered by author's GitHub username (team-scoped)

## Status: Complete ✅

All features implemented and tested:
- ✅ Action buttons with enum-based types
- ✅ Clickable @mentions in insight text
- ✅ Team-scoped github_name filter
- ✅ Enhanced user prompt with actionable data
- ✅ 34 insight_llm tests passing
- ✅ 8 linkify_mentions tests passing
- ✅ 4 github_name filter tests passing

## Commands

```bash
# Verify all tests pass
DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/pytest apps/metrics/tests/services/test_insight_llm.py apps/metrics/tests/test_pr_list_tags.py::TestLinkifyMentionsFilter apps/metrics/tests/test_pr_list_service.py -k github_name -v

# Generate insight for any team (for testing)
DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/python manage.py shell -c "
from apps.teams.models import Team
from apps.metrics.services.insight_llm import gather_insight_data, generate_insight, cache_insight
from datetime import date, timedelta

team = Team.objects.get(slug='activepieces-demo')
end_date = date.today()
start_date = end_date - timedelta(days=30)

data = gather_insight_data(team, start_date, end_date)
insight = generate_insight(data)
cache_insight(team, insight, end_date, cadence='30')
print('Headline:', insight.get('headline'))
print('Actions:', insight.get('actions'))
"
```
