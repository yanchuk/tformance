"""Tests for time-based aggregation in dashboard_service.

This test module covers:
- get_monthly_cycle_time_trend: Monthly aggregation of cycle time
- get_monthly_pr_count: Monthly aggregation of PR counts
- get_monthly_ai_adoption: Monthly aggregation of AI adoption %
- get_monthly_review_time: Monthly aggregation of review time
- get_weekly_pr_count: Weekly aggregation of PR counts
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory
from apps.metrics.services import dashboard_service


def make_aware_date(year: int, month: int, day: int):
    """Create a timezone-aware datetime from date components."""
    return timezone.make_aware(timezone.datetime(year, month, day))


class TestGetMonthlyCycleTimeTrend(TestCase):
    """Tests for monthly cycle time aggregation."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_empty_list_for_no_data(self):
        """Test that empty list returned when no PRs exist."""
        result = dashboard_service.get_monthly_cycle_time_trend(self.team, date(2024, 1, 1), date(2024, 12, 31))

        self.assertEqual(result, [])

    def test_returns_monthly_aggregated_data(self):
        """Test that data is grouped by month."""
        # Create PRs in different months
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 1, 15),
            cycle_time_hours=Decimal("24.0"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 1, 20),
            cycle_time_hours=Decimal("36.0"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 2, 10),
            cycle_time_hours=Decimal("12.0"),
        )

        result = dashboard_service.get_monthly_cycle_time_trend(self.team, date(2024, 1, 1), date(2024, 3, 31))

        # Should have 2 months with data
        self.assertEqual(len(result), 2)
        # January average: (24 + 36) / 2 = 30
        jan_data = next(r for r in result if r["month"] == "2024-01")
        self.assertAlmostEqual(float(jan_data["value"]), 30.0, places=1)
        # February: 12
        feb_data = next(r for r in result if r["month"] == "2024-02")
        self.assertAlmostEqual(float(feb_data["value"]), 12.0, places=1)

    def test_excludes_non_merged_prs(self):
        """Test that only merged PRs are included."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 1, 15),
            cycle_time_hours=Decimal("24.0"),
        )
        PullRequestFactory(
            team=self.team,
            state="open",
            merged_at=None,
            cycle_time_hours=None,
        )

        result = dashboard_service.get_monthly_cycle_time_trend(self.team, date(2024, 1, 1), date(2024, 1, 31))

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(float(result[0]["value"]), 24.0, places=1)

    def test_respects_date_range(self):
        """Test that only PRs in date range are included."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 1, 15),
            cycle_time_hours=Decimal("24.0"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 6, 15),  # Outside range
            cycle_time_hours=Decimal("48.0"),
        )

        result = dashboard_service.get_monthly_cycle_time_trend(self.team, date(2024, 1, 1), date(2024, 3, 31))

        self.assertEqual(len(result), 1)

    def test_month_format_is_yyyy_mm(self):
        """Test that month key is in YYYY-MM format."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 3, 15),
            cycle_time_hours=Decimal("24.0"),
        )

        result = dashboard_service.get_monthly_cycle_time_trend(self.team, date(2024, 1, 1), date(2024, 12, 31))

        self.assertEqual(result[0]["month"], "2024-03")


class TestGetMonthlyPRCount(TestCase):
    """Tests for monthly PR count aggregation."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_empty_list_for_no_data(self):
        """Test that empty list returned when no PRs exist."""
        result = dashboard_service.get_monthly_pr_count(self.team, date(2024, 1, 1), date(2024, 12, 31))

        self.assertEqual(result, [])

    def test_counts_prs_per_month(self):
        """Test that PRs are counted correctly per month."""
        # 3 PRs in January
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=make_aware_date(2024, 1, 15),
            )
        # 5 PRs in February
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=make_aware_date(2024, 2, 15),
            )

        result = dashboard_service.get_monthly_pr_count(self.team, date(2024, 1, 1), date(2024, 3, 31))

        jan_data = next(r for r in result if r["month"] == "2024-01")
        feb_data = next(r for r in result if r["month"] == "2024-02")
        self.assertEqual(jan_data["value"], 3)
        self.assertEqual(feb_data["value"], 5)


