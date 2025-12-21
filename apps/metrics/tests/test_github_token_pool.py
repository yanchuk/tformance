"""
Tests for GitHubTokenPool - multiple token management for higher API throughput.

Follows TDD approach - these tests are written BEFORE implementation.
They should all FAIL until the GitHubTokenPool class is implemented.
"""

import threading
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from django.test import TestCase

from apps.metrics.seeding.github_token_pool import (
    AllTokensExhaustedException,
    GitHubTokenPool,
    TokenInfo,
)


class TestTokenInfo(TestCase):
    """Tests for TokenInfo dataclass."""

    def test_masked_token_hides_middle_of_token(self):
        """Test that masked_token property masks the middle of the token for security."""
        token = "ghp_1234567890abcdefghijklmnop"
        mock_client = Mock()

        token_info = TokenInfo(token=token, client=mock_client)

        # Should show first 4 and last 4 chars only
        self.assertEqual(token_info.masked_token, "ghp_...mnop")

    def test_masked_token_handles_short_tokens(self):
        """Test that masked_token handles tokens shorter than 8 characters."""
        token = "short"
        mock_client = Mock()

        token_info = TokenInfo(token=token, client=mock_client)

        # Should return just asterisks for short tokens
        self.assertEqual(token_info.masked_token, "***")

    def test_refresh_rate_limit_updates_remaining_count(self):
        """Test that refresh_rate_limit() updates the remaining request count from API."""
        token = "ghp_test_token"

        # Mock the GitHub client and rate limit response
        mock_rate = Mock()
        mock_rate.remaining = 4500
        mock_rate.reset = datetime(2025, 12, 21, 12, 0, 0, tzinfo=UTC)

        mock_rate_limit = Mock()
        mock_rate_limit.rate = mock_rate

        mock_client = Mock()
        mock_client.get_rate_limit.return_value = mock_rate_limit

        token_info = TokenInfo(token=token, client=mock_client)
        token_info.refresh_rate_limit()

        # Should update remaining and reset_time
        self.assertEqual(token_info.remaining, 4500)
        self.assertEqual(token_info.reset_time, datetime(2025, 12, 21, 12, 0, 0, tzinfo=UTC))
        self.assertFalse(token_info.is_exhausted)

    def test_refresh_rate_limit_marks_exhausted_when_zero(self):
        """Test that refresh_rate_limit() marks token as exhausted when remaining is 0."""
        token = "ghp_test_token"

        mock_rate = Mock()
        mock_rate.remaining = 0
        mock_rate.reset = datetime(2025, 12, 21, 12, 0, 0, tzinfo=UTC)

        mock_rate_limit = Mock()
        mock_rate_limit.rate = mock_rate

        mock_client = Mock()
        mock_client.get_rate_limit.return_value = mock_rate_limit

        token_info = TokenInfo(token=token, client=mock_client)
        token_info.refresh_rate_limit()

        # Should mark as exhausted
        self.assertEqual(token_info.remaining, 0)
        self.assertTrue(token_info.is_exhausted)

    def test_refresh_rate_limit_handles_api_errors_gracefully(self):
        """Test that refresh_rate_limit() handles GitHub API errors without crashing."""
        from github import GithubException

        token = "ghp_test_token"
        mock_client = Mock()
        mock_client.get_rate_limit.side_effect = GithubException(500, "Server error")

        token_info = TokenInfo(token=token, client=mock_client, remaining=3000)
        initial_remaining = token_info.remaining

        # Should not crash, should keep previous values
        token_info.refresh_rate_limit()
        self.assertEqual(token_info.remaining, initial_remaining)


