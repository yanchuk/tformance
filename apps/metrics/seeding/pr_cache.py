"""
PR Cache for GitHub data - speeds up real project seeding.

This module implements caching for GitHub PR data to avoid
repeated API calls during development/testing.

Follows GitHub API best practices:
- Stores repo_pushed_at to detect if repo has changed since last fetch
- Allows skipping API calls when data hasn't changed
See: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass
class PRCache:
    """Cache for GitHub PR data to speed up real project seeding.

    Attributes:
        repo: Repository name in "org/repo" format
        fetched_at: When the cache was created
        since_date: The date filter used when fetching
        prs: List of PR data dictionaries
        repo_pushed_at: When the repo was last pushed to (for change detection)
    """

    repo: str
    fetched_at: datetime
    since_date: date
    prs: list[dict]
    repo_pushed_at: datetime | None = field(default=None)

    def save(self, cache_dir: Path | None = None) -> None:
        """Save cache to JSON file.

        Args:
            cache_dir: Optional cache directory. Defaults to .seeding_cache
        """
        cache_path = self.get_cache_path(self.repo, cache_dir)

        # Create parent directories if they don't exist
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize to JSON with datetime/date as ISO strings
        cache_data = {
            "repo": self.repo,
            "fetched_at": self.fetched_at.isoformat(),
            "since_date": self.since_date.isoformat(),
            "prs": self.prs,
        }

        # Add repo_pushed_at if present
        if self.repo_pushed_at:
            cache_data["repo_pushed_at"] = self.repo_pushed_at.isoformat()

        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)

    @classmethod
    def load(cls, repo: str, cache_dir: Path | None = None) -> "PRCache | None":
        """Load cache from JSON file.

        Args:
            repo: Repository name in format "org/repo"
            cache_dir: Optional cache directory. Defaults to .seeding_cache

        Returns:
            PRCache instance if file exists, None otherwise
        """
        cache_path = cls.get_cache_path(repo, cache_dir)

        # Return None if file doesn't exist
        if not cache_path.exists():
            return None

        # Load JSON and parse datetime/date from ISO strings
        with open(cache_path) as f:
            data = json.load(f)

        # Parse repo_pushed_at if present (backward compatibility with old cache files)
        repo_pushed_at = None
        if data.get("repo_pushed_at"):
            repo_pushed_at = datetime.fromisoformat(data["repo_pushed_at"])

        return cls(
            repo=data["repo"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            since_date=date.fromisoformat(data["since_date"]),
            prs=data["prs"],
            repo_pushed_at=repo_pushed_at,
        )

    def is_valid(self, since_date: date, repo_pushed_at: datetime | None = None) -> bool:
        """Check if cache is valid for the given parameters.

        Cache is valid if:
        1. The since_date matches exactly
        2. The repo hasn't been pushed to since the cache was created (if repo_pushed_at provided)

        Args:
            since_date: The date to check against
            repo_pushed_at: Current repo pushed_at timestamp (optional, for change detection)

        Returns:
            True if cache is valid, False otherwise
        """
        # First check: since_date must match exactly
        if self.since_date != since_date:
            return False

        # Second check: if repo_pushed_at is provided, check if repo has changed
        # Cache is valid unless repo has been pushed to since cache was created
        return not (
            repo_pushed_at is not None and self.repo_pushed_at is not None and repo_pushed_at > self.repo_pushed_at
        )

    @staticmethod
    def get_cache_path(repo: str, cache_dir: Path | None = None) -> Path:
        """Get the cache file path for a repository.

        Args:
            repo: Repository name in format "org/repo"
            cache_dir: Optional cache directory. Defaults to .seeding_cache

        Returns:
            Path object for the cache file: {cache_dir}/{org}/{repo}.json
        """
        if cache_dir is None:
            cache_dir = Path(".seeding_cache")

        # Split repo into org/name
        org, name = repo.split("/")

        # Return cache_dir / org / f"{name}.json"
        return cache_dir / org / f"{name}.json"
