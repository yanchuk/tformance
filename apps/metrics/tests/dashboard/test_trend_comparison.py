"""Tests for get_trend_comparison and monthly/weekly trend functions."""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.metrics.services.dashboard_service import (
    get_monthly_ai_adoption,
    get_monthly_cycle_time_trend,
    get_monthly_pr_count,
    get_monthly_review_time_trend,
    get_trend_comparison,
    get_weekly_pr_count,
)


class TestGetTrendComparison(TestCase):
    """Tests for get_trend_comparison function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        # Current period: this year
        self.current_end = date.today()
        self.current_start = self.current_end - timedelta(days=365)
        # Comparison period: last year
        self.compare_end = self.current_start - timedelta(days=1)
        self.compare_start = self.compare_end - timedelta(days=365)

    def test_returns_dict_with_required_keys(self):
        """get_trend_comparison returns dict with current, comparison, change_pct."""
        result = get_trend_comparison(
            self.team,
            "pr_count",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        self.assertIsInstance(result, dict)
        self.assertIn("current", result)
        self.assertIn("comparison", result)
        self.assertIn("change_pct", result)

    def test_current_contains_list_of_monthly_data(self):
        """current key contains list of monthly data points."""
        result = get_trend_comparison(
            self.team,
            "pr_count",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        self.assertIsInstance(result["current"], list)

    def test_comparison_contains_list_of_monthly_data(self):
        """comparison key contains list of monthly data points."""
        result = get_trend_comparison(
            self.team,
            "pr_count",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        self.assertIsInstance(result["comparison"], list)

    def test_change_pct_is_numeric(self):
        """change_pct is a numeric value."""
        result = get_trend_comparison(
            self.team,
            "pr_count",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        self.assertIsInstance(result["change_pct"], (int, float))

    def test_supports_cycle_time_metric(self):
        """Supports cycle_time metric."""
        result = get_trend_comparison(
            self.team,
            "cycle_time",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        self.assertIn("current", result)
        self.assertIn("comparison", result)

    def test_supports_review_time_metric(self):
        """Supports review_time metric."""
        result = get_trend_comparison(
            self.team,
            "review_time",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        self.assertIn("current", result)
        self.assertIn("comparison", result)

    def test_supports_pr_count_metric(self):
        """Supports pr_count metric."""
        result = get_trend_comparison(
            self.team,
            "pr_count",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        self.assertIn("current", result)
        self.assertIn("comparison", result)

    def test_supports_ai_adoption_metric(self):
        """Supports ai_adoption metric."""
        result = get_trend_comparison(
            self.team,
            "ai_adoption",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        self.assertIn("current", result)
        self.assertIn("comparison", result)

    def test_calculates_positive_change_percentage(self):
        """Calculates positive change when current avg exceeds comparison avg."""
        # Create PRs in comparison period (2 per month)
        for i in range(3):
            month_date = self.compare_start + timedelta(days=30 * i + 10)
            for _ in range(2):
                PullRequestFactory(
                    team=self.team,
                    author=self.member,
                    state="merged",
                    merged_at=timezone.make_aware(timezone.datetime.combine(month_date, timezone.datetime.min.time())),
                )

        # Create PRs in current period (4 per month - 100% increase)
        for i in range(3):
            month_date = self.current_start + timedelta(days=30 * i + 10)
            for _ in range(4):
                PullRequestFactory(
                    team=self.team,
                    author=self.member,
                    state="merged",
                    merged_at=timezone.make_aware(timezone.datetime.combine(month_date, timezone.datetime.min.time())),
                )

        result = get_trend_comparison(
            self.team,
            "pr_count",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        # Current avg (4) vs comparison avg (2) = 100% increase
        self.assertGreater(result["change_pct"], 0)

    def test_returns_zero_change_when_no_comparison_data(self):
        """Returns 0 change_pct when comparison period has no data."""
        # Create PRs only in current period
        month_date = self.current_start + timedelta(days=15)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(month_date, timezone.datetime.min.time())),
        )

        result = get_trend_comparison(
            self.team,
            "pr_count",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        self.assertEqual(result["change_pct"], 0.0)

    def test_defaults_to_cycle_time_for_unknown_metric(self):
        """Defaults to cycle_time function for unknown metric names."""
        result = get_trend_comparison(
            self.team,
            "unknown_metric",
            self.current_start,
            self.current_end,
            self.compare_start,
            self.compare_end,
        )

        # Should still return valid structure
        self.assertIn("current", result)
        self.assertIn("comparison", result)


class TestGetMonthlyCycleTimeTrend(TestCase):
    """Tests for get_monthly_cycle_time_trend function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=90)

    def test_returns_list_of_dicts(self):
        """Returns list of dicts."""
        result = get_monthly_cycle_time_trend(self.team, self.start_date, self.end_date)
        self.assertIsInstance(result, list)

    def test_returns_empty_list_when_no_prs(self):
        """Returns empty list when no PRs exist."""
        result = get_monthly_cycle_time_trend(self.team, self.start_date, self.end_date)
        self.assertEqual(result, [])

    def test_each_entry_has_month_and_value_keys(self):
        """Each entry has month and value keys."""
        merge_date = self.end_date - timedelta(days=15)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            cycle_time_hours=Decimal("24.0"),
        )

        result = get_monthly_cycle_time_trend(self.team, self.start_date, self.end_date)

        self.assertGreater(len(result), 0)
        self.assertIn("month", result[0])
        self.assertIn("value", result[0])

    def test_month_format_is_yyyy_mm(self):
        """Month is in YYYY-MM format."""
        merge_date = self.end_date - timedelta(days=15)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            cycle_time_hours=Decimal("24.0"),
        )

        result = get_monthly_cycle_time_trend(self.team, self.start_date, self.end_date)

        import re

        pattern = r"^\d{4}-\d{2}$"
        self.assertTrue(re.match(pattern, result[0]["month"]))

    def test_calculates_monthly_average_cycle_time(self):
        """Calculates average cycle time per month."""
        merge_date = self.end_date - timedelta(days=15)
        # Create 2 PRs with 10h and 20h cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            cycle_time_hours=Decimal("10.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            cycle_time_hours=Decimal("20.0"),
        )

        result = get_monthly_cycle_time_trend(self.team, self.start_date, self.end_date)

        # Average should be 15.0
        self.assertEqual(result[0]["value"], 15.0)