class TestGitHubTokenPoolInitialization(TestCase):
    """Tests for GitHubTokenPool initialization."""

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_single_token_initialization(self, mock_github_class):
        """Test that pool can be initialized with a single token."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        pool = GitHubTokenPool(tokens=["ghp_single_token"])

        # Should have one token
        self.assertEqual(len(pool._tokens), 1)
        self.assertEqual(pool._tokens[0].token, "ghp_single_token")
        mock_github_class.assert_called_once_with("ghp_single_token")

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_multiple_token_initialization(self, mock_github_class):
        """Test that pool can be initialized with multiple tokens."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        tokens = ["ghp_token1", "ghp_token2", "ghp_token3"]
        pool = GitHubTokenPool(tokens=tokens)

        # Should have three tokens
        self.assertEqual(len(pool._tokens), 3)
        self.assertEqual(pool._tokens[0].token, "ghp_token1")
        self.assertEqual(pool._tokens[1].token, "ghp_token2")
        self.assertEqual(pool._tokens[2].token, "ghp_token3")
        self.assertEqual(mock_github_class.call_count, 3)

    def test_empty_token_list_raises_error(self):
        """Test that initializing with empty token list raises ValueError."""
        with self.assertRaises(ValueError) as context:
            GitHubTokenPool(tokens=[])

        self.assertIn("No GitHub tokens provided", str(context.exception))

    def test_none_tokens_without_env_var_raises_error(self):
        """Test that initializing without tokens or env vars raises ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError) as context:
                GitHubTokenPool(tokens=None)

            self.assertIn("No GitHub tokens provided", str(context.exception))

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_env_var_github_seeding_tokens_comma_separated(self, mock_github_class):
        """Test that pool loads from GITHUB_SEEDING_TOKENS env var (comma-separated)."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        with patch.dict("os.environ", {"GITHUB_SEEDING_TOKENS": "ghp_env1,ghp_env2,ghp_env3"}):
            pool = GitHubTokenPool(tokens=None)

        # Should parse comma-separated tokens
        self.assertEqual(len(pool._tokens), 3)
        self.assertEqual(pool._tokens[0].token, "ghp_env1")
        self.assertEqual(pool._tokens[1].token, "ghp_env2")
        self.assertEqual(pool._tokens[2].token, "ghp_env3")

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_env_var_github_seeding_tokens_handles_whitespace(self, mock_github_class):
        """Test that env var parsing strips whitespace from tokens."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        with patch.dict("os.environ", {"GITHUB_SEEDING_TOKENS": " ghp_env1 , ghp_env2 , ghp_env3 "}):
            pool = GitHubTokenPool(tokens=None)

        # Should strip whitespace
        self.assertEqual(pool._tokens[0].token, "ghp_env1")
        self.assertEqual(pool._tokens[1].token, "ghp_env2")
        self.assertEqual(pool._tokens[2].token, "ghp_env3")

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_env_var_github_seeding_token_fallback(self, mock_github_class):
        """Test that pool falls back to GITHUB_SEEDING_TOKEN (single) if GITHUB_SEEDING_TOKENS not set."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        with patch.dict("os.environ", {"GITHUB_SEEDING_TOKEN": "ghp_fallback_token"}, clear=True):
            pool = GitHubTokenPool(tokens=None)

        # Should use fallback single token
        self.assertEqual(len(pool._tokens), 1)
        self.assertEqual(pool._tokens[0].token, "ghp_fallback_token")

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_env_var_github_seeding_tokens_takes_precedence(self, mock_github_class):
        """Test that GITHUB_SEEDING_TOKENS takes precedence over GITHUB_SEEDING_TOKEN."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock rate limit
        mock_rate = Mock()
        mock_rate.remaining = 5000
        mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
        mock_client.get_rate_limit.return_value.rate = mock_rate

        with patch.dict(
            "os.environ",
            {"GITHUB_SEEDING_TOKENS": "ghp_multi1,ghp_multi2", "GITHUB_SEEDING_TOKEN": "ghp_single"},
        ):
            pool = GitHubTokenPool(tokens=None)

        # Should use GITHUB_SEEDING_TOKENS, not GITHUB_SEEDING_TOKEN
        self.assertEqual(len(pool._tokens), 2)
        self.assertEqual(pool._tokens[0].token, "ghp_multi1")
        self.assertEqual(pool._tokens[1].token, "ghp_multi2")


class TestGitHubTokenPoolTokenSelection(TestCase):
    """Tests for token selection logic."""

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_get_best_client_returns_highest_quota(self, mock_github_class):
        """Test that get_best_client() returns the client with highest remaining quota."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        # Mock different rate limits for each token
        def create_mock_rate_limit(remaining):
            mock_rate = Mock()
            mock_rate.remaining = remaining
            mock_rate.reset = datetime.now(UTC) + timedelta(hours=1)
            mock_rl = Mock()
            mock_rl.rate = mock_rate
            return mock_rl

        # Create pool with 3 tokens
        tokens = ["ghp_low", "ghp_high", "ghp_medium"]

        # Mock Github constructor to return different clients
        mock_clients = []
        for token in tokens:
            client = Mock()
            client._token = token  # Track which token this is
            mock_clients.append(client)

        mock_github_class.side_effect = mock_clients

        pool = GitHubTokenPool(tokens=tokens)

        # Manually set different remaining counts (simulating after rate limit refresh)
        pool._tokens[0].remaining = 1000  # ghp_low
        pool._tokens[1].remaining = 4500  # ghp_high
        pool._tokens[2].remaining = 2500  # ghp_medium

        best_client = pool.get_best_client()

        # Should return client with highest remaining (4500)
        self.assertEqual(best_client._token, "ghp_high")

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_get_best_client_skips_exhausted_tokens(self, mock_github_class):
        """Test that get_best_client() skips exhausted tokens."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        tokens = ["ghp_exhausted", "ghp_available"]
        mock_clients = []
        for token in tokens:
            client = Mock()
            client._token = token
            mock_clients.append(client)

        mock_github_class.side_effect = mock_clients

        pool = GitHubTokenPool(tokens=tokens)

        # Mark first token as exhausted
        pool._tokens[0].remaining = 0
        pool._tokens[0].is_exhausted = True

        # Second token has quota
        pool._tokens[1].remaining = 3000
        pool._tokens[1].is_exhausted = False

        best_client = pool.get_best_client()

        # Should return the available token, not the exhausted one
        self.assertEqual(best_client._token, "ghp_available")

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_get_best_client_raises_when_all_exhausted(self, mock_github_class):
        """Test that get_best_client() raises AllTokensExhaustedException when all tokens exhausted."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        tokens = ["ghp_token1", "ghp_token2"]
        pool = GitHubTokenPool(tokens=tokens)

        # Mark all tokens as exhausted
        for token_info in pool._tokens:
            token_info.remaining = 0
            token_info.is_exhausted = True
            token_info.reset_time = datetime.now(UTC) + timedelta(hours=1)

        # Should raise exception
        with self.assertRaises(AllTokensExhaustedException) as context:
            pool.get_best_client()

        # Exception should include reset time info
        self.assertIsNotNone(str(context.exception))


