# Insights DateTime Bug - Context

**Last Updated:** 2025-12-22

## Key Files

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/metrics/services/dashboard_service.py` | Dashboard data functions | Fix datetime serialization |
| `apps/metrics/insights/rules.py` | Insight rule implementations | None (uses dashboard service) |
| `apps/metrics/insights/engine.py` | Insight engine | None (just saves to DB) |
| `apps/metrics/models/insights.py` | DailyInsight model | None (JSONField is fine) |
| `apps/metrics/tests/test_insight_rules.py` | Rule tests | Add serialization tests |

## Bug Discovery Context

During Gumroad demo data seeding, the insights engine failed with:
```
TypeError: Object of type datetime is not JSON serializable
```

This happened when `compute_insights()` tried to save insights to the database.

## Root Cause Details

### Line-by-line trace:

1. `dashboard_service.py:151-159` - TruncWeek returns datetime
```python
weekly_data = (
    prs.annotate(week=TruncWeek("merged_at"))  # datetime object
    .values("week")
    ...
)
```

2. `dashboard_service.py:163-164` - datetime passed through unchanged
```python
result.append({"week": entry["week"], "value": pct})  # datetime object
```

3. `rules.py:196` - datetime embedded in metric_value dict
```python
metric_value={"trend": trend_data, "change": change},
```

4. `engine.py:120` - Fails when saving to JSONField
```python
metric_value=result.metric_value,  # Cannot serialize datetime
```

## Dependencies

- Django's `TruncWeek` returns `datetime` objects
- PostgreSQL JSONField uses Python's `json.dumps()` which doesn't handle datetime
- Chart.js on frontend can handle ISO date strings fine

## Related Functions to Check

All functions that use `TruncWeek` or similar:
- `get_ai_adoption_trend()` - **AFFECTED**
- `get_cycle_time_trend()` via `_get_metric_trend()` - **AFFECTED**
- `_get_metric_trend()` helper - **FIX HERE**
- Other weekly aggregations that might be added later

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-22 | Fix at dashboard service level | Source of the problem, cleanest fix |
| 2025-12-22 | Use ISO format strings | Standard, sortable, compatible |
