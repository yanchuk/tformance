"""Management command to backfill AI detection using Groq Batch API.

Uses Groq's batch API for 50% cost savings on bulk PR analysis.
"""

from django.core.management.base import BaseCommand

from apps.integrations.services.groq_batch import GroqBatchProcessor
from apps.metrics.models import PullRequest
from apps.teams.models import Team


class Command(BaseCommand):
    """Backfill AI detection using Groq Batch API (50% cheaper)."""

    help = "Backfill AI detection for existing PRs using Groq Batch API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--team",
            type=str,
            help="Team name to filter PRs",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=1000,
            help="Maximum PRs to process (default: 1000, max: 50000)",
        )
        parser.add_argument(
            "--only-undetected",
            action="store_true",
            help="Only process PRs not currently marked as AI-assisted",
        )
        parser.add_argument(
            "--submit",
            action="store_true",
            help="Submit batch job (without this, shows preview only)",
        )
        parser.add_argument(
            "--status",
            type=str,
            help="Check status of a batch job by ID",
        )
        parser.add_argument(
            "--apply",
            type=str,
            help="Apply results from a completed batch job by ID",
        )
        parser.add_argument(
            "--completion-window",
            type=str,
            default="24h",
            help="Processing window: 24h to 7d (default: 24h)",
        )

    def handle(self, *args, **options):
        # Check status mode
        if options.get("status"):
            self._check_status(options["status"])
            return

        # Apply results mode
        if options.get("apply"):
            self._apply_results(options["apply"])
            return

        # Submit mode
        self._submit_batch(options)

    def _submit_batch(self, options):
        """Submit PRs for batch processing."""
        team_name = options.get("team")
        limit = min(options["limit"], 50000)  # Groq max
        only_undetected = options["only_undetected"]
        submit = options["submit"]
        completion_window = options["completion_window"]

        # Get team if specified
        team = None
        if team_name:
            try:
                team = Team.objects.get(name=team_name)
                self.stdout.write(f"Filtering by team: {team.name}")
            except Team.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Team '{team_name}' not found"))
                return

        # Build queryset
        qs = PullRequest.objects.filter(  # noqa: TEAM001 - Admin command with team filter
            body__isnull=False,
        ).exclude(body="")

        if team:
            qs = qs.filter(team=team)

        if only_undetected:
            qs = qs.filter(is_ai_assisted=False)

        prs = list(qs[:limit])

        if not prs:
            self.stdout.write("No PRs to process")
            return

        self.stdout.write(f"\nFound {len(prs)} PRs to process")

        if not submit:
            self.stdout.write(self.style.WARNING("\nPREVIEW MODE"))
            self.stdout.write("Sample PRs that would be processed:")
            for pr in prs[:5]:
                body_preview = (pr.body or "")[:80].replace("\n", " ")
                self.stdout.write(f"  PR #{pr.github_pr_id}: {body_preview}...")
            if len(prs) > 5:
                self.stdout.write(f"  ... and {len(prs) - 5} more")

            # Cost estimate
            estimated_cost = len(prs) * 0.00008  # $0.08/1000 PRs
            self.stdout.write(f"\nEstimated cost: ${estimated_cost:.4f}")
            self.stdout.write(f"Completion window: {completion_window}")
            self.stdout.write("\nRun with --submit to create batch job")
            return

        # Submit batch
        self.stdout.write(f"\nSubmitting batch of {len(prs)} PRs...")
        processor = GroqBatchProcessor()

        try:
            batch_id = processor.submit_batch(prs, completion_window=completion_window)
            self.stdout.write(self.style.SUCCESS(f"\nBatch submitted: {batch_id}"))
            self.stdout.write("\nCheck status with:")
            self.stdout.write(f"  python manage.py backfill_ai_detection_batch --status {batch_id}")
            self.stdout.write("\nApply results when complete with:")
            self.stdout.write(f"  python manage.py backfill_ai_detection_batch --apply {batch_id}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to submit batch: {e}"))

    def _check_status(self, batch_id: str):
        """Check status of a batch job."""
        processor = GroqBatchProcessor()

        try:
            status = processor.get_status(batch_id)
            self.stdout.write(f"\nBatch: {status.batch_id}")
            self.stdout.write(f"Status: {status.status}")
            self.stdout.write(
                f"Progress: {status.completed_requests}/{status.total_requests} ({status.progress_pct:.1f}%)"
            )
            self.stdout.write(f"Failed: {status.failed_requests}")

            if status.is_complete:
                if status.status == "completed":
                    self.stdout.write(self.style.SUCCESS("\nBatch complete! Apply results with:"))
                    self.stdout.write(f"  python manage.py backfill_ai_detection_batch --apply {batch_id}")
                else:
                    self.stdout.write(self.style.ERROR(f"\nBatch ended with status: {status.status}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to get status: {e}"))

    def _apply_results(self, batch_id: str):
        """Apply results from a completed batch."""
        processor = GroqBatchProcessor()

        try:
            # Check status first
            status = processor.get_status(batch_id)
            if not status.is_complete:
                self.stderr.write(self.style.ERROR(f"Batch is not complete (status: {status.status})"))
                return

            if status.status != "completed":
                self.stderr.write(self.style.ERROR(f"Batch failed with status: {status.status}"))
                return

            # Get results
            self.stdout.write(f"\nDownloading results for batch {batch_id}...")
            results = processor.get_results(batch_id)
            self.stdout.write(f"Got {len(results)} results")

            # Apply to database
            updated = 0
            errors = 0
            new_detections = 0

            for result in results:
                if result.error:
                    errors += 1
                    continue

                try:
                    pr = PullRequest.objects.get(id=result.pr_id)  # noqa: TEAM001
                    old_ai = pr.is_ai_assisted

                    pr.is_ai_assisted = result.is_ai_assisted
                    pr.ai_tools_detected = result.tools
                    pr.save(update_fields=["is_ai_assisted", "ai_tools_detected"])

                    updated += 1
                    if result.is_ai_assisted and not old_ai:
                        new_detections += 1
                except PullRequest.DoesNotExist:
                    errors += 1

            # Summary
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("RESULTS APPLIED"))
            self.stdout.write("=" * 50)
            self.stdout.write(f"PRs updated: {updated}")
            self.stdout.write(f"New AI detections: {new_detections}")
            self.stdout.write(f"Errors: {errors}")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to apply results: {e}"))
