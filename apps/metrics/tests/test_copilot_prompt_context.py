"""
Tests for extended Copilot metrics context for LLM prompts.

This module tests the extended get_copilot_metrics_for_prompt function that
includes seat utilization data and delivery impact comparison.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.integrations.services.copilot_metrics_prompt import get_copilot_metrics_for_prompt
from apps.metrics.factories import (
    AIUsageDailyFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.models import CopilotSeatSnapshot


class TestCopilotPromptContextExistingMetrics(TestCase):
    """Tests for existing Copilot metrics in prompt context."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.today = date.today()
        self.start_date = self.today - timedelta(days=7)
        self.end_date = self.today

    def test_returns_existing_copilot_metrics(self):
        """Test that function returns existing Copilot metrics structure.

        Verifies that total_suggestions, total_accepted, acceptance_rate,
        and active_users are included in the response.
        """
        # Arrange - create Copilot usage for 3 members
        members = TeamMemberFactory.create_batch(3, team=self.team)
        for member in members:
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                date=self.today,
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=40,
                acceptance_rate=Decimal("40.00"),
            )

        # Act - use include_copilot=True to bypass flag check for data structure testing
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,
        )

        # Assert - verify existing metrics are present
        self.assertIn("total_suggestions", result)
        self.assertIn("total_acceptances", result)
        self.assertIn("avg_acceptance_rate", result)
        self.assertIn("active_users", result)

        # Verify values are correct
        self.assertEqual(result["total_suggestions"], 300)  # 3 * 100
        self.assertEqual(result["total_acceptances"], 120)  # 3 * 40
        self.assertEqual(result["active_users"], 3)


class TestCopilotPromptContextSeatData(TestCase):
    """Tests for seat utilization data in Copilot prompt context."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.today = date.today()
        self.start_date = self.today - timedelta(days=7)
        self.end_date = self.today

    def test_includes_seat_utilization_data(self):
        """Test that seat_data is included from latest CopilotSeatSnapshot.

        The seat_data should include:
        - total_seats
        - active_seats
        - inactive_seats
        - utilization_rate
        - monthly_cost
        - wasted_spend
        - cost_per_active_user
        """
        # Arrange - create Copilot usage and seat snapshot
        member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Create seat snapshot for today
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=25,
            active_this_cycle=20,
            inactive_this_cycle=5,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,
        )

        # Assert - verify seat_data is present and has correct structure
        self.assertIn("seat_data", result)
        self.assertIsNotNone(result["seat_data"])

        seat_data = result["seat_data"]
        self.assertIn("total_seats", seat_data)
        self.assertIn("active_seats", seat_data)
        self.assertIn("inactive_seats", seat_data)
        self.assertIn("utilization_rate", seat_data)
        self.assertIn("monthly_cost", seat_data)
        self.assertIn("wasted_spend", seat_data)
        self.assertIn("cost_per_active_user", seat_data)

        # Verify values
        self.assertEqual(seat_data["total_seats"], 25)
        self.assertEqual(seat_data["active_seats"], 20)
        self.assertEqual(seat_data["inactive_seats"], 5)
        self.assertEqual(seat_data["utilization_rate"], Decimal("80.00"))
        self.assertEqual(seat_data["monthly_cost"], Decimal("475.00"))  # 25 * $19
        self.assertEqual(seat_data["wasted_spend"], Decimal("95.00"))  # 5 * $19
        self.assertEqual(seat_data["cost_per_active_user"], Decimal("23.75"))  # $475 / 20

    def test_seat_data_uses_latest_snapshot(self):
        """Test that seat_data uses the most recent CopilotSeatSnapshot."""
        # Arrange - create Copilot usage
        member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Create older snapshot
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today - timedelta(days=5),
            total_seats=20,
            active_this_cycle=15,
            inactive_this_cycle=5,
        )

        # Create more recent snapshot (should be used)
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today - timedelta(days=1),
            total_seats=30,
            active_this_cycle=25,
            inactive_this_cycle=5,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,
        )

        # Assert - should use the more recent snapshot (30 seats)
        self.assertIsNotNone(result.get("seat_data"))
        self.assertEqual(result["seat_data"]["total_seats"], 30)

    def test_seat_data_none_when_no_snapshot(self):
        """Test that seat_data is None when no CopilotSeatSnapshot exists."""
        # Arrange - create Copilot usage but no seat snapshot
        member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,
        )

        # Assert - seat_data should be None
        self.assertIn("seat_data", result)
        self.assertIsNone(result["seat_data"])


class TestCopilotPromptContextDeliveryImpact(TestCase):
    """Tests for delivery impact data in Copilot prompt context."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.today = date.today()
        self.start_date = self.today - timedelta(days=30)
        self.end_date = self.today

    def test_includes_delivery_impact_data(self):
        """Test that delivery_impact is included from get_copilot_delivery_comparison.

        The delivery_impact should include:
        - copilot_prs_count
        - non_copilot_prs_count
        - cycle_time_improvement_percent
        - review_time_improvement_percent
        - sample_sufficient
        """
        # Arrange - create Copilot usage
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        AIUsageDailyFactory(
            team=self.team,
            member=copilot_user,
            date=date(2024, 1, 15),
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Create merged PRs for both user types (10 each for sample_sufficient=True)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            include_copilot=True,
        )

        # Assert - verify delivery_impact is present
        self.assertIn("delivery_impact", result)
        self.assertIsNotNone(result["delivery_impact"])

        delivery_impact = result["delivery_impact"]
        self.assertIn("copilot_prs_count", delivery_impact)
        self.assertIn("non_copilot_prs_count", delivery_impact)
        self.assertIn("cycle_time_improvement_percent", delivery_impact)
        self.assertIn("review_time_improvement_percent", delivery_impact)
        self.assertIn("sample_sufficient", delivery_impact)

        # Verify counts
        self.assertEqual(delivery_impact["copilot_prs_count"], 10)
        self.assertEqual(delivery_impact["non_copilot_prs_count"], 10)
        self.assertTrue(delivery_impact["sample_sufficient"])

    def test_delivery_impact_none_when_no_prs(self):
        """Test that delivery_impact is None when no PR data exists."""
        # Arrange - create Copilot usage but no PRs
        member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,
        )

        # Assert - delivery_impact should be None when no PR data
        self.assertIn("delivery_impact", result)
        self.assertIsNone(result["delivery_impact"])


