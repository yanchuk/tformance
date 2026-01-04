"""Tests for LLM analysis Celery tasks."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.metrics.factories import (
    CommitFactory,
    PRFileFactory,
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services.llm_prompts import PROMPT_VERSION

# Import tasks at module level for cleaner mocking
from apps.metrics.tasks import run_all_teams_llm_analysis, run_llm_analysis_batch


@patch("apps.metrics.tasks.time.sleep")  # Mock rate limit delays
class TestRunLLMAnalysisBatchTask(TestCase):
    """Tests for run_llm_analysis_batch task.

    Note: time.sleep is mocked at class level to avoid real rate limit delays.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_skips_prs_with_current_llm_summary(self, mock_sleep):
        """PRs with current llm_summary version are skipped."""
        # Create PR with current version
        PullRequestFactory(
            team=self.team,
            body="Some PR description",
            llm_summary={"ai": {"is_assisted": False}},
            llm_summary_version=PROMPT_VERSION,
        )

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
        ):
            result = run_llm_analysis_batch(team_id=self.team.id, limit=10)

        # Should not call API for already-analyzed PR
        mock_groq.return_value.chat.completions.create.assert_not_called()
        self.assertEqual(result["processed"], 0)

    def test_processes_prs_without_llm_summary(self, mock_sleep):
        """PRs without llm_summary are processed."""
        pr = PullRequestFactory(
            team=self.team,
            body="Test PR description",
            llm_summary=None,
            llm_summary_version="",  # Empty string for null-like state
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=(
                        '{"ai": {"is_assisted": false, "tools": [], "confidence": 0.0}, "health": {"scope": "small"}}'
                    )
                )
            )
        ]

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
        ):
            mock_groq.return_value.chat.completions.create.return_value = mock_response
            result = run_llm_analysis_batch(team_id=self.team.id, limit=10)

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["errors"], 0)

        # Verify PR was updated
        pr.refresh_from_db()
        self.assertIsNotNone(pr.llm_summary)
        self.assertEqual(pr.llm_summary_version, PROMPT_VERSION)

    def test_processes_prs_with_outdated_version(self, mock_sleep):
        """PRs with older llm_summary version are reprocessed."""
        pr = PullRequestFactory(
            team=self.team,
            body="Test PR description",
            llm_summary={"ai": {"is_assisted": True}},
            llm_summary_version="5.0.0",  # Older version
        )

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=(
                        '{"ai": {"is_assisted": true, "tools": ["claude"], "confidence": 0.9}, '
                        '"health": {"scope": "medium"}}'
                    )
                )
            )
        ]

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
        ):
            mock_groq.return_value.chat.completions.create.return_value = mock_response
            result = run_llm_analysis_batch(team_id=self.team.id, limit=10)

        self.assertEqual(result["processed"], 1)

        # Verify version was updated
        pr.refresh_from_db()
        self.assertEqual(pr.llm_summary_version, PROMPT_VERSION)

    def test_skips_prs_without_body(self, mock_sleep):
        """PRs with empty body are skipped."""
        PullRequestFactory(team=self.team, body="")
        # Note: body column has NOT NULL constraint, so we only test empty string

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
        ):
            result = run_llm_analysis_batch(team_id=self.team.id, limit=10)

        mock_groq.return_value.chat.completions.create.assert_not_called()
        self.assertEqual(result["processed"], 0)

    def test_respects_limit_parameter(self, mock_sleep):
        """Only processes up to limit PRs."""
        # Create 5 PRs
        for _ in range(5):
            PullRequestFactory(team=self.team, body="Test description")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"ai": {"is_assisted": false}, "health": {"scope": "small"}}'))
        ]

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
        ):
            mock_groq.return_value.chat.completions.create.return_value = mock_response
            result = run_llm_analysis_batch(team_id=self.team.id, limit=2)

        # Should only process 2 PRs
        self.assertEqual(result["processed"], 2)
        self.assertEqual(mock_groq.return_value.chat.completions.create.call_count, 2)

    def test_handles_api_errors_gracefully(self, mock_sleep):
        """API errors are caught and counted."""
        PullRequestFactory(team=self.team, body="Test description")

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
        ):
            mock_groq.return_value.chat.completions.create.side_effect = Exception("API Error")
            result = run_llm_analysis_batch(team_id=self.team.id, limit=10)

        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["errors"], 1)

    def test_raises_error_without_api_key(self, mock_sleep):
        """Raises ValueError when GROQ_API_KEY not set to properly fail pipeline."""
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(ValueError) as ctx:
            run_llm_analysis_batch(team_id=self.team.id, limit=10)

        self.assertIn("GROQ_API_KEY", str(ctx.exception))


