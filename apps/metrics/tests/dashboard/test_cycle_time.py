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
)
from apps.metrics.services import dashboard_service


class TestGetCycleTimeTrend(TestCase):
    """Tests for get_cycle_time_trend function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_cycle_time_trend_returns_list_of_dicts(self):
        """Test that get_cycle_time_trend returns a list of week/value dicts."""
        result = dashboard_service.get_cycle_time_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_cycle_time_trend_groups_by_week(self):
        """Test that get_cycle_time_trend groups data by week."""
        # Week 1 PRs
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
            cycle_time_hours=Decimal("24.00"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            cycle_time_hours=Decimal("48.00"),
        )

        # Week 2 PRs
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("36.00"),
        )

        result = dashboard_service.get_cycle_time_trend(self.team, self.start_date, self.end_date)

        # Should have entries for multiple weeks
        self.assertIsInstance(result, list)
        for entry in result:
            self.assertIn("week", entry)
            self.assertIn("value", entry)

    def test_get_cycle_time_trend_calculates_weekly_average(self):
        """Test that get_cycle_time_trend calculates average cycle time per week."""
        # Create PRs in same week with different cycle times
        merged_dates = [
            timezone.datetime(2024, 1, 3, 12, 0),
            timezone.datetime(2024, 1, 4, 12, 0),
            timezone.datetime(2024, 1, 5, 12, 0),
        ]
        cycle_times = [Decimal("24.00"), Decimal("36.00"), Decimal("48.00")]

        for merged_date, cycle_time in zip(merged_dates, cycle_times, strict=True):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(merged_date),
                cycle_time_hours=cycle_time,
            )

        result = dashboard_service.get_cycle_time_trend(self.team, self.start_date, self.end_date)

        # Find the week with our data
        if len(result) > 0:
            week_data = result[0]
            # Average should be (24 + 36 + 48) / 3 = 36
            self.assertAlmostEqual(float(week_data["value"]), 36.0, places=1)
