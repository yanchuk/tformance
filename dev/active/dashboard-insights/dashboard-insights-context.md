# Dashboard Insights Feature - Context

**Last Updated**: 2025-12-31
**Branch**: `feature/dashboard-insights`
**Status**: Implementation Complete

## Overview

LLM-powered engineering insights displayed on the main dashboard. Uses Groq API with deepseek-r1-distill-qwen-32b model to generate weekly/monthly summaries of team performance metrics.

## Implementation Summary

### Completed Phases

| Phase | Description | Tests | Commit |
|-------|-------------|-------|--------|
| Phase 1 | Data Layer (DashboardInsightService) | 10 | 9f1604c |
| Phase 2 | LLM Integration (insight_llm.py) | 19 + 41 schema | 9f1604c |
| Phase 3 | Celery Tasks | 8 | 9f1604c |
| Phase 5 | Dashboard UI | 18 view tests | acee607, c7583b5 |

**Total Tests**: 96 (10 + 19 + 41 + 8 + 18)

### Deferred

- **Phase 4 (Promptfoo Testing)**: Requires external tool setup, not blocking
- **Email notifications**: Weekly/monthly insight emails deferred to future

## Key Files

### Services
- `apps/metrics/services/insight_service.py` - DashboardInsightService
- `apps/metrics/services/insight_llm.py` - LLM generation functions
- `apps/metrics/services/insight_schema.py` - Pydantic schema (InsightResponseSchema)

### Views
- `apps/metrics/views/dashboard_views.py` - engineering_insights, refresh_insight views

### Templates
- `templates/metrics/partials/engineering_insights.html` - HTMX partial
- `templates/web/app_home.html` - Dashboard with insights card

### URLs
- `GET /app/metrics/partials/engineering-insights/` - Fetch cached insight
- `POST /app/metrics/partials/engineering-insights/refresh/` - Regenerate on demand

### Celery Tasks
- `apps/metrics/tasks/insight_tasks.py` - generate_weekly_insights, generate_monthly_insights

### Tests
- `apps/metrics/tests/services/test_insight_llm.py` - 19 LLM service tests
- `apps/metrics/tests/services/test_insight_tasks.py` - 8 Celery task tests
- `apps/metrics/tests/views/test_dashboard_views.py` - 18 view tests (insight endpoints)

## Key Decisions

1. **Model**: deepseek-r1-distill-qwen-32b via Groq API (fast, cheap, good quality)
2. **Caching**: DailyInsight model with category="llm_insight" and comparison_period
3. **Cadence**: Weekly (Monday) and Monthly (1st) via Celery Beat
4. **UI**: Accessible to all team members (not admin-only)
5. **Fallback**: Graceful fallback response if LLM fails

## Data Flow

1. Celery task calls `gather_insight_data()` → aggregates metrics from service layer
2. `build_insight_prompt()` renders Jinja2 template with data
3. `generate_insight()` calls Groq API → parses JSON response
4. `cache_insight()` stores in DailyInsight with metric_value=JSON
5. View fetches cached insight by team + cadence + date
6. Template renders headline/detail/recommendation/metric_cards

## Schema (InsightResponseSchema)

```json
{
  "headline": "AI-Assisted PRs Show 23% Faster Review Times",
  "detail": "Teams using Copilot...",
  "recommendation": "Consider expanding...",
  "metric_cards": [
    {"label": "AI Adoption", "value": "67%", "trend": "positive"}
  ],
  "is_fallback": false
}
```

## Remaining Work

None - feature is complete. Ready for merge to main after testing in staging.

## Commands

```bash
# Run all insight tests
cd /Users/yanchuk/Documents/GitHub/tformance-dashboard-insights
.venv/bin/pytest apps/metrics/tests/services/test_insight_llm.py apps/metrics/tests/services/test_insight_tasks.py apps/metrics/tests/views/test_dashboard_views.py::TestEngineeringInsightsView apps/metrics/tests/views/test_dashboard_views.py::TestRefreshInsightView -v

# Manual test: trigger insight generation
.venv/bin/python manage.py shell
>>> from apps.metrics.tasks.insight_tasks import generate_weekly_insights
>>> generate_weekly_insights()
```
