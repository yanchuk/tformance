# AI Adoption Data Source Feature Flag - Implementation Plan

**Last Updated:** 2026-01-02
**Status:** Planning
**Priority:** High

---

## Executive Summary

Create a waffle feature flag `rely_on_surveys_for_ai_adoption` to control the data source for AI adoption calculations across the platform. When the flag is **false** (default), the system uses only LLM and regex pattern detection (`effective_is_ai_assisted`). When **true**, it uses survey data (`PRSurvey.author_ai_assisted`) as the primary source.

### Why This Matters

Currently, there's a mismatch between different parts of the application:
- **Dashboard cards/sparklines**: Use survey data (ISS-006 fix)
- **LLM insights**: Use `effective_is_ai_assisted` (after recent fix, now uses surveys)
- **PR filters**: Use `effective_is_ai_assisted`

The user has no survey data yet, so all survey-based metrics show 0% AI adoption, while pattern detection shows higher rates. This flag allows teams to choose their preferred data source based on their data availability.

---

## Current State Analysis

### AI Adoption Calculation Locations

| Function | File | Current Source | Impact |
|----------|------|----------------|--------|
| `get_key_metrics()` | dashboard_service.py:163 | Surveys | Dashboard card |
| `get_ai_adoption_trend()` | dashboard_service.py:222 | Surveys | Trend chart |
| `get_ai_quality_comparison()` | dashboard_service.py:261 | Surveys | AI quality comparison |
| `get_sparkline_data()` | dashboard_service.py:2025 | Surveys | Sparkline values & trends |
| `get_ai_impact_stats()` | dashboard_service.py:2723 | Surveys + fallback | LLM insight generation |
| `get_pr_type_breakdown()` | dashboard_service.py:2232 | `effective_is_ai_assisted` | PR type filters |
| `get_tech_breakdown()` | dashboard_service.py:2291 | `effective_is_ai_assisted` | Tech category filters |
| `get_file_category_breakdown()` | dashboard_service.py:2352 | `effective_is_ai_assisted` | File type filters |
| `get_contributor_breakdown()` | dashboard_service.py:2416 | `effective_is_ai_assisted` | Contributor filters |
| `get_repository_breakdown()` | dashboard_service.py:2478 | `effective_is_ai_assisted` | Repo filters |
| `get_pr_size_breakdown()` | dashboard_service.py:2543 | `effective_is_ai_assisted` | PR size filters |
| `_calculate_ai_percentage()` | dashboard_service.py:84 | Surveys | Helper function |
| `compute_metrics_for_day()` | aggregation_service.py:113 | Surveys | Weekly aggregation |
| `compute_ai_adoption_weekly()` | aggregation_service.py:178 | Surveys | Weekly trend |
| `get_quick_stats_data()` | quick_stats.py:96 | Surveys | Quick stats |
| `get_recent_activity()` | quick_stats.py:143 | Surveys | Recent activity feed |

### Data Sources Explained

1. **Survey Data** (`PRSurvey.author_ai_assisted`)
   - Source: Author responds via Slack/GitHub/Web
   - Values: `True` (used AI), `False` (no AI), `None` (not responded)
   - Pros: Author intent, most accurate when available
   - Cons: Low response rate, many `None` values

2. **Detection Data** (`PullRequest.effective_is_ai_assisted`)
   - Source: LLM analysis + regex pattern matching
   - Priority: LLM detection (confidence ≥0.5) > regex patterns
   - Pros: Always available, no user action needed
   - Cons: May miss AI usage, false positives possible

---

## Proposed Future State

### Feature Flag Design

```python
# Flag name: rely_on_surveys_for_ai_adoption
# Default: False (use detection data only)
# When True: Use survey data with fallback to detection data

def get_ai_adoption_source(team: Team) -> str:
    """Determine AI adoption data source for a team.

    Returns:
        "surveys" if flag is active, "detection" otherwise
    """
    if waffle_flag_is_active("rely_on_surveys_for_ai_adoption", team):
        return "surveys"
    return "detection"
```

### Behavior Matrix

| Flag Value | Survey Available | Survey Value | AI Status Used |
|------------|------------------|--------------|----------------|
| False | Any | Any | `effective_is_ai_assisted` |
| True | Yes | True/False | `author_ai_assisted` |
| True | Yes | None | `effective_is_ai_assisted` (fallback) |
| True | No | N/A | `effective_is_ai_assisted` (fallback) |

