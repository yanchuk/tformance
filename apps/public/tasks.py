"""Celery tasks for public analytics.

Daily pipeline:
1. sync_public_oss_repositories_task (3 AM) — fetch fresh PR data for flagship repos
2. compute_public_stats_task (7 AM) — recompute PublicOrgStats + PublicRepoStats
3. clear_public_cache — clears Redis cache after stats refresh

The sync task runs before customer sync (4 AM) using separate PAT tokens.
"""

import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from apps.metrics.models import PullRequest
from apps.public.aggregations import (
    BOT_USERNAMES,
    compute_ai_tools_breakdown,
    compute_team_summary,
)
from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile, PublicRepoStats
from apps.public.services import CACHE_PREFIX
from apps.public.services.sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)


def _best_data_year(team_id, fallback=None):
    """Return the year with the most merged PRs for a given team.

    Seeded data may land in different years (e.g., 2025 vs 2026).
    Using the wrong year causes all aggregations to return zeros.

    Falls back to `fallback` (or current year) if no merged PRs exist.
    """
    from django.db.models import Count
    from django.db.models.functions import ExtractYear

    rows = (
        PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
            team_id=team_id,
            state="merged",
            pr_created_at__isnull=False,
        )
        .annotate(yr=ExtractYear("pr_created_at"))
        .values("yr")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    if rows:
        return rows[0]["yr"]

    if fallback is not None:
        return fallback

    from django.utils import timezone

    return timezone.now().year


@shared_task(soft_time_limit=600, time_limit=660)
def compute_public_stats_task():
    """Recompute PublicOrgStats for all public organizations.

    Iterates over all public org profiles, computes fresh metrics
    via aggregation functions, and updates the PublicOrgStats table.
    Then clears the public cache so pages serve fresh data.

    Safe to run multiple times — uses update_or_create for idempotency.
    """
    logger.info("Starting public stats computation")
    now = timezone.now()

    profiles = PublicOrgProfile.objects.filter(
        is_public=True,
    ).select_related("team")

    computed = 0
    errors = 0

    for profile in profiles:
        try:
            # Determine the best year for aggregation: use the year with the most
            # merged PRs, since seeded data may span 2025 or 2026
            year = _best_data_year(profile.team_id, fallback=now.year)

            summary = compute_team_summary(profile.team_id, year=year)
            ai_tools = compute_ai_tools_breakdown(profile.team_id, year=year)

            # total_prs uses ALL-TIME count (not year-filtered) because it
            # gates directory visibility via MIN_PRS_THRESHOLD and represents
            # overall data significance, not a time-bound metric.
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
            computed += 1
            logger.debug(f"Computed stats for {profile.display_name}: {summary['total_prs']} PRs")
        except Exception:
            errors += 1
            logger.exception(f"Failed to compute stats for {profile.display_name}")

    # Build repo-level snapshots for ALL public repos (not just flagship)
    from apps.public.repo_snapshot_service import build_repo_snapshot

    repo_snapshots = 0
    repo_errors = 0

    for repo_profile in PublicRepoProfile.objects.snapshot_eligible():
        try:
            build_repo_snapshot(repo_profile)
            repo_snapshots += 1
        except Exception:
            repo_errors += 1
            logger.exception(f"Failed to build snapshot for {repo_profile.display_name}")

    # Clear public cache after all stats are updated
    _clear_public_cache()

    # Purge Cloudflare edge cache (fire-and-forget)
    from apps.public.cloudflare import purge_all_cache

    purge_all_cache()

    logger.info(
        "Public stats computation complete. Orgs: %d, Repo snapshots: %d, Errors: %d/%d",
        computed,
        repo_snapshots,
        errors,
        repo_errors,
    )

    return {
        "computed": computed,
        "errors": errors,
        "repo_snapshots": repo_snapshots,
        "repo_errors": repo_errors,
    }


