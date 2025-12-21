"""Tests for Celery tasks for computing daily insights."""

from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.metrics.factories import DailyInsightFactory, TeamFactory


class TestComputeTeamInsightsTask(TestCase):
    """Tests for compute_team_insights Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.today = date.today()

    @patch("apps.metrics.tasks.compute_insights")
    def test_compute_team_insights_creates_insights(self, mock_compute_insights):
        """Test that compute_team_insights calls compute_insights with correct team and date."""
        from apps.metrics.tasks import compute_team_insights

        # Mock compute_insights to return list of insights
        mock_insights = [
            DailyInsightFactory.build(team=self.team, date=self.today),
            DailyInsightFactory.build(team=self.team, date=self.today),
        ]
        mock_compute_insights.return_value = mock_insights

        # Call the task
        result = compute_team_insights(self.team.id)

        # Verify compute_insights was called with correct team and today's date
        mock_compute_insights.assert_called_once()
        called_team = mock_compute_insights.call_args[0][0]
        called_date = mock_compute_insights.call_args[0][1]

        self.assertEqual(called_team.id, self.team.id)
        self.assertEqual(called_date, self.today)

        # Verify result contains count of insights created
        self.assertEqual(result, 2)

    @patch("apps.metrics.tasks.compute_insights")
    def test_compute_team_insights_returns_count(self, mock_compute_insights):
        """Test that compute_team_insights returns count of insights created."""
        from apps.metrics.tasks import compute_team_insights

        # Mock compute_insights to return 5 insights
        mock_insights = [DailyInsightFactory.build(team=self.team, date=self.today) for _ in range(5)]
        mock_compute_insights.return_value = mock_insights

        # Call the task
        result = compute_team_insights(self.team.id)

        # Verify count is returned
        self.assertEqual(result, 5)

    def test_compute_team_insights_invalid_team_id_raises(self):
        """Test that compute_team_insights raises exception for invalid team_id."""
        from apps.metrics.tasks import compute_team_insights
        from apps.teams.models import Team

        non_existent_id = 99999

        # Call the task with non-existent ID - should raise exception
        with self.assertRaises(Team.DoesNotExist):
            compute_team_insights(non_existent_id)

    @patch("apps.metrics.tasks.compute_insights")
    def test_compute_team_insights_uses_todays_date(self, mock_compute_insights):
        """Test that task uses today's date when computing insights."""
        from apps.metrics.tasks import compute_team_insights

        mock_compute_insights.return_value = []

        # Call the task
        compute_team_insights(self.team.id)

        # Verify today's date was used
        called_date = mock_compute_insights.call_args[0][1]
        self.assertEqual(called_date, date.today())

    @patch("apps.metrics.tasks.compute_insights")
    def test_compute_team_insights_handles_zero_insights(self, mock_compute_insights):
        """Test that task handles case when no insights are generated."""
        from apps.metrics.tasks import compute_team_insights

        # Mock compute_insights to return empty list
        mock_compute_insights.return_value = []

        # Call the task
        result = compute_team_insights(self.team.id)

        # Verify zero count is returned
        self.assertEqual(result, 0)


class TestComputeAllTeamInsightsTask(TestCase):
    """Tests for compute_all_team_insights Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team1 = TeamFactory(name="Team Alpha")
        self.team2 = TeamFactory(name="Team Beta")
        self.team3 = TeamFactory(name="Team Gamma")

    @patch("apps.metrics.tasks.compute_team_insights")
    def test_compute_all_team_insights_runs_for_all_teams(self, mock_compute_team_insights):
        """Test that compute_all_team_insights dispatches tasks for all teams."""
        from apps.metrics.tasks import compute_all_team_insights

        # Mock the task.delay method to track calls
        mock_compute_team_insights.delay = MagicMock()

        # Call the task
        compute_all_team_insights()

        # Verify compute_team_insights.delay was called for each team
        self.assertEqual(mock_compute_team_insights.delay.call_count, 3)

        # Verify it was called with correct team IDs
        called_team_ids = [call[0][0] for call in mock_compute_team_insights.delay.call_args_list]
        self.assertIn(self.team1.id, called_team_ids)
        self.assertIn(self.team2.id, called_team_ids)
        self.assertIn(self.team3.id, called_team_ids)

    @patch("apps.metrics.tasks.compute_team_insights")
    def test_compute_all_team_insights_returns_team_count(self, mock_compute_team_insights):
        """Test that compute_all_team_insights returns count of teams processed."""
        from apps.metrics.tasks import compute_all_team_insights

        mock_compute_team_insights.delay = MagicMock()

        # Call the task
        result = compute_all_team_insights()

        # Verify result contains team count
        self.assertIsInstance(result, dict)
        self.assertIn("teams_dispatched", result)
        self.assertEqual(result["teams_dispatched"], 3)

    @patch("apps.metrics.tasks.compute_team_insights")
    def test_compute_all_team_insights_handles_no_teams(self, mock_compute_team_insights):
        """Test that task handles case when no teams exist."""
        from apps.metrics.tasks import compute_all_team_insights
        from apps.teams.models import Team

        # Delete all teams
        Team.objects.all().delete()

        mock_compute_team_insights.delay = MagicMock()

        # Call the task
        result = compute_all_team_insights()

        # Verify no tasks were dispatched
        mock_compute_team_insights.delay.assert_not_called()
        self.assertEqual(result["teams_dispatched"], 0)

    @patch("apps.metrics.tasks.compute_team_insights")
    def test_compute_all_team_insights_continues_on_dispatch_failure(self, mock_compute_team_insights):
        """Test that task continues processing remaining teams if one dispatch fails."""
        from apps.metrics.tasks import compute_all_team_insights

        # Mock delay to raise exception for first team only
        def delay_side_effect(team_id):
            if team_id == self.team1.id:
                raise Exception("Dispatch failed")

        mock_compute_team_insights.delay = MagicMock(side_effect=delay_side_effect)

        # Call the task
        result = compute_all_team_insights()

        # Verify all teams were attempted (3 calls)
        self.assertEqual(mock_compute_team_insights.delay.call_count, 3)

        # Verify result shows only 2 successful dispatches
        self.assertEqual(result["teams_dispatched"], 2)


class TestRulesRegisteredOnImport(TestCase):
    """Tests that insight rules are registered when tasks module is imported."""

    @patch("apps.metrics.tasks.register_rule")
    def test_rules_are_registered_on_import(self, mock_register_rule):
        """Test that all insight rules are registered when tasks module is imported."""
        # This test verifies that importing the tasks module triggers rule registration
        # The actual implementation will import insight rule modules and register them

        # Import the tasks module (this should trigger rule registration)
        import importlib

        import apps.metrics.tasks

        importlib.reload(apps.metrics.tasks)

        # Verify register_rule was called at least once
        # (We'll implement multiple rules, so this confirms the pattern works)
        # This will fail initially since tasks.py doesn't exist yet
        self.assertTrue(
            mock_register_rule.called,
            "register_rule should be called when tasks module is imported to register insight rules",
        )

    def test_registered_rules_are_available_to_compute_insights(self):
        """Test that registered rules can be retrieved by compute_insights."""
        # Import tasks module to trigger registration
        import apps.metrics.tasks  # noqa: F401
        from apps.metrics.insights.engine import get_all_rules

        # Get registered rules
        rules = get_all_rules()

        # Verify at least some rules are registered
        # This will fail initially since tasks.py doesn't exist yet
        self.assertGreater(
            len(rules),
            0,
            "At least one insight rule should be registered after importing tasks module",
        )
