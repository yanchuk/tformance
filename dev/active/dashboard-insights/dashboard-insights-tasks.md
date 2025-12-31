# Dashboard Insights Feature - Tasks

**Last Updated**: 2025-12-31 (Session 2)

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

- [x] **NEW: Actionable Insight Links** (Session 2)
  - [x] Add `actions` array to INSIGHT_JSON_SCHEMA
  - [x] Add ACTION_URL_MAP constant
  - [x] Implement resolve_action_url() function
  - [x] Update INSIGHT_SYSTEM_PROMPT with action type instructions
  - [x] Update _create_fallback_insight() to include contextual actions
  - [x] Update engineering_insights view to resolve action URLs
  - [x] Add action buttons to template
  - [x] Add TestResolveActionUrl tests (7 tests)
  - [x] Add TestInsightJsonSchemaActions tests (5 tests)
  - [x] Add view tests for action URL resolution (3 tests)
  - [x] Fix outdated cadence tests (removed 2, fixed 1)
  - [x] Generate insights for Antiwork team (7, 30, 90 days)
  - [x] Verify UI renders action buttons correctly
  - [x] Verify clicking buttons navigates to filtered PR list

## Deferred Tasks

- [ ] Phase 4: Promptfoo Testing (optional, requires external setup)
- [ ] Email notifications (weekly/monthly insight emails)

## Uncommitted Changes (Needs Commit)

The following changes were made in this session and need to be committed:

| File | Change |
|------|--------|
| `apps/metrics/services/insight_llm.py` | ACTION_URL_MAP, resolve_action_url(), updated schema, updated prompt, updated fallback |
| `apps/metrics/views/dashboard_views.py` | Import resolve_action_url, update engineering_insights view |
| `templates/metrics/partials/engineering_insights.html` | Action buttons section |
| `apps/metrics/tests/services/test_insight_llm.py` | TestResolveActionUrl (7), TestInsightJsonSchemaActions (5) |
| `apps/metrics/tests/views/test_dashboard_views.py` | 3 new tests, 2 removed tests, 1 fixed test |

**No migrations needed** - only code changes, no model modifications.

## Commits

1. `9f1604c` - feat(insights): add LLM-powered dashboard insights (Phases 1-3)
2. `acee607` - feat(insights): add Engineering Insights card to dashboard (Phase 5)
3. `c7583b5` - test(insights): add view tests for engineering_insights endpoints (Phase 6)
4. **PENDING** - feat(insights): add actionable insight links with TDD

## Test Summary

| Test File | Tests | Passing |
|-----------|-------|---------|
| test_insight_llm.py | 31 (19 + 12 new) | ✅ |
| test_insight_tasks.py | 8 | ✅ |
| test_dashboard_views.py (insights) | 21 (18 - 2 removed + 3 new + 2 unchanged) | ✅ |
| Schema tests (InsightResponseSchema) | 41 | ✅ |

**Total**: ~101 tests passing

## Verification Commands

```bash
# Run insight-related tests
DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/pytest apps/metrics/tests/services/test_insight_llm.py apps/metrics/tests/views/test_dashboard_views.py::TestEngineeringInsightsView -v

# Should see all 43 tests pass:
# - TestResolveActionUrl (7 tests)
# - TestInsightJsonSchemaActions (5 tests)
# - TestEngineeringInsightsView (15 tests including 3 new action tests)
# - Other insight_llm tests (19 tests)

# Verify dev server is running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/

# View insights in browser
# http://localhost:8000/app/ (login as admin@example.com / admin123)
```
