"""
Review Bottleneck scenario - High AI adoption but slowing delivery.

This scenario tells the story of a team with good AI adoption but
a bottleneck in their review process, causing cycle times to worsen.

Pattern:
- AI Adoption: Steady 70%
- Cycle Time: 36h → 60h (worsening due to review queue)
- Quality Rating: 2.8 → 2.2 (declining as reviews become rushed)
- Key: One reviewer handles 60% of all reviews
"""

from decimal import Decimal

from .base import BaseScenario, MemberArchetype, ScenarioConfig, WeeklyParams
from .registry import register_scenario


@register_scenario("review-bottleneck")
class ReviewBottleneckScenario(BaseScenario):
    """Scenario demonstrating review process bottleneck."""

    config = ScenarioConfig(
        name="review-bottleneck",
        description="High AI output bottlenecked by slow reviews",
        team_name="Bottleneck Team",
        team_slug="bottleneck-team",
        member_count=5,
        weeks=8,
        prs_per_member_per_week=(4, 6),  # Higher volume due to AI
    )

    def get_weekly_params(self, week: int) -> WeeklyParams:
        """Return worsening metrics over 8 weeks due to review bottleneck.

        AI adoption stays high but delivery slows as review queue grows.
        """
        week = max(0, min(week, self.config.weeks - 1))
        progress = week / (self.config.weeks - 1)

        # AI adoption: Steady at 70%
        ai_adoption = 0.70

        # Cycle time: 36h → 60h (worsening)
        cycle_time = 36 + (24 * progress)

        # Review time: 8h → 32h (getting much worse)
        review_time = 8 + (24 * progress)

        # Quality rating: 2.8 → 2.2 (declining as reviews are rushed)
        quality = 2.8 - (0.6 * progress)

        # Revert rate: 3% → 8% (increasing due to rushed reviews)
        revert_rate = 0.03 + (0.05 * progress)

        # CI pass rate: Steady at 90%
        ci_pass_rate = 0.90

        return WeeklyParams(
            ai_adoption_rate=Decimal(str(round(ai_adoption, 3))),
            avg_cycle_time_hours=Decimal(str(round(cycle_time, 1))),
            avg_review_time_hours=Decimal(str(round(review_time, 1))),
            quality_rating=Decimal(str(round(quality, 2))),
            revert_rate=Decimal(str(round(revert_rate, 3))),
            ci_pass_rate=Decimal(str(round(ci_pass_rate, 3))),
        )

    def get_member_archetypes(self) -> list[MemberArchetype]:
        """Return team composition with one bottleneck reviewer."""
        return [
            MemberArchetype(
                name="bottleneck_reviewer",
                count=1,
                ai_adoption_modifier=0.0,
                review_load_weight=4.0,  # 4x more reviews = ~60% of total
                pr_volume_modifier=0.5,  # Creates fewer PRs (busy reviewing)
                detectability=0.5,
            ),
            MemberArchetype(
                name="productive_dev",
                count=3,
                ai_adoption_modifier=0.10,  # High AI users
                review_load_weight=0.5,  # Do few reviews
                pr_volume_modifier=1.3,  # High PR output
                detectability=0.6,
            ),
            MemberArchetype(
                name="balanced_dev",
                count=1,
                ai_adoption_modifier=0.0,
                review_load_weight=1.0,
                pr_volume_modifier=1.0,
                detectability=0.5,
            ),
        ]

    def get_reviewer_selection_weights(self, week: int) -> dict[str, float]:
        """Return heavily skewed reviewer distribution.

        The bottleneck reviewer handles 60% of all reviews.
        """
        return {
            "bottleneck_reviewer": 0.60,
            "productive_dev": 0.25,  # Split among 3 devs = ~8% each
            "balanced_dev": 0.15,
        }

    def get_pr_state_distribution(self, week: int) -> dict[str, float]:
        """Return PR state distribution with more open PRs as time goes on.

        As the bottleneck worsens, more PRs stay open waiting for review.
        """
        week = max(0, min(week, self.config.weeks - 1))
        progress = week / (self.config.weeks - 1)

        # Open PRs increase as bottleneck worsens: 10% → 25%
        open_rate = 0.10 + (0.15 * progress)
        merged_rate = 0.70 - (0.10 * progress)
        closed_rate = 0.20 - (0.05 * progress)

        return {
            "merged": merged_rate,
            "closed": closed_rate,
            "open": open_rate,
        }
