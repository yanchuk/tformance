# Dashboard Insights Feature - Tasks

**Last Updated**: 2025-12-31

## Completed Tasks

- [x] Phase 1: Data Layer (DashboardInsightService)
  - [x] DashboardInsightService with gather_velocity_data, gather_quality_data, etc.
  - [x] 10 unit tests for data gathering

- [x] Phase 2: LLM Integration
  - [x] insight_llm.py with gather_insight_data, build_insight_prompt, generate_insight, cache_insight
  - [x] Jinja2 prompt template at apps/metrics/prompts/templates/insights_prompt.j2
  - [x] InsightResponseSchema for parsing LLM response
  - [x] 19 unit tests + 41 schema tests

- [x] Phase 3: Celery Tasks
  - [x] generate_weekly_insights task (runs Monday 7am)
  - [x] generate_monthly_insights task (runs 1st of month 7am)
  - [x] 8 task tests

- [x] Phase 5: Dashboard UI
  - [x] engineering_insights.html partial template
  - [x] engineering_insights view (GET)
  - [x] refresh_insight view (POST)
  - [x] URL patterns
  - [x] Integration into app_home.html
  - [x] 18 view tests

## Deferred Tasks

- [ ] Phase 4: Promptfoo Testing (optional, requires external setup)
- [ ] Email notifications (weekly/monthly insight emails)

## Commits

1. `9f1604c` - feat(insights): add LLM-powered dashboard insights (Phases 1-3)
2. `acee607` - feat(insights): add Engineering Insights card to dashboard (Phase 5)
3. `c7583b5` - test(insights): add view tests for engineering_insights endpoints (Phase 6)

## Test Summary

| Test File | Tests | Passing |
|-----------|-------|---------|
| test_insight_llm.py | 19 | ✅ |
| test_insight_tasks.py | 8 | ✅ |
| test_dashboard_views.py (insights) | 18 | ✅ |
| Schema tests (InsightResponseSchema) | 41 | ✅ |

**Total**: 86+ tests passing
