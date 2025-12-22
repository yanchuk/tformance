"""GitHub request queue service with serial execution enforcement."""

import contextlib
import threading
from collections.abc import Callable
from typing import Any, TypedDict

from github import GithubException


class RateLimitInfo(TypedDict, total=False):
    """Type definition for GitHub API rate limit information."""

    remaining: int | None
    limit: int
    reset: int
    retry_after: int


# GitHub API rate limit header names
HEADER_RATE_LIMIT_REMAINING = "X-RateLimit-Remaining"
HEADER_RATE_LIMIT_LIMIT = "X-RateLimit-Limit"
HEADER_RATE_LIMIT_RESET = "X-RateLimit-Reset"
HEADER_RETRY_AFTER = "retry-after"


class GitHubRequestQueue:
    """Service for executing GitHub API requests serially with rate limit tracking."""

    def __init__(self) -> None:
        """Initialize the request queue with a lock for serial execution."""
        self._lock = threading.Lock()
        self._rate_limit_info: RateLimitInfo | None = None

    def _is_rate_limit_exception(self, exception: GithubException) -> bool:
        """
        Check if an exception indicates rate limiting.

        Args:
            exception: The GitHub exception to check

        Returns:
            True if this is a rate limit exception (403 or 429 status)
        """
        return exception.status in (403, 429)

    def request(self, callable: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute a callable serially and track rate limit info from response.

        Args:
            callable: A callable to execute (function or method)
            *args: Positional arguments to pass to the callable
            **kwargs: Keyword arguments to pass to the callable

        Returns:
            The result from the callable
        """
        with self._lock:
            try:
                result = callable(*args, **kwargs)

                # Track rate limit headers if response has them
                if hasattr(result, "headers"):
                    self._extract_rate_limit_info(result.headers)

                return result
            except GithubException as e:
                # Capture rate limit info from exception headers before re-raising
                if self._is_rate_limit_exception(e) and hasattr(e, "headers") and e.headers:
                    self._extract_rate_limit_info(e.headers)
                raise

    def _extract_rate_limit_info(self, headers: dict[str, str]) -> None:
        """
        Extract and store rate limit information from response headers.

        Args:
            headers: HTTP response headers dictionary
        """
        # Initialize rate limit info
        self._rate_limit_info = {}

        # Extract standard rate limit headers
        if HEADER_RATE_LIMIT_REMAINING in headers:
            try:
                self._rate_limit_info = {
                    "remaining": int(headers[HEADER_RATE_LIMIT_REMAINING]),
                    "limit": int(headers[HEADER_RATE_LIMIT_LIMIT]),
                    "reset": int(headers[HEADER_RATE_LIMIT_RESET]),
                }
            except (ValueError, KeyError):
                # Invalid header values - set remaining to None to indicate issue
                self._rate_limit_info = {"remaining": None}
        else:
            # Response object exists but no rate limit headers
            self._rate_limit_info = {"remaining": None}

        # Extract retry-after header if present (can be present with or without rate limit headers)
        if HEADER_RETRY_AFTER in headers:
            with contextlib.suppress(ValueError):
                self._rate_limit_info["retry_after"] = int(headers[HEADER_RETRY_AFTER])

    def get_rate_limit_info(self) -> RateLimitInfo | None:
        """
        Get the most recent rate limit information.

        Returns:
            Dict with 'remaining', 'limit', and 'reset' keys, or None if no requests made yet
        """
        return self._rate_limit_info

    def get_retry_after(self) -> int:
        """
        Get the retry-after seconds from the most recent response.

        Returns:
            Number of seconds to wait before retrying, or 0 if no retry-after header present
        """
        if self._rate_limit_info is None:
            return 0
        return self._rate_limit_info.get("retry_after", 0)
