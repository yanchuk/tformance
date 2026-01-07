"""Onboarding sync service for historical data import.

Orchestrates historical sync for onboarding by fetching PR data via GraphQL
and processing through LLM for AI detection.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync
from django.conf import settings

from apps.integrations.services.github_graphql_sync import (
    sync_repository_history_by_search,
    sync_repository_history_graphql,
)

if TYPE_CHECKING:
    from apps.integrations.models import TrackedRepository
    from apps.teams.models import Team

logger = logging.getLogger(__name__)

# Get config with defaults
SYNC_CONFIG = getattr(settings, "HISTORICAL_SYNC_CONFIG", {})


class OnboardingSyncService:
    """
    Orchestrates historical sync for onboarding.

    Uses existing GraphQL fetcher with batched LLM processing.
    Token management is handled per-repo by the GraphQL sync functions
    via _get_access_token(), so github_token is kept for backward
    compatibility but is not used by this service.
    """

    # Configurable settings from HISTORICAL_SYNC_CONFIG
    HISTORY_MONTHS = SYNC_CONFIG.get("HISTORY_MONTHS", 12)
    LLM_BATCH_SIZE = SYNC_CONFIG.get("LLM_BATCH_SIZE", 100)
    GRAPHQL_PAGE_SIZE = SYNC_CONFIG.get("GRAPHQL_PAGE_SIZE", 25)

    def __init__(self, team: Team, github_token: str | None = None):
        """
        Initialize the sync service.

        Args:
            team: The team to sync data for
            github_token: Deprecated - tokens are now fetched per-repo by
                         GraphQL sync functions via _get_access_token().
                         Kept for backward compatibility but not used.
        """
        self.team = team
        self.github_token = github_token  # Kept for backward compatibility

    def _calculate_days_back(self) -> int:
        """Calculate days_back based on HISTORY_MONTHS config."""
        # Approximate days: months * 30.5 days (average month length)
        return int(self.HISTORY_MONTHS * 30.5)

    def sync_repository(
        self,
        repo: TrackedRepository,
        progress_callback: Callable[[int, int, str], None] | None = None,
        days_back: int | None = None,
        skip_recent: int = 0,
    ) -> dict:
        """
        Sync a single repository with progress reporting.

        Uses GraphQL API for fast bulk fetching of PRs.

        Supports two-phase onboarding:
        - Phase 1: days_back=30, skip_recent=0 (sync recent 30 days)
        - Phase 2: days_back=90, skip_recent=30 (sync days 31-90)

        Args:
            repo: TrackedRepository to sync
            progress_callback: Optional callback for progress updates
                               (prs_completed, prs_total, message)
            days_back: How many days of history to sync (default: from config)
            skip_recent: Skip PRs from the most recent N days (default: 0)

        Returns:
            Dict with sync results (prs_synced, errors, etc.)
        """
        logger.info(f"Syncing repository {repo.full_name} for team {self.team.name}")

        # Use provided days_back or calculate from config
        if days_back is None:
            days_back = self._calculate_days_back()

        # Report start of sync
        if progress_callback:
            progress_callback(0, 1, f"Starting sync for {repo.full_name}")

        try:
            # Check if Search API is enabled for more accurate progress tracking
            github_config = getattr(settings, "GITHUB_API_CONFIG", {})
            graphql_ops = github_config.get("GRAPHQL_OPERATIONS", {})
            use_search_api = graphql_ops.get("use_search_api", False)

            # Run async GraphQL sync in sync context using async_to_sync
            # NOTE: Using async_to_sync instead of asyncio.run() is critical!
            # asyncio.run() creates a new event loop which breaks @sync_to_async
            # decorators' thread handling, causing DB operations to silently fail
            # in Celery workers. async_to_sync properly manages the event loop
            # and thread context for Django's database connections.
            if use_search_api:
                # Search API provides accurate PR count from issueCount
                logger.info(f"Using Search API for accurate progress: {repo.full_name}")
                sync_fn = async_to_sync(sync_repository_history_by_search)
            else:
                # Default to pullRequests connection (less accurate progress)
                sync_fn = async_to_sync(sync_repository_history_graphql)

            result = sync_fn(
                repo,
                days_back=days_back,
                skip_recent=skip_recent,
            )

            prs_synced = result.get("prs_synced", 0)

            # Report completion
            if progress_callback:
                progress_callback(prs_synced, prs_synced, f"Synced {prs_synced} PRs")

            return {
                "prs_synced": prs_synced,
                "reviews_synced": result.get("reviews_synced", 0),
                "commits_synced": result.get("commits_synced", 0),
                "errors": result.get("errors", []),
            }

        except Exception as e:
            logger.error(f"Error syncing {repo.full_name}: {e}")
            if progress_callback:
                progress_callback(0, 0, f"Error: {e}")
            raise

    def sync_all_repositories(
        self,
        repos: list[TrackedRepository],
        progress_callback: Callable[[str, int, int, str], None] | None = None,
    ) -> dict:
        """
        Sync all repositories with overall progress reporting.

        Args:
            repos: List of TrackedRepository objects to sync
            progress_callback: Optional callback for progress updates
                               (step, current, total, message)

        Returns:
            Dict with overall sync results
        """
        total_prs = 0
        errors = []

        for i, repo in enumerate(repos):
            try:
                result = self.sync_repository(repo)
                total_prs += result.get("prs_synced", 0)
                if progress_callback:
                    progress_callback("repos", i + 1, len(repos), f"Synced {repo.full_name}")
            except Exception as e:
                logger.error(f"Failed to sync {repo.full_name}: {e}")
                errors.append({"repo": repo.full_name, "error": str(e)})

        return {
            "repos_synced": len(repos) - len(errors),
            "total_prs": total_prs,
            "errors": errors,
        }
