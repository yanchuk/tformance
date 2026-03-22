"""Shared aggregation functions for public OSS analytics.

Pure functions that compute metrics from PullRequest data. Used by both
the public analytics service layer and the export script.

All functions use Django ORM (.values().annotate()) and never load full
PR objects into memory — they push computation to PostgreSQL.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import (
    Aggregate,
    Avg,
    Case,
    Count,
    F,
    Q,
    Value,
    When,
)
from django.db.models.functions import TruncMonth

from apps.metrics.models import PullRequest

# Constants shared with export script
# Configurable via settings.PUBLIC_MIN_PRS_THRESHOLD (default: 500 for production,
# lower for demo/seeded data where repos have 100-500 merged PRs).
MIN_PRS_THRESHOLD = getattr(settings, "PUBLIC_MIN_PRS_THRESHOLD", 500)
MAX_CYCLE_TIME_HOURS = 200

# Bot accounts to exclude from all public metrics. These are CI/CD bots
# whose automated PRs distort contributor metrics and adoption percentages.
BOT_USERNAMES = frozenset(
    {
        "github-actions",
        "dependabot",
        "renovate",
        "codecov",
        "stale",
        "greenkeeper",
        "snyk-bot",
        "mergify",
    }
)


def _date_bounds(year=None, start_date=None, end_date=None):
    """Normalize year or date range into (start_date, end_date) tuple.

    Used by functions that need raw date bounds for secondary queries
    (PRReview, PRCheckRun) outside the main PullRequest queryset.
    """
    if start_date is not None and end_date is not None:
        return (start_date, end_date)
    if year is None:
        from django.utils import timezone

        year = timezone.now().year
    return (datetime(year, 1, 1, tzinfo=UTC), datetime(year + 1, 1, 1, tzinfo=UTC))


def _data_window(team_id, months=12):
    """Compute rolling date window anchored to a team's most recent PR.

    Returns (start_date, end_date) spanning ``months`` months back from
    the latest merged PR. This ensures charts show all available data
    even when it spans calendar year boundaries (e.g., Jul 2025 -> Feb 2026).
    """
    from django.utils import timezone

    latest = (
        PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
            team_id=team_id,
            state="merged",
            merged_at__isnull=False,
        )
        .order_by("-merged_at")
        .values_list("merged_at", flat=True)
        .first()
    )

    end_date = timezone.now() if latest is None else latest + timedelta(days=1)

    # Go back `months` months, snap to first of month
    year = end_date.year
    month = end_date.month - months
    while month <= 0:
        month += 12
        year -= 1
    start_date = datetime(year, month, 1, tzinfo=UTC)

    return (start_date, end_date)


class PercentileCont(Aggregate):
    """PostgreSQL PERCENTILE_CONT ordered-set aggregate function.

    Usage: PercentileCont(0.5, 'cycle_time_hours') for median.
    Generates: PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cycle_time_hours)

    Must extend Aggregate (not Func) because PERCENTILE_CONT operates
    on a group of rows, not individual rows.
    """

    function = "PERCENTILE_CONT"
    template = "%(function)s(%(percentile)s) WITHIN GROUP (ORDER BY %(expressions)s)"

    def __init__(self, percentile, expression, **kwargs):
        super().__init__(expression, percentile=percentile, **kwargs)


def _base_pr_queryset(team_id, year=None, start_date=None, end_date=None, github_repo=None):
    """Base queryset for merged PRs with date filtering and bot exclusion.

    Args:
        team_id: Team ID to filter by.
        year: Year to filter PRs (calendar year bounds).
        start_date: Start datetime for rolling window. Takes precedence over year.
        end_date: End datetime for rolling window. Used with start_date.
        github_repo: Optional owner/repo string to filter by specific repository.

    Returns:
        Filtered PullRequest queryset (bots excluded).
    """
    qs = PullRequest.objects.filter(  # noqa: TEAM001 - intentionally cross-team for public analytics
        team_id=team_id,
        state="merged",
    ).exclude(Q(author__github_username__endswith="[bot]") | Q(author__github_username__in=BOT_USERNAMES))

    if github_repo:
        qs = qs.filter(github_repo=github_repo)

    if start_date is not None:
        qs = qs.filter(pr_created_at__gte=start_date)
        if end_date is not None:
            qs = qs.filter(pr_created_at__lt=end_date)
    elif year is not None:
        qs = qs.filter(
            pr_created_at__gte=datetime(year, 1, 1, tzinfo=UTC),
            pr_created_at__lt=datetime(year + 1, 1, 1, tzinfo=UTC),
        )
    else:
        from django.utils import timezone

        year = timezone.now().year
        qs = qs.filter(
            pr_created_at__gte=datetime(year, 1, 1, tzinfo=UTC),
            pr_created_at__lt=datetime(year + 1, 1, 1, tzinfo=UTC),
        )

    return qs


def compute_team_summary(team_id, year=None, start_date=None, end_date=None, github_repo=None):
    """Compute summary metrics for a team.

    Args:
        team_id: Team ID.
        year: Year to aggregate (defaults to current year).
        start_date: Start datetime for rolling window. Takes precedence over year.
        end_date: End datetime for rolling window.
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        Dict with total_prs, ai_prs, ai_pct, median_cycle_time_hours,
        median_review_time_hours, active_contributors_90d.
    """
    qs = _base_pr_queryset(team_id, year=year, start_date=start_date, end_date=end_date, github_repo=github_repo)

    # Basic counts and averages via ORM
    stats = qs.aggregate(
        total_prs=Count("id"),
        ai_prs=Count("id", filter=Q(is_ai_assisted=True)),
    )

    total_prs = stats["total_prs"]
    ai_prs = stats["ai_prs"]
    ai_pct = Decimal(str(round(ai_prs * 100.0 / total_prs, 2))) if total_prs > 0 else Decimal("0")

    # Median cycle time and review time via PostgreSQL percentile_cont
    # Filter outliers for cycle time calculation
    filtered_qs = qs.filter(cycle_time_hours__lte=MAX_CYCLE_TIME_HOURS)
    medians = filtered_qs.aggregate(
        median_cycle=PercentileCont(0.5, F("cycle_time_hours")),
        median_review=PercentileCont(0.5, F("review_time_hours")),
    )

    median_cycle = (
        Decimal(str(round(float(medians["median_cycle"]), 2))) if medians["median_cycle"] is not None else Decimal("0")
    )
    median_review = (
        Decimal(str(round(float(medians["median_review"]), 2)))
        if medians["median_review"] is not None
        else Decimal("0")
    )

    # Active contributors in the last 90 days of the data period
    from django.utils import timezone

    now = timezone.now()
    if start_date is not None and end_date is not None:
        # Rolling window: 90/30 days back from end of window
        ninety_days_ago = end_date - timedelta(days=90)
        thirty_days_ago = end_date - timedelta(days=30)
    elif year and year < now.year:
        # Historical: last 90/30 days of that year
        end_of_year = datetime(year, 12, 31, 23, 59, 59, tzinfo=UTC)
        ninety_days_ago = end_of_year - timedelta(days=90)
        thirty_days_ago = end_of_year - timedelta(days=30)
    else:
        ninety_days_ago = now - timedelta(days=90)
        thirty_days_ago = now - timedelta(days=30)

    active_contributors_90d = (
        qs.filter(pr_created_at__gte=ninety_days_ago).values("author").distinct().exclude(author__isnull=True).count()
    )
    active_contributors_30d = (
        qs.filter(pr_created_at__gte=thirty_days_ago).values("author").distinct().exclude(author__isnull=True).count()
    )

    return {
        "total_prs": total_prs,
        "ai_prs": ai_prs,
        "ai_pct": ai_pct,
        "median_cycle_time_hours": median_cycle,
        "median_review_time_hours": median_review,
        "active_contributors_90d": active_contributors_90d,
        "active_contributors_30d": active_contributors_30d,
    }


def compute_monthly_trends(team_id, year=None, start_date=None, end_date=None, github_repo=None):
    """Compute monthly AI adoption trends for a team.

    Args:
        team_id: Team ID.
        year: Year to aggregate (defaults to current year).
        start_date: Start datetime for rolling window.
        end_date: End datetime for rolling window.
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        List of dicts with month, total_prs, ai_prs, ai_pct.
    """
    qs = _base_pr_queryset(team_id, year=year, start_date=start_date, end_date=end_date, github_repo=github_repo)

    monthly = (
        qs.annotate(month=TruncMonth("pr_created_at"))
        .values("month")
        .annotate(
            total_prs=Count("id"),
            ai_prs=Count("id", filter=Q(is_ai_assisted=True)),
        )
        .order_by("month")
    )

    results = []
    for row in monthly:
        total = row["total_prs"]
        ai = row["ai_prs"]
        pct = round(ai * 100.0 / total, 1) if total > 0 else 0
        results.append(
            {
                "month": row["month"],
                "total_prs": total,
                "ai_prs": ai,
                "ai_pct": pct,
            }
        )

    return results


def compute_ai_tools_breakdown(team_id, year=None, start_date=None, end_date=None, github_repo=None):
    """Compute AI tool usage breakdown for a team.

    Uses PostgreSQL jsonb_array_elements_text to extract tools from
    llm_summary.ai.tools (preferred) or ai_tools_detected (fallback).

    Args:
        team_id: Team ID.
        year: Year to aggregate (defaults to current year).
        start_date: Start datetime for rolling window.
        end_date: End datetime for rolling window.
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        List of dicts with tool, count, pct — sorted by count descending.
    """
    from django.db import connection

    dt_start, dt_end = _date_bounds(year=year, start_date=start_date, end_date=end_date)

    repo_clause = ""
    params = [team_id, dt_start, dt_end]
    if github_repo:
        repo_clause = "AND pr.github_repo = %s"
        params.append(github_repo)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                tool,
                COUNT(*) as count
            FROM metrics_pullrequest pr
            CROSS JOIN LATERAL jsonb_array_elements_text(
                COALESCE(llm_summary->'ai'->'tools', ai_tools_detected)
            ) as tool
            WHERE pr.team_id = %s
            AND pr.state = 'merged'
            AND pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            {repo_clause}
            AND (
                (pr.llm_summary IS NOT NULL AND jsonb_array_length(pr.llm_summary->'ai'->'tools') > 0)
                OR (pr.ai_tools_detected IS NOT NULL AND jsonb_array_length(pr.ai_tools_detected) > 0)
            )
            GROUP BY tool
            ORDER BY count DESC
            LIMIT 10
            """,
            params,
        )
        rows = cursor.fetchall()

    total = sum(count for _, count in rows)
    return [
        {
            "tool": tool,
            "count": count,
            "pct": round(count * 100.0 / total, 1) if total > 0 else 0,
        }
        for tool, count in rows
    ]


