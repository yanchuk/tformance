"""Copilot mock data generator for testing.

This module generates mock data in the exact GitHub Copilot metrics API format
for testing purposes.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TypedDict

from apps.metrics.seeding.deterministic import DeterministicRandom


class CopilotScenario(str, Enum):
    """Available scenarios for Copilot mock data generation."""

    HIGH_ADOPTION = "high_adoption"
    LOW_ADOPTION = "low_adoption"
    MIXED_USAGE = "mixed_usage"
    GROWTH = "growth"
    DECLINE = "decline"
    INACTIVE_LICENSES = "inactive_licenses"


class ScenarioParams(TypedDict, total=False):
    """Parameters controlling mock data generation for a single day."""

    acceptance_rate_range: tuple[float, float]
    active_users_range: tuple[int, int]
    completions_range: tuple[int, int]
    is_inactive_day: bool


@dataclass
class ScenarioConfig:
    """Configuration for a scenario type."""

    acceptance_rate_range: tuple[float, float] | None = None
    active_users_range: tuple[int, int] = (10, 50)
    completions_range: tuple[int, int] = (100, 3000)
    start_acceptance_rate: float | None = None
    end_acceptance_rate: float | None = None
    inactive_probability: float = 0.0

    @property
    def is_progression_scenario(self) -> bool:
        """Return True if this is a growth/decline progression scenario."""
        return self.start_acceptance_rate is not None and self.end_acceptance_rate is not None


# Scenario configurations using dataclass
SCENARIO_CONFIGS: dict[str, ScenarioConfig] = {
    CopilotScenario.HIGH_ADOPTION.value: ScenarioConfig(
        acceptance_rate_range=(0.40, 0.55),
        active_users_range=(15, 30),
        completions_range=(500, 3000),
    ),
    CopilotScenario.LOW_ADOPTION.value: ScenarioConfig(
        acceptance_rate_range=(0.15, 0.25),
        active_users_range=(5, 15),
        completions_range=(50, 500),
    ),
    CopilotScenario.MIXED_USAGE.value: ScenarioConfig(
        acceptance_rate_range=(0.15, 0.65),
        active_users_range=(10, 50),
        completions_range=(100, 3000),
    ),
    CopilotScenario.GROWTH.value: ScenarioConfig(
        start_acceptance_rate=0.30,
        end_acceptance_rate=0.70,
        active_users_range=(10, 30),
        completions_range=(100, 2000),
    ),
    CopilotScenario.DECLINE.value: ScenarioConfig(
        start_acceptance_rate=0.70,
        end_acceptance_rate=0.30,
        active_users_range=(10, 30),
        completions_range=(100, 2000),
    ),
    CopilotScenario.INACTIVE_LICENSES.value: ScenarioConfig(
        acceptance_rate_range=(0.20, 0.40),
        active_users_range=(0, 10),
        completions_range=(0, 500),
        inactive_probability=0.30,
    ),
}


class CopilotMockDataGenerator:
    """Generates mock Copilot metrics data in GitHub API format."""

    LANGUAGES = ["python", "typescript", "javascript", "go"]
    EDITORS = ["vscode", "jetbrains", "neovim"]

    def __init__(self, seed: int = 42):
        """Initialize generator with a seed for reproducibility.

        Args:
            seed: Integer seed value for deterministic random generation.
        """
        self.seed = seed
        self.rng = DeterministicRandom(seed)

    def generate(self, since: str, until: str, scenario: str = "mixed_usage") -> list[dict]:
        """Generate daily Copilot metrics in GitHub API format.

        Args:
            since: Start date in ISO 8601 format (YYYY-MM-DD).
            until: End date in ISO 8601 format (YYYY-MM-DD), inclusive.
            scenario: Scenario name controlling data patterns.
                Options: high_adoption, low_adoption, growth, decline,
                mixed_usage (default), inactive_licenses.

        Returns:
            List of daily metrics dictionaries.
        """
        start_date = datetime.strptime(since, "%Y-%m-%d").date()
        end_date = datetime.strptime(until, "%Y-%m-%d").date()

        # Calculate total days for progression scenarios
        total_days = (end_date - start_date).days + 1

        result = []
        current_date = start_date
        day_index = 0

        while current_date <= end_date:
            params = self._get_scenario_params(scenario, day_index, total_days)
            day_data = self._generate_day(current_date, params)
            result.append(day_data)
            current_date += timedelta(days=1)
            day_index += 1

        return result

    def _get_scenario_params(self, scenario: str, day_index: int, total_days: int) -> ScenarioParams:
        """Get generation parameters for a specific scenario and day.

        Args:
            scenario: Scenario name.
            day_index: 0-indexed day number (0 = first day).
            total_days: Total days being generated.

        Returns:
            ScenarioParams with: acceptance_rate_range, active_users_range, completions_range.

        Raises:
            ValueError: If the scenario name is not recognized.
        """
        if scenario not in SCENARIO_CONFIGS:
            valid_scenarios = [s.value for s in CopilotScenario]
            raise ValueError(f"Unknown scenario '{scenario}'. Valid scenarios: {valid_scenarios}")

        config = SCENARIO_CONFIGS[scenario]

        # Handle progression scenarios (growth/decline) with linear interpolation
        if config.is_progression_scenario:
            rate_range = self._interpolate_acceptance_rate(config, day_index, total_days)
            return {
                "acceptance_rate_range": rate_range,
                "active_users_range": config.active_users_range,
                "completions_range": config.completions_range,
                "is_inactive_day": False,
            }

        # Handle inactive_licenses scenario with random inactive days
        if config.inactive_probability > 0:
            is_inactive = self.rng.random() < config.inactive_probability
            if is_inactive:
                return {
                    "acceptance_rate_range": config.acceptance_rate_range,
                    "active_users_range": (0, 0),
                    "completions_range": (0, 5),
                    "is_inactive_day": True,
                }

        # Static scenarios: high_adoption, low_adoption, mixed_usage, inactive_licenses (active day)
        return {
            "acceptance_rate_range": config.acceptance_rate_range,
            "active_users_range": config.active_users_range,
            "completions_range": config.completions_range,
            "is_inactive_day": False,
        }

    def _interpolate_acceptance_rate(
        self, config: ScenarioConfig, day_index: int, total_days: int
    ) -> tuple[float, float]:
        """Calculate acceptance rate range using linear interpolation.

        Args:
            config: ScenarioConfig with start and end acceptance rates.
            day_index: 0-indexed day number (0 = first day).
            total_days: Total days being generated.

        Returns:
            Tuple of (min_rate, max_rate) with small variance around target.
        """
        assert config.start_acceptance_rate is not None, "start_acceptance_rate required for interpolation"
        assert config.end_acceptance_rate is not None, "end_acceptance_rate required for interpolation"
        progress = day_index / max(total_days - 1, 1)
        target_rate = (
            config.start_acceptance_rate + (config.end_acceptance_rate - config.start_acceptance_rate) * progress
        )
        # Add small variance around target
        rate_min = max(0.0, target_rate - 0.05)
        rate_max = min(1.0, target_rate + 0.05)
        return (rate_min, rate_max)

    def _generate_day(self, current_date, params: ScenarioParams | None = None) -> dict:
        """Generate metrics for a single day.

        Args:
            current_date: The date to generate metrics for.
            params: Scenario parameters controlling generation ranges.

        Returns:
            Dictionary with day's metrics.
        """
        # Use default params if not provided (for backward compatibility)
        if params is None:
            params = ScenarioParams(
                acceptance_rate_range=(0.25, 0.50),
                active_users_range=(10, 50),
                completions_range=(100, 3000),
                is_inactive_day=False,
            )

        active_min, active_max = params["active_users_range"]
        total_active_users = self.rng.randint(active_min, max(active_min, active_max))
        total_engaged_users = self.rng.randint(0, total_active_users) if total_active_users > 0 else 0

        comp_min, comp_max = params["completions_range"]
        total_completions = self.rng.randint(comp_min, max(comp_min, comp_max))

        rate_min, rate_max = params["acceptance_rate_range"]
        acceptance_rate = self.rng.uniform(rate_min, rate_max)
        total_acceptances = int(total_completions * acceptance_rate)
        # Ensure we stay within the specified rate range (use ceil for min to avoid truncation below range)
        if total_completions > 0:
            min_acceptances = math.ceil(total_completions * rate_min)
            max_acceptances = int(total_completions * rate_max)
            total_acceptances = max(min_acceptances, min(max_acceptances, total_acceptances))

        total_lines_suggested = self.rng.randint(200, 5000) if total_completions > 0 else 0
        lines_acceptance_rate = self.rng.uniform(rate_min, rate_max)
        total_lines_accepted = int(total_lines_suggested * lines_acceptance_rate)

        return {
            "date": current_date.isoformat(),
            "total_active_users": total_active_users,
            "total_engaged_users": total_engaged_users,
            "copilot_ide_code_completions": {
                "total_completions": total_completions,
                "total_acceptances": total_acceptances,
                "total_lines_suggested": total_lines_suggested,
                "total_lines_accepted": total_lines_accepted,
                "languages": self._generate_languages(total_completions, acceptance_rate),
                "editors": self._generate_editors(total_completions, acceptance_rate),
            },
            "copilot_ide_chat": {
                "total_chats": self.rng.randint(0, 100) if total_active_users > 0 else 0,
                "total_engaged_users": self.rng.randint(0, max(1, min(15, total_engaged_users)))
                if total_engaged_users > 0
                else 0,
            },
            "copilot_dotcom_chat": {
                "total_chats": self.rng.randint(0, 30) if total_active_users > 0 else 0,
            },
            "copilot_dotcom_pull_requests": {
                "total_prs": self.rng.randint(0, 20) if total_active_users > 0 else 0,
            },
        }

    def _generate_breakdown(self, items: list[str], total_completions: int) -> list[dict]:
        """Generate breakdown of completions across items (languages or editors).

        Distributes total completions across items with random acceptance rates.

        Args:
            items: List of item names (e.g., languages or editors).
            total_completions: Total completions to distribute.

        Returns:
            List of dictionaries with name, total_completions, total_acceptances,
            total_lines_suggested, and total_lines_accepted.
        """
        result = []
        remaining_completions = total_completions

        for i, item_name in enumerate(items):
            # Last item gets all remaining completions
            if i == len(items) - 1:
                item_completions = remaining_completions
            else:
                item_completions = self.rng.randint(0, remaining_completions // 2)
                remaining_completions -= item_completions

            if item_completions > 0:
                item_acceptance_rate = self.rng.uniform(0.25, 0.50)
                item_acceptances = int(item_completions * item_acceptance_rate)
                # Generate lines suggested/accepted proportional to completions
                item_lines_suggested = int(item_completions * self.rng.uniform(1.2, 2.0))
                item_lines_accepted = int(item_lines_suggested * item_acceptance_rate)
                result.append(
                    {
                        "name": item_name,
                        "total_completions": item_completions,
                        "total_acceptances": item_acceptances,
                        "total_lines_suggested": item_lines_suggested,
                        "total_lines_accepted": item_lines_accepted,
                    }
                )

        return result

    def _generate_languages(self, total_completions: int, acceptance_rate: float) -> list[dict]:
        """Generate language breakdown for completions.

        Args:
            total_completions: Total completions for the day.
            acceptance_rate: Base acceptance rate (unused, kept for API compatibility).

        Returns:
            List of language dictionaries.
        """
        return self._generate_breakdown(self.LANGUAGES, total_completions)

    def _generate_editors(self, total_completions: int, acceptance_rate: float) -> list[dict]:
        """Generate editor breakdown for completions.

        Args:
            total_completions: Total completions for the day.
            acceptance_rate: Base acceptance rate (unused, kept for API compatibility).

        Returns:
            List of editor dictionaries.
        """
        return self._generate_breakdown(self.EDITORS, total_completions)
