"""Tests for LLM-powered dashboard insight Celery tasks.

Tests for Phase 3 of Dashboard Insights feature:
- generate_weekly_insights: Generate insights for all teams
- generate_monthly_insights: Generate monthly insights for all teams
"""

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory


class TestGenerateWeeklyInsightsTask(TestCase):
    """Tests for generate_weekly_insights Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team1 = TeamFactory(name="Team Alpha")
        self.team2 = TeamFactory(name="Team Beta")
        self.today = date.today()

    @patch("apps.metrics.tasks.generate_insight")
    @patch("apps.metrics.tasks.gather_insight_data")
    @patch("apps.metrics.tasks.cache_insight")
    def test_runs_for_all_teams(self, mock_cache, mock_gather, mock_generate):
        """Test that generate_weekly_insights processes all teams."""
        from apps.metrics.tasks import generate_weekly_insights

        # Mock insight generation
        mock_gather.return_value = {"velocity": {}, "quality": {}}
        mock_generate.return_value = {
            "headline": "Test headline",
            "detail": "Test detail",
            "recommendation": "Test rec",
            "metric_cards": [],
            "is_fallback": False,
        }

        # Call the task
        result = generate_weekly_insights()

        # Verify gather_insight_data was called for each team
        self.assertEqual(mock_gather.call_count, 2)

        # Verify generate_insight was called for each team
        self.assertEqual(mock_generate.call_count, 2)

        # Verify result contains team count
        self.assertIn("teams_processed", result)
        self.assertEqual(result["teams_processed"], 2)

    @patch("apps.metrics.tasks.generate_insight")
    @patch("apps.metrics.tasks.gather_insight_data")
    @patch("apps.metrics.tasks.cache_insight")
    def test_stores_results_in_daily_insight(self, mock_cache, mock_gather, mock_generate):
        """Test that generate_weekly_insights stores results via cache_insight."""
        from apps.metrics.tasks import generate_weekly_insights

        # Mock insight generation
        mock_gather.return_value = {"velocity": {}, "quality": {}}
        insight_result = {
            "headline": "Test headline",
            "detail": "Test detail",
            "recommendation": "Test rec",
            "metric_cards": [],
            "is_fallback": False,
        }
        mock_generate.return_value = insight_result

        # Call the task
        generate_weekly_insights()

        # Verify cache_insight was called for each team with correct parameters
        self.assertEqual(mock_cache.call_count, 2)

        # Check first call
        call_kwargs = mock_cache.call_args_list[0][1]
        self.assertEqual(call_kwargs["cadence"], "weekly")
        self.assertEqual(call_kwargs["insight"], insight_result)

    @patch("apps.metrics.tasks.generate_insight")
    @patch("apps.metrics.tasks.gather_insight_data")
    @patch("apps.metrics.tasks.cache_insight")
    def test_uses_7_day_period(self, mock_cache, mock_gather, mock_generate):
        """Test that generate_weekly_insights uses a 7-day period."""
        from apps.metrics.tasks import generate_weekly_insights

        mock_gather.return_value = {"velocity": {}, "quality": {}}
        mock_generate.return_value = {
            "headline": "Test",
            "detail": "Test",
            "recommendation": "Test",
            "metric_cards": [],
            "is_fallback": False,
        }

        generate_weekly_insights()

        # Check that gather_insight_data was called with correct date range
        first_call_args = mock_gather.call_args_list[0]
        start_date = first_call_args[1]["start_date"]
        end_date = first_call_args[1]["end_date"]

        # Should be 7 days
        self.assertEqual((end_date - start_date).days, 7)

    @patch("apps.metrics.tasks.generate_insight")
    @patch("apps.metrics.tasks.gather_insight_data")
    @patch("apps.metrics.tasks.cache_insight")
    def test_continues_on_team_error(self, mock_cache, mock_gather, mock_generate):
        """Test that task continues processing if one team fails."""
        from apps.metrics.tasks import generate_weekly_insights

        # Make first call fail, second succeed
        mock_gather.side_effect = [
            Exception("Team 1 failed"),
            {"velocity": {}, "quality": {}},
        ]
        mock_generate.return_value = {
            "headline": "Test",
            "detail": "Test",
            "recommendation": "Test",
            "metric_cards": [],
            "is_fallback": False,
        }

        result = generate_weekly_insights()

        # Should still process second team
        self.assertEqual(result["teams_processed"], 1)
        self.assertEqual(result["errors"], 1)

    @patch("apps.metrics.tasks.generate_insight")
    @patch("apps.metrics.tasks.gather_insight_data")
    @patch("apps.metrics.tasks.cache_insight")
    def test_handles_no_teams(self, mock_cache, mock_gather, mock_generate):
        """Test that task handles case when no teams exist."""
        from apps.metrics.tasks import generate_weekly_insights
        from apps.teams.models import Team

        # Delete all teams
        Team.objects.all().delete()

        result = generate_weekly_insights()

        # Verify no processing happened
        mock_gather.assert_not_called()
        self.assertEqual(result["teams_processed"], 0)


class TestGenerateMonthlyInsightsTask(TestCase):
    """Tests for generate_monthly_insights Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory(name="Team Alpha")
        self.today = date.today()

    @patch("apps.metrics.tasks.generate_insight")
    @patch("apps.metrics.tasks.gather_insight_data")
    @patch("apps.metrics.tasks.cache_insight")
    def test_runs_for_all_teams_monthly(self, mock_cache, mock_gather, mock_generate):
        """Test that generate_monthly_insights processes all teams."""
        from apps.metrics.tasks import generate_monthly_insights

        mock_gather.return_value = {"velocity": {}, "quality": {}}
        mock_generate.return_value = {
            "headline": "Monthly insight",
            "detail": "Monthly detail",
            "recommendation": "Monthly rec",
            "metric_cards": [],
            "is_fallback": False,
        }

        result = generate_monthly_insights()

        self.assertEqual(mock_generate.call_count, 1)
        self.assertEqual(result["teams_processed"], 1)

    @patch("apps.metrics.tasks.generate_insight")
    @patch("apps.metrics.tasks.gather_insight_data")
    @patch("apps.metrics.tasks.cache_insight")
    def test_uses_30_day_period(self, mock_cache, mock_gather, mock_generate):
        """Test that generate_monthly_insights uses a 30-day period."""
        from apps.metrics.tasks import generate_monthly_insights

        mock_gather.return_value = {"velocity": {}, "quality": {}}
        mock_generate.return_value = {
            "headline": "Test",
            "detail": "Test",
            "recommendation": "Test",
            "metric_cards": [],
            "is_fallback": False,
        }

        generate_monthly_insights()

        # Check that gather_insight_data was called with correct date range
        first_call_args = mock_gather.call_args_list[0]
        start_date = first_call_args[1]["start_date"]
        end_date = first_call_args[1]["end_date"]

        # Should be 30 days
        self.assertEqual((end_date - start_date).days, 30)

    @patch("apps.metrics.tasks.generate_insight")
    @patch("apps.metrics.tasks.gather_insight_data")
    @patch("apps.metrics.tasks.cache_insight")
    def test_stores_with_monthly_cadence(self, mock_cache, mock_gather, mock_generate):
        """Test that monthly insights are stored with monthly cadence."""
        from apps.metrics.tasks import generate_monthly_insights

        mock_gather.return_value = {"velocity": {}, "quality": {}}
        mock_generate.return_value = {
            "headline": "Test",
            "detail": "Test",
            "recommendation": "Test",
            "metric_cards": [],
            "is_fallback": False,
        }

        generate_monthly_insights()

        # Verify cache_insight was called with monthly cadence
        call_kwargs = mock_cache.call_args[1]
        self.assertEqual(call_kwargs["cadence"], "monthly")