def compute_industry_stats(industry, year=None):
    """Compute aggregate metrics for all public teams in an industry.

    Args:
        industry: Industry key (e.g., "analytics").
        year: Year to aggregate (defaults to current year).

    Returns:
        Dict with org_count, total_prs, avg_ai_pct, avg_cycle_time, avg_review_time.
    """
    from apps.public.models import PublicOrgProfile, PublicOrgStats

    profiles = PublicOrgProfile.objects.filter(
        industry=industry,
        is_public=True,
    ).select_related("stats")

    stats_list = []
    for profile in profiles:
        try:
            stats = profile.stats
            if stats.total_prs >= MIN_PRS_THRESHOLD:
                stats_list.append(stats)
        except PublicOrgStats.DoesNotExist:
            continue

    if not stats_list:
        return {
            "org_count": 0,
            "total_prs": 0,
            "avg_ai_pct": Decimal("0"),
            "avg_cycle_time": Decimal("0"),
            "avg_review_time": Decimal("0"),
        }

    total_prs = sum(s.total_prs for s in stats_list)
    avg_ai_pct = Decimal(str(round(sum(float(s.ai_assisted_pct) for s in stats_list) / len(stats_list), 2)))
    avg_cycle = Decimal(str(round(sum(float(s.median_cycle_time_hours) for s in stats_list) / len(stats_list), 2)))
    avg_review = Decimal(str(round(sum(float(s.median_review_time_hours) for s in stats_list) / len(stats_list), 2)))

    return {
        "org_count": len(stats_list),
        "total_prs": total_prs,
        "avg_ai_pct": avg_ai_pct,
        "avg_cycle_time": avg_cycle,
        "avg_review_time": avg_review,
    }


