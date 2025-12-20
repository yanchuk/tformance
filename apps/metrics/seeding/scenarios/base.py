"""
Base classes for scenario-based demo data seeding.

Scenarios define patterns for generating coherent demo data that tells
a specific story (e.g., AI adoption success, review bottleneck).

Each scenario specifies:
- Team configuration (members, duration)
- Weekly parameter progression (AI adoption, cycle time, quality)
- Member archetypes and distributions
- Reviewer selection weights
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TypedDict


class WeeklyParams(TypedDict):
    """Weekly evolution parameters for a scenario.

    These parameters define the target metrics for a given week,
    which the data generator uses to create coherent data.
    """

    ai_adoption_rate: Decimal  # 0.0 to 1.0 - fraction of PRs that are AI-assisted
    avg_cycle_time_hours: Decimal  # Target average cycle time
    avg_review_time_hours: Decimal  # Target time to first review
    quality_rating: Decimal  # 1.0 to 3.0 average quality rating
    revert_rate: Decimal  # 0.0 to 1.0 - fraction of PRs that are reverts
    ci_pass_rate: Decimal  # 0.0 to 1.0 - fraction of CI runs that pass


@dataclass
class MemberArchetype:
    """Definition of a member archetype within a scenario.

    Archetypes represent different "personalities" or behaviors
    that team members exhibit (e.g., early adopter, skeptic).
    """

    name: str
    count: int  # Number of members with this archetype
    ai_adoption_modifier: float = 0.0  # Added to base AI adoption rate
    review_load_weight: float = 1.0  # Relative weight for being assigned reviews
    pr_volume_modifier: float = 1.0  # Multiplier for PR creation rate
    detectability: float = 0.5  # How obvious is their AI usage (for detective game)


@dataclass
class ScenarioConfig:
    """Configuration for a seeding scenario.

    Defines the high-level parameters for a scenario, including
    team structure and data sourcing options.
    """

    name: str  # Scenario identifier (e.g., "ai-success")
    description: str  # Human-readable description
    team_name: str  # Name for the created team
    team_slug: str  # URL slug for the team
    member_count: int  # Total team members
    weeks: int = 8  # Duration of data in weeks
    prs_per_member_per_week: tuple[int, int] = (3, 5)  # (min, max) PRs per member/week
    github_source_repos: list[str] = field(
        default_factory=lambda: [
            "yanchuk/github-issues-rag",
            "tiangolo/fastapi",
            "pallets/flask",
        ]
    )
    github_pr_percentage: float = 0.25  # Fraction of PRs to source from GitHub


class BaseScenario(ABC):
    """Abstract base class for seeding scenarios.

    Subclasses define specific scenarios by implementing:
    - get_weekly_params(week) - Returns target metrics for each week
    - get_member_archetypes() - Returns member distribution

    Optional overrides:
    - get_reviewer_selection_weights(week) - Custom reviewer distribution
    - get_pr_state_distribution(week) - Custom merge/close rates
    """

    config: ScenarioConfig

    @abstractmethod
    def get_weekly_params(self, week: int) -> WeeklyParams:
        """Return target parameters for a specific week.

        Args:
            week: Week number (0-indexed from start of data).

        Returns:
            WeeklyParams with target metrics for this week.

        Example:
            # Week 0 might have 10% AI adoption
            # Week 7 might have 75% AI adoption
            progress = week / 7
            return WeeklyParams(
                ai_adoption_rate=Decimal(str(0.1 + 0.65 * progress)),
                ...
            )
        """
        pass

    @abstractmethod
    def get_member_archetypes(self) -> list[MemberArchetype]:
        """Return the member archetypes for this scenario.

        Returns:
            List of MemberArchetype definitions. The sum of counts
            should equal config.member_count.

        Example:
            return [
                MemberArchetype("early_adopter", count=2, ai_adoption_modifier=0.2),
                MemberArchetype("follower", count=2, ai_adoption_modifier=0.0),
                MemberArchetype("skeptic", count=1, ai_adoption_modifier=-0.15),
            ]
        """
        pass

    def get_reviewer_selection_weights(self, week: int) -> dict[str, float]:
        """Return weights for selecting reviewers by archetype.

        Override this to create unbalanced review distributions
        (e.g., for review bottleneck scenarios).

        Args:
            week: Week number (0-indexed).

        Returns:
            Dict mapping archetype names to relative weights.
            Empty dict means uniform distribution.

        Example (bottleneck scenario):
            return {
                "bottleneck_reviewer": 0.6,
                "normal_reviewer": 0.25,
                "productive_dev": 0.15,
            }
        """
        return {}

    def get_pr_state_distribution(self, week: int) -> dict[str, float]:
        """Return the distribution of PR states for a given week.

        Override to customize merge/close rates per week.

        Args:
            week: Week number (0-indexed).

        Returns:
            Dict with weights for each state: merged, closed, open.

        Default:
            {"merged": 0.7, "closed": 0.2, "open": 0.1}
        """
        return {"merged": 0.7, "closed": 0.2, "open": 0.1}

    def get_review_state_distribution(self, week: int) -> dict[str, float]:
        """Return the distribution of review states for a given week.

        Args:
            week: Week number (0-indexed).

        Returns:
            Dict with weights for each state: approved, changes_requested, commented.

        Default:
            {"approved": 0.6, "changes_requested": 0.25, "commented": 0.15}
        """
        return {"approved": 0.6, "changes_requested": 0.25, "commented": 0.15}

    def get_guess_accuracy_for_archetype(self, archetype: str) -> tuple[float, float]:
        """Return the (min, max) guess accuracy range for an archetype.

        Used in detective-game scenario to vary how detectable
        AI usage is for different member types.

        Args:
            archetype: The archetype name.

        Returns:
            Tuple of (min_accuracy, max_accuracy) as floats 0.0-1.0.

        Default:
            (0.4, 0.6) - 40-60% accuracy (essentially random)
        """
        return (0.4, 0.6)

    def get_total_member_count(self) -> int:
        """Calculate total members from archetypes."""
        return sum(a.count for a in self.get_member_archetypes())

    def validate(self) -> list[str]:
        """Validate scenario configuration.

        Returns:
            List of error messages. Empty list means valid.
        """
        errors = []

        archetypes = self.get_member_archetypes()
        total = sum(a.count for a in archetypes)
        if total != self.config.member_count:
            errors.append(f"Archetype counts ({total}) don't match config.member_count ({self.config.member_count})")

        if self.config.weeks < 1:
            errors.append("weeks must be at least 1")

        if not (0 <= self.config.github_pr_percentage <= 1):
            errors.append("github_pr_percentage must be between 0 and 1")

        return errors
