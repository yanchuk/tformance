"""
Management command to seed demo data from real GitHub projects.

Seeds realistic demo data from open source projects like PostHog, Polar.sh,
and FastAPI, with simulated Jira issues, surveys, and AI usage.

Usage:
    # List available projects
    python manage.py seed_real_projects --list-projects

    # Seed all projects
    python manage.py seed_real_projects

    # Seed specific project
    python manage.py seed_real_projects --project posthog

    # Clear and reseed
    python manage.py seed_real_projects --project polar --clear

    # Custom options
    python manage.py seed_real_projects --project posthog --max-prs 200 --days-back 60

    # Use specific seed for reproducibility
    python manage.py seed_real_projects --project posthog --seed 42

NOTE: This command requires development dependencies (factory-boy).
      It is not available in production environments.
"""

import os

from django.core.management.base import BaseCommand, CommandError

# Guard imports - seeding requires factory-boy (dev dependency)
try:
    from apps.metrics.seeding.real_project_seeder import RealProjectSeeder, clear_project_data
    from apps.metrics.seeding.real_projects import REAL_PROJECTS, get_project, list_projects

    SEEDING_AVAILABLE = True
except ImportError:
    SEEDING_AVAILABLE = False
    RealProjectSeeder = None
    clear_project_data = None
    REAL_PROJECTS = {}
    get_project = None
    list_projects = None


