"""Service to build and store repo-level snapshots for public pages.

Orchestrates existing aggregation functions with repo-level filtering
to produce a self-contained PublicRepoStats record that drives the
canonical repo page without live queries.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from apps.metrics.models import PullRequest
from apps.metrics.services.dashboard.ai_metrics import get_ai_impact_stats
from apps.public.aggregations import (
    BOT_USERNAMES,
    _base_pr_queryset,
    compute_ai_tools_breakdown,
    compute_monthly_cycle_time,
    compute_monthly_trends,
    compute_pr_size_distribution,
    compute_pr_type_trends,
    compute_recent_prs,
    compute_team_summary,
)
from apps.public.formatting import format_duration
from apps.public.models import PublicOrgStats, PublicRepoProfile, PublicRepoStats
from apps.public.services.public_trends import build_combined_trend, build_correlation_scatter
from apps.public.views.helpers import PUBLIC_SUMMARY_WINDOW_DAYS, PUBLIC_TREND_WINDOW_DAYS

logger = logging.getLogger(__name__)


def build_repo_snapshot(repo_profile: PublicRepoProfile) -> PublicRepoStats:
    """Build or update a complete snapshot for a public repo.

    Computes all metrics needed to render the canonical repo page
    and stores them in PublicRepoStats. Uses update_or_create for
    idempotency — safe to call multiple times.
    """
    now = timezone.now()
    team_id = repo_profile.team_id
    github_repo = repo_profile.github_repo

    # Summary window: last 30 days
    summary_end = now
    summary_start = now - timedelta(days=PUBLIC_SUMMARY_WINDOW_DAYS)

    # Trend window: last 90 days
    trend_end = now
    trend_start = now - timedelta(days=PUBLIC_TREND_WINDOW_DAYS)

    # Core summary metrics (30-day window)
    summary = compute_team_summary(
        team_id,
        start_date=summary_start,
        end_date=summary_end,
        github_repo=github_repo,
    )

    # All-time PR count for this repo (no date filter — _base_pr_queryset
    # always applies date bounds, so we query directly here)
    total_prs_all_time = (
        PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
            team_id=team_id,
            state="merged",
            github_repo=github_repo,
        )
        .exclude(Q(author__github_username__endswith="[bot]") | Q(author__github_username__in=BOT_USERNAMES))
        .count()
    )

    # Trend data (90-day window)
    monthly_trends = compute_monthly_trends(
        team_id,
        start_date=trend_start,
        end_date=trend_end,
        github_repo=github_repo,
    )
    cycle_time_trends = compute_monthly_cycle_time(
        team_id,
        start_date=trend_start,
        end_date=trend_end,
        github_repo=github_repo,
    )

    # Serialize trend data (datetimes → ISO strings)
    trend_data = {
        "adoption": [
            {
                "month": row["month"].isoformat() if row["month"] else None,
                "total_prs": row["total_prs"],
                "ai_prs": row["ai_prs"],
                "ai_pct": row["ai_pct"],
            }
            for row in monthly_trends
        ],
        "cycle_time": [
            {
                "month": row["month"].isoformat() if row["month"] else None,
                "avg_cycle_time": row["avg_cycle_time"],
            }
            for row in cycle_time_trends
        ],
    }

    # Breakdowns (30-day window)
    ai_tools = compute_ai_tools_breakdown(
        team_id,
        start_date=summary_start,
        end_date=summary_end,
        github_repo=github_repo,
    )
    pr_sizes = compute_pr_size_distribution(
        team_id,
        start_date=summary_start,
        end_date=summary_end,
        github_repo=github_repo,
    )
    pr_types_raw = compute_pr_type_trends(
        team_id,
        start_date=summary_start,
        end_date=summary_end,
        github_repo=github_repo,
    )
    # Flatten monthly type counts into aggregate totals for the summary card
    pr_type_totals: dict[str, int] = {}
    for entry in pr_types_raw:
        for pr_type, count in entry.get("types", {}).items():
            pr_type_totals[pr_type] = pr_type_totals.get(pr_type, 0) + count
    pr_types = [{"type": t, "count": c} for t, c in sorted(pr_type_totals.items(), key=lambda x: -x[1])]
    breakdown_data = {
        "ai_tools": ai_tools,
        "pr_sizes": pr_sizes,
        "pr_types": pr_types,
    }

    # Recent PRs (repo-scoped)
    recent = compute_recent_prs(team_id, limit=10, github_repo=github_repo)
    # Serialize datetimes for JSON storage
    for pr in recent:
        if pr.get("merged_at"):
            pr["merged_at"] = pr["merged_at"].isoformat()

    # Cadence change (pass `now` to avoid clock drift within the pipeline)
    cadence_change = _compute_cadence_change(team_id, github_repo, now=now)

    # Signals
    best_signal = _compute_best_signal(summary, cadence_change)
    watchout_signal = _compute_watchout_signal(summary, cadence_change)

    # Combined trend data (review 6A: isolated try/except)
    try:
        combined_trend = build_combined_trend(repo_profile.team, trend_start.date(), trend_end.date(), repo=github_repo)
    except Exception:
        logger.warning("Failed to build combined trend for %s", repo_profile.display_name, exc_info=True)
        combined_trend = {}

    # Correlation scatter (review 6A)
    try:
        correlation = build_correlation_scatter(
            repo_profile.team, trend_start.date(), trend_end.date(), repo=github_repo
        )
    except Exception:
        logger.warning("Failed to build correlation for %s", repo_profile.display_name, exc_info=True)
        correlation = {}

    # AI impact comparison (review 6A)
    try:
        ai_impact = get_ai_impact_stats(repo_profile.team, summary_start.date(), summary_end.date(), repo=github_repo)
        # Convert Decimal values to float for JSON serialization
        ai_impact = {k: float(v) if isinstance(v, Decimal) else v for k, v in ai_impact.items()}
    except Exception:
        logger.warning("Failed to compute AI impact for %s", repo_profile.display_name, exc_info=True)
        ai_impact = {}

    # Repo vs org comparison (review 4A, 8A)
    try:
        org_stats = PublicOrgStats.objects.get(org_profile=repo_profile.org_profile)
        comparison = {
            "ai_adoption_delta": float(summary["ai_pct"]) - float(org_stats.ai_assisted_pct),
            "cycle_time_delta": float(summary["median_cycle_time_hours"]) - float(org_stats.median_cycle_time_hours),
            "review_time_delta": float(summary["median_review_time_hours"]) - float(org_stats.median_review_time_hours),
        }
    except PublicOrgStats.DoesNotExist:
        comparison = {}
    except Exception:
        logger.warning("Failed to compute comparison for %s", repo_profile.display_name, exc_info=True)
        comparison = {}

    stats, _created = PublicRepoStats.objects.update_or_create(
        repo_profile=repo_profile,
        defaults={
            "summary_window_days": PUBLIC_SUMMARY_WINDOW_DAYS,
            "trend_window_days": PUBLIC_TREND_WINDOW_DAYS,
            "total_prs": total_prs_all_time,
            "total_prs_in_window": summary["total_prs"],
            "ai_assisted_pct": summary["ai_pct"],
            "median_cycle_time_hours": summary["median_cycle_time_hours"],
            "median_review_time_hours": summary["median_review_time_hours"],
            "active_contributors_30d": summary["active_contributors_30d"],
            "cadence_change_pct": cadence_change,
            "best_signal": best_signal,
            "watchout_signal": watchout_signal,
            "trend_data": trend_data,
            "breakdown_data": breakdown_data,
            "recent_prs": recent,
            "benchmark_data": {},
            "combined_trend_data": combined_trend,
            "correlation_data": correlation,
            "ai_impact_data": ai_impact,
            "comparison_data": comparison,
            "last_computed_at": now,
        },
    )

    logger.info(
        "Built snapshot for %s: %d PRs in window, %.1f%% AI",
        repo_profile.display_name,
        summary["total_prs"],
        float(summary["ai_pct"]),
    )
    return stats


def _compute_cadence_change(team_id: int, github_repo: str, now=None) -> Decimal:
    """Compute period-over-period PR volume change (30d vs prior 30d).

    Uses _base_pr_queryset for consistent bot-exclusion and repo filtering.
    Accepts `now` to stay aligned with the parent snapshot's clock.
    """
    if now is None:
        now = timezone.now()

    current_start = now - timedelta(days=30)
    prior_start = now - timedelta(days=60)

    current_count = _base_pr_queryset(
        team_id,
        start_date=current_start,
        end_date=now,
        github_repo=github_repo,
    ).count()

    prior_count = _base_pr_queryset(
        team_id,
        start_date=prior_start,
        end_date=current_start,
        github_repo=github_repo,
    ).count()

    if prior_count == 0:
        return Decimal("0")
    change = (current_count - prior_count) / prior_count * 100
    return Decimal(str(round(change, 2)))


def _compute_best_signal(summary: dict, cadence_change: Decimal) -> dict:
    """Identify the most positive metric as the 'best signal'."""
    signals = []

    ai_pct = float(summary["ai_pct"])
    if ai_pct >= 30:
        signals.append(
            {
                "metric": "ai_adoption",
                "label": "AI Adoption",
                "value": f"{ai_pct:.0f}%",
                "description": f"{ai_pct:.0f}% of PRs are AI-assisted",
                "strength": ai_pct,
            }
        )

    if float(cadence_change) > 10:
        signals.append(
            {
                "metric": "cadence_growth",
                "label": "Growing Cadence",
                "value": f"+{float(cadence_change):.0f}%",
                "description": f"PR volume up {float(cadence_change):.0f}% vs prior period",
                "strength": float(cadence_change),
            }
        )

    cycle_time = float(summary["median_cycle_time_hours"])
    if 0 < cycle_time <= 24:
        signals.append(
            {
                "metric": "fast_delivery",
                "label": "Fast Delivery",
                "value": format_duration(cycle_time),
                "description": f"Median cycle time of {format_duration(cycle_time)}",
                "strength": 100 - cycle_time,
            }
        )

    if not signals:
        return {"metric": "none", "label": "Steady", "value": "-", "description": "Metrics are stable"}

    return max(signals, key=lambda s: s["strength"])


def _compute_watchout_signal(summary: dict, cadence_change: Decimal) -> dict:
    """Identify the most concerning metric as the 'watchout signal'."""
    signals = []

    review_time = float(summary["median_review_time_hours"])
    if review_time > 24:
        signals.append(
            {
                "metric": "review_pressure",
                "label": "Review Pressure",
                "value": format_duration(review_time),
                "description": f"Median review time is {format_duration(review_time)}",
                "severity": review_time,
            }
        )

    cycle_time = float(summary["median_cycle_time_hours"])
    if cycle_time > 72:
        signals.append(
            {
                "metric": "slow_delivery",
                "label": "Slow Delivery",
                "value": format_duration(cycle_time),
                "description": f"Median cycle time of {format_duration(cycle_time)}",
                "severity": cycle_time,
            }
        )

    if float(cadence_change) < -20:
        signals.append(
            {
                "metric": "declining_cadence",
                "label": "Declining Cadence",
                "value": f"{float(cadence_change):.0f}%",
                "description": f"PR volume down {abs(float(cadence_change)):.0f}% vs prior period",
                "severity": abs(float(cadence_change)),
            }
        )

    if not signals:
        return {"metric": "none", "label": "No Concerns", "value": "-", "description": "No concerning signals"}

    return max(signals, key=lambda s: s["severity"])
