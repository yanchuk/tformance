"""
PR Cache for GitHub data - speeds up real project seeding.

This module implements caching for GitHub PR data to avoid
repeated API calls during development/testing.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass
class PRCache:
    """Cache for GitHub PR data to speed up real project seeding."""

    repo: str
    fetched_at: datetime
    since_date: date
    prs: list[dict]

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

        return cls(
            repo=data["repo"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            since_date=date.fromisoformat(data["since_date"]),
            prs=data["prs"],
        )

    def is_valid(self, since_date: date) -> bool:
        """Check if cache is valid for the given since_date.

        Cache is only valid if the since_date matches exactly.

        Args:
            since_date: The date to check against

        Returns:
            True if cache is valid for this since_date, False otherwise
        """
        return self.since_date == since_date

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
