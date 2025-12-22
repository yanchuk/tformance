"""
GitHub Token Pool - Manage multiple GitHub tokens for higher API throughput.

This module provides a token pool that automatically selects the best available
GitHub token based on remaining rate limit quota. When one token gets rate-limited,
the pool seamlessly switches to another token with available quota.

Usage:
    # Initialize with tokens
    pool = GitHubTokenPool(tokens=["ghp_token1", "ghp_token2"])

    # Or use GITHUB_SEEDING_TOKENS environment variable (comma-separated)
    pool = GitHubTokenPool()

    # Get the best client (highest quota)
    client = pool.get_best_client()

    # Mark a client as rate-limited when hitting 403
    pool.mark_rate_limited(client, reset_time)
"""

import os
import threading
from dataclasses import dataclass
from datetime import datetime

from github import Auth, Github, GithubException


class AllTokensExhaustedException(Exception):
    """Raised when all tokens in the pool are rate-limited."""

    def __init__(self, reset_time: datetime | None = None):
        self.reset_time = reset_time
        if reset_time:
            message = f"All GitHub tokens are rate-limited. Reset time: {reset_time}"
        else:
            message = "All GitHub tokens are rate-limited."
        super().__init__(message)


@dataclass
class TokenInfo:
    """Information about a GitHub token and its rate limit status."""

    token: str
    client: Github
    remaining: int = 5000
    reset_time: datetime | None = None
    is_exhausted: bool = False

    @property
    def masked_token(self) -> str:
        """Return a masked version of the token for safe logging."""
        if len(self.token) < 8:
            return "***"
        return f"{self.token[:4]}...{self.token[-4:]}"

    def refresh_rate_limit(self) -> None:
        """Refresh rate limit info from the GitHub API."""
        try:
            rate_limit = self.client.get_rate_limit()
            self.remaining = rate_limit.rate.remaining
            self.reset_time = rate_limit.rate.reset
            self.is_exhausted = self.remaining == 0
        except GithubException:
            # If API call fails, keep previous values
            pass


class GitHubTokenPool:
    """
    Manages a pool of GitHub tokens for load balancing and rate limit handling.

    Thread-safe implementation that automatically selects the best available token
    based on remaining API quota.
    """

    def __init__(self, tokens: list[str] | None = None):
        """
        Initialize the token pool.

        Args:
            tokens: List of GitHub tokens. If None, will check GITHUB_SEEDING_TOKENS
                   environment variable (comma-separated list of tokens).

        Raises:
            ValueError: If no tokens provided and none found in environment
        """
        self._lock = threading.Lock()
        self._tokens: list[TokenInfo] = []

        # Determine token list
        if tokens is not None:
            token_list = tokens
        else:
            # Check environment variable (comma-separated tokens)
            env_tokens = os.environ.get("GITHUB_SEEDING_TOKENS")
            token_list = [t.strip() for t in env_tokens.split(",")] if env_tokens else []

        # Validate we have tokens
        if not token_list:
            raise ValueError(
                "No GitHub tokens provided. Set GITHUB_SEEDING_TOKENS environment variable "
                "(comma-separated), or pass tokens to constructor."
            )

        # Create TokenInfo for each token
        for token in token_list:
            client = Github(auth=Auth.Token(token))
            token_info = TokenInfo(token=token, client=client)
            self._tokens.append(token_info)

    def get_best_client(self) -> Github:
        """
        Get the GitHub client with the highest remaining rate limit quota.

        Returns:
            Github client with the most remaining quota

        Raises:
            AllTokensExhaustedException: If all tokens are exhausted
        """
        with self._lock:
            # Filter to non-exhausted tokens
            available_tokens = [t for t in self._tokens if not t.is_exhausted]

            if not available_tokens:
                # Find the earliest reset time
                reset_time = None
                for token in self._tokens:
                    if token.reset_time and (reset_time is None or token.reset_time < reset_time):
                        reset_time = token.reset_time
                raise AllTokensExhaustedException(reset_time=reset_time)

            # Return the client with highest remaining quota
            best_token = max(available_tokens, key=lambda t: t.remaining)
            return best_token.client

    def mark_rate_limited(self, client: Github, reset_time: datetime) -> None:
        """
        Mark a specific client as rate-limited.

        Args:
            client: The Github client that hit rate limit
            reset_time: When the rate limit will reset
        """
        with self._lock:
            # Find the token that matches this client
            for token_info in self._tokens:
                if token_info.client is client:
                    token_info.is_exhausted = True
                    token_info.remaining = 0
                    token_info.reset_time = reset_time
                    break

    @property
    def all_exhausted(self) -> bool:
        """Check if all tokens are exhausted."""
        with self._lock:
            return all(t.is_exhausted for t in self._tokens)

    @property
    def total_remaining(self) -> int:
        """Get the total remaining quota across all non-exhausted tokens."""
        with self._lock:
            return sum(t.remaining for t in self._tokens if not t.is_exhausted)

    @property
    def token_count(self) -> int:
        """Get the number of tokens in the pool."""
        return len(self._tokens)
