"""Rebuild all public repo snapshots and org stats.

Useful after DB restore or initial Unraid setup.

Usage:
    python manage.py rebuild_public_catalog_snapshots
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.metrics.models import PullRequest
from apps.public.aggregations import BOT_USERNAMES, compute_ai_tools_breakdown, compute_team_summary
from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Rebuild PublicRepoStats and PublicOrgStats for all public repos"

    def handle(self, *args, **options):
        from apps.public.repo_snapshot_service import build_repo_snapshot
        from apps.public.tasks import _best_data_year

        now = timezone.now()

        # Phase 1: Rebuild repo snapshots
        repos = PublicRepoProfile.objects.snapshot_eligible()
        repo_count = 0
        repo_errors = 0

        for repo_profile in repos:
            try:
                build_repo_snapshot(repo_profile)
                repo_count += 1
            except Exception:
                repo_errors += 1
                logger.exception("Failed to build snapshot for %s", repo_profile.display_name)

        self.stdout.write(f"Repo snapshots: {repo_count} built, {repo_errors} errors")

        # Phase 2: Rebuild org stats
        org_count = 0
        for profile in PublicOrgProfile.objects.filter(is_public=True).select_related("team"):
            try:
                year = _best_data_year(profile.team_id, fallback=now.year)
                summary = compute_team_summary(profile.team_id, year=year)
                ai_tools = compute_ai_tools_breakdown(profile.team_id, year=year)

                total_prs_all_time = (
                    PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
                        team_id=profile.team_id,
                        state="merged",
                    )
                    .exclude(author__github_username__endswith="[bot]")
                    .exclude(author__github_username__in=BOT_USERNAMES)
                    .count()
                )

                PublicOrgStats.objects.update_or_create(
                    org_profile=profile,
                    defaults={
                        "total_prs": total_prs_all_time,
                        "ai_assisted_pct": summary["ai_pct"],
                        "median_cycle_time_hours": summary["median_cycle_time_hours"],
                        "median_review_time_hours": summary["median_review_time_hours"],
                        "active_contributors_90d": summary["active_contributors_90d"],
                        "top_ai_tools": ai_tools,
                        "last_computed_at": now,
                    },
                )
                org_count += 1
            except Exception:
                logger.exception("Failed to compute org stats for %s", profile.display_name)

        self.stdout.write(f"Org stats: {org_count} computed")
