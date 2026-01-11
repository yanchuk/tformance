"""Copilot-related metrics for dashboard.

Functions for GitHub Copilot usage metrics and trends.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

from apps.metrics.models import AIUsageDaily, PullRequest
from apps.teams.models import Team


def get_copilot_metrics(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get Copilot metrics summary for a team within a date range.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository filter (not applicable - Copilot data is not repo-specific)

    Returns:
        dict with keys:
            - total_suggestions (int): Total suggestions shown
            - total_accepted (int): Total suggestions accepted
            - acceptance_rate (Decimal): Acceptance rate percentage (0.00 to 100.00)
            - active_users (int): Count of distinct members using Copilot

    Note:
        repo parameter is accepted for API consistency but has no effect since
        Copilot usage is tracked at the member level, not per-repository.
    """
    # Note: AIUsageDaily doesn't have repo field - Copilot data is not repo-specific
    copilot_usage = AIUsageDaily.objects.filter(
        team=team,
        source="copilot",
        date__gte=start_date,
        date__lte=end_date,
    )

    # Aggregate totals
    stats = copilot_usage.aggregate(
        total_suggestions=Sum("suggestions_shown"),
        total_accepted=Sum("suggestions_accepted"),
        active_users=Count("member", distinct=True),
    )

    total_suggestions = stats["total_suggestions"] or 0
    total_accepted = stats["total_accepted"] or 0
    active_users = stats["active_users"] or 0

    # Calculate acceptance rate
    if total_suggestions > 0:
        acceptance_rate = Decimal(str(round((total_accepted / total_suggestions) * 100, 2)))
    else:
        acceptance_rate = Decimal("0.00")

    return {
        "total_suggestions": total_suggestions,
        "total_accepted": total_accepted,
        "acceptance_rate": acceptance_rate,
        "active_users": active_users,
    }


