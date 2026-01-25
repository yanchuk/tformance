# DX-Inspired Features Implementation Plan

**Last Updated:** 2025-01-25

## Executive Summary

Implement DX (Developer Experience) research-inspired features to show factual Copilot engagement metrics and team health indicators. This adds value for CTOs without speculative time-to-money calculations.

**Key Principle:** Show factual data CTOs can trust, not speculative estimates.

---

## Current State Analysis

### Existing Data Sources
| Model | Data Available | Location |
|-------|----------------|----------|
| `AIUsageDaily` | Per-member daily Copilot usage | `apps/metrics/models/aggregations.py` |
| `CopilotSeatSnapshot` | Seat counts, utilization, costs | `apps/metrics/models/aggregations.py` |
| `CopilotLanguageDaily` | Per-language acceptance rates | `apps/metrics/models/aggregations.py` |
| `CopilotEditorDaily` | Per-editor usage breakdown | `apps/metrics/models/aggregations.py` |
| `PRSurveyReview` | Quality rating (1-3), AI guess | `apps/metrics/models/surveys.py` |
| `WeeklyMetrics` | Per-member weekly aggregations | `apps/metrics/models/aggregations.py` |

### Existing Services
| Service | Function | Location |
|---------|----------|----------|
| `get_copilot_metrics()` | Summary stats | `services/dashboard/copilot_metrics.py` |
| `get_copilot_trend()` | Weekly acceptance trend | `services/dashboard/copilot_metrics.py` |
| `get_copilot_delivery_comparison()` | Cycle time comparison | `services/dashboard/copilot_metrics.py` |
| `get_team_health_metrics()` | Basic health metrics | `services/dashboard/velocity_metrics.py` |

### Existing Mock Data
- `seed_copilot_demo.py` - Seeds AIUsageDaily, CopilotSeatSnapshot, CopilotLanguageDaily, CopilotEditorDaily
- `CopilotMockDataGenerator` - Scenarios: high_adoption, low_adoption, growth, decline, mixed_usage

---

## Proposed Future State

### P0: Copilot Engagement Dashboard
New service function that aggregates factual Copilot metrics with confidence indicators.

### P0: Cost Visibility Dashboard
Configurable Copilot pricing tiers ($10/$19/$39) with accurate cost calculations.

### P1: Review Experience Survey
Extended PRSurveyReview with feedback_clarity and review_burden fields (25% sampling).

### P2: Team Health Indicators
Traffic light indicators for throughput, cycle time, quality, bottleneck, AI adoption.

---

## Implementation Phases

### Phase 1: P0 - Copilot Engagement Dashboard (Week 1)

**Goal:** Show factual Copilot metrics with statistical confidence.

#### 1.1 Service Layer (TDD)
**File:** `apps/metrics/services/dashboard/copilot_metrics.py`

```python
def get_copilot_engagement_summary(team, start_date, end_date) -> dict:
    """Aggregate factual Copilot engagement metrics.

    Returns:
        dict with keys:
        - suggestions_accepted: int
        - lines_of_code_accepted: int (from CopilotLanguageDaily)
        - acceptance_rate: Decimal
        - active_copilot_users: int
        - cycle_time_with_copilot: Decimal | None
        - cycle_time_without_copilot: Decimal | None
        - review_time_with_copilot: Decimal | None
        - review_time_without_copilot: Decimal | None
        - sample_sufficient: bool (True if both groups >= 10 PRs)
        - acceptance_rate_trend: "up" | "down" | "stable"
    """
```

#### 1.2 View Layer
**File:** `apps/metrics/views/chart_views.py`

```python
def copilot_engagement_card(request):
    """HTMX partial for Copilot engagement metrics."""
```

#### 1.3 Template
**File:** `templates/metrics/partials/copilot_engagement_card.html`

#### 1.4 Tests
**File:** `apps/metrics/tests/services/dashboard/test_copilot_engagement.py`

