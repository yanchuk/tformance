"""Run LLM analysis on PRs using Groq's Batch API for 50% cost savings.

Uses file upload batch processing instead of individual API calls.
Much faster for large batches (500+ PRs).

Usage:
    python manage.py run_llm_batch --limit 500
    python manage.py run_llm_batch --limit 500 --poll  # Submit and wait for results
    python manage.py run_llm_batch --limit 500 --with-fallback  # Two-pass with auto-retry
    python manage.py run_llm_batch --status batch_abc123  # Check status
    python manage.py run_llm_batch --results batch_abc123  # Download and save results

Workflow (standard):
    1. Submit: python manage.py run_llm_batch --limit 500
       -> Returns batch_id
    2. Poll: python manage.py run_llm_batch --status <batch_id>
       -> Check progress (usually 1-5 minutes)
    3. Save: python manage.py run_llm_batch --results <batch_id>
       -> Downloads results and saves to database

Workflow (two-pass with fallback):
    python manage.py run_llm_batch --limit 500 --with-fallback
    -> Pass 1: Cheap model (openai/gpt-oss-20b) for 80-95% success
    -> Pass 2: Retry failures with better model (llama-3.3-70b-versatile)
    -> Both passes use Batch API for 50% discount
    -> Results automatically saved to database
"""

import time

from django.core.management.base import BaseCommand

