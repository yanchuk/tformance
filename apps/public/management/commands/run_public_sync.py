"""Sync public repos via SyncOrchestrator with progress output.

Designed for nohup on Unraid — shows per-repo progress and a summary.

Usage:
    python manage.py run_public_sync
    python manage.py run_public_sync --rebuild
    python manage.py run_public_sync --project vercel-demo
    python manage.py run_public_sync --verbose
"""

import contextlib
import logging
import os
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.metrics.seeding.github_token_pool import GitHubTokenPool
from apps.public.models import PublicRepoProfile
from apps.public.services.sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync all eligible public repos and optionally rebuild snapshots"

    def add_arguments(self, parser):
        parser.add_argument(
            "--rebuild",
            action="store_true",
            help="Rebuild snapshots after sync (runs rebuild_public_catalog_snapshots directly)",
        )
        parser.add_argument(
            "--project",
            type=str,
            help="Sync only repos for one team slug (e.g., --project vercel-demo)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show full logging and print output (noisy, useful for debugging)",
        )

    def handle(self, *args, **options):
        token_pool = GitHubTokenPool()
        orchestrator = SyncOrchestrator(token_pool)
        verbose = options["verbose"]

        repos = PublicRepoProfile.objects.sync_eligible()
        if options["project"]:
            repos = repos.filter(team__slug=options["project"])

        repo_list = list(repos)
        total = len(repo_list)

        self.stdout.write(f"Starting sync for {total} repos...")

        # Suppress log noise from apps.* loggers unless --verbose
        apps_logger = logging.getLogger("apps")
        original_level = apps_logger.level
        if not verbose:
            apps_logger.setLevel(logging.WARNING)

        totals = {"fetched": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0}

        with open(os.devnull, "w") as devnull:
            try:
                for i, repo_profile in enumerate(repo_list, start=1):
                    t0 = time.monotonic()
                    try:
                        if verbose:
                            result = orchestrator.sync_repo(repo_profile)
                        else:
                            with contextlib.redirect_stdout(devnull):
                                result = orchestrator.sync_repo(repo_profile)
                        elapsed = time.monotonic() - t0
                        self.stdout.write(
                            f"[{i}/{total}] {repo_profile.github_repo}... "
                            f"fetched={result.get('fetched', 0)}, "
                            f"created={result.get('created', 0)}, "
                            f"updated={result.get('updated', 0)} "
                            f"({elapsed:.0f}s)"
                        )
                        for key in totals:
                            totals[key] += result.get(key, 0)
                    except Exception:
                        elapsed = time.monotonic() - t0
                        totals["errors"] += 1
                        self.stderr.write(f"[{i}/{total}] {repo_profile.github_repo}... FAILED ({elapsed:.0f}s)")
                        logger.exception("Sync failed for %s", repo_profile.github_repo)
            finally:
                apps_logger.setLevel(original_level)

        self.stdout.write(
            f"\nDone: {total} repos, "
            f"fetched={totals['fetched']}, created={totals['created']}, "
            f"updated={totals['updated']}, skipped={totals['skipped']}, "
            f"errors={totals['errors']}"
        )

        if options["rebuild"]:
            self.stdout.write("\nRebuilding snapshots...")
            call_command("rebuild_public_catalog_snapshots", verbosity=options["verbosity"])
            self.stdout.write("Snapshots rebuilt.")