Edge cases:
- Zero Copilot users (division by zero)
- Mixed adoption (some active, some not)
- Insufficient sample size (<10 PRs per group)
- New team (no historical data)
- Large team (100+ members, query <100ms)

---

### Phase 2: P0 - Cost Visibility Dashboard (Week 1)

**Goal:** Show accurate Copilot costs with configurable pricing.

#### 2.1 Model Change
**File:** `apps/teams/models.py`

```python
class Team(models.Model):
    # ... existing fields ...
    copilot_price_tier = models.CharField(
        max_length=20,
        choices=[
            ("individual", "Individual ($10/mo)"),
            ("business", "Business ($19/mo)"),
            ("enterprise", "Enterprise ($39/mo)"),
        ],
        default="business",
        help_text="Copilot subscription tier for cost calculations"
    )
```

#### 2.2 Migration
Create migration for new `copilot_price_tier` field.

#### 2.3 Update CopilotSeatSnapshot
**File:** `apps/metrics/models/aggregations.py`

```python
def get_copilot_seat_price(team) -> Decimal:
    """Get Copilot seat price based on team's tier setting."""
    tier_prices = {
        "individual": Decimal("10.00"),
        "business": Decimal("19.00"),
        "enterprise": Decimal("39.00"),
    }
    return tier_prices.get(team.copilot_price_tier, Decimal("19.00"))

class CopilotSeatSnapshot(BaseTeamModel):
    @property
    def monthly_cost(self) -> Decimal:
        """Calculate monthly cost based on team's tier."""
        price = get_copilot_seat_price(self.team)
        return (Decimal(self.total_seats) * price).quantize(Decimal("0.01"))
```

#### 2.4 Tests
**File:** `apps/metrics/tests/services/dashboard/test_cost_visibility.py`

Test each tier ($10, $19, $39) calculates correctly.

---

### Phase 3: P1 - Review Experience Survey (Week 2)

**Goal:** Collect reviewer experience data without survey fatigue.

#### 3.1 Model Extension
**File:** `apps/metrics/models/surveys.py`

```python
FEEDBACK_CLARITY_CHOICES = [
    (1, "Unclear"),
    (2, "OK"),
    (3, "Clear"),
    (4, "Very clear"),
    (5, "Excellent"),
]

REVIEW_BURDEN_CHOICES = [
    (1, "Very taxing"),
    (2, "Taxing"),
    (3, "Moderate"),
    (4, "Light"),
    (5, "Very light"),
]

class PRSurveyReview(BaseTeamModel):
    # ... existing fields ...

    feedback_clarity = models.IntegerField(
        choices=FEEDBACK_CLARITY_CHOICES,
        null=True,
        blank=True,
        help_text="How clear was the review feedback?"
    )
    review_burden = models.IntegerField(
        choices=REVIEW_BURDEN_CHOICES,
        null=True,
        blank=True,
        help_text="How mentally demanding was this review?"
    )
```

#### 3.2 Sampling Logic
Only show extended questions 25% of the time to avoid fatigue.

```python
import random

def should_show_extended_survey() -> bool:
    """25% chance to show extended survey questions."""
    return random.random() < 0.25
```

#### 3.3 Update Survey Handlers
- `apps/integrations/services/slack/survey_handler.py`
- `apps/metrics/views/survey_views.py`
- GitHub comment survey template

#### 3.4 Tests
- Model field tests
- Sampling distribution test (run 1000x, expect ~25%)
- Survey submission with new fields

---

### Phase 4: P2 - Team Health Indicators (Week 3)

**Goal:** Show individual health signals with traffic light status.

#### 4.1 Service Function
**File:** `apps/metrics/services/dashboard/velocity_metrics.py`

```python
def get_team_health_indicators(team, start_date, end_date) -> dict:
    """Calculate team health indicators with traffic light status.

    Returns:
        dict with keys:
        - throughput: {value, trend, status}
        - cycle_time: {value, trend, status}
        - quality: {value, trend, status}
        - review_bottleneck: {detected, reviewer, status}
        - ai_adoption: {value, trend, status}
    """
```

