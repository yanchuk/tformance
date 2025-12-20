"""
GitHub PR fetcher for demo data seeding.

Fetches real PR metadata from public repositories to use as templates
for generating realistic demo data. Uses unauthenticated access with
60 requests/hour rate limit.

Usage:
    fetcher = GitHubPublicFetcher()
    prs = fetcher.fetch_prs("tiangolo/fastapi", limit=10)
    for pr in prs:
        print(f"{pr.title}: +{pr.additions}/-{pr.deletions}")
"""

import logging
from dataclasses import dataclass
from typing import ClassVar

from github import Github, GithubException, RateLimitExceededException

logger = logging.getLogger(__name__)


@dataclass
class FetchedPR:
    """Metadata from a fetched GitHub PR.

    Contains the essential data needed to create realistic demo PRs
    without storing the full PR content.
    """

    title: str
    additions: int
    deletions: int
    files_changed: int
    commits_count: int
    # Optional metadata for enhanced realism
    labels: list[str]
    is_draft: bool
    review_comments_count: int


class GitHubPublicFetcher:
    """Fetches PR metadata from public GitHub repositories.

    Uses unauthenticated PyGithub client with 60 requests/hour limit.
    Implements in-memory caching to avoid repeated API calls within
    the same seeding session.

    Attributes:
        DEFAULT_REPOS: Default public repos to fetch from.
    """

    DEFAULT_REPOS: ClassVar[list[str]] = [
        "tiangolo/fastapi",
        "pallets/flask",
        "psf/requests",
    ]

    def __init__(self):
        """Initialize the fetcher with unauthenticated client."""
        self._client = Github()  # Unauthenticated = 60 req/hour
        self._cache: dict[str, list[FetchedPR]] = {}

    def fetch_prs(
        self,
        repo_name: str,
        limit: int = 20,
        state: str = "closed",
    ) -> list[FetchedPR]:
        """Fetch PR metadata from a public repository.

        Args:
            repo_name: Repository in "owner/repo" format.
            limit: Maximum PRs to fetch (default 20).
            state: PR state to filter ("open", "closed", "all").

        Returns:
            List of FetchedPR objects with PR metadata.
            Returns empty list if rate limited or repo not found.

        Note:
            Results are cached by (repo_name, state) key.
            Subsequent calls with same args return cached data.
        """
        cache_key = f"{repo_name}:{state}"

        # Return cached results if available
        if cache_key in self._cache:
            logger.debug("Using cached PRs for %s", cache_key)
            return self._cache[cache_key][:limit]

        try:
            repo = self._client.get_repo(repo_name)
            pulls = repo.get_pulls(state=state, sort="updated", direction="desc")

            fetched: list[FetchedPR] = []
            for pr in pulls[:limit]:
                try:
                    fetched.append(
                        FetchedPR(
                            title=pr.title,
                            additions=pr.additions,
                            deletions=pr.deletions,
                            files_changed=pr.changed_files,
                            commits_count=pr.commits,
                            labels=[label.name for label in pr.labels],
                            is_draft=pr.draft,
                            review_comments_count=pr.review_comments,
                        )
                    )
                except GithubException as e:
                    # Individual PR fetch failed, skip it
                    logger.warning("Failed to fetch PR details: %s", e)
                    continue

            # Cache the results
            self._cache[cache_key] = fetched
            logger.info("Fetched %d PRs from %s", len(fetched), repo_name)
            return fetched

        except RateLimitExceededException:
            logger.warning(
                "GitHub rate limit exceeded. Using factory data only. Consider using --no-github flag or waiting."
            )
            return []

        except GithubException as e:
            logger.warning("Failed to fetch PRs from %s: %s", repo_name, e)
            return []

    def fetch_from_defaults(self, per_repo_limit: int = 15) -> list[FetchedPR]:
        """Fetch PRs from all default repositories.

        Args:
            per_repo_limit: Max PRs to fetch per repo.

        Returns:
            Combined list of FetchedPR from all default repos.
        """
        all_prs: list[FetchedPR] = []
        for repo in self.DEFAULT_REPOS:
            prs = self.fetch_prs(repo, limit=per_repo_limit)
            all_prs.extend(prs)
        return all_prs

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()

    def get_rate_limit_remaining(self) -> int:
        """Get remaining API requests before rate limit.

        Returns:
            Number of requests remaining (0-60 for unauthenticated).
        """
        try:
            rate_limit = self._client.get_rate_limit()
            return rate_limit.core.remaining
        except GithubException:
            return 0
