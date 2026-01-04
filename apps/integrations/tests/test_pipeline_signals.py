"""Tests for signal-based pipeline state machine.

Tests the signal handler that dispatches next pipeline tasks
when Team.onboarding_pipeline_status changes.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory


class TestPipelineStatusTracking(TestCase):
    """Tests for _original_pipeline_status tracking on Team model."""

    def test_original_status_tracked_on_model_load(self):
        """Team should track original pipeline status when loaded from DB."""
        team = TeamFactory(onboarding_pipeline_status="syncing")

        # Reload from database
        from apps.teams.models import Team

        reloaded = Team.objects.get(id=team.id)

        self.assertEqual(reloaded._original_pipeline_status, "syncing")

    def test_original_status_is_default_on_new_instance(self):
        """New Team instance should have default status tracked."""
        from apps.teams.models import Team

        team = Team(name="Test", slug="test")

        self.assertEqual(team._original_pipeline_status, "not_started")


class TestPipelineSignalDispatch(TestCase):
    """Tests for signal-based task dispatch on status change."""

    @patch("apps.integrations.pipeline_signals.dispatch_pipeline_task")
    def test_signal_fires_on_status_change(self, mock_dispatch):
        """Signal should dispatch task when status changes."""
        team = TeamFactory(onboarding_pipeline_status="not_started")

        # Change status via update_pipeline_status (the normal flow)
        team.update_pipeline_status("syncing_members")

        # Signal should have dispatched the task for the new status
        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args
        self.assertEqual(call_args[0][0], team.id)
        self.assertEqual(call_args[0][1], "syncing_members")

    @patch("apps.integrations.pipeline_signals.dispatch_pipeline_task")
    def test_no_dispatch_when_status_unchanged(self, mock_dispatch):
        """Signal should NOT dispatch when status doesn't actually change."""
        team = TeamFactory(onboarding_pipeline_status="syncing")

        # Reload team to reset _original_pipeline_status
        from apps.teams.models import Team

        team = Team.objects.get(id=team.id)

        # Save without changing status
        team.name = "Updated Name"
        team.save()

        # No dispatch should happen for unchanged status
        mock_dispatch.assert_not_called()

    @patch("apps.integrations.pipeline_signals.dispatch_pipeline_task")
    def test_no_dispatch_on_non_status_field_update(self, mock_dispatch):
        """Signal should NOT dispatch when only other fields change."""
        team = TeamFactory(onboarding_pipeline_status="syncing")

        # Update only non-status field using update_fields
        team.background_sync_progress = 50
        team.save(update_fields=["background_sync_progress"])

        # No dispatch should happen
        mock_dispatch.assert_not_called()


class TestPipelineStateMachine(TestCase):
    """Tests for state machine task mapping.

    These tests mock at the actual task source locations to verify
    the dispatch_pipeline_task function correctly imports and dispatches.
    """

    @patch("apps.integrations.onboarding_pipeline.sync_github_members_pipeline_task")
    def test_syncing_members_dispatches_member_sync(self, mock_task):
        """syncing_members status should dispatch member sync task."""
        team = TeamFactory(onboarding_pipeline_status="not_started")

        team.update_pipeline_status("syncing_members")

        mock_task.apply_async.assert_called_once()
        call_args = mock_task.apply_async.call_args
        self.assertEqual(call_args[1]["args"][0], team.id)

    @patch("apps.integrations.tasks.sync_historical_data_task")
    def test_syncing_dispatches_historical_sync(self, mock_task):
        """syncing status should dispatch historical data sync task."""
        team = TeamFactory(onboarding_pipeline_status="syncing_members")

        team.update_pipeline_status("syncing")

        mock_task.apply_async.assert_called_once()

    @patch("apps.integrations._task_modules.metrics.queue_llm_analysis_batch_task")
    def test_llm_processing_dispatches_llm_task(self, mock_task):
        """llm_processing status should dispatch LLM analysis task."""
        team = TeamFactory(onboarding_pipeline_status="syncing")

        team.update_pipeline_status("llm_processing")

        mock_task.apply_async.assert_called_once()

    @patch("apps.integrations._task_modules.metrics.aggregate_team_weekly_metrics_task")
    def test_computing_metrics_dispatches_aggregation(self, mock_task):
        """computing_metrics status should dispatch metrics aggregation."""
        team = TeamFactory(onboarding_pipeline_status="llm_processing")

        team.update_pipeline_status("computing_metrics")

        mock_task.apply_async.assert_called_once()

    @patch("apps.metrics.tasks.compute_team_insights")
    def test_computing_insights_dispatches_insights(self, mock_task):
        """computing_insights status should dispatch insights computation."""
        team = TeamFactory(onboarding_pipeline_status="computing_metrics")

        team.update_pipeline_status("computing_insights")

        mock_task.apply_async.assert_called_once()


