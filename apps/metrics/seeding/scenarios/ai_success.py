"""
AI Success scenario - Progressive AI adoption with improving metrics.

This scenario tells the story of a team that successfully adopts AI coding tools,
showing gradual improvement in key metrics over 8 weeks.

Pattern:
- AI Adoption: 10% → 75% (progressive increase)
- Cycle Time: 72h → 24h (improving)
- Quality Rating: 2.5 → 2.8 (maintained/improving)
- Revert Rate: 5% → 3% (improving)
"""

from decimal import Decimal

from .base import BaseScenario, MemberArchetype, ScenarioConfig, WeeklyParams
from .registry import register_scenario


@register_scenario("ai-success")
class AISuccessScenario(BaseScenario):
    """Scenario demonstrating successful AI tool adoption."""

    config = ScenarioConfig(
        name="ai-success",
        description="Progressive AI adoption success story with improving metrics",
        team_name="AI Pioneers",
        team_slug="ai-pioneers",
        member_count=5,
        weeks=8,
        prs_per_member_per_week=(3, 5),
    )

    def get_weekly_params(self, week: int) -> WeeklyParams:
        """Return progressively improving metrics over 8 weeks.

        Week 0: Low AI adoption, slow cycle times
        Week 7: High AI adoption, fast cycle times
        """
        # Clamp week to valid range
        week = max(0, min(week, self.config.weeks - 1))
        progress = week / (self.config.weeks - 1)

        # AI adoption: 10% → 75%
        ai_adoption = 0.10 + (0.65 * progress)

        # Cycle time: 72h → 24h (decreasing is good)
        cycle_time = 72 - (48 * progress)

        # Review time: 24h → 8h (decreasing is good)
        review_time = 24 - (16 * progress)

        # Quality rating: 2.5 → 2.8 (1-3 scale, higher is better)
        quality = 2.5 + (0.3 * progress)

        # Revert rate: 5% → 3% (decreasing is good)
        revert_rate = 0.05 - (0.02 * progress)

        # CI pass rate: 85% → 95% (increasing is good)
        ci_pass_rate = 0.85 + (0.10 * progress)

        return WeeklyParams(
            ai_adoption_rate=Decimal(str(round(ai_adoption, 3))),
            avg_cycle_time_hours=Decimal(str(round(cycle_time, 1))),
            avg_review_time_hours=Decimal(str(round(review_time, 1))),
            quality_rating=Decimal(str(round(quality, 2))),
            revert_rate=Decimal(str(round(revert_rate, 3))),
            ci_pass_rate=Decimal(str(round(ci_pass_rate, 3))),
        )

    def get_member_archetypes(self) -> list[MemberArchetype]:
        """Return team composition with early adopters, followers, and skeptics."""
        return [
            MemberArchetype(
                name="early_adopter",
                count=2,
                ai_adoption_modifier=0.20,  # +20% above base AI adoption
                review_load_weight=1.0,
                pr_volume_modifier=1.2,  # 20% more PRs
                detectability=0.7,  # AI usage is more obvious
            ),
            MemberArchetype(
                name="follower",
                count=2,
                ai_adoption_modifier=0.0,  # Matches base AI adoption
                review_load_weight=1.0,
                pr_volume_modifier=1.0,
                detectability=0.5,
            ),
            MemberArchetype(
                name="skeptic",
                count=1,
                ai_adoption_modifier=-0.15,  # 15% below base AI adoption
                review_load_weight=1.2,  # Does more reviews
                pr_volume_modifier=0.8,  # Fewer PRs
                detectability=0.3,  # Rarely uses AI, less detectable
            ),
        ]

    def get_guess_accuracy_for_archetype(self, archetype: str) -> tuple[float, float]:
        """Return guess accuracy ranges based on archetype.

        Early adopters are more obvious, skeptics are harder to detect.
        """
        accuracy_ranges = {
            "early_adopter": (0.6, 0.8),  # Easier to detect AI usage
            "follower": (0.4, 0.6),  # Medium detectability
            "skeptic": (0.3, 0.5),  # Harder to detect (rarely uses AI)
        }
        return accuracy_ranges.get(archetype, (0.4, 0.6))
