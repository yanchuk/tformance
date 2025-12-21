"""
Jira issue simulator for real project demo data seeding.

Simulates Jira issues from PR data by:
1. Extracting existing Jira keys from PR titles/branches
2. Generating synthetic keys for PRs without references
3. Estimating story points from PR size
4. Simulating sprint assignments

Usage:
    simulator = JiraIssueSimulator("POST", rng)
    jira_key = simulator.extract_or_generate_jira_key(pr)
    issue = simulator.create_jira_issue(team, jira_key, pr, assignee)
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.db import models

from apps.metrics.factories import JiraIssueFactory
from apps.metrics.models import TeamMember

from .deterministic import DeterministicRandom
from .github_authenticated_fetcher import FetchedPRFull


@dataclass
class SprintInfo:
    """Sprint information for Jira issue assignment."""

    sprint_number: int
    sprint_name: str
    start_date: datetime
    end_date: datetime


class JiraIssueSimulator:
    """Simulates Jira issues from PR data.

    Uses multiple strategies:
    1. Extract existing keys from PR titles/branches (e.g., "PROJ-123")
    2. Generate synthetic keys for PRs without explicit references
    3. Assign story points based on PR size
    4. Simulate sprint assignments based on PR dates

    Attributes:
        project_key: Jira project key (e.g., "POST", "POLAR").
        JIRA_KEY_PATTERN: Regex pattern for extracting Jira issue keys.
    """

    JIRA_KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9]+-\d+")

    # Story point thresholds based on lines changed
    STORY_POINTS_THRESHOLDS = [
        (50, Decimal("1")),
        (150, Decimal("2")),
        (400, Decimal("3")),
        (800, Decimal("5")),
        (float("inf"), Decimal("8")),
    ]

    # Issue type distribution
    ISSUE_TYPES = {
        "Story": 0.50,
        "Task": 0.25,
        "Bug": 0.20,
        "Improvement": 0.05,
    }

    # Priority distribution
    PRIORITIES = {
        "Medium": 0.50,
        "High": 0.25,
        "Low": 0.20,
        "Critical": 0.05,
    }

    def __init__(self, project_key: str, rng: DeterministicRandom):
        """Initialize the Jira simulator.

        Args:
            project_key: Jira project key (e.g., "POST").
            rng: Deterministic random generator for reproducibility.
        """
        self.project_key = project_key.upper() if project_key else "PROJ"
        self.rng = rng
        self._issue_counter = 1000  # Start at PROJ-1000
        self._sprint_cache: dict[str, SprintInfo] = {}

    def extract_jira_key(self, text: str | None) -> str | None:
        """Extract Jira issue key from text.

        Args:
            text: Text to search (PR title or branch name).

        Returns:
            Jira key (e.g., "POST-123") or None if not found.
        """
        if not text:
            return None
        match = self.JIRA_KEY_PATTERN.search(text)
        return match.group() if match else None

    def generate_jira_key(self) -> str:
        """Generate a synthetic Jira issue key.

        Returns:
            Synthetic key (e.g., "POST-1001").
        """
        key = f"{self.project_key}-{self._issue_counter}"
        self._issue_counter += 1
        return key

    def extract_or_generate_jira_key(self, pr: FetchedPRFull) -> str:
        """Extract Jira key from PR or generate a synthetic one.

        Tries to extract from:
        1. PR title (e.g., "[POST-123] Fix bug")
        2. Branch name (e.g., "feature/POST-123-new-feature")

        Falls back to generating a synthetic key if none found.

        Args:
            pr: Fetched PR data.

        Returns:
            Jira issue key.
        """
        # Try title first
        if pr.jira_key_from_title:
            return pr.jira_key_from_title

        # Try branch name
        if pr.jira_key_from_branch:
            return pr.jira_key_from_branch

        # Generate synthetic
        return self.generate_jira_key()

    def estimate_story_points(self, pr: FetchedPRFull) -> Decimal:
        """Estimate story points based on PR size.

        Uses lines changed (additions + deletions) as proxy for complexity.

        Args:
            pr: Fetched PR data.

        Returns:
            Story points (1, 2, 3, 5, or 8).
        """
        total_lines = pr.additions + pr.deletions

        for threshold, points in self.STORY_POINTS_THRESHOLDS:
            if total_lines < threshold:
                return points

        return Decimal("8")  # Default to 8 for very large PRs

    def get_sprint_for_date(self, date: datetime) -> SprintInfo:
        """Get sprint information for a given date.

        Simulates 2-week sprints starting from a fixed date.

        Args:
            date: Date to find sprint for.

        Returns:
            SprintInfo for the sprint containing the date.
        """
        # Fixed sprint start date (first Monday of 2024)
        epoch = datetime(2024, 1, 1, tzinfo=UTC)
        # Adjust to Monday
        epoch = epoch - timedelta(days=epoch.weekday())

        # Calculate sprint number (2-week sprints)
        days_since_epoch = (date - epoch).days
        sprint_number = (days_since_epoch // 14) + 1

        cache_key = f"sprint-{sprint_number}"
        if cache_key in self._sprint_cache:
            return self._sprint_cache[cache_key]

        # Calculate sprint dates
        sprint_start = epoch + timedelta(days=(sprint_number - 1) * 14)
        sprint_end = sprint_start + timedelta(days=13)

        sprint = SprintInfo(
            sprint_number=sprint_number,
            sprint_name=f"Sprint {sprint_number}",
            start_date=sprint_start,
            end_date=sprint_end,
        )

        self._sprint_cache[cache_key] = sprint
        return sprint

    def determine_issue_type(self, pr: FetchedPRFull) -> str:
        """Determine issue type based on PR characteristics.

        Uses PR labels and title to guess the type.

        Args:
            pr: Fetched PR data.

        Returns:
            Issue type (Story, Task, Bug, Improvement).
        """
        title_lower = pr.title.lower()
        labels_lower = [label.lower() for label in pr.labels]

        # Check for bug indicators
        if "bug" in labels_lower or "fix" in title_lower or "bugfix" in title_lower:
            return "Bug"

        # Check for feature indicators
        if "feature" in labels_lower or "feat" in title_lower:
            return "Story"

        # Check for improvement indicators
        if "enhancement" in labels_lower or "improve" in title_lower or "refactor" in title_lower:
            return "Improvement"

        # Check for chore/task indicators
        if "chore" in labels_lower or "task" in labels_lower:
            return "Task"

        # Fall back to weighted random
        return self.rng.weighted_choice(self.ISSUE_TYPES)

    def create_jira_issue(
        self,
        team: models.Model,
        jira_key: str,
        pr: FetchedPRFull,
        assignee: TeamMember,
    ):
        """Create a JiraIssue from PR data with simulated fields.

        Args:
            team: Team model instance.
            jira_key: Jira issue key.
            pr: Fetched PR data.
            assignee: TeamMember to assign the issue to.

        Returns:
            Created JiraIssue instance.
        """
        # Get story points
        story_points = self.estimate_story_points(pr)

        # Get sprint info
        pr_date = pr.merged_at or pr.created_at
        sprint = self.get_sprint_for_date(pr_date)

        # Determine issue type
        issue_type = self.determine_issue_type(pr)

        # Calculate cycle time if merged
        cycle_time_hours = None
        resolved_at = None
        if pr.is_merged and pr.merged_at:
            resolved_at = pr.merged_at
            # Calculate cycle time from creation to merge
            delta = pr.merged_at - pr.created_at
            cycle_time_hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))

        # Determine status based on PR state
        if pr.is_merged:
            status = "Done"
        elif pr.state == "closed":
            status = "Won't Do"
        else:
            status = self.rng.choice(["To Do", "In Progress", "In Review"])

        # Create the issue
        return JiraIssueFactory(
            team=team,
            jira_key=jira_key,
            jira_id=str(self.rng.randint(10000, 99999)),  # Simulated Jira ID
            summary=pr.title[:200],  # Limit to 200 chars
            issue_type=issue_type,
            status=status,
            story_points=story_points,
            assignee=assignee,
            sprint_id=str(sprint.sprint_number),
            sprint_name=sprint.sprint_name,
            cycle_time_hours=cycle_time_hours,
            issue_created_at=pr.created_at,
            resolved_at=resolved_at,
        )
