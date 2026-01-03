"""
Scenario definitions for demo data seeding.

Available scenarios:
- ai-success: Progressive AI adoption success story
- review-bottleneck: High AI output, bottlenecked reviews
- baseline: Steady-state, low AI adoption for comparison
- detective-game: Survey engagement and leaderboard focus
"""

# Import scenarios to register them
from .ai_success import AISuccessScenario
from .base import BaseScenario, MemberArchetype, ScenarioConfig, WeeklyParams
from .baseline import BaselineScenario
from .detective_game import DetectiveGameScenario
from .registry import SCENARIO_REGISTRY, get_scenario, list_scenarios
from .review_bottleneck import ReviewBottleneckScenario
from .test_minimal import TestMinimalScenario

__all__ = [
    "BaseScenario",
    "MemberArchetype",
    "ScenarioConfig",
    "WeeklyParams",
    "SCENARIO_REGISTRY",
    "get_scenario",
    "list_scenarios",
    "AISuccessScenario",
    "BaselineScenario",
    "DetectiveGameScenario",
    "ReviewBottleneckScenario",
    "TestMinimalScenario",
]
