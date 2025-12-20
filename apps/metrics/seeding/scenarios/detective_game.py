"""
Detective Game scenario - Focus on AI detection and survey engagement.

This scenario is designed to demonstrate the AI Detective leaderboard feature,
with team members who have varying levels of detectability when using AI.

Pattern:
- Archetypes: obvious_ai, stealth_ai, obvious_manual, stealth_manual
- Guess Accuracy: Varies 30-70% based on archetype
- Focus: Survey engagement and detection patterns
"""

from decimal import Decimal

from .base import BaseScenario, MemberArchetype, ScenarioConfig, WeeklyParams
from .registry import register_scenario


@register_scenario("detective-game")
class DetectiveGameScenario(BaseScenario):
    """Scenario designed for AI Detective leaderboard demonstration."""

    config = ScenarioConfig(
        name="detective-game",
        description="Survey engagement focus with varied AI detectability",
        team_name="AI Detectives",
        team_slug="ai-detectives",
        member_count=6,
        weeks=8,
        prs_per_member_per_week=(3, 5),
    )

    def get_weekly_params(self, week: int) -> WeeklyParams:
        """Return mixed AI adoption for interesting detection patterns.

        Maintains moderate metrics while focusing on varied AI usage patterns.
        """
        week = max(0, min(week, self.config.weeks - 1))

        # Varied AI adoption around 50% - interesting for detection
        # Slight increase over time as more people try AI
        progress = week / (self.config.weeks - 1)
        ai_adoption = 0.45 + (0.15 * progress)

        return WeeklyParams(
            ai_adoption_rate=Decimal(str(round(ai_adoption, 3))),
            avg_cycle_time_hours=Decimal("36"),  # Moderate
            avg_review_time_hours=Decimal("12"),
            quality_rating=Decimal("2.6"),  # Average
            revert_rate=Decimal("0.04"),
            ci_pass_rate=Decimal("0.90"),
        )

    def get_member_archetypes(self) -> list[MemberArchetype]:
        """Return archetypes designed for AI detection game.

        Four types based on AI usage level and how obvious it is:
        - obvious_ai: Uses AI a lot, easy to detect
        - stealth_ai: Uses AI but writes in personal style
        - obvious_manual: Doesn't use AI, writes like AI
        - stealth_manual: Doesn't use AI, unique personal style
        """
        return [
            MemberArchetype(
                name="obvious_ai",
                count=2,
                ai_adoption_modifier=0.30,  # Heavy AI user
                review_load_weight=1.0,
                pr_volume_modifier=1.2,  # More productive with AI
                detectability=0.9,  # Very obvious AI patterns
            ),
            MemberArchetype(
                name="stealth_ai",
                count=1,
                ai_adoption_modifier=0.25,  # Also heavy AI user
                review_load_weight=1.0,
                pr_volume_modifier=1.1,
                detectability=0.3,  # But edits to personal style
            ),
            MemberArchetype(
                name="obvious_manual",
                count=1,
                ai_adoption_modifier=-0.40,  # Rarely uses AI
                review_load_weight=1.2,
                pr_volume_modifier=0.9,
                detectability=0.7,  # But writes in formulaic style
            ),
            MemberArchetype(
                name="stealth_manual",
                count=2,
                ai_adoption_modifier=-0.35,  # Also rarely uses AI
                review_load_weight=1.0,
                pr_volume_modifier=1.0,
                detectability=0.2,  # Unique personal style
            ),
        ]

    def get_guess_accuracy_for_archetype(self, archetype: str) -> tuple[float, float]:
        """Return guess accuracy ranges for the detection game.

        - obvious_ai: High accuracy (easy to spot)
        - stealth_ai: Low accuracy (hard to spot despite using AI)
        - obvious_manual: Low accuracy (looks like AI but isn't)
        - stealth_manual: High accuracy (clearly human)
        """
        accuracy_ranges = {
            "obvious_ai": (0.70, 0.85),  # Easy to correctly identify as AI
            "stealth_ai": (0.30, 0.45),  # Often guessed wrong (looks human)
            "obvious_manual": (0.35, 0.50),  # Often guessed wrong (looks AI)
            "stealth_manual": (0.65, 0.80),  # Easy to correctly identify as human
        }
        return accuracy_ranges.get(archetype, (0.45, 0.55))

    def get_review_state_distribution(self, week: int) -> dict[str, float]:
        """Return review distribution with more engagement for survey feature.

        Higher approval rate to generate more survey opportunities.
        """
        return {
            "approved": 0.70,  # More approvals = more survey chances
            "changes_requested": 0.20,
            "commented": 0.10,
        }
