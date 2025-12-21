"""
Real project configurations for demo data seeding.

Defines target open source projects with their seeding configurations.
Each project will be seeded as a separate team with real GitHub data.

Usage:
    from apps.metrics.seeding.real_projects import REAL_PROJECTS, get_project

    config = get_project("posthog")
    print(config.repo_full_name)  # "posthog/posthog"
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RealProjectConfig:
    """Configuration for a real open source project.

    Attributes:
        repo_full_name: GitHub repository in "owner/repo" format.
        team_name: Display name for the team.
        team_slug: URL-safe slug for the team.
        max_prs: Maximum PRs to fetch (default 500).
        max_members: Maximum team members from contributors (default 15).
        days_back: Days of history to fetch (default 90).
        jira_project_key: Synthetic Jira project key (e.g., "POST").
        ai_base_adoption_rate: Base probability of AI usage (0.0-1.0).
        survey_response_rate: Probability of survey completion (0.0-1.0).
        description: Short description of the project.
    """

    repo_full_name: str
    team_name: str
    team_slug: str
    max_prs: int = 500
    max_members: int = 15
    days_back: int = 90
    jira_project_key: str = ""
    ai_base_adoption_rate: float = 0.35
    survey_response_rate: float = 0.60
    description: str = ""


# Registry of available real projects
REAL_PROJECTS: dict[str, RealProjectConfig] = {
    # Full parsing - smaller focused teams for complete picture
    "gumroad": RealProjectConfig(
        repo_full_name="antiwork/gumroad",
        team_name="Gumroad",
        team_slug="gumroad-demo",
        max_prs=1000,  # Full parsing
        max_members=50,  # All contributors
        days_back=90,
        jira_project_key="GUM",
        ai_base_adoption_rate=0.50,
        survey_response_rate=0.70,
        description="E-commerce platform for creators (full team)",
    ),
    "polar": RealProjectConfig(
        repo_full_name="polarsource/polar",
        team_name="Polar.sh",
        team_slug="polar-demo",
        max_prs=1000,  # Full parsing
        max_members=50,  # All contributors
        days_back=90,
        jira_project_key="POLAR",
        ai_base_adoption_rate=0.45,
        survey_response_rate=0.60,
        description="Open-source funding platform (full team)",
    ),
    # Sampled - large active repos
    "posthog": RealProjectConfig(
        repo_full_name="posthog/posthog",
        team_name="PostHog Analytics",
        team_slug="posthog-demo",
        max_prs=200,  # Sampled - very active repo
        max_members=25,
        days_back=90,
        jira_project_key="POST",
        ai_base_adoption_rate=0.40,
        survey_response_rate=0.65,
        description="Open-source product analytics (sampled)",
    ),
    "fastapi": RealProjectConfig(
        repo_full_name="tiangolo/fastapi",
        team_name="FastAPI Team",
        team_slug="fastapi-demo",
        max_prs=300,
        max_members=15,
        days_back=90,
        jira_project_key="FAST",
        ai_base_adoption_rate=0.30,
        survey_response_rate=0.55,
        description="Modern Python web framework",
    ),
}


def get_project(name: str) -> RealProjectConfig:
    """Get project configuration by name.

    Args:
        name: Project name (e.g., "posthog", "polar", "fastapi").

    Returns:
        RealProjectConfig for the project.

    Raises:
        KeyError: If project name is not found.
    """
    if name not in REAL_PROJECTS:
        available = ", ".join(REAL_PROJECTS.keys())
        raise KeyError(f"Project '{name}' not found. Available: {available}")
    return REAL_PROJECTS[name]


def list_projects() -> list[str]:
    """List all available project names.

    Returns:
        List of project names.
    """
    return list(REAL_PROJECTS.keys())


def get_all_projects() -> list[RealProjectConfig]:
    """Get all project configurations.

    Returns:
        List of all RealProjectConfig objects.
    """
    return list(REAL_PROJECTS.values())
