"""Copilot-related metrics for dashboard.

Functions for GitHub Copilot usage metrics and trends.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncWeek

from apps.metrics.models import AIUsageDaily
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
