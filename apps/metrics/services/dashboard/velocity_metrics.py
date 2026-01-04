"""Velocity and quality metrics for dashboard.

Functions for velocity comparison, quality metrics, and team health.
"""

from datetime import date, timedelta

from django.db.models import Avg, Count, F, Q

from apps.metrics.models import PRReview
from apps.metrics.services.dashboard._helpers import (
    _apply_repo_filter,
    _get_merged_prs_in_range,
)
from apps.metrics.services.dashboard.pr_metrics import PR_SIZE_L_MAX, get_open_prs_stats
from apps.metrics.services.dashboard.review_metrics import detect_review_bottleneck
from apps.teams.models import Team


def get_velocity_comparison(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Compare velocity metrics between current and previous period.

    Compares current period (start_date to end_date) against a previous period
    of the same length immediately preceding the current period.

    Example: If current period is 2024-01-08 to 2024-01-14 (7 days),
    previous period is 2024-01-01 to 2024-01-07 (also 7 days).

    Args:
        team: Team instance
        start_date: Start of current period
        end_date: End of current period
        repo: Optional repository filter

    Returns:
        dict with:
        - throughput: dict with current (int), previous (int), pct_change (float|None)
        - cycle_time: dict with current (Decimal|None), previous (Decimal|None), pct_change (float|None)
        - review_time: dict with current (Decimal|None), previous (Decimal|None), pct_change (float|None)

        pct_change is None when previous value is 0 (avoid division by zero)
        pct_change formula: (current - previous) / previous * 100
        Negative pct_change means improvement (faster, more throughput)
    """

    # Calculate period length
    period_length = (end_date - start_date).days + 1

    # Calculate previous period dates
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length - 1)

    # Get PRs for both periods
    current_prs = _apply_repo_filter(_get_merged_prs_in_range(team, start_date, end_date), repo)
    previous_prs = _apply_repo_filter(_get_merged_prs_in_range(team, previous_start, previous_end), repo)

    # Aggregate all metrics in a single query per period (reduces 6 queries to 2)
    current_stats = current_prs.aggregate(
        throughput=Count("id"),
        avg_cycle_time=Avg("cycle_time_hours"),
        avg_review_time=Avg("review_time_hours"),
    )
    previous_stats = previous_prs.aggregate(
        throughput=Count("id"),
        avg_cycle_time=Avg("cycle_time_hours"),
        avg_review_time=Avg("review_time_hours"),
    )

    current_throughput = current_stats["throughput"]
    previous_throughput = previous_stats["throughput"]
    current_cycle_time = current_stats["avg_cycle_time"]
    previous_cycle_time = previous_stats["avg_cycle_time"]
    current_review_time = current_stats["avg_review_time"]
    previous_review_time = previous_stats["avg_review_time"]

    # Helper to calculate percentage change
    def calc_pct_change(current_val, previous_val):
        if previous_val is None or previous_val == 0:
            return None
        if current_val is None:
            return None
        return float((current_val - previous_val) / previous_val * 100)

    return {
        "throughput": {
            "current": current_throughput,
            "previous": previous_throughput,
            "pct_change": calc_pct_change(current_throughput, previous_throughput),
        },
        "cycle_time": {
            "current": current_cycle_time,
            "previous": previous_cycle_time,
            "pct_change": calc_pct_change(current_cycle_time, previous_cycle_time),
        },
        "review_time": {
            "current": current_review_time,
            "previous": previous_review_time,
            "pct_change": calc_pct_change(current_review_time, previous_review_time),
        },
    }


def get_quality_metrics(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get quality metrics for PRs in a period.

    Args:
        team: Team instance
        start_date: Start of period
        end_date: End of period
        repo: Optional repository filter

    Returns:
        dict with:
        - revert_count: int - Number of revert PRs
        - revert_rate: float - Percentage of PRs that are reverts (0-100)
        - hotfix_count: int - Number of hotfix PRs
        - hotfix_rate: float - Percentage of PRs that are hotfixes (0-100)
        - avg_review_rounds: float|None - Average number of review rounds per PR (None if no data)
        - large_pr_pct: float - Percentage of PRs over 500 lines changed (0-100)
    """
    # Get merged PRs for the period
    prs = _apply_repo_filter(_get_merged_prs_in_range(team, start_date, end_date), repo)

    # Aggregate all metrics in a single query
    stats = prs.annotate(lines_changed=F("additions") + F("deletions")).aggregate(
        total_prs=Count("id"),
        revert_count=Count("id", filter=Q(is_revert=True)),
        hotfix_count=Count("id", filter=Q(is_hotfix=True)),
        avg_review_rounds=Avg("review_rounds"),
        large_pr_count=Count("id", filter=Q(lines_changed__gt=PR_SIZE_L_MAX)),
    )

    total_prs = stats["total_prs"]
    revert_count = stats["revert_count"]
    hotfix_count = stats["hotfix_count"]
    avg_review_rounds = stats["avg_review_rounds"]
    large_pr_count = stats["large_pr_count"]

    # Calculate rates (handle division by zero)
    if total_prs > 0:
        revert_rate = revert_count * 100.0 / total_prs
        hotfix_rate = hotfix_count * 100.0 / total_prs
        large_pr_pct = large_pr_count * 100.0 / total_prs
    else:
        revert_rate = 0.0
        hotfix_rate = 0.0
        large_pr_pct = 0.0

    # Convert avg_review_rounds to float if present
    if avg_review_rounds is not None:
        avg_review_rounds = float(avg_review_rounds)

    return {
        "revert_count": revert_count,
        "revert_rate": revert_rate,
        "hotfix_count": hotfix_count,
        "hotfix_rate": hotfix_rate,
        "avg_review_rounds": avg_review_rounds,
        "large_pr_pct": large_pr_pct,
    }


def get_team_health_metrics(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get team health metrics for a period.

    Args:
        team: Team instance
        start_date: Start of period
        end_date: End of period
        repo: Optional repository filter

    Returns:
        dict with:
        - active_contributors: int - Count of unique PR authors in period
        - pr_distribution: dict - { "top_contributor_pct": float, "is_concentrated": bool }
        - review_distribution: dict - { "avg_reviews_per_reviewer": float|None, "max_reviews": int }
        - bottleneck: dict|None - Result from detect_review_bottleneck() or None
        - open_prs: dict - Open PR stats (total_open, draft_count, ready_for_review, draft_pct)
    """
    # Get merged PRs for the period
    prs = _apply_repo_filter(_get_merged_prs_in_range(team, start_date, end_date), repo)

    # Count unique authors (active contributors)
    active_contributors = prs.values("author").distinct().count()

    # Calculate PR distribution
    if active_contributors > 0:
        # Group PRs by author and count
        author_pr_counts = list(prs.values("author").annotate(pr_count=Count("id")).order_by("-pr_count"))
        total_prs = sum(a["pr_count"] for a in author_pr_counts)
        if total_prs > 0:
            max_pr_count = author_pr_counts[0]["pr_count"]
            top_contributor_pct = max_pr_count * 100.0 / total_prs
        else:
            top_contributor_pct = 0.0
    else:
        top_contributor_pct = 0.0

    is_concentrated = top_contributor_pct > 50.0

    # Calculate review distribution
    # Filter reviews for merged PRs in the date range
    review_filters = {
        "team": team,
        "pull_request__in": prs,
    }

    reviewer_stats = list(
        PRReview.objects.filter(**review_filters)  # noqa: TEAM001 - team in filters
        .values("reviewer")
        .annotate(review_count=Count("id"))
    )

    if reviewer_stats:
        review_counts = [r["review_count"] for r in reviewer_stats]
        avg_reviews_per_reviewer = sum(review_counts) / len(review_counts)
        max_reviews = max(review_counts)
    else:
        avg_reviews_per_reviewer = None
        max_reviews = 0

    # Get bottleneck info
    bottleneck = detect_review_bottleneck(team, start_date, end_date, repo)

    # Get open PR stats (draft vs ready for review)
    open_prs = get_open_prs_stats(team, repo)

    return {
        "active_contributors": active_contributors,
        "pr_distribution": {
            "top_contributor_pct": top_contributor_pct,
            "is_concentrated": is_concentrated,
        },
        "review_distribution": {
            "avg_reviews_per_reviewer": avg_reviews_per_reviewer,
            "max_reviews": max_reviews,
        },
        "bottleneck": bottleneck,
        "open_prs": open_prs,
    }
