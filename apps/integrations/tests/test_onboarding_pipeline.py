"""Tests for the onboarding pipeline task chain.

TDD RED Phase: These tests define the expected behavior of the pipeline.
"""

from unittest.mock import patch

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
    """Tests for start_onboarding_pipeline function (signal-based)."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    def test_start_onboarding_pipeline_function_exists(self):
        """Test that start_onboarding_pipeline is importable."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        self.assertTrue(callable(start_onboarding_pipeline))

    @patch("apps.integrations.pipeline_signals.dispatch_pipeline_task")
    def test_start_onboarding_pipeline_sets_status_syncing_members(self, mock_dispatch):
        """Test that function sets status to syncing_members to start pipeline."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        # Call function
        result = start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Verify team status was updated to syncing_members
        self.team.refresh_from_db()
        self.assertEqual(self.team.onboarding_pipeline_status, "syncing_members")

        # Verify result is a dict (not AsyncResult)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "started")
        self.assertEqual(result["execution_mode"], "signal_based")

    @patch("apps.integrations.pipeline_signals.dispatch_pipeline_task")
    def test_start_onboarding_pipeline_triggers_signal(self, mock_dispatch):
        """Test that updating status triggers signal dispatch."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Signal should have dispatched the first task
        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args
        self.assertEqual(call_args[0][0], self.team.id)
        self.assertEqual(call_args[0][1], "syncing_members")

    def test_start_onboarding_pipeline_handles_missing_team(self):
        """Test that function handles non-existent team gracefully."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        result = start_onboarding_pipeline(99999, [self.repo.id])

        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["error"])


class TestPipelineTaskSequence(TestCase):
    """Tests for the signal-based pipeline state machine configuration."""

    def test_state_machine_includes_sync_task(self):
        """Test that state machine maps syncing → sync_historical_data_task."""
        from apps.integrations.pipeline_signals import PIPELINE_STATE_MACHINE

        self.assertIn("syncing", PIPELINE_STATE_MACHINE)
        config = PIPELINE_STATE_MACHINE["syncing"]
        self.assertEqual(config["task_path"], "apps.integrations.tasks.sync_historical_data_task")

    def test_state_machine_includes_llm_analysis(self):
        """Test that state machine maps llm_processing → LLM task."""
        from apps.integrations.pipeline_signals import PIPELINE_STATE_MACHINE

        self.assertIn("llm_processing", PIPELINE_STATE_MACHINE)
        config = PIPELINE_STATE_MACHINE["llm_processing"]
        self.assertIn("llm", config["task_path"].lower())

    def test_state_machine_includes_metrics_aggregation(self):
        """Test that state machine maps computing_metrics → aggregation task."""
        from apps.integrations.pipeline_signals import PIPELINE_STATE_MACHINE

        self.assertIn("computing_metrics", PIPELINE_STATE_MACHINE)
        config = PIPELINE_STATE_MACHINE["computing_metrics"]
        self.assertIn("aggregate", config["task_path"].lower())

    def test_state_machine_includes_insights(self):
        """Test that state machine maps computing_insights → insights task."""
        from apps.integrations.pipeline_signals import PIPELINE_STATE_MACHINE

        self.assertIn("computing_insights", PIPELINE_STATE_MACHINE)
        config = PIPELINE_STATE_MACHINE["computing_insights"]
        self.assertIn("insights", config["task_path"].lower())

    def test_phase2_state_machine_includes_background_sync(self):
        """Test that Phase 2 state machine includes background syncing."""
        from apps.integrations.pipeline_signals import PHASE2_STATE_MACHINE

        self.assertIn("background_syncing", PHASE2_STATE_MACHINE)

    def test_phase2_state_machine_includes_background_llm(self):
        """Test that Phase 2 state machine includes background LLM."""
        from apps.integrations.pipeline_signals import PHASE2_STATE_MACHINE

        self.assertIn("background_llm", PHASE2_STATE_MACHINE)

    def test_terminal_states_defined(self):
        """Test that terminal states are properly defined."""
        from apps.integrations.pipeline_signals import TERMINAL_STATES

        self.assertIn("complete", TERMINAL_STATES)
        self.assertIn("failed", TERMINAL_STATES)


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
