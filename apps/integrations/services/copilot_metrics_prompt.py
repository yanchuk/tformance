"""
Copilot Metrics Service for LLM Prompt Context.

Aggregates Copilot usage data from AIUsageDaily for inclusion
in LLM insight prompts.
"""

from datetime import date

from django.db.models import Avg, Sum
from django.http import HttpRequest

from apps.integrations.services.integration_flags import is_copilot_feature_active
from apps.metrics.models import AIUsageDaily, CopilotSeatSnapshot
from apps.metrics.services.copilot_champions import get_copilot_champions
from apps.metrics.services.dashboard.copilot_metrics import get_copilot_delivery_comparison
from apps.teams.models import Team


def get_copilot_metrics_for_prompt(
    team: Team,
    start_date: date,
    end_date: date,
    request: HttpRequest | None = None,
    include_copilot: bool | None = None,
) -> dict:
    """Get aggregated Copilot metrics for LLM prompt context.

    Aggregates Copilot usage data for the specified team and date range
    to provide context for LLM-generated insights.

    Feature flag gating:
    - When request is provided, checks the `copilot_llm_insights` flag
    - When include_copilot is explicitly set, uses that value (for Celery tasks)
    - When neither is provided, defaults to excluding Copilot metrics

    Args:
        team: The team to get metrics for.
        start_date: Start date of the period (inclusive).
        end_date: End date of the period (inclusive).
        request: Optional HTTP request for feature flag checking.
        include_copilot: Optional explicit override (for Celery tasks without request context).

    Returns:
        Dictionary with Copilot metrics, or empty dict if flag disabled/no data:
        {
            "active_users": int,  # Users with suggestions > 0
            "inactive_count": int,  # Users with usage records but 0 suggestions
            "avg_acceptance_rate": float,  # Average acceptance rate %
            "total_suggestions": int,  # Total suggestions shown
            "total_acceptances": int,  # Total suggestions accepted
            "top_users": list[dict],  # Top users by usage
            "seat_data": dict | None,  # Seat utilization from latest snapshot
            "delivery_impact": dict | None,  # Delivery comparison between Copilot/non-Copilot users
        }
    """
    # Check feature flag
    if include_copilot is not None:
        # Explicit override takes precedence
        if not include_copilot:
            return {}
    elif request is not None:
        # Check flag using request
        if not is_copilot_feature_active(request, "copilot_llm_insights"):
            return {}
    else:
        # No request and no explicit override - default to excluding Copilot
        return {}
    # Query Copilot usage within date range
    usage_qs = AIUsageDaily.objects.filter(
        team=team,
        source="copilot",
        date__gte=start_date,
        date__lte=end_date,
    )

    if not usage_qs.exists():
        return {}

    # Get totals
    totals = usage_qs.aggregate(
        total_suggestions=Sum("suggestions_shown"),
        total_acceptances=Sum("suggestions_accepted"),
    )

    # Count active users (with suggestions > 0)
    active_users = usage_qs.filter(suggestions_shown__gt=0).values("member_id").distinct().count()

    # Count inactive users (have records but 0 suggestions)
    inactive_count = usage_qs.filter(suggestions_shown=0).values("member_id").distinct().count()

    # Calculate average acceptance rate from users with activity
    active_usage = usage_qs.filter(suggestions_shown__gt=0)
    avg_rate_result = active_usage.aggregate(avg_rate=Avg("acceptance_rate"))
    avg_acceptance_rate = float(avg_rate_result["avg_rate"] or 0)

    # Get top users by total suggestions
    top_users_qs = (
        usage_qs.filter(suggestions_shown__gt=0)
        .values("member_id", "member__display_name")
        .annotate(
            total_suggestions=Sum("suggestions_shown"),
            total_acceptances=Sum("suggestions_accepted"),
        )
        .order_by("-total_suggestions")[:5]
    )

    top_users = [
        {
            "name": user["member__display_name"],
            "suggestions": user["total_suggestions"],
            "acceptances": user["total_acceptances"],
        }
        for user in top_users_qs
    ]

    # Get seat data from latest CopilotSeatSnapshot
    seat_data = _get_seat_data(team)

    # Get delivery impact comparison
    delivery_impact = _get_delivery_impact(team, start_date, end_date)

    # Get Copilot champions (potential mentors)
    champions = _get_champions_for_prompt(team, start_date, end_date)

    return {
        "active_users": active_users,
        "inactive_count": inactive_count,
        "avg_acceptance_rate": avg_acceptance_rate,
        "total_suggestions": totals["total_suggestions"] or 0,
        "total_acceptances": totals["total_acceptances"] or 0,
        "top_users": top_users,
        "seat_data": seat_data,
        "delivery_impact": delivery_impact,
        "champions": champions,
    }