---

## Implementation Phases

### Phase 1: Core Infrastructure (S - Small)

**Goal**: Create the feature flag and helper utilities.

1. Create data migration to add the waffle flag
2. Create helper function `should_use_survey_data(team)`
3. Add constants for flag name
4. Write unit tests for helper function

**Acceptance Criteria**:
- [ ] Flag exists in database (default inactive)
- [ ] Helper function correctly checks flag status
- [ ] Tests cover both flag states

### Phase 2: Dashboard Service Refactor (L - Large)

**Goal**: Update all dashboard service functions to use the flag.

**Functions to Update**:
1. `_calculate_ai_percentage()` - Add team parameter, check flag
2. `get_key_metrics()` - Switch based on flag
3. `get_ai_adoption_trend()` - Switch based on flag
4. `get_ai_quality_comparison()` - Switch based on flag
5. `get_sparkline_data()` - Switch based on flag
6. `get_ai_impact_stats()` - Already has fallback, just change default
7. Filter functions (6 total) - Already use detection, no change needed

**Acceptance Criteria**:
- [ ] All functions respect the flag
- [ ] Default behavior (flag=false) uses detection data
- [ ] Flag=true uses survey data with fallback
- [ ] All existing tests pass
- [ ] New tests cover flag behavior

### Phase 3: Aggregation & Quick Stats (M - Medium)

**Goal**: Update aggregation and quick stats services.

1. `compute_metrics_for_day()` - Check flag
2. `compute_ai_adoption_weekly()` - Check flag
3. `get_quick_stats_data()` - Check flag
4. `get_recent_activity()` - Check flag

**Acceptance Criteria**:
- [ ] Aggregation respects flag
- [ ] Quick stats respect flag
- [ ] Cached data invalidated when flag changes

### Phase 4: LLM Insights (S - Small)

**Goal**: Update insight generation to use correct data source.

1. `get_ai_impact_stats()` - Already done, verify behavior
2. `gather_insight_data()` - Ensure consistent with flag

**Acceptance Criteria**:
- [ ] LLM insights use correct AI adoption data
- [ ] Regenerated insights show correct percentages

### Phase 5: Cache Invalidation (S - Small)

**Goal**: Ensure cache is properly invalidated when flag changes.

1. Add flag change detection in admin
2. Clear related caches on flag toggle
3. Document cache dependencies

**Acceptance Criteria**:
- [ ] Cache cleared when flag changes
- [ ] Dashboard shows updated data immediately

### Phase 6: Admin UI & Documentation (S - Small)

**Goal**: Make the flag discoverable and documented.

1. Add flag to Django admin with description
2. Update CLAUDE.md with flag documentation
3. Add inline help text in admin

**Acceptance Criteria**:
- [ ] Flag visible and editable in admin
- [ ] Documentation updated
- [ ] Help text explains behavior

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | Medium | High | Run full test suite after each change |
| Inconsistent data between views | Medium | Medium | Update all functions atomically |
| Performance regression (extra DB queries) | Low | Medium | Cache flag value per request |
| User confusion (different numbers) | Medium | Low | Document behavior, add tooltips |

---

## Success Metrics

1. **Correctness**: All AI adoption metrics match based on flag setting
2. **Consistency**: Dashboard, insights, and filters show same AI status for a PR
3. **Performance**: No measurable latency increase
4. **Test Coverage**: 100% of affected functions have flag-aware tests

---

## Required Resources

- **Django Waffle**: Already installed (`teams.Flag` model)
- **Tests**: TDD approach, write tests first
- **Time Estimate**: 2-3 hours for full implementation

---

## Dependencies

- No external dependencies
- Internal: Requires understanding of `effective_is_ai_assisted` property
- Database: Requires migration for waffle flag creation

---

## Rollout Strategy

1. Deploy with flag defaulting to `false` (current behavior unchanged)
2. Test in development/staging with flag toggled
3. For teams with survey data, optionally enable flag
4. Monitor for any data discrepancies

---

## Open Questions

1. **Per-team vs global**: Should this be a per-team flag or global switch?
   - **Recommendation**: Per-team (using existing `teams.Flag` model)

2. **Cache TTL**: Should we clear all dashboard caches when flag changes?
   - **Recommendation**: Yes, add cache invalidation on flag change

3. **Migration path**: If a team enables surveys later, should we auto-enable the flag?
   - **Recommendation**: No, keep it manual to avoid surprises
