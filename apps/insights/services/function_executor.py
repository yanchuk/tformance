"""
Function executor for Gemini function calls.

Executes the functions requested by Gemini based on user questions.
Maps Gemini function calls to the dashboard service functions.
"""

import logging
from datetime import date, timedelta
from typing import Any

from apps.metrics.services import dashboard_service

logger = logging.getLogger(__name__)

# Maximum lookback periods
MAX_DAYS_DEFAULT = 90
MAX_DAYS_RECENT = 30
MAX_LIMIT = 20


def execute_function(
    function_name: str,
    arguments: dict[str, Any],
    team,
) -> dict[str, Any]:
    """Execute a Gemini function call.

    Args:
        function_name: The name of the function to execute.
        arguments: The arguments passed by Gemini.
        team: The team to query data for.

    Returns:
        Dictionary containing the function result.

    Raises:
        ValueError: If the function name is not recognized.
    """
    executor = FUNCTION_EXECUTORS.get(function_name)
    if not executor:
        raise ValueError(f"Unknown function: {function_name}")

    return executor(arguments, team)


def _get_date_range(days: int, max_days: int = MAX_DAYS_DEFAULT) -> tuple[date, date]:
    """Calculate date range from days parameter.

    Args:
        days: Number of days to look back.
        max_days: Maximum allowed days.

    Returns:
        Tuple of (start_date, end_date).
    """
    days = min(max(1, days), max_days)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def _execute_get_team_metrics(arguments: dict[str, Any], team) -> dict[str, Any]:
    """Execute get_team_metrics function."""
    days = arguments.get("days", 30)
    start_date, end_date = _get_date_range(days)

    result = dashboard_service.get_key_metrics(team, start_date, end_date)

    # Convert Decimal values to float for JSON serialization
    return {
        "period_days": days,
        "total_prs": result.get("total_prs", 0),
        "merged_prs": result.get("merged_prs", 0),
        "merge_rate_percent": float(result.get("merge_rate", 0)),
        "avg_cycle_time_hours": float(result.get("avg_cycle_time", 0)),
        "avg_review_time_hours": float(result.get("avg_review_time", 0)),
        "ai_adoption_percent": float(result.get("ai_adoption", 0)),
    }


def _execute_get_ai_adoption_trend(arguments: dict[str, Any], team) -> dict[str, Any]:
    """Execute get_ai_adoption_trend function."""
    days = arguments.get("days", 30)
    start_date, end_date = _get_date_range(days)

    result = dashboard_service.get_ai_adoption_trend(team, start_date, end_date)

    return {
        "period_days": days,
        "trend": [
            {
                "period": item.get("period", ""),
                "ai_percent": float(item.get("ai_percent", 0)),
                "total_prs": item.get("total_prs", 0),
            }
            for item in result
        ],
    }


def _execute_get_developer_stats(arguments: dict[str, Any], team) -> dict[str, Any]:
    """Execute get_developer_stats function."""
    days = arguments.get("days", 30)
    developer_name = arguments.get("developer_name")
    start_date, end_date = _get_date_range(days)

    result = dashboard_service.get_team_breakdown(team, start_date, end_date)

    # Filter to specific developer if requested
    if developer_name:
        developer_name_lower = developer_name.lower()
        result = [item for item in result if developer_name_lower in item.get("author", "").lower()]

    return {
        "period_days": days,
        "developers": [
            {
                "name": item.get("author", "Unknown"),
                "pr_count": item.get("pr_count", 0),
                "avg_cycle_time_hours": float(item.get("avg_cycle_time", 0)),
                "ai_adoption_percent": float(item.get("ai_percent", 0)),
                "lines_added": item.get("lines_added", 0),
                "lines_deleted": item.get("lines_deleted", 0),
            }
            for item in result
        ],
    }


def _execute_get_ai_quality_comparison(arguments: dict[str, Any], team) -> dict[str, Any]:
    """Execute get_ai_quality_comparison function."""
    days = arguments.get("days", 30)
    start_date, end_date = _get_date_range(days)

    result = dashboard_service.get_ai_quality_comparison(team, start_date, end_date)

    return {
        "period_days": days,
        "ai_assisted": {
            "pr_count": result.get("ai_prs", 0),
            "avg_cycle_time_hours": float(result.get("ai_cycle_time", 0)),
            "revert_rate_percent": float(result.get("ai_revert_rate", 0)),
        },
        "non_ai": {
            "pr_count": result.get("non_ai_prs", 0),
            "avg_cycle_time_hours": float(result.get("non_ai_cycle_time", 0)),
            "revert_rate_percent": float(result.get("non_ai_revert_rate", 0)),
        },
    }


def _execute_get_reviewer_workload(arguments: dict[str, Any], team) -> dict[str, Any]:
    """Execute get_reviewer_workload function."""
    days = arguments.get("days", 30)
    start_date, end_date = _get_date_range(days)

    result = dashboard_service.get_reviewer_workload(team, start_date, end_date)

    return {
        "period_days": days,
        "reviewers": [
            {
                "name": item.get("reviewer", "Unknown"),
                "review_count": item.get("review_count", 0),
                "avg_review_time_hours": float(item.get("avg_review_time", 0)),
                "approval_rate_percent": float(item.get("approval_rate", 0)),
            }
            for item in result
        ],
    }


def _execute_get_recent_prs(arguments: dict[str, Any], team) -> dict[str, Any]:
    """Execute get_recent_prs function."""
    days = min(arguments.get("days", 7), MAX_DAYS_RECENT)
    limit = min(arguments.get("limit", 10), MAX_LIMIT)
    start_date, end_date = _get_date_range(days, MAX_DAYS_RECENT)

    result = dashboard_service.get_recent_prs(team, start_date, end_date, limit=limit)

    return {
        "period_days": days,
        "pull_requests": [
            {
                "title": item.get("title", ""),
                "author": item.get("author", "Unknown"),
                "state": item.get("state", ""),
                "cycle_time_hours": float(item.get("cycle_time", 0)) if item.get("cycle_time") else None,
                "is_ai_assisted": item.get("is_ai_assisted", False),
                "merged_at": item.get("merged_at").isoformat() if item.get("merged_at") else None,
            }
            for item in result
        ],
    }


# Map function names to their executors
FUNCTION_EXECUTORS = {
    "get_team_metrics": _execute_get_team_metrics,
    "get_ai_adoption_trend": _execute_get_ai_adoption_trend,
    "get_developer_stats": _execute_get_developer_stats,
    "get_ai_quality_comparison": _execute_get_ai_quality_comparison,
    "get_reviewer_workload": _execute_get_reviewer_workload,
    "get_recent_prs": _execute_get_recent_prs,
}
