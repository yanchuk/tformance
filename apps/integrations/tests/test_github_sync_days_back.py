"""Tests for sync_repository_history days_back parameter.

TDD RED Phase: These tests verify that sync_repository_history correctly
honors the days_back parameter to limit data fetched from GitHub.

Problem: Currently sync_repository_history ignores days_back and fetches ALL PRs,
causing memory issues and Celery timeouts for large repos (100k+ PRs).
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.integrations.services.github_sync import (
    get_repository_pull_requests,
    sync_repository_history,
)


class TestSyncRepositoryHistoryDaysBack(TestCase):
    """Tests for days_back parameter in sync_repository_history."""

    def setUp(self):
        """Set up test fixtures."""
        self.integration = GitHubIntegrationFactory()
        self.tracked_repo = TrackedRepositoryFactory(
            integration=self.integration,
            team=self.integration.team,
            full_name="test-org/test-repo",
        )

    @patch("apps.integrations.services.github_sync.get_repository_pull_requests")
    def test_sync_repository_history_passes_days_back_to_fetcher(self, mock_get_prs):
        """Test that days_back is passed to the PR fetching function.

        This test verifies that sync_repository_history actually uses
        the days_back parameter when fetching PRs from GitHub.
        """
        mock_get_prs.return_value = []

        # Call with days_back=30
        sync_repository_history(self.tracked_repo, days_back=30)

        # Verify days_back was passed to the fetcher
        mock_get_prs.assert_called_once()
        call_kwargs = mock_get_prs.call_args
        # The function should pass days_back to filter PRs
        self.assertIn("days_back", call_kwargs.kwargs)
        self.assertEqual(call_kwargs.kwargs["days_back"], 30)

    @patch("apps.integrations.services.github_sync._convert_pr_to_dict")
    @patch("apps.integrations.services.github_sync.Github")
    def test_get_repository_pull_requests_supports_days_back(self, mock_github_class, mock_convert):
        """Test that get_repository_pull_requests can filter by days_back.

        This test verifies the function signature accepts days_back and
        uses it to filter results by stopping iteration when hitting old PRs.
        """
        # Set up mock
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        # Create mock PRs with different dates (sorted by updated_at desc)
        now = timezone.now()

        recent_pr = MagicMock()
        recent_pr.number = 2
        recent_pr.created_at = now - timedelta(days=10)
        recent_pr.updated_at = now - timedelta(days=5)

        old_pr = MagicMock()
        old_pr.number = 1
        old_pr.created_at = now - timedelta(days=60)
        old_pr.updated_at = now - timedelta(days=60)

        # PRs returned in updated_at desc order (recent first)
        mock_repo.get_pulls.return_value = [recent_pr, old_pr]

        # Mock conversion
        mock_convert.side_effect = lambda pr: {"number": pr.number}

        # Call with days_back=30 - should only return recent PR
        result = get_repository_pull_requests(
            access_token="test-token",
            repo_full_name="test-org/test-repo",
            days_back=30,
        )

        # Convert generator to list
        result_list = list(result)

        # Should only have the recent PR (within 30 days)
        self.assertEqual(len(result_list), 1)
        self.assertEqual(result_list[0]["number"], 2)


class TestGetRepositoryPullRequestsMemoryEfficiency(TestCase):
    """Tests for memory-efficient PR fetching."""

    @patch("apps.integrations.services.github_sync._convert_pr_to_dict")
    @patch("apps.integrations.services.github_sync.Github")
    def test_returns_generator_not_list_for_large_repos(self, mock_github_class, mock_convert):
        """Test that function returns a generator for memory efficiency.

        For repos with 100k+ PRs, loading all into a list causes OOM.
        The function should return a generator/iterator instead.
        """
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        # Simulate PRs (PyGithub's PaginatedList is already lazy)
        mock_prs = [MagicMock(number=i) for i in range(10)]
        mock_repo.get_pulls.return_value = mock_prs

        # Mock the conversion to avoid complex PR object setup
        mock_convert.side_effect = lambda pr: {"number": pr.number}

        result = get_repository_pull_requests(
            access_token="test-token",
            repo_full_name="test-org/test-repo",
        )

        # Should return generator/iterator for memory efficiency
        import types

        self.assertIsInstance(
            result,
            types.GeneratorType,
            "Should return generator for memory efficiency, not list",
        )
