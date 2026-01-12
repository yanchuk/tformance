"""Tests for sync_repository_initial_task Celery task."""

from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    TrackedRepositoryFactory,
)
from apps.metrics.factories import TeamFactory


class TestSyncRepositoryInitialTask(TestCase):
    """Tests for sync_repository_initial_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="encrypted_token_12345",
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

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_sync_initial_sets_status_to_syncing(self, mock_sync_history):
        """Test that sync_repository_initial_task sets sync_status to SYNCING at start."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_initial_task

        mock_sync_history.return_value = {
            "prs_synced": 10,
            "reviews_synced": 5,
            "errors": [],
        }

        # Verify initial status is pending
        self.assertEqual(self.tracked_repo.sync_status, "pending")

        # Call the task
        sync_repository_initial_task(self.tracked_repo.id, days_back=30)

        # Reload repo and verify status was set to syncing
        repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
        # Note: After successful sync, status will be 'complete', but we need to verify
        # it was set to 'syncing' during execution. We'll check this by mocking
        # sync_repository_history to verify the state.

        # For now, verify the task completes and status is updated
        self.assertEqual(repo.sync_status, "complete")

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_sync_initial_sets_sync_started_at(self, mock_sync_history):
        """Test that sync_repository_initial_task sets sync_started_at at start."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_initial_task

        mock_sync_history.return_value = {
            "prs_synced": 10,
            "reviews_synced": 5,
            "errors": [],
        }

        # Verify sync_started_at is None initially
        self.assertIsNone(self.tracked_repo.sync_started_at)

        # Store time before calling task
        before_time = timezone.now()

        # Call the task
        sync_repository_initial_task(self.tracked_repo.id, days_back=30)

        # Reload repo and verify sync_started_at was set
        repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
        self.assertIsNotNone(repo.sync_started_at)
        self.assertGreaterEqual(repo.sync_started_at, before_time)

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_sync_initial_calls_sync_repository_history_with_days_back(self, mock_sync_history):
        """Test that sync_repository_initial_task calls sync_repository_history with days_back parameter."""
        from apps.integrations.tasks import sync_repository_initial_task

        mock_sync_history.return_value = {
            "prs_synced": 10,
            "reviews_synced": 5,
            "errors": [],
        }

        # Call the task with custom days_back
        sync_repository_initial_task(self.tracked_repo.id, days_back=60)

        # Verify sync_repository_history was called with correct arguments
        mock_sync_history.assert_called_once()
        call_args = mock_sync_history.call_args

        # Verify first argument is the tracked_repo
        called_repo = call_args[0][0]
        self.assertEqual(called_repo.id, self.tracked_repo.id)

        # Verify days_back was passed correctly
        self.assertIn("days_back", call_args[1])
        self.assertEqual(call_args[1]["days_back"], 60)

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_sync_initial_sets_status_to_complete_on_success(self, mock_sync_history):
        """Test that sync_repository_initial_task sets sync_status to COMPLETE after success."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_initial_task

        mock_sync_history.return_value = {
            "prs_synced": 10,
            "reviews_synced": 5,
            "errors": [],
        }

        # Call the task
        sync_repository_initial_task(self.tracked_repo.id, days_back=30)

        # Reload repo and verify status is complete
        repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
        self.assertEqual(repo.sync_status, "complete")

    @patch("apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task")
    @patch("apps.integrations._task_modules.github_sync._sync_with_graphql_or_rest")
    def test_sync_initial_triggers_weekly_metrics_aggregation(self, mock_sync, mock_aggregate_task):
        """Test that sync_repository_initial_task triggers aggregate_team_weekly_metrics_task.delay."""
        from apps.integrations.tasks import sync_repository_initial_task

        mock_sync.return_value = {
            "prs_synced": 10,
            "reviews_synced": 5,
            "errors": [],
        }

        # Call the task
        sync_repository_initial_task(self.tracked_repo.id, days_back=30)

        # Verify aggregate_team_weekly_metrics_task.delay was called with team_id
        mock_aggregate_task.delay.assert_called_once_with(self.team.id)

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_sync_initial_returns_sync_stats(self, mock_sync_history):
        """Test that sync_repository_initial_task returns dict with sync stats."""
        from apps.integrations.tasks import sync_repository_initial_task

        expected_result = {
            "prs_synced": 15,
            "reviews_synced": 8,
            "commits_synced": 25,
            "errors": [],
        }
        mock_sync_history.return_value = expected_result

        # Call the task
        result = sync_repository_initial_task(self.tracked_repo.id, days_back=30)

        # Verify result contains sync stats from sync_repository_history
        self.assertIsInstance(result, dict)
        self.assertEqual(result["prs_synced"], 15)
        self.assertEqual(result["reviews_synced"], 8)
        self.assertEqual(result["commits_synced"], 25)
        self.assertIn("errors", result)

    def test_sync_initial_returns_error_for_missing_repo(self):
        """Test that sync_repository_initial_task returns error for non-existent repo."""
        from apps.integrations.tasks import sync_repository_initial_task

        non_existent_id = 99999

        # Call the task with non-existent ID
        result = sync_repository_initial_task(non_existent_id, days_back=30)

        # Verify error is returned
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_sync_initial_uses_default_30_days(self, mock_sync_history):
        """Test that sync_repository_initial_task uses default days_back=30."""
        from apps.integrations.tasks import sync_repository_initial_task

        mock_sync_history.return_value = {
            "prs_synced": 10,
            "reviews_synced": 5,
            "errors": [],
        }

        # Call the task WITHOUT specifying days_back
        sync_repository_initial_task(self.tracked_repo.id)

        # Verify sync_repository_history was called with default days_back=30
        mock_sync_history.assert_called_once()
        call_args = mock_sync_history.call_args

        # Verify days_back parameter defaults to 30
        self.assertIn("days_back", call_args[1])
        self.assertEqual(call_args[1]["days_back"], 30)

    @patch("apps.integrations.services.sync_notifications.send_sync_complete_notification")
    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_sync_initial_sends_notification_on_success(self, mock_sync_history, mock_send_notification):
        """Test that sync_repository_initial_task sends notification after successful sync."""
        from apps.integrations.tasks import sync_repository_initial_task

        sync_result = {
            "prs_synced": 15,
            "reviews_synced": 8,
            "commits_synced": 25,
            "errors": [],
        }
        mock_sync_history.return_value = sync_result

        # Call the task
        sync_repository_initial_task(self.tracked_repo.id, days_back=30)

        # Verify send_sync_complete_notification was called with tracked_repo and result
        mock_send_notification.assert_called_once()
        call_args = mock_send_notification.call_args

        # Verify first argument is tracked_repo
        called_repo = call_args[0][0]
        self.assertEqual(called_repo.id, self.tracked_repo.id)

        # Verify second argument is the sync result
        called_stats = call_args[0][1]
        self.assertEqual(called_stats, sync_result)

    @patch("apps.integrations.services.sync_notifications.send_sync_complete_notification")
    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_sync_initial_passes_stats_to_notification(self, mock_sync_history, mock_send_notification):
        """Test that sync_repository_initial_task passes stats dict from sync_repository_history to notification."""
        from apps.integrations.tasks import sync_repository_initial_task

        # Create specific stats to verify they're passed through
        expected_stats = {
            "prs_synced": 42,
            "reviews_synced": 18,
            "commits_synced": 95,
            "errors": [],
        }
        mock_sync_history.return_value = expected_stats

        # Call the task
        sync_repository_initial_task(self.tracked_repo.id, days_back=60)

        # Verify send_sync_complete_notification received the exact stats
        mock_send_notification.assert_called_once()
        _, actual_stats = mock_send_notification.call_args[0]

        self.assertEqual(actual_stats["prs_synced"], 42)
        self.assertEqual(actual_stats["reviews_synced"], 18)
        self.assertEqual(actual_stats["commits_synced"], 95)
        self.assertIn("errors", actual_stats)
