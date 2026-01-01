"""Tests for Two-Phase Onboarding pipeline orchestration.

TDD RED Phase: These tests define the expected behavior of the two-phase pipeline.

Two-Phase Onboarding:
- Phase 1: sync 30 days → LLM ALL PRs → metrics → insights → phase1_complete
- Phase 2: sync 31-90 days → LLM remaining PRs → complete (background)
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.factories import TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory


class TestStartPhase1PipelineExists(TestCase):
    """Tests for start_phase1_pipeline function existence."""

    def test_start_phase1_pipeline_function_exists(self):
        """Test that start_phase1_pipeline is importable."""
        from apps.integrations.onboarding_pipeline import start_phase1_pipeline

        self.assertTrue(callable(start_phase1_pipeline))


class TestPhase1PipelineSync(TestCase):
    """Tests for Phase 1 sync behavior (30 days only)."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.chain")
    @patch("apps.integrations.tasks.sync_historical_data_task")
    def test_phase1_uses_30_day_sync(self, mock_sync_task, mock_chain):
        """Phase 1 should sync only 30 days of data for quick start."""
        from apps.integrations.onboarding_pipeline import start_phase1_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance
        mock_sync_task.si = MagicMock()

        start_phase1_pipeline(self.team.id, [self.repo.id])

        # Verify sync_historical_data_task.si was called with days_back=30
        mock_sync_task.si.assert_called()
        call_kwargs = mock_sync_task.si.call_args[1]
        self.assertEqual(call_kwargs.get("days_back"), 30)


class TestPhase1PipelineLLM(TestCase):
    """Tests for Phase 1 LLM behavior (process ALL PRs)."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.chain")
    @patch("apps.metrics.tasks.run_llm_analysis_batch")
    def test_phase1_processes_all_synced_prs(self, mock_llm_task, mock_chain):
        """Phase 1 should use limit=None to process ALL synced PRs."""
        from apps.integrations.onboarding_pipeline import start_phase1_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance
        mock_llm_task.si = MagicMock()

        start_phase1_pipeline(self.team.id, [self.repo.id])

        # Verify run_llm_analysis_batch.si was called with limit=None
        mock_llm_task.si.assert_called()
        call_kwargs = mock_llm_task.si.call_args[1]
        self.assertIsNone(call_kwargs.get("limit"))


class TestPhase1PipelineStatus(TestCase):
    """Tests for Phase 1 status transitions."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_phase1_ends_with_phase1_complete_status(self, mock_chain):
        """Phase 1 should end with 'phase1_complete' status, not 'complete'."""
        from apps.integrations.onboarding_pipeline import start_phase1_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        start_phase1_pipeline(self.team.id, [self.repo.id])

        # Verify chain was called
        mock_chain.assert_called_once()

        # Get all tasks in chain and check for phase1_complete status update
        chain_args = mock_chain.call_args[0]
        # Chain should include status update to 'phase1_complete'
        status_updates = [str(arg) for arg in chain_args if "update_pipeline_status" in str(arg)]
        self.assertTrue(
            any("phase1_complete" in status for status in status_updates),
            f"Expected phase1_complete status in chain, got: {status_updates}",
        )