def _get_seat_data(team: Team) -> dict | None:
    """Get seat utilization data from the latest CopilotSeatSnapshot.

    Args:
        team: The team to get seat data for.

    Returns:
        Dictionary with seat data or None if no snapshot exists:
        {
            "total_seats": int,
            "active_seats": int,
            "inactive_seats": int,
            "utilization_rate": Decimal,
            "monthly_cost": Decimal,
            "wasted_spend": Decimal,
            "cost_per_active_user": Decimal | None,
        }
    """
    latest_snapshot = CopilotSeatSnapshot.objects.filter(team=team).order_by("-date").first()

    if not latest_snapshot:
        return None

    return {
        "total_seats": latest_snapshot.total_seats,
        "active_seats": latest_snapshot.active_this_cycle,
        "inactive_seats": latest_snapshot.inactive_this_cycle,
        "utilization_rate": latest_snapshot.utilization_rate,
        "monthly_cost": latest_snapshot.monthly_cost,
        "wasted_spend": latest_snapshot.wasted_spend,
        "cost_per_active_user": latest_snapshot.cost_per_active_user,
    }


def _get_delivery_impact(team: Team, start_date: date, end_date: date) -> dict | None:
    """Get delivery impact comparison between Copilot and non-Copilot users.

    Args:
        team: The team to get delivery impact for.
        start_date: Start date of the period (inclusive).
        end_date: End date of the period (inclusive).

    Returns:
        Dictionary with delivery impact or None if no PR data:
        {
            "copilot_prs_count": int,
            "non_copilot_prs_count": int,
            "cycle_time_improvement_percent": int,
            "review_time_improvement_percent": int,
            "sample_sufficient": bool,
        }
    """
    comparison = get_copilot_delivery_comparison(team, start_date, end_date)

    # Return None if no PR data exists
    copilot_count = comparison["copilot_prs"]["count"]
    non_copilot_count = comparison["non_copilot_prs"]["count"]

    if copilot_count == 0 and non_copilot_count == 0:
        return None

    return {
        "copilot_prs_count": copilot_count,
        "non_copilot_prs_count": non_copilot_count,
        "cycle_time_improvement_percent": comparison["improvement"]["cycle_time_percent"],
        "review_time_improvement_percent": comparison["improvement"]["review_time_percent"],
        "sample_sufficient": comparison["sample_sufficient"],
    }


def _get_champions_for_prompt(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get Copilot champions formatted for LLM prompt context.

    Returns simplified champion data for inclusion in prompts.

    Args:
        team: The team to get champions for.
        start_date: Start date of the period (inclusive).
        end_date: End date of the period (inclusive).

    Returns:
        List of champion dictionaries:
        [
            {
                "name": str,           # Display name
                "github_username": str,
                "acceptance_rate": float,
                "prs_merged": int,
                "avg_cycle_time": float,
            },
            ...
        ]
    """
    champions = get_copilot_champions(team, start_date, end_date, top_n=3)

    return [
        {
            "name": c["display_name"],
            "github_username": c["github_username"],
            "acceptance_rate": c["stats"]["acceptance_rate"],
            "prs_merged": c["stats"]["prs_merged"],
            "avg_cycle_time": c["stats"]["avg_cycle_time_hours"],
        }
        for c in champions
    ]
