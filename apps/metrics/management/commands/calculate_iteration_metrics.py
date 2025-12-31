"""
Management command to calculate iteration metrics for merged PRs.

Computes review_rounds, commits_after_first_review, total_comments,
and avg_fix_response_hours from existing review and commit data.

Usage:
    python manage.py calculate_iteration_metrics --team Gumroad
    python manage.py calculate_iteration_metrics --team Gumroad --dry-run
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.metrics.models import Commit, PRReview, PullRequest
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Calculate iteration metrics for merged PRs from review/commit data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--team",
            type=str,
            default="Gumroad",
            help="Team name to process (default: Gumroad)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recalculate even if already populated",
        )

    def handle(self, *args, **options):
        team_name = options["team"]
        dry_run = options["dry_run"]
        force = options["force"]

        try:
            team = Team.objects.get(name=team_name)
        except Team.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Team '{team_name}' not found"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be saved"))

        # Query merged PRs
        prs = PullRequest.objects.filter(team=team, state="merged")
        if not force:
            # Only process PRs without iteration metrics
            prs = prs.filter(review_rounds__isnull=True)

        total = prs.count()
        self.stdout.write(f"Processing {total} merged PRs for team '{team_name}'...")

        updated = 0
        with_reviews = 0
        with_commits_after = 0

        for pr in prs:
            reviews = PRReview.objects.filter(  # noqa: TEAM001 - PR is team-scoped
                pull_request=pr
            ).order_by("submitted_at")

            if not reviews.exists():
                # No reviews - set defaults
                pr.review_rounds = 0
                pr.commits_after_first_review = 0
                pr.total_comments = 0
                pr.avg_fix_response_hours = None
                if not dry_run:
                    pr.save(
                        update_fields=[
                            "review_rounds",
                            "commits_after_first_review",
                            "total_comments",
                            "avg_fix_response_hours",
                        ]
                    )
                updated += 1
                continue

            with_reviews += 1

            # Review rounds = number of distinct reviewers
            pr.review_rounds = reviews.values("reviewer").distinct().count()

            # Total comments = PRReview records with non-empty body
            # Note: PRComment records are synced separately during GitHub sync
            pr.total_comments = reviews.exclude(body="").exclude(body__isnull=True).count()

            # Commits after first review
            first_review = reviews.first()
            if first_review and first_review.submitted_at:
                commits_after = Commit.objects.filter(  # noqa: TEAM001 - PR is team-scoped
                    pull_request=pr, committed_at__gt=first_review.submitted_at
                ).count()
                pr.commits_after_first_review = commits_after
                if commits_after > 0:
                    with_commits_after += 1

                # Calculate avg fix response time
                # Time between each review and the next commit
                fix_times = []
                for review in reviews:
                    if review.submitted_at:
                        next_commit = (
                            Commit.objects.filter(  # noqa: TEAM001 - PR is team-scoped
                                pull_request=pr, committed_at__gt=review.submitted_at
                            )
                            .order_by("committed_at")
                            .first()
                        )
                        if next_commit and next_commit.committed_at:
                            time_diff = next_commit.committed_at - review.submitted_at
                            hours = time_diff.total_seconds() / 3600
                            if hours > 0:  # Only positive times
                                fix_times.append(hours)

                if fix_times:
                    avg_hours = sum(fix_times) / len(fix_times)
                    pr.avg_fix_response_hours = Decimal(str(round(avg_hours, 2)))
            else:
                pr.commits_after_first_review = 0

            if not dry_run:
                pr.save(
                    update_fields=[
                        "review_rounds",
                        "commits_after_first_review",
                        "total_comments",
                        "avg_fix_response_hours",
                    ]
                )
            updated += 1

        # Summary
        self.stdout.write(f"\nProcessed {total} merged PRs")
        self.stdout.write(f"PRs with reviews: {with_reviews}")
        self.stdout.write(f"PRs with commits after review: {with_commits_after}")
        self.stdout.write(f"Updated: {updated}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete - no changes saved"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {updated} PRs"))
