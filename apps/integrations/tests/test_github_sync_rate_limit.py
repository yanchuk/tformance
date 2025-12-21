"""Tests for GitHub sync rate limit integration.

Tests for modifying _process_prs() in apps/integrations/services/github_sync.py
to check rate limits after each PR and stop early if needed.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.factories import TrackedRepositoryFactory
from apps.integrations.services.github_sync import _process_prs


class TestProcessPRsRateLimitIntegration(TestCase):
    """Tests for rate limit checking in _process_prs()."""

    def _create_mock_pr_data(self, count=5):
        """Create mock PR data for testing.

        Args:
            count: Number of PRs to create

        Returns:
            List of PR dictionaries in the format returned by GitHub API
        """
        prs = []
        for i in range(count):
            prs.append(
                {
                    "id": 100000 + i,
                    "number": i + 1,
                    "title": f"Test PR #{i + 1}",
                    "state": "open",
                    "merged": False,
                    "merged_at": None,
                    "created_at": "2025-12-01T10:00:00Z",
                    "updated_at": "2025-12-01T12:00:00Z",
                    "additions": 50,
                    "deletions": 20,
                    "commits": 3,
                    "changed_files": 5,
                    "user": {
                        "id": 12345,
                        "login": "testuser",
                    },
                    "base": {
                        "ref": "main",
                    },
                    "head": {
                        "ref": f"feature-branch-{i}",
                        "sha": f"abc123def456{i:03d}",
                    },
                    "html_url": f"https://github.com/owner/repo/pull/{i + 1}",
                    "jira_key": "",
                }
            )
        return prs

    def _setup_github_rate_limit_mock(self, mock_github_class, remaining_values, reset_time=None):
        """Set up GitHub mock to return different rate limit values.

        Args:
            mock_github_class: The mocked Github class
            remaining_values: List of remaining values to return (one per call)
            reset_time: Optional reset timestamp (defaults to 2025-12-21 16:00:00 UTC)

        Returns:
            The mocked Github instance
        """
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        if reset_time is None:
            reset_time = datetime(2025, 12, 21, 16, 0, 0, tzinfo=UTC)

        # Set up rate limit responses
        rate_limit_responses = []
        for remaining in remaining_values:
            mock_rate_limit = MagicMock()
            mock_core = MagicMock()
            mock_core.remaining = remaining
            mock_core.limit = 5000
            mock_core.reset = reset_time
            mock_rate_limit.core = mock_core
            rate_limit_responses.append(mock_rate_limit)

        mock_github.get_rate_limit.side_effect = rate_limit_responses

        return mock_github

    @patch("apps.integrations.services.github_sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync._sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.calculate_pr_iteration_metrics")
    @patch("apps.integrations.services.github_sync.Github")
    def test_process_prs_updates_rate_limit_remaining(
        self,
        mock_github_class,
        mock_calc_metrics,
        mock_sync_reviews,
        mock_sync_commits,
        mock_sync_check_runs,
        mock_sync_files,
        mock_sync_issue_comments,
        mock_sync_review_comments,
    ):
        """Test that _process_prs updates TrackedRepository.rate_limit_remaining after processing PRs."""
        # Arrange
        tracked_repo = TrackedRepositoryFactory()
        prs_data = self._create_mock_pr_data(count=3)
        access_token = "gho_test_token"

        # Mock rate limit responses (decreasing from 500 -> 400 -> 300)
        self._setup_github_rate_limit_mock(mock_github_class, [500, 400, 300])

        # Mock sync functions to return 0
        mock_sync_reviews.return_value = 0
        mock_sync_commits.return_value = 0
        mock_sync_check_runs.return_value = 0
        mock_sync_files.return_value = 0
        mock_sync_issue_comments.return_value = 0
        mock_sync_review_comments.return_value = 0

        # Act
        _process_prs(prs_data, tracked_repo, access_token)

        # Assert - TrackedRepository should have rate_limit_remaining updated
        tracked_repo.refresh_from_db()
        self.assertEqual(tracked_repo.rate_limit_remaining, 300)

    @patch("apps.integrations.services.github_sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync._sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.calculate_pr_iteration_metrics")
    @patch("apps.integrations.services.github_sync.Github")
    def test_process_prs_updates_rate_limit_reset_at(
        self,
        mock_github_class,
        mock_calc_metrics,
        mock_sync_reviews,
        mock_sync_commits,
        mock_sync_check_runs,
        mock_sync_files,
        mock_sync_issue_comments,
        mock_sync_review_comments,
    ):
        """Test that _process_prs updates TrackedRepository.rate_limit_reset_at after processing PRs."""
        # Arrange
        tracked_repo = TrackedRepositoryFactory()
        prs_data = self._create_mock_pr_data(count=2)
        access_token = "gho_test_token"

        reset_time = datetime(2025, 12, 21, 17, 0, 0, tzinfo=UTC)

        # Set up rate limit mock with specific reset time
        self._setup_github_rate_limit_mock(mock_github_class, [500, 500], reset_time=reset_time)

        # Mock sync functions
        mock_sync_reviews.return_value = 0
        mock_sync_commits.return_value = 0
        mock_sync_check_runs.return_value = 0
        mock_sync_files.return_value = 0
        mock_sync_issue_comments.return_value = 0
        mock_sync_review_comments.return_value = 0

        # Act
        _process_prs(prs_data, tracked_repo, access_token)

        # Assert - TrackedRepository should have rate_limit_reset_at updated
        tracked_repo.refresh_from_db()
        self.assertEqual(tracked_repo.rate_limit_reset_at, reset_time)

    @patch("apps.integrations.services.github_sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync._sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.calculate_pr_iteration_metrics")
    @patch("apps.integrations.services.github_sync.Github")
    def test_process_prs_stops_when_rate_limited(
        self,
        mock_github_class,
        mock_calc_metrics,
        mock_sync_reviews,
        mock_sync_commits,
        mock_sync_check_runs,
        mock_sync_files,
        mock_sync_issue_comments,
        mock_sync_review_comments,
    ):
        """Test that _process_prs stops processing when rate_limit_remaining < 100."""
        # Arrange
        tracked_repo = TrackedRepositoryFactory()
        prs_data = self._create_mock_pr_data(count=5)
        access_token = "gho_test_token"

        # Mock rate limit: 500 -> 300 -> 99 (should stop after 3rd PR)
        self._setup_github_rate_limit_mock(mock_github_class, [500, 300, 99])

        # Mock sync functions
        mock_sync_reviews.return_value = 0
        mock_sync_commits.return_value = 0
        mock_sync_check_runs.return_value = 0
        mock_sync_files.return_value = 0
        mock_sync_issue_comments.return_value = 0
        mock_sync_review_comments.return_value = 0

        # Act
        result = _process_prs(prs_data, tracked_repo, access_token)

        # Assert - Should only sync 3 PRs, not all 5
        self.assertEqual(result["prs_synced"], 3)

        # Sync functions should only be called 3 times (once per PR)
        self.assertEqual(mock_sync_reviews.call_count, 3)
        self.assertEqual(mock_sync_commits.call_count, 3)

    @patch("apps.integrations.services.github_sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync._sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.calculate_pr_iteration_metrics")
    @patch("apps.integrations.services.github_sync.Github")
    def test_process_prs_returns_rate_limited_false_normally(
        self,
        mock_github_class,
        mock_calc_metrics,
        mock_sync_reviews,
        mock_sync_commits,
        mock_sync_check_runs,
        mock_sync_files,
        mock_sync_issue_comments,
        mock_sync_review_comments,
    ):
        """Test that _process_prs returns rate_limited: False when not rate limited."""
        # Arrange
        tracked_repo = TrackedRepositoryFactory()
        prs_data = self._create_mock_pr_data(count=3)
        access_token = "gho_test_token"

        # Mock rate limit with values always above threshold
        self._setup_github_rate_limit_mock(mock_github_class, [500, 400, 300])

        # Mock sync functions
        mock_sync_reviews.return_value = 0
        mock_sync_commits.return_value = 0
        mock_sync_check_runs.return_value = 0
        mock_sync_files.return_value = 0
        mock_sync_issue_comments.return_value = 0
        mock_sync_review_comments.return_value = 0

        # Act
        result = _process_prs(prs_data, tracked_repo, access_token)

        # Assert - Should have rate_limited: False in result
        self.assertIn("rate_limited", result)
        self.assertFalse(result["rate_limited"])

    @patch("apps.integrations.services.github_sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync_pr_commits")
    @patch("apps.integrations.services.github_sync._sync_pr_reviews")
    @patch("apps.integrations.services.github_sync.calculate_pr_iteration_metrics")
    @patch("apps.integrations.services.github_sync.Github")
    def test_process_prs_returns_rate_limited_true_when_stopped(
        self,
        mock_github_class,
        mock_calc_metrics,
        mock_sync_reviews,
        mock_sync_commits,
        mock_sync_check_runs,
        mock_sync_files,
        mock_sync_issue_comments,
        mock_sync_review_comments,
    ):
        """Test that _process_prs returns rate_limited: True when stopped early due to rate limit."""
        # Arrange
        tracked_repo = TrackedRepositoryFactory()
        prs_data = self._create_mock_pr_data(count=5)
        access_token = "gho_test_token"

        # Mock rate limit to hit threshold after 2 PRs
        self._setup_github_rate_limit_mock(mock_github_class, [500, 99])

        # Mock sync functions
        mock_sync_reviews.return_value = 0
        mock_sync_commits.return_value = 0
        mock_sync_check_runs.return_value = 0
        mock_sync_files.return_value = 0
        mock_sync_issue_comments.return_value = 0
        mock_sync_review_comments.return_value = 0

        # Act
        result = _process_prs(prs_data, tracked_repo, access_token)

        # Assert - Should have rate_limited: True in result
        self.assertIn("rate_limited", result)
        self.assertTrue(result["rate_limited"])

        # Should only process 2 PRs, not all 5
        self.assertEqual(result["prs_synced"], 2)
