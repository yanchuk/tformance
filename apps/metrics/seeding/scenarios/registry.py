"""
Scenario registry for demo data seeding.

Maps scenario names to their implementation classes.
Use --list-scenarios with the seed command to see available options.

Usage:
    from apps.metrics.seeding.scenarios import SCENARIO_REGISTRY

    scenario_class = SCENARIO_REGISTRY["ai-success"]
    scenario = scenario_class()
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseScenario

# Registry will be populated when scenario modules are imported
# This is done lazily to avoid circular imports
SCENARIO_REGISTRY: dict[str, type["BaseScenario"]] = {}


def register_scenario(name: str):
    """Decorator to register a scenario class.

    Usage:
        @register_scenario("ai-success")
        class AISuccessScenario(BaseScenario):
            ...
    """

    def decorator(cls):
        SCENARIO_REGISTRY[name] = cls
        return cls

    return decorator


def get_scenario(name: str) -> "BaseScenario":
    """Get a scenario instance by name.

    Args:
        name: The scenario name (e.g., "ai-success").

    Returns:
        An instance of the scenario.

    Raises:
        KeyError: If scenario name is not registered.

    Note:
        Scenarios are registered when imported via the @register_scenario
        decorator. Import from apps.metrics.seeding.scenarios to ensure
        all scenarios are loaded.
    """
    if name not in SCENARIO_REGISTRY:
        available = ", ".join(sorted(SCENARIO_REGISTRY.keys()))
        raise KeyError(f"Unknown scenario '{name}'. Available: {available}")

    return SCENARIO_REGISTRY[name]()


def list_scenarios() -> list[dict]:
    """List all available scenarios with their descriptions.

    Returns:
        List of dicts with 'name', 'description', 'member_count', 'weeks' keys.

    Note:
        Scenarios are registered when imported. Import from
        apps.metrics.seeding.scenarios to ensure all scenarios are loaded.
    """
    result = []
    for name, cls in sorted(SCENARIO_REGISTRY.items()):
        scenario = cls()
        result.append(
            {
                "name": name,
                "description": scenario.config.description,
                "member_count": scenario.config.member_count,
                "weeks": scenario.config.weeks,
            }
        )
    return result
