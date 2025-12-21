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

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_get_top_contributors_uses_token_pool(self, mock_github_class, mock_pool_class):
        """Test that get_top_contributors uses the token pool's client, not self._client directly."""
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

        # Mock PR with user
        mock_user = Mock()
        mock_user.id = 12345
        mock_user.login = "testuser"
        mock_user.name = "Test User"
        mock_user.avatar_url = "https://example.com/avatar.jpg"

        mock_pr = Mock()
        mock_pr.user = mock_user
        mock_pr.created_at = datetime.now(UTC) - timedelta(days=1)

        mock_repo.get_pulls.return_value = [mock_pr]

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Call get_top_contributors
        contributors = fetcher.get_top_contributors("test/repo", max_count=10)

        # Should have used _get_current_client() which uses the token pool
        mock_pool.get_best_client.assert_called()
        # Should have successfully retrieved contributors
        self.assertEqual(len(contributors), 1)
        self.assertEqual(contributors[0].github_login, "testuser")

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_get_top_contributors_works_with_multi_token_mode(self, mock_github_class, mock_pool_class):
        """Test that get_top_contributors method works correctly when initialized with multiple tokens."""
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

        # Mock multiple PRs from different users
        mock_users = []
        mock_prs = []
        for i in range(3):
            mock_user = Mock()
            mock_user.id = 12345 + i
            mock_user.login = f"user{i}"
            mock_user.name = f"User {i}"
            mock_user.avatar_url = f"https://example.com/avatar{i}.jpg"
            mock_users.append(mock_user)

            mock_pr = Mock()
            mock_pr.user = mock_user
            mock_pr.created_at = datetime.now(UTC) - timedelta(days=i)
            mock_prs.append(mock_pr)

        # Add more PRs for user0 to test sorting
        for _ in range(2):
            mock_pr = Mock()
            mock_pr.user = mock_users[0]
            mock_pr.created_at = datetime.now(UTC) - timedelta(days=5)
            mock_prs.append(mock_pr)

        mock_repo.get_pulls.return_value = mock_prs

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 12000  # Multiple tokens
        mock_pool_class.return_value = mock_pool

        tokens = ["ghp_token1", "ghp_token2", "ghp_token3"]
        fetcher = GitHubAuthenticatedFetcher(tokens=tokens)

        # Call get_top_contributors
        contributors = fetcher.get_top_contributors("test/repo", max_count=10)

        # Should have successfully retrieved and sorted contributors
        self.assertEqual(len(contributors), 3)
        # user0 should be first (3 PRs)
        self.assertEqual(contributors[0].github_login, "user0")
        self.assertEqual(contributors[0].pr_count, 3)
        # user1 should be second (1 PR)
        self.assertEqual(contributors[1].github_login, "user1")
        self.assertEqual(contributors[1].pr_count, 1)
        # user2 should be third (1 PR)
        self.assertEqual(contributors[2].github_login, "user2")
        self.assertEqual(contributors[2].pr_count, 1)


