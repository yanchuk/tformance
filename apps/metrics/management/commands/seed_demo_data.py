"""
Management command to seed demo data for development.

Supports two modes:
1. Scenario-based seeding (recommended) - Uses predefined scenarios with coherent data
2. Legacy mode - Uses simple factory-based seeding

Usage:
    # Scenario-based seeding (recommended)
    python manage.py seed_demo_data --scenario ai-success --seed 42
    python manage.py seed_demo_data --scenario review-bottleneck --seed 123
    python manage.py seed_demo_data --scenario baseline
    python manage.py seed_demo_data --scenario detective-game

    # List available scenarios
    python manage.py seed_demo_data --list-scenarios

    # Scenario with options
    python manage.py seed_demo_data --scenario ai-success --no-github
    python manage.py seed_demo_data --scenario ai-success --source-repo tiangolo/fastapi

    # Legacy mode (backward compatible)
    python manage.py seed_demo_data --teams 2 --members 10 --prs 100

    # Clear existing data before seeding
    python manage.py seed_demo_data --clear --scenario ai-success

NOTE: This command requires development dependencies (factory-boy).
      It is not available in production environments.
"""

from django.core.management.base import BaseCommand, CommandError

# Guard imports - factory-boy is only available in dev environment
try:
    from apps.metrics.factories import (
        AIUsageDailyFactory,
        CommitFactory,
        JiraIssueFactory,
        PRReviewFactory,
        PRSurveyFactory,
        PRSurveyReviewFactory,
        PullRequestFactory,
        TeamMemberFactory,
        WeeklyMetricsFactory,
    )

    FACTORY_BOY_AVAILABLE = True
except ImportError:
    FACTORY_BOY_AVAILABLE = False
    # Define dummy placeholders to prevent NameError
    AIUsageDailyFactory = None
    CommitFactory = None
    JiraIssueFactory = None
    PRReviewFactory = None
    PRSurveyFactory = None
    PRSurveyReviewFactory = None
    PullRequestFactory = None
    TeamMemberFactory = None
    WeeklyMetricsFactory = None

from apps.metrics.models import (
    AIUsageDaily,
    Commit,
    JiraIssue,
    PRReview,
    PRSurvey,
    PRSurveyReview,
    PullRequest,
    TeamMember,
    WeeklyMetrics,
)

# Seeding module also requires factory-boy
try:
    from apps.metrics.seeding import ScenarioDataGenerator, get_scenario, list_scenarios
except ImportError:
    ScenarioDataGenerator = None
    get_scenario = None
    list_scenarios = None

from apps.teams.models import Team


