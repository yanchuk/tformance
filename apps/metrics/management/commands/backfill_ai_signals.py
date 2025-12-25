"""Management command to backfill AI signal aggregation fields for existing PRs.

Aggregates signals from commits, reviews, and files to the PR level:
- has_ai_commits: True if any commit has AI co-authors or is_ai_assisted
- has_ai_review: True if any review is from an AI reviewer
- has_ai_files: True if PR modifies AI config files (.cursorrules, CLAUDE.md, etc.)
- ai_confidence_score: Weighted composite score (0.0 - 1.0)
- ai_signals: JSON breakdown of each detection signal
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.metrics.models import PullRequest
from apps.metrics.services.ai_signals import (
    aggregate_all_ai_signals,
    calculate_ai_confidence,
)
from apps.teams.models import Team


class Command(BaseCommand):
    """Backfill AI signal aggregation for existing PRs."""

    help = "Backfill AI signal aggregation and confidence scoring fields"

    def add_arguments(self, parser):
        parser.add_argument(
            "--team",
            type=str,
            help="Team name to filter PRs",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving to database",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum PRs to process (default: all)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of PRs to update per batch (default: 500)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output for each PR",
        )
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Only process PRs that don't have any signal flags set",
        )
        parser.add_argument(
            "--skip-scoring",
            action="store_true",
            help="Skip confidence score calculation (just update signal flags)",
        )

    def handle(self, *args, **options):
        """Execute the backfill command."""
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        batch_size = options["batch_size"]
        limit = options["limit"]
        only_missing = options["only_missing"]
        skip_scoring = options["skip_scoring"]

        # Build queryset - management command intentionally accesses all PRs
        queryset = PullRequest.objects.all()  # noqa: TEAM001

        if options["team"]:
            try:
                team = Team.objects.get(name=options["team"])
                queryset = queryset.filter(team=team)
                self.stdout.write(f"Filtering to team: {team.name}")
            except Team.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Team not found: {options['team']}"))
                return

        if only_missing:
            queryset = queryset.filter(
                has_ai_commits=False,
                has_ai_review=False,
                has_ai_files=False,
            )
            self.stdout.write("Filtering to PRs without signal flags")

        # Prefetch related data for efficiency
        queryset = queryset.prefetch_related("commits", "reviews", "files")

        total_count = queryset.count()
        if limit:
            queryset = queryset[:limit]
            self.stdout.write(f"Limiting to {limit} PRs")

        self.stdout.write(f"Processing {min(limit or total_count, total_count)} PRs...")
        if skip_scoring:
            self.stdout.write("Skipping confidence score calculation")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be saved"))

        # Statistics
        stats = {
            "processed": 0,
            "has_ai_commits": 0,
            "has_ai_review": 0,
            "has_ai_files": 0,
            "any_signal": 0,
            "high_confidence": 0,  # Score >= 0.5
            "medium_confidence": 0,  # Score >= 0.2 and < 0.5
            "low_confidence": 0,  # Score > 0 and < 0.2
        }

        # Process in batches
        prs_to_update = []
        for pr in queryset.iterator(chunk_size=batch_size):
            signals = aggregate_all_ai_signals(pr)

            # Track statistics
            if signals["has_ai_commits"]:
                stats["has_ai_commits"] += 1
            if signals["has_ai_review"]:
                stats["has_ai_review"] += 1
            if signals["has_ai_files"]:
                stats["has_ai_files"] += 1
            if any([signals["has_ai_commits"], signals["has_ai_review"], signals["has_ai_files"]]):
                stats["any_signal"] += 1

            # Update PR fields
            pr.has_ai_commits = signals["has_ai_commits"]
            pr.has_ai_review = signals["has_ai_review"]
            pr.has_ai_files = signals["has_ai_files"]

            # Calculate and store confidence score
            if not skip_scoring:
                score, signal_breakdown = calculate_ai_confidence(pr)
                pr.ai_confidence_score = Decimal(str(round(score, 3)))
                pr.ai_signals = signal_breakdown

                # Track confidence distribution
                if score >= 0.5:
                    stats["high_confidence"] += 1
                elif score >= 0.2:
                    stats["medium_confidence"] += 1
                elif score > 0:
                    stats["low_confidence"] += 1

            prs_to_update.append(pr)
            stats["processed"] += 1

            if verbose:
                has_any = any([signals["has_ai_commits"], signals["has_ai_review"], signals["has_ai_files"]])
                if has_any or (not skip_scoring and score > 0):
                    score_str = f" score={score:.3f}" if not skip_scoring else ""
                    self.stdout.write(
                        f"  {pr.github_repo}#{pr.github_pr_id}: "
                        f"commits={signals['has_ai_commits']} "
                        f"review={signals['has_ai_review']} "
                        f"files={signals['has_ai_files']}{score_str}"
                    )
                    if signals["has_ai_files"]:
                        self.stdout.write(f"    Tools: {signals['file_details']['tools']}")

            # Batch update
            if len(prs_to_update) >= batch_size:
                if not dry_run:
                    self._bulk_update(prs_to_update, include_scoring=not skip_scoring)
                self.stdout.write(f"  Processed {stats['processed']} PRs...")
                prs_to_update = []

        # Final batch
        if prs_to_update and not dry_run:
            self._bulk_update(prs_to_update, include_scoring=not skip_scoring)

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Backfill Complete ==="))
        self.stdout.write(f"Total PRs processed: {stats['processed']}")
        self.stdout.write(f"PRs with AI commits: {stats['has_ai_commits']}")
        self.stdout.write(f"PRs with AI reviews: {stats['has_ai_review']}")
        self.stdout.write(f"PRs with AI files: {stats['has_ai_files']}")
        self.stdout.write(f"PRs with any new signal: {stats['any_signal']}")

        if not skip_scoring:
            self.stdout.write("")
            self.stdout.write("Confidence Distribution:")
            self.stdout.write(f"  High (≥0.5): {stats['high_confidence']}")
            self.stdout.write(f"  Medium (0.2-0.5): {stats['medium_confidence']}")
            self.stdout.write(f"  Low (<0.2): {stats['low_confidence']}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - no changes were saved"))

    def _bulk_update(self, prs, include_scoring=True):
        """Bulk update PRs with new signal values."""
        fields = ["has_ai_commits", "has_ai_review", "has_ai_files"]
        if include_scoring:
            fields.extend(["ai_confidence_score", "ai_signals"])

        with transaction.atomic():
            # Management command - bulk update on known PR instances
            PullRequest.objects.bulk_update(  # noqa: TEAM001
                prs,
                fields,
                batch_size=500,
            )