class TestGetMonthlyReviewTimeTrend(TestCase):
    """Tests for get_monthly_review_time_trend function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=90)

    def test_returns_list_of_dicts(self):
        """Returns list of dicts."""
        result = get_monthly_review_time_trend(self.team, self.start_date, self.end_date)
        self.assertIsInstance(result, list)

    def test_calculates_monthly_average_review_time(self):
        """Calculates average review time per month."""
        merge_date = self.end_date - timedelta(days=15)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            review_time_hours=Decimal("5.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            review_time_hours=Decimal("15.0"),
        )

        result = get_monthly_review_time_trend(self.team, self.start_date, self.end_date)

        # Average should be 10.0
        self.assertEqual(result[0]["value"], 10.0)


class TestGetMonthlyPRCount(TestCase):
    """Tests for get_monthly_pr_count function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=90)

    def test_returns_list_of_dicts(self):
        """Returns list of dicts."""
        result = get_monthly_pr_count(self.team, self.start_date, self.end_date)
        self.assertIsInstance(result, list)

    def test_counts_prs_per_month(self):
        """Counts number of PRs merged per month."""
        merge_date = self.end_date - timedelta(days=15)
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            )

        result = get_monthly_pr_count(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["value"], 3)

    def test_groups_by_month(self):
        """Groups PRs by their merge month."""
        # PRs in current month
        current_month_date = self.end_date - timedelta(days=5)
        for _ in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(
                    timezone.datetime.combine(current_month_date, timezone.datetime.min.time())
                ),
            )

        # PRs in previous month
        prev_month_date = self.end_date - timedelta(days=35)
        for _ in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(prev_month_date, timezone.datetime.min.time())),
            )

        result = get_monthly_pr_count(self.team, self.start_date, self.end_date)

        # Should have at least 2 months of data
        self.assertGreaterEqual(len(result), 2)
        values = [r["value"] for r in result]
        self.assertIn(2, values)
        self.assertIn(4, values)


class TestGetWeeklyPRCount(TestCase):
    """Tests for get_weekly_pr_count function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=30)

    def test_returns_list_of_dicts(self):
        """Returns list of dicts."""
        result = get_weekly_pr_count(self.team, self.start_date, self.end_date)
        self.assertIsInstance(result, list)

    def test_each_entry_has_week_and_value_keys(self):
        """Each entry has week and value keys."""
        merge_date = self.end_date - timedelta(days=5)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
        )

        result = get_weekly_pr_count(self.team, self.start_date, self.end_date)

        self.assertGreater(len(result), 0)
        self.assertIn("week", result[0])
        self.assertIn("value", result[0])

    def test_counts_prs_per_week(self):
        """Counts number of PRs merged per week."""
        merge_date = self.end_date - timedelta(days=3)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            )

        result = get_weekly_pr_count(self.team, self.start_date, self.end_date)

        # Find the week with our PRs
        values = [r["value"] for r in result]
        self.assertIn(5, values)


class TestGetMonthlyAIAdoption(TestCase):
    """Tests for get_monthly_ai_adoption function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=90)

    def test_returns_list_of_dicts(self):
        """Returns list of dicts."""
        result = get_monthly_ai_adoption(self.team, self.start_date, self.end_date)
        self.assertIsInstance(result, list)

    def test_calculates_ai_adoption_percentage_per_month(self):
        """Calculates AI adoption percentage per month."""
        merge_date = self.end_date - timedelta(days=15)
        # 3 AI-assisted, 1 non-AI = 75%
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
                is_ai_assisted=True,
            )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            is_ai_assisted=False,
        )

        result = get_monthly_ai_adoption(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["value"], 75.0)

    def test_returns_zero_when_no_ai_assisted_prs(self):
        """Returns 0% when all PRs are non-AI-assisted."""
        merge_date = self.end_date - timedelta(days=15)
        for _ in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
                is_ai_assisted=False,
            )

        result = get_monthly_ai_adoption(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["value"], 0.0)

    def test_returns_100_when_all_ai_assisted(self):
        """Returns 100% when all PRs are AI-assisted."""
        merge_date = self.end_date - timedelta(days=15)
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
                is_ai_assisted=True,
            )

        result = get_monthly_ai_adoption(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["value"], 100.0)
