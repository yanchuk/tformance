"""
Tests for GitHubAuthenticatedFetcher integration with GitHubTokenPool.

These tests verify that the fetcher can use multiple GitHub tokens to increase
API throughput and automatically switch tokens when rate limits are hit.

Follows TDD approach - these tests are written BEFORE the integration exists.
They should all FAIL until GitHubAuthenticatedFetcher is updated to support token pooling.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from github import RateLimitExceededException

from apps.metrics.seeding.github_authenticated_fetcher import GitHubAuthenticatedFetcher


class TestGitHubAuthenticatedFetcherInitialization(TestCase):
    """Tests for GitHubAuthenticatedFetcher initialization with token pooling."""

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_accepts_multiple_tokens_parameter(self, mock_github_class, mock_pool_class):
        """Test that fetcher can be initialized with a list of tokens."""
        # Mock GitHub client
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock token pool
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool
        mock_pool.get_best_client.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        # Initialize with multiple tokens
        tokens = ["ghp_token1", "ghp_token2", "ghp_token3"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Should create token pool with the tokens
        mock_pool_class.assert_called_once_with(tokens=tokens)
        # Should have internal reference to pool
        self.assertIsNotNone(fetcher._token_pool)

    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_backward_compatible_with_single_token(self, mock_github_class):
        """Test that fetcher still works with single token parameter (backward compatibility)."""
        # Mock GitHub client
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        # Initialize with single token (old behavior)
        fetcher = GitHubAuthenticatedFetcher(token="ghp_single_token")

        # Should still work and use single client
        self.assertIsNotNone(fetcher._client)
        self.assertEqual(fetcher.token, "ghp_single_token")

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_uses_token_pool_internally(self, mock_github_class, mock_pool_class):
        """Test that fetcher uses GitHubTokenPool when multiple tokens are provided."""
        # Mock GitHub client
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock token pool
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool
        mock_pool.get_best_client.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        tokens = ["ghp_token1", "ghp_token2"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Internal _token_pool should be created
        self.assertIsNotNone(fetcher._token_pool)
        # Should be the mocked pool
        self.assertEqual(fetcher._token_pool, mock_pool)

    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_raises_error_when_both_token_and_tokens_provided(self, mock_github_class):
        """Test that providing both 'token' and 'tokens' raises a clear error."""
        with self.assertRaises(ValueError) as context:
            GitHubAuthenticatedFetcher(token="ghp_single", tokens=["ghp_multi1", "ghp_multi2"])

        # Error message should be clear
        self.assertIn("both", str(context.exception).lower())


class TestGitHubAuthenticatedFetcherTokenRotation(TestCase):
    """Tests for automatic token rotation when rate limits are hit."""

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_switches_token_on_rate_limit_exception(self, mock_github_class, mock_pool_class):
        """Test that fetcher automatically switches to another token when RateLimitExceededException occurs."""
        # Create two mock clients
        mock_client1 = Mock()
        mock_client2 = Mock()

        # Mock rate limit responses
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client1.get_rate_limit.return_value.rate = mock_rate
        mock_client2.get_rate_limit.return_value.rate = mock_rate

        # Mock repository
        mock_repo = Mock()

        # First call: mock_client1 raises RateLimitExceededException
        # Second call: mock_client2 succeeds
        mock_client1.get_repo.side_effect = RateLimitExceededException(
            status=403,
            data={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Reset": str(int((datetime.now(UTC) + timedelta(hours=1)).timestamp()))},
        )
        mock_client2.get_repo.return_value = mock_repo

        # Mock token pool to return different clients
        mock_pool = Mock()
        mock_pool.get_best_client.side_effect = [mock_client1, mock_client2]
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Mock pulls to avoid further API calls
        mock_repo.get_pulls.return_value = []

        # Fetch PRs - should switch tokens automatically
        fetcher.fetch_prs_with_details("test/repo", max_prs=10)

        # Should have called get_best_client twice (initial + retry with new token)
        self.assertEqual(mock_pool.get_best_client.call_count, 2)
        # Should have marked the first client as rate-limited
        mock_pool.mark_rate_limited.assert_called_once()

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_continues_fetching_after_token_switch(self, mock_github_class, mock_pool_class):
        """Test that fetcher successfully continues fetching PRs after switching tokens."""
        # Create two mock clients
        mock_client1 = Mock()
        mock_client2 = Mock()

        # Mock rate limit responses
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client1.get_rate_limit.return_value.rate = mock_rate
        mock_client2.get_rate_limit.return_value.rate = mock_rate

        # Mock repository and PRs
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.draft = False
        mock_pr.created_at = datetime.now(UTC)
        mock_pr.updated_at = datetime.now(UTC)

        # First call raises rate limit, second succeeds
        mock_client1.get_repo.side_effect = RateLimitExceededException(
            status=403,
            data={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Reset": str(int((datetime.now(UTC) + timedelta(hours=1)).timestamp()))},
        )
        mock_client2.get_repo.return_value = mock_repo
        mock_repo.get_pulls.return_value = [mock_pr]

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.side_effect = [mock_client1, mock_client2]
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Mock _fetch_pr_details to avoid detailed fetching
        with patch.object(fetcher, "_fetch_pr_details") as mock_fetch_details:
            mock_fetch_details.return_value = Mock(number=123, title="Test PR")

            # Should successfully fetch PRs after token switch
            result = fetcher.fetch_prs_with_details("test/repo", max_prs=10)

            # Should have successfully fetched
            self.assertIsNotNone(result)
            # Should have switched tokens
            self.assertEqual(mock_pool.get_best_client.call_count, 2)


class TestGitHubAuthenticatedFetcherRateLimitHandling(TestCase):
    """Tests for comprehensive rate limit handling."""

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_handles_all_tokens_exhausted_gracefully(self, mock_github_class, mock_pool_class):
        """Test that fetcher handles the case when all tokens are rate-limited."""
        from apps.metrics.seeding.github_token_pool import AllTokensExhaustedException

        # Mock GitHub client
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 0
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        # Mock token pool that raises AllTokensExhaustedException
        mock_pool = Mock()
        reset_time = datetime.now(UTC) + timedelta(hours=1)
        mock_pool.get_best_client.side_effect = AllTokensExhaustedException(reset_time=reset_time)
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Should handle all tokens exhausted gracefully (not crash)
        result = fetcher.fetch_prs_with_details("test/repo", max_prs=10)

        # Should return empty list when all tokens exhausted
        self.assertEqual(result, [])

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_logs_token_switch_events(self, mock_github_class, mock_pool_class):
        """Test that fetcher logs when switching between tokens."""
        # Mock clients
        mock_client1 = Mock()
        mock_client2 = Mock()

        # Mock rate limit responses
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client1.get_rate_limit.return_value.rate = mock_rate
        mock_client2.get_rate_limit.return_value.rate = mock_rate

        # First client raises rate limit
        mock_client1.get_repo.side_effect = RateLimitExceededException(
            status=403,
            data={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Reset": str(int((datetime.now(UTC) + timedelta(hours=1)).timestamp()))},
        )

        # Second client succeeds
        mock_repo = Mock()
        mock_client2.get_repo.return_value = mock_repo
        mock_repo.get_pulls.return_value = []

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.side_effect = [mock_client1, mock_client2]
        mock_pool.total_remaining = 3000
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Capture log output
        with self.assertLogs("apps.metrics.seeding.github_authenticated_fetcher", level="WARNING") as log_context:
            fetcher.fetch_prs_with_details("test/repo", max_prs=10)

            # Should have logged the token switch
            log_output = " ".join(log_context.output)
            self.assertIn("rate limit", log_output.lower())

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_get_rate_limit_remaining_uses_pool_total(self, mock_github_class, mock_pool_class):
        """Test that get_rate_limit_remaining() returns total from pool when using multiple tokens."""
        # Mock GitHub client
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        # Mock token pool with total_remaining
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 12000  # 3 tokens with 4000 each
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2", "ghp_token3"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Should return total from pool, not single client
        remaining = fetcher.get_rate_limit_remaining()
        self.assertEqual(remaining, 12000)


class TestGitHubAuthenticatedFetcherTokenPoolIntegration(TestCase):
    """Integration tests for token pool usage during PR fetching."""

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_uses_best_client_for_each_request(self, mock_github_class, mock_pool_class):
        """Test that fetcher requests best client from pool for each major operation."""
        # Mock GitHub client
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        # Mock repository
        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_repo.get_pulls.return_value = []

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Fetch PRs
        fetcher.fetch_prs_with_details("test/repo", max_prs=10)

        # Should have requested best client from pool
        self.assertGreater(mock_pool.get_best_client.call_count, 0)

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_marks_client_as_rate_limited_on_exception(self, mock_github_class, mock_pool_class):
        """Test that fetcher marks the client as rate-limited in the pool when exception occurs."""
        # Mock GitHub client
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        # Client raises rate limit exception
        reset_time = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_repo.side_effect = RateLimitExceededException(
            status=403,
            data={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Reset": str(int(reset_time.timestamp()))},
        )

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Try to fetch PRs
        fetcher.fetch_prs_with_details("test/repo", max_prs=10)

        # Should have called mark_rate_limited on the pool
        mock_pool.mark_rate_limited.assert_called()
        # First argument should be the client that hit the limit
        call_args = mock_pool.mark_rate_limited.call_args
        self.assertEqual(call_args[0][0], mock_client)

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_parallel_fetching_uses_token_pool(self, mock_github_class, mock_pool_class):
        """Test that parallel fetching also uses token pool for rate limit management."""
        # Mock GitHub client
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        # Mock repository with PRs
        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo

        # Create mock PRs
        mock_prs = []
        for i in range(5):
            mock_pr = Mock()
            mock_pr.number = i + 1
            mock_pr.draft = False
            mock_pr.created_at = datetime.now(UTC) - timedelta(days=i)
            mock_pr.updated_at = datetime.now(UTC) - timedelta(days=i)
            mock_prs.append(mock_pr)

        mock_repo.get_pulls.return_value = mock_prs

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Mock _fetch_pr_details to avoid complex mocking
        with patch.object(fetcher, "_fetch_pr_details") as mock_fetch_details:
            mock_fetch_details.return_value = Mock(number=1, title="Test")

            # Fetch PRs with parallel enabled
            fetcher.fetch_prs_with_details("test/repo", max_prs=5, parallel=True)

            # Should have used token pool
            self.assertGreater(mock_pool.get_best_client.call_count, 0)
