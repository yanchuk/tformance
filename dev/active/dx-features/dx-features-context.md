# DX Features - Key Context

**Last Updated:** 2025-01-25

## Critical Files

### Models to Modify

| File | Changes |
|------|---------|
| `apps/teams/models.py` | Add `copilot_price_tier` field |
| `apps/metrics/models/aggregations.py` | Update `CopilotSeatSnapshot.monthly_cost` property |
| `apps/metrics/models/surveys.py` | Add `feedback_clarity`, `review_burden` to PRSurveyReview |

### Services to Create/Modify

| File | Function | Priority |
|------|----------|----------|
| `apps/metrics/services/dashboard/copilot_metrics.py` | `get_copilot_engagement_summary()` | P0 |
| `apps/metrics/services/dashboard/velocity_metrics.py` | `get_team_health_indicators()` | P2 |
| `apps/metrics/services/dashboard/__init__.py` | Export new functions | P0 |

### Views to Create

| File | View | Priority |
|------|------|----------|
| `apps/metrics/views/chart_views.py` | `copilot_engagement_card()` | P0 |
| `apps/metrics/views/chart_views.py` | `team_health_indicators_card()` | P2 |

### Templates to Create

| File | Purpose | Priority |
|------|---------|----------|
| `templates/metrics/partials/copilot_engagement_card.html` | Engagement metrics | P0 |
| `templates/metrics/partials/team_health_indicators.html` | Traffic light indicators | P2 |

### Tests to Create

| File | Covers | Priority |
|------|--------|----------|
| `apps/metrics/tests/services/dashboard/test_copilot_engagement.py` | P0 engagement | P0 |
| `apps/metrics/tests/services/dashboard/test_cost_visibility.py` | P0 cost tiers | P0 |
| `apps/metrics/tests/test_prsurvey_review_extension.py` | P1 survey fields | P1 |
| `apps/metrics/tests/services/dashboard/test_team_health_indicators.py` | P2 indicators | P2 |
| `tests/e2e/dx-features.spec.ts` | E2E all features | All |

### Mock Data to Update

| File | Changes |
|------|---------|
| `apps/metrics/management/commands/seed_copilot_demo.py` | Ensure lines_accepted populated |
| `apps/metrics/factories.py` | Add `CopilotSeatSnapshotFactory` |

---

## Key Decisions

### Decision 1: Factual Over Speculative
**Context:** Original plan had `time_saved = suggestions * 0.5min` which has no research backing.

**Decision:** Show raw data only:
- Suggestions accepted (factual)
- Lines of code accepted (factual)
- Cycle time comparison (factual with confidence indicator)

**Rationale:** CTOs can draw their own conclusions. Speculative calculations undermine credibility.

### Decision 2: Configurable Pricing
**Context:** Hardcoded `$19/seat` only applies to Copilot Business.

**Decision:** Add `copilot_price_tier` field with options:
- Individual: $10
- Business: $19 (default)
- Enterprise: $39

**Rationale:** Accurate cost calculations require knowing the tier.

### Decision 3: Traffic Lights Over Composite Score
**Context:** Composite health score (0.3+0.3+0.2+0.2) hides problems.

**Decision:** Show 5 individual indicators with green/yellow/red status:
- Throughput
- Cycle time
- Quality (revert rate)
- Review bottleneck
- AI adoption

**Rationale:** More actionable - CTOs see exactly what needs attention.

### Decision 4: Survey Sampling
**Context:** Adding 2 more questions increases survey fatigue.

**Decision:** Show extended questions only 25% of the time.

**Rationale:** Balance data collection with response rate preservation.

---

## Data Dependencies

### For Copilot Engagement Summary

```python
# Required models
from apps.metrics.models import AIUsageDaily, CopilotLanguageDaily, PullRequest
from apps.metrics.models import TeamMember

# Key fields
AIUsageDaily.suggestions_accepted  # Per-member daily
CopilotLanguageDaily.lines_accepted  # Per-language daily
TeamMember.has_recent_copilot_activity  # Property (30-day window)
PullRequest.cycle_time_hours  # For comparison
```

### For Cost Visibility

```python
# Required models
from apps.metrics.models import CopilotSeatSnapshot
from apps.teams.models import Team

# Key fields
Team.copilot_price_tier  # NEW FIELD
CopilotSeatSnapshot.total_seats
CopilotSeatSnapshot.active_this_cycle
CopilotSeatSnapshot.inactive_this_cycle
```

### For Team Health Indicators

```python
# Required models
from apps.metrics.models import PullRequest, WeeklyMetrics

# Key calculations
# Throughput: PRs merged per week
# Cycle time: Average hours from open to merge
# Quality: Revert rate percentage
# Bottleneck: Reviewer with most open reviews
# AI adoption: % of PRs with is_ai_assisted=True
```

---

## API Contracts

### get_copilot_engagement_summary()

