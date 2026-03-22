"""Reconcile local public repo data from DB + .seeding_cache.

Analyzes DB-vs-cache coverage, imports missing data, rebuilds public
snapshots, and renders org/repo pages on localhost:8000.

Usage:
    # Dry-run analysis (no writes)
    python manage.py reconcile_public_repo_local_data --org polar --org posthog --dry-run

    # Full reconciliation with snapshot rebuild
    python manage.py reconcile_public_repo_local_data --org polar --org posthog --rebuild-snapshots

    # Scoped LLM enrichment (flagship repos only)
    python manage.py reconcile_public_repo_local_data --org polar --with-llm --max-llm-prs-per-repo 25
"""

import logging

from django.core.management.base import BaseCommand

from apps.public.services.local_fixture_manifest import (
    filter_repos_by_github_repo,
    get_repos_for_orgs,
)
from apps.public.services.local_reconciliation import LocalReconciliationService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconcile local public repo data from DB + .seeding_cache"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            action="append",
            dest="orgs",
            default=[],
            help="Public org slug to reconcile (repeatable)",
        )
        parser.add_argument(
            "--repo",
            action="append",
            dest="repos",
            default=[],
            help="Specific github_repo to reconcile, e.g. PostHog/posthog (repeatable)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analyze only — no DB writes",
        )
        parser.add_argument(
            "--rebuild-snapshots",
            action="store_true",
            help="Rebuild PublicRepoStats/PublicOrgStats after reconciliation",
        )
        parser.add_argument(
            "--with-llm",
            action="store_true",
            help="Enable scoped Groq LLM enrichment (flagship repos only)",
        )
        parser.add_argument(
            "--max-llm-prs-per-repo",
            type=int,
            default=50,
            help="Max PRs per repo to submit for LLM enrichment (default: 50)",
        )
        parser.add_argument(
            "--allow-backup-fallback",
            action="store_true",
            help="Allow backup-based recovery if cache is insufficient",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        org_slugs = options["orgs"]
        repo_filters = options["repos"]

        if not org_slugs:
            raise SystemExit("At least one --org is required.")

        service = LocalReconciliationService(dry_run=dry_run)

        # Phase 0: Prerequisites
        service.validate_prerequisites()

        # Phase 1: Resolve repos from manifest
        repos = get_repos_for_orgs(org_slugs)
        if repo_filters:
            repos = filter_repos_by_github_repo(repos, repo_filters)
            if not repos:
                raise SystemExit(f"No repos matched filters: {repo_filters}. Check --repo values against manifest.")

        # Phase 2: Validate org profiles and cache files
        org_profiles = service.validate_org_profiles(org_slugs)
        if not options["allow_backup_fallback"]:
            service.validate_cache_files(repos)
        else:
            # Warn about missing cache files but don't abort — DB-first mode
            service.warn_missing_cache_files(repos, self.stderr)

        mode = "DRY RUN" if dry_run else "APPLY"
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(f"  Local Public Repo Reconciliation — {mode}")
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"  Orgs: {', '.join(org_slugs)}")
        self.stdout.write(f"  Repos: {len(repos)}")
        self.stdout.write(f"{'=' * 60}\n")

        # Phase 2b: Bootstrap repo profiles (idempotent)
        if not dry_run:
            service.bootstrap_repo_profiles(repos, org_profiles)

        # Phase 3: Analyze each repo
        for repo_info in repos:
            github_repo = repo_info["github_repo"]
            org_slug = repo_info["org_slug"]
            team = org_profiles[org_slug].team

            self.stdout.write(f"Analyzing {github_repo}...")
            report = service.analyze_repo(team, github_repo)
            service.reports.append(report)

            self.stdout.write(
                f"  DB: {report.db_pr_count} PRs | "
                f"Cache: {report.cache_pr_count} PRs | "
                f"Missing: {report.missing_pr_count} | "
                f"Stale: {report.stale_pr_count} | "
                f"Partial: {report.partial_pr_count}"
            )
            if report.skipped_cache_errors:
                self.stdout.write(
                    f"  WARNING: {report.skipped_cache_errors} cache entries skipped (deserialization errors)"
                )

        # Phase 4: Apply (if not dry-run)
        if not dry_run:
            self.stdout.write("\nApplying reconciliation...")
            for report in service.reports:
                if report.missing_pr_count or report.stale_pr_count or report.partial_pr_count:
                    org_slug = next(r["org_slug"] for r in repos if r["github_repo"] == report.github_repo)
                    team = org_profiles[org_slug].team
                    result = service.apply_repo(team, report.github_repo, report)
                    self.stdout.write(f"  {report.github_repo}: {result}")

            # Phase 5: Rebuild snapshots
            if options["rebuild_snapshots"]:
                self.stdout.write("\nRebuilding snapshots...")
                service.rebuild_snapshots(repos, org_profiles)

            # Phase 6: LLM enrichment
            if options["with_llm"]:
                self.stdout.write("\nRunning scoped LLM enrichment...")
                service.run_llm_enrichment(repos, org_profiles, max_per_repo=options["max_llm_prs_per_repo"])
        else:
            # Dry-run summary
            total_missing = sum(r.missing_pr_count for r in service.reports)
            total_stale = sum(r.stale_pr_count for r in service.reports)
            total_partial = sum(r.partial_pr_count for r in service.reports)

            self.stdout.write("\n--- DRY RUN Summary ---")
            self.stdout.write(f"  Total missing PRs: {total_missing}")
            self.stdout.write(f"  Total stale PRs: {total_stale}")
            self.stdout.write(f"  Total partial PRs: {total_partial}")
            if options["with_llm"]:
                # Use accurate scoped candidate count (90-day window + cap)
                max_per_repo = options["max_llm_prs_per_repo"]
                total_llm = 0
                for repo_info in repos:
                    if repo_info.get("is_flagship"):
                        org_slug = repo_info["org_slug"]
                        team = org_profiles[org_slug].team
                        candidates = service._get_llm_candidates(repo_info["github_repo"], team, max_per_repo)
                        total_llm += len(candidates)
                        self.stdout.write(
                            f"  Would submit {len(candidates)} PRs for "
                            f"{repo_info['github_repo']} to Groq (cap: {max_per_repo})"
                        )
                self.stdout.write(f"  Total Groq candidates: {total_llm}")
            self.stdout.write("  No changes written.\n")

        self.stdout.write("Done.")
