# Phase 1: Rule-Based Insights - Context

**Last Updated:** 2025-12-21
**Status:** ✅ COMPLETE

## Implementation Summary

Phase 1 of the AI insights feature is complete. The system generates pre-computed daily insights that surface actionable information on the CTO dashboard.

### What Was Built

1. **DailyInsight Model** - Stores pre-computed insights with categories, priorities, and dismiss functionality
2. **Insight Engine** - Runs rules and saves results to database with error handling
3. **7 Insight Rules** - 2 trend, 3 anomaly, 2 action rules
4. **Celery Tasks** - `compute_team_insights` and `compute_all_team_insights` scheduled at 6 AM UTC
5. **Dashboard Integration** - Insights panel on CTO dashboard with HTMX dismiss

## Architecture

```
apps/metrics/
├── insights/
│   ├── __init__.py              # Package init with rule registration
│   ├── engine.py                # InsightResult, InsightRule ABC, compute_insights()
│   └── rules.py                 # 7 rule implementations
├── migrations/
│   └── 0011_add_daily_insight.py
├── services/
│   └── insight_service.py       # get_recent_insights()
├── tasks.py                     # Celery tasks
├── models.py                    # DailyInsight model
├── factories.py                 # DailyInsightFactory
└── tests/
    ├── test_daily_insight.py    # 22 tests
    ├── test_insight_engine.py   # 17 tests
    ├── test_insight_rules.py    # 35 tests
    ├── test_insight_tasks.py    # 11 tests
    └── test_insight_dashboard.py # 11 tests
```

## 7 Implemented Rules

| Rule | Category | Priority | Trigger |
|------|----------|----------|---------|
| AIAdoptionTrendRule | trend | medium | >10% change over 4 weeks |
| CycleTimeTrendRule | trend | medium/high | >20% change (high if regression) |
| HotfixSpikeRule | anomaly | high | 3x above 4-week average |
| RevertSpikeRule | anomaly | high | Any reverts in current week |
| CIFailureRateRule | anomaly | medium | >20% failure rate |
| RedundantReviewerRule | action | low | 95%+ agreement on 10+ PRs |
| UnlinkedPRsRule | action | low | 5+ PRs missing Jira links |

## Key Design Decisions

1. **InsightResult dataclass** - Immutable data transfer object for rule outputs
2. **InsightRule ABC** - Abstract base class enforcing `evaluate(team, date)` contract
3. **Module-level registry** - Rules registered on import, cleared for testing
4. **Template Method pattern** - `BaseTrendRule` for trend detection with subclasses implementing specific logic
5. **Class constants** - All thresholds defined as class constants for maintainability

## Thresholds

```python
# Trend Rules
AIAdoptionTrendRule.CHANGE_THRESHOLD = 10      # percentage points
CycleTimeTrendRule.CHANGE_THRESHOLD = 20       # percent

# Anomaly Rules
HotfixSpikeRule.SPIKE_THRESHOLD = 3            # 3x above average
CIFailureRateRule.FAILURE_THRESHOLD = 20       # percent

# Action Rules
UnlinkedPRsRule.THRESHOLD = 5                  # minimum PRs
RedundantReviewerRule.MAX_PAIRS_TO_REPORT = 3  # limit output
```

## Dependencies

### Dashboard Service Functions Used
```python
from apps.metrics.services.dashboard_service import (
    get_ai_adoption_trend,      # AIAdoptionTrendRule
    get_cycle_time_trend,       # CycleTimeTrendRule
    get_revert_hotfix_stats,    # HotfixSpikeRule, RevertSpikeRule
    get_cicd_pass_rate,         # CIFailureRateRule
    get_reviewer_correlations,  # RedundantReviewerRule
    get_unlinked_prs,           # UnlinkedPRsRule
)
```

## Test Coverage

- 96 new tests added, all passing
- Full test suite: 1716 tests passing

## Commit

`db55990` - Add rule-based insights system with 7 rules and dashboard integration

## Next Steps (Phase 2)

1. **LLM-Powered Insights** - Use Gemini function calling to analyze metrics and generate natural language insights
2. **Comparison Rules** - AI vs non-AI quality comparison, top performer rule
3. **Enhanced UI** - Category icons, trend indicators, historical view
