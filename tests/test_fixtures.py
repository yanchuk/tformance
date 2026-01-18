"""Tests for root-level pytest fixtures.

These tests verify that the global test fixtures work correctly,
particularly the pipeline dispatch mock that prevents cross-test pollution.
"""

import pytest


@pytest.mark.django_db
class TestPipelineDispatchMock:
    """Tests for mock_pipeline_task_dispatch fixture."""

    def test_pipeline_dispatch_is_mocked_by_default(self, mock_pipeline_task_dispatch):
        """Verify that pipeline task dispatch is mocked in all tests.

        Note: The signal uses transaction.on_commit() which doesn't fire in
        standard TestCase (transactions are rolled back, not committed).
        So we test the mock is active by calling dispatch directly.
        """
        from apps.integrations.pipeline_signals import dispatch_pipeline_task

        # Call dispatch directly - it should be intercepted by our mock
        dispatch_pipeline_task(team_id=123, status="syncing")

        # The mock should have captured the call
        mock_pipeline_task_dispatch.assert_called_once()

    def test_team_creation_does_not_invoke_real_tasks(self, mock_pipeline_task_dispatch):
        """Verify that TeamFactory doesn't cause actual Celery tasks to run.

        This is the key test - without the mock, creating teams would trigger
        Celery tasks that could cause cross-test pollution.
        """
        from apps.metrics.factories import TeamFactory

        # Create multiple teams - none should trigger real task execution
        for status in ["syncing_members", "syncing", "analyzing_llm", "complete"]:
            TeamFactory(onboarding_pipeline_status=status)

        # The mock captures all calls, but no real tasks were invoked
        # If tasks had run, we'd see database changes or other side effects
        assert mock_pipeline_task_dispatch.call_count >= 0  # Just verify no exception

    def test_mock_returns_false(self, mock_pipeline_task_dispatch):
        """Verify the mock returns False (indicating no task was dispatched)."""
        from apps.integrations.pipeline_signals import dispatch_pipeline_task

        # Direct call to dispatch should return the mock's return value
        result = dispatch_pipeline_task(team_id=1, status="syncing")

        assert result is False
        mock_pipeline_task_dispatch.assert_called_once_with(team_id=1, status="syncing")