def compute_monthly_sparklines(team_id, year=None, start_date=None, end_date=None, github_repo=None):
    """Compute monthly sparkline data for 4 key metrics.

    Returns a dict with prs_merged, cycle_time, ai_adoption, and review_time,
    each containing {values: list, change_pct: int, trend: str}.

    Args:
        team_id: Team ID.
        year: Year to aggregate (defaults to current year).
        start_date: Start datetime for rolling window.
        end_date: End datetime for rolling window.
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        Dict with 4 sparkline metric dicts.
    """
    qs = _base_pr_queryset(team_id, year=year, start_date=start_date, end_date=end_date, github_repo=github_repo)

    monthly = (
        qs.annotate(month=TruncMonth("merged_at"))
        .values("month")
        .annotate(
            prs_merged=Count("id"),
            avg_cycle_time=Avg("cycle_time_hours", filter=Q(cycle_time_hours__lte=MAX_CYCLE_TIME_HOURS)),
            total_prs=Count("id"),
            ai_prs=Count("id", filter=Q(is_ai_assisted=True)),
            avg_review_time=Avg("review_time_hours"),
        )
        .order_by("month")
    )

    rows = list(monthly)

    def _sparkline(values):
        if not values or len(values) < 2:
            return {"values": values, "change_pct": 0, "trend": "flat"}
        first = values[0]
        last = values[-1]
        change_pct = round((last - first) / first * 100) if first and first > 0 else 0
        if abs(change_pct) < 1:
            trend = "flat"
        elif change_pct > 0:
            trend = "up"
        else:
            trend = "down"
        return {"values": values, "change_pct": change_pct, "trend": trend}

    return {
        "prs_merged": _sparkline([r["prs_merged"] for r in rows]),
        "cycle_time": _sparkline([round(float(r["avg_cycle_time"]), 1) if r["avg_cycle_time"] else 0 for r in rows]),
        "ai_adoption": _sparkline(
            [round(r["ai_prs"] * 100.0 / r["total_prs"], 1) if r["total_prs"] > 0 else 0 for r in rows]
        ),
        "review_time": _sparkline([round(float(r["avg_review_time"]), 1) if r["avg_review_time"] else 0 for r in rows]),
    }


