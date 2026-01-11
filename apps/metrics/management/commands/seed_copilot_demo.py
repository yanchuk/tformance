"""
Management command to seed Copilot demo data using CopilotMockDataGenerator.

Creates AIUsageDaily records for team members based on mock Copilot metrics.

Usage:
    # Basic usage (4 weeks of mixed_usage scenario)
    python manage.py seed_copilot_demo --team=demo-team

    # Growth scenario (8 weeks)
    python manage.py seed_copilot_demo --team=demo-team --scenario=growth --weeks=8

    # Replace existing Copilot data
    python manage.py seed_copilot_demo --team=demo-team --scenario=high_adoption --clear-existing

    # Reproducible seeding
    python manage.py seed_copilot_demo --team=demo-team --seed=123

    # Correlate PRs with Copilot usage after seeding
    python manage.py seed_copilot_demo --team=demo-team --correlate-prs
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.integrations.services.copilot_metrics import (
    parse_metrics_response,
    sync_copilot_editor_data,
    sync_copilot_language_data,
)
from apps.integrations.services.copilot_mock_data import CopilotMockDataGenerator, CopilotScenario
from apps.integrations.services.copilot_pr_correlation import correlate_prs_with_copilot_usage
from apps.metrics.models import AIUsageDaily, CopilotEditorDaily, CopilotLanguageDaily, CopilotSeatSnapshot, TeamMember
from apps.metrics.seeding.deterministic import DeterministicRandom
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Seed Copilot demo data for a team using mock data generator"

    def add_arguments(self, parser):
        parser.add_argument(
            "--team",
            type=str,
            required=True,
            help="Team slug to seed data for (required)",
        )
        parser.add_argument(
            "--scenario",
            type=str,
            default="mixed_usage",
            choices=[s.value for s in CopilotScenario],
            help="Copilot usage scenario (default: mixed_usage)",
        )
        parser.add_argument(
            "--weeks",
            type=int,
            default=4,
            help="Number of weeks of data to generate (default: 4)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducible generation (default: 42)",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            dest="clear_existing",
            help="Delete existing Copilot AIUsageDaily records before seeding",
        )
        parser.add_argument(
            "--correlate-prs",
            action="store_true",
            dest="correlate_prs",
            help="After seeding, correlate existing PRs with Copilot usage",
        )
        parser.add_argument(
            "--no-seats",
            action="store_true",
            dest="no_seats",
            help="Skip seeding seat utilization data (CopilotSeatSnapshot)",
        )

    def handle(self, *args, **options):
        team_slug = options["team"]
        scenario = options["scenario"]
        weeks = options["weeks"]
        seed = options["seed"]
        clear_existing = options["clear_existing"]
        correlate_prs = options["correlate_prs"]

        # Validate team exists
        try:
            team = Team.objects.get(slug=team_slug)
        except Team.DoesNotExist as err:
            raise CommandError(f"Team '{team_slug}' not found. Please create the team first.") from err

        # Get team members
        members = list(TeamMember.objects.filter(team=team))
        if not members:
            raise CommandError(f"Team '{team_slug}' has no members. Please add team members first.")

        # Clear existing Copilot data if requested
        if clear_existing:
            deleted_usage, _ = AIUsageDaily.objects.filter(team=team, source="copilot").delete()
            deleted_seats, _ = CopilotSeatSnapshot.objects.filter(team=team).delete()
            deleted_lang, _ = CopilotLanguageDaily.objects.filter(team=team).delete()
            deleted_editor, _ = CopilotEditorDaily.objects.filter(team=team).delete()
            self.stdout.write(
                f"Deleted {deleted_usage} usage records, {deleted_seats} seat snapshots, "
                f"{deleted_lang} language records, {deleted_editor} editor records"
            )

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=weeks * 7 - 1)

        # Generate mock data
        generator = CopilotMockDataGenerator(seed=seed)
        daily_metrics = generator.generate(
            since=start_date.isoformat(),
            until=end_date.isoformat(),
            scenario=scenario,
        )

        # Sync language and editor data to CopilotLanguageDaily/CopilotEditorDaily
        # This populates the "By Language" and "By Editor" cards on the AI Adoption dashboard
        parsed_metrics = parse_metrics_response(daily_metrics)
        lang_records = sync_copilot_language_data(team, parsed_metrics)
        editor_records = sync_copilot_editor_data(team, parsed_metrics)
        self.stdout.write(f"Synced {lang_records} language records, {editor_records} editor records")

        # Create AIUsageDaily records for each member for each day
        records_created = 0

        # The mock generator produces totals for ~20-30 users. Scale based on actual team size.
        # This ensures large teams get proportionally more completions.
        expected_generator_users = 25  # Approximate midpoint of generator's active_users_range
        scale_factor = max(1, len(members) / expected_generator_users)

        for day_data in daily_metrics:
            day_date = date.fromisoformat(day_data["date"])
            completions_data = day_data["copilot_ide_code_completions"]

            # Distribute daily totals across members (scaled for team size)
            raw_completions = completions_data["total_completions"]
            raw_acceptances = completions_data["total_acceptances"]
            total_completions = int(raw_completions * scale_factor)
            total_acceptances = int(raw_acceptances * scale_factor)

            # Calculate per-member allocation (deterministic distribution)
            member_seed = seed + day_date.toordinal()
            rng = DeterministicRandom(member_seed)

            for member in members:
                # Generate member-specific variation
                member_factor = rng.uniform(0.5, 1.5)
                base_completions = total_completions // len(members)
                member_completions = int(base_completions * member_factor)

                # Calculate acceptance rate based on scenario
                if member_completions > 0:
                    base_rate = total_acceptances / total_completions if total_completions > 0 else 0.3
                    member_rate = base_rate * rng.uniform(0.85, 1.15)
                    member_rate = max(0.0, min(1.0, member_rate))
                    member_acceptances = int(member_completions * member_rate)
                    acceptance_rate_pct = Decimal(str(round(member_rate * 100, 2)))
                else:
                    member_acceptances = 0
                    acceptance_rate_pct = Decimal("0.00")

                # Create or update record
                AIUsageDaily.objects.update_or_create(
                    team=team,
                    member=member,
                    date=day_date,
                    source="copilot",
                    defaults={
                        "suggestions_shown": member_completions,
                        "suggestions_accepted": member_acceptances,
                        "acceptance_rate": acceptance_rate_pct,
                        "active_hours": Decimal(str(round(rng.uniform(1, 8), 2))) if member_completions > 0 else None,
                    },
                )
                records_created += 1

        # Output summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {records_created} Copilot AIUsageDaily records "
                f"for team '{team_slug}' ({len(members)} members, {weeks} weeks, scenario: {scenario})"
            )
        )

        # Seed seat utilization data (unless disabled)
        if not options.get("no_seats"):
            seat_records = self._seed_seat_snapshots(team, members, start_date, end_date, scenario, seed)
            self.stdout.write(self.style.SUCCESS(f"Created {seat_records} CopilotSeatSnapshot records"))

        # Correlate PRs with Copilot usage if requested
        if correlate_prs:
            prs_updated = correlate_prs_with_copilot_usage(team=team)
            self.stdout.write(self.style.SUCCESS(f"Correlated {prs_updated} PRs with Copilot usage"))

    def _seed_seat_snapshots(self, team, members, start_date, end_date, scenario, seed):
        """Create CopilotSeatSnapshot records matching the scenario.

        Args:
            team: Team instance
            members: List of TeamMember instances
            start_date: Start date for seeding
            end_date: End date for seeding
            scenario: Copilot scenario name (affects utilization rates)
            seed: Random seed for reproducibility

        Returns:
            Number of records created
        """
        total_seats = len(members) + 2  # Slightly more seats than members
        rng = DeterministicRandom(seed + 1000)  # Different seed offset from usage data
        records_created = 0

        current_date = start_date
        while current_date <= end_date:
            # Calculate active rate based on scenario
            if scenario == "high_adoption":
                active_rate = rng.uniform(0.85, 0.95)
            elif scenario == "low_adoption":
                active_rate = rng.uniform(0.40, 0.60)
            elif scenario == "inactive_licenses":
                active_rate = rng.uniform(0.30, 0.50)
            elif scenario == "growth":
                # Grows from 50% to 90% over time
                days_elapsed = (current_date - start_date).days
                total_days = (end_date - start_date).days or 1
                progress = days_elapsed / total_days
                active_rate = 0.50 + (0.40 * progress)
            elif scenario == "decline":
                # Declines from 90% to 50%
                days_elapsed = (current_date - start_date).days
                total_days = (end_date - start_date).days or 1
                progress = days_elapsed / total_days
                active_rate = 0.90 - (0.40 * progress)
            else:  # mixed_usage
                active_rate = rng.uniform(0.50, 0.80)

            active = int(total_seats * active_rate)
            inactive = total_seats - active

            CopilotSeatSnapshot.objects.update_or_create(
                team=team,
                date=current_date,
                defaults={
                    "total_seats": total_seats,
                    "active_this_cycle": active,
                    "inactive_this_cycle": inactive,
                    "pending_cancellation": rng.choice([0, 0, 0, 1]) if inactive > 0 else 0,
                },
            )
            records_created += 1
            current_date += timedelta(days=1)

        return records_created
