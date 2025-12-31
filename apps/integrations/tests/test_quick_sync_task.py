"""Tests for Quick Sync Task (7-day fast sync for initial insights).

TDD RED Phase: These tests verify the behavior of sync_quick_data_task which
provides fast initial data sync (7 days only, pattern detection only, no LLM).
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    TrackedRepositoryFactory,
)
from apps.integrations.models import TrackedRepository
from apps.metrics.factories import PullRequestFactory, TeamFactory


class TestSyncQuickDataTaskExists(TestCase):
    """Tests that sync_quick_data_task exists and is callable."""

    def test_sync_quick_data_task_is_importable(self):
        """Test that sync_quick_data_task can be imported from tasks module."""
        from apps.integrations.tasks import sync_quick_data_task

        # Verify it exists and is callable
        self.assertTrue(callable(sync_quick_data_task))

    def test_sync_quick_data_task_is_celery_task(self):
        """Test that sync_quick_data_task is a Celery shared_task."""
        from apps.integrations.tasks import sync_quick_data_task

        # Celery tasks have a 'delay' method
        self.assertTrue(hasattr(sync_quick_data_task, "delay"))

    def test_sync_quick_data_task_accepts_repo_id_argument(self):
        """Test that sync_quick_data_task accepts repo_id as an argument."""
        from apps.integrations.tasks import sync_quick_data_task

        # Call with a non-existent ID to verify it accepts the argument
        # (should return error dict, not raise TypeError)
        result = sync_quick_data_task(99999)

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)


class TestSyncQuickDataTaskFetches7Days(TestCase):
    """Tests that sync_quick_data_task only fetches PRs from the last 7 days."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
            is_active=True,
        )

    @patch("apps.integrations.tasks.sync_full_history_task.delay")
    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_sync_quick_data_task_syncs_only_7_days(self, mock_sync, mock_full_history):
        """Test that sync_quick_data_task passes days_back=7 to sync function."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {
            "prs_synced": 5,
            "reviews_synced": 3,
            "errors": [],
        }

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Verify sync was called with days_back=7
        mock_sync.assert_called_once()
        call_kwargs = mock_sync.call_args
        # Check either positional or keyword argument for days_back
        days_back = call_kwargs[0][1] if len(call_kwargs[0]) >= 2 else call_kwargs[1].get("days_back")

        self.assertEqual(days_back, 7)

        # Verify full history sync was queued
        mock_full_history.assert_called_once_with(self.tracked_repo.id)

    @patch("apps.integrations.tasks.get_repository_pull_requests")
    def test_sync_quick_data_task_filters_prs_by_7_day_window(self, mock_get_prs):
        """Test that only PRs from last 7 days are processed."""
        from apps.integrations.tasks import sync_quick_data_task

        now = timezone.now()

        # Mock PRs with various ages
        mock_get_prs.return_value = [
            {
                "id": 1,
                "number": 1,
                "title": "PR from 2 days ago",
                "created_at": (now - timedelta(days=2)).isoformat(),
                "updated_at": (now - timedelta(days=1)).isoformat(),
                "state": "merged",
                "merged": True,
                "merged_at": (now - timedelta(days=1)).isoformat(),
                "additions": 100,
                "deletions": 50,
                "commits": 3,
                "changed_files": 5,
                "user": {"id": 12345, "login": "developer1"},
                "base": {"ref": "main"},
                "head": {"ref": "feature/branch", "sha": "abc123"},
                "html_url": "https://github.com/acme-corp/api-server/pull/1",
                "jira_key": "",
            },
            {
                "id": 2,
                "number": 2,
                "title": "PR from 10 days ago",
                "created_at": (now - timedelta(days=10)).isoformat(),
                "updated_at": (now - timedelta(days=8)).isoformat(),
                "state": "merged",
                "merged": True,
                "merged_at": (now - timedelta(days=8)).isoformat(),
                "additions": 200,
                "deletions": 100,
                "commits": 5,
                "changed_files": 8,
                "user": {"id": 12346, "login": "developer2"},
                "base": {"ref": "main"},
                "head": {"ref": "feature/old", "sha": "def456"},
                "html_url": "https://github.com/acme-corp/api-server/pull/2",
                "jira_key": "",
            },
        ]

        # Call the task
        result = sync_quick_data_task(self.tracked_repo.id)

        # Should only sync the recent PR (within 7 days)
        self.assertEqual(result.get("prs_synced", 0), 1)


class TestSyncQuickDataTaskUpdatesProgress(TestCase):
    """Tests that sync_quick_data_task updates TrackedRepository progress fields."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
            is_active=True,
            sync_status=TrackedRepository.SYNC_STATUS_PENDING,
        )

    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_sets_sync_status_to_syncing_during_sync(self, mock_sync):
        """Test that sync_status is set to 'syncing' during the sync process."""
        from apps.integrations.tasks import sync_quick_data_task

        def check_status_during_sync(repo, *args, **kwargs):
            repo.refresh_from_db()
            assert repo.sync_status == TrackedRepository.SYNC_STATUS_SYNCING
            return {"prs_synced": 5, "reviews_synced": 3, "errors": []}

        mock_sync.side_effect = check_status_during_sync

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Status was checked during execution (via side_effect)

    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_sets_sync_started_at_when_starting(self, mock_sync):
        """Test that sync_started_at is set when sync begins."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}

        # Verify no sync_started_at initially
        self.assertIsNone(self.tracked_repo.sync_started_at)

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Verify sync_started_at is set
        self.tracked_repo.refresh_from_db()
        self.assertIsNotNone(self.tracked_repo.sync_started_at)

    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_sets_sync_status_to_complete_on_success(self, mock_sync):
        """Test that sync_status is set to 'complete' after successful sync."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Verify status is complete
        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_status, TrackedRepository.SYNC_STATUS_COMPLETE)


