# Copilot Champions Feature

Last Updated: 2026-01-11

## Executive Summary

Identify "Copilot Champions" - team members who effectively use Copilot, ship fast, and maintain quality. These power users can mentor/train struggling teammates, addressing the CTO question: *"Who should train others on Copilot?"*

## Problem Statement

CTOs want to know:
1. Who is getting the most value from Copilot?
2. Who can help train others?
3. Is our Copilot investment paying off at the individual level?

## Current State Analysis

**Data Available:**
- `AIUsageDaily` - Per-user daily Copilot metrics (suggestions, acceptance rate)
- `PullRequest` - Per-author PR metrics (cycle time, is_revert flag)
- `TeamMember` - Links Copilot usage to PR performance

**Existing Patterns:**
- `get_copilot_metrics_for_prompt()` - Already aggregates user-level data
- `get_copilot_by_member()` in dashboard_service.py - Similar aggregation pattern
- `WeeklyMetrics` - Pre-aggregated weekly data (consider extending)

## Proposed Solution

### Scoring Algorithm (Revised per Review)

**Team-Relative Percentile Scoring:**
```python
# Instead of fixed thresholds, use percentiles within the team
copilot_percentile = percentileofscore(team_acceptance_rates, member_rate)
delivery_percentile = 100 - percentileofscore(team_cycle_times, member_time)
quality_percentile = 100 - percentileofscore(team_revert_rates, member_rate)

# Weighted average
overall = (
    copilot_percentile * 0.40 +
    delivery_percentile * 0.35 +
    quality_percentile * 0.25
)
```

**Qualification Thresholds:**
- Minimum 5 days active in period (Copilot usage)
- Minimum 3 PRs merged
- Minimum 20% acceptance rate (excludes inactive users)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  copilot_champions.py                       │
│  get_copilot_champions(team, start_date, end_date, top_n)  │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ AIUsageDaily  │ │ PullRequest   │ │ TeamMember    │
│ .for_team     │ │ .for_team     │ │ (display_name)│
└───────────────┘ └───────────────┘ └───────────────┘
```

## Implementation Phases

### Phase 1: Service Layer (TDD)

**New file:** `apps/metrics/services/copilot_champions.py`

**Functions:**
1. `get_copilot_usage_by_member()` - Aggregate AIUsageDaily per member
2. `get_pr_metrics_by_member()` - Aggregate PullRequest per author
3. `calculate_champion_scores()` - Combine and score
4. `get_copilot_champions()` - Main entry point, returns top N

**Critical fixes from review:**
- Calculate `revert_rate` from `is_revert` boolean aggregation
- Use `.for_team` manager for TEAM001 compliance
- Join paths: AIUsageDaily.member → TeamMember ← PullRequest.author

### Phase 2: LLM Integration

**Modify:** `apps/integrations/services/copilot_metrics_prompt.py`
- Add `champions` field to output dict
- Include only if feature flag enabled

**Modify:** `apps/metrics/prompts/templates/sections/copilot_metrics.jinja2`
- Add champions section
- Requires PROMPT_VERSION bump

**Modify:** `apps/metrics/services/insight_llm.py`
- Add guidance for mentioning champions as mentors
- Only when team has both champions AND struggling users

### Phase 3: Dashboard UI

**Modify:** `templates/metrics/analytics/ai_adoption.html`
- Add Champions card with top 3

**Modify:** `apps/metrics/views/analytics_views.py`
- Pass champions to template context
- Check feature flag before including

### Phase 4: Feature Flag & Rollout

**Add feature flag:** `copilot_champions`
- Admin-only initially
- Gradual rollout to all teams

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scoring produces unexpected results | Medium | Medium | Feature flag, A/B test |
| Performance on large teams | Medium | High | Use pre-aggregated data, caching |
| Privacy concerns (public shaming) | Medium | High | Admin-only visibility initially |
| Gaming metrics | Low | Medium | Monitor for sudden changes |
| Prompt changes break LLM | Low | Medium | Version bump, promptfoo tests |

## Success Metrics

1. **Adoption:** X% of teams view Champions card
2. **Accuracy:** Champions have >40% acceptance rate (validation)
3. **Impact:** Mentioned in >30% of Copilot-related insights
4. **Performance:** Query <500ms for 95th percentile

## Dependencies

- Existing `AIUsageDaily` data (seeded via seed_copilot_demo)
- Existing `PullRequest` data with `cycle_time_hours`
- Feature flag system (Django Waffle)

## Files to Create/Modify

| File | Action | Effort |
|------|--------|--------|
| `apps/metrics/services/copilot_champions.py` | CREATE | M |
| `apps/metrics/tests/test_copilot_champions.py` | CREATE | M |
| `apps/integrations/services/copilot_metrics_prompt.py` | MODIFY | S |
| `apps/metrics/prompts/templates/sections/copilot_metrics.jinja2` | MODIFY | S |
| `apps/metrics/services/insight_llm.py` | MODIFY | S |
| `templates/metrics/analytics/ai_adoption.html` | MODIFY | S |
| `apps/metrics/views/analytics_views.py` | MODIFY | S |
