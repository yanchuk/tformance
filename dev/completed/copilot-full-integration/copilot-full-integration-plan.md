# Copilot Full Integration - Implementation Plan

## Overview

Integrate all available GitHub Copilot data to help CTOs make informed decisions about their AI tool investments. Users without Copilot will continue to see existing dashboards unchanged (graceful degradation).

## ICP Decision Framework

**Who:** CTOs / Engineering Leaders paying for Copilot licenses

| Question | Required Data | Dashboard Impact |
|----------|---------------|------------------|
| "Is Copilot worth the $19/seat/month?" | Acceptance rates, PR velocity comparison | ROI metrics |
| "Are we wasting money on unused licenses?" | Seat utilization, inactive users | Cost analytics |
| "Who's actually using it vs who isn't?" | Per-user activity, last login | User engagement |
| "Which languages/editors benefit most?" | Language/editor breakdowns | Tech stack insights |
| "Is Copilot making my team faster?" | Copilot PRs vs non-Copilot cycle times | Delivery impact |

## GitHub Copilot API Endpoints

### 1. Metrics API (`/orgs/{org}/copilot/metrics`)
**Requires 5+ licenses**
- Daily suggestions shown/accepted
- Language breakdown (Python, TypeScript, etc.)
- Editor breakdown (VS Code, JetBrains, etc.)
- Lines suggested/accepted
- Chat metrics (IDE + GitHub.com)
- PR summaries generated

### 2. Billing API (`/orgs/{org}/copilot/billing`)
**No minimum**
- Total seats, active/inactive counts
- Feature policies (chat, CLI, public code)
- Plan type (Business/Enterprise)

### 3. Seats API (`/orgs/{org}/copilot/billing/seats`)
**No minimum**
- Per-user last activity timestamp
- Per-user last editor used
- Seat creation date
- Pending cancellation status

## Feature Flag Strategy

All Copilot features gated by Django Waffle flags:

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `copilot_enabled` | Flag | Off | Master switch for all Copilot UI |
| `copilot_seat_utilization` | Flag | Off | ROI & seat analytics (Epic 1) |
| `copilot_language_insights` | Flag | Off | Language/editor breakdown (Epic 2) |
| `copilot_delivery_impact` | Flag | Off | PR comparison metrics (Epic 3) |
| `copilot_llm_insights` | Flag | Off | Include Copilot in LLM prompts (Epic 4) |

### Flag Hierarchy
```
copilot_enabled (master)
├── copilot_seat_utilization
├── copilot_language_insights
├── copilot_delivery_impact
└── copilot_llm_insights
```

## Implementation Phases

### Phase 1: Feature Flags Foundation (Epic 5)
- Create Waffle flag definitions
- Add flag checking utilities
- Gate Celery tasks with flags
- Add flag status to view contexts

### Phase 2: ROI & Seat Utilization (Epic 1)
- Sync seat utilization data from Billing API
- Create `CopilotSeatSnapshot` model
- Add seat stats cards to CTO Overview
- Add inactive users table
- Calculate wasted spend metrics

### Phase 3: Language & Editor Insights (Epic 2)
- Store language/editor breakdown from Metrics API
- Create `CopilotLanguageDaily`, `CopilotEditorDaily` models
- Add language breakdown chart
- Add editor comparison chart

### Phase 4: Delivery Impact Correlation (Epic 3)
- Enhance PR correlation with Copilot member data
- Add Copilot vs Non-Copilot comparison cards
- Track per-user Copilot activity timestamps

### Phase 5: Enhanced LLM Insights (Epic 4)
- Extend LLM prompt template with seat/ROI data
- Add inactive license warnings
- Identify champions and struggling users
- Generate actionable recommendations

### Phase 6: Graceful Degradation (Epic 6)
- Ensure no UI changes for non-Copilot users
- Add helpful empty states
- Handle partial data scenarios

## Data Model Changes

### New Models

```python
class CopilotSeatSnapshot(BaseTeamModel):
    date = models.DateField()
    total_seats = models.IntegerField()
    active_this_cycle = models.IntegerField()
    inactive_this_cycle = models.IntegerField()
    pending_cancellation = models.IntegerField(default=0)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['team', 'date']


class CopilotLanguageDaily(BaseTeamModel):
    date = models.DateField()
    language = models.CharField(max_length=50)
    suggestions_shown = models.IntegerField()
    suggestions_accepted = models.IntegerField()
    lines_suggested = models.IntegerField()
    lines_accepted = models.IntegerField()

    class Meta:
        unique_together = ['team', 'date', 'language']


class CopilotEditorDaily(BaseTeamModel):
    date = models.DateField()
    editor = models.CharField(max_length=100)
    suggestions_shown = models.IntegerField()
    suggestions_accepted = models.IntegerField()

    class Meta:
        unique_together = ['team', 'date', 'editor']
```

### Model Extensions

```python
# Add to TeamMember model
copilot_last_activity_at = models.DateTimeField(null=True, blank=True)
copilot_last_editor = models.CharField(max_length=100, null=True, blank=True)
```

## Files to Modify

### Feature Flags
- `apps/integrations/services/integration_flags.py` - Add Copilot flag helpers
- `fixtures/waffle_flags.json` - Define default Copilot flags
- `apps/integrations/_task_modules/copilot.py` - Check flags before sync

### Models & Services
- `apps/metrics/models/aggregations.py` - Add new Copilot models
- `apps/teams/models.py` - Add Copilot fields to TeamMember
- `apps/integrations/services/copilot_metrics.py` - Add billing/seats fetch
- `apps/metrics/services/dashboard/copilot_metrics.py` - Dashboard queries

### Views & Templates
- `apps/metrics/views/chart_views.py` - Add Copilot chart endpoints
- `apps/metrics/views/dashboard_views.py` - Pass flag status to context
- `templates/metrics/partials/copilot_*.html` - New cards/charts
- `templates/metrics/cto_overview.html` - Wrap in flag checks

### LLM Integration
- `apps/metrics/prompts/templates/sections/copilot_metrics.jinja2` - Enhance
- `apps/integrations/services/copilot_metrics_prompt.py` - Add seat data
- `apps/metrics/prompts/render.py` - Conditional Copilot context

## Success Metrics

| Metric | Target |
|--------|--------|
| CTOs can identify wasted Copilot spend | 100% of connected orgs |
| Language insights load without errors | <500ms |
| No broken UI for non-Copilot users | 0 regressions |
| LLM insights mention Copilot when relevant | When data exists |

## TDD Approach

Every feature follows strict Red-Green-Refactor:

1. **RED**: Write failing test describing expected behavior
2. **GREEN**: Implement minimum code to pass test
3. **REFACTOR**: Clean up while keeping tests green

Test organization:
- `apps/integrations/tests/test_copilot_*.py` - API/sync tests
- `apps/metrics/tests/test_copilot_*.py` - Dashboard/metrics tests
- Unit tests for services, integration tests for views