class TestGetMonthlyAIAdoption(TestCase):
    """Tests for monthly AI adoption percentage."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_empty_list_for_no_data(self):
        """Test that empty list returned when no PRs exist."""
        result = dashboard_service.get_monthly_ai_adoption(self.team, date(2024, 1, 1), date(2024, 12, 31))

        self.assertEqual(result, [])

    def test_calculates_ai_percentage_per_month(self):
        """Test AI adoption percentage is calculated correctly."""
        # January: 2 AI, 3 total = 66.67%
        PullRequestFactory(team=self.team, state="merged", merged_at=make_aware_date(2024, 1, 10), is_ai_assisted=True)
        PullRequestFactory(team=self.team, state="merged", merged_at=make_aware_date(2024, 1, 15), is_ai_assisted=True)
        PullRequestFactory(team=self.team, state="merged", merged_at=make_aware_date(2024, 1, 20), is_ai_assisted=False)

        # February: 1 AI, 2 total = 50%
        PullRequestFactory(team=self.team, state="merged", merged_at=make_aware_date(2024, 2, 10), is_ai_assisted=True)
        PullRequestFactory(team=self.team, state="merged", merged_at=make_aware_date(2024, 2, 15), is_ai_assisted=False)

        result = dashboard_service.get_monthly_ai_adoption(self.team, date(2024, 1, 1), date(2024, 3, 31))

        jan_data = next(r for r in result if r["month"] == "2024-01")
        feb_data = next(r for r in result if r["month"] == "2024-02")
        self.assertAlmostEqual(float(jan_data["value"]), 66.67, places=1)
        self.assertAlmostEqual(float(feb_data["value"]), 50.0, places=1)


class TestGetMonthlyReviewTime(TestCase):
    """Tests for monthly review time aggregation."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_empty_list_for_no_data(self):
        """Test that empty list returned when no PRs exist."""
        result = dashboard_service.get_monthly_review_time_trend(self.team, date(2024, 1, 1), date(2024, 12, 31))

        self.assertEqual(result, [])

    def test_calculates_average_review_time_per_month(self):
        """Test average review time is calculated correctly."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 1, 15),
            review_time_hours=Decimal("4.0"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 1, 20),
            review_time_hours=Decimal("8.0"),
        )

        result = dashboard_service.get_monthly_review_time_trend(self.team, date(2024, 1, 1), date(2024, 1, 31))

        # Average: (4 + 8) / 2 = 6
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(float(result[0]["value"]), 6.0, places=1)


class TestGetTrendComparison(TestCase):
    """Tests for YoY trend comparison."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_current_and_comparison_data(self):
        """Test that both current and comparison periods are returned."""
        # 2024 data
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 3, 15),
            cycle_time_hours=Decimal("24.0"),
        )
        # 2023 data (comparison)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2023, 3, 15),
            cycle_time_hours=Decimal("36.0"),
        )

        result = dashboard_service.get_trend_comparison(
            team=self.team,
            metric="cycle_time",
            current_start=date(2024, 1, 1),
            current_end=date(2024, 6, 30),
            compare_start=date(2023, 1, 1),
            compare_end=date(2023, 6, 30),
        )

        self.assertIn("current", result)
        self.assertIn("comparison", result)
        self.assertIn("change_pct", result)

    def test_calculates_change_percentage(self):
        """Test that change percentage is calculated correctly."""
        # 2024: avg 20h, 2023: avg 25h = -20% (improvement)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 3, 15),
            cycle_time_hours=Decimal("20.0"),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2023, 3, 15),
            cycle_time_hours=Decimal("25.0"),
        )

        result = dashboard_service.get_trend_comparison(
            team=self.team,
            metric="cycle_time",
            current_start=date(2024, 1, 1),
            current_end=date(2024, 6, 30),
            compare_start=date(2023, 1, 1),
            compare_end=date(2023, 6, 30),
        )

        # Change should be -20%
        self.assertAlmostEqual(float(result["change_pct"]), -20.0, places=1)


class TestGetWeeklyPRCount(TestCase):
    """Tests for weekly PR count aggregation."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_empty_list_for_no_data(self):
        """Test that empty list returned when no PRs exist."""
        result = dashboard_service.get_weekly_pr_count(self.team, date(2024, 1, 1), date(2024, 12, 31))

        self.assertEqual(result, [])

    def test_counts_prs_per_week(self):
        """Test that PRs are counted correctly per week."""
        # 3 PRs in week 2 (Jan 8-14)
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=make_aware_date(2024, 1, 10),
            )
        # 5 PRs in week 3 (Jan 15-21)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=make_aware_date(2024, 1, 17),
            )

        result = dashboard_service.get_weekly_pr_count(self.team, date(2024, 1, 1), date(2024, 1, 31))

        self.assertEqual(len(result), 2)
        # Find week 2 and week 3 data
        week2_data = next((r for r in result if "W02" in r["week"]), None)
        week3_data = next((r for r in result if "W03" in r["week"]), None)
        self.assertIsNotNone(week2_data)
        self.assertIsNotNone(week3_data)
        self.assertEqual(week2_data["value"], 3)
        self.assertEqual(week3_data["value"], 5)

    def test_respects_date_range(self):
        """Test that only PRs in date range are included."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 1, 15),
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 6, 15),  # Outside range
        )

        result = dashboard_service.get_weekly_pr_count(self.team, date(2024, 1, 1), date(2024, 1, 31))

        self.assertEqual(len(result), 1)

    def test_week_format_is_yyyy_wnn(self):
        """Test that week key is in YYYY-WNN format."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 3, 15),
        )

        result = dashboard_service.get_weekly_pr_count(self.team, date(2024, 1, 1), date(2024, 12, 31))

        self.assertEqual(len(result), 1)
        # March 15 2024 is week 11
        self.assertRegex(result[0]["week"], r"^\d{4}-W\d{2}$")

    def test_excludes_non_merged_prs(self):
        """Test that only merged PRs are included."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=make_aware_date(2024, 1, 15),
        )
        PullRequestFactory(
            team=self.team,
            state="open",
            merged_at=None,
        )
        PullRequestFactory(
            team=self.team,
            state="closed",
            merged_at=None,
        )

        result = dashboard_service.get_weekly_pr_count(self.team, date(2024, 1, 1), date(2024, 1, 31))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["value"], 1)
