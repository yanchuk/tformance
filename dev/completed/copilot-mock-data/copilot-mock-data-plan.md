# Copilot Mock Data Implementation Plan

**Last Updated**: 2026-01-06

## Executive Summary

Implement a comprehensive mock data generation system for GitHub Copilot metrics to enable development, testing, and demos without requiring 5+ Copilot licenses. Uses real GitHub data (PostHog, Railsware) as foundation with controllable Copilot scenario overlays.

## Problem Statement

- GitHub Copilot Metrics API requires 5+ active licenses (we don't have this)
- Can't battle-test dashboard visualizations, charts, correlations
- Can't test LLM insights generation with Copilot context
- Real-world usage is unpredictable (some users active, some inactive)

## Solution Approach

**Real Data + Copilot Overlay Pattern:**
1. Seed real GitHub PR/commit/member data from public repos
2. Overlay configurable Copilot usage scenarios on top
3. Correlate Copilot usage with PRs for richer insights
4. Test full pipeline: charts → correlations → LLM insights

## Implementation Phases

### Phase 1: Mock Data Generator Core (TDD)
Create `CopilotMockDataGenerator` class that produces exact GitHub API format.

**Deliverables:**
- `apps/integrations/services/copilot_mock_data.py`
- `apps/integrations/tests/test_copilot_mock_data.py`
- API-compatible response format
- Deterministic seeding for reproducibility

### Phase 2: Copilot Scenarios (TDD)
Implement 6 configurable scenarios with user archetypes.

**Scenarios:**
| Scenario | Pattern | Use Case |
|----------|---------|----------|
| `high_adoption` | 70-90% acceptance | Success demo |
| `low_adoption` | 20-35% acceptance | Struggling team |
| `growth` | 30% → 80% over time | Adoption journey |
| `decline` | 70% → 30% over time | Churn detection |
| `mixed_usage` | Varied per user | Realistic production |
| `inactive_licenses` | Some users at 0% | Waste detection |

**User Archetypes:**
| Archetype | Acceptance Rate | Usage Days/Week |
|-----------|-----------------|-----------------|
| `power_user` | 40-55% | 5-7 |
| `casual_user` | 25-40% | 3-5 |
| `reluctant_user` | 10-20% | 1-3 |
| `inactive_license` | 0% | 0 |

### Phase 3: Management Command (TDD)
Create `seed_copilot_demo` command for easy scenario switching.

```bash
python manage.py seed_copilot_demo --team=demo --scenario=growth --weeks=8
python manage.py seed_copilot_demo --team=demo --scenario=inactive_licenses --clear-existing
```

### Phase 4: PR Correlation (TDD)
Link daily Copilot usage to actual PRs for richer insights.

```python
# PRs created on days with Copilot usage get is_ai_assisted=True
# Enables: "AI-assisted PRs have 15% faster review times"
```

### Phase 5: LLM Integration (TDD)
Pass Copilot metrics context to insight prompt templates.

**New prompt section:**
```jinja2
## Copilot Usage Metrics
- Active users: {{ copilot_metrics.active_users }}
- Inactive licenses: {{ copilot_metrics.inactive_count }}
- Team acceptance rate: {{ copilot_metrics.avg_acceptance_rate }}%
```

### Phase 6: Settings Toggle
Add environment variable control for mock mode.

```python
COPILOT_USE_MOCK_DATA = env.bool("COPILOT_USE_MOCK_DATA", default=False)
COPILOT_MOCK_SEED = env.int("COPILOT_MOCK_SEED", default=42)
COPILOT_MOCK_SCENARIO = env.str("COPILOT_MOCK_SCENARIO", default="mixed_usage")
```

## GitHub Copilot API Response Schema

Mock generator must produce this exact format:

```json
{
  "date": "2025-01-06",
  "total_active_users": 15,
  "total_engaged_users": 12,
  "copilot_ide_code_completions": {
    "total_completions": 2500,
    "total_acceptances": 875,
    "total_lines_suggested": 4200,
    "total_lines_accepted": 1470,
    "languages": [
      {"name": "python", "total_completions": 1200, "total_acceptances": 480}
    ],
    "editors": [
      {"name": "vscode", "total_completions": 2000, "total_acceptances": 700}
    ]
  },
  "copilot_ide_chat": {
    "total_chats": 45,
    "total_engaged_users": 8
  },
  "copilot_dotcom_chat": {
    "total_chats": 12
  },
  "copilot_dotcom_pull_requests": {
    "total_prs": 5
  }
}
```

## End-to-End Data Flow

```
Real GitHub Data (PostHog/Railsware)
         ↓
    PRs, Commits, Members
         ↓
┌────────────────────────────────────┐
│   Copilot Scenario Overlay         │
│   (high_adoption, mixed, decline)  │
│   • AIUsageDaily per member/day    │
│   • PR.is_ai_assisted correlation  │
└────────────────────────────────────┘
         ↓
    Dashboard Charts
         ↓
    LLM Insights
         ↓
    Iterate & Tune
```

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| API schema changes | Medium | Schema validation tests |
| Unrealistic data patterns | Low | Multiple scenarios + archetypes |
| Performance with large datasets | Low | Deterministic random, batch creation |
| Mock/real confusion | Medium | Clear logging, demo banner |

## Success Metrics

1. **Schema Compliance**: 100% of mock data passes GitHub API schema validation
2. **Scenario Coverage**: All 6 scenarios produce visually distinct charts
3. **LLM Integration**: Copilot insights appear in generated reports
4. **Reproducibility**: Same seed produces identical data
5. **Iteration Speed**: Scenario switch in < 30 seconds

## Dependencies

- `apps/metrics/seeding/deterministic.py` - DeterministicRandom
- `apps/metrics/factories.py` - AIUsageDailyFactory
- `apps/metrics/seeding/real_project_seeder.py` - Base seeder pattern
- `apps/integrations/services/copilot_metrics.py` - Existing API integration