class TestGitHubTokenPoolRateLimitHandling(TestCase):
    """Tests for rate limit handling."""

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_mark_rate_limited_sets_token_as_exhausted(self, mock_github_class):
        """Test that mark_rate_limited() correctly marks a token as exhausted."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        tokens = ["ghp_token1"]
        pool = GitHubTokenPool(tokens=tokens)

        # Initially not exhausted
        self.assertFalse(pool._tokens[0].is_exhausted)

        reset_time = datetime.now(UTC) + timedelta(hours=1)
        pool.mark_rate_limited(pool._tokens[0].client, reset_time)

        # Should be marked as exhausted
        self.assertTrue(pool._tokens[0].is_exhausted)
        self.assertEqual(pool._tokens[0].remaining, 0)
        self.assertEqual(pool._tokens[0].reset_time, reset_time)

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_mark_rate_limited_only_affects_matching_client(self, mock_github_class):
        """Test that mark_rate_limited() only affects the token for the given client."""
        mock_clients = [Mock(), Mock()]
        mock_github_class.side_effect = mock_clients

        tokens = ["ghp_token1", "ghp_token2"]
        pool = GitHubTokenPool(tokens=tokens)

        # Mark only first token as rate limited
        reset_time = datetime.now(UTC) + timedelta(hours=1)
        pool.mark_rate_limited(pool._tokens[0].client, reset_time)

        # First should be exhausted, second should not
        self.assertTrue(pool._tokens[0].is_exhausted)
        self.assertFalse(pool._tokens[1].is_exhausted)

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_all_exhausted_property_returns_true_when_all_limited(self, mock_github_class):
        """Test that all_exhausted property returns True when all tokens are rate-limited."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        tokens = ["ghp_token1", "ghp_token2"]
        pool = GitHubTokenPool(tokens=tokens)

        # Initially not all exhausted
        self.assertFalse(pool.all_exhausted)

        # Mark all as exhausted
        for token_info in pool._tokens:
            token_info.is_exhausted = True

        # Now should be all exhausted
        self.assertTrue(pool.all_exhausted)

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_all_exhausted_property_returns_false_when_some_available(self, mock_github_class):
        """Test that all_exhausted property returns False when some tokens still available."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        tokens = ["ghp_token1", "ghp_token2"]
        pool = GitHubTokenPool(tokens=tokens)

        # Mark only first as exhausted
        pool._tokens[0].is_exhausted = True
        pool._tokens[1].is_exhausted = False

        # Should not be all exhausted
        self.assertFalse(pool.all_exhausted)

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_total_remaining_sums_non_exhausted_tokens(self, mock_github_class):
        """Test that total_remaining sums remaining quota across non-exhausted tokens."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        tokens = ["ghp_token1", "ghp_token2", "ghp_token3"]
        pool = GitHubTokenPool(tokens=tokens)

        # Set different remaining counts
        pool._tokens[0].remaining = 1000
        pool._tokens[0].is_exhausted = False

        pool._tokens[1].remaining = 2500
        pool._tokens[1].is_exhausted = False

        pool._tokens[2].remaining = 0
        pool._tokens[2].is_exhausted = True  # This one should not be counted

        # Total should be 1000 + 2500 = 3500 (excluding exhausted)
        self.assertEqual(pool.total_remaining, 3500)