#### 4.2 Traffic Light Logic
```python
def _calculate_status(value, thresholds) -> str:
    """Map value to green/yellow/red status."""
    if value >= thresholds["green"]:
        return "green"
    elif value >= thresholds["yellow"]:
        return "yellow"
    return "red"
```

#### 4.3 Template
**File:** `templates/metrics/partials/team_health_indicators.html`

Use DaisyUI badges for traffic lights:
- `badge-success` (green)
- `badge-warning` (yellow)
- `badge-error` (red)

---

## Mock Data Updates

### Update seed_copilot_demo.py
Ensure mock data supports all new features:

1. **Lines of code accepted** - Already in CopilotLanguageDaily.lines_accepted
2. **Acceptance rate trends** - Already supported via scenarios
3. **Sample sufficiency** - Ensure enough PRs per group

### New Factory Support
Add factory helpers for testing:

```python
# apps/metrics/factories.py
class CopilotSeatSnapshotFactory(DjangoModelFactory):
    class Meta:
        model = CopilotSeatSnapshot

    team = factory.SubFactory(TeamFactory)
    date = factory.LazyFunction(lambda: date.today())
    total_seats = factory.LazyFunction(lambda: random.randint(5, 20))
    active_this_cycle = factory.LazyAttribute(lambda o: int(o.total_seats * 0.7))
    inactive_this_cycle = factory.LazyAttribute(lambda o: o.total_seats - o.active_this_cycle)
```

---

## E2E Testing with Playwright

### New Test File
**File:** `tests/e2e/dx-features.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { loginAs } from './fixtures/test-users';

test.describe('DX Features @dx', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Copilot Engagement Dashboard', () => {
    test('shows factual engagement metrics', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      // Verify suggestions_accepted is numeric
      // Verify acceptance_rate is percentage
      // Verify sample_sufficient indicator exists
    });

    test('shows confidence indicator when sample insufficient', async ({ page }) => {
      // Test with small sample size
    });
  });

  test.describe('Cost Visibility Dashboard', () => {
    test('shows monthly cost based on tier', async ({ page }) => {
      // Verify cost calculation
    });

    test('tier selector changes cost display', async ({ page }) => {
      // Change tier and verify cost updates
    });
  });

  test.describe('Team Health Indicators', () => {
    test('shows traffic light for each indicator', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      // Verify 5 indicators with status badges
    });

    test('indicators show trend direction', async ({ page }) => {
      // Verify trend arrows (up/down/stable)
    });
  });
});
```

### Update Existing Tests
**File:** `tests/e2e/copilot.spec.ts`

Add tests for:
- Engagement summary card
- Cost visibility with tier selector
- Sample sufficiency warning

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| N+1 queries in engagement summary | Performance | Use `aggregate()` and `annotate()` |
| Division by zero | Crash | Handle zero cases explicitly |
| Survey fatigue from new questions | Low response rates | 25% sampling, track rates |
| Migration on production data | Data integrity | Test migration on staging first |

### Business Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| CTOs expect time savings number | Confusion | Clear documentation, factual framing |
| Incorrect tier pricing | Trust loss | Default to Business ($19), make configurable |

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| All tests pass | 100% | `make test` |
| E2E tests pass | 100% | `make e2e` |
| Query performance | <100ms | Django Debug Toolbar |
| Survey response rate | >50% | Track in PRSurveyReview |
| No regressions | 0 | Existing test suite |

---

## Dependencies

### Internal Dependencies
- `apps/metrics/services/dashboard/` - Existing service layer
- `apps/teams/models.py` - Team model for tier setting
- `apps/integrations/services/slack/` - Survey delivery

### External Dependencies
- None (all data already available)

---

## Implementation Checklist

See `dx-features-tasks.md` for detailed task checklist.
