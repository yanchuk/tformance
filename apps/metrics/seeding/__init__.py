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

Note: Most submodules depend on factory-boy (dev-only). Imports are lazy
to avoid breaking production where factory-boy is not installed.
Only real_projects (INDUSTRIES, REAL_PROJECTS) is safe to import eagerly.
"""

# These modules have no dev-only dependencies — safe to import eagerly
from .real_projects import REAL_PROJECTS, RealProjectConfig, get_project, list_projects


def __getattr__(name):
    """Lazy imports for modules that depend on factory-boy (dev-only)."""
    _lazy_imports = {
        "GeneratorStats": (".data_generator", "GeneratorStats"),
        "ScenarioDataGenerator": (".data_generator", "ScenarioDataGenerator"),
        "DeterministicRandom": (".deterministic", "DeterministicRandom"),
        "GitHubAuthenticatedFetcher": (
            ".github_authenticated_fetcher",
            "GitHubAuthenticatedFetcher",
        ),
        "FetchedPR": (".github_fetcher", "FetchedPR"),
        "GitHubPublicFetcher": (".github_fetcher", "GitHubPublicFetcher"),
        "JiraIssueSimulator": (".jira_simulator", "JiraIssueSimulator"),
        "RealProjectSeeder": (".real_project_seeder", "RealProjectSeeder"),
        "RealProjectStats": (".real_project_seeder", "RealProjectStats"),
        "SCENARIO_REGISTRY": (".scenarios.registry", "SCENARIO_REGISTRY"),
        "get_scenario": (".scenarios.registry", "get_scenario"),
        "list_scenarios": (".scenarios.registry", "list_scenarios"),
        "SurveyAISimulator": (".survey_ai_simulator", "SurveyAISimulator"),
    }
    if name in _lazy_imports:
        module_path, attr = _lazy_imports[name]
        import importlib

        module = importlib.import_module(module_path, __package__)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
