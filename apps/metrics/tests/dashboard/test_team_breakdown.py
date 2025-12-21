"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRSurveyFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetTeamBreakdown(TestCase):
    """Tests for get_team_breakdown function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_team_breakdown_returns_list_of_dicts(self):
        """Test that get_team_breakdown returns a list of member dicts."""
        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_team_breakdown_includes_member_name(self):
        """Test that get_team_breakdown includes member display name."""
        member = TeamMemberFactory(team=self.team, display_name="Alice Smith")
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertGreater(len(result), 0)
        member_data = next((m for m in result if m["member_name"] == "Alice Smith"), None)
        self.assertIsNotNone(member_data)

    def test_get_team_breakdown_counts_prs_merged_per_member(self):
        """Test that get_team_breakdown counts PRs merged per member."""
        member = TeamMemberFactory(team=self.team, display_name="Alice Smith")

        # Create 3 merged PRs for this member
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Alice Smith"), None)
        self.assertEqual(member_data["prs_merged"], 3)

    def test_get_team_breakdown_calculates_avg_cycle_time_per_member(self):
        """Test that get_team_breakdown calculates average cycle time per member."""
        member = TeamMemberFactory(team=self.team, display_name="Bob Jones")

        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("24.00"),
        )
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            cycle_time_hours=Decimal("48.00"),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Bob Jones"), None)
        # Average should be (24 + 48) / 2 = 36
        self.assertEqual(member_data["avg_cycle_time"], Decimal("36.00"))

    def test_get_team_breakdown_calculates_ai_percentage_per_member(self):
        """Test that get_team_breakdown calculates AI-assisted percentage per member."""
        member = TeamMemberFactory(team=self.team, display_name="Charlie Brown")

        # Create 4 PRs: 3 AI-assisted, 1 not
        ai_flags = [True, True, True, False]
        for i, ai_flag in enumerate(ai_flags):
            pr = PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=ai_flag)

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Charlie Brown"), None)
        # 3 out of 4 = 75%
        self.assertAlmostEqual(float(member_data["ai_pct"]), 75.0, places=1)

    def test_get_team_breakdown_includes_multiple_members(self):
        """Test that get_team_breakdown includes all members with activity."""
        member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        member2 = TeamMemberFactory(team=self.team, display_name="Bob")

        PullRequestFactory(
            team=self.team,
            author=member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=member2,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertGreaterEqual(len(result), 2)
        names = [m["member_name"] for m in result]
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)

    def test_get_team_breakdown_excludes_members_with_no_activity(self):
        """Test that get_team_breakdown excludes members with no merged PRs."""
        active_member = TeamMemberFactory(team=self.team, display_name="Active")
        TeamMemberFactory(team=self.team, display_name="Inactive")  # Intentionally unused

        PullRequestFactory(
            team=self.team,
            author=active_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        names = [m["member_name"] for m in result]
        self.assertIn("Active", names)
        self.assertNotIn("Inactive", names)
