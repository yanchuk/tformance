"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.metrics.factories import (
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestCopilotDashboardService(TestCase):
    """Tests for Copilot metrics dashboard service functions."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_copilot_metrics_returns_correct_totals(self):
        """Test that get_copilot_metrics returns correct total suggestions, accepted, rate, and active users."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Create Copilot usage data for member1
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 10),
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
            acceptance_rate=Decimal("40.00"),
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 15),
            source="copilot",
            suggestions_shown=200,
            suggestions_accepted=80,
            acceptance_rate=Decimal("40.00"),
        )

        # Create Copilot usage data for member2
        AIUsageDailyFactory(
            team=self.team,
            member=self.member2,
            date=date(2024, 1, 20),
            source="copilot",
            suggestions_shown=150,
            suggestions_accepted=60,
            acceptance_rate=Decimal("40.00"),
        )

        # Create Cursor usage data (should be excluded)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 12),
            source="cursor",
            suggestions_shown=500,
            suggestions_accepted=250,
            acceptance_rate=Decimal("50.00"),
        )

        result = dashboard_service.get_copilot_metrics(self.team, self.start_date, self.end_date)

        # Total suggestions: 100 + 200 + 150 = 450
        self.assertEqual(result["total_suggestions"], 450)
        # Total accepted: 40 + 80 + 60 = 180
        self.assertEqual(result["total_accepted"], 180)
        # Acceptance rate: 180 / 450 * 100 = 40.00%
        self.assertEqual(result["acceptance_rate"], Decimal("40.00"))
        # Active users: 2 (Alice and Bob)
        self.assertEqual(result["active_users"], 2)

    def test_get_copilot_metrics_returns_zero_with_no_data(self):
        """Test that get_copilot_metrics returns zero values when there is no Copilot usage data."""
        result = dashboard_service.get_copilot_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_suggestions"], 0)
        self.assertEqual(result["total_accepted"], 0)
        self.assertEqual(result["acceptance_rate"], Decimal("0.00"))
        self.assertEqual(result["active_users"], 0)

    def test_get_copilot_trend_returns_weekly_data(self):
        """Test that get_copilot_trend returns weekly acceptance rate trend."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Week 1 (Jan 1-7): 50% acceptance rate
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 3),
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=50,
            acceptance_rate=Decimal("50.00"),
        )

        # Week 2 (Jan 8-14): 40% acceptance rate
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 10),
            source="copilot",
            suggestions_shown=200,
            suggestions_accepted=80,
            acceptance_rate=Decimal("40.00"),
        )

        # Week 3 (Jan 15-21): 60% acceptance rate
        AIUsageDailyFactory(
            team=self.team,
            member=self.member2,
            date=date(2024, 1, 17),
            source="copilot",
            suggestions_shown=150,
            suggestions_accepted=90,
            acceptance_rate=Decimal("60.00"),
        )

        result = dashboard_service.get_copilot_trend(self.team, self.start_date, self.end_date)

        # Should return 3 weeks of data
        self.assertEqual(len(result), 3)

        # First week should have 50% acceptance
        self.assertIn("week", result[0])
        self.assertIn("acceptance_rate", result[0])
        self.assertEqual(result[0]["acceptance_rate"], Decimal("50.00"))

        # Second week should have 40% acceptance
        self.assertEqual(result[1]["acceptance_rate"], Decimal("40.00"))

        # Third week should have 60% acceptance
        self.assertEqual(result[2]["acceptance_rate"], Decimal("60.00"))

    def test_get_copilot_by_member_returns_per_member_stats(self):
        """Test that get_copilot_by_member returns per-member breakdown of Copilot usage."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Alice: 300 shown, 120 accepted (40%)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 10),
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
            acceptance_rate=Decimal("40.00"),
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2024, 1, 15),
            source="copilot",
            suggestions_shown=200,
            suggestions_accepted=80,
            acceptance_rate=Decimal("40.00"),
        )

        # Bob: 150 shown, 90 accepted (60%)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member2,
            date=date(2024, 1, 20),
            source="copilot",
            suggestions_shown=150,
            suggestions_accepted=90,
            acceptance_rate=Decimal("60.00"),
        )

        result = dashboard_service.get_copilot_by_member(self.team, self.start_date, self.end_date)

        # Should return 2 members
        self.assertEqual(len(result), 2)

        # Find Alice's data
        alice_data = next((m for m in result if m["member_name"] == "Alice"), None)
        self.assertIsNotNone(alice_data)
        self.assertEqual(alice_data["suggestions"], 300)
        self.assertEqual(alice_data["accepted"], 120)
        self.assertEqual(alice_data["acceptance_rate"], Decimal("40.00"))

        # Find Bob's data
        bob_data = next((m for m in result if m["member_name"] == "Bob"), None)
        self.assertIsNotNone(bob_data)
        self.assertEqual(bob_data["suggestions"], 150)
        self.assertEqual(bob_data["accepted"], 90)
        self.assertEqual(bob_data["acceptance_rate"], Decimal("60.00"))
