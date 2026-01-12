"""Tests for GitHub sync service."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    GitHubOAuthError,
    get_pull_request_reviews,
)


class TestGetPullRequestReviews(TestCase):
    """Tests for fetching reviews for a specific pull request."""

    def _create_mock_review(
        self,
        review_id: int,
        user_id: int,
        user_login: str,
        state: str,
        body: str,
        submitted_at: str,
    ) -> MagicMock:
        """Create a mock PyGithub Review object with all required attributes."""
        mock_review = MagicMock()
        mock_review.id = review_id
        mock_review.state = state
        mock_review.body = body
        mock_review.submitted_at = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.login = user_login
        mock_review.user = mock_user

        return mock_review

    @patch("apps.integrations.services.github_sync.client.Github")
    def test_get_pull_request_reviews_returns_reviews(self, mock_github_class):
        """Test that get_pull_request_reviews returns list of reviews from GitHub API."""
        # Create mock reviews
        mock_review1 = self._create_mock_review(
            review_id=12345,
            user_id=2001,
            user_login="reviewer1",
            state="APPROVED",
            body="Looks good to me!",
            submitted_at="2025-01-05T14:30:00Z",
        )
        mock_review2 = self._create_mock_review(
            review_id=12346,
            user_id=2002,
            user_login="reviewer2",
            state="CHANGES_REQUESTED",
            body="Please fix the typo in line 45",
            submitted_at="2025-01-05T15:00:00Z",
        )

        # Mock PyGithub chain: Github().get_repo().get_pull().get_reviews()
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_reviews.return_value = [mock_review1, mock_review2]
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 101

        result = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Verify result contains reviews
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 12345)
        self.assertEqual(result[0]["state"], "APPROVED")
        self.assertEqual(result[0]["body"], "Looks good to me!")
        self.assertEqual(result[1]["id"], 12346)
        self.assertEqual(result[1]["state"], "CHANGES_REQUESTED")

        # Verify PyGithub was called correctly
        mock_github_class.assert_called_once_with(access_token)
        mock_github.get_repo.assert_called_once_with(repo_full_name)
        mock_repo.get_pull.assert_called_once_with(pr_number)
        mock_pr.get_reviews.assert_called_once()

    @patch("apps.integrations.services.github_sync.client.Github")
    def test_get_pull_request_reviews_handles_empty_reviews(self, mock_github_class):
        """Test that get_pull_request_reviews returns empty list when no reviews exist."""
        # Mock PyGithub chain to return empty list
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_reviews.return_value = []
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 999

        result = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Verify result is an empty list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

        # Verify PyGithub was called correctly
        mock_github_class.assert_called_once_with(access_token)
        mock_github.get_repo.assert_called_once_with(repo_full_name)
        mock_repo.get_pull.assert_called_once_with(pr_number)

    @patch("apps.integrations.services.github_sync.client.Github")
    def test_get_pull_request_reviews_handles_pagination(self, mock_github_class):
        """Test that PyGithub handles pagination automatically (no manual pagination needed)."""
        # Create multiple mock reviews (PyGithub handles pagination internally)
        mock_reviews = [
            self._create_mock_review(
                review_id=i,
                user_id=2000 + i,
                user_login=f"reviewer{i}",
                state="APPROVED",
                body=f"Review {i}",
                submitted_at=f"2025-01-{1 + (i // 24):02d}T{i % 24:02d}:00:00Z",
            )
            for i in range(1, 151)  # 150 reviews - would span multiple pages
        ]

        # Mock PyGithub chain
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_reviews.return_value = mock_reviews  # PyGithub returns all reviews automatically
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 101

        result = get_pull_request_reviews(access_token, repo_full_name, pr_number)

        # Verify all reviews were returned (PyGithub handled pagination internally)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 150, "Should return all reviews - PyGithub handles pagination")
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[-1]["id"], 150)

        # Verify only one call was made to get_reviews (PyGithub handles pagination internally)
        mock_pr.get_reviews.assert_called_once()

    @patch("apps.integrations.services.github_sync.client.Github")
    def test_get_pull_request_reviews_raises_on_api_error(self, mock_github_class):
        """Test that get_pull_request_reviews raises GitHubOAuthError on API errors."""
        from github import GithubException

        # Mock PyGithub to raise exception (404, 403, etc)
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_reviews.side_effect = GithubException(404, {"message": "Not Found"})
        mock_repo.get_pull.return_value = mock_pr
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        access_token = "gho_test_token"
        repo_full_name = "acme-corp/backend-api"
        pr_number = 99999

        with self.assertRaises(GitHubOAuthError) as context:
            get_pull_request_reviews(access_token, repo_full_name, pr_number)

        self.assertIn("404", str(context.exception))