def compute_monthly_cycle_time(team_id, year=None, start_date=None, end_date=None, github_repo=None):
    """Compute monthly average cycle time trend.

    Args:
        team_id: Team ID.
        year: Year to aggregate (defaults to current year).
        start_date: Start datetime for rolling window.
        end_date: End datetime for rolling window.
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        List of dicts with month (datetime) and avg_cycle_time (float).
    """
    qs = _base_pr_queryset(
        team_id, year=year, start_date=start_date, end_date=end_date, github_repo=github_repo
    ).filter(cycle_time_hours__lte=MAX_CYCLE_TIME_HOURS)

    monthly = (
        qs.annotate(month=TruncMonth("merged_at"))
        .values("month")
        .annotate(avg_cycle_time=Avg("cycle_time_hours"))
        .order_by("month")
    )

    return [
        {
            "month": row["month"],
            "avg_cycle_time": round(float(row["avg_cycle_time"]), 1) if row["avg_cycle_time"] else 0,
        }
        for row in monthly
    ]


def compute_recent_prs(team_id, limit=10, github_repo=None):
    """Fetch recently merged PRs for display.

    Args:
        team_id: Team ID.
        limit: Maximum number of PRs to return.
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        List of dicts with PR display data.
    """
    qs = PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
        team_id=team_id,
        state="merged",
    ).exclude(Q(author__github_username__endswith="[bot]") | Q(author__github_username__in=BOT_USERNAMES))

    if github_repo:
        qs = qs.filter(github_repo=github_repo)

    prs = qs.select_related("author").order_by("-merged_at")[:limit]

    results = []
    for pr in prs:
        results.append(
            {
                "title": pr.title,
                "author_name": pr.author.display_name if pr.author else "Unknown",
                "author_github": pr.author.github_username if pr.author else "",
                "github_repo": pr.github_repo,
                "cycle_time_hours": float(pr.cycle_time_hours) if pr.cycle_time_hours else None,
                "is_ai_assisted": pr.is_ai_assisted,
                "ai_tools": pr.effective_ai_tools,
                "merged_at": pr.merged_at,
                "github_pr_id": pr.github_pr_id,
                "github_url": f"https://github.com/{pr.github_repo}/pull/{pr.github_pr_id}",
            }
        )
    return results