class TestSyncQuickDataTaskQueuesFullSync(TestCase):
    """Tests that sync_quick_data_task queues sync_full_history_task after completion."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
            is_active=True,
        )

    @patch("apps.integrations.tasks.sync_full_history_task")
    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_queues_full_sync_after_quick_sync_completes(self, mock_sync, mock_full_sync_task):
        """Test that sync_full_history_task is queued after quick sync completes."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}
        mock_delay = MagicMock()
        mock_full_sync_task.delay = mock_delay

        # Call the task
        result = sync_quick_data_task(self.tracked_repo.id)

        # Verify sync_full_history_task.delay was called with repo_id
        mock_delay.assert_called_once_with(self.tracked_repo.id)

        # Verify result indicates full sync was queued
        self.assertTrue(result.get("full_sync_queued", False))

    @patch("apps.integrations.tasks.sync_full_history_task")
    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_does_not_queue_full_sync_on_error(self, mock_sync, mock_full_sync_task):
        """Test that sync_full_history_task is NOT queued if quick sync fails."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.side_effect = Exception("GitHub API error")
        mock_delay = MagicMock()
        mock_full_sync_task.delay = mock_delay

        # Mock retry to simulate exhausted retries
        with patch.object(sync_quick_data_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            with patch("sentry_sdk.capture_exception"):
                # Call the task
                sync_quick_data_task(self.tracked_repo.id)

        # Verify sync_full_history_task.delay was NOT called
        mock_delay.assert_not_called()


class TestSyncQuickDataTaskSkipsLLM(TestCase):
    """Tests that sync_quick_data_task skips LLM analysis."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
            is_active=True,
        )

    @patch("apps.integrations.services.groq_batch.GroqBatchProcessor")
    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_does_not_call_llm_analysis(self, mock_sync, mock_groq_processor):
        """Test that LLM analysis is NOT called during quick sync."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Verify GroqBatchProcessor was NOT instantiated (no LLM calls)
        mock_groq_processor.assert_not_called()

    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_prs_have_no_llm_summary_after_quick_sync(self, mock_sync):
        """Test that PRs synced via quick sync do not have llm_summary set."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}

        # Create some PRs that would be synced
        pr = PullRequestFactory(
            team=self.team,
            github_repo=self.tracked_repo.full_name,
            body="Generated by Claude",  # Would trigger AI detection
        )

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Verify PR does not have llm_summary
        pr.refresh_from_db()
        self.assertIsNone(pr.llm_summary)


