"""Local reconciliation service for public repo data.

Analyzes DB-vs-cache coverage and imports missing/stale/partial PR data
from .seeding_cache without live GitHub API calls.
"""

import logging
from dataclasses import dataclass, field

from apps.integrations.services.groq_batch import GroqBatchProcessor
from apps.metrics.seeding.pr_cache import PRCache, deserialize_cache_prs
from apps.public.repo_snapshot_service import build_repo_snapshot

logger = logging.getLogger(__name__)


@dataclass
class RepoReconciliationReport:
    """Analysis report for a single repo's DB-vs-cache state."""

    github_repo: str
    db_pr_count: int = 0
    cache_pr_count: int = 0
    ready_pr_count: int = 0
    missing_pr_count: int = 0
    stale_pr_count: int = 0
    partial_pr_count: int = 0
    unusable_repo: bool = False
    llm_candidate_count: int = 0
    skipped_cache_errors: int = 0

    # Internal tracking for apply phase — only actionable subsets stored
    missing_pr_ids: list = field(default_factory=list)
    stale_pr_ids: list = field(default_factory=list)
    partial_pr_ids: list = field(default_factory=list)
    cache_prs_by_id: dict = field(default_factory=dict)
    db_prs_by_id: dict = field(default_factory=dict)


class LocalReconciliationService:
    """Orchestrates local DB reconciliation from cache data.

    Phases:
    1. Analyze: Compare DB state vs cache, produce reports
    2. Apply: Import missing PRs, update stale, repair partial
    3. Bootstrap: Create PublicRepoProfile/Stats/Insight rows
    """

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.reports: list[RepoReconciliationReport] = []
        self.modified_repos: set[str] = set()

    def validate_prerequisites(self):
        """Check migration state and cache availability.

        Raises:
            SystemExit with message if prerequisites not met.
        """
        from django.db.migrations.recorder import MigrationRecorder

        recorder = MigrationRecorder.Migration.objects.filter(app="public", name="0003_public_repo_pages")
        if not recorder.exists():
            raise SystemExit(
                "Migration 'public.0003_public_repo_pages' is not applied. "
                "Run: .venv/bin/python manage.py migrate public"
            )

    def validate_org_profiles(self, org_slugs):
        """Verify each org slug has a PublicOrgProfile.

        Returns:
            Dict mapping org_slug → PublicOrgProfile

        Raises:
            SystemExit if any slug is missing.
        """
        from apps.public.models import PublicOrgProfile

        profiles = {p.public_slug: p for p in PublicOrgProfile.objects.filter(public_slug__in=org_slugs)}
        missing = [slug for slug in org_slugs if slug not in profiles]

        if missing:
            raise SystemExit(
                f"PublicOrgProfile not found for: {', '.join(missing)}. Create them first via admin or data migration."
            )
        return profiles

    def validate_cache_files(self, repos):
        """Verify cache files exist for all repos.

        Args:
            repos: List of repo dicts with 'github_repo' key

        Raises:
            SystemExit if any cache file is missing.
        """
        missing = []
        for repo in repos:
            cache_path = PRCache.get_cache_path(repo["github_repo"])
            if not cache_path.exists():
                missing.append(f"  {repo['github_repo']}: {cache_path}")

        if missing:
            raise SystemExit("Cache files missing:\n" + "\n".join(missing))

    def warn_missing_cache_files(self, repos, stderr=None):
        """Log warnings for missing cache files without aborting.

        Used when --allow-backup-fallback is set (DB-first mode).
        """
        for repo in repos:
            cache_path = PRCache.get_cache_path(repo["github_repo"])
            if not cache_path.exists():
                msg = f"WARNING: Cache missing for {repo['github_repo']}: {cache_path} (DB-only mode)"
                logger.warning(msg)
                if stderr:
                    stderr.write(msg + "\n")

    def analyze_repo(self, team, github_repo):
        """Analyze a single repo's DB-vs-cache state.

        Pure read-only analysis. No writes to DB.

        Returns:
            RepoReconciliationReport
        """
        from django.db.models import Count

        from apps.metrics.models import PullRequest

        report = RepoReconciliationReport(github_repo=github_repo)

        # Load cache
        cache = PRCache.load(github_repo)
        if cache is None:
            report.unusable_repo = True
            report.db_pr_count = PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public
                team=team, github_repo=github_repo
            ).count()
            return report

        cache_prs, skipped = deserialize_cache_prs(cache.prs)
        report.skipped_cache_errors = skipped
        report.cache_pr_count = len(cache_prs)

        # Build cache lookup by github_pr_id (temporary, pruned after classification)
        cache_by_id = {pr.github_pr_id: pr for pr in cache_prs}

        # Load DB PRs with child counts in a single annotated query.
        # distinct=True is critical: without it, joining multiple reverse
        # relations multiplies rows and inflates counts.
        db_prs = PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public
            team=team, github_repo=github_repo
        ).annotate(
            review_count=Count("reviews", distinct=True),
            commit_count=Count("commits", distinct=True),
            file_count=Count("files", distinct=True),
            check_count=Count("check_runs", distinct=True),
        )

        db_pr_map = {}
        for pr in db_prs:
            db_pr_map[pr.github_pr_id] = pr

        report.db_pr_count = len(db_pr_map)

        # Classify each cache PR
        for cache_pr_id, cache_pr in cache_by_id.items():
            db_pr = db_pr_map.get(cache_pr_id)

            if db_pr is None:
                # Missing: in cache but not in DB
                report.missing_pr_count += 1
                report.missing_pr_ids.append(cache_pr_id)
                report.cache_prs_by_id[cache_pr_id] = cache_pr
                continue

            # Check staleness via material field comparison
            if self._is_stale(db_pr, cache_pr):
                report.stale_pr_count += 1
                report.stale_pr_ids.append(cache_pr_id)
                report.cache_prs_by_id[cache_pr_id] = cache_pr
                report.db_prs_by_id[cache_pr_id] = db_pr
                continue

            # Check for child record gaps
            if self._has_child_gaps(db_pr, cache_pr):
                report.partial_pr_count += 1
                report.partial_pr_ids.append(cache_pr_id)
                report.cache_prs_by_id[cache_pr_id] = cache_pr
                report.db_prs_by_id[cache_pr_id] = db_pr
                continue

            # PR is ready
            report.ready_pr_count += 1

        # Count LLM candidates (PRs missing llm_summary)
        report.llm_candidate_count = PullRequest.objects.filter(  # noqa: TEAM001
            team=team,
            github_repo=github_repo,
            state="merged",
            llm_summary__isnull=True,
        ).count()

        return report

    def _is_stale(self, db_pr, cache_pr):
        """Compare material fields between DB and cache PR.

        Returns True if any material field differs.
        """
        # Title
        if (cache_pr.title or "") != (db_pr.title or ""):
            return True

        # Body
        cache_body = cache_pr.body or ""
        db_body = db_pr.body or ""
        if cache_body != db_body:
            return True

        # State
        cache_state = "merged" if cache_pr.is_merged else cache_pr.state
        if cache_state != db_pr.state:
            return True

        # Size metrics
        if cache_pr.additions != db_pr.additions:
            return True
        if cache_pr.deletions != db_pr.deletions:
            return True

        # Draft status
        if cache_pr.is_draft != db_pr.is_draft:
            return True

        # JSON fields
        if (cache_pr.labels or []) != (db_pr.labels or []):
            return True
        if (cache_pr.milestone_title or "") != (db_pr.milestone_title or ""):
            return True
        if (cache_pr.assignees or []) != (db_pr.assignees or []):
            return True
        return (cache_pr.linked_issues or []) != (db_pr.linked_issues or [])

    def _has_child_gaps(self, db_pr, cache_pr):
        """Check if DB PR is missing child records that cache has.

        Uses annotated counts from the batch query.
        """
        # Compare review count
        cache_review_count = len(cache_pr.reviews) if cache_pr.reviews else 0
        if cache_review_count > db_pr.review_count:
            return True

        # Compare commit count
        cache_commit_count = len(cache_pr.commits) if cache_pr.commits else 0
        if cache_commit_count > db_pr.commit_count:
            return True

        # Compare file count
        cache_file_count = len(cache_pr.files) if cache_pr.files else 0
        if cache_file_count > db_pr.file_count:
            return True

        # Compare check run count
        cache_check_count = len(cache_pr.check_runs) if cache_pr.check_runs else 0
        return cache_check_count > db_pr.check_count

    def apply_repo(self, team, github_repo, report):
        """Apply reconciliation for a single repo.

        Uses PRPersistenceService for all write operations.
        Each PR is wrapped in its own transaction for isolation.

        Returns:
            Dict with counts of operations performed.
        """
        from django.db import transaction

        from apps.metrics.seeding.persistence import PRPersistenceService

        if self.dry_run:
            return {"created": 0, "updated": 0, "repaired": 0, "errors": 0}

        persistence = PRPersistenceService(team)

        # Pre-build member cache from all cache PRs that will be touched
        cache_prs_to_process = []
        for pr_id in report.missing_pr_ids + report.stale_pr_ids + report.partial_pr_ids:
            cache_pr = report.cache_prs_by_id.get(pr_id)
            if cache_pr:
                cache_prs_to_process.append(cache_pr)
        persistence.build_member_cache(cache_prs_to_process)

        created = 0
        updated = 0
        repaired = 0
        errors = 0

        # Create missing PRs
        for pr_id in report.missing_pr_ids:
            cache_pr = report.cache_prs_by_id.get(pr_id)
            if not cache_pr:
                continue
            try:
                persistence.create_pr(cache_pr, github_repo)
                created += 1
            except Exception:
                logger.warning("Failed to create PR %s for %s", pr_id, github_repo, exc_info=True)
                errors += 1

        # Update stale PRs (use pre-fetched DB PRs from analysis)
        for pr_id in report.stale_pr_ids:
            cache_pr = report.cache_prs_by_id.get(pr_id)
            db_pr = report.db_prs_by_id.get(pr_id)
            if not cache_pr or not db_pr:
                continue
            try:
                # Refresh from DB to get current state (analysis may be stale)
                db_pr.refresh_from_db()
                with transaction.atomic():
                    persistence.update_stale_pr(db_pr, cache_pr)
                updated += 1
            except Exception:
                logger.warning("Failed to update PR %s for %s", pr_id, github_repo, exc_info=True)
                errors += 1

        # Repair partial PRs (use pre-fetched DB PRs from analysis)
        for pr_id in report.partial_pr_ids:
            cache_pr = report.cache_prs_by_id.get(pr_id)
            db_pr = report.db_prs_by_id.get(pr_id)
            if not cache_pr or not db_pr:
                continue
            try:
                db_pr.refresh_from_db()
                with transaction.atomic():
                    persistence.repair_partial_pr(db_pr, cache_pr, github_repo)
                repaired += 1
            except Exception:
                logger.warning("Failed to repair PR %s for %s", pr_id, github_repo, exc_info=True)
                errors += 1

        if created or updated or repaired:
            self.modified_repos.add(github_repo)

        return {"created": created, "updated": updated, "repaired": repaired, "errors": errors}

    def bootstrap_repo_profiles(self, repos, org_profiles):
        """Ensure PublicRepoProfile rows exist for all fixture repos.

        Uses update_or_create for idempotency.
        """
        from apps.public.models import PublicRepoProfile

        for repo_info in repos:
            org_slug = repo_info["org_slug"]
            org_profile = org_profiles[org_slug]

            PublicRepoProfile.objects.update_or_create(
                org_profile=org_profile,
                repo_slug=repo_info["repo_slug"],
                defaults={
                    "team": org_profile.team,
                    "github_repo": repo_info["github_repo"],
                    "display_name": repo_info["repo_slug"].replace("-", " ").title(),
                    "is_flagship": repo_info["is_flagship"],
                    "is_public": True,
                },
            )

    def rebuild_snapshots(self, repos, org_profiles):
        """Rebuild PublicRepoStats and PublicOrgStats for modified repos.

        Only rebuilds repos that were modified during reconciliation or
        are missing PublicRepoStats entirely.
        """
        from apps.public.models import PublicRepoProfile, PublicRepoStats

        rebuilt = 0
        for repo_info in repos:
            github_repo = repo_info["github_repo"]
            org_slug = repo_info["org_slug"]

            try:
                repo_profile = PublicRepoProfile.objects.get(
                    org_profile=org_profiles[org_slug],
                    repo_slug=repo_info["repo_slug"],
                )
            except PublicRepoProfile.DoesNotExist:
                continue

            # Only rebuild if repo was modified or stats are missing
            needs_rebuild = github_repo in self.modified_repos
            if not needs_rebuild:
                needs_rebuild = not PublicRepoStats.objects.filter(repo_profile=repo_profile).exists()
            if not needs_rebuild:
                continue

            logger.info("Building snapshot for %s (%d/%d)...", github_repo, rebuilt + 1, len(repos))
            try:
                build_repo_snapshot(repo_profile)
                rebuilt += 1
            except Exception:
                logger.warning("Failed to build snapshot for %s", github_repo, exc_info=True)

        # Rebuild org stats for affected orgs
        if rebuilt > 0:
            self._rebuild_org_stats(org_profiles)

        # Generate deterministic insights for repos with stats
        repo_profiles_with_stats = []
        for repo_info in repos:
            try:
                rp = PublicRepoProfile.objects.select_related("stats").get(
                    org_profile=org_profiles[repo_info["org_slug"]],
                    repo_slug=repo_info["repo_slug"],
                )
                if hasattr(rp, "stats"):
                    repo_profiles_with_stats.append(rp)
            except PublicRepoProfile.DoesNotExist:
                continue

        if repo_profiles_with_stats:
            self.generate_deterministic_insights(repo_profiles_with_stats)

        return {"rebuilt": rebuilt}

    def _rebuild_org_stats(self, org_profiles):
        """Rebuild PublicOrgStats for orgs that had repo changes."""
        from apps.public.aggregations import BOT_USERNAMES, compute_ai_tools_breakdown, compute_team_summary
        from apps.public.models import PublicOrgStats

        for org_slug, org_profile in org_profiles.items():
            team_id = org_profile.team_id
            try:
                from apps.public.tasks import _best_data_year

                year = _best_data_year(team_id)
                summary = compute_team_summary(team_id, year=year)
                ai_tools = compute_ai_tools_breakdown(team_id, year=year)

                from apps.metrics.models import PullRequest

                total_prs = (
                    PullRequest.objects.filter(  # noqa: TEAM001 - cross-team
                        team_id=team_id, state="merged"
                    )
                    .exclude(author__github_username__endswith="[bot]")
                    .exclude(author__github_username__in=BOT_USERNAMES)
                    .count()
                )

                from django.utils import timezone

                PublicOrgStats.objects.update_or_create(
                    org_profile=org_profile,
                    defaults={
                        "total_prs": total_prs,
                        "ai_assisted_pct": summary.get("ai_pct", 0),
                        "median_cycle_time_hours": summary.get("median_cycle_time_hours", 0),
                        "median_review_time_hours": summary.get("median_review_time_hours", 0),
                        "active_contributors_90d": summary.get("active_contributors_90d", 0),
                        "top_ai_tools": ai_tools,
                        "last_computed_at": timezone.now(),
                    },
                )
            except Exception:
                logger.warning("Failed to rebuild org stats for %s", org_slug, exc_info=True)

    def generate_deterministic_insights(self, repo_profiles):
        """Generate template-based insights without Groq.

        Uses data from PublicRepoStats to create meaningful but deterministic content.
        """
        from apps.public.models import PublicRepoInsight

        for repo_profile in repo_profiles:
            try:
                stats = repo_profile.stats
            except Exception:
                continue

            total_in_window = getattr(stats, "total_prs_in_window", 0) or 0
            ai_pct = getattr(stats, "ai_assisted_pct", 0) or 0
            cycle_time = getattr(stats, "median_cycle_time_hours", 0) or 0

            content = (
                f"{repo_profile.display_name} merged {total_in_window} PRs in the past 30 days"
                f" with {ai_pct}% AI-assisted."
            )
            if cycle_time:
                content += f" Median cycle time is {cycle_time} hours."

            PublicRepoInsight.objects.update_or_create(
                repo_profile=repo_profile,
                is_current=True,
                defaults={
                    "content": content,
                    "insight_type": "weekly",
                    "batch_id": "local-deterministic",
                },
            )

    def _get_llm_candidates(self, github_repo, team, max_per_repo=50):
        """Get PRs eligible for LLM enrichment.

        Scoping rules:
        - Merged PRs only
        - Last 90 days only
        - Missing llm_summary
        - Capped at max_per_repo
        """
        from datetime import timedelta

        from django.utils import timezone

        from apps.metrics.models import PullRequest

        cutoff = timezone.now() - timedelta(days=90)
        return list(
            PullRequest.objects.filter(  # noqa: TEAM001 - cross-team
                team=team,
                github_repo=github_repo,
                state="merged",
                merged_at__gte=cutoff,
                llm_summary__isnull=True,
            ).order_by("-merged_at")[:max_per_repo]
        )

    def run_llm_enrichment(self, repos, org_profiles, max_per_repo=50):
        """Run scoped Groq LLM enrichment for flagship repos only.

        Only processes flagship repos. Uses GroqBatchProcessor exclusively.
        """
        flagship_repos = [r for r in repos if r.get("is_flagship")]

        if not flagship_repos:
            logger.info("No flagship repos to enrich with LLM")
            return

        for repo_info in flagship_repos:
            github_repo = repo_info["github_repo"]
            org_slug = repo_info["org_slug"]
            team = org_profiles[org_slug].team

            candidates = self._get_llm_candidates(github_repo, team, max_per_repo)
            if not candidates:
                logger.info("No LLM candidates for %s", github_repo)
                continue

            if self.dry_run:
                logger.info(
                    "Would submit %d PRs for %s to Groq (cap: %d)",
                    len(candidates),
                    github_repo,
                    max_per_repo,
                )
                continue

            logger.info("Submitting %d PRs for %s to Groq", len(candidates), github_repo)
            try:
                processor = GroqBatchProcessor()
                processor.submit_batch(candidates)
            except Exception:
                logger.warning("Failed to process LLM batch for %s", github_repo, exc_info=True)
