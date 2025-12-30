"""Tests for get_team_velocity function.

Tests for the dashboard service function that returns top contributors
by PR count with average cycle time.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetTeamVelocity(TestCase):
    """Tests for get_team_velocity function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team, display_name="Alice Developer")
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_list_of_dicts(self):
        """Test that get_team_velocity returns list of dicts with required keys."""
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
        )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], dict)

        # Check required keys
        self.assertIn("member_id", result[0])
        self.assertIn("display_name", result[0])
        self.assertIn("avatar_url", result[0])
        self.assertIn("pr_count", result[0])
        self.assertIn("avg_cycle_time", result[0])

    def test_orders_by_pr_count_descending(self):
        """Test that results are ordered by PR count descending."""
        member_low = TeamMemberFactory(team=self.team, display_name="Low Contributor")
        member_high = TeamMemberFactory(team=self.team, display_name="High Contributor")

        # Low contributor: 1 PR
        PullRequestFactory(
            team=self.team,
            author=member_low,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # High contributor: 3 PRs
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=member_high,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["display_name"], "High Contributor")
        self.assertEqual(result[0]["pr_count"], 3)
        self.assertEqual(result[1]["display_name"], "Low Contributor")
        self.assertEqual(result[1]["pr_count"], 1)

    def test_limits_results_to_limit_param(self):
        """Test that limit parameter restricts number of results."""
        # Create 5 members with 1 PR each
        for i in range(5):
            member = TeamMemberFactory(team=self.team, display_name=f"Member {i}")
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date, limit=3)

        self.assertEqual(len(result), 3)

    def test_includes_member_details(self):
        """Test that member_id, display_name, avatar_url are present and correct."""
        member = TeamMemberFactory(
            team=self.team,
            display_name="Test Developer",
            github_id="12345",
        )
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["member_id"], member.id)
        self.assertEqual(result[0]["display_name"], "Test Developer")
        self.assertEqual(result[0]["avatar_url"], "https://avatars.githubusercontent.com/u/12345?s=80")

    def test_calculates_pr_count_correctly(self):
        """Test that pr_count is the correct count of merged PRs per member."""
        # Create 4 PRs for this member
        for _ in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["pr_count"], 4)

    def test_calculates_avg_cycle_time_correctly(self):
        """Test that avg_cycle_time is the average of member's PR cycle times."""
        # Create PRs with specific cycle times: 10, 20, 30 hours -> avg = 20
        cycle_times = [Decimal("10.0"), Decimal("20.0"), Decimal("30.0")]
        for ct in cycle_times:
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
                cycle_time_hours=ct,
            )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["avg_cycle_time"], Decimal("20.0"))

    def test_handles_member_with_no_cycle_time_data(self):
        """Test that avg_cycle_time is None when member has no cycle time data."""
        # Create PR without cycle_time_hours
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            cycle_time_hours=None,
        )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["avg_cycle_time"])

    def test_filters_by_date_range(self):
        """Test that only PRs merged within date range are counted."""
        # In range
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # Before start date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
        )

        # After end date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
        )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["pr_count"], 1)  # Only the in-range PR

    def test_filters_by_team(self):
        """Test that only PRs from specified team are included."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team, display_name="Other Team Dev")

        # Target team PR
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # Other team PR (should be excluded)
        PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["display_name"], "Alice Developer")

    def test_excludes_members_with_no_prs(self):
        """Test that members with 0 merged PRs are not in results."""
        # Create another member with no PRs
        TeamMemberFactory(team=self.team, display_name="No PRs Member")

        # Create 1 PR for the original member
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["display_name"], "Alice Developer")

    def test_handles_empty_period(self):
        """Test that returns empty list when no PRs in range."""
        # Create PR outside the date range
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 6, 15, 12, 0)),
        )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(result, [])

    def test_ties_sorted_by_display_name(self):
        """Test that members with same PR count are sorted alphabetically by display_name."""
        member_zack = TeamMemberFactory(team=self.team, display_name="Zack Developer")
        member_alice = TeamMemberFactory(team=self.team, display_name="Alice Developer")
        member_bob = TeamMemberFactory(team=self.team, display_name="Bob Developer")

        # All three have 2 PRs each
        for member in [member_zack, member_alice, member_bob]:
            for _ in range(2):
                PullRequestFactory(
                    team=self.team,
                    author=member,
                    state="merged",
                    merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
                )

        result = dashboard_service.get_team_velocity(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 3)
        # All have same PR count, should be alphabetical
        self.assertEqual(result[0]["display_name"], "Alice Developer")
        self.assertEqual(result[1]["display_name"], "Bob Developer")
        self.assertEqual(result[2]["display_name"], "Zack Developer")
