"""Tests for Cost Visibility Dashboard feature.

TDD RED Phase: These tests define the expected behavior for:
1. Team.copilot_price_tier field
2. get_copilot_seat_price() helper function
3. CopilotSeatSnapshot cost calculations using team tier pricing

Tests should FAIL initially because:
- copilot_price_tier field doesn't exist on Team
- get_copilot_seat_price() function doesn't exist
- CopilotSeatSnapshot.monthly_cost currently uses hardcoded $19
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import CopilotSeatSnapshot


class TestTeamCopilotPriceTierField(TestCase):
    """Tests for Team.copilot_price_tier field."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()

    def test_team_has_copilot_price_tier_field(self):
        """Test that Team model has copilot_price_tier field."""
        from apps.teams.models import Team

        # The field should exist on the model
        self.assertTrue(hasattr(Team, "copilot_price_tier"))

        # Should be able to access it on an instance
        team = TeamFactory()
        self.assertIsNotNone(team.copilot_price_tier)

    def test_copilot_price_tier_defaults_to_business(self):
        """Test that copilot_price_tier defaults to 'business'."""
        team = TeamFactory()

        self.assertEqual(team.copilot_price_tier, "business")

    def test_copilot_price_tier_accepts_individual(self):
        """Test that copilot_price_tier can be set to 'individual'."""
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Individual Tier Team",
            slug="individual-tier-team",
            copilot_price_tier="individual",
        )

        self.assertEqual(team.copilot_price_tier, "individual")

    def test_copilot_price_tier_accepts_enterprise(self):
        """Test that copilot_price_tier can be set to 'enterprise'."""
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Enterprise Tier Team",
            slug="enterprise-tier-team",
            copilot_price_tier="enterprise",
        )

        self.assertEqual(team.copilot_price_tier, "enterprise")


class TestGetCopilotSeatPrice(TestCase):
    """Tests for get_copilot_seat_price() helper function."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()

    def test_get_copilot_seat_price_individual(self):
        """Test that individual tier returns $10.00."""
        from apps.metrics.models.aggregations import get_copilot_seat_price
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Individual Team",
            slug="individual-team-price",
            copilot_price_tier="individual",
        )

        price = get_copilot_seat_price(team)

        self.assertEqual(price, Decimal("10.00"))

    def test_get_copilot_seat_price_business(self):
        """Test that business tier returns $19.00."""
        from apps.metrics.models.aggregations import get_copilot_seat_price
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Business Team",
            slug="business-team-price",
            copilot_price_tier="business",
        )

        price = get_copilot_seat_price(team)

        self.assertEqual(price, Decimal("19.00"))

    def test_get_copilot_seat_price_enterprise(self):
        """Test that enterprise tier returns $39.00."""
        from apps.metrics.models.aggregations import get_copilot_seat_price
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Enterprise Team",
            slug="enterprise-team-price",
            copilot_price_tier="enterprise",
        )

        price = get_copilot_seat_price(team)

        self.assertEqual(price, Decimal("39.00"))

    def test_get_copilot_seat_price_defaults_to_business(self):
        """Test that invalid/None tier defaults to business price ($19.00)."""
        from apps.metrics.models.aggregations import get_copilot_seat_price

        # Team without explicit tier (should default to business)
        price = get_copilot_seat_price(self.team)

        self.assertEqual(price, Decimal("19.00"))


class TestCopilotSeatSnapshotCostWithTier(TestCase):
    """Tests for CopilotSeatSnapshot cost calculations using team tier pricing."""

    def test_monthly_cost_uses_team_tier_individual(self):
        """Test that monthly_cost uses individual tier price ($10)."""
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Individual Cost Team",
            slug="individual-cost-team",
            copilot_price_tier="individual",
        )

        snapshot = CopilotSeatSnapshot.objects.create(
            team=team,
            date=date.today(),
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        # 10 seats * $10 = $100
        self.assertEqual(snapshot.monthly_cost, Decimal("100.00"))

    def test_monthly_cost_uses_team_tier_business(self):
        """Test that monthly_cost uses business tier price ($19)."""
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Business Cost Team",
            slug="business-cost-team",
            copilot_price_tier="business",
        )

        snapshot = CopilotSeatSnapshot.objects.create(
            team=team,
            date=date.today(),
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        # 10 seats * $19 = $190
        self.assertEqual(snapshot.monthly_cost, Decimal("190.00"))

    def test_monthly_cost_uses_team_tier_enterprise(self):
        """Test that monthly_cost uses enterprise tier price ($39)."""
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Enterprise Cost Team",
            slug="enterprise-cost-team",
            copilot_price_tier="enterprise",
        )

        snapshot = CopilotSeatSnapshot.objects.create(
            team=team,
            date=date.today(),
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        # 10 seats * $39 = $390
        self.assertEqual(snapshot.monthly_cost, Decimal("390.00"))

    def test_wasted_spend_uses_team_tier(self):
        """Test that wasted_spend uses team's tier price."""
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Wasted Spend Team",
            slug="wasted-spend-team",
            copilot_price_tier="enterprise",
        )

        snapshot = CopilotSeatSnapshot.objects.create(
            team=team,
            date=date.today(),
            total_seats=20,
            active_this_cycle=15,
            inactive_this_cycle=5,
        )

        # 5 inactive seats * $39 = $195
        self.assertEqual(snapshot.wasted_spend, Decimal("195.00"))

    def test_cost_per_active_user_uses_team_tier(self):
        """Test that cost_per_active_user uses team's tier price."""
        from apps.teams.models import Team

        team = Team.objects.create(
            name="Cost Per User Team",
            slug="cost-per-user-team",
            copilot_price_tier="individual",
        )

        snapshot = CopilotSeatSnapshot.objects.create(
            team=team,
            date=date.today(),
            total_seats=10,
            active_this_cycle=5,
            inactive_this_cycle=5,
        )

        # monthly_cost = 10 seats * $10 = $100
        # cost_per_active_user = $100 / 5 active = $20.00
        self.assertEqual(snapshot.cost_per_active_user, Decimal("20.00"))
