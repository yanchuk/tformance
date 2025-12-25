"""Onboarding sync service for historical data import.

Orchestrates historical sync for onboarding by fetching PR data via GraphQL
and processing through LLM for AI detection.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from django.conf import settings

from apps.integrations.services.github_graphql_sync import sync_repository_history_graphql

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
    """

    # Configurable settings from HISTORICAL_SYNC_CONFIG
    HISTORY_MONTHS = SYNC_CONFIG.get("HISTORY_MONTHS", 12)
    LLM_BATCH_SIZE = SYNC_CONFIG.get("LLM_BATCH_SIZE", 100)
    GRAPHQL_PAGE_SIZE = SYNC_CONFIG.get("GRAPHQL_PAGE_SIZE", 25)

    def __init__(self, team: Team, github_token: str):
        """
        Initialize the sync service.

        Args:
            team: The team to sync data for
            github_token: GitHub access token for API calls
        """
        self.team = team
        self.github_token = github_token

    def _calculate_days_back(self) -> int:
        """Calculate days_back based on HISTORY_MONTHS config."""
        # Approximate days: months * 30.5 days (average month length)
        return int(self.HISTORY_MONTHS * 30.5)

    def sync_repository(
        self,
        repo: TrackedRepository,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict:
        """
        Sync a single repository with progress reporting.

        Uses GraphQL API for fast bulk fetching of PRs.

        Args:
            repo: TrackedRepository to sync
            progress_callback: Optional callback for progress updates
                               (prs_completed, prs_total, message)

        Returns:
            Dict with sync results (prs_synced, errors, etc.)
        """
        logger.info(f"Syncing repository {repo.full_name} for team {self.team.name}")

        days_back = self._calculate_days_back()

        # Report start of sync
        if progress_callback:
            progress_callback(0, 1, f"Starting sync for {repo.full_name}")

        try:
            # Run async GraphQL sync in sync context
            result = asyncio.run(sync_repository_history_graphql(repo, days_back=days_back))

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
