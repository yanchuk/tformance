"""GitHub API rate limit helper service.

This module provides utilities for checking and handling GitHub API rate limits.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime

from github import Github

logger = logging.getLogger(__name__)

# Maximum wait time for rate limit reset (default: 1 hour)
MAX_RATE_LIMIT_WAIT_SECONDS = 3600


def check_rate_limit(access_token: str) -> dict:
    """Check the current GitHub API rate limit status.

    Args:
        access_token: GitHub personal access token

    Returns:
        Dictionary with keys: remaining, limit, reset_at
    """
    github = Github(access_token)
    rate_limit = github.get_rate_limit()
    # PyGithub API changed: rate_limit.core → rate_limit.rate
    core = rate_limit.rate

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
    """Wait until the rate limit resets (synchronous version).

    Args:
        reset_at: DateTime when the rate limit will reset
    """
    current_timestamp = time.time()
    reset_timestamp = reset_at.timestamp()
    seconds_until_reset = reset_timestamp - current_timestamp

    if seconds_until_reset > 0:
        sleep_duration = int(seconds_until_reset) + 1  # Add 1 second buffer
        time.sleep(sleep_duration)


async def wait_for_rate_limit_reset_async(
    reset_at_iso: str,
    max_wait_seconds: int = MAX_RATE_LIMIT_WAIT_SECONDS,
) -> bool:
    """Wait until the rate limit resets (async version for GraphQL client).

    Args:
        reset_at_iso: ISO datetime string when the rate limit will reset
        max_wait_seconds: Maximum seconds to wait (default: 1 hour)

    Returns:
        True if waited successfully, False if wait would exceed max_wait_seconds
    """
    from dateutil import parser as date_parser

    # Parse the ISO datetime string
    reset_at = date_parser.isoparse(reset_at_iso)
    now = datetime.now(UTC)
    seconds_until_reset = (reset_at - now).total_seconds()

    if seconds_until_reset <= 0:
        # Already reset, no need to wait
        return True

    if seconds_until_reset > max_wait_seconds:
        # Too long to wait
        logger.warning(f"Rate limit reset in {seconds_until_reset:.0f}s exceeds max wait of {max_wait_seconds}s")
        return False

    # Add 5 second buffer
    sleep_duration = seconds_until_reset + 5
    logger.info(f"Rate limit low, waiting {sleep_duration:.0f}s until reset at {reset_at_iso}")
    await asyncio.sleep(sleep_duration)
    return True