def compute_member_breakdown(team_id, year=None, start_date=None, end_date=None, github_repo=None):
    """Compute per-member metrics breakdown.

    Args:
        team_id: Team ID.
        year: Year to aggregate (defaults to current year).
        start_date: Start datetime for rolling window.
        end_date: End datetime for rolling window.
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        List of dicts with member stats, sorted by prs_merged desc, limit 20.
    """
    from apps.metrics.models import PRReview

    qs = _base_pr_queryset(team_id, year=year, start_date=start_date, end_date=end_date, github_repo=github_repo)

    # Per-author PR stats
    author_stats = (
        qs.filter(author__isnull=False)
        .values("author", "author__display_name", "author__github_username")
        .annotate(
            prs_merged=Count("id"),
            avg_cycle_time=Avg("cycle_time_hours", filter=Q(cycle_time_hours__lte=MAX_CYCLE_TIME_HOURS)),
            ai_count=Count("id", filter=Q(is_ai_assisted=True)),
            total_count=Count("id"),
        )
        .order_by("-prs_merged")[:20]
    )

    # Build a lookup of review counts per reviewer using consistent date bounds
    dt_start, dt_end = _date_bounds(year=year, start_date=start_date, end_date=end_date)
    review_counts = dict(
        PRReview.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
            team_id=team_id,
            pull_request__state="merged",
            pull_request__pr_created_at__gte=dt_start,
            pull_request__pr_created_at__lt=dt_end,
            reviewer__isnull=False,
        )
        .values("reviewer")
        .annotate(reviews_given=Count("id"))
        .values_list("reviewer", "reviews_given")
    )

    results = []
    for row in author_stats:
        total = row["total_count"]
        ai_pct = round(row["ai_count"] * 100.0 / total, 1) if total > 0 else 0
        username = row["author__github_username"]
        results.append(
            {
                "author_id": row["author"],
                "display_name": row["author__display_name"],
                "github_username": username,
                "avatar_url": f"https://github.com/{username}.png?size=40" if username else "",
                "prs_merged": row["prs_merged"],
                "avg_cycle_time": round(float(row["avg_cycle_time"]), 1) if row["avg_cycle_time"] else 0,
                "ai_pct": ai_pct,
                "reviews_given": review_counts.get(row["author"], 0),
            }
        )
    return results