from apps.integrations.services.groq_batch import GroqBatchProcessor
from apps.metrics.models import PullRequest
from apps.metrics.services.llm_prompts import PROMPT_VERSION
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Run LLM analysis using Groq Batch API (faster, 50% cheaper)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum PRs to process (default: 100)",
        )
        parser.add_argument(
            "--team",
            type=str,
            help="Filter by team name",
        )
        parser.add_argument(
            "--poll",
            action="store_true",
            help="Submit and wait for results (polls every 30s)",
        )
        parser.add_argument(
            "--status",
            type=str,
            metavar="BATCH_ID",
            help="Check status of existing batch",
        )
        parser.add_argument(
            "--results",
            type=str,
            metavar="BATCH_ID",
            help="Download and save results from completed batch",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without submitting",
        )
        parser.add_argument(
            "--with-fallback",
            action="store_true",
            help="Use two-pass processing: cheap model first, retry failures with better model",
        )

    def handle(self, *args, **options):
        import os

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            self.stderr.write(self.style.ERROR("GROQ_API_KEY not set"))
            return

        processor = GroqBatchProcessor(api_key=api_key)

        # Handle status check
        if options.get("status"):
            self._check_status(processor, options["status"])
            return

        # Handle results download
        if options.get("results"):
            self._download_results(processor, options["results"])
            return

        # Submit new batch
        self._submit_batch(processor, options)

    def _submit_batch(self, processor: GroqBatchProcessor, options: dict):
        """Submit a new batch for processing."""
        limit = options["limit"]
        team_name = options.get("team")
        poll = options.get("poll", False)
        dry_run = options.get("dry_run", False)
        with_fallback = options.get("with_fallback", False)

        # Query PRs without LLM analysis
        qs = (
            PullRequest.objects.filter(body__isnull=False)  # noqa: TEAM001
            .exclude(body="")
            .filter(llm_summary__isnull=True)
        )

        if team_name:
            try:
                team = Team.objects.get(name=team_name)
                qs = qs.filter(team=team)
                self.stdout.write(f"Filtering to team: {team_name}")
            except Team.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Team not found: {team_name}"))
                return

        # Prefetch for context building
        prs = list(
            qs.select_related("author", "team")
            .prefetch_related("files", "commits", "reviews__reviewer", "comments__author")
            .order_by("-pr_created_at")[:limit]
        )

        self.stdout.write(f"Found {len(prs)} PRs to process")
        self.stdout.write(f"Prompt version: {PROMPT_VERSION}")

        if not prs:
            self.stdout.write(self.style.SUCCESS("No PRs need processing"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN ==="))
            for pr in prs[:10]:
                self.stdout.write(f"  - PR #{pr.github_pr_id}: {pr.title[:50]}...")
            if len(prs) > 10:
                self.stdout.write(f"  ... and {len(prs) - 10} more")
            return

        # Use fallback mode if requested
        if with_fallback:
            self._submit_batch_with_fallback(processor, prs)
            return

        # Submit batch (standard mode)
        self.stdout.write("\nSubmitting batch to Groq...")
        try:
            batch_id = processor.submit_batch(prs)
            self.stdout.write(self.style.SUCCESS(f"\nBatch submitted: {batch_id}"))
            self.stdout.write(f"Total requests: {len(prs)}")
            self.stdout.write("\nTo check status:")
            self.stdout.write(f"  python manage.py run_llm_batch --status {batch_id}")
            self.stdout.write("\nTo download results when complete:")
            self.stdout.write(f"  python manage.py run_llm_batch --results {batch_id}")

            if poll:
                self._poll_until_complete(processor, batch_id)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to submit batch: {e}"))

    def _submit_batch_with_fallback(self, processor: GroqBatchProcessor, prs: list):
        """Submit batch with two-pass processing: cheap model + retry with better model."""
        self.stdout.write("\n=== Two-Pass Batch Processing ===")
        self.stdout.write(f"Pass 1 model: {processor.DEFAULT_MODEL} (cheap)")
        self.stdout.write(f"Pass 2 model: {processor.FALLBACK_MODEL} (reliable)")
        self.stdout.write(f"Total PRs: {len(prs)}")

        def on_progress(status):
            self.stdout.write(
                f"  {status.completed_requests}/{status.total_requests} ({status.progress_pct:.1f}%) - {status.status}"
            )

        try:
            self.stdout.write("\n--- Pass 1: Submitting with cheap model ---")
            results, stats = processor.submit_batch_with_fallback(
                prs,
                poll_interval=30,
                on_progress=on_progress,
            )

            # Log results
            self.stdout.write(f"\n{'=' * 50}")
            self.stdout.write(f"Pass 1 batch ID: {stats['first_batch_id']}")
            self.stdout.write(f"Pass 1 failures: {stats['first_pass_failures']}")

            if stats["retry_batch_id"]:
                self.stdout.write(f"\n--- Pass 2: Retried {stats['first_pass_failures']} failures ---")
                self.stdout.write(f"Pass 2 batch ID: {stats['retry_batch_id']}")

            self.stdout.write(f"\nFinal failures: {stats['final_failures']}")

            # Save results to database
            self._save_results(results)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed: {e}"))

    def _save_results(self, results: list):
        """Save batch results to database."""
        success_count = 0
        error_count = 0

        for result in results:
            if result.error:
                self.stdout.write(self.style.WARNING(f"  PR {result.pr_id}: {result.error}"))
                error_count += 1
                continue

            try:
                pr = PullRequest.objects.get(id=result.pr_id)  # noqa: TEAM001
                pr.llm_summary = result.llm_summary
                pr.llm_summary_version = result.prompt_version
                pr.save(update_fields=["llm_summary", "llm_summary_version"])
                success_count += 1
            except PullRequest.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  PR {result.pr_id}: Not found"))
                error_count += 1

        self.stdout.write(f"\n{'=' * 50}")
        self.stdout.write(self.style.SUCCESS(f"Saved: {success_count}"))
        if error_count:
            self.stdout.write(self.style.WARNING(f"Errors: {error_count}"))

    def _check_status(self, processor: GroqBatchProcessor, batch_id: str):
        """Check status of an existing batch."""
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
                    self.stdout.write(self.style.SUCCESS("\nBatch complete! Run with --results to save:"))
                    self.stdout.write(f"  python manage.py run_llm_batch --results {batch_id}")
                else:
                    self.stdout.write(self.style.ERROR(f"\nBatch ended with status: {status.status}"))
            else:
                self.stdout.write("\nStill processing... check again in 30s")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to get status: {e}"))

    def _poll_until_complete(self, processor: GroqBatchProcessor, batch_id: str):
        """Poll for completion and download results."""
        self.stdout.write("\nPolling for completion (Ctrl+C to stop)...")

        while True:
            try:
                status = processor.get_status(batch_id)
                self.stdout.write(
                    f"  {status.completed_requests}/{status.total_requests} "
                    f"({status.progress_pct:.1f}%) - {status.status}"
                )

                if status.is_complete:
                    if status.status == "completed":
                        self.stdout.write(self.style.SUCCESS("\nBatch complete!"))
                        self._download_results(processor, batch_id)
                    else:
                        self.stderr.write(self.style.ERROR(f"\nBatch failed: {status.status}"))
                    return

                time.sleep(30)

            except KeyboardInterrupt:
                self.stdout.write("\nStopped polling. Batch continues in background.")
                self.stdout.write(f"Check later: python manage.py run_llm_batch --status {batch_id}")
                return

    def _download_results(self, processor: GroqBatchProcessor, batch_id: str):
        """Download results and save to database."""
        try:
            self.stdout.write(f"\nDownloading results for batch {batch_id}...")
            results = processor.get_results(batch_id)

            success_count = 0
            error_count = 0

            for result in results:
                if result.error:
                    self.stdout.write(self.style.WARNING(f"  PR {result.pr_id}: {result.error}"))
                    error_count += 1
                    continue

                try:
                    pr = PullRequest.objects.get(id=result.pr_id)  # noqa: TEAM001
                    pr.llm_summary = result.llm_summary
                    pr.llm_summary_version = result.prompt_version
                    pr.save(update_fields=["llm_summary", "llm_summary_version"])
                    success_count += 1
                except PullRequest.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  PR {result.pr_id}: Not found"))
                    error_count += 1

            self.stdout.write(f"\n{'=' * 50}")
            self.stdout.write(self.style.SUCCESS(f"Saved: {success_count}"))
            if error_count:
                self.stdout.write(self.style.WARNING(f"Errors: {error_count}"))

        except ValueError as e:
            self.stderr.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to download results: {e}"))
