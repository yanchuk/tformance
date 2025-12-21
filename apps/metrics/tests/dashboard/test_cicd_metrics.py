"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRCheckRunFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetCicdPassRate(TestCase):
    """Tests for get_cicd_pass_rate function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_cicd_pass_rate_returns_dict(self):
        """Test that get_cicd_pass_rate returns a dict with required keys."""
        result = dashboard_service.get_cicd_pass_rate(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("total_runs", result)
        self.assertIn("pass_rate", result)
        self.assertIn("success_count", result)
        self.assertIn("failure_count", result)
        self.assertIn("top_failing_checks", result)

    def test_get_cicd_pass_rate_calculates_correctly(self):
        """Test that get_cicd_pass_rate calculates pass rate correctly."""
        member = TeamMemberFactory(team=self.team)
        pr = PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        # Create 4 successful and 1 failed check run
        for _ in range(4):
            PRCheckRunFactory(team=self.team, pull_request=pr, status="completed", conclusion="success")
        PRCheckRunFactory(team=self.team, pull_request=pr, status="completed", conclusion="failure")

        result = dashboard_service.get_cicd_pass_rate(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_runs"], 5)
        self.assertEqual(result["success_count"], 4)
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(result["pass_rate"], Decimal("80.00"))

    def test_get_cicd_pass_rate_returns_zero_when_no_data(self):
        """Test that get_cicd_pass_rate returns zero values when no data exists."""
        result = dashboard_service.get_cicd_pass_rate(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_runs"], 0)
        self.assertEqual(result["pass_rate"], Decimal("0.00"))

    def test_get_cicd_pass_rate_excludes_in_progress_checks(self):
        """Test that get_cicd_pass_rate excludes in-progress checks."""
        member = TeamMemberFactory(team=self.team)
        pr = PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        # 2 completed, 1 in progress
        PRCheckRunFactory(team=self.team, pull_request=pr, status="completed", conclusion="success")
        PRCheckRunFactory(team=self.team, pull_request=pr, status="completed", conclusion="failure")
        PRCheckRunFactory(team=self.team, pull_request=pr, status="in_progress", conclusion=None)

        result = dashboard_service.get_cicd_pass_rate(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_runs"], 2)  # Only completed checks counted

    def test_get_cicd_pass_rate_tracks_top_failing_checks(self):
        """Test that get_cicd_pass_rate identifies top failing checks."""
        member = TeamMemberFactory(team=self.team)
        pr = PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        # Create multiple failures for different checks
        for _ in range(3):
            PRCheckRunFactory(team=self.team, pull_request=pr, name="pytest", status="completed", conclusion="failure")
        for _ in range(2):
            PRCheckRunFactory(team=self.team, pull_request=pr, name="eslint", status="completed", conclusion="failure")

        result = dashboard_service.get_cicd_pass_rate(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result["top_failing_checks"]), 2)
        # pytest should be first with more failures
        self.assertEqual(result["top_failing_checks"][0]["name"], "pytest")
        self.assertEqual(result["top_failing_checks"][0]["failures"], 3)

    def test_get_cicd_pass_rate_filters_by_team(self):
        """Test that get_cicd_pass_rate only includes data from the specified team."""
        member = TeamMemberFactory(team=self.team)
        pr = PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRCheckRunFactory(team=self.team, pull_request=pr, status="completed", conclusion="success")

        # Create check run for other team
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        other_pr = PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRCheckRunFactory(team=other_team, pull_request=other_pr, status="completed", conclusion="failure")

        result = dashboard_service.get_cicd_pass_rate(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_runs"], 1)
        self.assertEqual(result["pass_rate"], Decimal("100.00"))