class TestRunAllTeamsLLMAnalysisTask(TestCase):
    """Tests for run_all_teams_llm_analysis task."""

    def test_dispatches_tasks_for_all_teams(self):
        """Dispatches individual tasks for each team."""
        TeamFactory()
        TeamFactory()

        with patch("apps.metrics.tasks.run_llm_analysis_batch") as mock_task:
            mock_task.delay = MagicMock()
            result = run_all_teams_llm_analysis()

        self.assertEqual(mock_task.delay.call_count, 2)
        self.assertEqual(result["teams_dispatched"], 2)


@patch("apps.metrics.tasks.time.sleep")  # Mock rate limit delays
class TestLLMTaskDataExtraction(TestCase):
    """Tests for v6.1.0 data extraction in run_llm_analysis_batch.

    Note: time.sleep is mocked at class level to avoid real rate limit delays.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, display_name="John Developer")

    def _mock_response(self):
        """Create mock Groq response."""
        mock = MagicMock()
        mock.choices = [
            MagicMock(message=MagicMock(content='{"ai": {"is_assisted": false}, "health": {"scope": "small"}}'))
        ]
        return mock

    def test_extracts_file_paths_from_pr_files(self, mock_sleep):
        """File paths should be extracted and passed to prompt."""
        pr = PullRequestFactory(team=self.team, body="Test PR", author=self.author)
        PRFileFactory(pull_request=pr, team=self.team, filename="apps/auth/views.py")
        PRFileFactory(pull_request=pr, team=self.team, filename="tests/test_auth.py")

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
            patch("apps.metrics.tasks.get_user_prompt") as mock_prompt,
        ):
            mock_groq.return_value.chat.completions.create.return_value = self._mock_response()
            mock_prompt.return_value = "mocked prompt"
            run_llm_analysis_batch(team_id=self.team.id, limit=10)

        # Verify file_paths was passed
        call_kwargs = mock_prompt.call_args[1]
        self.assertIn("file_paths", call_kwargs)
        self.assertIn("apps/auth/views.py", call_kwargs["file_paths"])
        self.assertIn("tests/test_auth.py", call_kwargs["file_paths"])

    def test_extracts_commit_messages_from_commits(self, mock_sleep):
        """Commit messages should be extracted and passed to prompt."""
        pr = PullRequestFactory(team=self.team, body="Test PR", author=self.author)
        CommitFactory(pull_request=pr, team=self.team, message="Add login endpoint")
        CommitFactory(pull_request=pr, team=self.team, message="Fix typo")

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
            patch("apps.metrics.tasks.get_user_prompt") as mock_prompt,
        ):
            mock_groq.return_value.chat.completions.create.return_value = self._mock_response()
            mock_prompt.return_value = "mocked prompt"
            run_llm_analysis_batch(team_id=self.team.id, limit=10)

        # Verify commit_messages was passed
        call_kwargs = mock_prompt.call_args[1]
        self.assertIn("commit_messages", call_kwargs)
        self.assertIn("Add login endpoint", call_kwargs["commit_messages"])
        self.assertIn("Fix typo", call_kwargs["commit_messages"])

    def test_extracts_reviewers_from_pr_reviews(self, mock_sleep):
        """Reviewer names should be extracted and passed to prompt."""
        pr = PullRequestFactory(team=self.team, body="Test PR", author=self.author)
        reviewer1 = TeamMemberFactory(team=self.team, display_name="Alice Reviewer")
        reviewer2 = TeamMemberFactory(team=self.team, display_name="Bob Reviewer")
        PRReviewFactory(pull_request=pr, team=self.team, reviewer=reviewer1)
        PRReviewFactory(pull_request=pr, team=self.team, reviewer=reviewer2)

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
            patch("apps.metrics.tasks.get_user_prompt") as mock_prompt,
        ):
            mock_groq.return_value.chat.completions.create.return_value = self._mock_response()
            mock_prompt.return_value = "mocked prompt"
            run_llm_analysis_batch(team_id=self.team.id, limit=10)

        # Verify reviewers was passed
        call_kwargs = mock_prompt.call_args[1]
        self.assertIn("reviewers", call_kwargs)
        self.assertIn("Alice Reviewer", call_kwargs["reviewers"])
        self.assertIn("Bob Reviewer", call_kwargs["reviewers"])

    def test_extracts_pr_metadata(self, mock_sleep):
        """PR metadata (milestone, assignees, jira_key) should be passed."""
        PullRequestFactory(
            team=self.team,
            body="Test PR",
            author=self.author,
            milestone_title="Q1 2025 Release",
            assignees=["john", "jane"],
            linked_issues=[123, 456],
            jira_key="PROJ-1234",
        )

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
            patch("apps.metrics.tasks.get_user_prompt") as mock_prompt,
        ):
            mock_groq.return_value.chat.completions.create.return_value = self._mock_response()
            mock_prompt.return_value = "mocked prompt"
            run_llm_analysis_batch(team_id=self.team.id, limit=10)

        call_kwargs = mock_prompt.call_args[1]
        self.assertEqual(call_kwargs.get("milestone"), "Q1 2025 Release")
        self.assertEqual(call_kwargs.get("assignees"), ["john", "jane"])
        self.assertEqual(call_kwargs.get("jira_key"), "PROJ-1234")

    def test_extracts_author_name(self, mock_sleep):
        """Author display name should be passed to prompt."""
        PullRequestFactory(team=self.team, body="Test PR", author=self.author)

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
            patch("apps.metrics.tasks.get_user_prompt") as mock_prompt,
        ):
            mock_groq.return_value.chat.completions.create.return_value = self._mock_response()
            mock_prompt.return_value = "mocked prompt"
            run_llm_analysis_batch(team_id=self.team.id, limit=10)

        call_kwargs = mock_prompt.call_args[1]
        self.assertEqual(call_kwargs.get("author_name"), "John Developer")

    def test_works_with_no_related_data(self, mock_sleep):
        """Task should work when PR has no files, commits, or reviews."""
        PullRequestFactory(
            team=self.team,
            body="Simple PR",
            author=None,  # No author
            milestone_title="",  # No milestone
        )

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
            patch("apps.metrics.tasks.get_user_prompt") as mock_prompt,
        ):
            mock_groq.return_value.chat.completions.create.return_value = self._mock_response()
            mock_prompt.return_value = "mocked prompt"
            result = run_llm_analysis_batch(team_id=self.team.id, limit=10)

        self.assertEqual(result["processed"], 1)

        # Verify empty/None values are handled
        call_kwargs = mock_prompt.call_args[1]
        self.assertEqual(call_kwargs.get("file_paths"), [])
        self.assertEqual(call_kwargs.get("commit_messages"), [])
        self.assertEqual(call_kwargs.get("reviewers"), [])
        self.assertIsNone(call_kwargs.get("author_name"))


@patch("apps.metrics.tasks.time.sleep")  # Mock rate limit delays
class TestLLMBatchLimitNone(TestCase):
    """Tests for limit=None support in run_llm_analysis_batch.

    Two-Phase Onboarding requires processing ALL PRs in Phase 1.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def _mock_response(self):
        """Create mock Groq response."""
        mock = MagicMock()
        mock.choices = [
            MagicMock(message=MagicMock(content='{"ai": {"is_assisted": false}, "health": {"scope": "small"}}'))
        ]
        return mock

    def test_limit_none_processes_all_prs(self, mock_sleep):
        """When limit=None, all PRs should be processed (Two-Phase Onboarding)."""
        # Create 10 PRs
        for _ in range(10):
            PullRequestFactory(team=self.team, body="Test description")

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
        ):
            mock_groq.return_value.chat.completions.create.return_value = self._mock_response()
            result = run_llm_analysis_batch(team_id=self.team.id, limit=None)

        # Should process ALL 10 PRs
        self.assertEqual(result["processed"], 10)
        self.assertEqual(mock_groq.return_value.chat.completions.create.call_count, 10)

    def test_limit_none_works_with_many_prs(self, mock_sleep):
        """limit=None should handle more PRs than default limit of 50."""
        # Create 60 PRs (more than default limit of 50)
        for _ in range(60):
            PullRequestFactory(team=self.team, body="Test description")

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
        ):
            mock_groq.return_value.chat.completions.create.return_value = self._mock_response()
            result = run_llm_analysis_batch(team_id=self.team.id, limit=None)

        # Should process ALL 60 PRs
        self.assertEqual(result["processed"], 60)

    def test_default_limit_is_50(self, mock_sleep):
        """Default limit should be 50 for backward compatibility."""
        # Create 60 PRs
        for _ in range(60):
            PullRequestFactory(team=self.team, body="Test description")

        with (
            patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
            patch("apps.metrics.tasks.Groq") as mock_groq,
        ):
            mock_groq.return_value.chat.completions.create.return_value = self._mock_response()
            result = run_llm_analysis_batch(team_id=self.team.id)  # No limit specified

        # Should only process 50 (default limit)
        self.assertEqual(result["processed"], 50)


class TestLLMTaskTimeLimits(TestCase):
    """Tests for time limit configuration on run_llm_analysis_batch task.

    Time limits ensure the pipeline error handlers fire if the task hangs,
    preventing stuck onboarding pipelines (A-006 fix).
    """

    def test_task_has_soft_time_limit(self):
        """Task should have soft_time_limit=900 (15 min) to raise SoftTimeLimitExceeded."""
        self.assertEqual(run_llm_analysis_batch.soft_time_limit, 900)

    def test_task_has_hard_time_limit(self):
        """Task should have time_limit=960 (16 min) for hard kill if soft limit fails."""
        self.assertEqual(run_llm_analysis_batch.time_limit, 960)

    def test_task_has_max_retries(self):
        """Task should have max_retries=2 for transient failures."""
        self.assertEqual(run_llm_analysis_batch.max_retries, 2)

    def test_task_has_retry_delay(self):
        """Task should have default_retry_delay=300 (5 min) between retries."""
        self.assertEqual(run_llm_analysis_batch.default_retry_delay, 300)
