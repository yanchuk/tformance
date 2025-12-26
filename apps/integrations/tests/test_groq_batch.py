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
from apps.metrics.factories import (
    CommitFactory,
    PRFileFactory,
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)


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

    def test_from_response_v5_format(self):
        """Test parsing v5 nested response format with ai/tech/summary."""
        response_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "ai": {
                                    "is_assisted": True,
                                    "tools": ["cursor", "claude"],
                                    "usage_type": "authored",
                                    "confidence": 0.95,
                                },
                                "tech": {
                                    "languages": ["python", "typescript"],
                                    "frameworks": ["django", "react"],
                                    "categories": ["backend", "frontend"],
                                },
                                "summary": {
                                    "title": "Add dark mode toggle",
                                    "description": "Implements dark mode with user preferences.",
                                    "type": "feature",
                                },
                            }
                        )
                    }
                }
            ]
        }

        result = BatchResult.from_response("pr-200", response_body)

        # AI detection
        self.assertEqual(result.pr_id, 200)
        self.assertTrue(result.is_ai_assisted)
        self.assertEqual(result.tools, ["cursor", "claude"])
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.usage_category, "authored")

        # Technology detection
        self.assertEqual(result.primary_language, "python")
        self.assertEqual(result.tech_languages, ["python", "typescript"])
        self.assertEqual(result.tech_frameworks, ["django", "react"])
        self.assertEqual(result.tech_categories, ["backend", "frontend"])

        # Summary
        self.assertEqual(result.summary_title, "Add dark mode toggle")
        self.assertEqual(result.summary_description, "Implements dark mode with user preferences.")
        self.assertEqual(result.summary_type, "feature")

        # Full LLM response stored
        self.assertIn("ai", result.llm_summary)
        self.assertIn("tech", result.llm_summary)
        self.assertIn("summary", result.llm_summary)

    def test_from_response_v5_no_ai_usage(self):
        """Test parsing v5 response with no AI usage detected."""
        response_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "ai": {
                                    "is_assisted": False,
                                    "tools": [],
                                    "usage_type": None,
                                    "confidence": 0.1,
                                },
                                "tech": {
                                    "languages": ["go"],
                                    "frameworks": [],
                                    "categories": ["backend"],
                                },
                                "summary": {
                                    "title": "Fix memory leak in cache",
                                    "description": "Resolves OOM issues in production.",
                                    "type": "bugfix",
                                },
                            }
                        )
                    }
                }
            ]
        }

        result = BatchResult.from_response("pr-300", response_body)

        self.assertFalse(result.is_ai_assisted)
        self.assertEqual(result.tools, [])
        self.assertEqual(result.primary_language, "go")
        self.assertEqual(result.summary_type, "bugfix")

    def test_from_response_v6_format_with_health(self):
        """Test parsing v6 nested response format with health assessment."""
        response_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "ai": {
                                    "is_assisted": True,
                                    "tools": ["claude"],
                                    "usage_type": "authored",
                                    "confidence": 0.95,
                                },
                                "tech": {
                                    "languages": ["python"],
                                    "frameworks": ["django"],
                                    "categories": ["backend"],
                                },
                                "summary": {
                                    "title": "Fix auth timeout bug",
                                    "description": "Resolves session expiry issue.",
                                    "type": "bugfix",
                                },
                                "health": {
                                    "review_friction": "low",
                                    "scope": "small",
                                    "risk_level": "high",
                                    "insights": [
                                        "Hotfix with quick review turnaround",
                                        "Small scope but critical fix",
                                    ],
                                },
                            }
                        )
                    }
                }
            ]
        }

        result = BatchResult.from_response("pr-400", response_body)

        # AI detection
        self.assertEqual(result.pr_id, 400)
        self.assertTrue(result.is_ai_assisted)
        self.assertEqual(result.tools, ["claude"])

        # Summary
        self.assertEqual(result.summary_title, "Fix auth timeout bug")
        self.assertEqual(result.summary_type, "bugfix")

        # Health assessment (v6)
        self.assertEqual(result.health_review_friction, "low")
        self.assertEqual(result.health_scope, "small")
        self.assertEqual(result.health_risk_level, "high")
        self.assertEqual(len(result.health_insights), 2)
        self.assertIn("Hotfix with quick review turnaround", result.health_insights)

        # Full LLM response stored
        self.assertIn("health", result.llm_summary)

    def test_from_response_v6_format_high_friction(self):
        """Test parsing v6 response with high review friction."""
        response_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "ai": {
                                    "is_assisted": False,
                                    "tools": [],
                                    "usage_type": None,
                                    "confidence": 0.0,
                                },
                                "tech": {
                                    "languages": ["typescript", "python"],
                                    "frameworks": ["react", "django"],
                                    "categories": ["frontend", "backend"],
                                },
                                "summary": {
                                    "title": "Major database migration",
                                    "description": "Migrates from MySQL to PostgreSQL.",
                                    "type": "refactor",
                                },
                                "health": {
                                    "review_friction": "high",
                                    "scope": "xlarge",
                                    "risk_level": "high",
                                    "insights": [
                                        "5 review rounds indicates significant back-and-forth",
                                        "Large scope across 45 files requires careful review",
                                    ],
                                },
                            }
                        )
                    }
                }
            ]
        }

        result = BatchResult.from_response("pr-500", response_body)

        # Health assessment
        self.assertEqual(result.health_review_friction, "high")
        self.assertEqual(result.health_scope, "xlarge")
        self.assertEqual(result.health_risk_level, "high")
        self.assertEqual(result.summary_type, "refactor")

    def test_from_response_v5_format_no_health(self):
        """Test v5 response without health section still works."""
        response_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "ai": {
                                    "is_assisted": True,
                                    "tools": ["copilot"],
                                    "usage_type": "assisted",
                                    "confidence": 0.8,
                                },
                                "tech": {
                                    "languages": ["javascript"],
                                    "frameworks": ["express"],
                                    "categories": ["backend"],
                                },
                                "summary": {
                                    "title": "Add API endpoint",
                                    "description": "Adds new user API.",
                                    "type": "feature",
                                },
                            }
                        )
                    }
                }
            ]
        }

        result = BatchResult.from_response("pr-600", response_body)

        # Health assessment should be None when not present
        self.assertIsNone(result.health_review_friction)
        self.assertIsNone(result.health_scope)
        self.assertIsNone(result.health_risk_level)
        self.assertEqual(result.health_insights, [])

        # But AI and summary should still work
        self.assertTrue(result.is_ai_assisted)
        self.assertEqual(result.summary_type, "feature")


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

    def test_build_llm_pr_context_integration(self):
        """Test that build_llm_pr_context produces expected output for batch processing."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

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

        context = build_llm_pr_context(pr)

        # Verify all metadata is included (new format)
        self.assertIn("Title: Fix bug in AI module", context)
        self.assertIn("Test User (@testuser)", context)
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
            self.assertEqual(first_request["body"]["model"], "openai/gpt-oss-20b")
            self.assertEqual(first_request["body"]["response_format"], {"type": "json_object"})

            # Verify rich context is in user message (v6.2.0 unified format)
            user_content = first_request["body"]["messages"][1]["content"]
            self.assertIn("Analyze this pull request:", user_content)
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

    def test_build_llm_pr_context_with_files(self):
        """Test PR context includes files changed by category."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        pr = PullRequestFactory(team=self.team, body="Fix authentication")

        # Add files in different categories
        PRFileFactory(
            team=self.team,
            pull_request=pr,
            filename="src/components/Login.tsx",
            file_category="frontend",
            additions=50,
            deletions=10,
        )
        PRFileFactory(
            team=self.team,
            pull_request=pr,
            filename="apps/auth/views.py",
            file_category="backend",
            additions=30,
            deletions=5,
        )
        PRFileFactory(
            team=self.team,
            pull_request=pr,
            filename="tests/test_auth.py",
            file_category="test",
            additions=100,
            deletions=0,
        )

        context = build_llm_pr_context(pr)

        # Verify files section exists (new format)
        self.assertIn("Files changed:", context)
        self.assertIn("Login.tsx", context)
        self.assertIn("views.py", context)
        self.assertIn("test_auth.py", context)

    def test_build_llm_pr_context_with_commits(self):
        """Test PR context includes commit messages."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        member = TeamMemberFactory(team=self.team, github_username="dev1")
        pr = PullRequestFactory(team=self.team, author=member, body="Add feature")

        # Add commits with AI disclosure
        CommitFactory(
            team=self.team,
            pull_request=pr,
            author=member,
            message="feat: Add login form\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
        )
        CommitFactory(
            team=self.team,
            pull_request=pr,
            author=member,
            message="fix: Handle edge case",
        )

        context = build_llm_pr_context(pr)

        # Verify commits section with AI disclosure (new format)
        self.assertIn("Commits:", context)
        self.assertIn("Add login form", context)
        self.assertIn("Co-Authored-By: Claude", context)

    def test_build_llm_pr_context_with_reviews(self):
        """Test PR context includes review comments."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        author = TeamMemberFactory(team=self.team, github_username="author1")
        reviewer = TeamMemberFactory(team=self.team, github_username="reviewer1")
        pr = PullRequestFactory(team=self.team, author=author, body="Refactor module")

        # Add reviews with discussion
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=reviewer,
            body="This looks AI-generated. Did you use Cursor for this?",
            state="changes_requested",
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=reviewer,
            body="LGTM after changes",
            state="approved",
        )

        context = build_llm_pr_context(pr)

        # Verify reviews section (new format)
        self.assertIn("Reviews:", context)
        self.assertIn("Did you use Cursor", context)

    def test_build_llm_pr_context_with_all_data(self):
        """Test PR context with files, commits, and reviews combined."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        author = TeamMemberFactory(team=self.team, github_username="author1")
        reviewer = TeamMemberFactory(team=self.team, github_username="reviewer1")
        pr = PullRequestFactory(
            team=self.team,
            author=author,
            title="Add AI-powered search",
            body="## AI Disclosure\nUsed Cursor with Claude Sonnet for implementation",
            labels=["feature", "ai-assisted"],
        )

        # Add file
        PRFileFactory(team=self.team, pull_request=pr, filename="search.py")

        # Add commit with AI co-author
        CommitFactory(
            team=self.team,
            pull_request=pr,
            author=author,
            message="feat: AI search\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
        )

        # Add review
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=reviewer,
            body="Great use of AI here!",
        )

        context = build_llm_pr_context(pr)

        # Verify all sections present (new format)
        self.assertIn("Analyze this pull request:", context)
        self.assertIn("Description:", context)
        self.assertIn("Files changed:", context)
        self.assertIn("Commits:", context)
        self.assertIn("Reviews:", context)

        # Verify AI disclosure detected in multiple places
        self.assertIn("Cursor", context)
        self.assertIn("Claude", context)
        self.assertIn("ai-assisted", context)


class TestFallbackMethods(TestCase):
    """Tests for two-pass fallback batch processing methods."""

    def test_merge_results_no_failures(self):
        """Test merging when first pass has no failures."""
        processor = GroqBatchProcessor(api_key="test-key")

        first_results = [
            BatchResult(pr_id=1, is_ai_assisted=True, tools=["cursor"], confidence=0.9),
            BatchResult(pr_id=2, is_ai_assisted=False, tools=[], confidence=0.1),
        ]
        retry_results = []  # No retries needed

        merged = processor._merge_results(first_results, retry_results)

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].pr_id, 1)
        self.assertTrue(merged[0].is_ai_assisted)
        self.assertEqual(merged[1].pr_id, 2)

    def test_merge_results_replaces_failures(self):
        """Test that failures are replaced with retry results."""
        processor = GroqBatchProcessor(api_key="test-key")

        first_results = [
            BatchResult(pr_id=1, is_ai_assisted=True, tools=["cursor"], confidence=0.9),
            BatchResult(pr_id=2, is_ai_assisted=False, tools=[], confidence=0.0, error="JSON validation failed"),
            BatchResult(pr_id=3, is_ai_assisted=False, tools=[], confidence=0.0, error="Max tokens exceeded"),
        ]
        retry_results = [
            BatchResult(pr_id=2, is_ai_assisted=True, tools=["claude"], confidence=0.95),
            BatchResult(pr_id=3, is_ai_assisted=False, tools=[], confidence=0.2),
        ]

        merged = processor._merge_results(first_results, retry_results)

        self.assertEqual(len(merged), 3)
        # First result unchanged
        self.assertEqual(merged[0].pr_id, 1)
        self.assertIsNone(merged[0].error)
        # Second result replaced with retry
        self.assertEqual(merged[1].pr_id, 2)
        self.assertIsNone(merged[1].error)
        self.assertEqual(merged[1].tools, ["claude"])
        # Third result replaced with retry
        self.assertEqual(merged[2].pr_id, 3)
        self.assertIsNone(merged[2].error)
        self.assertEqual(merged[2].confidence, 0.2)

    def test_merge_results_keeps_error_if_retry_also_fails(self):
        """Test that if retry also fails, error is kept."""
        processor = GroqBatchProcessor(api_key="test-key")

        first_results = [
            BatchResult(pr_id=1, is_ai_assisted=False, tools=[], confidence=0.0, error="JSON validation failed"),
        ]
        retry_results = [
            BatchResult(pr_id=1, is_ai_assisted=False, tools=[], confidence=0.0, error="Still failed"),
        ]

        merged = processor._merge_results(first_results, retry_results)

        self.assertEqual(len(merged), 1)
        # Retry result replaces original (even if still an error)
        self.assertEqual(merged[0].error, "Still failed")

    def test_merge_results_adds_api_level_failures(self):
        """Test that PRs missing from first_results (API-level failures) get retry results added."""
        processor = GroqBatchProcessor(api_key="test-key")

        # PR 1 succeeded in first pass, PR 2 and 3 failed at API level (not in results)
        first_results = [
            BatchResult(pr_id=1, is_ai_assisted=True, tools=["cursor"], confidence=0.9),
        ]
        # Retry got results for PRs 2 and 3
        retry_results = [
            BatchResult(pr_id=2, is_ai_assisted=True, tools=["claude"], confidence=0.85),
            BatchResult(pr_id=3, is_ai_assisted=False, tools=[], confidence=0.95),
        ]
        # These were the failed PR IDs from error file
        failed_pr_ids = [2, 3]

        merged = processor._merge_results(first_results, retry_results, failed_pr_ids)

        # Should have all 3 PRs: 1 from first pass, 2 and 3 from retry
        self.assertEqual(len(merged), 3)
        pr_ids = {r.pr_id for r in merged}
        self.assertEqual(pr_ids, {1, 2, 3})

        # Verify results
        by_id = {r.pr_id: r for r in merged}
        self.assertEqual(by_id[1].tools, ["cursor"])  # From first pass
        self.assertEqual(by_id[2].tools, ["claude"])  # From retry
        self.assertFalse(by_id[3].is_ai_assisted)  # From retry

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_get_failed_pr_ids_from_error_file(self, mock_groq_class):
        """Test extracting failed PR IDs from error file."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        # Mock batch with error file
        mock_batch = MagicMock()
        mock_batch.id = "batch-123"
        mock_batch.status = "completed"
        mock_batch.request_counts.total = 5
        mock_batch.request_counts.completed = 3
        mock_batch.request_counts.failed = 2
        mock_batch.output_file_id = "output-file"
        mock_batch.error_file_id = "error-file-123"
        mock_client.batches.retrieve.return_value = mock_batch

        # Mock error file content
        error_jsonl = "\n".join(
            [
                '{"custom_id": "pr-100", "response": {"status_code": 400, '
                '"body": {"error": {"message": "JSON validation failed"}}}}',
                '{"custom_id": "pr-200", "response": {"status_code": 400, '
                '"body": {"error": {"message": "Max tokens exceeded"}}}}',
            ]
        )
        mock_response = MagicMock()
        mock_response.text.return_value = error_jsonl
        mock_client.files.content.return_value = mock_response

        processor = GroqBatchProcessor(api_key="test-key")
        failed_ids = processor._get_failed_pr_ids("batch-123")

        self.assertEqual(len(failed_ids), 2)
        self.assertIn(100, failed_ids)
        self.assertIn(200, failed_ids)

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_get_failed_pr_ids_no_error_file(self, mock_groq_class):
        """Test getting failed IDs when no error file exists."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_batch = MagicMock()
        mock_batch.status = "completed"
        mock_batch.request_counts.total = 5
        mock_batch.request_counts.completed = 5
        mock_batch.request_counts.failed = 0
        mock_batch.output_file_id = "output-file"
        mock_batch.error_file_id = None  # No errors
        mock_client.batches.retrieve.return_value = mock_batch

        processor = GroqBatchProcessor(api_key="test-key")
        failed_ids = processor._get_failed_pr_ids("batch-123")

        self.assertEqual(failed_ids, [])

    @patch("time.sleep")
    @patch("apps.integrations.services.groq_batch.Groq")
    def test_wait_for_completion_polls_until_done(self, mock_groq_class, mock_sleep):
        """Test that _wait_for_completion polls until batch is complete."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        # First call: in_progress, second call: completed
        in_progress_batch = MagicMock()
        in_progress_batch.id = "batch-123"
        in_progress_batch.status = "in_progress"
        in_progress_batch.request_counts.total = 2
        in_progress_batch.request_counts.completed = 1
        in_progress_batch.request_counts.failed = 0
        in_progress_batch.output_file_id = None
        in_progress_batch.error_file_id = None

        completed_batch = MagicMock()
        completed_batch.id = "batch-123"
        completed_batch.status = "completed"
        completed_batch.request_counts.total = 2
        completed_batch.request_counts.completed = 2
        completed_batch.request_counts.failed = 0
        completed_batch.output_file_id = "output-file"
        completed_batch.error_file_id = None

        # Need 3 responses: 1 for in_progress, 1 for completed (exit loop), 1 for get_results
        mock_client.batches.retrieve.side_effect = [in_progress_batch, completed_batch, completed_batch]

        # Mock results
        results_jsonl = (
            '{"custom_id": "pr-1", "response": {"body": {"choices": [{"message": '
            '{"content": "{\\"is_ai_assisted\\": true, \\"tools\\": [], \\"confidence\\": 0.8}"}}]}}}'
        )
        mock_response = MagicMock()
        mock_response.text.return_value = results_jsonl
        mock_client.files.content.return_value = mock_response

        processor = GroqBatchProcessor(api_key="test-key")
        results = processor._wait_for_completion("batch-123", poll_interval=5)

        # Should have polled twice, plus one call for get_results
        self.assertEqual(mock_client.batches.retrieve.call_count, 3)
        mock_sleep.assert_called_once_with(5)
        self.assertEqual(len(results), 1)

    def test_model_constants(self):
        """Test that model constants are defined correctly."""
        self.assertEqual(GroqBatchProcessor.DEFAULT_MODEL, "openai/gpt-oss-20b")
        self.assertEqual(GroqBatchProcessor.FALLBACK_MODEL, "llama-3.3-70b-versatile")

    def test_init_with_custom_model(self):
        """Test initializing processor with custom model."""
        processor = GroqBatchProcessor(api_key="test-key", model="custom-model")
        self.assertEqual(processor.model, "custom-model")

    def test_init_with_default_model(self):
        """Test initializing processor uses DEFAULT_MODEL by default."""
        processor = GroqBatchProcessor(api_key="test-key")
        self.assertEqual(processor.model, GroqBatchProcessor.DEFAULT_MODEL)


