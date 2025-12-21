"""
Checkpoint management for GitHub seeding.

Allows saving and resuming from checkpoints when rate limits are hit,
preventing the need to re-fetch already-processed PRs.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SeedingCheckpoint:
    """Checkpoint data for resuming GitHub PR fetching.

    Attributes:
        repo: Repository in "owner/repo" format.
        fetched_pr_numbers: List of PR numbers successfully fetched.
        last_updated: ISO timestamp of last checkpoint update.
        total_prs_found: Total number of PRs discovered (for progress tracking).
        completed: Whether the seeding completed successfully.
    """

    repo: str
    fetched_pr_numbers: list[int] = field(default_factory=list)
    last_updated: str = ""
    total_prs_found: int = 0
    completed: bool = False

    def __post_init__(self):
        """Set last_updated if not provided."""
        if not self.last_updated:
            self.last_updated = datetime.now(UTC).isoformat()

    def save(self, path: str | Path) -> None:
        """Save checkpoint to file.

        Args:
            path: Path to the checkpoint file.
        """
        try:
            self.last_updated = datetime.now(UTC).isoformat()
            with open(path, "w") as f:
                json.dump(asdict(self), f, indent=2)
            logger.debug("Saved checkpoint to %s (%d PRs)", path, len(self.fetched_pr_numbers))
        except OSError as e:
            logger.warning("Failed to save checkpoint to %s: %s", path, e)

    def add_fetched_pr(self, pr_number: int) -> None:
        """Add a PR number to the fetched list.

        Args:
            pr_number: The PR number to add.
        """
        if pr_number not in self.fetched_pr_numbers:
            self.fetched_pr_numbers.append(pr_number)

    def is_fetched(self, pr_number: int) -> bool:
        """Check if a PR has already been fetched.

        Args:
            pr_number: The PR number to check.

        Returns:
            True if the PR is in the checkpoint.
        """
        return pr_number in self.fetched_pr_numbers

    def mark_completed(self, path: str | Path | None = None) -> None:
        """Mark the checkpoint as completed (all PRs fetched).

        Args:
            path: Optional path to save the updated checkpoint.
        """
        self.completed = True
        self.fetched_pr_numbers = []  # Clear to reduce file size
        if path:
            self.save(path)

    @classmethod
    def load(cls, path: str | Path, repo: str) -> "SeedingCheckpoint":
        """Load checkpoint from file, or create empty one if not found/invalid.

        Args:
            path: Path to the checkpoint file.
            repo: Repository name to validate against.

        Returns:
            Loaded checkpoint if valid, or new empty checkpoint.
        """
        try:
            with open(path) as f:
                data = json.load(f)

            # Check if checkpoint is for the same repo
            if data.get("repo") != repo:
                logger.info(
                    "Checkpoint for different repo (%s vs %s), starting fresh",
                    data.get("repo"),
                    repo,
                )
                return cls(repo=repo)

            # Check if checkpoint is marked as completed
            if data.get("completed", False):
                logger.info("Previous seeding completed, starting fresh")
                return cls(repo=repo)

            checkpoint = cls(
                repo=data.get("repo", repo),
                fetched_pr_numbers=data.get("fetched_pr_numbers", []),
                last_updated=data.get("last_updated", ""),
                total_prs_found=data.get("total_prs_found", 0),
                completed=data.get("completed", False),
            )
            logger.info(
                "Resuming from checkpoint: %d PRs already fetched",
                len(checkpoint.fetched_pr_numbers),
            )
            return checkpoint

        except FileNotFoundError:
            logger.debug("No checkpoint file found at %s, starting fresh", path)
            return cls(repo=repo)

        except json.JSONDecodeError as e:
            logger.warning("Corrupt checkpoint file at %s: %s, starting fresh", path, e)
            return cls(repo=repo)

        except Exception as e:
            logger.warning("Error loading checkpoint from %s: %s, starting fresh", path, e)
            return cls(repo=repo)
