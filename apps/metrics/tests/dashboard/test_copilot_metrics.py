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


class TestCopilotTrendsFunctions(TestCase):
    """Tests for Copilot acceptance trend functions for Trends tab.

    These functions provide monthly and weekly aggregations of Copilot acceptance
    rates for display in the Trends tab with YoY comparison support.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")

    def test_get_monthly_copilot_acceptance_trend_returns_monthly_data(self):
        """Monthly trend aggregates daily data into months."""
        from apps.metrics.factories import AIUsageDailyFactory

        # January data: 2000 shown, 800 accepted = 40%
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2025, 1, 10),
            source="copilot",
            suggestions_shown=1000,
            suggestions_accepted=400,
            acceptance_rate=Decimal("40.00"),
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2025, 1, 20),
            source="copilot",
            suggestions_shown=1000,
            suggestions_accepted=400,
            acceptance_rate=Decimal("40.00"),
        )

        # February data: 1500 shown, 450 accepted = 30%
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2025, 2, 15),
            source="copilot",
            suggestions_shown=1500,
            suggestions_accepted=450,
            acceptance_rate=Decimal("30.00"),
        )

        result = dashboard_service.get_monthly_copilot_acceptance_trend(self.team, date(2025, 1, 1), date(2025, 2, 28))

        # Should return 2 months
        self.assertEqual(len(result), 2)

        # Check format: {month: "YYYY-MM", value: float}
        self.assertIn("month", result[0])
        self.assertIn("value", result[0])

        # January: 40%
        self.assertEqual(result[0]["month"], "2025-01")
        self.assertAlmostEqual(result[0]["value"], 40.0, places=1)

        # February: 30%
        self.assertEqual(result[1]["month"], "2025-02")
        self.assertAlmostEqual(result[1]["value"], 30.0, places=1)

    def test_get_monthly_copilot_acceptance_trend_empty_data_returns_empty_list(self):
        """No data returns empty list, not error."""
        result = dashboard_service.get_monthly_copilot_acceptance_trend(self.team, date(2025, 1, 1), date(2025, 12, 31))

        self.assertEqual(result, [])

    def test_get_monthly_copilot_acceptance_trend_calculates_rate_correctly(self):
        """Acceptance rate = (accepted / shown) * 100."""
        from apps.metrics.factories import AIUsageDailyFactory

        # 2500 shown, 750 accepted = 30%
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2025, 3, 15),
            source="copilot",
            suggestions_shown=2500,
            suggestions_accepted=750,
            acceptance_rate=Decimal("30.00"),
        )

        result = dashboard_service.get_monthly_copilot_acceptance_trend(self.team, date(2025, 3, 1), date(2025, 3, 31))

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["value"], 30.0, places=1)

    def test_get_monthly_copilot_acceptance_trend_zero_suggestions_returns_zero(self):
        """Month with 0 suggestions returns 0.0 (no division error)."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Edge case: 0 suggestions shown
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2025, 4, 10),
            source="copilot",
            suggestions_shown=0,
            suggestions_accepted=0,
            acceptance_rate=Decimal("0.00"),
        )

        result = dashboard_service.get_monthly_copilot_acceptance_trend(self.team, date(2025, 4, 1), date(2025, 4, 30))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["value"], 0.0)

    def test_get_monthly_copilot_acceptance_trend_aggregates_multiple_members(self):
        """Data from multiple members aggregates into single month value."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Alice: 1000 shown, 400 accepted (40%)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2025, 5, 10),
            source="copilot",
            suggestions_shown=1000,
            suggestions_accepted=400,
            acceptance_rate=Decimal("40.00"),
        )

        # Bob: 1000 shown, 200 accepted (20%)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member2,
            date=date(2025, 5, 15),
            source="copilot",
            suggestions_shown=1000,
            suggestions_accepted=200,
            acceptance_rate=Decimal("20.00"),
        )

        # Combined: 2000 shown, 600 accepted = 30%
        result = dashboard_service.get_monthly_copilot_acceptance_trend(self.team, date(2025, 5, 1), date(2025, 5, 31))

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["value"], 30.0, places=1)

    def test_get_monthly_copilot_acceptance_trend_excludes_cursor_source(self):
        """Only 'copilot' source included, 'cursor' excluded."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Copilot data: 1000 shown, 400 accepted = 40%
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2025, 6, 10),
            source="copilot",
            suggestions_shown=1000,
            suggestions_accepted=400,
            acceptance_rate=Decimal("40.00"),
        )

        # Cursor data (should be excluded)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2025, 6, 15),
            source="cursor",
            suggestions_shown=5000,
            suggestions_accepted=4000,
            acceptance_rate=Decimal("80.00"),
        )

        result = dashboard_service.get_monthly_copilot_acceptance_trend(self.team, date(2025, 6, 1), date(2025, 6, 30))

        # Should only include Copilot data
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["value"], 40.0, places=1)

    def test_get_weekly_copilot_acceptance_trend_returns_trends_format(self):
        """Weekly wrapper returns {week: "YYYY-MM-DD", value: float} format."""
        from apps.metrics.factories import AIUsageDailyFactory

        # Week starting 2025-01-06 (Monday)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member1,
            date=date(2025, 1, 8),  # Wednesday of week 2
            source="copilot",
            suggestions_shown=1000,
            suggestions_accepted=350,
            acceptance_rate=Decimal("35.00"),
        )

        result = dashboard_service.get_weekly_copilot_acceptance_trend(self.team, date(2025, 1, 1), date(2025, 1, 14))

        self.assertEqual(len(result), 1)

        # Check format matches Trends tab expectations
        self.assertIn("week", result[0])
        self.assertIn("value", result[0])

        # Week should be ISO format string YYYY-MM-DD
        self.assertIsInstance(result[0]["week"], str)
        self.assertRegex(result[0]["week"], r"^\d{4}-\d{2}-\d{2}$")

        # Value should be float percentage
        self.assertIsInstance(result[0]["value"], float)
        self.assertAlmostEqual(result[0]["value"], 35.0, places=1)