def compute_quality_indicators(team_id, year=None, start_date=None, end_date=None, github_repo=None):
    """Compute quality indicator metrics.

    Args:
        team_id: Team ID.
        year: Year to aggregate (defaults to current year).
        start_date: Start datetime for rolling window.
        end_date: End datetime for rolling window.
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        Dict with revert_rate, hotfix_rate, ci_pass_rate, avg_review_rounds.
    """
    from apps.metrics.models import PRCheckRun

    qs = _base_pr_queryset(team_id, year=year, start_date=start_date, end_date=end_date, github_repo=github_repo)

    stats = qs.aggregate(
        total=Count("id"),
        reverts=Count("id", filter=Q(is_revert=True)),
        hotfixes=Count("id", filter=Q(is_hotfix=True)),
        avg_review_rounds=Avg("review_rounds"),
    )

    total = stats["total"]
    revert_rate = round(stats["reverts"] * 100.0 / total, 1) if total > 0 else 0
    hotfix_rate = round(stats["hotfixes"] * 100.0 / total, 1) if total > 0 else 0
    avg_review_rounds = round(float(stats["avg_review_rounds"]), 1) if stats["avg_review_rounds"] else 0

    # CI pass rate from PRCheckRun using consistent date bounds
    dt_start, dt_end = _date_bounds(year=year, start_date=start_date, end_date=end_date)
    check_stats = PRCheckRun.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
        team_id=team_id,
        pull_request__state="merged",
        pull_request__pr_created_at__gte=dt_start,
        pull_request__pr_created_at__lt=dt_end,
        status="completed",
    ).aggregate(
        ci_total=Count("id"),
        ci_success=Count("id", filter=Q(conclusion="success")),
    )

    ci_total = check_stats["ci_total"]
    ci_pass_rate = round(check_stats["ci_success"] * 100.0 / ci_total, 1) if ci_total > 0 else 0

    return {
        "revert_rate": revert_rate,
        "hotfix_rate": hotfix_rate,
        "ci_pass_rate": ci_pass_rate,
        "avg_review_rounds": avg_review_rounds,
    }


def compute_review_distribution(team_id, year=None, start_date=None, end_date=None):
    """Compute review activity distribution across reviewers.

    Args:
        team_id: Team ID.
        year: Year to aggregate (defaults to current year).
        start_date: Start datetime for rolling window.
        end_date: End datetime for rolling window.

    Returns:
        List of dicts with reviewer stats, sorted by reviews_given desc, limit 15.
    """
    from apps.metrics.models import PRReview

    dt_start, dt_end = _date_bounds(year=year, start_date=start_date, end_date=end_date)

    reviewer_stats = (
        PRReview.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
            team_id=team_id,
            pull_request__state="merged",
            pull_request__pr_created_at__gte=dt_start,
            pull_request__pr_created_at__lt=dt_end,
            reviewer__isnull=False,
        )
        .values("reviewer", "reviewer__display_name", "reviewer__github_username")
        .annotate(
            reviews_given=Count("id"),
            approvals=Count("id", filter=Q(state="approved")),
            total=Count("id"),
        )
        .order_by("-reviews_given")[:15]
    )

    results = []
    for row in reviewer_stats:
        total = row["total"]
        approval_rate = round(row["approvals"] * 100.0 / total, 1) if total > 0 else 0
        results.append(
            {
                "reviewer_id": row["reviewer"],
                "display_name": row["reviewer__display_name"],
                "github_username": row["reviewer__github_username"],
                "reviews_given": row["reviews_given"],
                "approval_rate": approval_rate,
            }
        )
    return results


def compute_repos_analyzed(team_id, start_date=None, end_date=None):
    """Compute list of tracked repositories with merged PR counts.

    Args:
        team_id: Team ID.
        start_date: Start datetime for rolling window (optional).
        end_date: End datetime for rolling window (optional).

    Returns:
        List of dicts with repo name, PR count, and GitHub URL,
        sorted by pr_count descending. Excludes bot PRs.
    """
    qs = PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
        team_id=team_id,
        state="merged",
    ).exclude(Q(author__github_username__endswith="[bot]") | Q(author__github_username__in=BOT_USERNAMES))

    if start_date is not None:
        qs = qs.filter(pr_created_at__gte=start_date)
        if end_date is not None:
            qs = qs.filter(pr_created_at__lt=end_date)

    repo_stats = qs.values("github_repo").annotate(pr_count=Count("id")).order_by("-pr_count")

    return [
        {
            "repo": row["github_repo"],
            "pr_count": row["pr_count"],
            "github_url": f"https://github.com/{row['github_repo']}",
        }
        for row in repo_stats
    ]