def _clear_public_cache():
    """Clear all public analytics cache keys.

    Uses Redis SCAN to find and delete keys matching the public prefix.
    Falls back to deleting known key patterns if SCAN is unavailable.
    """
    try:
        # Use Redis SCAN to find and delete public cache keys (non-blocking)
        from django_redis import get_redis_connection  # type: ignore[import-untyped]

        redis_conn = get_redis_connection("default")
        keys = list(redis_conn.scan_iter(match=f"*{CACHE_PREFIX}*", count=100))
        if keys:
            redis_conn.delete(*keys)
            logger.info(f"Cleared {len(keys)} public cache keys")
    except (ImportError, Exception):
        # Fallback: delete known cache keys
        known_keys = [
            f"{CACHE_PREFIX}directory",
            f"{CACHE_PREFIX}global",
        ]
        # Also clear per-org and per-industry keys
        for profile in PublicOrgProfile.objects.filter(is_public=True).values_list("public_slug", flat=True):
            known_keys.append(f"{CACHE_PREFIX}org:{profile}")
        for industry_key, _ in PublicOrgProfile._meta.get_field("industry").choices:
            known_keys.append(f"{CACHE_PREFIX}industry:{industry_key}")

        cache.delete_many(known_keys)
        logger.info(f"Cleared {len(known_keys)} known public cache keys (fallback)")


@shared_task(soft_time_limit=1800, time_limit=1860)
def sync_public_oss_repositories_task():
    """Sync PR data for all sync-eligible public repos using PAT-based fetchers.

    Runs at 3 AM UTC, before customer sync at 4 AM. Uses GITHUB_SEEDING_TOKENS
    for authentication. Uses Redis lock to prevent concurrent runs.
    After sync, chains compute_public_stats_task.
    """
    # Atomic lock via cache.add() to prevent concurrent sync runs (#1)
    acquired = cache.add("public_sync_lock", "1", timeout=1800)
    if not acquired:
        logger.warning("Public sync already running, skipping")
        return {"synced": 0, "errors": 0, "skipped": "locked"}

    try:
        return _run_sync()
    finally:
        cache.delete("public_sync_lock")


def _run_sync():
    """Inner sync logic, separated for testability."""
    logger.info("Starting public OSS repository sync")

    # Initialize token pool (reads GITHUB_SEEDING_TOKENS env var)
    try:
        from apps.public.public_sync import GitHubTokenPool

        token_pool = GitHubTokenPool()
    except ValueError:
        logger.error("No GitHub seeding tokens configured, skipping public sync")
        return {"synced": 0, "errors": 1, "reason": "no_tokens"}

    orchestrator = SyncOrchestrator(token_pool)
    repos = PublicRepoProfile.objects.sync_eligible()

    synced = 0
    errors = 0

    for repo_profile in repos:
        if token_pool.all_exhausted:
            logger.warning("All tokens exhausted, stopping sync")
            break

        result = orchestrator.sync_repo(repo_profile)
        if result.get("errors", 0) == 0:
            synced += 1
        else:
            errors += 1

    logger.info("Public OSS sync complete. Synced: %d, Errors: %d", synced, errors)

    # Chain: recompute stats after sync
    if synced > 0:
        compute_public_stats_task.delay()

    return {"synced": synced, "errors": errors}


@shared_task(soft_time_limit=900, time_limit=960)
def generate_public_repo_insights_weekly():
    """Generate LLM-powered narrative insights for all flagship public repos.

    Runs weekly on Monday 8 AM UTC. Uses Groq Batch API for 50% cost savings.
    Submits all repos as a single batch, polls for completion, stores results.
    Graceful degradation: failures leave previous insights in place.
    """
    from apps.public.repo_insight_service import process_insights_batch, submit_insights_batch

    logger.info("Starting weekly public repo insight generation (batch mode)")

    repos = PublicRepoProfile.objects.filter(
        insights_enabled=True,
        sync_enabled=True,
        is_public=True,
    ).select_related("org_profile", "stats")

    # Collect repos with stats
    repos_with_stats = []
    skipped = 0

    for repo_profile in repos:
        try:
            stats = repo_profile.stats
            repos_with_stats.append((repo_profile, stats))
        except PublicRepoStats.DoesNotExist:
            logger.warning("No stats for %s, skipping insight", repo_profile.display_name)
            skipped += 1

    if not repos_with_stats:
        logger.info("No repos with stats to generate insights for")
        return {"generated": 0, "skipped": skipped, "errors": 0}

    # Submit batch
    batch_id = submit_insights_batch(repos_with_stats)
    if not batch_id:
        logger.error("Failed to submit insights batch")
        return {"generated": 0, "skipped": skipped, "errors": len(repos_with_stats)}

    # Poll and process results
    result = process_insights_batch(batch_id, repos_with_stats)

    logger.info(
        "Weekly insights complete (batch %s). Generated: %d, Skipped: %d, Errors: %d",
        batch_id,
        result["generated"],
        skipped,
        result["errors"],
    )
    return {"generated": result["generated"], "skipped": skipped, "errors": result["errors"]}