class TestPhase1PipelineDispatchPhase2(TestCase):
    """Tests for Phase 1 dispatching Phase 2."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_phase1_dispatches_phase2(self, mock_chain):
        """Phase 1 should dispatch Phase 2 after completing."""
        from apps.integrations.onboarding_pipeline import start_phase1_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        start_phase1_pipeline(self.team.id, [self.repo.id])

        # Verify chain was called
        mock_chain.assert_called_once()

        # Chain should include dispatch_phase2_pipeline task
        chain_args = mock_chain.call_args[0]
        task_names = [str(arg) for arg in chain_args]
        self.assertTrue(
            any("dispatch_phase2" in name for name in task_names),
            f"Expected dispatch_phase2 task in chain, got: {task_names}",
        )


class TestDispatchPhase2PipelineExists(TestCase):
    """Tests for dispatch_phase2_pipeline task existence."""

    def test_dispatch_phase2_pipeline_task_exists(self):
        """Test that dispatch_phase2_pipeline is importable."""
        from apps.integrations.onboarding_pipeline import dispatch_phase2_pipeline

        self.assertTrue(callable(dispatch_phase2_pipeline))


class TestPhase2PipelineSync(TestCase):
    """Tests for Phase 2 sync behavior (31-90 days)."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.chain")
    @patch("apps.integrations.tasks.sync_historical_data_task")
    def test_phase2_syncs_days_31_to_90(self, mock_sync_task, mock_chain):
        """Phase 2 should sync days 31-90 (skip recent 30 days)."""
        from apps.integrations.onboarding_pipeline import run_phase2_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance
        mock_sync_task.si = MagicMock()

        run_phase2_pipeline(self.team.id, [self.repo.id])

        # Verify sync_historical_data_task.si was called with days_back=90, skip_recent=30
        mock_sync_task.si.assert_called()
        call_kwargs = mock_sync_task.si.call_args[1]
        self.assertEqual(call_kwargs.get("days_back"), 90)
        self.assertEqual(call_kwargs.get("skip_recent"), 30)


