"""GitHub API rate limit helper service.

This module provides utilities for checking and handling GitHub API rate limits.
"""

import time
from datetime import datetime

from github import Github


def check_rate_limit(access_token: str) -> dict:
    """Check the current GitHub API rate limit status.

    Args:
        access_token: GitHub personal access token

    Returns:
        Dictionary with keys: remaining, limit, reset_at
    """
    github = Github(access_token)
    rate_limit = github.get_rate_limit()
    core = rate_limit.core

    return {
        "remaining": core.remaining,
        "limit": core.limit,
        "reset_at": core.reset,
    }


def should_pause_for_rate_limit(remaining: int, threshold: int = 100) -> bool:
    """Determine if we should pause due to rate limit.

    Args:
        remaining: Number of API calls remaining
        threshold: Minimum threshold before pausing (default: 100)

    Returns:
        True if remaining < threshold, False otherwise
    """
    return remaining < threshold


def wait_for_rate_limit_reset(reset_at: datetime) -> None:
    """Wait until the rate limit resets.

    Args:
        reset_at: DateTime when the rate limit will reset
    """
    current_timestamp = time.time()
    reset_timestamp = reset_at.timestamp()
    seconds_until_reset = reset_timestamp - current_timestamp

    if seconds_until_reset > 0:
        sleep_duration = int(seconds_until_reset) + 1  # Add 1 second buffer
        time.sleep(sleep_duration)