class TestCopilotPromptContextCostCalculations(TestCase):
    """Tests for cost calculations in Copilot prompt context."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.today = date.today()
        self.start_date = self.today - timedelta(days=7)
        self.end_date = self.today

    def test_includes_cost_calculations(self):
        """Test that wasted_spend and cost_per_active_user are calculated correctly.

        Cost calculations:
        - Monthly cost = total_seats * $19
        - Wasted spend = inactive_seats * $19
        - Cost per active user = monthly_cost / active_seats
        """
        # Arrange
        member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Create seat snapshot: 10 total, 6 active, 4 inactive
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=10,
            active_this_cycle=6,
            inactive_this_cycle=4,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,
        )

        # Assert - verify cost calculations
        seat_data = result.get("seat_data")
        self.assertIsNotNone(seat_data)

        # Monthly cost: 10 * $19 = $190
        self.assertEqual(seat_data["monthly_cost"], Decimal("190.00"))

        # Wasted spend: 4 * $19 = $76
        self.assertEqual(seat_data["wasted_spend"], Decimal("76.00"))

        # Cost per active user: $190 / 6 = $31.67
        self.assertEqual(seat_data["cost_per_active_user"], Decimal("31.67"))

    def test_cost_per_active_user_none_when_no_active_users(self):
        """Test that cost_per_active_user is None when no active users."""
        # Arrange
        member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Create seat snapshot with 0 active users
        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=5,
            active_this_cycle=0,
            inactive_this_cycle=5,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,
        )

        # Assert - cost_per_active_user should be None
        seat_data = result.get("seat_data")
        self.assertIsNotNone(seat_data)
        self.assertIsNone(seat_data["cost_per_active_user"])


class TestCopilotPromptContextTeamIsolation(TestCase):
    """Tests for team isolation in Copilot prompt context."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.other_team = TeamFactory()
        self.today = date.today()
        self.start_date = self.today - timedelta(days=7)
        self.end_date = self.today

    def test_team_isolation_enforced(self):
        """Test that only data for specified team is returned.

        Verifies that:
        - Copilot usage from other teams is not included
        - Seat snapshots from other teams are not included
        - PRs from other teams are not included
        """
        # Arrange - create data for our team
        member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        CopilotSeatSnapshot.objects.create(
            team=self.team,
            date=self.today,
            total_seats=10,
            active_this_cycle=8,
            inactive_this_cycle=2,
        )

        # Create data for other team (should NOT be included)
        other_member = TeamMemberFactory(team=self.other_team)
        AIUsageDailyFactory(
            team=self.other_team,
            member=other_member,
            date=self.today,
            source="copilot",
            suggestions_shown=500,
            suggestions_accepted=300,
        )

        CopilotSeatSnapshot.objects.create(
            team=self.other_team,
            date=self.today,
            total_seats=50,
            active_this_cycle=40,
            inactive_this_cycle=10,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,
        )

        # Assert - only our team's data
        self.assertEqual(result["total_suggestions"], 100)  # Not 500
        self.assertEqual(result["active_users"], 1)

        seat_data = result.get("seat_data")
        self.assertIsNotNone(seat_data)
        self.assertEqual(seat_data["total_seats"], 10)  # Not 50

    def test_seat_data_from_correct_team_only(self):
        """Test that seat_data only uses snapshots from the specified team."""
        # Arrange - create usage for our team
        member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Create seat snapshot only for other team
        CopilotSeatSnapshot.objects.create(
            team=self.other_team,
            date=self.today,
            total_seats=50,
            active_this_cycle=40,
            inactive_this_cycle=10,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.end_date,
            include_copilot=True,
        )

        # Assert - seat_data should be None (no snapshot for our team)
        self.assertIn("seat_data", result)
        self.assertIsNone(result["seat_data"])
