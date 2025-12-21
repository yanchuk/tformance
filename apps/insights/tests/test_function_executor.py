"""
Tests for the Gemini function executor.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.insights.services.function_executor import (
    FUNCTION_EXECUTORS,
    _get_date_range,
    execute_function,
)
from apps.metrics.factories import TeamFactory


class TestGetDateRange(TestCase):
    """Tests for the date range helper."""

    def test_returns_tuple_of_dates(self):
        """Test that _get_date_range returns a tuple of dates."""
        start_date, end_date = _get_date_range(30)
        self.assertIsInstance(start_date, date)
        self.assertIsInstance(end_date, date)

    def test_end_date_is_today(self):
        """Test that end_date is today."""
        _, end_date = _get_date_range(30)
        self.assertEqual(end_date, date.today())

    def test_start_date_is_days_before_today(self):
        """Test that start_date is the correct number of days before today."""
        start_date, end_date = _get_date_range(30)
        expected_start = end_date - timedelta(days=30)
        self.assertEqual(start_date, expected_start)

    def test_clamps_to_max_days(self):
        """Test that days are clamped to max_days."""
        start_date, end_date = _get_date_range(100, max_days=30)
        expected_start = end_date - timedelta(days=30)
        self.assertEqual(start_date, expected_start)

    def test_clamps_to_minimum_one_day(self):
        """Test that days are clamped to at least 1."""
        start_date, end_date = _get_date_range(0)
        expected_start = end_date - timedelta(days=1)
        self.assertEqual(start_date, expected_start)


class TestExecuteFunction(TestCase):
    """Tests for the execute_function function."""

    def test_raises_for_unknown_function(self):
        """Test that unknown functions raise ValueError."""
        team = TeamFactory()
        with self.assertRaises(ValueError) as context:
            execute_function("unknown_function", {}, team)
        self.assertIn("Unknown function", str(context.exception))

    def test_all_executors_are_callable(self):
        """Test that all registered executors are callable."""
        for name, executor in FUNCTION_EXECUTORS.items():
            self.assertTrue(callable(executor), f"{name} executor is not callable")


class TestGetTeamMetrics(TestCase):
    """Tests for the get_team_metrics function."""

    @patch("apps.insights.services.function_executor.dashboard_service")
    def test_returns_expected_structure(self, mock_service):
        """Test that get_team_metrics returns expected structure."""
        mock_service.get_key_metrics.return_value = {
            "total_prs": 50,
            "merged_prs": 45,
            "merge_rate": Decimal("90.0"),
            "avg_cycle_time": Decimal("24.5"),
            "avg_review_time": Decimal("4.2"),
            "ai_adoption": Decimal("55.0"),
        }

        team = TeamFactory()
        result = execute_function("get_team_metrics", {"days": 30}, team)

        self.assertIn("period_days", result)
        self.assertIn("total_prs", result)
        self.assertIn("merged_prs", result)
        self.assertIn("merge_rate_percent", result)
        self.assertIn("avg_cycle_time_hours", result)
        self.assertIn("avg_review_time_hours", result)
        self.assertIn("ai_adoption_percent", result)

    @patch("apps.insights.services.function_executor.dashboard_service")
    def test_converts_decimals_to_floats(self, mock_service):
        """Test that Decimal values are converted to floats."""
        mock_service.get_key_metrics.return_value = {
            "total_prs": 50,
            "merged_prs": 45,
            "merge_rate": Decimal("90.0"),
            "avg_cycle_time": Decimal("24.5"),
            "avg_review_time": Decimal("4.2"),
            "ai_adoption": Decimal("55.0"),
        }

        team = TeamFactory()
        result = execute_function("get_team_metrics", {"days": 30}, team)

        self.assertIsInstance(result["merge_rate_percent"], float)
        self.assertIsInstance(result["avg_cycle_time_hours"], float)
        self.assertIsInstance(result["ai_adoption_percent"], float)


class TestGetAiAdoptionTrend(TestCase):
    """Tests for the get_ai_adoption_trend function."""

    @patch("apps.insights.services.function_executor.dashboard_service")
    def test_returns_expected_structure(self, mock_service):
        """Test that get_ai_adoption_trend returns expected structure."""
        mock_service.get_ai_adoption_trend.return_value = [
            {"period": "Week 1", "ai_percent": Decimal("50.0"), "total_prs": 10},
            {"period": "Week 2", "ai_percent": Decimal("55.0"), "total_prs": 12},
        ]

        team = TeamFactory()
        result = execute_function("get_ai_adoption_trend", {"days": 30}, team)

        self.assertIn("period_days", result)
        self.assertIn("trend", result)
        self.assertEqual(len(result["trend"]), 2)
        self.assertIn("period", result["trend"][0])
        self.assertIn("ai_percent", result["trend"][0])


class TestGetDeveloperStats(TestCase):
    """Tests for the get_developer_stats function."""

    @patch("apps.insights.services.function_executor.dashboard_service")
    def test_returns_expected_structure(self, mock_service):
        """Test that get_developer_stats returns expected structure."""
        mock_service.get_team_breakdown.return_value = [
            {
                "author": "Alice",
                "pr_count": 10,
                "avg_cycle_time": Decimal("20.0"),
                "ai_percent": Decimal("60.0"),
                "lines_added": 500,
                "lines_deleted": 100,
            },
        ]

        team = TeamFactory()
        result = execute_function("get_developer_stats", {"days": 30}, team)

        self.assertIn("period_days", result)
        self.assertIn("developers", result)
        self.assertEqual(len(result["developers"]), 1)
        self.assertEqual(result["developers"][0]["name"], "Alice")

    @patch("apps.insights.services.function_executor.dashboard_service")
    def test_filters_by_developer_name(self, mock_service):
        """Test that developer_name parameter filters results."""
        mock_service.get_team_breakdown.return_value = [
            {
                "author": "Alice",
                "pr_count": 10,
                "avg_cycle_time": 20.0,
                "ai_percent": 60.0,
                "lines_added": 500,
                "lines_deleted": 100,
            },
            {
                "author": "Bob",
                "pr_count": 8,
                "avg_cycle_time": 18.0,
                "ai_percent": 55.0,
                "lines_added": 400,
                "lines_deleted": 80,
            },
        ]

        team = TeamFactory()
        result = execute_function("get_developer_stats", {"days": 30, "developer_name": "Alice"}, team)

        self.assertEqual(len(result["developers"]), 1)
        self.assertEqual(result["developers"][0]["name"], "Alice")


class TestGetReviewerWorkload(TestCase):
    """Tests for the get_reviewer_workload function."""

    @patch("apps.insights.services.function_executor.dashboard_service")
    def test_returns_expected_structure(self, mock_service):
        """Test that get_reviewer_workload returns expected structure."""
        mock_service.get_reviewer_workload.return_value = [
            {
                "reviewer": "Charlie",
                "review_count": 15,
                "avg_review_time": Decimal("2.5"),
                "approval_rate": Decimal("80.0"),
            },
        ]

        team = TeamFactory()
        result = execute_function("get_reviewer_workload", {"days": 30}, team)

        self.assertIn("period_days", result)
        self.assertIn("reviewers", result)
        self.assertEqual(len(result["reviewers"]), 1)
        self.assertEqual(result["reviewers"][0]["name"], "Charlie")


class TestGetRecentPrs(TestCase):
    """Tests for the get_recent_prs function."""

    @patch("apps.insights.services.function_executor.dashboard_service")
    def test_returns_expected_structure(self, mock_service):
        """Test that get_recent_prs returns expected structure."""
        mock_service.get_recent_prs.return_value = [
            {
                "title": "Fix bug",
                "author": "Alice",
                "state": "merged",
                "cycle_time": Decimal("12.5"),
                "is_ai_assisted": True,
                "merged_at": date.today(),
            },
        ]

        team = TeamFactory()
        result = execute_function("get_recent_prs", {"days": 7, "limit": 10}, team)

        self.assertIn("period_days", result)
        self.assertIn("pull_requests", result)
        self.assertEqual(len(result["pull_requests"]), 1)
        self.assertEqual(result["pull_requests"][0]["title"], "Fix bug")

    @patch("apps.insights.services.function_executor.dashboard_service")
    def test_clamps_limit_to_max(self, mock_service):
        """Test that limit is clamped to maximum value."""
        mock_service.get_recent_prs.return_value = []

        team = TeamFactory()
        execute_function("get_recent_prs", {"days": 7, "limit": 100}, team)

        # Verify the limit was clamped to 20
        call_args = mock_service.get_recent_prs.call_args
        self.assertEqual(call_args.kwargs["limit"], 20)