class TestSyncQuickDataTaskRunsPatternDetection(TestCase):
    """Tests that sync_quick_data_task runs pattern detection (regex-based AI detection)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
            is_active=True,
        )

    @patch("apps.metrics.services.ai_detector.detect_ai_in_text")
    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_runs_pattern_detection_on_synced_prs(self, mock_sync, mock_detect_ai):
        """Test that pattern detection is called on synced PRs."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 5, "reviews_synced": 3, "errors": []}
        mock_detect_ai.return_value = MagicMock(
            detected=True,
            tools=["copilot"],
        )

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Verify pattern detection was called (at least once for synced PRs)
        self.assertTrue(mock_detect_ai.called)

    @patch("apps.integrations.tasks.sync_full_history_task.delay")
    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_prs_have_is_ai_assisted_set_after_quick_sync(self, mock_sync, mock_full_history):
        """Test that PRs have is_ai_assisted field populated after quick sync."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.return_value = {"prs_synced": 1, "reviews_synced": 0, "errors": []}

        # Create a PR with AI signature in body
        pr = PullRequestFactory(
            team=self.team,
            github_repo=self.tracked_repo.full_name,
            body="Generated with GitHub Copilot",
            is_ai_assisted=None,  # Not set initially
        )

        # Call the task
        sync_quick_data_task(self.tracked_repo.id)

        # Verify is_ai_assisted is now set (True or False based on pattern detection)
        pr.refresh_from_db()
        self.assertIsNotNone(pr.is_ai_assisted)


class TestSyncQuickDataTaskHandlesErrors(TestCase):
    """Tests error handling for sync_quick_data_task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
            is_active=True,
        )

    def test_returns_error_for_nonexistent_repo(self):
        """Test that task returns error for non-existent repo ID."""
        from apps.integrations.tasks import sync_quick_data_task

        result = sync_quick_data_task(99999)

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    def test_skips_inactive_repos(self):
        """Test that task skips inactive repositories."""
        from apps.integrations.tasks import sync_quick_data_task

        self.tracked_repo.is_active = False
        self.tracked_repo.save()

        result = sync_quick_data_task(self.tracked_repo.id)

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("skipped", False))
        self.assertIn("not active", result.get("reason", "").lower())

    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_sets_error_status_on_permanent_failure(self, mock_sync):
        """Test that sync_status is set to 'error' on permanent failure."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.side_effect = Exception("GitHub API rate limit exceeded")

        with patch.object(sync_quick_data_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            with patch("sentry_sdk.capture_exception"):
                sync_quick_data_task(self.tracked_repo.id)

        self.tracked_repo.refresh_from_db()
        self.assertEqual(self.tracked_repo.sync_status, TrackedRepository.SYNC_STATUS_ERROR)

    @patch("apps.integrations.tasks._sync_with_graphql_or_rest")
    def test_saves_error_message_on_failure(self, mock_sync):
        """Test that sanitized last_sync_error is populated on failure."""
        from apps.integrations.tasks import sync_quick_data_task

        mock_sync.side_effect = Exception("GitHub API rate limit exceeded")

        with patch.object(sync_quick_data_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            with patch("sentry_sdk.capture_exception"):
                sync_quick_data_task(self.tracked_repo.id)

        self.tracked_repo.refresh_from_db()
        self.assertIsNotNone(self.tracked_repo.last_sync_error)
        # Sanitized message should be user-friendly, not exposing internal details
        self.assertIn("error occurred", self.tracked_repo.last_sync_error.lower())


class TestSyncFullHistoryTaskExists(TestCase):
    """Tests that sync_full_history_task exists (companion task for full sync after quick sync)."""

    def test_sync_full_history_task_is_importable(self):
        """Test that sync_full_history_task can be imported from tasks module."""
        from apps.integrations.tasks import sync_full_history_task

        # Verify it exists and is callable
        self.assertTrue(callable(sync_full_history_task))

    def test_sync_full_history_task_is_celery_task(self):
        """Test that sync_full_history_task is a Celery shared_task."""
        from apps.integrations.tasks import sync_full_history_task

        # Celery tasks have a 'delay' method
        self.assertTrue(hasattr(sync_full_history_task, "delay"))

    def test_sync_full_history_task_accepts_repo_id_argument(self):
        """Test that sync_full_history_task accepts repo_id as an argument."""
        from apps.integrations.tasks import sync_full_history_task

        # Call with a non-existent ID to verify it accepts the argument
        result = sync_full_history_task(99999)

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
