"""Tests for Quick Sync Task dispatching metrics aggregation.

TDD RED Phase: These tests verify that sync_quick_data_task dispatches
aggregate_team_weekly_metrics_task after successful completion, allowing
the dashboard to show preliminary metrics from 7-day data immediately.

Current behavior (to be fixed):
- sync_quick_data_task completes and queues sync_full_history_task
- Metrics aggregation only runs after full history sync
- Dashboard has no data until full sync completes

Desired behavior:
- After quick sync completes successfully, also dispatch aggregate_team_weekly_metrics_task
- Dashboard can show preliminary metrics from 7-day data immediately
- Full sync will update metrics again when it completes
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    TrackedRepositoryFactory,
)
from apps.metrics.factories import TeamFactory


class TestSyncQuickDataTaskDispatchesMetricsAggregation(TestCase):
    """Tests that sync_quick_data_task dispatches aggregate_team_weekly_metrics_task on success."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
            is_active=True,
        )

    @patch("apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task")
    @patch("apps.integrations._task_modules.github_sync.sync_full_history_task")
    @patch("apps.integrations._task_modules.github_sync._sync_with_graphql_or_rest")
    def test_dispatches_metrics_aggregation_after_quick_sync_success(
        self, mock_sync, mock_full_sync_task, mock_metrics_task
    ):
        """Test that aggregate_team_weekly_metrics_task is dispatched after quick sync completes."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}
        mock_full_sync_delay = MagicMock()
        mock_full_sync_task.delay = mock_full_sync_delay
        mock_metrics_delay = MagicMock()
        mock_metrics_task.delay = mock_metrics_delay

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Verify aggregate_team_weekly_metrics_task.delay was called
        mock_metrics_delay.assert_called_once()

    @patch("apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task")
    @patch("apps.integrations._task_modules.github_sync.sync_full_history_task")
    @patch("apps.integrations._task_modules.github_sync._sync_with_graphql_or_rest")
    def test_dispatches_metrics_aggregation_with_correct_team_id(
        self, mock_sync, mock_full_sync_task, mock_metrics_task
    ):
        """Test that metrics aggregation is dispatched with the correct team_id from TrackedRepository."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}
        mock_full_sync_delay = MagicMock()
        mock_full_sync_task.delay = mock_full_sync_delay
        mock_metrics_delay = MagicMock()
        mock_metrics_task.delay = mock_metrics_delay

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Verify metrics task was called with the correct team_id
        mock_metrics_delay.assert_called_once_with(self.tracked_repo.team_id)


