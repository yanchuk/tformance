# Insights Engine DateTime Serialization Bug Fix

**Last Updated:** 2025-12-22

## Executive Summary

The insights engine fails to save insights to the database because the `metric_value` JSONField contains `datetime` objects that cannot be serialized to JSON. The bug occurs in the dashboard service functions `get_ai_adoption_trend()` and `get_cycle_time_trend()` which return dictionaries with `datetime` objects in the "week" key.

## Bug Analysis

### Error Message
```
TypeError: Object of type datetime is not JSON serializable
```

### Root Cause

1. **Location**: `apps/metrics/services/dashboard_service.py` lines 163-164
   ```python
   result.append({"week": entry["week"], "value": pct})
   ```

2. **The `entry["week"]`** is a `datetime` object from Django's `TruncWeek("merged_at")`

3. **Data Flow**:
   - `get_ai_adoption_trend()` returns `[{"week": datetime(...), "value": 50.0}, ...]`
   - `AIAdoptionTrendRule._generate_insight()` puts this in `metric_value={"trend": trend_data, ...}`
   - `engine.compute_insights()` tries to save to `DailyInsight.metric_value` (JSONField)
   - PostgreSQL/Django tries to JSON-serialize the datetime → **BOOM**

### Affected Rules
- `AIAdoptionTrendRule` (uses `get_ai_adoption_trend`)
- `CycleTimeTrendRule` (uses `get_cycle_time_trend`)

## Proposed Solution

Convert `datetime` objects to ISO format strings in the dashboard service functions before returning. This is the cleanest fix because:
1. It fixes the issue at the source
2. It's backwards compatible (strings are still sortable/comparable)
3. It doesn't require changes to the insight rules
4. ISO format is standard and easily parseable

### Implementation

In `apps/metrics/services/dashboard_service.py`:

```python
# Before (line 163-164):
result.append({"week": entry["week"], "value": pct})

# After:
week_str = entry["week"].strftime("%Y-%m-%d") if entry["week"] else None
result.append({"week": week_str, "value": pct})
```

Apply same fix to `get_cycle_time_trend()` via `_get_metric_trend()` helper.

## Implementation Phases

### Phase 1: TDD Red Phase
- Write failing tests that verify datetime serialization works
- Test that insights can be saved to database with trend data

### Phase 2: TDD Green Phase
- Fix the datetime serialization in dashboard service
- Ensure all tests pass

### Phase 3: TDD Refactor Phase
- Consider creating a helper function for date formatting
- Verify no other functions have similar issues

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing consumers of trend data | Low | Medium | ISO strings are still comparable, chart.js handles them |
| Missing other datetime fields | Low | Low | Review all JSONField usage |

## Success Metrics

1. All insight rules can save to database without errors
2. Existing tests continue to pass
3. Trend data displays correctly in dashboard charts

## Seeding Instructions

After fix is applied, regenerate insights for demo teams:

```bash
# Generate insights for Gumroad
cat << 'EOF' | .venv/bin/python manage.py shell
from datetime import date
from apps.teams.models import Team
from apps.metrics.insights import engine
from apps.metrics.insights.rules import (
    AIAdoptionTrendRule, CIFailureRateRule, CycleTimeTrendRule,
    HotfixSpikeRule, RedundantReviewerRule, RevertSpikeRule, UnlinkedPRsRule,
)

# Register rules
for rule in [AIAdoptionTrendRule, CycleTimeTrendRule, HotfixSpikeRule,
             RevertSpikeRule, CIFailureRateRule, RedundantReviewerRule, UnlinkedPRsRule]:
    engine.register_rule(rule)

# Generate for Gumroad
team = Team.objects.get(slug="gumroad-demo")
insights = engine.compute_insights(team, date.today())
print(f"Generated {len(insights)} insights for {team.name}")
for insight in insights:
    print(f"  - [{insight.category}] {insight.title}")
EOF
```
