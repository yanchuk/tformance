"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
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


class TestGetIterationMetrics(TestCase):
    """Tests for get_iteration_metrics function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_iteration_metrics_returns_dict_with_required_keys(self):
        """Test that get_iteration_metrics returns a dict with all required keys."""
        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        self.assertIn("avg_review_rounds", result)
        self.assertIn("avg_fix_response_hours", result)
        self.assertIn("avg_commits_after_first_review", result)
        self.assertIn("avg_total_comments", result)
        self.assertIn("prs_with_metrics", result)

    def test_get_iteration_metrics_calculates_averages(self):
        """Test that get_iteration_metrics calculates averages correctly."""
        # Create PRs with iteration metrics
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=2,
            avg_fix_response_hours=Decimal("4.00"),
            commits_after_first_review=3,
            total_comments=10,
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            review_rounds=4,
            avg_fix_response_hours=Decimal("8.00"),
            commits_after_first_review=5,
            total_comments=20,
        )

        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        # Averages: review_rounds=(2+4)/2=3, fix_response=(4+8)/2=6, commits=(3+5)/2=4, comments=(10+20)/2=15
        self.assertEqual(result["avg_review_rounds"], Decimal("3.00"))
        self.assertEqual(result["avg_fix_response_hours"], Decimal("6.00"))
        self.assertEqual(result["avg_commits_after_first_review"], Decimal("4.00"))
        self.assertEqual(result["avg_total_comments"], Decimal("15.00"))
        self.assertEqual(result["prs_with_metrics"], 2)

    def test_get_iteration_metrics_handles_no_data(self):
        """Test that get_iteration_metrics handles empty dataset gracefully."""
        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        self.assertIsNone(result["avg_review_rounds"])
        self.assertIsNone(result["avg_fix_response_hours"])
        self.assertIsNone(result["avg_commits_after_first_review"])
        self.assertIsNone(result["avg_total_comments"])
        self.assertEqual(result["prs_with_metrics"], 0)

    def test_get_iteration_metrics_handles_null_values(self):
        """Test that get_iteration_metrics handles PRs with null iteration metrics."""
        # PR with metrics
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=2,
            avg_fix_response_hours=Decimal("4.00"),
            commits_after_first_review=3,
            total_comments=10,
        )
        # PR without metrics (nulls)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            review_rounds=None,
            avg_fix_response_hours=None,
            commits_after_first_review=None,
            total_comments=None,
        )

        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        # Should only count PRs with non-null values
        self.assertEqual(result["avg_review_rounds"], Decimal("2.00"))
        self.assertEqual(result["prs_with_metrics"], 1)

    def test_get_iteration_metrics_filters_by_team(self):
        """Test that get_iteration_metrics only includes data from the specified team."""
        other_team = TeamFactory()

        # Create PR for target team
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=2,
        )

        # Create PR for other team (should be excluded)
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=10,
        )

        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["avg_review_rounds"], Decimal("2.00"))

    def test_get_iteration_metrics_filters_by_date_range(self):
        """Test that get_iteration_metrics only includes PRs within date range."""
        # PR in range
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=2,
        )

        # PR out of range
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
            review_rounds=10,
        )

        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["avg_review_rounds"], Decimal("2.00"))
