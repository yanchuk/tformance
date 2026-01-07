"""
Tests for Copilot metrics service used in LLM prompt context.

This module tests the service that aggregates Copilot usage data
for inclusion in LLM insight prompts.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.integrations.services.copilot_metrics_prompt import get_copilot_metrics_for_prompt
from apps.metrics.factories import AIUsageDailyFactory, TeamFactory, TeamMemberFactory


class TestGetCopilotMetricsForPrompt(TestCase):
    """Tests for get_copilot_metrics_for_prompt function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(slug="test-team")
        self.members = TeamMemberFactory.create_batch(3, team=self.team)
        self.today = date.today()
        self.start_date = self.today - timedelta(days=7)

    def test_returns_dict_with_expected_keys(self):
        """Test that function returns dictionary with all expected keys."""
        # Arrange - Create some Copilot usage
        for member in self.members:
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
            end_date=self.today,
            include_copilot=True,
        )

        # Assert - Check expected keys
        self.assertIsInstance(result, dict)
        self.assertIn("active_users", result)
        self.assertIn("inactive_count", result)
        self.assertIn("avg_acceptance_rate", result)
        self.assertIn("total_suggestions", result)
        self.assertIn("total_acceptances", result)

    def test_returns_empty_dict_when_no_data(self):
        """Test that function returns empty dict when no Copilot data exists."""
        # Act - No data created
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.today,
            include_copilot=True,
        )

        # Assert
        self.assertEqual(result, {})

    def test_calculates_active_users_correctly(self):
        """Test that active users count is correct."""
        # Arrange - Only 2 of 3 members have Copilot usage
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[0],
            date=self.today,
            source="copilot",
            suggestions_shown=100,
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[1],
            date=self.today,
            source="copilot",
            suggestions_shown=50,
        )
        # members[2] has no usage

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.today,
            include_copilot=True,
        )

        # Assert
        self.assertEqual(result["active_users"], 2)

    def test_calculates_inactive_count(self):
        """Test that inactive users (with licenses but no usage) are counted."""
        # Arrange - Create usage with 0 suggestions (inactive)
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[0],
            date=self.today,
            source="copilot",
            suggestions_shown=100,  # Active
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[1],
            date=self.today,
            source="copilot",
            suggestions_shown=0,  # Inactive - has license but no usage
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.today,
            include_copilot=True,
        )

        # Assert
        self.assertEqual(result["inactive_count"], 1)

    def test_calculates_avg_acceptance_rate(self):
        """Test that average acceptance rate is calculated correctly."""
        # Arrange
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[0],
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
            acceptance_rate=Decimal("40.00"),
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[1],
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=60,
            acceptance_rate=Decimal("60.00"),
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.today,
            include_copilot=True,
        )

        # Assert - Average of 40% and 60% = 50%
        self.assertAlmostEqual(float(result["avg_acceptance_rate"]), 50.0, places=1)

    def test_includes_top_users(self):
        """Test that top users by usage are included."""
        # Arrange - Create usage with varying amounts
        member1 = TeamMemberFactory(team=self.team, display_name="Power User")
        member2 = TeamMemberFactory(team=self.team, display_name="Casual User")

        AIUsageDailyFactory(
            team=self.team,
            member=member1,
            date=self.today,
            source="copilot",
            suggestions_shown=500,  # High usage
        )
        AIUsageDailyFactory(
            team=self.team,
            member=member2,
            date=self.today,
            source="copilot",
            suggestions_shown=50,  # Low usage
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.today,
            include_copilot=True,
        )

        # Assert - top_users should be a list
        self.assertIn("top_users", result)
        self.assertIsInstance(result["top_users"], list)
        # Power User should be first
        if len(result["top_users"]) > 0:
            self.assertEqual(result["top_users"][0]["name"], "Power User")

    def test_only_includes_copilot_source(self):
        """Test that only Copilot data is included (not Cursor)."""
        # Arrange
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[0],
            date=self.today,
            source="copilot",
            suggestions_shown=100,
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[1],
            date=self.today,
            source="cursor",  # Should be excluded
            suggestions_shown=200,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.today,
            include_copilot=True,
        )

        # Assert
        self.assertEqual(result["active_users"], 1)
        self.assertEqual(result["total_suggestions"], 100)

    def test_respects_date_range(self):
        """Test that only data within date range is included."""
        # Arrange - Create usage inside and outside date range
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[0],
            date=self.today,  # Within range
            source="copilot",
            suggestions_shown=100,
        )
        AIUsageDailyFactory(
            team=self.team,
            member=self.members[0],
            date=self.today - timedelta(days=30),  # Outside range
            source="copilot",
            suggestions_shown=500,
        )

        # Act
        result = get_copilot_metrics_for_prompt(
            team=self.team,
            start_date=self.start_date,
            end_date=self.today,
            include_copilot=True,
        )

        # Assert - Only today's 100 suggestions should be counted
        self.assertEqual(result["total_suggestions"], 100)
