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

# =============================================================================
# Team Health Indicator Thresholds
# =============================================================================
# Throughput: PRs merged per week
THROUGHPUT_GREEN_THRESHOLD = 5  # >= 5 PRs/week is healthy
THROUGHPUT_YELLOW_THRESHOLD = 3  # >= 3 PRs/week is moderate

# Cycle Time: hours from PR open to merge (lower is better)
CYCLE_TIME_GREEN_THRESHOLD = 24  # <= 24 hours is healthy
CYCLE_TIME_YELLOW_THRESHOLD = 72  # <= 72 hours is moderate

# Quality: revert rate percentage (lower is better)
QUALITY_GREEN_THRESHOLD = 2  # <= 2% revert rate is healthy
QUALITY_YELLOW_THRESHOLD = 5  # <= 5% revert rate is moderate

# AI Adoption: percentage of AI-assisted PRs
AI_ADOPTION_GREEN_THRESHOLD = 30  # >= 30% is healthy
AI_ADOPTION_YELLOW_THRESHOLD = 10  # >= 10% is moderate

# Review Bottleneck: percentage of reviews by single reviewer
BOTTLENECK_THRESHOLD = 50  # > 50% triggers bottleneck warning


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


def get_team_health_indicators(team: Team, start_date: date, end_date: date) -> dict:
    """Get team health indicators with status and trend for each metric.

    Calculates five key health indicators for the team, each with a value,
    trend (compared to previous period), and status (green/yellow/red).

    Thresholds (defined as module constants):
        - Throughput: >= 5 PRs/week (green), >= 3 (yellow), < 3 (red)
        - Cycle Time: <= 24 hours (green), <= 72 hours (yellow), > 72 (red)
        - Quality: <= 2% revert rate (green), <= 5% (yellow), > 5% (red)
        - AI Adoption: >= 30% (green), >= 10% (yellow), < 10% (red)
        - Review Bottleneck: detected if one reviewer has > 50% of reviews

    Args:
        team: Team instance
        start_date: Start of current period
        end_date: End of current period

    Returns:
        dict with:
        - throughput: dict with value (float), trend (str), status (str)
        - cycle_time: dict with value (float), trend (str), status (str)
        - quality: dict with value (float), trend (str), status (str)
        - review_bottleneck: dict with detected (bool), reviewer (str|None), status (str)
        - ai_adoption: dict with value (float), trend (str), status (str)
    """
    # Calculate period length for previous period comparison
    period_length = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length - 1)

    # Get PRs for current and previous periods
    current_prs = _get_merged_prs_in_range(team, start_date, end_date)
    previous_prs = _get_merged_prs_in_range(team, previous_start, previous_end)

    # Calculate weeks in current period for throughput normalization
    weeks_in_period = max(period_length / 7.0, 1.0)

    # Aggregate all PR metrics in a single query per period (reduces 4 queries to 1)
    current_stats = current_prs.aggregate(
        pr_count=Count("id"),
        avg_cycle_time=Avg("cycle_time_hours"),
        revert_count=Count("id", filter=Q(is_revert=True)),
        ai_assisted_count=Count("id", filter=Q(is_ai_assisted=True)),
    )
    previous_stats = previous_prs.aggregate(
        pr_count=Count("id"),
        avg_cycle_time=Avg("cycle_time_hours"),
        revert_count=Count("id", filter=Q(is_revert=True)),
        ai_assisted_count=Count("id", filter=Q(is_ai_assisted=True)),
    )

    current_pr_count = current_stats["pr_count"]
    previous_pr_count = previous_stats["pr_count"]

    # --- Throughput ---
    throughput_value = current_pr_count / weeks_in_period
    throughput_status = _get_status_higher_is_better(
        throughput_value, THROUGHPUT_GREEN_THRESHOLD, THROUGHPUT_YELLOW_THRESHOLD
    )
    throughput_trend = _calculate_trend(current_pr_count, previous_pr_count)

    # --- Cycle Time ---
    current_cycle_time = current_stats["avg_cycle_time"]
    previous_cycle_time = previous_stats["avg_cycle_time"]
    cycle_time_value = float(current_cycle_time) if current_cycle_time else 0.0

    cycle_time_status = _get_status_lower_is_better(
        cycle_time_value, CYCLE_TIME_GREEN_THRESHOLD, CYCLE_TIME_YELLOW_THRESHOLD
    )
    cycle_time_trend = _calculate_trend(
        float(current_cycle_time) if current_cycle_time else 0.0,
        float(previous_cycle_time) if previous_cycle_time else 0.0,
    )

    # --- Quality (Revert Rate) ---
    quality_value = _calc_percentage(current_stats["revert_count"], current_pr_count)
    previous_quality_value = _calc_percentage(previous_stats["revert_count"], previous_pr_count)

    quality_status = _get_status_lower_is_better(quality_value, QUALITY_GREEN_THRESHOLD, QUALITY_YELLOW_THRESHOLD)
    quality_trend = _calculate_trend(quality_value, previous_quality_value)

    # --- Review Bottleneck ---
    bottleneck_detected, bottleneck_reviewer = _detect_bottleneck(team, current_prs)
    bottleneck_status = "red" if bottleneck_detected else "green"

    # --- AI Adoption ---
    ai_adoption_value = _calc_percentage(current_stats["ai_assisted_count"], current_pr_count)
    previous_ai_value = _calc_percentage(previous_stats["ai_assisted_count"], previous_pr_count)

    ai_adoption_status = _get_status_higher_is_better(
        ai_adoption_value, AI_ADOPTION_GREEN_THRESHOLD, AI_ADOPTION_YELLOW_THRESHOLD
    )
    ai_adoption_trend = _calculate_trend(ai_adoption_value, previous_ai_value)

    return {
        "throughput": {
            "value": throughput_value,
            "trend": throughput_trend,
            "status": throughput_status,
        },
        "cycle_time": {
            "value": cycle_time_value,
            "trend": cycle_time_trend,
            "status": cycle_time_status,
        },
        "quality": {
            "value": quality_value,
            "trend": quality_trend,
            "status": quality_status,
        },
        "review_bottleneck": {
            "detected": bottleneck_detected,
            "reviewer": bottleneck_reviewer,
            "status": bottleneck_status,
        },
        "ai_adoption": {
            "value": ai_adoption_value,
            "trend": ai_adoption_trend,
            "status": ai_adoption_status,
        },
    }


