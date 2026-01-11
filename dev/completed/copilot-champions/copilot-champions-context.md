# Copilot Champions - Context

Last Updated: 2026-01-11

## Key Files

### Models (Read-Only Reference)

| File | Purpose |
|------|---------|
| `apps/metrics/models/aggregations.py` | AIUsageDaily, WeeklyMetrics models |
| `apps/metrics/models/pull_requests.py` | PullRequest model with cycle_time_hours, is_revert |
| `apps/metrics/models/team.py` | TeamMember model linking users to Copilot data |

### Existing Services (Patterns to Follow)

| File | Pattern |
|------|---------|
| `apps/integrations/services/copilot_metrics_prompt.py` | User aggregation, top_users pattern |
| `apps/metrics/services/dashboard_service.py` | get_copilot_by_member(), team metrics |
| `apps/metrics/services/velocity_metrics.py` | Quality metrics calculation |

### Files to Modify

| File | Change |
|------|--------|
| `apps/metrics/services/copilot_champions.py` | NEW - Main service |
| `apps/metrics/tests/test_copilot_champions.py` | NEW - TDD tests |
| `apps/integrations/services/copilot_metrics_prompt.py` | Add champions to output |
| `apps/metrics/prompts/templates/sections/copilot_metrics.jinja2` | Display champions |
| `apps/metrics/services/insight_llm.py` | Add guidance for champions |
| `templates/metrics/analytics/ai_adoption.html` | Champions UI card |
| `apps/metrics/views/analytics_views.py` | Pass champions to context |

## Key Decisions

1. **Top 3 selection** - Always show exactly 3 champions (consistent, simple)
2. **Balanced scoring** - 40% Copilot, 35% Delivery, 25% Quality
3. **Both UI + Insights** - Show on dashboard AND in LLM insights
4. **Percentile-based scoring** - Relative to team, not fixed thresholds

## Data Model Relationships

```
AIUsageDaily (team, member, date, source='copilot')
    │
    │ member (FK to TeamMember)
    ▼
TeamMember (team, github_username, display_name)
    │
    │ reverse: pull_requests
    ▼
PullRequest (team, author, cycle_time_hours, is_revert)
```

## Critical Implementation Notes

### TEAM001 Compliance
All queries MUST use `.for_team` manager or explicit `team=` filter:
```python
# CORRECT
AIUsageDaily.for_team.filter(source='copilot', ...)
PullRequest.for_team.filter(author=member, state='merged', ...)

# WRONG - will be flagged by linter
AIUsageDaily.objects.filter(date__gte=start)
```

### Revert Rate Calculation
`is_revert` is a boolean on PullRequest, NOT a rate field:
```python
prs = PullRequest.for_team.filter(author=member, state='merged')
total = prs.count()
reverts = prs.filter(is_revert=True).count()
revert_rate = reverts / total if total > 0 else 0
```

### Prompt Version Bump
Per CLAUDE.md, changes to `apps/metrics/prompts/templates/*` require:
1. User approval before making changes
2. Bump `PROMPT_VERSION` in llm_prompts.py
3. Run `make export-prompts && npx promptfoo eval`

## Test Data Available

Demo teams with seeded Copilot data:
- `langchain-demo` - inactive_licenses scenario ($934/contributor waste)
- `grafana-demo` - low_adoption scenario ($247/contributor waste)
- `vercel-demo` - high_adoption scenario ($101/contributor waste)
- `dify-demo` - growth scenario ($40/contributor waste)
- `n8n-demo`, `tooljet-demo`, `appsmith-demo`, `supabase-demo`

## Existing Factories

```python
from apps.metrics.factories import (
    TeamFactory,
    TeamMemberFactory,
    PullRequestFactory,
)
# Note: AIUsageDailyFactory may need to be created
```

## API Response Format

```python
{
    "member_id": 123,
    "display_name": "Alice",
    "github_username": "alice",
    "copilot_score": 85.2,
    "delivery_score": 78.5,
    "quality_score": 95.0,
    "overall_score": 86.2,
    "stats": {
        "acceptance_rate": 52.3,
        "suggestions_accepted": 1245,
        "prs_merged": 18,
        "avg_cycle_time_hours": 24.5,
        "revert_rate": 0.0,
    }
}
```