def get_copilot_trend(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get Copilot acceptance rate trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository filter (not applicable - Copilot data is not repo-specific)

    Returns:
        list of dicts with keys:
            - week (date): Week start date
            - acceptance_rate (Decimal): Acceptance rate percentage for that week

    Note:
        repo parameter is accepted for API consistency but has no effect since
        Copilot usage is tracked at the member level, not per-repository.
    """
    # Note: AIUsageDaily doesn't have repo field - Copilot data is not repo-specific
    copilot_usage = AIUsageDaily.objects.filter(
        team=team,
        source="copilot",
        date__gte=start_date,
        date__lte=end_date,
    )

    # Group by week and calculate acceptance rate
    weekly_data = (
        copilot_usage.annotate(week=TruncWeek("date"))
        .values("week")
        .annotate(
            total_suggestions=Sum("suggestions_shown"),
            total_accepted=Sum("suggestions_accepted"),
        )
        .order_by("week")
    )

    result = []
    for entry in weekly_data:
        total_suggestions = entry["total_suggestions"] or 0
        total_accepted = entry["total_accepted"] or 0

        if total_suggestions > 0:
            acceptance_rate = Decimal(str(round((total_accepted / total_suggestions) * 100, 2)))
        else:
            acceptance_rate = Decimal("0.00")

        result.append(
            {
                "week": entry["week"],
                "acceptance_rate": acceptance_rate,
            }
        )

    return result


def get_monthly_copilot_acceptance_trend(
    team: Team, start_date: date, end_date: date, repo: str | None = None
) -> list[dict]:
    """Get Copilot acceptance rate trend by month.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository filter (not applicable - Copilot data is not repo-specific)

    Returns:
        list of dicts with keys:
            - month (str): Month in "YYYY-MM" format
            - value (float): Acceptance rate percentage for that month

    Note:
        repo parameter is accepted for API consistency but has no effect since
        Copilot usage is tracked at the member level, not per-repository.
    """
    copilot_usage = AIUsageDaily.objects.filter(
        team=team,
        source="copilot",
        date__gte=start_date,
        date__lte=end_date,
    )

    monthly_data = (
        copilot_usage.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(
            total_suggestions=Sum("suggestions_shown"),
            total_accepted=Sum("suggestions_accepted"),
        )
        .order_by("month")
    )

    result = []
    for entry in monthly_data:
        total_suggestions = entry["total_suggestions"] or 0
        total_accepted = entry["total_accepted"] or 0

        rate = round(total_accepted / total_suggestions * 100, 2) if total_suggestions > 0 else 0.0

        result.append(
            {
                "month": entry["month"].strftime("%Y-%m"),
                "value": rate,
            }
        )

    return result


def get_weekly_copilot_acceptance_trend(
    team: Team, start_date: date, end_date: date, repo: str | None = None
) -> list[dict]:
    """Get Copilot acceptance rate trend by week in Trends-compatible format.

    This is a wrapper around get_copilot_trend() that returns data in the
    format expected by the Trends tab ({week: "YYYY-MM-DD", value: float}).

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository filter (not applicable - Copilot data is not repo-specific)

    Returns:
        list of dicts with keys:
            - week (str): Week start date in "YYYY-MM-DD" format
            - value (float): Acceptance rate percentage for that week

    Note:
        repo parameter is accepted for API consistency but has no effect since
        Copilot usage is tracked at the member level, not per-repository.
    """
    raw_data = get_copilot_trend(team, start_date, end_date, repo)

    return [
        {
            "week": entry["week"].strftime("%Y-%m-%d"),
            "value": float(entry["acceptance_rate"]),
        }
        for entry in raw_data
    ]


def get_copilot_delivery_comparison(team: Team, start_date: date, end_date: date) -> dict:
    """Compare delivery metrics between Copilot and non-Copilot users.

    Categorizes PRs by whether their author has recent Copilot activity
    (activity within the last 30 days) and compares average cycle time
    and review time between the two groups.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        dict with keys:
            - copilot_prs: dict with count, avg_cycle_time_hours, avg_review_time_hours
            - non_copilot_prs: dict with count, avg_cycle_time_hours, avg_review_time_hours
            - improvement: dict with cycle_time_percent, review_time_percent
            - sample_sufficient: bool (True if both groups have >= 10 PRs)
    """
    # Convert dates to datetime for filtering
    start_datetime = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))
    end_datetime = timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time()))

    # Query merged PRs in date range for team with valid cycle/review times
    prs = PullRequest.objects.filter(
        team=team,
        state="merged",
        pr_created_at__gte=start_datetime,
        pr_created_at__lte=end_datetime,
        cycle_time_hours__isnull=False,
        review_time_hours__isnull=False,
    ).select_related("author")

    # Separate PRs into copilot and non-copilot groups based on author's recent activity
    copilot_prs_data = []
    non_copilot_prs_data = []

    for pr in prs:
        if pr.author and pr.author.has_recent_copilot_activity:
            copilot_prs_data.append(pr)
        else:
            non_copilot_prs_data.append(pr)

    # Calculate averages for copilot users
    copilot_count = len(copilot_prs_data)
    if copilot_count > 0:
        copilot_avg_cycle = sum(pr.cycle_time_hours for pr in copilot_prs_data) / copilot_count
        copilot_avg_review = sum(pr.review_time_hours for pr in copilot_prs_data) / copilot_count
    else:
        copilot_avg_cycle = Decimal("0.00")
        copilot_avg_review = Decimal("0.00")

    # Calculate averages for non-copilot users
    non_copilot_count = len(non_copilot_prs_data)
    if non_copilot_count > 0:
        non_copilot_avg_cycle = sum(pr.cycle_time_hours for pr in non_copilot_prs_data) / non_copilot_count
        non_copilot_avg_review = sum(pr.review_time_hours for pr in non_copilot_prs_data) / non_copilot_count
    else:
        non_copilot_avg_cycle = Decimal("0.00")
        non_copilot_avg_review = Decimal("0.00")

    # Calculate improvement percentages
    # Improvement = (copilot - non_copilot) / non_copilot * 100
    # Negative means copilot is faster (better)
    if non_copilot_avg_cycle > 0:
        cycle_time_improvement = int(((copilot_avg_cycle - non_copilot_avg_cycle) / non_copilot_avg_cycle) * 100)
    else:
        cycle_time_improvement = 0

    if non_copilot_avg_review > 0:
        review_time_improvement = int(((copilot_avg_review - non_copilot_avg_review) / non_copilot_avg_review) * 100)
    else:
        review_time_improvement = 0

    # Sample is sufficient if both groups have >= 10 PRs
    sample_sufficient = copilot_count >= 10 and non_copilot_count >= 10

    return {
        "copilot_prs": {
            "count": copilot_count,
            "avg_cycle_time_hours": Decimal(str(round(copilot_avg_cycle, 2))),
            "avg_review_time_hours": Decimal(str(round(copilot_avg_review, 2))),
        },
        "non_copilot_prs": {
            "count": non_copilot_count,
            "avg_cycle_time_hours": Decimal(str(round(non_copilot_avg_cycle, 2))),
            "avg_review_time_hours": Decimal(str(round(non_copilot_avg_review, 2))),
        },
        "improvement": {
            "cycle_time_percent": cycle_time_improvement,
            "review_time_percent": review_time_improvement,
        },
        "sample_sufficient": sample_sufficient,
    }