def _get_status_higher_is_better(value: float, green_threshold: float, yellow_threshold: float) -> str:
    """Determine status for metrics where higher values are better.

    Args:
        value: The metric value
        green_threshold: Value at or above this is green
        yellow_threshold: Value at or above this (but below green) is yellow

    Returns:
        "green", "yellow", or "red"
    """
    if value >= green_threshold:
        return "green"
    elif value >= yellow_threshold:
        return "yellow"
    return "red"


def _get_status_lower_is_better(value: float, green_threshold: float, yellow_threshold: float) -> str:
    """Determine status for metrics where lower values are better.

    Args:
        value: The metric value
        green_threshold: Value at or below this is green
        yellow_threshold: Value at or below this (but above green) is yellow

    Returns:
        "green", "yellow", or "red"
    """
    if value <= green_threshold:
        return "green"
    elif value <= yellow_threshold:
        return "yellow"
    return "red"


def _calc_percentage(count: int, total: int) -> float:
    """Calculate percentage, returning 0.0 if total is zero."""
    return (count / total) * 100 if total > 0 else 0.0


def _detect_bottleneck(team: Team, current_prs) -> tuple[bool, str | None]:
    """Detect if there's a review bottleneck (one reviewer doing > 50% of reviews).

    Args:
        team: Team instance
        current_prs: QuerySet of merged PRs in current period

    Returns:
        Tuple of (bottleneck_detected, bottleneck_reviewer_name)
    """
    reviews = PRReview.objects.filter(
        team=team,
        pull_request__in=current_prs,
        reviewer__isnull=False,
    )  # noqa: TEAM001 - team in filters

    reviewer_counts = list(
        reviews.values("reviewer", "reviewer__display_name")
        .annotate(review_count=Count("id"))
        .order_by("-review_count")
    )

    total_reviews = sum(r["review_count"] for r in reviewer_counts)

    if total_reviews > 0 and reviewer_counts:
        top_reviewer = reviewer_counts[0]
        top_reviewer_pct = (top_reviewer["review_count"] / total_reviews) * 100
        if top_reviewer_pct > BOTTLENECK_THRESHOLD:
            return True, top_reviewer["reviewer__display_name"]

    return False, None


def _calculate_trend(current: float, previous: float) -> str:
    """Calculate trend based on percentage change.

    Args:
        current: Current period value
        previous: Previous period value

    Returns:
        "up" if current > previous by > 10%
        "down" if current < previous by > 10%
        "stable" if within +/- 10%
    """
    if previous == 0:
        if current > 0:
            return "up"
        return "stable"

    pct_change = ((current - previous) / previous) * 100

    if pct_change > 10:
        return "up"
    elif pct_change < -10:
        return "down"
    else:
        return "stable"