class TestJSONSchemaMode(TestCase):
    """Tests for JSON Schema mode support (strict structured outputs).

    JSON Schema mode can improve reliability from ~96% to ~100% by
    constraining model output at the token level.

    See: https://console.groq.com/docs/structured-outputs
    """

    def test_get_strict_schema_returns_valid_schema(self):
        """Test that get_strict_schema() returns a Groq-compatible schema."""
        from apps.integrations.services.groq_batch import get_strict_schema

        schema = get_strict_schema()

        # Must have required top-level keys for Groq
        self.assertIn("type", schema)
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)
        self.assertIn("required", schema)

        # Strict mode requires additionalProperties: false
        self.assertEqual(schema.get("additionalProperties"), False)

    def test_strict_schema_has_all_required_fields(self):
        """Test that strict schema has all fields required (no optional fields)."""
        from apps.integrations.services.groq_batch import get_strict_schema

        schema = get_strict_schema()

        # All top-level properties must be in required array
        required = set(schema.get("required", []))
        properties = set(schema.get("properties", {}).keys())
        self.assertEqual(required, properties)

    def test_strict_schema_no_null_types(self):
        """Test that strict schema doesn't use null union types.

        Groq strict mode requires explicit types, not ["string", "null"].
        usage_type in our schema needs special handling.
        """
        from apps.integrations.services.groq_batch import get_strict_schema

        schema = get_strict_schema()

        def check_no_null_unions(obj, path=""):
            """Recursively check for null union types."""
            if isinstance(obj, dict):
                if "type" in obj and isinstance(obj["type"], list) and "null" in obj["type"]:
                    self.fail(f"Found null union type at {path}: {obj['type']}")
                for key, value in obj.items():
                    check_no_null_unions(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_no_null_unions(item, f"{path}[{i}]")

        check_no_null_unions(schema)

    def test_processor_with_json_schema_mode(self):
        """Test that processor can be configured to use JSON Schema mode."""
        processor = GroqBatchProcessor(
            api_key="test-key",
            use_json_schema_mode=True,
        )
        self.assertTrue(processor.use_json_schema_mode)

    @patch("apps.integrations.services.groq_batch.Groq")
    def test_batch_file_uses_json_schema_format(self, mock_groq_class):
        """Test that batch file uses json_schema response_format when enabled."""
        import json
        import tempfile

        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        team = TeamFactory()
        member = TeamMemberFactory(team=team)
        pr = PullRequestFactory(
            team=team,
            author=member,
            body="Test PR",
            title="Test",
        )

        processor = GroqBatchProcessor(
            api_key="test-key",
            use_json_schema_mode=True,
        )

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            batch_file = processor.create_batch_file([pr], output_path=f.name)

            with open(batch_file) as bf:
                request = json.loads(bf.readline())

            # Should use json_schema format instead of json_object
            response_format = request["body"]["response_format"]
            self.assertEqual(response_format["type"], "json_schema")
            self.assertIn("json_schema", response_format)
            self.assertTrue(response_format["json_schema"].get("strict"))

    def test_strict_schema_matches_v6_structure(self):
        """Test that strict schema produces v6-compatible responses."""
        from apps.integrations.services.groq_batch import get_strict_schema

        schema = get_strict_schema()

        # Should have all 4 v6 sections
        properties = schema.get("properties", {})
        self.assertIn("ai", properties)
        self.assertIn("tech", properties)
        self.assertIn("summary", properties)
        self.assertIn("health", properties)

        # AI section should have required fields
        ai_props = properties["ai"]["properties"]
        self.assertIn("is_assisted", ai_props)
        self.assertIn("tools", ai_props)
        self.assertIn("confidence", ai_props)