class Command(BaseCommand):
    help = "Seed demo data for development and testing (requires dev dependencies)"

    def add_arguments(self, parser):
        # Scenario-based seeding (new)
        parser.add_argument(
            "--scenario",
            type=str,
            choices=["ai-success", "review-bottleneck", "baseline", "detective-game"],
            help="Use scenario-based seeding with predefined patterns",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducible generation (default: 42)",
        )
        parser.add_argument(
            "--source-repo",
            type=str,
            action="append",
            dest="source_repos",
            help="GitHub repo to fetch PR data from (can specify multiple)",
        )
        parser.add_argument(
            "--no-github",
            action="store_true",
            help="Skip fetching real PR data from GitHub",
        )
        parser.add_argument(
            "--list-scenarios",
            action="store_true",
            help="List available scenarios and exit",
        )

        # Legacy mode arguments (backward compatible)
        parser.add_argument(
            "--teams",
            type=int,
            default=1,
            help="[Legacy] Number of teams to create (default: 1)",
        )
        parser.add_argument(
            "--members",
            type=int,
            default=5,
            help="[Legacy] Number of team members per team (default: 5)",
        )
        parser.add_argument(
            "--prs",
            type=int,
            default=50,
            help="[Legacy] Number of pull requests per team (default: 50)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing metrics data before seeding",
        )
        parser.add_argument(
            "--team-slug",
            type=str,
            help="Use existing team by slug instead of creating new one",
        )

    def handle(self, *args, **options):
        # Check dev dependencies are available
        if not FACTORY_BOY_AVAILABLE:
            raise CommandError(
                "This command requires development dependencies.\n"
                "Install them with: uv sync --group dev\n"
                "The seed_demo_data command is not available in production."
            )

        # Handle --list-scenarios
        if options["list_scenarios"]:
            self.print_scenarios()
            return

        if options["clear"]:
            self.clear_data()

        # Scenario-based seeding (new mode)
        if options["scenario"]:
            self.handle_scenario_mode(options)
            return

        # Legacy mode (backward compatible)
        self.handle_legacy_mode(options)

    def handle_scenario_mode(self, options):
        """Handle scenario-based seeding."""
        scenario_name = options["scenario"]
        seed = options["seed"]
        fetch_github = not options["no_github"]

        self.stdout.write(f"\nScenario-based seeding: {scenario_name}")
        self.stdout.write(f"  Seed: {seed}")
        self.stdout.write(f"  GitHub data: {'enabled' if fetch_github else 'disabled'}")

        # Get or create team
        scenario = get_scenario(scenario_name)
        team = self.get_or_create_scenario_team(scenario, options)
        if not team:
            return

        # Check for existing data
        existing_prs = PullRequest.objects.filter(team=team).count()
        if existing_prs > 0 and not options["clear"]:
            msg = f"  Team already has {existing_prs} PRs. Use --clear to reseed."
            self.stdout.write(self.style.WARNING(msg))
            return

        # Override source repos if specified
        if options["source_repos"]:
            scenario.config.github_source_repos = options["source_repos"]

        # Generate data
        generator = ScenarioDataGenerator(
            scenario=scenario,
            seed=seed,
            fetch_github=fetch_github,
        )

        stats = generator.generate(team)

        self.stdout.write(self.style.SUCCESS("\nScenario data seeded successfully!"))
        self.stdout.write(f"  Team members: {stats.team_members_created}")
        self.stdout.write(f"  Pull requests: {stats.prs_created}")
        self.stdout.write(f"    - From GitHub: {stats.github_prs_used}")
        self.stdout.write(f"    - From factory: {stats.factory_prs_used}")
        self.stdout.write(f"  Reviews: {stats.reviews_created}")
        self.stdout.write(f"  Commits: {stats.commits_created}")
        self.stdout.write(f"  Surveys: {stats.surveys_created}")
        self.stdout.write(f"  AI usage records: {stats.ai_usage_records}")
        self.stdout.write(f"  Weekly metrics: {stats.weekly_metrics_created}")

    def get_or_create_scenario_team(self, scenario, options):
        """Get or create team for scenario."""
        if options["team_slug"]:
            try:
                team = Team.objects.get(slug=options["team_slug"])
                self.stdout.write(f"Using existing team: {team.name}")
                return team
            except Team.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Team with slug '{options['team_slug']}' not found"))
                return None

        # Use scenario's default team config
        team, created = Team.objects.get_or_create(
            slug=scenario.config.team_slug,
            defaults={"name": scenario.config.team_name},
        )
        if created:
            self.stdout.write(f"Created team: {team.name} (slug: {team.slug})")
        else:
            self.stdout.write(f"Using existing team: {team.name} (slug: {team.slug})")
        return team

    def print_scenarios(self):
        """Print available scenarios."""
        self.stdout.write("\nAvailable scenarios:")
        self.stdout.write("=" * 60)
        for info in list_scenarios():
            self.stdout.write(f"\n  {info['name']}")
            self.stdout.write(f"    {info['description']}")
            self.stdout.write(f"    Members: {info['member_count']}, Weeks: {info['weeks']}")
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("\nUsage: python manage.py seed_demo_data --scenario <name>")

    def handle_legacy_mode(self, options):
        """Handle legacy factory-based seeding."""
        teams = self.get_or_create_teams(options)

        for team in teams:
            self.stdout.write(f"\nSeeding data for team: {team.name}")

            # Check if team already has PR data - if so, skip seeding to avoid conflicts
            existing_prs = PullRequest.objects.filter(team=team).count()
            if existing_prs > 0 and not options["clear"]:
                msg = f"  Team already has {existing_prs} PRs. Use --clear to reseed."
                self.stdout.write(self.style.WARNING(msg))
                continue

            members = self.seed_team_members(team, options["members"])
            prs = self.seed_pull_requests(team, members, options["prs"])
            self.seed_reviews(team, prs, members)
            self.seed_commits(team, prs, members)
            self.seed_jira_issues(team, members)
            self.seed_ai_usage(team, members)
            self.seed_surveys(team, prs)
            self.seed_weekly_metrics(team, members)

        self.stdout.write(self.style.SUCCESS("\nDemo data seeded successfully!"))
        self.print_summary()

    def clear_data(self):
        """Clear all existing metrics data."""
        self.stdout.write("Clearing existing metrics data...")
        models = [
            PRSurveyReview,
            PRSurvey,
            PRReview,
            Commit,
            PullRequest,
            JiraIssue,
            AIUsageDaily,
            WeeklyMetrics,
            TeamMember,
        ]
        for model in models:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f"  Deleted {count} {model.__name__} records")

    def get_or_create_teams(self, options):
        """Get existing team or create new ones."""
        if options["team_slug"]:
            try:
                team = Team.objects.get(slug=options["team_slug"])
                self.stdout.write(f"Using existing team: {team.name}")
                return [team]
            except Team.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Team with slug '{options['team_slug']}' not found"))
                return []

        teams = []
        for i in range(options["teams"]):
            slug = f"demo-team-{i + 1}"
            team, created = Team.objects.get_or_create(
                slug=slug,
                defaults={"name": f"Demo Team {i + 1}"},
            )
            teams.append(team)
            if created:
                self.stdout.write(f"Created team: {team.name} (slug: {team.slug})")
            else:
                self.stdout.write(f"Using existing team: {team.name} (slug: {team.slug})")
        return teams

    def seed_team_members(self, team, count):
        """Create team members or return existing ones."""
        # Check if team already has members
        existing_members = list(TeamMember.objects.filter(team=team))
        if existing_members:
            self.stdout.write(f"  Using {len(existing_members)} existing team members")
            return existing_members

        members = []
        # Create one lead
        lead = TeamMemberFactory(team=team, role="lead", display_name="Tech Lead")
        members.append(lead)

        # Create developers
        for _ in range(count - 1):
            member = TeamMemberFactory(team=team, role="developer")
            members.append(member)

        self.stdout.write(f"  Created {len(members)} team members")
        return members

    def seed_pull_requests(self, team, members, count):
        """Create pull requests."""
        prs = []
        for _ in range(count):
            author = members[hash(str(_)) % len(members)]  # Deterministic but varied
            pr = PullRequestFactory(team=team, author=author)
            prs.append(pr)
        self.stdout.write(f"  Created {len(prs)} pull requests")
        return prs

    def seed_reviews(self, team, prs, members):
        """Create PR reviews."""
        reviews = []
        for pr in prs:
            # 1-3 reviews per PR
            num_reviews = (hash(str(pr.id)) % 3) + 1
            reviewers = [m for m in members if m != pr.author]
            for i in range(min(num_reviews, len(reviewers))):
                reviewer = reviewers[i % len(reviewers)]
                review = PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer)
                reviews.append(review)
        self.stdout.write(f"  Created {len(reviews)} PR reviews")
        return reviews

    def seed_commits(self, team, prs, members):
        """Create commits for PRs and standalone."""
        commits = []
        # Commits linked to PRs
        for pr in prs:
            num_commits = (hash(str(pr.id)) % 5) + 1  # 1-5 commits per PR
            for _ in range(num_commits):
                commit = CommitFactory(team=team, pull_request=pr, author=pr.author, github_repo=pr.github_repo)
                commits.append(commit)

        # Some standalone commits
        for member in members:
            for _ in range(3):
                commit = CommitFactory(team=team, author=member, pull_request=None)
                commits.append(commit)

        self.stdout.write(f"  Created {len(commits)} commits")
        return commits

    def seed_jira_issues(self, team, members):
        """Create Jira issues."""
        issues = []
        issues_per_member = 8
        for member in members:
            for _ in range(issues_per_member):
                issue = JiraIssueFactory(team=team, assignee=member)
                issues.append(issue)
        self.stdout.write(f"  Created {len(issues)} Jira issues")
        return issues

    def seed_ai_usage(self, team, members):
        """Create AI usage records."""
        from datetime import timedelta

        from django.utils import timezone

        records = []
        days_of_data = 30
        base_date = timezone.now().date()

        for member in members:
            for day in range(days_of_data):
                # ~70% chance of AI usage on any given day
                if hash(f"{member.id}-{day}") % 10 < 7:
                    date = base_date - timedelta(days=day)
                    # Alternate between copilot and cursor
                    source = "copilot" if day % 2 == 0 else "cursor"
                    try:
                        record = AIUsageDailyFactory(team=team, member=member, date=date, source=source)
                        records.append(record)
                    except Exception:
                        pass  # Skip duplicates
        self.stdout.write(f"  Created {len(records)} AI usage records")
        return records

    def seed_surveys(self, team, prs):
        """Create PR surveys and reviews."""
        surveys = []
        survey_reviews = []

        # Create surveys for ~60% of merged PRs
        merged_prs = [pr for pr in prs if pr.state == "merged"]
        for pr in merged_prs:
            if hash(str(pr.id)) % 10 < 6:
                survey = PRSurveyFactory(team=team, pull_request=pr, author=pr.author)
                surveys.append(survey)

                # Add 1-2 reviewer responses per survey
                num_reviews = (hash(str(survey.id)) % 2) + 1
                for _ in range(num_reviews):
                    try:
                        review = PRSurveyReviewFactory(team=team, survey=survey)
                        survey_reviews.append(review)
                    except Exception:
                        pass  # Skip if unique constraint violated

        self.stdout.write(f"  Created {len(surveys)} PR surveys with {len(survey_reviews)} reviews")
        return surveys, survey_reviews

    def seed_weekly_metrics(self, team, members):
        """Create weekly metrics aggregates."""
        from datetime import timedelta

        from django.utils import timezone

        metrics = []
        weeks_of_data = 8
        base_date = timezone.now().date()
        # Get Monday of current week
        base_monday = base_date - timedelta(days=base_date.weekday())

        for member in members:
            for week in range(weeks_of_data):
                week_start = base_monday - timedelta(weeks=week)
                try:
                    metric = WeeklyMetricsFactory(team=team, member=member, week_start=week_start)
                    metrics.append(metric)
                except Exception:
                    pass  # Skip if unique constraint violated
        self.stdout.write(f"  Created {len(metrics)} weekly metrics records")
        return metrics

    def print_summary(self):
        """Print summary of seeded data."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("DATA SUMMARY")
        self.stdout.write("=" * 50)

        models = [
            ("Teams", Team),
            ("Team Members", TeamMember),
            ("Pull Requests", PullRequest),
            ("PR Reviews", PRReview),
            ("Commits", Commit),
            ("Jira Issues", JiraIssue),
            ("AI Usage Daily", AIUsageDaily),
            ("PR Surveys", PRSurvey),
            ("PR Survey Reviews", PRSurveyReview),
            ("Weekly Metrics", WeeklyMetrics),
        ]

        for name, model in models:
            count = model.objects.count()
            self.stdout.write(f"  {name}: {count}")

        self.stdout.write("=" * 50)
