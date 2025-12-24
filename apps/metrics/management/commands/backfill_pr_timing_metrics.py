"""
Management command to backfill PR timing metrics.

Backfills cycle_time_hours, first_review_at, and review_time_hours for existing PRs
that are missing these metrics.

Usage:
    python manage.py backfill_pr_timing_metrics --team "Team Name"
    python manage.py backfill_pr_timing_metrics --team "Team Name" --dry-run
"""

from django.core.management.base import BaseCommand

from apps.metrics.models import PullRequest
from apps.metrics.processors import _calculate_cycle_time_hours, _calculate_time_diff_hours
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Backfill cycle_time_hours, first_review_at, and review_time_hours for existing PRs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--team",
            type=str,
            required=True,
            help="Team name to process",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving to database",
        )

    def handle(self, *args, **options):
        team_name = options["team"]
        dry_run = options["dry_run"]
        verbosity = options["verbosity"]

        try:
            team = Team.objects.get(name=team_name)
        except Team.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Team '{team_name}' not found"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))

        # Backfill cycle_time_hours for merged PRs
        prs_to_update_cycle_time = []
        merged_prs_without_cycle_time = PullRequest.objects.filter(
            team=team, state="merged", cycle_time_hours__isnull=True
        )

        for pr in merged_prs_without_cycle_time:
            cycle_time = _calculate_cycle_time_hours(pr.pr_created_at, pr.merged_at)
            if cycle_time is not None:
                pr.cycle_time_hours = cycle_time
                prs_to_update_cycle_time.append(pr)
                if verbosity >= 2:
                    self.stdout.write(f"  PR #{pr.pr_number}: cycle_time={cycle_time}h")

        if not dry_run and prs_to_update_cycle_time:
            PullRequest.objects.bulk_update(  # noqa: TEAM001 - PRs from team-filtered query
                prs_to_update_cycle_time, ["cycle_time_hours"]
            )

        # Backfill first_review_at and review_time_hours for PRs with reviews
        prs_to_update_review_time = []
        prs_without_review_time = PullRequest.objects.filter(team=team, first_review_at__isnull=True).prefetch_related(
            "reviews"
        )

        for pr in prs_without_review_time:
            # Use prefetched reviews to avoid N+1 query
            reviews = list(pr.reviews.all())
            if not reviews:
                continue

            # Find earliest review from prefetched data
            earliest_review = min(
                (r for r in reviews if r.submitted_at),
                key=lambda r: r.submitted_at,
                default=None,
            )

            if earliest_review and earliest_review.submitted_at:
                pr.first_review_at = earliest_review.submitted_at
                # Only calculate review_time_hours if pr_created_at exists
                if pr.pr_created_at:
                    pr.review_time_hours = _calculate_time_diff_hours(pr.pr_created_at, earliest_review.submitted_at)
                    prs_to_update_review_time.append(pr)
                    if verbosity >= 2:
                        self.stdout.write(
                            f"  PR #{pr.pr_number}: first_review_at={earliest_review.submitted_at}, "
                            f"review_time={pr.review_time_hours}h"
                        )
                elif verbosity >= 2:
                    self.stdout.write(self.style.WARNING(f"  PR #{pr.pr_number}: Skipping - missing pr_created_at"))

        if not dry_run and prs_to_update_review_time:
            PullRequest.objects.bulk_update(  # noqa: TEAM001 - PRs from team-filtered query
                prs_to_update_review_time, ["first_review_at", "review_time_hours"]
            )

        # Output results
        cycle_time_updated = len(prs_to_update_cycle_time)
        review_time_updated = len(prs_to_update_review_time)
        total_updated = cycle_time_updated + review_time_updated

        self.stdout.write(f"Updated {cycle_time_updated} PRs with cycle time")
        self.stdout.write(f"Updated {review_time_updated} PRs with review time")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDRY RUN: Would update {total_updated} PRs (no changes saved)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {total_updated} PRs"))
