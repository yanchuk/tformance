"""Tests for get_velocity_comparison function.

Tests for the dashboard service function that compares velocity metrics
between current and previous periods.
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


class TestGetVelocityComparison(TestCase):
    """Tests for get_velocity_comparison function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team, display_name="Alice Developer")
        # Current period: Jan 8-14, 2024 (7 days)
        self.start_date = date(2024, 1, 8)
        self.end_date = date(2024, 1, 14)

    def test_returns_correct_structure(self):
        """Test that get_velocity_comparison returns dict with expected keys."""
        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

        # Check top-level keys (grouped by metric type)
        self.assertIn("throughput", result)
        self.assertIn("cycle_time", result)
        self.assertIn("review_time", result)

        # Check throughput structure
        throughput = result["throughput"]
        self.assertIn("current", throughput)
        self.assertIn("previous", throughput)
        self.assertIn("pct_change", throughput)

        # Check cycle_time structure
        cycle_time = result["cycle_time"]
        self.assertIn("current", cycle_time)
        self.assertIn("previous", cycle_time)
        self.assertIn("pct_change", cycle_time)

        # Check review_time structure
        review_time = result["review_time"]
        self.assertIn("current", review_time)
        self.assertIn("previous", review_time)
        self.assertIn("pct_change", review_time)

    def test_calculates_current_period_metrics(self):
        """Test that current period metrics are calculated correctly."""
        # Create 3 PRs in current period (Jan 8-14)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            cycle_time_hours=Decimal("48.0"),
            review_time_hours=Decimal("8.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 14, 12, 0)),
            cycle_time_hours=Decimal("36.0"),
            review_time_hours=Decimal("6.0"),
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Check throughput
        self.assertEqual(result["throughput"]["current"], 3)

        # Average cycle time: (24 + 48 + 36) / 3 = 36.0
        self.assertEqual(result["cycle_time"]["current"], Decimal("36.0"))

        # Average review time: (4 + 8 + 6) / 3 = 6.0
        self.assertEqual(result["review_time"]["current"], Decimal("6.0"))

    def test_calculates_previous_period_metrics(self):
        """Test that previous period metrics are calculated correctly."""
        # Create 2 PRs in previous period (Jan 1-7)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
            cycle_time_hours=Decimal("20.0"),
            review_time_hours=Decimal("5.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 6, 12, 0)),
            cycle_time_hours=Decimal("40.0"),
            review_time_hours=Decimal("10.0"),
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Check throughput
        self.assertEqual(result["throughput"]["previous"], 2)

        # Average cycle time: (20 + 40) / 2 = 30.0
        self.assertEqual(result["cycle_time"]["previous"], Decimal("30.0"))

        # Average review time: (5 + 10) / 2 = 7.5
        self.assertEqual(result["review_time"]["previous"], Decimal("7.5"))

    def test_calculates_percentage_changes(self):
        """Test that percentage changes are calculated correctly."""
        # Previous period (Jan 1-7): 2 PRs, avg cycle 30h, avg review 5h
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
            cycle_time_hours=Decimal("30.0"),
            review_time_hours=Decimal("5.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            cycle_time_hours=Decimal("30.0"),
            review_time_hours=Decimal("5.0"),
        )

        # Current period (Jan 8-14): 4 PRs, avg cycle 15h, avg review 10h
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                cycle_time_hours=Decimal("15.0"),
                review_time_hours=Decimal("10.0"),
            )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Throughput: (4 - 2) / 2 * 100 = 100% increase
        self.assertAlmostEqual(result["throughput"]["pct_change"], 100.0, places=1)

        # Cycle time: (15 - 30) / 30 * 100 = -50% (negative = improvement)
        self.assertAlmostEqual(result["cycle_time"]["pct_change"], -50.0, places=1)

        # Review time: (10 - 5) / 5 * 100 = 100% (positive = slower)
        self.assertAlmostEqual(result["review_time"]["pct_change"], 100.0, places=1)

    def test_handles_no_prs_in_period(self):
        """Test that returns zeros/None when no PRs in either period."""
        # No PRs created at all
        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Throughput should be 0 for both periods
        self.assertEqual(result["throughput"]["current"], 0)
        self.assertEqual(result["throughput"]["previous"], 0)
        self.assertIsNone(result["throughput"]["pct_change"])

        # Cycle time should be None (no data)
        self.assertIsNone(result["cycle_time"]["current"])
        self.assertIsNone(result["cycle_time"]["previous"])
        self.assertIsNone(result["cycle_time"]["pct_change"])

        # Review time should be None (no data)
        self.assertIsNone(result["review_time"]["current"])
        self.assertIsNone(result["review_time"]["previous"])
        self.assertIsNone(result["review_time"]["pct_change"])

    def test_previous_period_same_length(self):
        """Test that previous period has same length as current period by checking date math."""
        # Create PRs in different periods to verify the function uses correct date ranges

        # For 7-day period Jan 8-14, previous should be Jan 1-7
        # Create a PR on Jan 3 (in previous period)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
            cycle_time_hours=Decimal("10.0"),
            review_time_hours=Decimal("2.0"),
        )

        result_7_days = dashboard_service.get_velocity_comparison(
            self.team,
            date(2024, 1, 8),  # Start
            date(2024, 1, 14),  # End (7 days)
        )
        # PR on Jan 3 should be in previous period
        self.assertEqual(result_7_days["throughput"]["previous"], 1)
        self.assertEqual(result_7_days["throughput"]["current"], 0)

    def test_filters_by_team(self):
        """Test that only PRs from specified team are included."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)

        # Create PR for target team in current period
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )

        # Create PR for other team (should be excluded)
        PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("100.0"),
            review_time_hours=Decimal("50.0"),
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Should only count target team's PR
        self.assertEqual(result["throughput"]["current"], 1)
        self.assertEqual(result["cycle_time"]["current"], Decimal("24.0"))
        self.assertEqual(result["review_time"]["current"], Decimal("4.0"))

    def test_excludes_non_merged_prs(self):
        """Test that open and closed PRs are not counted."""
        # Create merged PR (should be counted)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )

        # Create open PR (should not be counted)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="open",
            pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            merged_at=None,
        )

        # Create closed PR (should not be counted)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="closed",
            pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            merged_at=None,
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Should only count the merged PR
        self.assertEqual(result["throughput"]["current"], 1)
