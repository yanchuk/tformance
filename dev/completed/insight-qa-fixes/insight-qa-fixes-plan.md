# Insight QA Fixes - Implementation Plan

**Last Updated:** 2026-01-02

## Executive Summary

This plan addresses 4 open issues discovered during LLM insight QA testing. All fixes follow strict TDD (Red-Green-Refactor) methodology and are prioritized by severity.

| Issue | Priority | Component | Effort |
|-------|----------|-----------|--------|
| ISS-005 | High | Onboarding Team Context | S |
| ISS-006 | High | Sparkline AI Data Source | M |
| ISS-001 | Medium | Sparkline Low-Data Handling | M |
| ISS-007 | Medium | (Same fix as ISS-001) | - |

**Total Estimated Effort:** 3-4 TDD cycles

---

## Current State Analysis

### ISS-005: Onboarding sync_progress shows wrong team

**Location:** `apps/onboarding/views.py:479`

**Current Code:**
```python
@login_required
def sync_progress(request):
    """Show sync progress page with Celery progress tracking."""
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()  # BUG: Ignores session team
```

**Problem:** When user navigates to Analytics while viewing a team via `?team=` parameter, they get redirected to onboarding but see their FIRST team, not the team they were viewing.

**Existing Tests:** `apps/onboarding/tests/test_views.py:183` - `SyncProgressViewTests` exists but doesn't test multi-team scenarios.

---

### ISS-006: AI Adoption sparkline uses different data source than card

**Location:** `apps/metrics/services/dashboard_service.py`

**Current Code:**
```python
# Card (get_key_metrics) - uses survey data
surveys = PRSurvey.objects.filter(pull_request__in=prs)
ai_assisted_pct = _calculate_ai_percentage(surveys)

# Sparkline (get_sparkline_data) - uses pattern detection
ai_count=Count("id", filter=Q(is_ai_assisted=True))
```

**Problem:** Card shows 33% (survey-based), sparkline shows 0% (pattern-based). Different data sources cause user confusion.

**Existing Tests:** `apps/metrics/tests/dashboard/test_sparkline_data.py` - Tests exist but use `is_ai_assisted` field (pattern detection).

---

### ISS-001 & ISS-007: Sparkline trend misleading during low-data periods

**Location:** `apps/metrics/services/dashboard_service.py:2123`

**Current Code:**
```python
def _calculate_change_and_trend(values: list) -> tuple[int, str]:
    """Calculate change percentage and trend direction from values list."""
    if len(values) < 2:
        return 0, "flat"

    first_val = values[0]
    last_val = values[-1]
    # ... simple point-to-point comparison
```

**Problem:**
- First week with 1-2 PRs creates unrealistic baseline
- Holiday weeks with minimal activity skew trends
- Results in +44321% or -98% that don't reflect reality

**Existing Tests:** Tests exist for basic trend calculation but not for low-data edge cases.

---

## Proposed Future State

### ISS-005 Fix
```python
@login_required
def sync_progress(request):
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    # Use session team if available, fallback to first team
    team = getattr(request, 'team', None) or getattr(request, 'default_team', None)
    if not team:
        team = request.user.teams.first()
```

### ISS-006 Fix

Update sparkline to use survey data instead of pattern detection:
```python
# Get weekly AI adoption percentages from surveys (matches get_key_metrics)
ai_adoption_data = (
    prs.annotate(week=TruncWeek("merged_at"))
    .values("week")
    .annotate(
        total_with_survey=Count("survey", filter=Q(survey__isnull=False)),
        ai_count=Count("survey", filter=Q(survey__author_ai_assisted=True)),
    )
    .order_by("week")
)
```

### ISS-001/ISS-007 Fix

Add minimum sample size requirement and weighted comparison:
```python
def _calculate_change_and_trend(
    values: list,
    sample_sizes: list | None = None,
    min_sample_size: int = 3
) -> tuple[int, str]:
    """Calculate change percentage with sample size consideration."""
    if len(values) < 2:
        return 0, "flat"

    # Find first week with sufficient data
    first_idx = 0
    if sample_sizes:
        for i, size in enumerate(sample_sizes):
            if size >= min_sample_size:
                first_idx = i
                break
        else:
            return 0, "flat"  # No week has enough data

    # Find last week with sufficient data
    last_idx = len(values) - 1
    if sample_sizes:
        for i in range(len(sample_sizes) - 1, -1, -1):
            if sample_sizes[i] >= min_sample_size:
                last_idx = i
                break

    first_val = values[first_idx]
    last_val = values[last_idx]
    # ... rest of calculation
```

