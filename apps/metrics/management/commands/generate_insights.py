"""
Management command to generate insights for testing.

This runs all insight rules against existing team data and creates DailyInsight records.

Usage:
    # Generate insights for all teams
    python manage.py generate_insights

    # Generate insights for a specific team
    python manage.py generate_insights --team-slug demo-team

    # Generate insights for a specific date
    python manage.py generate_insights --date 2025-12-20

    # Clear existing insights before generating
    python manage.py generate_insights --clear

    # Generate sample insights without running rules (for UI testing)
    python manage.py generate_insights --sample
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.metrics.insights.engine import compute_insights
from apps.metrics.models import DailyInsight
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Generate insights for testing the insights dashboard"

    def add_arguments(self, parser):
        parser.add_argument(
            "--team-slug",
            type=str,
            help="Generate insights for a specific team by slug",
        )
        parser.add_argument(
            "--date",
            type=str,
            help="Generate insights for a specific date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing insights before generating",
        )
        parser.add_argument(
            "--sample",
            action="store_true",
            help="Generate sample insights for UI testing (doesn't run rules)",
        )

    def handle(self, *args, **options):
        team_slug = options.get("team_slug")
        date_str = options.get("date")
        clear = options.get("clear")
        sample = options.get("sample")

        # Determine target date
        target_date = date.fromisoformat(date_str) if date_str else date.today()

        # Get teams
        if team_slug:
            teams = Team.objects.filter(slug=team_slug)
            if not teams.exists():
                self.stderr.write(self.style.ERROR(f"Team '{team_slug}' not found"))
                return
        else:
            teams = Team.objects.all()

        if not teams.exists():
            self.stderr.write(self.style.ERROR("No teams found. Run seed_demo_data first."))
            return

        # Clear existing insights if requested
        if clear:
            count = DailyInsight.objects.filter(team__in=teams).count()
            DailyInsight.objects.filter(team__in=teams).delete()
            self.stdout.write(self.style.WARNING(f"Cleared {count} existing insights"))

        # Generate insights
        if sample:
            self._generate_sample_insights(teams, target_date)
        else:
            self._generate_real_insights(teams, target_date)

    def _generate_real_insights(self, teams, target_date):
        """Run insight rules against real data."""
        total_insights = 0

        for team in teams:
            self.stdout.write(f"Processing team: {team.name}")
            try:
                insights = compute_insights(team, target_date)
                total_insights += len(insights)
                self.stdout.write(self.style.SUCCESS(f"  Generated {len(insights)} insights for {team.name}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Error processing {team.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nTotal: {total_insights} insights generated"))

    def _generate_sample_insights(self, teams, target_date):
        """Generate sample insights for UI testing."""
        sample_insights = [
            {
                "category": "trend",
                "priority": "high",
                "title": "Cycle time increased 35% this week",
                "description": "Average PR cycle time jumped from 18 hours to 24 hours. "
                "This may indicate review bottlenecks or larger PRs being submitted.",
                "metric_type": "cycle_time",
                "metric_value": {"current": 24.3, "previous": 18.0, "change_percent": 35},
                "comparison_period": "week_over_week",
            },
            {
                "category": "trend",
                "priority": "medium",
                "title": "AI adoption up 12% this month",
                "description": "The percentage of PRs flagged as AI-assisted increased from 45% to 57%. "
                "Team is embracing AI coding tools more.",
                "metric_type": "ai_adoption",
                "metric_value": {"current": 57, "previous": 45, "change_percent": 12},
                "comparison_period": "month_over_month",
            },
            {
                "category": "anomaly",
                "priority": "high",
                "title": "Hotfix spike detected",
                "description": "5 hotfixes this week vs average of 1.2. Check if recent deployments "
                "introduced instability.",
                "metric_type": "hotfix_count",
                "metric_value": {"current": 5, "average": 1.2, "multiplier": 4.2},
                "comparison_period": "4_week_average",
            },
            {
                "category": "anomaly",
                "priority": "high",
                "title": "Revert commits detected",
                "description": "3 revert commits found this week. Review recent merges for quality issues.",
                "metric_type": "revert_count",
                "metric_value": {"count": 3},
                "comparison_period": "current_week",
            },
            {
                "category": "anomaly",
                "priority": "medium",
                "title": "CI failure rate above threshold",
                "description": "CI/CD pipeline failure rate is 28%, above the 20% threshold. "
                "Investigate flaky tests or infrastructure issues.",
                "metric_type": "ci_failure_rate",
                "metric_value": {"failure_rate": 28, "threshold": 20},
                "comparison_period": "last_7_days",
            },
            {
                "category": "action",
                "priority": "low",
                "title": "Consider removing redundant reviewers",
                "description": "Alice and Bob agree on 98% of reviews (52 PRs). "
                "Consider if both are needed on the same PRs.",
                "metric_type": "reviewer_correlation",
                "metric_value": {"reviewer1": "Alice", "reviewer2": "Bob", "agreement": 98, "pr_count": 52},
                "comparison_period": "last_90_days",
            },
            {
                "category": "action",
                "priority": "low",
                "title": "8 PRs missing Jira links",
                "description": "8 merged PRs in the last 30 days don't have Jira issue links. "
                "This affects traceability and sprint metrics.",
                "metric_type": "unlinked_prs",
                "metric_value": {"count": 8},
                "comparison_period": "last_30_days",
            },
        ]

        total_insights = 0

        for team in teams:
            self.stdout.write(f"Creating sample insights for: {team.name}")

            for i, insight_data in enumerate(sample_insights):
                # Vary dates slightly for realism
                insight_date = target_date - timedelta(days=i % 3)

                DailyInsight.objects.create(
                    team=team,
                    date=insight_date,
                    **insight_data,
                )
                total_insights += 1

            self.stdout.write(self.style.SUCCESS(f"  Created {len(sample_insights)} sample insights for {team.name}"))

        self.stdout.write(self.style.SUCCESS(f"\nTotal: {total_insights} sample insights created"))
        self.stdout.write("\nView them at: /app/metrics/")
