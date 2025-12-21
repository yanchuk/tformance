"""
Demo data seeding package for tformance.

This package provides scenario-based demo data generation with:
- Hybrid data sourcing (GitHub + factories)
- Deterministic reproducibility via --seed flag
- 4 scenario presets: ai-success, review-bottleneck, baseline, detective-game
- Real project seeding from PostHog, Polar, FastAPI

Usage:
    python manage.py seed_demo_data --scenario ai-success --seed 42
    python manage.py seed_real_projects --project posthog
"""

from .data_generator import GeneratorStats, ScenarioDataGenerator
from .deterministic import DeterministicRandom
from .github_authenticated_fetcher import GitHubAuthenticatedFetcher
from .github_fetcher import FetchedPR, GitHubPublicFetcher
from .jira_simulator import JiraIssueSimulator
from .real_project_seeder import RealProjectSeeder, RealProjectStats
from .real_projects import REAL_PROJECTS, RealProjectConfig, get_project, list_projects
from .scenarios.registry import SCENARIO_REGISTRY, get_scenario, list_scenarios
from .survey_ai_simulator import SurveyAISimulator

__all__ = [
    "DeterministicRandom",
    "FetchedPR",
    "GeneratorStats",
    "GitHubAuthenticatedFetcher",
    "GitHubPublicFetcher",
    "JiraIssueSimulator",
    "REAL_PROJECTS",
    "RealProjectConfig",
    "RealProjectSeeder",
    "RealProjectStats",
    "SCENARIO_REGISTRY",
    "ScenarioDataGenerator",
    "SurveyAISimulator",
    "get_project",
    "get_scenario",
    "list_projects",
    "list_scenarios",
]