```python
def get_copilot_engagement_summary(
    team: Team,
    start_date: date,
    end_date: date
) -> dict:
    """
    Returns:
        {
            "suggestions_accepted": int,
            "lines_of_code_accepted": int,
            "acceptance_rate": Decimal,  # 0-100
            "active_copilot_users": int,
            "cycle_time_with_copilot": Decimal | None,  # hours
            "cycle_time_without_copilot": Decimal | None,  # hours
            "review_time_with_copilot": Decimal | None,  # hours
            "review_time_without_copilot": Decimal | None,  # hours
            "sample_sufficient": bool,
            "acceptance_rate_trend": str,  # "up" | "down" | "stable"
        }
    """
```

### get_team_health_indicators()

```python
def get_team_health_indicators(
    team: Team,
    start_date: date,
    end_date: date
) -> dict:
    """
    Returns:
        {
            "throughput": {
                "value": float,  # PRs per week
                "trend": str,  # "up" | "down" | "stable"
                "status": str,  # "green" | "yellow" | "red"
            },
            "cycle_time": {
                "value": float,  # hours
                "trend": str,
                "status": str,
            },
            "quality": {
                "value": float,  # revert rate %
                "trend": str,
                "status": str,
            },
            "review_bottleneck": {
                "detected": bool,
                "reviewer": str | None,
                "status": str,  # "green" | "red"
            },
            "ai_adoption": {
                "value": float,  # adoption %
                "trend": str,
                "status": str,
            },
        }
    """
```

---

## Testing Patterns

### Service Test Pattern

```python
from django.test import TestCase
from apps.metrics.factories import TeamFactory, TeamMemberFactory, AIUsageDailyFactory

class TestCopilotEngagementSummary(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.members = TeamMemberFactory.create_batch(3, team=cls.team)

    def test_returns_expected_keys(self):
        # Arrange
        # Act
        result = get_copilot_engagement_summary(
            self.team, start_date, end_date
        )
        # Assert
        self.assertIn("suggestions_accepted", result)
        self.assertIn("sample_sufficient", result)
```

### E2E Test Pattern

```typescript
test('shows engagement metrics card', async ({ page }) => {
  await page.goto('/app/metrics/overview/');
  await page.waitForLoadState('domcontentloaded');

  // Wait for HTMX
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout: 5000 }
  );

  // Verify card exists
  const card = page.locator('[data-testid="copilot-engagement"]');
  await expect(card).toBeVisible();

  // Verify numeric values
  const suggestions = card.locator('[data-metric="suggestions-accepted"]');
  const text = await suggestions.textContent();
  expect(text).toMatch(/^\d+$/);
});
```

---

## Playwright Verification

### Required Checks
1. **P0 Engagement:** Navigate to `/app/metrics/overview/`, verify engagement card renders
2. **P0 Cost:** Verify cost display, change tier, verify update
3. **P1 Survey:** Submit survey, verify new fields saved
4. **P2 Health:** Verify 5 indicators with traffic lights

### Test Commands

```bash
# Run specific E2E test
npx playwright test dx-features.spec.ts

# Run with UI
npx playwright test dx-features.spec.ts --ui

# Run with debug
npx playwright test dx-features.spec.ts --debug
```

---

## URL Routes

### Existing Routes to Use

```python
# apps/metrics/urls.py
path("chart/copilot-metrics/", copilot_metrics_card, name="copilot_metrics_card"),
path("chart/copilot-trend/", copilot_trend_chart, name="copilot_trend_chart"),
```

### New Routes to Add

```python
# apps/metrics/urls.py
path("chart/copilot-engagement/", copilot_engagement_card, name="copilot_engagement_card"),
path("chart/team-health-indicators/", team_health_indicators_card, name="team_health_indicators_card"),
```

---

## Constants

### Copilot Pricing

```python
COPILOT_TIER_PRICES = {
    "individual": Decimal("10.00"),
    "business": Decimal("19.00"),
    "enterprise": Decimal("39.00"),
}
```

### Health Indicator Thresholds

```python
HEALTH_THRESHOLDS = {
    "throughput": {
        "green": 5,    # >= 5 PRs/week
        "yellow": 3,   # >= 3 PRs/week
    },
    "cycle_time": {
        "green": 24,   # <= 24 hours
        "yellow": 72,  # <= 72 hours
    },
    "quality": {
        "green": 2,    # <= 2% revert rate
        "yellow": 5,   # <= 5% revert rate
    },
    "ai_adoption": {
        "green": 30,   # >= 30% adoption
        "yellow": 10,  # >= 10% adoption
    },
}
```

---

## Migration Notes

### P0: Team.copilot_price_tier

```bash
.venv/bin/python manage.py makemigrations teams --name add_copilot_price_tier
.venv/bin/python manage.py migrate
```

### P1: PRSurveyReview Extensions

```bash
.venv/bin/python manage.py makemigrations metrics --name add_review_experience_fields
.venv/bin/python manage.py migrate
```

**Note:** All existing records will have NULL for new fields. Handle gracefully in templates.