# PR size bucket boundaries (inclusive upper bound for each bucket)
_SIZE_BUCKETS = [
    ("XS", 1, 50),
    ("S", 51, 200),
    ("M", 201, 500),
    ("L", 501, 1000),
    ("XL", 1001, None),  # No upper bound
]


def compute_pr_size_distribution(team_id, start_date=None, end_date=None, github_repo=None):
    """Compute PR size distribution across 5 buckets for a doughnut chart.

    Buckets: XS (1-50), S (51-200), M (201-500), L (501-1000), XL (1000+)
    Size = additions + deletions.

    Args:
        team_id: Team ID.
        start_date: Start datetime for rolling window (optional).
        end_date: End datetime for rolling window (optional).
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        List of dicts with bucket, count, pct — always 5 entries in order.
    """
    qs = _base_pr_queryset(team_id, start_date=start_date, end_date=end_date, github_repo=github_repo)

    # Annotate each PR with its size bucket using Case/When
    size_expr = F("additions") + F("deletions")
    bucket_annotation = Case(
        When(condition=Q(**{"_size__lte": 50}), then=Value("XS")),
        When(condition=Q(**{"_size__lte": 200}), then=Value("S")),
        When(condition=Q(**{"_size__lte": 500}), then=Value("M")),
        When(condition=Q(**{"_size__lte": 1000}), then=Value("L")),
        default=Value("XL"),
    )

    counts = (
        qs.annotate(_size=size_expr).annotate(bucket=bucket_annotation).values("bucket").annotate(count=Count("id"))
    )

    # Build lookup from DB results
    count_by_bucket = {row["bucket"]: row["count"] for row in counts}
    total = sum(count_by_bucket.values())

    # Always return all 5 buckets in order
    result = []
    for label, _low, _high in _SIZE_BUCKETS:
        count = count_by_bucket.get(label, 0)
        pct = round(count * 100.0 / total, 1) if total > 0 else 0
        result.append({"bucket": label, "count": count, "pct": pct})

    return result


def compute_tech_category_trends(team_id, start_date=None, end_date=None, github_repo=None):
    """Compute monthly technology category trends.

    Uses effective_tech_categories property (LLM → file annotations fallback).
    PRs without categories are skipped.

    Args:
        team_id: Team ID.
        start_date: Start datetime for rolling window (optional).
        end_date: End datetime for rolling window (optional).
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        List of dicts with month (datetime) and categories (dict of name→count),
        sorted chronologically.
    """
    qs = _base_pr_queryset(team_id, start_date=start_date, end_date=end_date, github_repo=github_repo)
    prs = qs.only("pr_created_at", "llm_summary")

    # Group by month in Python (effective_tech_categories is a @property)
    from collections import defaultdict

    monthly = defaultdict(lambda: defaultdict(int))

    for pr in prs:
        cats = pr.effective_tech_categories
        if not cats:
            continue
        month_key = pr.pr_created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for cat in cats:
            monthly[month_key][cat] += 1

    return [{"month": month, "categories": dict(cats)} for month, cats in sorted(monthly.items())]


def compute_pr_type_trends(team_id, start_date=None, end_date=None, github_repo=None):
    """Compute monthly PR type distribution trends.

    Uses effective_pr_type property (LLM → labels fallback → 'unknown').

    Args:
        team_id: Team ID.
        start_date: Start datetime for rolling window (optional).
        end_date: End datetime for rolling window (optional).
        github_repo: Optional owner/repo string for repo-level filtering.

    Returns:
        List of dicts with month (datetime) and types (dict of type→count),
        sorted chronologically.
    """
    qs = _base_pr_queryset(team_id, start_date=start_date, end_date=end_date, github_repo=github_repo)
    prs = qs.only("pr_created_at", "llm_summary", "labels")

    from collections import defaultdict

    monthly = defaultdict(lambda: defaultdict(int))

    for pr in prs:
        pr_type = pr.effective_pr_type
        month_key = pr.pr_created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly[month_key][pr_type] += 1

    return [{"month": month, "types": dict(types)} for month, types in sorted(monthly.items())]
