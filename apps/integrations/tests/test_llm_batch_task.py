"""Tests for queue_llm_analysis_batch_task Celery task.

TDD RED Phase: These tests verify the behavior of a deferred LLM batch analysis task
that processes PRs missing LLM analysis (llm_summary is NULL).

The task should:
1. Find PRs where llm_summary is NULL
2. Process them in batches (configurable batch size)
3. Update PRs with LLM results
4. Skip PRs that already have llm_summary
5. Respect team isolation - only process PRs for the specified team
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
)
from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory


class TestQueueLLMAnalysisBatchTask(TestCase):
    """Tests for queue_llm_analysis_batch_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

    def test_task_exists_and_is_callable(self):
        """Test that queue_llm_analysis_batch_task exists and is callable."""
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Task should be a Celery task with .delay() method
        self.assertTrue(callable(queue_llm_analysis_batch_task))
        self.assertTrue(hasattr(queue_llm_analysis_batch_task, "delay"))

    def test_finds_prs_with_null_llm_summary(self):
        """Test that task finds PRs where llm_summary is NULL."""
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Create PRs - some with llm_summary, some without
        pr_without_summary = PullRequestFactory(
            team=self.team,
            author=self.member,
            body="PR without LLM summary",
            llm_summary=None,
            state="merged",
        )
        pr_with_summary = PullRequestFactory(
            team=self.team,
            author=self.member,
            body="PR with LLM summary",
            llm_summary={"ai": {"is_assisted": True}},
            state="merged",
        )

        # Mock the LLM processor to capture what PRs are processed
        with patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor
            mock_processor.submit_batch_with_fallback.return_value = ([], {})

            queue_llm_analysis_batch_task(self.team.id)

            # Should have attempted to process PRs
            mock_processor.submit_batch_with_fallback.assert_called_once()
            processed_prs = mock_processor.submit_batch_with_fallback.call_args[0][0]

            # Only PR without llm_summary should be processed
            processed_pr_ids = [pr.id for pr in processed_prs]
            self.assertIn(pr_without_summary.id, processed_pr_ids)
            self.assertNotIn(pr_with_summary.id, processed_pr_ids)

    def test_processes_prs_in_batches(self):
        """Test that task processes PRs in batches with configurable batch size."""
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Create 5 PRs without llm_summary
        prs = []
        for i in range(5):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                body=f"PR {i} body content",
                llm_summary=None,
                state="merged",
            )
            prs.append(pr)

        # Test with batch_size=3 (should process only 3 PRs)
        with patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor
            mock_processor.submit_batch_with_fallback.return_value = ([], {})

            queue_llm_analysis_batch_task(self.team.id, batch_size=3)

            # Should have processed exactly 3 PRs
            mock_processor.submit_batch_with_fallback.assert_called_once()
            processed_prs = mock_processor.submit_batch_with_fallback.call_args[0][0]
            self.assertEqual(len(processed_prs), 3)

    def test_updates_prs_with_llm_results(self):
        """Test that task updates PRs with LLM analysis results."""
        from apps.integrations.services.groq_batch import BatchResult
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Create PR without llm_summary
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            body="PR body for LLM analysis",
            llm_summary=None,
            state="merged",
        )

        # Mock LLM processor to return analysis results
        mock_result = BatchResult(
            pr_id=pr.id,
            is_ai_assisted=True,
            tools=["cursor", "claude"],
            confidence=0.95,
            usage_category="authored",
            llm_summary={
                "ai": {
                    "is_assisted": True,
                    "tools": ["cursor", "claude"],
                    "confidence": 0.95,
                    "usage_type": "authored",
                },
                "tech": {
                    "languages": ["python"],
                    "frameworks": ["django"],
                    "categories": ["backend"],
                },
                "summary": {
                    "title": "Add feature",
                    "description": "Adds new feature",
                    "type": "feature",
                },
            },
        )

        with patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor
            mock_processor.submit_batch_with_fallback.return_value = (
                [mock_result],
                {"first_batch_id": "batch-123"},
            )

            queue_llm_analysis_batch_task(self.team.id)

        # Reload PR from database
        pr.refresh_from_db()

        # Verify PR was updated with LLM results
        self.assertIsNotNone(pr.llm_summary)
        self.assertEqual(pr.llm_summary["ai"]["is_assisted"], True)
        self.assertEqual(pr.llm_summary["ai"]["tools"], ["cursor", "claude"])
        self.assertIn("tech", pr.llm_summary)
        self.assertIn("summary", pr.llm_summary)

    def test_skips_prs_with_existing_llm_summary(self):
        """Test that task skips PRs that already have llm_summary."""
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Create PR with existing llm_summary
        pr_with_summary = PullRequestFactory(
            team=self.team,
            author=self.member,
            body="PR with existing summary",
            llm_summary={
                "ai": {"is_assisted": False, "tools": [], "confidence": 0.1},
                "tech": {"languages": ["python"], "categories": ["backend"]},
            },
            state="merged",
        )

        # Call task
        with patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor
            mock_processor.submit_batch_with_fallback.return_value = ([], {})

            queue_llm_analysis_batch_task(self.team.id)

            # Check if submit_batch_with_fallback was called with empty list
            # or not called at all
            if mock_processor.submit_batch_with_fallback.called:
                processed_prs = mock_processor.submit_batch_with_fallback.call_args[0][0]
                processed_pr_ids = [pr.id for pr in processed_prs]
                self.assertNotIn(pr_with_summary.id, processed_pr_ids)

    def test_team_isolation(self):
        """Test that task only processes PRs for the specified team."""
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Create another team
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)

        # Create PRs for both teams without llm_summary
        pr_own_team = PullRequestFactory(
            team=self.team,
            author=self.member,
            body="PR for own team",
            llm_summary=None,
            state="merged",
        )
        pr_other_team = PullRequestFactory(
            team=other_team,
            author=other_member,
            body="PR for other team",
            llm_summary=None,
            state="merged",
        )

        # Call task for self.team
        with patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor
            mock_processor.submit_batch_with_fallback.return_value = ([], {})

            queue_llm_analysis_batch_task(self.team.id)

            # Should only process PRs from self.team
            mock_processor.submit_batch_with_fallback.assert_called_once()
            processed_prs = mock_processor.submit_batch_with_fallback.call_args[0][0]
            processed_pr_ids = [pr.id for pr in processed_prs]

            self.assertIn(pr_own_team.id, processed_pr_ids)
            self.assertNotIn(pr_other_team.id, processed_pr_ids)

    def test_handles_team_not_found(self):
        """Test that task handles non-existent team gracefully."""
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Call task with non-existent team ID
        result = queue_llm_analysis_batch_task(99999)

        # Should return error dict
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    def test_returns_result_dict_with_counts(self):
        """Test that task returns a result dict with processing counts."""
        from apps.integrations.services.groq_batch import BatchResult
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Create PRs without llm_summary
        prs = []
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                body=f"PR {i} body",
                llm_summary=None,
                state="merged",
            )
            prs.append(pr)

        # Mock successful processing
        mock_results = [
            BatchResult(
                pr_id=pr.id,
                is_ai_assisted=True,
                tools=["cursor"],
                confidence=0.9,
                llm_summary={"ai": {"is_assisted": True}},
            )
            for pr in prs
        ]

        with patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor
            mock_processor.submit_batch_with_fallback.return_value = (
                mock_results,
                {"first_batch_id": "batch-123"},
            )

            result = queue_llm_analysis_batch_task(self.team.id)

        # Should return dict with processing counts
        self.assertIsInstance(result, dict)
        self.assertIn("prs_processed", result)
        self.assertEqual(result["prs_processed"], 3)

    def test_handles_no_prs_to_process(self):
        """Test that task handles case when no PRs need processing."""
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Create PR with existing llm_summary (nothing to process)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            body="PR with summary",
            llm_summary={"ai": {"is_assisted": False}},
            state="merged",
        )

        # Call task
        result = queue_llm_analysis_batch_task(self.team.id)

        # Should return success with 0 processed
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("prs_processed", 0), 0)

    def test_default_batch_size(self):
        """Test that task uses a reasonable default batch size."""
        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Create many PRs without llm_summary
        for i in range(100):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                body=f"PR {i} body",
                llm_summary=None,
                state="merged",
            )

        # Call task without specifying batch_size
        with patch("apps.integrations._task_modules.metrics.GroqBatchProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor_class.return_value = mock_processor
            mock_processor.submit_batch_with_fallback.return_value = ([], {})

            queue_llm_analysis_batch_task(self.team.id)

            # Should process a reasonable batch (not all 100)
            # Default should be something like 50
            mock_processor.submit_batch_with_fallback.assert_called_once()
            processed_prs = mock_processor.submit_batch_with_fallback.call_args[0][0]
            self.assertLessEqual(len(processed_prs), 50)
            self.assertGreater(len(processed_prs), 0)


class TestQueueLLMAnalysisBatchTaskIntegration(TestCase):
    """Integration tests for queue_llm_analysis_batch_task with real LLM processing."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_end_to_end_llm_analysis(self, mock_groq_class):
        """Test full flow of LLM analysis from PR to updated record."""
        import json

        from apps.integrations.tasks import queue_llm_analysis_batch_task

        # Create PR without llm_summary
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            title="Add AI feature",
            body="## AI Disclosure\nUsed Cursor with Claude for implementation",
            llm_summary=None,
            state="merged",
        )

        # Mock Groq API responses
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.files.create.return_value = MagicMock(id="file-123")
        mock_client.batches.create.return_value = MagicMock(id="batch-456")

        # Mock completed batch status
        mock_batch = MagicMock()
        mock_batch.id = "batch-456"
        mock_batch.status = "completed"
        mock_batch.request_counts.total = 1
        mock_batch.request_counts.completed = 1
        mock_batch.request_counts.failed = 0
        mock_batch.output_file_id = "output-file-123"
        mock_batch.error_file_id = None
        mock_client.batches.retrieve.return_value = mock_batch

        # Mock results
        llm_response = {
            "ai": {
                "is_assisted": True,
                "tools": ["cursor", "claude"],
                "usage_type": "authored",
                "confidence": 0.95,
            },
            "tech": {
                "languages": ["python"],
                "frameworks": ["django"],
                "categories": ["backend"],
            },
            "summary": {
                "title": "Add AI feature",
                "description": "Implements AI-powered feature",
                "type": "feature",
            },
            "health": {
                "review_friction": "low",
                "scope": "medium",
                "risk_level": "low",
                "insights": [],
            },
        }
        results_jsonl = json.dumps(
            {
                "custom_id": f"pr-{pr.id}",
                "response": {"body": {"choices": [{"message": {"content": json.dumps(llm_response)}}]}},
            }
        )
        mock_response = MagicMock()
        mock_response.text.return_value = results_jsonl
        mock_client.files.content.return_value = mock_response

        # Run task
        queue_llm_analysis_batch_task(self.team.id)

        # Verify PR was updated
        pr.refresh_from_db()
        self.assertIsNotNone(pr.llm_summary)
        self.assertEqual(pr.llm_summary["ai"]["is_assisted"], True)
        self.assertIn("cursor", pr.llm_summary["ai"]["tools"])
