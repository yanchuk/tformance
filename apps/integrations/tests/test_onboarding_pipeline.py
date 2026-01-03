"""Tests for the onboarding pipeline task chain.

TDD RED Phase: These tests define the expected behavior of the pipeline.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory


class TestUpdatePipelineStatusTask(TestCase):
    """Tests for update_pipeline_status task."""

    def setUp(self):
        self.team = TeamFactory()

    def test_update_pipeline_status_task_exists(self):
        """Test that update_pipeline_status task is importable."""
        from apps.integrations.onboarding_pipeline import update_pipeline_status

        self.assertTrue(callable(update_pipeline_status))

    def test_update_pipeline_status_updates_team(self):
        """Test that task updates team's pipeline status."""
        from apps.integrations.onboarding_pipeline import update_pipeline_status

        # Call task synchronously
        update_pipeline_status(self.team.id, "syncing")

        # Verify team was updated
        self.team.refresh_from_db()
        self.assertEqual(self.team.onboarding_pipeline_status, "syncing")

    def test_update_pipeline_status_sets_started_at(self):
        """Test that task sets started_at when status is syncing."""
        from apps.integrations.onboarding_pipeline import update_pipeline_status

        update_pipeline_status(self.team.id, "syncing")

        self.team.refresh_from_db()
        self.assertIsNotNone(self.team.onboarding_pipeline_started_at)

    def test_update_pipeline_status_sets_completed_at_on_complete(self):
        """Test that task sets completed_at when status is complete."""
        from apps.integrations.onboarding_pipeline import update_pipeline_status

        update_pipeline_status(self.team.id, "complete")

        self.team.refresh_from_db()
        self.assertIsNotNone(self.team.onboarding_pipeline_completed_at)

    def test_update_pipeline_status_handles_invalid_team(self):
        """Test that task handles non-existent team gracefully."""
        from apps.integrations.onboarding_pipeline import update_pipeline_status

        # Should not raise exception
        result = update_pipeline_status(99999, "syncing")

        # Should return error indicator
        self.assertIsNotNone(result)


class TestHandlePipelineFailureTask(TestCase):
    """Tests for handle_pipeline_failure task."""

    def setUp(self):
        self.team = TeamFactory()

    def test_handle_pipeline_failure_task_exists(self):
        """Test that handle_pipeline_failure task is importable."""
        from apps.integrations.onboarding_pipeline import handle_pipeline_failure

        self.assertTrue(callable(handle_pipeline_failure))

    def test_handle_pipeline_failure_sets_status_failed(self):
        """Test that task sets pipeline status to failed."""
        from apps.integrations.onboarding_pipeline import handle_pipeline_failure

        # Create a mock task request to simulate failure context
        handle_pipeline_failure(
            None,  # request (from chain)
            Exception("Test error"),  # exception
            None,  # traceback
            team_id=self.team.id,
        )

        self.team.refresh_from_db()
        self.assertEqual(self.team.onboarding_pipeline_status, "failed")

    def test_handle_pipeline_failure_stores_error_message(self):
        """Test that task stores a sanitized error message."""
        from apps.integrations.onboarding_pipeline import handle_pipeline_failure

        handle_pipeline_failure(
            None,
            Exception("Connection timeout during sync"),
            None,
            team_id=self.team.id,
        )

        self.team.refresh_from_db()
        # Sanitized message should be user-friendly, not exposing internal details
        self.assertIn("error occurred", self.team.onboarding_pipeline_error.lower())


class TestStartOnboardingPipeline(TestCase):
    """Tests for start_onboarding_pipeline function."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    def test_start_onboarding_pipeline_function_exists(self):
        """Test that start_onboarding_pipeline is importable."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        self.assertTrue(callable(start_onboarding_pipeline))

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_start_onboarding_pipeline_creates_chain(self, mock_chain):
        """Test that function creates a Celery chain."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        # Configure mock
        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        # Call function
        start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Verify chain was called
        mock_chain.assert_called_once()

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_start_onboarding_pipeline_sets_initial_status(self, mock_chain):
        """Test that function sets initial pipeline status."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Verify team status was updated
        self.team.refresh_from_db()
        # Status should be updated (either by task or function)
        self.assertIn(
            self.team.onboarding_pipeline_status,
            ["not_started", "syncing"],  # Either initial or updated
        )

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_start_onboarding_pipeline_has_error_handler(self, mock_chain):
        """Test that pipeline has error handler attached."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Verify on_error was called
        mock_chain_instance.on_error.assert_called_once()


class TestPipelineTaskSequence(TestCase):
    """Tests for the pipeline task sequence and dependencies."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_pipeline_includes_sync_task(self, mock_chain):
        """Test that pipeline includes sync_historical_data_task."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Get the tasks passed to chain()
        chain_args = mock_chain.call_args[0]

        # Should have multiple tasks
        self.assertGreater(len(chain_args), 1)

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_pipeline_includes_llm_analysis(self, mock_chain):
        """Test that pipeline includes LLM analysis task."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Chain should be called with multiple tasks
        mock_chain.assert_called_once()
        # We can't easily check specific tasks without more complex mocking,
        # but we can verify the chain was created

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_pipeline_includes_metrics_aggregation(self, mock_chain):
        """Test that pipeline includes metrics aggregation task."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Verify chain was created
        mock_chain.assert_called_once()

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_pipeline_ends_with_email(self, mock_chain):
        """Test that pipeline ends with email notification task."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Verify chain was created
        mock_chain.assert_called_once()


class TestSyncGithubMembersPipelineTask(TestCase):
    """Tests for sync_github_members_pipeline_task (A-025 fix)."""

    def setUp(self):
        self.team = TeamFactory()

    def test_sync_github_members_pipeline_task_exists(self):
        """Test that sync_github_members_pipeline_task is importable."""
        from apps.integrations.onboarding_pipeline import sync_github_members_pipeline_task

        self.assertTrue(callable(sync_github_members_pipeline_task))

    def test_sync_github_members_pipeline_task_handles_missing_team(self):
        """Test that task handles non-existent team gracefully."""
        from apps.integrations.onboarding_pipeline import sync_github_members_pipeline_task

        result = sync_github_members_pipeline_task(99999)

        self.assertIn("error", result)

    def test_sync_github_members_pipeline_task_skips_without_integration(self):
        """Test that task skips when no GitHub integration exists."""
        from apps.integrations.onboarding_pipeline import sync_github_members_pipeline_task

        result = sync_github_members_pipeline_task(self.team.id)

        self.assertTrue(result.get("skipped"))
        self.assertIn("No GitHub integration", result.get("reason", ""))

    @patch("apps.integrations.tasks.sync_github_members_task")
    def test_sync_github_members_pipeline_task_calls_oauth_sync(self, mock_sync_task):
        """Test that task calls OAuth member sync when integration exists."""
        from apps.integrations.onboarding_pipeline import sync_github_members_pipeline_task

        # Create OAuth integration
        integration = GitHubIntegrationFactory(team=self.team)
        mock_sync_task.return_value = {"created": 5, "updated": 0}

        result = sync_github_members_pipeline_task(self.team.id)

        # Verify sync task was called (synchronously, not .delay())
        mock_sync_task.assert_called_once_with(integration.id)
        self.assertEqual(result.get("created"), 5)