---

## Implementation Phases

### Phase 1: ISS-005 - Onboarding Team Context (TDD)

**Effort:** Small (S)

#### RED Phase - Write Failing Tests

1. **Test: sync_progress uses session team when available**
   - Create user with 2 teams
   - Set `request.team` via session/middleware
   - Assert view shows the session team, not first team

2. **Test: sync_progress falls back to first team when no session team**
   - Create user with team but no session team set
   - Assert view shows first team (backward compatibility)

3. **Test: start_sync uses session team**
   - Same pattern for the `start_sync` API endpoint

#### GREEN Phase - Minimal Implementation

- Update `sync_progress` to use `request.team or request.default_team or request.user.teams.first()`
- Update `start_sync` similarly

#### REFACTOR Phase

- Extract common team resolution logic to helper function if pattern repeats
- Update docstrings

---

### Phase 2: ISS-006 - AI Adoption Data Source Alignment (TDD)

**Effort:** Medium (M)

#### RED Phase - Write Failing Tests

1. **Test: sparkline AI adoption uses survey data**
   - Create PRs with surveys where `author_ai_assisted=True`
   - Create PRs without surveys or with `author_ai_assisted=False`
   - Assert sparkline values match survey-based calculation

2. **Test: sparkline AI adoption matches get_key_metrics**
   - Create same dataset
   - Call both `get_sparkline_data` and `get_key_metrics`
   - Assert AI adoption percentages are consistent

3. **Test: sparkline handles PRs without surveys**
   - Create PRs without surveys
   - Assert returns 0% (not counted in denominator)

#### GREEN Phase - Minimal Implementation

- Update `get_sparkline_data` to use survey data via subquery or join
- Match logic from `_calculate_ai_percentage`

#### REFACTOR Phase

- Consider extracting common AI percentage calculation
- Ensure efficient query (avoid N+1)
- Update docstrings to clarify data source

---

### Phase 3: ISS-001/ISS-007 - Low-Data Week Handling (TDD)

**Effort:** Medium (M)

#### RED Phase - Write Failing Tests

1. **Test: trend ignores weeks with insufficient data as baseline**
   - Create week 1 with 1 PR (below threshold)
   - Create week 2 with 10 PRs
   - Assert first_val uses week 2, not week 1

2. **Test: trend ignores weeks with insufficient data as endpoint**
   - Create week 1 with 10 PRs
   - Create week 2 with 1 PR (below threshold)
   - Assert last_val uses week 1, not week 2

3. **Test: returns flat when no week has sufficient data**
   - Create multiple weeks with 1-2 PRs each
   - Assert returns (0, "flat")

4. **Test: sample_sizes parameter passed correctly**
   - Verify integration with `get_sparkline_data`

5. **Test: configurable minimum sample size**
   - Test with different `min_sample_size` values

#### GREEN Phase - Minimal Implementation

- Add `sample_sizes` parameter to `_calculate_change_and_trend`
- Add `min_sample_size` parameter with default of 3
- Update `get_sparkline_data` to pass sample sizes
- Skip weeks below threshold when finding first/last values

#### REFACTOR Phase

- Consider making threshold configurable per metric
- Add constant `MIN_SPARKLINE_SAMPLE_SIZE = 3`
- Update function signatures and docstrings

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing sparkline tests | Medium | Medium | Run full test suite after each change |
| Survey data missing for historical PRs | Low | Low | Gracefully handle missing surveys |
| Performance impact from survey joins | Low | Medium | Use efficient subqueries, add indexes if needed |
| Regression in onboarding flow | Low | High | Manual E2E test after ISS-005 fix |

---

## Success Metrics

1. **All 4 issues resolved** - Verified via manual QA on affected teams
2. **No test regressions** - Full test suite passes
3. **Consistent UX** - Card and sparkline show same data source
4. **Meaningful trends** - No extreme percentages (>1000%) from low-data weeks

---

## Dependencies

- Existing test fixtures in `apps/metrics/factories.py`
- `PRSurveyFactory` for creating survey test data
- Understanding of `request.team` middleware behavior

---

## Files to Modify

| File | Changes |
|------|---------|
| `apps/onboarding/views.py` | Update `sync_progress` and `start_sync` team resolution |
| `apps/onboarding/tests/test_views.py` | Add multi-team tests for `sync_progress` |
| `apps/metrics/services/dashboard_service.py` | Update sparkline AI adoption, add sample size handling |
| `apps/metrics/tests/dashboard/test_sparkline_data.py` | Add tests for survey-based AI, low-data handling |
