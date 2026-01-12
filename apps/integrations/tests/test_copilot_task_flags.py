"""Tests for Copilot task feature flag gating.

These tests verify that Copilot Celery tasks respect feature flags
and skip execution when flags are disabled.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.integrations._task_modules.copilot import (
    sync_all_copilot_metrics,
    sync_copilot_metrics_task,
)
from apps.integrations.factories import GitHubIntegrationFactory, IntegrationCredentialFactory
from apps.metrics.factories import TeamFactory


class TestSyncCopilotMetricsTaskFlagGating(TestCase):
    """Tests for sync_copilot_metrics_task respecting feature flags."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="test-org",
        )

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled")
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    def test_task_skips_when_flag_disabled(self, mock_fetch, mock_flag_check):
        """Test that sync task skips execution when copilot_enabled flag is off."""
        mock_flag_check.return_value = False

        result = sync_copilot_metrics_task(self.team.id)

        # Should not call the API
        mock_fetch.assert_not_called()

        # Should return skip status with reason
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "flag_disabled")

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_enabled")
    @patch("apps.integrations._task_modules.copilot.fetch_copilot_metrics")
    @patch("apps.integrations._task_modules.copilot.parse_metrics_response")
    def test_task_runs_when_flag_enabled(self, mock_parse, mock_fetch, mock_flag_check):
        """Test that sync task runs normally when copilot_enabled flag is on."""
        mock_flag_check.return_value = True
        mock_fetch.return_value = []
        mock_parse.return_value = []

        result = sync_copilot_metrics_task(self.team.id)

        # Should call the API
        mock_fetch.assert_called_once()

        # Should return success result (not skip)
        self.assertNotIn("status", result)
        self.assertIn("metrics_synced", result)


class TestSyncAllCopilotMetricsFlagGating(TestCase):
    """Tests for sync_all_copilot_metrics respecting feature flags."""

    def setUp(self):
        """Set up test fixtures."""
        # Teams must have copilot_status="connected" to be included in sync
        self.team1 = TeamFactory(copilot_status="connected")
        self.credential1 = IntegrationCredentialFactory(
            team=self.team1,
            provider="github",
            access_token="test_token_1",
        )
        self.integration1 = GitHubIntegrationFactory(
            team=self.team1,
            credential=self.credential1,
            organization_slug="test-org-1",
        )

        self.team2 = TeamFactory(copilot_status="connected")
        self.credential2 = IntegrationCredentialFactory(
            team=self.team2,
            provider="github",
            access_token="test_token_2",
        )
        self.integration2 = GitHubIntegrationFactory(
            team=self.team2,
            credential=self.credential2,
            organization_slug="test-org-2",
        )

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_globally_enabled")
    @patch("apps.integrations._task_modules.copilot.sync_copilot_metrics_task")
    def test_sync_all_skips_when_global_flag_disabled(self, mock_task, mock_global_flag):
        """Test that sync_all skips all teams when global flag is off."""
        mock_global_flag.return_value = False

        result = sync_all_copilot_metrics()

        # Should not dispatch any tasks
        mock_task.delay.assert_not_called()

        # Should return skip status
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "flag_disabled")

    @patch("apps.integrations._task_modules.copilot.is_copilot_sync_globally_enabled")
    @patch("apps.integrations._task_modules.copilot.sync_copilot_metrics_task")
    def test_sync_all_runs_when_global_flag_enabled(self, mock_task, mock_global_flag):
        """Test that sync_all dispatches tasks when global flag is on."""
        mock_global_flag.return_value = True

        result = sync_all_copilot_metrics()

        # Should dispatch tasks for both teams
        self.assertEqual(mock_task.delay.call_count, 2)

        # Should return success with count
        self.assertIn("teams_dispatched", result)
        self.assertEqual(result["teams_dispatched"], 2)
