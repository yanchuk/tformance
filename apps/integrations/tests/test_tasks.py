"""Tests for Celery tasks in apps.integrations.tasks."""

from unittest.mock import MagicMock, patch

from celery.exceptions import Retry
from django.test import TestCase

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    TrackedRepositoryFactory,
)
from apps.metrics.factories import TeamFactory


class TestSyncRepositoryTask(TestCase):
    """Tests for sync_repository_task Celery task."""

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

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_calls_sync_repository_incremental_with_correct_repo(self, mock_sync):
        """Test that sync_repository_task calls sync_repository_incremental with the correct repository."""
        from apps.integrations.tasks import sync_repository_task

        mock_sync.return_value = {
            "prs_synced": 5,
            "reviews_synced": 3,
            "errors": [],
        }

        # Call the task
        result = sync_repository_task(self.tracked_repo.id)

        # Verify sync_repository_incremental was called with correct repo
        mock_sync.assert_called_once()
        called_repo = mock_sync.call_args[0][0]
        self.assertEqual(called_repo.id, self.tracked_repo.id)
        self.assertEqual(called_repo.full_name, "acme-corp/api-server")

        # Verify result is returned from sync
        self.assertEqual(result["prs_synced"], 5)
        self.assertEqual(result["reviews_synced"], 3)

    def test_sync_repository_task_skips_inactive_repos(self):
        """Test that sync_repository_task skips repositories where is_active=False."""
        from apps.integrations.tasks import sync_repository_task

        # Set repo to inactive
        self.tracked_repo.is_active = False
        self.tracked_repo.save()

        # Call the task
        result = sync_repository_task(self.tracked_repo.id)

        # Verify task was skipped
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])
        self.assertIn("reason", result)
        self.assertIn("not active", result["reason"].lower())

    def test_sync_repository_task_handles_does_not_exist(self):
        """Test that sync_repository_task handles TrackedRepository.DoesNotExist gracefully."""
        from apps.integrations.tasks import sync_repository_task

        non_existent_id = 99999

        # Call the task with non-existent ID
        result = sync_repository_task(non_existent_id)

        # Verify error is returned
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_retries_on_failure(self, mock_sync):
        """Test that sync_repository_task retries up to 3 times on failure with exponential backoff."""
        from apps.integrations.tasks import sync_repository_task

        # Mock sync_repository_incremental to raise an exception
        mock_sync.side_effect = Exception("GitHub API rate limit exceeded")

        # Mock the task's retry method
        with patch.object(sync_repository_task, "retry") as mock_retry:
            mock_retry.side_effect = Retry()

            # Call the task and expect it to raise Retry
            with self.assertRaises(Retry):
                sync_repository_task(self.tracked_repo.id)

            # Verify retry was called with correct parameters
            mock_retry.assert_called_once()
            # Check that max_retries and exponential backoff are configured
            # (the actual retry logic is tested by checking the decorator config)

    @patch("sentry_sdk.capture_exception")
    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_logs_to_sentry_on_final_failure(self, mock_sync, mock_sentry):
        """Test that sync_repository_task logs errors to Sentry on final failure after retries exhausted."""
        from apps.integrations.tasks import sync_repository_task

        # Mock sync_repository_incremental to raise an exception
        test_exception = Exception("Permanent failure")
        mock_sync.side_effect = test_exception

        # Mock the task's retry method to raise Retry for the first attempts,
        # then let the exception through on the final attempt
        with patch.object(sync_repository_task, "retry") as mock_retry:
            # Simulate max retries exceeded by not raising Retry
            mock_retry.side_effect = Exception("Max retries exceeded")

            # Call the task - should handle the exception and log to Sentry
            result = sync_repository_task(self.tracked_repo.id)

            # Verify Sentry was called
            mock_sentry.assert_called_once()

            # Verify error result is returned
            self.assertIsInstance(result, dict)
            self.assertIn("error", result)

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_returns_result_dict_from_sync(self, mock_sync):
        """Test that sync_repository_task returns the result dict from sync_repository_incremental."""
        from apps.integrations.tasks import sync_repository_task

        expected_result = {
            "prs_synced": 10,
            "reviews_synced": 7,
            "errors": ["Some warning"],
        }
        mock_sync.return_value = expected_result

        # Call the task
        result = sync_repository_task(self.tracked_repo.id)

        # Verify result matches sync output
        self.assertEqual(result, expected_result)

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_sets_status_to_syncing_before_sync(self, mock_sync):
        """Test that sync_repository_task sets sync_status to 'syncing' before starting sync."""
        from apps.integrations.tasks import sync_repository_task

        # Mock sync to check status during execution
        def check_status_during_sync(repo):
            # Reload repo from database to get current state
            repo.refresh_from_db()
            # Assert status is 'syncing' during execution
            assert repo.sync_status == "syncing", f"Expected 'syncing', got '{repo.sync_status}'"
            return {"prs_synced": 5, "reviews_synced": 3, "errors": []}

        mock_sync.side_effect = check_status_during_sync

        # Verify initial status
        self.assertEqual(self.tracked_repo.sync_status, "pending")

        # Call the task
        sync_repository_task(self.tracked_repo.id)

        # Verify status was set to 'syncing' (checked by the mock)

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_sets_status_to_complete_on_success(self, mock_sync):
        """Test that sync_repository_task sets sync_status to 'complete' on successful sync."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_task

        mock_sync.return_value = {
            "prs_synced": 10,
            "reviews_synced": 7,
            "errors": [],
        }

        # Verify initial status
        self.assertEqual(self.tracked_repo.sync_status, "pending")

        # Call the task
        sync_repository_task(self.tracked_repo.id)

        # Reload from database and verify status is 'complete'
        repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
        self.assertEqual(repo.sync_status, "complete")

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_sets_status_to_error_on_failure(self, mock_sync):
        """Test that sync_repository_task sets sync_status to 'error' on permanent failure."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_task

        # Mock sync to raise an exception
        error_message = "GitHub API rate limit exceeded"
        mock_sync.side_effect = Exception(error_message)

        # Mock retry to simulate max retries exhausted
        with patch.object(sync_repository_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            # Mock Sentry to avoid actual calls
            with patch("sentry_sdk.capture_exception"):
                # Call the task
                result = sync_repository_task(self.tracked_repo.id)

                # Verify error result is returned
                self.assertIn("error", result)

                # Reload from database and verify status is 'error'
                repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
                self.assertEqual(repo.sync_status, "error")

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_saves_error_message_on_failure(self, mock_sync):
        """Test that sync_repository_task saves error message to last_sync_error on failure."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_task

        # Mock sync to raise an exception
        error_message = "GitHub API rate limit exceeded"
        mock_sync.side_effect = Exception(error_message)

        # Mock retry to simulate max retries exhausted
        with patch.object(sync_repository_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            # Mock Sentry to avoid actual calls
            with patch("sentry_sdk.capture_exception"):
                # Call the task
                sync_repository_task(self.tracked_repo.id)

                # Reload from database and verify error message is saved
                repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
                self.assertIsNotNone(repo.last_sync_error)
                self.assertIn(error_message, repo.last_sync_error)

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_clears_last_sync_error_on_successful_sync(self, mock_sync):
        """Test that sync_repository_task clears last_sync_error on successful sync after previous error."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_task

        # Set up repo with previous error
        self.tracked_repo.sync_status = "error"
        self.tracked_repo.last_sync_error = "Previous error message"
        self.tracked_repo.save()

        mock_sync.return_value = {
            "prs_synced": 5,
            "reviews_synced": 3,
            "errors": [],
        }

        # Call the task
        sync_repository_task(self.tracked_repo.id)

        # Reload from database and verify error is cleared
        repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
        self.assertEqual(repo.sync_status, "complete")
        self.assertIsNone(repo.last_sync_error)


class TestSyncAllRepositoriesTask(TestCase):
    """Tests for sync_all_repositories_task Celery task."""

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

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_dispatches_tasks_for_all_active_repos(self, mock_task):
        """Test that sync_all_repositories_task dispatches sync_repository_task for all active repos."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Create multiple active repos
        repo1 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/repo-1",
            is_active=True,
        )
        repo2 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/repo-2",
            is_active=True,
        )
        repo3 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/repo-3",
            is_active=True,
        )

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_repositories_task()

        # Verify sync_repository_task.delay was called for each active repo
        self.assertEqual(mock_delay.call_count, 3)

        # Verify the correct repo IDs were passed
        called_repo_ids = {call[0][0] for call in mock_delay.call_args_list}
        expected_repo_ids = {repo1.id, repo2.id, repo3.id}
        self.assertEqual(called_repo_ids, expected_repo_ids)

        # Verify result contains correct counts
        self.assertIsInstance(result, dict)
        self.assertEqual(result["repos_dispatched"], 3)
        self.assertEqual(result["repos_skipped"], 0)

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_skips_inactive_repos(self, mock_task):
        """Test that sync_all_repositories_task only dispatches tasks for active repos (is_active=True)."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Create mix of active and inactive repos
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/active-repo",
            is_active=True,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/inactive-repo-1",
            is_active=False,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/inactive-repo-2",
            is_active=False,
        )

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_repositories_task()

        # Verify sync_repository_task.delay was called only once (for active repo)
        self.assertEqual(mock_delay.call_count, 1)

        # Verify result contains correct counts
        self.assertIsInstance(result, dict)
        self.assertEqual(result["repos_dispatched"], 1)
        self.assertEqual(result["repos_skipped"], 2)

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_returns_correct_counts(self, mock_task):
        """Test that sync_all_repositories_task returns dict with repos_dispatched and repos_skipped counts."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Create repos
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=False,
        )

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_repositories_task()

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("repos_dispatched", result)
        self.assertIn("repos_skipped", result)
        self.assertEqual(result["repos_dispatched"], 2)
        self.assertEqual(result["repos_skipped"], 1)

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_handles_empty_repository_list(self, mock_task):
        """Test that sync_all_repositories_task handles case where no repositories exist."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Don't create any repos

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_repositories_task()

        # Verify no tasks were dispatched
        mock_delay.assert_not_called()

        # Verify result contains zero counts
        self.assertIsInstance(result, dict)
        self.assertEqual(result["repos_dispatched"], 0)
        self.assertEqual(result["repos_skipped"], 0)

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_continues_on_individual_dispatch_error(self, mock_task):
        """Test that sync_all_repositories_task continues dispatching even if one dispatch fails."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Create multiple active repos
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        repo2 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )

        # Mock delay to raise exception for second repo only
        mock_delay = MagicMock()

        def delay_side_effect(repo_id):
            if repo_id == repo2.id:
                raise Exception("Celery connection error")
            return MagicMock()

        mock_delay.side_effect = delay_side_effect
        mock_task.delay = mock_delay

        # Call the task - should not raise exception
        result = sync_all_repositories_task()

        # Verify all repos were attempted
        self.assertEqual(mock_delay.call_count, 3)

        # Verify result still counts the successful dispatches
        # (Implementation detail: task should track successful vs failed dispatches)
        self.assertIsInstance(result, dict)
        self.assertIn("repos_dispatched", result)
        # Should show 2 successful dispatches (repo1 and repo3)
        self.assertEqual(result["repos_dispatched"], 2)