class TestSyncQuickDataTaskDoesNotDispatchMetricsOnFailure(TestCase):
    """Tests that sync_quick_data_task does NOT dispatch metrics aggregation on failure."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
            is_active=True,
        )

    @patch("apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task")
    @patch("apps.integrations._task_modules.github_sync.sync_full_history_task")
    @patch("apps.integrations._task_modules.github_sync._sync_with_graphql_or_rest")
    def test_does_not_dispatch_metrics_aggregation_on_sync_error(
        self, mock_sync, mock_full_sync_task, mock_metrics_task
    ):
        """Test that metrics aggregation is NOT dispatched when quick sync fails."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.side_effect = Exception("GitHub API error")
        mock_full_sync_delay = MagicMock()
        mock_full_sync_task.delay = mock_full_sync_delay
        mock_metrics_delay = MagicMock()
        mock_metrics_task.delay = mock_metrics_delay

        # Mock retry to simulate exhausted retries
        with patch.object(sync_quick_data_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            with patch("sentry_sdk.capture_exception"):
                # Call the task
                sync_quick_data_task(self.tracked_repo.id)

        # Verify aggregate_team_weekly_metrics_task.delay was NOT called
        mock_metrics_delay.assert_not_called()

    @patch("apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task")
    @patch("apps.integrations._task_modules.github_sync.sync_full_history_task")
    @patch("apps.integrations._task_modules.github_sync._sync_with_graphql_or_rest")
    def test_does_not_dispatch_metrics_aggregation_for_inactive_repo(
        self, mock_sync, mock_full_sync_task, mock_metrics_task
    ):
        """Test that metrics aggregation is NOT dispatched for inactive repositories."""
        from apps.integrations.tasks import sync_quick_data_task

        # Make repo inactive
        self.tracked_repo.is_active = False
        self.tracked_repo.save()

        mock_metrics_delay = MagicMock()
        mock_metrics_task.delay = mock_metrics_delay

        # Call the task
        result = sync_quick_data_task(self.tracked_repo.id)

        # Verify task was skipped
        self.assertTrue(result.get("skipped", False))

        # Verify aggregate_team_weekly_metrics_task.delay was NOT called
        mock_metrics_delay.assert_not_called()

    @patch("apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task")
    @patch("apps.integrations._task_modules.github_sync.sync_full_history_task")
    def test_does_not_dispatch_metrics_aggregation_for_nonexistent_repo(self, mock_full_sync_task, mock_metrics_task):
        """Test that metrics aggregation is NOT dispatched for non-existent repo ID."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_metrics_delay = MagicMock()
        mock_metrics_task.delay = mock_metrics_delay

        # Call the task with non-existent ID
        result = sync_quick_data_task(99999)

        # Verify task returned error
        self.assertIn("error", result)

        # Verify aggregate_team_weekly_metrics_task.delay was NOT called
        mock_metrics_delay.assert_not_called()


class TestSyncQuickDataTaskMetricsAggregationUsesCorrectTeamId(TestCase):
    """Tests that metrics aggregation uses the correct team_id from the TrackedRepository."""

    def setUp(self):
        """Set up test fixtures with multiple teams to verify correct team isolation."""
        # Create two teams
        self.team1 = TeamFactory(name="Team Alpha")
        self.team2 = TeamFactory(name="Team Beta")

        # Create credentials and integrations for team1
        self.credential1 = IntegrationCredentialFactory(
            team=self.team1,
            provider="github",
            access_token="team1_token",
        )
        self.integration1 = GitHubIntegrationFactory(
            team=self.team1,
            credential=self.credential1,
        )
        self.tracked_repo1 = TrackedRepositoryFactory(
            team=self.team1,
            integration=self.integration1,
            full_name="team1-org/repo",
            is_active=True,
        )

        # Create credentials and integrations for team2
        self.credential2 = IntegrationCredentialFactory(
            team=self.team2,
            provider="github",
            access_token="team2_token",
        )
        self.integration2 = GitHubIntegrationFactory(
            team=self.team2,
            credential=self.credential2,
        )
        self.tracked_repo2 = TrackedRepositoryFactory(
            team=self.team2,
            integration=self.integration2,
            full_name="team2-org/repo",
            is_active=True,
        )

    @patch("apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task")
    @patch("apps.integrations._task_modules.github_sync.sync_full_history_task")
    @patch("apps.integrations._task_modules.github_sync._sync_with_graphql_or_rest")
    def test_dispatches_metrics_with_team1_id_for_team1_repo(self, mock_sync, mock_full_sync_task, mock_metrics_task):
        """Test that syncing team1's repo dispatches metrics for team1, not team2."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}
        mock_full_sync_delay = MagicMock()
        mock_full_sync_task.delay = mock_full_sync_delay
        mock_metrics_delay = MagicMock()
        mock_metrics_task.delay = mock_metrics_delay

        # Sync team1's repo
        sync_quick_data_task(self.tracked_repo1.id)

        # Verify metrics task was called with team1's ID specifically
        mock_metrics_delay.assert_called_once_with(self.team1.id)

    @patch("apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task")
    @patch("apps.integrations._task_modules.github_sync.sync_full_history_task")
    @patch("apps.integrations._task_modules.github_sync._sync_with_graphql_or_rest")
    def test_dispatches_metrics_with_team2_id_for_team2_repo(self, mock_sync, mock_full_sync_task, mock_metrics_task):
        """Test that syncing team2's repo dispatches metrics for team2, not team1."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}
        mock_full_sync_delay = MagicMock()
        mock_full_sync_task.delay = mock_full_sync_delay
        mock_metrics_delay = MagicMock()
        mock_metrics_task.delay = mock_metrics_delay

        # Sync team2's repo
        sync_quick_data_task(self.tracked_repo2.id)

        # Verify metrics task was called with team2's ID specifically
        mock_metrics_delay.assert_called_once_with(self.team2.id)