class TestGitHubTokenPoolThreadSafety(TestCase):
    """Tests for thread-safe concurrent access."""

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_concurrent_get_best_client_is_thread_safe(self, mock_github_class):
        """Test that concurrent calls to get_best_client() don't cause race conditions."""
        mock_client = Mock()
        mock_github_class.return_value = mock_client

        tokens = ["ghp_token1", "ghp_token2", "ghp_token3"]
        mock_clients = [Mock() for _ in tokens]
        mock_github_class.side_effect = mock_clients

        pool = GitHubTokenPool(tokens=tokens)

        # Set initial remaining counts
        for i, token_info in enumerate(pool._tokens):
            token_info.remaining = 3000 + (i * 1000)

        results = []
        errors = []

        def get_client_worker():
            try:
                client = pool.get_best_client()
                results.append(client)
            except Exception as e:
                errors.append(e)

        # Run 10 concurrent threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_client_worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors
        self.assertEqual(len(errors), 0)
        # Should have 10 results (all successful)
        self.assertEqual(len(results), 10)

    @patch("apps.metrics.seeding.github_token_pool.Github")
    def test_concurrent_mark_rate_limited_is_thread_safe(self, mock_github_class):
        """Test that concurrent calls to mark_rate_limited() don't cause race conditions."""
        mock_clients = [Mock() for _ in range(3)]
        mock_github_class.side_effect = mock_clients

        tokens = ["ghp_token1", "ghp_token2", "ghp_token3"]
        pool = GitHubTokenPool(tokens=tokens)

        errors = []

        def mark_limited_worker(client_index):
            try:
                reset_time = datetime.now(UTC) + timedelta(hours=1)
                pool.mark_rate_limited(pool._tokens[client_index].client, reset_time)
            except Exception as e:
                errors.append(e)

        # Run 3 concurrent threads, each marking a different token
        threads = []
        for i in range(3):
            thread = threading.Thread(target=mark_limited_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors
        self.assertEqual(len(errors), 0)
        # All tokens should be marked as exhausted
        self.assertTrue(all(t.is_exhausted for t in pool._tokens))


class TestAllTokensExhaustedException(TestCase):
    """Tests for the AllTokensExhaustedException exception."""

    def test_exception_can_be_instantiated_with_reset_time(self):
        """Test that AllTokensExhaustedException can be created with reset time."""
        reset_time = datetime(2025, 12, 21, 15, 0, 0, tzinfo=UTC)
        exc = AllTokensExhaustedException(reset_time=reset_time)

        self.assertEqual(exc.reset_time, reset_time)

    def test_exception_can_be_instantiated_without_reset_time(self):
        """Test that AllTokensExhaustedException can be created without reset time."""
        exc = AllTokensExhaustedException(reset_time=None)

        self.assertIsNone(exc.reset_time)

    def test_exception_message_includes_reset_time_when_provided(self):
        """Test that exception message includes reset time information when available."""
        reset_time = datetime(2025, 12, 21, 15, 0, 0, tzinfo=UTC)
        exc = AllTokensExhaustedException(reset_time=reset_time)

        # Message should mention the reset time
        message = str(exc)
        self.assertIn("rate-limited", message.lower())
        # Should contain some representation of the time
        self.assertTrue(len(message) > 20)
