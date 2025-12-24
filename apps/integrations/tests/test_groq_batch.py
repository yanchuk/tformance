"""Tests for Groq Batch API service."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.groq_batch import (
    BatchResult,
    BatchStatus,
    GroqBatchProcessor,
)
from apps.metrics.factories import PullRequestFactory, TeamFactory


class TestBatchResult(TestCase):
    """Tests for BatchResult parsing."""

    def test_from_response_success(self):
        """Test parsing successful response."""
        response_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "is_ai_assisted": True,
                                "tools": ["cursor", "claude"],
                                "confidence": 0.95,
                                "usage_category": "assisted",
                                "reasoning": "PR mentions Cursor IDE",
                            }
                        )
                    }
                }
            ]
        }

        result = BatchResult.from_response("pr-123", response_body)

        self.assertEqual(result.pr_id, 123)
        self.assertTrue(result.is_ai_assisted)
        self.assertEqual(result.tools, ["cursor", "claude"])
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.usage_category, "assisted")
        self.assertIsNone(result.error)

    def test_from_response_error(self):
        """Test parsing error response."""
        response_body = {"error": {"message": "Rate limit exceeded"}}

        result = BatchResult.from_response("pr-456", response_body)

        self.assertEqual(result.pr_id, 456)
        self.assertFalse(result.is_ai_assisted)
        self.assertEqual(result.tools, [])
        self.assertEqual(result.error, "Rate limit exceeded")

    def test_from_response_invalid_json(self):
        """Test handling invalid JSON in response."""
        response_body = {"choices": [{"message": {"content": "not valid json"}}]}

        result = BatchResult.from_response("pr-789", response_body)

        self.assertEqual(result.pr_id, 789)
        self.assertFalse(result.is_ai_assisted)
        self.assertIn("Failed to parse", result.error)

    def test_from_response_negative_detection(self):
        """Test parsing negative detection."""
        response_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "is_ai_assisted": False,
                                "tools": [],
                                "confidence": 0.1,
                                "reasoning": "No AI disclosure found",
                            }
                        )
                    }
                }
            ]
        }

        result = BatchResult.from_response("pr-100", response_body)

        self.assertFalse(result.is_ai_assisted)
        self.assertEqual(result.tools, [])
        self.assertEqual(result.confidence, 0.1)


class TestBatchStatus(TestCase):
    """Tests for BatchStatus."""

    def test_is_complete_completed(self):
        """Test completed status."""
        status = BatchStatus(
            batch_id="batch-123",
            status="completed",
            total_requests=100,
            completed_requests=100,
            failed_requests=0,
            output_file_id="file-123",
        )

        self.assertTrue(status.is_complete)

    def test_is_complete_in_progress(self):
        """Test in_progress status."""
        status = BatchStatus(
            batch_id="batch-123",
            status="in_progress",
            total_requests=100,
            completed_requests=50,
            failed_requests=0,
        )

        self.assertFalse(status.is_complete)

    def test_is_complete_failed(self):
        """Test failed status."""
        status = BatchStatus(
            batch_id="batch-123",
            status="failed",
            total_requests=100,
            completed_requests=0,
            failed_requests=100,
        )

        self.assertTrue(status.is_complete)

    def test_progress_pct(self):
        """Test progress percentage calculation."""
        status = BatchStatus(
            batch_id="batch-123",
            status="in_progress",
            total_requests=200,
            completed_requests=50,
            failed_requests=0,
        )

        self.assertEqual(status.progress_pct, 25.0)

    def test_progress_pct_zero_total(self):
        """Test progress with zero total."""
        status = BatchStatus(
            batch_id="batch-123",
            status="validating",
            total_requests=0,
            completed_requests=0,
            failed_requests=0,
        )

        self.assertEqual(status.progress_pct, 0.0)


class TestGroqBatchProcessor(TestCase):
    """Tests for GroqBatchProcessor."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_format_pr_context(self):
        """Test rich PR context formatting."""
        from apps.metrics.factories import TeamMemberFactory

        member = TeamMemberFactory(
            team=self.team,
            github_username="testuser",
            display_name="Test User",
        )
        pr = PullRequestFactory(
            team=self.team,
            author=member,
            title="Fix bug in AI module",
            body="This PR fixes the bug.",
            github_repo="org/repo",
            additions=50,
            deletions=10,
            labels=["bug", "ai-generated"],
            linked_issues=[123, 456],
        )

        processor = GroqBatchProcessor(api_key="test-key")
        context = processor._format_pr_context(pr)

        # Verify all metadata is included
        self.assertIn("Title: Fix bug in AI module", context)
        self.assertIn("Author: testuser", context)
        self.assertIn("Repository: org/repo", context)
        self.assertIn("+50/-10 lines", context)
        self.assertIn("bug, ai-generated", context)
        self.assertIn("#123, #456", context)
        self.assertIn("This PR fixes the bug.", context)

    def test_create_batch_file(self):
        """Test creating JSONL batch file with rich context."""
        prs = [
            PullRequestFactory(
                team=self.team,
                body="Test PR with AI disclosure",
                title="Add feature",
                additions=100,
                deletions=20,
            ),
            PullRequestFactory(team=self.team, body="Another PR body"),
        ]

        processor = GroqBatchProcessor(api_key="test-key")

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = f.name

        try:
            result_path = processor.create_batch_file(prs, output_path=temp_path)

            self.assertTrue(result_path.exists())

            # Read and verify content
            with open(result_path) as f:
                lines = f.readlines()

            self.assertEqual(len(lines), 2)

            # Parse first line
            first_request = json.loads(lines[0])
            self.assertEqual(first_request["custom_id"], f"pr-{prs[0].id}")
            self.assertEqual(first_request["method"], "POST")
            self.assertEqual(first_request["url"], "/v1/chat/completions")
            self.assertEqual(first_request["body"]["model"], "llama-3.3-70b-versatile")
            self.assertEqual(first_request["body"]["response_format"], {"type": "json_object"})

            # Verify rich context is in user message
            user_content = first_request["body"]["messages"][1]["content"]
            self.assertIn("# PR Metadata", user_content)
            self.assertIn("Title: Add feature", user_content)
            self.assertIn("+100/-20 lines", user_content)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_create_batch_file_skips_empty_body(self):
        """Test that PRs with empty body are skipped."""
        prs = [
            PullRequestFactory(team=self.team, body="Has body"),
            PullRequestFactory(team=self.team, body=""),
        ]

        processor = GroqBatchProcessor(api_key="test-key")

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            temp_path = f.name

        try:
            result_path = processor.create_batch_file(prs, output_path=temp_path)

            with open(result_path) as f:
                lines = f.readlines()

            # Only one PR should be included
            self.assertEqual(len(lines), 1)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_upload_file(self, mock_groq_class):
        """Test file upload."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.files.create.return_value = MagicMock(id="file-123")

        processor = GroqBatchProcessor(api_key="test-key")

        with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w") as f:
            f.write('{"test": "data"}\n')
            f.flush()
            file_id = processor.upload_file(f.name)

        self.assertEqual(file_id, "file-123")
        mock_client.files.create.assert_called_once()

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_submit_batch(self, mock_groq_class):
        """Test submitting batch job."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.files.create.return_value = MagicMock(id="file-123")
        mock_client.batches.create.return_value = MagicMock(id="batch-456")

        prs = [PullRequestFactory(team=self.team, body="Test body")]
        processor = GroqBatchProcessor(api_key="test-key")

        batch_id = processor.submit_batch(prs)

        self.assertEqual(batch_id, "batch-456")
        mock_client.batches.create.assert_called_once_with(
            completion_window="24h",
            endpoint="/v1/chat/completions",
            input_file_id="file-123",
        )

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_get_status(self, mock_groq_class):
        """Test getting batch status."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_batch = MagicMock()
        mock_batch.id = "batch-123"
        mock_batch.status = "in_progress"
        mock_batch.request_counts.total = 100
        mock_batch.request_counts.completed = 50
        mock_batch.request_counts.failed = 0
        mock_batch.output_file_id = None
        mock_batch.error_file_id = None
        mock_client.batches.retrieve.return_value = mock_batch

        processor = GroqBatchProcessor(api_key="test-key")
        status = processor.get_status("batch-123")

        self.assertEqual(status.batch_id, "batch-123")
        self.assertEqual(status.status, "in_progress")
        self.assertEqual(status.total_requests, 100)
        self.assertEqual(status.completed_requests, 50)
        self.assertFalse(status.is_complete)

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_get_results(self, mock_groq_class):
        """Test getting results from completed batch."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        # Mock completed batch status
        mock_batch = MagicMock()
        mock_batch.id = "batch-123"
        mock_batch.status = "completed"
        mock_batch.request_counts.total = 2
        mock_batch.request_counts.completed = 2
        mock_batch.request_counts.failed = 0
        mock_batch.output_file_id = "output-file-123"
        mock_batch.error_file_id = None
        mock_client.batches.retrieve.return_value = mock_batch

        # Mock file content (text() is a method that returns the content)
        results_jsonl = (
            '{"custom_id": "pr-1", "response": {"body": {"choices": [{"message": '
            '{"content": "{\\"is_ai_assisted\\": true, \\"tools\\": [\\"cursor\\"], '
            '\\"confidence\\": 0.9}"}}]}}}\n'
            '{"custom_id": "pr-2", "response": {"body": {"choices": [{"message": '
            '{"content": "{\\"is_ai_assisted\\": false, \\"tools\\": [], '
            '\\"confidence\\": 0.1}"}}]}}}'
        )
        mock_response = MagicMock()
        mock_response.text.return_value = results_jsonl
        mock_client.files.content.return_value = mock_response

        processor = GroqBatchProcessor(api_key="test-key")
        results = processor.get_results("batch-123")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].pr_id, 1)
        self.assertTrue(results[0].is_ai_assisted)
        self.assertEqual(results[0].tools, ["cursor"])
        self.assertEqual(results[1].pr_id, 2)
        self.assertFalse(results[1].is_ai_assisted)

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_get_results_not_complete(self, mock_groq_class):
        """Test error when batch not complete."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_batch = MagicMock()
        mock_batch.status = "in_progress"
        mock_batch.request_counts.total = 100
        mock_batch.request_counts.completed = 50
        mock_batch.request_counts.failed = 0
        mock_batch.output_file_id = None
        mock_batch.error_file_id = None
        mock_client.batches.retrieve.return_value = mock_batch

        processor = GroqBatchProcessor(api_key="test-key")

        with self.assertRaises(ValueError) as ctx:
            processor.get_results("batch-123")

        self.assertIn("not complete", str(ctx.exception))

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_cancel_batch(self, mock_groq_class):
        """Test cancelling batch."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_batch = MagicMock()
        mock_batch.id = "batch-123"
        mock_batch.status = "cancelled"
        mock_batch.request_counts.total = 100
        mock_batch.request_counts.completed = 0
        mock_batch.request_counts.failed = 0
        mock_batch.output_file_id = None
        mock_batch.error_file_id = None
        mock_client.batches.retrieve.return_value = mock_batch

        processor = GroqBatchProcessor(api_key="test-key")
        status = processor.cancel_batch("batch-123")

        mock_client.batches.cancel.assert_called_once_with("batch-123")
        self.assertEqual(status.status, "cancelled")