class Command(BaseCommand):
    help = "Seed demo data from real GitHub projects (requires dev dependencies)"

    def add_arguments(self, parser):
        # Note: choices validation happens in handle() if seeding not available
        project_choices = list(REAL_PROJECTS.keys()) + ["all"] if REAL_PROJECTS else None
        parser.add_argument(
            "--project",
            type=str,
            choices=project_choices,
            help="Project to seed ('all' for all projects)",
        )
        parser.add_argument(
            "--list-projects",
            action="store_true",
            help="List available projects and exit",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing project data before seeding",
        )
        parser.add_argument(
            "--max-prs",
            type=int,
            help="Override maximum PRs to fetch",
        )
        parser.add_argument(
            "--max-members",
            type=int,
            help="Override maximum team members",
        )
        parser.add_argument(
            "--days-back",
            type=int,
            help="Override number of days of history to fetch",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility (default: 42)",
        )
        parser.add_argument(
            "--github-token",
            type=str,
            help="GitHub PAT (defaults to GITHUB_SEEDING_TOKENS env var)",
        )
        parser.add_argument(
            "--checkpoint-file",
            type=str,
            default=".seeding_checkpoint.json",
            help="Checkpoint file for resuming after rate limits (default: .seeding_checkpoint.json)",
        )
        parser.add_argument(
            "--no-graphql",
            action="store_true",
            help="Use REST API instead of GraphQL (slower but more reliable)",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Force re-fetch from GitHub, ignoring local cache",
        )
        parser.add_argument(
            "--no-cache",
            action="store_true",
            help="Disable local caching entirely (no read/write)",
        )
        parser.add_argument(
            "--no-check-runs",
            action="store_true",
            help="Skip fetching check runs (faster seeding, less CI/CD data)",
        )

    def handle(self, *args, **options):
        # Check dev dependencies are available
        if not SEEDING_AVAILABLE:
            raise CommandError(
                "This command requires development dependencies.\n"
                "Install them with: uv sync --group dev\n"
                "The seed_real_projects command is not available in production."
            )

        # Handle --list-projects
        if options["list_projects"]:
            self.print_projects()
            return

        # Check for GitHub token
        token = options["github_token"] or os.environ.get("GITHUB_SEEDING_TOKENS")
        if not token:
            self.stdout.write(
                self.style.ERROR(
                    "\nGitHub token required. Either:\n"
                    "  1. Set GITHUB_SEEDING_TOKENS env var (comma-separated for multiple tokens)\n"
                    "  2. Use --github-token argument\n"
                    "\nCreate tokens at: https://github.com/settings/tokens\n"
                    "Required scope: public_repo (read-only access)\n"
                )
            )
            return

        # Determine which projects to seed
        if options["project"] == "all":
            projects = list_projects()
        elif options["project"]:
            projects = [options["project"]]
        else:
            # Default to all projects
            projects = list_projects()

        self.stdout.write(f"\nSeeding {len(projects)} project(s)...")

        for project_name in projects:
            self.seed_project(project_name, token, options)

        self.stdout.write(self.style.SUCCESS("\nAll projects seeded successfully!"))

    def seed_project(self, project_name: str, token: str, options: dict):
        """Seed a single project.

        Args:
            project_name: Name of the project to seed.
            token: GitHub PAT.
            options: Command options.
        """
        config = get_project(project_name)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"Project: {config.team_name}")
        self.stdout.write(f"Repositories ({len(config.repos)}):")
        for repo in config.repos:
            self.stdout.write(f"  - {repo}")
        self.stdout.write("=" * 60)

        # Apply overrides
        if options["max_prs"]:
            config = config.__class__(**{**config.__dict__, "max_prs": options["max_prs"]})
        if options["max_members"]:
            config = config.__class__(**{**config.__dict__, "max_members": options["max_members"]})
        if options["days_back"]:
            config = config.__class__(**{**config.__dict__, "days_back": options["days_back"]})

        self.stdout.write(f"  Max PRs: {config.max_prs}")
        self.stdout.write(f"  Max members: {config.max_members}")
        self.stdout.write(f"  Days back: {config.days_back}")
        self.stdout.write(f"  Seed: {options['seed']}")

        # Clear if requested
        if options["clear"]:
            self.stdout.write(f"\nClearing existing data for {config.team_slug}...")
            if clear_project_data(config.team_slug):
                self.stdout.write(self.style.SUCCESS("  Data cleared"))
            else:
                self.stdout.write(self.style.WARNING("  No existing data to clear"))

        # Handle cache options
        use_cache = not options.get("no_cache", False)
        if options.get("refresh") and use_cache:
            self.stdout.write("\nRefreshing cache (deleting cached data)...")
            self._clear_cache_for_project(config)

        # Create seeder and run
        use_graphql = not options.get("no_graphql", False)
        api_type = "GraphQL (fast)" if use_graphql else "REST (slow)"
        cache_status = "enabled" if use_cache else "disabled"
        self.stdout.write(f"\nFetching data from GitHub using {api_type} (cache: {cache_status})...")
        checkpoint_file = options.get("checkpoint_file")
        if checkpoint_file and not use_graphql:
            self.stdout.write(f"  Checkpoint file: {checkpoint_file}")
        skip_check_runs = options.get("no_check_runs", False)
        if skip_check_runs:
            self.stdout.write("  Skipping check runs (--no-check-runs)")
        try:
            seeder = RealProjectSeeder(
                config=config,
                random_seed=options["seed"],
                github_token=token,
                checkpoint_file=checkpoint_file,
                use_graphql=use_graphql,
                use_cache=use_cache,
                skip_check_runs=skip_check_runs,
            )
            stats = seeder.seed()

            self.print_stats(stats)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError seeding {project_name}: {e}"))
            raise

    def print_projects(self):
        """Print available projects."""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("Available Projects")
        self.stdout.write("=" * 70)

        for name, config in REAL_PROJECTS.items():
            self.stdout.write(f"\n  {name}")
            self.stdout.write(f"    Repositories ({len(config.repos)}):")
            for repo in config.repos:
                self.stdout.write(f"      - {repo}")
            self.stdout.write(f"    Team: {config.team_name} ({config.team_slug})")
            self.stdout.write(f"    Max PRs per repo: {config.max_prs}")
            self.stdout.write(f"    Max members: {config.max_members}")
            self.stdout.write(f"    Days back: {config.days_back}")
            self.stdout.write(f"    AI adoption rate: {config.ai_base_adoption_rate:.0%}")
            if config.description:
                self.stdout.write(f"    Description: {config.description}")

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("\nUsage:")
        self.stdout.write("  python manage.py seed_real_projects --project <name>")
        self.stdout.write("  python manage.py seed_real_projects --project all")
        self.stdout.write("\nNote: Requires GITHUB_SEEDING_TOKENS environment variable (comma-separated)")
        self.stdout.write("Create tokens at: https://github.com/settings/tokens\n")

    def print_stats(self, stats):
        """Print seeding statistics.

        Args:
            stats: RealProjectStats instance.
        """
        self.stdout.write(self.style.SUCCESS(f"\n{stats.project_name} seeded successfully!"))
        self.stdout.write("  " + "-" * 40)
        self.stdout.write(f"  Team created: {'Yes' if stats.team_created else 'No (existing)'}")
        self.stdout.write(f"  Team members: {stats.team_members_created}")
        self.stdout.write(f"  Pull requests: {stats.prs_created}")
        self.stdout.write(f"  Reviews: {stats.reviews_created}")
        self.stdout.write(f"  Commits: {stats.commits_created}")
        self.stdout.write(f"  Files: {stats.files_created}")
        self.stdout.write(f"  Check runs: {stats.check_runs_created}")
        self.stdout.write(f"  Jira issues: {stats.jira_issues_created}")
        self.stdout.write(f"  Surveys: {stats.surveys_created}")
        self.stdout.write(f"  Survey reviews: {stats.survey_reviews_created}")
        self.stdout.write(f"  AI usage records: {stats.ai_usage_records}")
        self.stdout.write(f"  Weekly metrics: {stats.weekly_metrics_created}")
        self.stdout.write(f"  GitHub API calls: {stats.github_api_calls}")
        self.stdout.write("  " + "-" * 40)

    def _clear_cache_for_project(self, config):
        """Clear cached PR data for all repos in a project.

        Args:
            config: RealProjectConfig instance.
        """
        from pathlib import Path

        from apps.metrics.seeding.pr_cache import PRCache

        cache_dir = Path(".seeding_cache")
        for repo in config.repos:
            cache_path = PRCache.get_cache_path(repo, cache_dir)
            if cache_path.exists():
                cache_path.unlink()
                self.stdout.write(f"  Deleted cache: {cache_path}")
            else:
                self.stdout.write(f"  No cache found: {cache_path}")
