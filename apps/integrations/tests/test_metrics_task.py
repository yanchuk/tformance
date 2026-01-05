"""Tests for metrics task module - queue_llm_analysis_batch_task.

Tests for requeue depth limiting and stuck batch detection.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations._task_modules.metrics import (
    MAX_REQUEUE_DEPTH,
    queue_llm_analysis_batch_task,
)
from apps.metrics.factories import PullRequestFactory, TeamFactory


class TestQueueLLMAnalysisBatchRequeueDepth(TestCase):
    """Tests for requeue depth limiting in queue_llm_analysis_batch_task."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_max_requeue_depth_constant_exists(self):
        """MAX_REQUEUE_DEPTH constant should be defined."""
        self.assertIsNotNone(MAX_REQUEUE_DEPTH)
        self.assertGreater(MAX_REQUEUE_DEPTH, 0)
        self.assertLessEqual(MAX_REQUEUE_DEPTH, 100)  # Sanity check

    def test_requeue_depth_parameter_accepted(self):
        """Task should accept requeue_depth parameter."""
        # Create a PR that needs processing
        PullRequestFactory(team=self.team, body="Test PR", llm_summary=None)

        # Mock the Groq processor to avoid actual API calls
        with patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor:
            mock_instance = MagicMock()
            mock_instance.submit_batch_with_fallback.return_value = ([], {"processed": 0})
            mock_processor.return_value = mock_instance

            # Call task with requeue_depth parameter - should not raise
            result = queue_llm_analysis_batch_task(team_id=self.team.id, batch_size=50, requeue_depth=5)

            self.assertIn("prs_processed", result)

    def test_requeue_stops_at_max_depth(self):
        """Task should stop requeueing when max depth is reached."""
        # Create PRs that need processing
        for _ in range(5):
            PullRequestFactory(team=self.team, body="Test PR", llm_summary=None)

        # Mock the processor to simulate "stuck" state (no progress)
        with (
            patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor,
            patch.object(queue_llm_analysis_batch_task, "apply_async") as mock_apply_async,
        ):
            mock_instance = MagicMock()
            # Return empty results (no progress made)
            mock_instance.submit_batch_with_fallback.return_value = ([], {"processed": 0})
            mock_processor.return_value = mock_instance

            # Call with requeue_depth at max
            result = queue_llm_analysis_batch_task(team_id=self.team.id, batch_size=50, requeue_depth=MAX_REQUEUE_DEPTH)

            # Should NOT requeue (apply_async not called)
            mock_apply_async.assert_not_called()
            # Should indicate max depth reached
            self.assertIn("max_requeue_depth", result.get("warning", ""))

    def test_requeue_increments_depth(self):
        """When requeueing, depth should be incremented."""
        # Create PRs that need processing
        prs = []
        for _ in range(5):
            prs.append(PullRequestFactory(team=self.team, body="Test PR", llm_summary=None))

        with (
            patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor,
            patch.object(queue_llm_analysis_batch_task, "apply_async") as mock_apply_async,
        ):
            mock_instance = MagicMock()
            # Return some progress so it will requeue (but not all PRs processed)
            mock_result = MagicMock()
            mock_result.pr_id = prs[0].id
            mock_result.error = None
            mock_result.llm_summary = {"ai": {"is_assisted": False}}
            mock_instance.submit_batch_with_fallback.return_value = ([mock_result], {"processed": 1})
            mock_processor.return_value = mock_instance

            queue_llm_analysis_batch_task(team_id=self.team.id, batch_size=50, requeue_depth=5)

            # apply_async should be called with incremented depth
            mock_apply_async.assert_called_once()
            call_kwargs = mock_apply_async.call_args[1]
            self.assertEqual(call_kwargs["kwargs"]["requeue_depth"], 6)
