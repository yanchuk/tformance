# Copilot Acceptance in Trends Tab - Implementation Plan

**Last Updated:** 2026-01-11

## Executive Summary

Add **Copilot Acceptance Rate** as a selectable metric in the Trends tab, enabling CTOs to track Copilot adoption trends over 12 months with weekly/monthly granularity and Year-over-Year comparison.

**Business Value:** CTOs paying $19-39/user/month for Copilot need visibility into whether adoption is improving over time. This feature answers: "Is my team getting better at using Copilot?"

---

## Current State Analysis

### What Exists

| Component | Status | Location |
|-----------|--------|----------|
| `AIUsageDaily` model | ✅ Ready | `apps/metrics/models/aggregations.py` |
| `get_copilot_trend()` | ✅ Weekly data | `apps/metrics/services/dashboard/copilot_metrics.py` |
| Trends Tab UI | ✅ Ready | `templates/metrics/analytics/trends.html` |
| Multi-metric comparison | ✅ Ready | `wide_trend_chart()` in `trends_views.py` |
| YoY comparison | ✅ Ready | Built into Trends infrastructure |

### What's Missing

| Component | Gap |
|-----------|-----|
| Monthly aggregation | `get_monthly_copilot_acceptance_trend()` function |
| Weekly wrapper | `get_weekly_copilot_acceptance_trend()` with Trends-compatible format |
| METRIC_CONFIG entry | `copilot_acceptance` not in Trends metric selector |
| View integration | Not in `metric_functions` maps |

---

## Proposed Future State

After implementation, the Trends tab will:
1. Show "Copilot Acceptance" as a selectable metric alongside Cycle Time, Review Time, PRs Merged, AI Adoption %
2. Support weekly and monthly granularity toggle
3. Enable YoY comparison for Copilot acceptance rate
4. Allow multi-metric comparison (e.g., Copilot Acceptance vs Cycle Time)

**Visual Result:**
```
[Trends Tab]
┌─────────────────────────────────────────────────────────┐
│ Metrics: [x] Cycle Time [ ] Review Time [ ] PRs Merged  │
│          [ ] AI Adoption [x] Copilot Acceptance         │
│                                                         │
│ Granularity: ( ) Weekly  (•) Monthly                    │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [Chart: Emerald green line for Copilot Acceptance]  │ │
│ │ [Chart: Orange line for Cycle Time]                 │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Service Layer (TDD RED → GREEN)

**Objective:** Add service functions for monthly and weekly Copilot trends.

#### Step 1.1: Write Failing Tests

Create tests in `apps/metrics/tests/dashboard/test_copilot_metrics.py`:

```python
def test_get_monthly_copilot_acceptance_trend_returns_monthly_data(self):
    """Monthly trend aggregates daily data into months."""

def test_get_monthly_copilot_acceptance_trend_empty_data_returns_empty_list(self):
    """No data returns empty list, not error."""

def test_get_monthly_copilot_acceptance_trend_calculates_rate_correctly(self):
    """Acceptance rate = (accepted / shown) * 100."""

def test_get_weekly_copilot_acceptance_trend_returns_trends_format(self):
    """Weekly wrapper returns {week, value} format."""
```

#### Step 1.2: Implement Functions

Add to `apps/metrics/services/dashboard/copilot_metrics.py`:

```python
def get_monthly_copilot_acceptance_trend(
    team: Team, start_date: date, end_date: date, repo: str | None = None
) -> list[dict]:
    """Get Copilot acceptance rate trend by month.

    Returns:
        list of dicts: [{month: "2025-01", value: 45.5}, ...]
    """

def get_weekly_copilot_acceptance_trend(
    team: Team, start_date: date, end_date: date, repo: str | None = None
) -> list[dict]:
    """Weekly Copilot acceptance trend in Trends-compatible format.

    Returns:
        list of dicts: [{week: "2025-01-06", value: 45.5}, ...]
    """
```

#### Step 1.3: Export Functions

Add to `apps/metrics/services/dashboard/__init__.py`:
```python
from .copilot_metrics import (
    get_monthly_copilot_acceptance_trend,
    get_weekly_copilot_acceptance_trend,
)
```

---

### Phase 2: View Layer Integration (TDD RED → GREEN)

**Objective:** Wire up Copilot Acceptance to Trends views.

#### Step 2.1: Write Failing Tests

Create/update `apps/metrics/tests/test_trends_views.py`:

```python
def test_trend_chart_data_accepts_copilot_acceptance_metric(self):
    """trend_chart_data view accepts metric=copilot_acceptance."""

def test_wide_trend_chart_includes_copilot_acceptance_in_available_metrics(self):
    """Copilot Acceptance appears in metric selector."""

def test_copilot_acceptance_uses_correct_color(self):
    """Copilot Acceptance uses emerald green (#10B981)."""
```

#### Step 2.2: Update METRIC_CONFIG

In `apps/metrics/views/trends_views.py`:

```python
METRIC_CONFIG = {
    # ... existing ...
    "copilot_acceptance": {
        "name": "Copilot Acceptance",
        "unit": "%",
        "color": "#10B981",  # emerald green
        "yAxisID": "y2",
    },
}
```

#### Step 2.3: Update Function Maps

Update both `trend_chart_data()` and `wide_trend_chart()` functions.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Color | Emerald green (#10B981) | Distinct from AI Adoption (rose), still in "success" family |
| Y-Axis | Secondary (y2) | Percentage metric like AI Adoption |
| Repo filter | Ignored | Copilot data is org-level, not repo-specific |
| Format | `{month/week, value}` | Matches existing trend functions |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| No Copilot data for team | Medium | Low | Show empty chart with message |
| Performance with large date ranges | Low | Medium | Monthly aggregation reduces data points |
| Color confusion with AI Adoption | Low | Low | Emerald vs rose is visually distinct |

---

## Success Metrics

1. **Functional:** Copilot Acceptance appears in Trends metric selector
2. **Accuracy:** Acceptance rate matches AI Adoption page calculation
3. **Granularity:** Weekly/monthly toggle works correctly
4. **YoY:** Year-over-year comparison renders properly
5. **Multi-metric:** Can compare Copilot Acceptance with other metrics

---

## Files to Modify

| File | Type | Changes |
|------|------|---------|
| `apps/metrics/services/dashboard/copilot_metrics.py` | Service | Add 2 functions |
| `apps/metrics/services/dashboard/__init__.py` | Export | Add 2 exports |
| `apps/metrics/views/trends_views.py` | View | Add METRIC_CONFIG + function maps |
| `apps/metrics/tests/dashboard/test_copilot_metrics.py` | Test | Add 4 tests |
| `apps/metrics/tests/test_trends_views.py` | Test | Add 3 tests |

---

## Verification Plan

### Automated Tests
```bash
# Service tests
.venv/bin/pytest apps/metrics/tests/dashboard/test_copilot_metrics.py -v -k copilot

# View tests
.venv/bin/pytest apps/metrics/tests/test_trends_views.py -v -k copilot
```

### Manual Verification
```bash
make dev
# Navigate to: http://localhost:8000/a/{team}/metrics/analytics/trends/
# 1. Click "Copilot Acceptance" checkbox
# 2. Toggle weekly/monthly granularity
# 3. Select YoY comparison preset
# 4. Compare with another metric (e.g., Cycle Time)
```

### Visual Verification (Playwright)
```python
mcp__playwright__browser_navigate(url="http://localhost:8000/a/tformance/metrics/analytics/trends/")
mcp__playwright__browser_snapshot()
# Click Copilot Acceptance checkbox
# Verify chart renders with emerald green line
```
