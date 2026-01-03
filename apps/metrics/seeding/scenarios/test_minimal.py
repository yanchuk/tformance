"""
Minimal test scenario for fast unit tests.

This scenario is optimized for test speed, creating minimal data
while still exercising all generation paths.

Data volume:
- 2 members (1 adopter, 1 skeptic)
- 2 weeks of data
- 1-2 PRs per member per week = ~6 PRs total

Compared to ai-success (5 members × 8 weeks × 4 PRs = ~160 PRs),
this is ~25x smaller and runs proportionally faster.
"""

from decimal import Decimal

from .base import BaseScenario, MemberArchetype, ScenarioConfig, WeeklyParams
from .registry import register_scenario


@register_scenario("test-minimal")
class TestMinimalScenario(BaseScenario):
    """Minimal scenario for fast test execution."""

    config = ScenarioConfig(
        name="test-minimal",
        description="Minimal data for fast unit tests",
        team_name="Test Team",
        team_slug="test-team",
        member_count=2,
        weeks=2,
        prs_per_member_per_week=(1, 2),
    )

    def get_weekly_params(self, week: int) -> WeeklyParams:
        """Simple progression over 2 weeks."""
        progress = week / max(1, self.config.weeks - 1)

        return WeeklyParams(
            ai_adoption_rate=Decimal(str(round(0.3 + 0.4 * progress, 3))),
            avg_cycle_time_hours=Decimal(str(round(48 - 24 * progress, 1))),
            avg_review_time_hours=Decimal(str(round(16 - 8 * progress, 1))),
            quality_rating=Decimal(str(round(2.5 + 0.3 * progress, 2))),
            revert_rate=Decimal(str(round(0.05 - 0.02 * progress, 3))),
            ci_pass_rate=Decimal(str(round(0.90 + 0.05 * progress, 3))),
        )

    def get_member_archetypes(self) -> list[MemberArchetype]:
        """Minimal team: one adopter, one skeptic."""
        return [
            MemberArchetype(
                name="adopter",
                count=1,
                ai_adoption_modifier=0.20,
                review_load_weight=1.0,
                pr_volume_modifier=1.0,
                detectability=0.7,
            ),
            MemberArchetype(
                name="skeptic",
                count=1,
                ai_adoption_modifier=-0.10,
                review_load_weight=1.0,
                pr_volume_modifier=1.0,
                detectability=0.3,
            ),
        ]

    def get_guess_accuracy_for_archetype(self, archetype: str) -> tuple[float, float]:
        """Return simple accuracy ranges."""
        return {"adopter": (0.6, 0.8), "skeptic": (0.3, 0.5)}.get(archetype, (0.4, 0.6))
