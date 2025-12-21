"""Service functions for managing insights on the dashboard."""

from apps.metrics.models import DailyInsight


def get_recent_insights(team, limit=5):
    """Get recent non-dismissed insights for a team.

    Args:
        team: Team instance to get insights for
        limit: Maximum number of insights to return (default: 5)

    Returns:
        list of DailyInsight objects ordered by date desc, priority, category
    """
    return list(
        DailyInsight.objects.filter(
            team=team,
            is_dismissed=False,
        ).order_by("-date", "priority", "category")[:limit]
    )
