"""
Real project configurations for demo data seeding.

Defines target open source projects with their seeding configurations.
Each project will be seeded as a separate team with real GitHub data.

Usage:
    from apps.metrics.seeding.real_projects import REAL_PROJECTS, get_project

    config = get_project("polar")
    print(config.repos)  # ["polarsource/polar", "polarsource/polar-adapters", ...]
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RealProjectConfig:
    """Configuration for a real open source project.

    Attributes:
        repos: List of GitHub repositories in "owner/repo" format.
        team_name: Display name for the team.
        team_slug: URL-safe slug for the team.
        max_prs: Maximum PRs to fetch per repo (default 500).
        max_members: Maximum team members from contributors (default 15).
        days_back: Days of history to fetch (default 90).
        jira_project_key: Synthetic Jira project key (e.g., "POST").
        ai_base_adoption_rate: Base probability of AI usage (0.0-1.0).
        survey_response_rate: Probability of survey completion (0.0-1.0).
        description: Short description of the project.
    """

    repos: tuple[str, ...] = field(default_factory=tuple)
    team_name: str = ""
    team_slug: str = ""
    max_prs: int = 500
    max_members: int = 15
    days_back: int = 90
    jira_project_key: str = ""
    ai_base_adoption_rate: float = 0.35
    survey_response_rate: float = 0.60
    description: str = ""

    @property
    def repo_full_name(self) -> str:
        """Primary repo for backward compatibility."""
        return self.repos[0] if self.repos else ""


# Registry of available real projects
REAL_PROJECTS: dict[str, RealProjectConfig] = {
    # Full parsing - smaller focused teams for complete picture
    "antiwork": RealProjectConfig(
        repos=(
            "antiwork/gumroad",
            "antiwork/flexile",
            "antiwork/helper",
        ),
        team_name="Antiwork",
        team_slug="antiwork-demo",
        max_prs=300,  # Per repo limit
        max_members=50,  # All contributors
        days_back=90,
        jira_project_key="ANTI",
        ai_base_adoption_rate=0.50,
        survey_response_rate=0.70,
        description="Antiwork portfolio: Gumroad, Flexile, Helper",
    ),
    "polar": RealProjectConfig(
        repos=(
            "polarsource/polar",
            "polarsource/polar-adapters",
            "polarsource/polar-python",
            "polarsource/polar-js",
        ),
        team_name="Polar.sh",
        team_slug="polar-demo",
        max_prs=300,  # Per repo limit
        max_members=50,  # All contributors
        days_back=90,
        jira_project_key="POLAR",
        ai_base_adoption_rate=0.45,
        survey_response_rate=0.60,
        description="Polar platform + SDKs (Python, JS, Adapters)",
    ),
    # Sampled - large active repos
    "posthog": RealProjectConfig(
        repos=(
            "PostHog/posthog",  # Main product (Python)
            "PostHog/posthog.com",  # Website/docs (TypeScript)
            "PostHog/posthog-js",  # JavaScript SDK
            "PostHog/posthog-python",  # Python SDK
        ),
        team_name="PostHog Analytics",
        team_slug="posthog-demo",
        max_prs=200,  # Sampled - very active repos
        max_members=50,
        days_back=90,
        jira_project_key="POST",
        ai_base_adoption_rate=0.40,
        survey_response_rate=0.65,
        description="Open-source product analytics + SDKs",
    ),
    "fastapi": RealProjectConfig(
        repos=("tiangolo/fastapi",),
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
    # AI-native companies - high signal for AI detection patterns
    "anthropic": RealProjectConfig(
        repos=(
            "anthropics/anthropic-cookbook",
            "anthropics/anthropic-sdk-python",
            "anthropics/courses",
        ),
        team_name="Anthropic",
        team_slug="anthropic-demo",
        max_prs=100,
        max_members=30,
        days_back=90,
        jira_project_key="ANTH",
        ai_base_adoption_rate=0.80,  # High - AI company
        survey_response_rate=0.50,
        description="Anthropic AI - cookbook, SDKs, courses",
    ),
    # Active OSS projects with modern teams
    "calcom": RealProjectConfig(
        repos=("calcom/cal.com",),
        team_name="Cal.com",
        team_slug="calcom-demo",
        max_prs=150,
        max_members=50,
        days_back=90,
        jira_project_key="CAL",
        ai_base_adoption_rate=0.35,
        survey_response_rate=0.55,
        description="Open source scheduling infrastructure",
    ),
    "trigger": RealProjectConfig(
        repos=("triggerdotdev/trigger.dev",),
        team_name="Trigger.dev",
        team_slug="trigger-demo",
        max_prs=100,
        max_members=30,
        days_back=90,
        jira_project_key="TRIG",
        ai_base_adoption_rate=0.40,
        survey_response_rate=0.55,
        description="Open source background jobs platform",
    ),
    # ========== Tier 1: High AI Signal ==========
    "vercel": RealProjectConfig(
        repos=(
            "vercel/ai",  # AI SDK - likely high AI tool usage
            "vercel/next.js",  # Main framework
            "vercel/vercel",  # CLI
        ),
        team_name="Vercel",
        team_slug="vercel-demo",
        max_prs=150,  # Very active repos
        max_members=50,
        days_back=90,
        jira_project_key="VERC",
        ai_base_adoption_rate=0.45,
        survey_response_rate=0.55,
        description="Vercel platform, Next.js, and AI SDK",
    ),
    "supabase": RealProjectConfig(
        repos=(
            "supabase/supabase",  # Main platform
            "supabase/realtime",  # Realtime server
            "supabase/supabase-js",  # JS SDK
        ),
        team_name="Supabase",
        team_slug="supabase-demo",
        max_prs=150,
        max_members=50,
        days_back=90,
        jira_project_key="SUPA",
        ai_base_adoption_rate=0.40,
        survey_response_rate=0.55,
        description="Open source Firebase alternative",
    ),
    "langchain": RealProjectConfig(
        repos=(
            "langchain-ai/langchain",  # Python SDK
            "langchain-ai/langchainjs",  # JS SDK
        ),
        team_name="LangChain",
        team_slug="langchain-demo",
        max_prs=200,  # Very active
        max_members=50,
        days_back=90,
        jira_project_key="LANG",
        ai_base_adoption_rate=0.60,  # AI/LLM focused team
        survey_response_rate=0.50,
        description="LLM application framework",
    ),
    "linear": RealProjectConfig(
        repos=("linearapp/linear",),
        team_name="Linear",
        team_slug="linear-demo",
        max_prs=100,
        max_members=30,
        days_back=90,
        jira_project_key="LIN",
        ai_base_adoption_rate=0.45,
        survey_response_rate=0.60,
        description="Modern issue tracking",
    ),
    # ========== Tier 2: Varied Signal ==========
    "resend": RealProjectConfig(
        repos=(
            "resend/resend-node",  # Node SDK
            "resend/react-email",  # React Email
        ),
        team_name="Resend",
        team_slug="resend-demo",
        max_prs=100,
        max_members=20,
        days_back=90,
        jira_project_key="RSND",
        ai_base_adoption_rate=0.35,
        survey_response_rate=0.55,
        description="Developer-first email API",
    ),
    "deno": RealProjectConfig(
        repos=(
            "denoland/deno",  # Main runtime (Rust)
            "denoland/fresh",  # Fresh framework
        ),
        team_name="Deno",
        team_slug="deno-demo",
        max_prs=150,
        max_members=30,
        days_back=90,
        jira_project_key="DENO",
        ai_base_adoption_rate=0.30,  # Systems programming
        survey_response_rate=0.50,
        description="Modern JavaScript/TypeScript runtime",
    ),
    "neon": RealProjectConfig(
        repos=(
            "neondatabase/neon",  # Core (Rust)
            "neondatabase/serverless",  # Serverless driver
        ),
        team_name="Neon",
        team_slug="neon-demo",
        max_prs=100,
        max_members=30,
        days_back=90,
        jira_project_key="NEON",
        ai_base_adoption_rate=0.35,
        survey_response_rate=0.55,
        description="Serverless Postgres",
    ),
    # ========== Tier 3: Large Product Teams (100+ contributors) ==========
    "twenty": RealProjectConfig(
        repos=("twentyhq/twenty",),
        team_name="Twenty CRM",
        team_slug="twenty-demo",
        max_prs=300,
        max_members=50,
        days_back=90,
        jira_project_key="TWENTY",
        ai_base_adoption_rate=0.45,
        survey_response_rate=0.55,
        description="Open source Salesforce alternative (561 contributors)",
    ),
    "novu": RealProjectConfig(
        repos=("novuhq/novu",),
        team_name="Novu",
        team_slug="novu-demo",
        max_prs=300,
        max_members=50,
        days_back=90,
        jira_project_key="NOVU",
        ai_base_adoption_rate=0.50,
        survey_response_rate=0.55,
        description="Notification infrastructure (447 contributors)",
    ),
    "hoppscotch": RealProjectConfig(
        repos=("hoppscotch/hoppscotch",),
        team_name="Hoppscotch",
        team_slug="hoppscotch-demo",
        max_prs=200,
        max_members=50,
        days_back=90,
        jira_project_key="HOPP",
        ai_base_adoption_rate=0.40,
        survey_response_rate=0.50,
        description="Open source Postman alternative (314 contributors)",
    ),
    "plane": RealProjectConfig(
        repos=("makeplane/plane",),
        team_name="Plane",
        team_slug="plane-demo",
        max_prs=300,
        max_members=50,
        days_back=90,
        jira_project_key="PLANE",
        ai_base_adoption_rate=0.45,
        survey_response_rate=0.55,
        description="Open source Jira/Linear alternative (151 contributors)",
    ),
    "documenso": RealProjectConfig(
        repos=("documenso/documenso",),
        team_name="Documenso",
        team_slug="documenso-demo",
        max_prs=200,
        max_members=50,
        days_back=90,
        jira_project_key="DOCS",
        ai_base_adoption_rate=0.50,
        survey_response_rate=0.55,
        description="Open source DocuSign alternative (142 contributors)",
    ),
    # ========== Tier 4: Self-Hosting & DevTools ==========
    "coolify": RealProjectConfig(
        repos=("coollabsio/coolify",),
        team_name="Coolify",
        team_slug="coolify-demo",
        max_prs=300,
        max_members=50,
        days_back=90,
        jira_project_key="COOL",
        ai_base_adoption_rate=0.45,
        survey_response_rate=0.55,
        description="Self-hosted Heroku/Vercel alternative (48.7k stars)",
    ),
    "infisical": RealProjectConfig(
        repos=("Infisical/infisical",),
        team_name="Infisical",
        team_slug="infisical-demo",
        max_prs=300,
        max_members=50,
        days_back=90,
        jira_project_key="INFI",
        ai_base_adoption_rate=0.45,
        survey_response_rate=0.55,
        description="Secrets management platform (24.3k stars)",
    ),
    "dub": RealProjectConfig(
        repos=("dubinc/dub",),
        team_name="Dub",
        team_slug="dub-demo",
        max_prs=300,
        max_members=50,
        days_back=90,
        jira_project_key="DUB",
        ai_base_adoption_rate=0.50,
        survey_response_rate=0.55,
        description="Link management platform (88 contributors)",
    ),
    # ========== Tier 5: Billing & Surveys ==========
    "lago": RealProjectConfig(
        repos=("getlago/lago",),
        team_name="Lago",
        team_slug="lago-demo",
        max_prs=200,
        max_members=30,
        days_back=90,
        jira_project_key="LAGO",
        ai_base_adoption_rate=0.45,
        survey_response_rate=0.55,
        description="Usage-based billing (Y Combinator backed)",
    ),
    "formbricks": RealProjectConfig(
        repos=("formbricks/formbricks",),
        team_name="Formbricks",
        team_slug="formbricks-demo",
        max_prs=200,
        max_members=30,
        days_back=90,
        jira_project_key="FORM",
        ai_base_adoption_rate=0.50,
        survey_response_rate=0.60,
        description="Open source Qualtrics alternative",
    ),
    # ========== Tier 6: AI-Native Startups ==========
    "compai": RealProjectConfig(
        repos=("trycompai/comp",),
        team_name="Comp AI",
        team_slug="compai-demo",
        max_prs=200,
        max_members=30,
        days_back=90,
        jira_project_key="COMP",
        ai_base_adoption_rate=0.70,  # AI-native company
        survey_response_rate=0.60,
        description="AI-powered compliance platform (SOC2, ISO27001)",
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
