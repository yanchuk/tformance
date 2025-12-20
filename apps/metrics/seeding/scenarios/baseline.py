"""
Baseline scenario - Steady state with low AI adoption.

This scenario provides a reference baseline for comparison dashboards,
showing what a "typical" team looks like without significant AI adoption.

Pattern:
- AI Adoption: Steady 15%
- Cycle Time: Steady 48h
- Quality Rating: Steady 2.6
- Use Case: Reference for comparison with other scenarios
"""

from decimal import Decimal

from .base import BaseScenario, MemberArchetype, ScenarioConfig, WeeklyParams
from .registry import register_scenario


@register_scenario("baseline")
class BaselineScenario(BaseScenario):
    """Scenario providing steady-state baseline for comparisons."""

    config = ScenarioConfig(
        name="baseline",
        description="Steady state baseline with low AI adoption",
        team_name="Baseline Team",
        team_slug="baseline-team",
        member_count=5,
        weeks=8,
        prs_per_member_per_week=(2, 4),  # Moderate volume
    )

    def get_weekly_params(self, week: int) -> WeeklyParams:
        """Return steady metrics with small random-like variations.

        All metrics stay relatively constant, representing a team
        that hasn't significantly changed their process.
        """
        # Small week-based variations to add realism
        # Uses a simple pattern to avoid pure constants
        variation = (week % 3 - 1) * 0.02  # -0.02, 0, +0.02 cycle

        return WeeklyParams(
            ai_adoption_rate=Decimal(str(round(0.15 + variation, 3))),
            avg_cycle_time_hours=Decimal(str(round(48 + (week % 4 - 1.5) * 2, 1))),
            avg_review_time_hours=Decimal(str(round(16 + (week % 3 - 1) * 2, 1))),
            quality_rating=Decimal(str(round(2.6 + variation, 2))),
            revert_rate=Decimal(str(round(0.04 + variation * 0.5, 3))),
            ci_pass_rate=Decimal(str(round(0.88 + variation, 3))),
        )

    def get_member_archetypes(self) -> list[MemberArchetype]:
        """Return homogeneous team with minimal variation."""
        return [
            MemberArchetype(
                name="standard_dev",
                count=4,
                ai_adoption_modifier=0.0,
                review_load_weight=1.0,
                pr_volume_modifier=1.0,
                detectability=0.5,
            ),
            MemberArchetype(
                name="occasional_ai_user",
                count=1,
                ai_adoption_modifier=0.10,  # Slightly higher AI usage
                review_load_weight=1.0,
                pr_volume_modifier=1.0,
                detectability=0.4,
            ),
        ]