class TestPhase2PipelineStatus(TestCase):
    """Tests for Phase 2 status transitions."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_phase2_sets_background_syncing_status(self, mock_chain):
        """Phase 2 should set 'background_syncing' status during sync."""
        from apps.integrations.onboarding_pipeline import run_phase2_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        run_phase2_pipeline(self.team.id, [self.repo.id])

        chain_args = mock_chain.call_args[0]
        status_updates = [str(arg) for arg in chain_args]
        self.assertTrue(
            any("background_syncing" in status for status in status_updates),
            f"Expected background_syncing status, got: {status_updates}",
        )

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_phase2_ends_with_complete_status(self, mock_chain):
        """Phase 2 should end with 'complete' status."""
        from apps.integrations.onboarding_pipeline import run_phase2_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        run_phase2_pipeline(self.team.id, [self.repo.id])

        chain_args = mock_chain.call_args[0]
        status_updates = [str(arg) for arg in chain_args]
        # Should have 'complete' as the final status
        self.assertTrue(
            any("'complete'" in status for status in status_updates),
            f"Expected complete status, got: {status_updates}",
        )


class TestStartOnboardingPipelineRouting(TestCase):
    """Tests for start_onboarding_pipeline routing to Phase 1."""

    def setUp(self):
        self.team = TeamFactory()
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.start_phase1_pipeline")
    def test_start_onboarding_pipeline_calls_phase1(self, mock_phase1):
        """start_onboarding_pipeline should delegate to start_phase1_pipeline."""
        from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

        mock_phase1.return_value = MagicMock()

        start_onboarding_pipeline(self.team.id, [self.repo.id])

        # Should call start_phase1_pipeline
        mock_phase1.assert_called_once_with(self.team.id, [self.repo.id])


class TestPhase1ErrorHandling(TestCase):
    """Tests for Phase 1 pipeline failure behavior."""

    def setUp(self):
        self.team = TeamFactory(onboarding_pipeline_status="syncing")
        self.repo = TrackedRepositoryFactory(team=self.team)

    def test_phase1_failure_sets_status_to_failed(self):
        """Phase 1 failure should set team status to 'failed'."""
        from apps.integrations.onboarding_pipeline import handle_pipeline_failure

        # Simulate Phase 1 failure
        handle_pipeline_failure(
            request=MagicMock(),
            exc=Exception("Sync failed"),
            traceback=None,
            team_id=self.team.id,
        )

        self.team.refresh_from_db()
        self.assertEqual(self.team.onboarding_pipeline_status, "failed")

    def test_phase1_failure_blocks_dashboard_access(self):
        """Phase 1 failure should block dashboard access."""
        from apps.integrations.onboarding_pipeline import handle_pipeline_failure

        # Simulate Phase 1 failure
        handle_pipeline_failure(
            request=MagicMock(),
            exc=Exception("LLM analysis failed"),
            traceback=None,
            team_id=self.team.id,
        )

        self.team.refresh_from_db()
        self.assertFalse(self.team.dashboard_accessible)

    def test_phase1_failure_stores_error_message(self):
        """Phase 1 failure should store sanitized error message for display."""
        from apps.integrations.onboarding_pipeline import handle_pipeline_failure

        handle_pipeline_failure(
            request=MagicMock(),
            exc=Exception("Some internal error"),
            traceback=None,
            team_id=self.team.id,
        )

        self.team.refresh_from_db()
        # Error is sanitized for security - should have generic message
        self.assertIsNotNone(self.team.onboarding_pipeline_error)
        self.assertTrue(len(self.team.onboarding_pipeline_error) > 0)


class TestPhase2ErrorHandling(TestCase):
    """Tests for Phase 2 pipeline failure behavior.

    Phase 2 failures should NOT affect dashboard access since
    Phase 1 already completed successfully.
    """

    def setUp(self):
        # Team has completed Phase 1 and is in Phase 2
        self.team = TeamFactory(onboarding_pipeline_status="background_syncing")
        self.repo = TrackedRepositoryFactory(team=self.team)

    def test_phase2_failure_does_not_block_dashboard(self):
        """Phase 2 failure should NOT block dashboard access.

        This is critical - users should keep dashboard access even if
        background processing fails. They have 30 days of data already.
        """
        from apps.integrations.onboarding_pipeline import handle_phase2_failure

        # Simulate Phase 2 failure
        handle_phase2_failure(
            request=MagicMock(),
            exc=Exception("Background sync failed"),
            traceback=None,
            team_id=self.team.id,
        )

        self.team.refresh_from_db()
        # Dashboard should STILL be accessible
        self.assertTrue(self.team.dashboard_accessible)

    def test_phase2_failure_keeps_phase1_complete_status(self):
        """Phase 2 failure should revert to 'phase1_complete', not 'failed'."""
        from apps.integrations.onboarding_pipeline import handle_phase2_failure

        handle_phase2_failure(
            request=MagicMock(),
            exc=Exception("LLM quota exceeded"),
            traceback=None,
            team_id=self.team.id,
        )

        self.team.refresh_from_db()
        # Should be phase1_complete (fallback), not failed
        self.assertEqual(self.team.onboarding_pipeline_status, "phase1_complete")

    def test_phase2_failure_logs_error_but_continues(self):
        """Phase 2 failure should be logged but not disrupt user experience."""
        from apps.integrations.onboarding_pipeline import handle_phase2_failure

        result = handle_phase2_failure(
            request=MagicMock(),
            exc=Exception("Background error"),
            traceback=None,
            team_id=self.team.id,
        )

        # Should indicate failure was handled gracefully
        self.assertEqual(result["status"], "phase2_failed")
        self.assertIn("error", result)


class TestPhase2UsesCorrectErrorHandler(TestCase):
    """Tests that Phase 2 pipeline uses handle_phase2_failure, not handle_pipeline_failure."""

    def setUp(self):
        self.team = TeamFactory(onboarding_pipeline_status="phase1_complete")
        self.repo = TrackedRepositoryFactory(team=self.team)

    @patch("apps.integrations.onboarding_pipeline.chain")
    @patch("apps.integrations.onboarding_pipeline.handle_phase2_failure")
    def test_phase2_pipeline_uses_phase2_error_handler(self, mock_handler, mock_chain):
        """Phase 2 pipeline should use handle_phase2_failure for errors."""
        from apps.integrations.onboarding_pipeline import run_phase2_pipeline

        mock_chain_instance = MagicMock()
        mock_chain.return_value = mock_chain_instance
        mock_chain_instance.on_error.return_value = mock_chain_instance

        run_phase2_pipeline(self.team.id, [self.repo.id])

        # Verify on_error was called with handle_phase2_failure
        mock_chain_instance.on_error.assert_called_once()
        call_args = mock_chain_instance.on_error.call_args[0][0]
        self.assertIn("phase2_failure", str(call_args))