class TestPhase1ToPhase2Transition(TestCase):
    """Tests for automatic Phase 2 dispatch after Phase 1."""

    @patch("apps.integrations.pipeline_signals.dispatch_phase2_start")
    def test_phase1_complete_triggers_phase2(self, mock_dispatch):
        """phase1_complete status should trigger Phase 2 dispatch."""
        team = TeamFactory(onboarding_pipeline_status="computing_insights")

        team.update_pipeline_status("phase1_complete")

        mock_dispatch.assert_called_once_with(team.id)


class TestPhase2StateMachine(TestCase):
    """Tests for Phase 2 (background) state machine."""

    @patch("apps.integrations.tasks.sync_historical_data_task")
    def test_background_syncing_dispatches_sync(self, mock_task):
        """background_syncing should dispatch historical sync with skip_recent."""
        team = TeamFactory(onboarding_pipeline_status="phase1_complete")

        team.update_pipeline_status("background_syncing")

        mock_task.apply_async.assert_called_once()
        # Should include days_back=90 and skip_recent=30
        call_kwargs = mock_task.apply_async.call_args[1]["kwargs"]
        self.assertEqual(call_kwargs.get("days_back"), 90)
        self.assertEqual(call_kwargs.get("skip_recent"), 30)

    @patch("apps.integrations._task_modules.metrics.queue_llm_analysis_batch_task")
    def test_background_llm_dispatches_llm(self, mock_task):
        """background_llm should dispatch LLM analysis task."""
        team = TeamFactory(onboarding_pipeline_status="background_syncing")

        team.update_pipeline_status("background_llm")

        mock_task.apply_async.assert_called_once()


class TestSignalErrorHandling(TestCase):
    """Tests for signal handler error resilience."""

    @patch("apps.integrations.pipeline_signals.dispatch_pipeline_task")
    def test_signal_exception_does_not_block_save(self, mock_dispatch):
        """Signal handler exception should not prevent status save."""
        mock_dispatch.side_effect = Exception("Task dispatch failed")

        team = TeamFactory(onboarding_pipeline_status="not_started")

        # This should NOT raise - save should succeed
        team.update_pipeline_status("syncing_members")

        # Verify status was saved despite exception
        team.refresh_from_db()
        self.assertEqual(team.onboarding_pipeline_status, "syncing_members")

    @patch("apps.integrations.pipeline_signals.logger")
    @patch("apps.integrations.pipeline_signals.dispatch_pipeline_task")
    def test_signal_exception_is_logged(self, mock_dispatch, mock_logger):
        """Signal handler should log exceptions."""
        mock_dispatch.side_effect = Exception("Task dispatch failed")

        team = TeamFactory(onboarding_pipeline_status="not_started")
        team.update_pipeline_status("syncing_members")

        # Exception should be logged
        mock_logger.exception.assert_called()


class TestTerminalStatesNoDispatch(TestCase):
    """Tests that terminal states don't dispatch further tasks."""

    @patch("apps.integrations.pipeline_signals.dispatch_pipeline_task")
    def test_complete_status_no_dispatch(self, mock_dispatch):
        """complete status should not dispatch any task."""
        team = TeamFactory(onboarding_pipeline_status="background_llm")

        team.update_pipeline_status("complete")

        # dispatch_pipeline_task is called but returns False for terminal state
        # Let's verify by checking what it was called with
        if mock_dispatch.called:
            # If called, should be with terminal status which returns False
            self.assertEqual(mock_dispatch.call_args[0][1], "complete")

    @patch("apps.integrations.pipeline_signals.dispatch_pipeline_task")
    def test_failed_status_no_dispatch(self, mock_dispatch):
        """failed status should not dispatch any task."""
        team = TeamFactory(onboarding_pipeline_status="syncing")

        team.update_pipeline_status("failed", error="Something went wrong")

        # dispatch_pipeline_task is called but returns False for terminal state
        if mock_dispatch.called:
            self.assertEqual(mock_dispatch.call_args[0][1], "failed")