class TestGitHubFetcherCheckpointing(TestCase):
    """Tests for checkpoint-based resume functionality."""

    def setUp(self):
        """Set up test fixtures."""
        import tempfile

        self.temp_dir = tempfile.mkdtemp()
        self.checkpoint_file = f"{self.temp_dir}/test_checkpoint.json"

    def tearDown(self):
        """Clean up temporary files."""
        import os
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_mock_client(self, mock_github_class):
        """Helper to create a properly configured mock client."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        return mock_client

    def _create_mock_prs(self, count: int, start_number: int = 1):
        """Helper to create mock PR objects."""
        mock_prs = []
        for i in range(count):
            mock_pr = Mock()
            mock_pr.number = start_number + i
            mock_pr.id = 1000 + i
            mock_pr.draft = False
            mock_pr.created_at = datetime.now(UTC) - timedelta(days=i)
            mock_pr.updated_at = datetime.now(UTC) - timedelta(days=i)
            mock_prs.append(mock_pr)
        return mock_prs

    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_accepts_checkpoint_file_parameter(self, mock_github_class):
        """Test that fetcher can be initialized with a checkpoint_file parameter."""
        self._create_mock_client(mock_github_class)

        # Should accept checkpoint_file parameter
        fetcher = GitHubAuthenticatedFetcher(
            token="ghp_test_token",
            checkpoint_file=self.checkpoint_file,
        )

        self.assertEqual(fetcher.checkpoint_file, self.checkpoint_file)

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_checkpoint_saves_after_each_batch(self, mock_github_class, mock_pool_class):
        """Test that checkpoint file is updated after processing each batch of PRs."""
        import json
        import os

        mock_client = self._create_mock_client(mock_github_class)

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        # Mock repository and PRs
        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_prs = self._create_mock_prs(5)
        mock_repo.get_pulls.return_value = mock_prs

        fetcher = GitHubAuthenticatedFetcher(
            token="ghp_test_token",
            checkpoint_file=self.checkpoint_file,
        )

        # Mock _fetch_pr_details to return mocks with correct number attribute
        with patch.object(fetcher, "_fetch_pr_details") as mock_fetch_details:

            def return_mock_with_number(pr, repo_name):
                result = Mock()
                result.number = pr.number
                result.title = "Test"
                result.created_at = pr.created_at
                return result

            mock_fetch_details.side_effect = return_mock_with_number

            fetcher.fetch_prs_with_details("test/repo", max_prs=5)

        # Checkpoint file should exist and contain fetched PR numbers
        self.assertTrue(os.path.exists(self.checkpoint_file))

        with open(self.checkpoint_file) as f:
            checkpoint = json.load(f)

        # After completion, checkpoint should be marked as completed (empty PR list)
        self.assertTrue(checkpoint.get("completed", False))

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_checkpoint_contains_required_fields(self, mock_github_class, mock_pool_class):
        """Test that checkpoint contains project, repo, pr_numbers, and timestamp."""
        import json
        import os

        mock_client = self._create_mock_client(mock_github_class)

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo

        mock_prs = self._create_mock_prs(1, start_number=123)
        mock_repo.get_pulls.return_value = mock_prs

        fetcher = GitHubAuthenticatedFetcher(
            token="ghp_test_token",
            checkpoint_file=self.checkpoint_file,
        )

        with patch.object(fetcher, "_fetch_pr_details") as mock_fetch_details:

            def return_mock_with_number(pr, repo_name):
                result = Mock()
                result.number = pr.number
                result.title = "Test"
                result.created_at = pr.created_at
                return result

            mock_fetch_details.side_effect = return_mock_with_number

            fetcher.fetch_prs_with_details("owner/repo-name", max_prs=5)

        self.assertTrue(os.path.exists(self.checkpoint_file))

        with open(self.checkpoint_file) as f:
            checkpoint = json.load(f)

        # Required fields
        self.assertIn("repo", checkpoint)
        self.assertIn("last_updated", checkpoint)
        self.assertEqual(checkpoint["repo"], "owner/repo-name")

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_fetcher_resumes_from_checkpoint(self, mock_github_class, mock_pool_class):
        """Test that fetcher skips PRs already listed in checkpoint."""
        import json

        # Create checkpoint with some PRs already fetched
        checkpoint_data = {
            "repo": "test/repo",
            "fetched_pr_numbers": [1, 2, 3],
            "last_updated": datetime.now(UTC).isoformat(),
        }
        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)

        mock_client = self._create_mock_client(mock_github_class)

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo

        # PRs 1-5, but 1-3 are already in checkpoint
        mock_prs = self._create_mock_prs(5)
        mock_repo.get_pulls.return_value = mock_prs

        fetcher = GitHubAuthenticatedFetcher(
            token="ghp_test_token",
            checkpoint_file=self.checkpoint_file,
        )

        fetched_numbers = []
        with patch.object(fetcher, "_fetch_pr_details") as mock_fetch_details:

            def track_fetch(pr, repo_name):
                fetched_numbers.append(pr.number)
                result = Mock()
                result.number = pr.number
                result.title = "Test"
                result.created_at = pr.created_at
                return result

            mock_fetch_details.side_effect = track_fetch

            fetcher.fetch_prs_with_details("test/repo", max_prs=10)

        # Should only fetch PRs 4 and 5, not 1-3 (already in checkpoint)
        self.assertNotIn(1, fetched_numbers)
        self.assertNotIn(2, fetched_numbers)
        self.assertNotIn(3, fetched_numbers)
        self.assertIn(4, fetched_numbers)
        self.assertIn(5, fetched_numbers)

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_checkpoint_cleared_on_successful_completion(self, mock_github_class, mock_pool_class):
        """Test that checkpoint is cleared when all PRs are successfully fetched."""
        import json
        import os

        mock_client = self._create_mock_client(mock_github_class)

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo

        mock_prs = self._create_mock_prs(1)
        mock_repo.get_pulls.return_value = mock_prs

        fetcher = GitHubAuthenticatedFetcher(
            token="ghp_test_token",
            checkpoint_file=self.checkpoint_file,
        )

        with patch.object(fetcher, "_fetch_pr_details") as mock_fetch_details:

            def return_mock_with_number(pr, repo_name):
                result = Mock()
                result.number = pr.number
                result.title = "Test"
                result.created_at = pr.created_at
                return result

            mock_fetch_details.side_effect = return_mock_with_number

            # Fetch all PRs successfully
            result = fetcher.fetch_prs_with_details("test/repo", max_prs=5)

        # Should have fetched the PR
        self.assertEqual(len(result), 1)

        # Checkpoint should be cleared (marked as complete or empty)
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file) as f:
                checkpoint = json.load(f)
            # If file exists, it should be marked as complete or empty
            self.assertTrue(checkpoint.get("completed", False) or len(checkpoint.get("fetched_pr_numbers", [])) == 0)

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_checkpoint_handles_missing_file(self, mock_github_class, mock_pool_class):
        """Test that fetcher handles missing checkpoint file gracefully (fresh start)."""
        import os

        # Ensure checkpoint file doesn't exist
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)

        mock_client = self._create_mock_client(mock_github_class)

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_repo.get_pulls.return_value = []

        fetcher = GitHubAuthenticatedFetcher(
            token="ghp_test_token",
            checkpoint_file=self.checkpoint_file,
        )

        # Should not raise an exception
        result = fetcher.fetch_prs_with_details("test/repo", max_prs=5)

        # Should return empty list (no PRs to fetch)
        self.assertEqual(result, [])

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_checkpoint_handles_corrupt_file(self, mock_github_class, mock_pool_class):
        """Test that fetcher handles corrupt/invalid JSON in checkpoint gracefully."""
        # Create corrupt checkpoint file
        with open(self.checkpoint_file, "w") as f:
            f.write("{ invalid json }")

        mock_client = self._create_mock_client(mock_github_class)

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_repo.get_pulls.return_value = []

        fetcher = GitHubAuthenticatedFetcher(
            token="ghp_test_token",
            checkpoint_file=self.checkpoint_file,
        )

        # Should not raise an exception - treat as fresh start
        result = fetcher.fetch_prs_with_details("test/repo", max_prs=5)

        # Should return empty list (no PRs to fetch)
        self.assertEqual(result, [])

    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_checkpoint_handles_different_repo(self, mock_github_class, mock_pool_class):
        """Test that checkpoint for different repo is ignored (fresh start for new repo)."""
        import json

        # Create checkpoint for a different repo
        checkpoint_data = {
            "repo": "different/repo",
            "fetched_pr_numbers": [1, 2, 3],
            "last_updated": datetime.now(UTC).isoformat(),
        }
        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)

        mock_client = self._create_mock_client(mock_github_class)

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo

        mock_prs = self._create_mock_prs(1)
        mock_repo.get_pulls.return_value = mock_prs

        fetcher = GitHubAuthenticatedFetcher(
            token="ghp_test_token",
            checkpoint_file=self.checkpoint_file,
        )

        fetched_numbers = []
        with patch.object(fetcher, "_fetch_pr_details") as mock_fetch_details:

            def track_fetch(pr, repo_name):
                fetched_numbers.append(pr.number)
                result = Mock()
                result.number = pr.number
                result.title = "Test"
                result.created_at = pr.created_at
                return result

            mock_fetch_details.side_effect = track_fetch

            fetcher.fetch_prs_with_details("new/repo", max_prs=10)

        # Should fetch PR 1 because checkpoint is for different repo
        self.assertIn(1, fetched_numbers)


class TestSecondaryRateLimitDetection(TestCase):
    """Tests for secondary rate limit (abuse detection) handling.

    GitHub has two types of rate limits:
    1. Primary: Based on X-RateLimit-Remaining quota (5000/hour)
    2. Secondary: Abuse detection that triggers 403 even with quota remaining

    Secondary limits include a Retry-After header indicating how long to wait.
    """

    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_is_secondary_rate_limit_detects_retry_after_header(self, mock_github_class):
        """Test that secondary rate limit is detected by Retry-After header."""
        from github import GithubException

        from apps.metrics.seeding.github_authenticated_fetcher import is_secondary_rate_limit

        # Create 403 exception WITH Retry-After header (secondary limit)
        secondary_exception = GithubException(
            status=403,
            data={"message": "You have exceeded a secondary rate limit"},
            headers={"Retry-After": "60"},
        )

        self.assertTrue(is_secondary_rate_limit(secondary_exception))

    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_is_secondary_rate_limit_false_for_primary_limit(self, mock_github_class):
        """Test that primary rate limit (no Retry-After) is not detected as secondary."""
        from github import GithubException

        from apps.metrics.seeding.github_authenticated_fetcher import is_secondary_rate_limit

        # Create 403 exception WITHOUT Retry-After header (primary limit)
        primary_exception = GithubException(
            status=403,
            data={"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1234567890"},
        )

        self.assertFalse(is_secondary_rate_limit(primary_exception))

    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_is_secondary_rate_limit_false_for_non_403(self, mock_github_class):
        """Test that non-403 errors are not detected as secondary rate limit."""
        from github import GithubException

        from apps.metrics.seeding.github_authenticated_fetcher import is_secondary_rate_limit

        # Create 401 exception (not rate limit)
        auth_exception = GithubException(
            status=401,
            data={"message": "Bad credentials"},
            headers={},
        )

        self.assertFalse(is_secondary_rate_limit(auth_exception))

    @patch("apps.metrics.seeding.github_authenticated_fetcher.time")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_secondary_limit_waits_for_retry_after_duration(self, mock_github_class, mock_pool_class, mock_time):
        """Test that secondary rate limit causes wait based on Retry-After header."""
        from github import GithubException

        mock_client = Mock()
        mock_github_class.return_value = mock_client

        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        # Mock repo to raise secondary rate limit, then succeed
        mock_repo = Mock()
        secondary_exception = GithubException(
            status=403,
            data={"message": "You have exceeded a secondary rate limit"},
            headers={"Retry-After": "30"},
        )
        mock_client.get_repo.side_effect = [secondary_exception, mock_repo]
        mock_repo.get_pulls.return_value = []

        fetcher = GitHubAuthenticatedFetcher(token="ghp_test_token")

        # Fetch should succeed after waiting
        fetcher.fetch_prs_with_details("test/repo", max_prs=5)

        # Should have called sleep with the Retry-After value
        mock_time.sleep.assert_any_call(30)

    @patch("apps.metrics.seeding.github_authenticated_fetcher.time")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
    @patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
    def test_secondary_limit_logs_distinct_message(self, mock_github_class, mock_pool_class, mock_time):
        """Test that secondary rate limit logs a distinct message from primary."""
        from github import GithubException

        mock_client = Mock()
        mock_github_class.return_value = mock_client

        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        # Mock token pool
        mock_pool = Mock()
        mock_pool.get_best_client.return_value = mock_client
        mock_pool.total_remaining = 5000
        mock_pool_class.return_value = mock_pool

        # Mock repo to raise secondary rate limit (will exhaust retries)
        secondary_exception = GithubException(
            status=403,
            data={"message": "You have exceeded a secondary rate limit"},
            headers={"Retry-After": "60"},
        )
        mock_client.get_repo.side_effect = secondary_exception

        fetcher = GitHubAuthenticatedFetcher(token="ghp_test_token")

        with self.assertLogs("apps.metrics.seeding.github_authenticated_fetcher", level="WARNING") as log:
            fetcher.fetch_prs_with_details("test/repo", max_prs=5)

            log_output = " ".join(log.output)
            # Should log about secondary/abuse rate limit
            self.assertTrue(
                "secondary" in log_output.lower() or "abuse" in log_output.lower(),
                f"Expected 'secondary' or 'abuse' in log output: {log_output}",
            )
