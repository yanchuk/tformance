"""Trend and time-series metrics for dashboard.

Functions for weekly/monthly trend data, sparklines, and period comparisons.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth, TruncWeek

from apps.metrics.services.dashboard._helpers import (
    _apply_repo_filter,
    _get_merged_prs_in_range,
    _get_metric_trend,
    _get_monthly_metric_trend,
)
from apps.teams.models import Team
from apps.utils.date_utils import end_of_day, start_of_day

# Minimum sample size for sparkline trend calculations (ISS-001/ISS-007)
MIN_SPARKLINE_SAMPLE_SIZE = 3

# Maximum percentage for trend display (A-001)
MAX_TREND_PERCENTAGE = 500


def get_cycle_time_trend(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get cycle time trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - week (str): Week start date in ISO format (YYYY-MM-DD)
            - value (float): Average cycle time in hours for that week
    """
    return _get_metric_trend(team, start_date, end_date, "cycle_time_hours", "avg_cycle_time", repo)


def get_review_time_trend(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get review time trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - week (date): Week start date
            - value (float): Average review time in hours for that week
    """
    return _get_metric_trend(team, start_date, end_date, "review_time_hours", "avg_review_time", repo)


def get_monthly_cycle_time_trend(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get cycle time trend by month.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - month (str): Month in YYYY-MM format
            - value (float): Average cycle time in hours for that month
    """
    return _get_monthly_metric_trend(team, start_date, end_date, "cycle_time_hours", "avg_cycle_time", repo)


def get_monthly_review_time_trend(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get review time trend by month.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - month (str): Month in YYYY-MM format
            - value (float): Average review time in hours for that month
    """
    return _get_monthly_metric_trend(team, start_date, end_date, "review_time_hours", "avg_review_time", repo)


def get_monthly_pr_count(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get PR count by month.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - month (str): Month in YYYY-MM format
            - value (int): Number of merged PRs for that month
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Group by month and count
    monthly_data = (
        prs.annotate(month=TruncMonth("merged_at")).values("month").annotate(count=Count("id")).order_by("month")
    )

    result = []
    for entry in monthly_data:
        month_str = entry["month"].strftime("%Y-%m") if entry["month"] else None
        result.append(
            {
                "month": month_str,
                "value": entry["count"],
            }
        )
    return result


def get_weekly_pr_count(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get PR count by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository filter (owner/repo format)

    Returns:
        list of dicts with keys:
            - week (str): Week in YYYY-WNN format
            - value (int): Number of merged PRs for that week
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Group by week and count
    weekly_data = prs.annotate(week=TruncWeek("merged_at")).values("week").annotate(count=Count("id")).order_by("week")

    result = []
    for entry in weekly_data:
        week_str = entry["week"].strftime("%Y-W%W") if entry["week"] else None
        result.append(
            {
                "week": week_str,
                "value": entry["count"],
            }
        )
    return result


def get_monthly_ai_adoption(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get AI adoption percentage by month.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - month (str): Month in YYYY-MM format
            - value (float): Percentage of AI-assisted PRs (0.0 to 100.0)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Group by month with AI count and total count
    monthly_data = (
        prs.annotate(month=TruncMonth("merged_at"))
        .values("month")
        .annotate(
            total=Count("id"),
            ai_count=Count("id", filter=Q(is_ai_assisted=True)),
        )
        .order_by("month")
    )

    result = []
    for entry in monthly_data:
        month_str = entry["month"].strftime("%Y-%m") if entry["month"] else None
        total = entry["total"]
        ai_count = entry["ai_count"]
        pct = round((ai_count / total) * 100, 2) if total > 0 else 0.0
        result.append(
            {
                "month": month_str,
                "value": pct,
            }
        )
    return result


def get_trend_comparison(
    team: Team,
    metric: str,
    current_start: date,
    current_end: date,
    compare_start: date,
    compare_end: date,
    repo: str | None = None,
) -> dict:
    """Get trend comparison between two periods (e.g., YoY).

    Args:
        team: Team instance
        metric: Metric name (cycle_time, review_time, pr_count, ai_adoption)
        current_start: Start of current period
        current_end: End of current period
        compare_start: Start of comparison period
        compare_end: End of comparison period
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - current: list of monthly data for current period
            - comparison: list of monthly data for comparison period
            - change_pct: Percentage change (current avg vs comparison avg)
    """
    # Get the appropriate function based on metric
    metric_functions = {
        "cycle_time": get_monthly_cycle_time_trend,
        "review_time": get_monthly_review_time_trend,
        "pr_count": get_monthly_pr_count,
        "ai_adoption": get_monthly_ai_adoption,
    }

    func = metric_functions.get(metric, get_monthly_cycle_time_trend)

    current_data = func(team, current_start, current_end, repo=repo)
    compare_data = func(team, compare_start, compare_end, repo=repo)

    # Calculate averages for change percentage
    current_values = [d["value"] for d in current_data if d["value"]]
    compare_values = [d["value"] for d in compare_data if d["value"]]

    current_avg = sum(current_values) / len(current_values) if current_values else 0
    compare_avg = sum(compare_values) / len(compare_values) if compare_values else 0

    # Calculate change percentage
    change_pct = round((current_avg - compare_avg) / compare_avg * 100, 2) if compare_avg > 0 else 0.0

    return {
        "current": current_data,
        "comparison": compare_data,
        "change_pct": change_pct,
    }


def get_sparkline_data(
    team: Team,
    start_date: date,
    end_date: date,
    repo: str | None = None,
    use_survey_data: bool | None = None,
) -> dict:
    """Get sparkline data for key metric cards.

    Returns 12 weeks of data for each metric, along with change percentage
    and trend direction for display in small inline charts.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository filter (owner/repo format)
        use_survey_data: If True, use survey data for AI adoption.
            If False/None, use detection data (effective_is_ai_assisted).

    Returns:
        dict with keys for each metric (prs_merged, cycle_time, ai_adoption, review_time).
        Each metric contains:
            - values (list): List of weekly values (up to 12)
            - change_pct (int): Percentage change from first to last week
            - trend (str): Direction ("up", "down", or "flat")
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Get weekly PR counts
    pr_count_data = (
        prs.annotate(week=TruncWeek("merged_at")).values("week").annotate(count=Count("id")).order_by("week")
    )
    prs_merged_values = [entry["count"] for entry in pr_count_data]

    # Get weekly cycle time averages
    cycle_time_data = (
        prs.annotate(week=TruncWeek("merged_at")).values("week").annotate(avg=Avg("cycle_time_hours")).order_by("week")
    )
    cycle_time_values = [float(entry["avg"]) if entry["avg"] else 0.0 for entry in cycle_time_data]

    # Get weekly AI adoption percentages
    # Default to detection data; use survey data when use_survey_data=True
    use_surveys = use_survey_data if use_survey_data is not None else False

    if use_surveys:
        # Survey-based calculation (ISS-006 fix)
        # Uses PRSurvey.author_ai_assisted
        # Only counts PRs with survey responses (author_ai_assisted is not None)
        ai_adoption_data = (
            prs.annotate(week=TruncWeek("merged_at"))
            .values("week")
            .annotate(
                # Count PRs with surveys that have a response (not None)
                total_with_response=Count(
                    "survey",
                    filter=Q(survey__author_ai_assisted__isnull=False),
                ),
                # Count PRs with surveys saying AI was used
                ai_count=Count(
                    "survey",
                    filter=Q(survey__author_ai_assisted=True),
                ),
            )
            .order_by("week")
        )
        ai_adoption_values = [
            round((entry["ai_count"] / entry["total_with_response"]) * 100, 1)
            if entry["total_with_response"] > 0
            else 0.0
            for entry in ai_adoption_data
        ]
    else:
        # Detection-based calculation (default)
        # Uses effective_is_ai_assisted (LLM > pattern detection)
        # Group PRs by week and calculate AI adoption per week
        weekly_stats = defaultdict(lambda: {"total": 0, "ai_count": 0})

        for pr in prs.select_related("team"):
            if pr.merged_at:
                # Get Monday of the week
                week_start = pr.merged_at.date() - timedelta(days=pr.merged_at.weekday())
                weekly_stats[week_start]["total"] += 1
                if pr.effective_is_ai_assisted:
                    weekly_stats[week_start]["ai_count"] += 1

        # Convert to sorted list of values
        sorted_weeks = sorted(weekly_stats.keys())
        ai_adoption_values = [
            round((weekly_stats[week]["ai_count"] / weekly_stats[week]["total"]) * 100, 1)
            if weekly_stats[week]["total"] > 0
            else 0.0
            for week in sorted_weeks
        ]

    # Get weekly review time averages
    review_time_data = (
        prs.annotate(week=TruncWeek("merged_at")).values("week").annotate(avg=Avg("review_time_hours")).order_by("week")
    )
    review_time_values = [float(entry["avg"]) if entry["avg"] else 0.0 for entry in review_time_data]

    def _calculate_change_and_trend(
        values: list,
        sample_sizes: list | None = None,
        min_sample_size: int = MIN_SPARKLINE_SAMPLE_SIZE,
    ) -> tuple[int, str]:
        """Calculate change percentage and trend direction from values list.

        Args:
            values: List of metric values per week
            sample_sizes: Optional list of PR counts per week (same length as values)
            min_sample_size: Minimum PRs required for a week to be valid (ISS-001/ISS-007)

        Returns:
            Tuple of (change_percentage, trend_direction)
            trend_direction is "up", "down", or "flat"
        """
        if len(values) < 2:
            return 0, "flat"

        # Find first valid week (>= min_sample_size PRs)
        first_idx = 0
        if sample_sizes:
            for i, size in enumerate(sample_sizes):
                if size >= min_sample_size:
                    first_idx = i
                    break
            else:
                # No week has enough data
                return 0, "flat"

        # Find last valid week (>= min_sample_size PRs)
        last_idx = len(values) - 1
        if sample_sizes:
            for i in range(len(sample_sizes) - 1, -1, -1):
                if sample_sizes[i] >= min_sample_size:
                    last_idx = i
                    break
            # Check if we found a valid last week after first
            if last_idx <= first_idx:
                return 0, "flat"

        first_val = values[first_idx]
        last_val = values[last_idx]

        if first_val == 0:
            if last_val > 0:
                return 100, "up"
            return 0, "flat"

        change_pct = int(round(((last_val - first_val) / first_val) * 100))

        # Cap extreme percentages at ±MAX_TREND_PERCENTAGE (A-001)
        change_pct = max(-MAX_TREND_PERCENTAGE, min(MAX_TREND_PERCENTAGE, change_pct))

        if change_pct > 0:
            trend = "up"
        elif change_pct < 0:
            trend = "down"
        else:
            trend = "flat"

        return change_pct, trend

    # Pass sample sizes (PR counts per week) to trend calculation
    prs_merged_change, prs_merged_trend = _calculate_change_and_trend(prs_merged_values, sample_sizes=prs_merged_values)
    cycle_time_change, cycle_time_trend = _calculate_change_and_trend(cycle_time_values, sample_sizes=prs_merged_values)
    ai_adoption_change, ai_adoption_trend = _calculate_change_and_trend(
        ai_adoption_values, sample_sizes=prs_merged_values
    )
    review_time_change, review_time_trend = _calculate_change_and_trend(
        review_time_values, sample_sizes=prs_merged_values
    )

    return {
        "prs_merged": {
            "values": prs_merged_values,
            "change_pct": prs_merged_change,
            "trend": prs_merged_trend,
        },
        "cycle_time": {
            "values": cycle_time_values,
            "change_pct": cycle_time_change,
            "trend": cycle_time_trend,
        },
        "ai_adoption": {
            "values": ai_adoption_values,
            "change_pct": ai_adoption_change,
            "trend": ai_adoption_trend,
        },
        "review_time": {
            "values": review_time_values,
            "change_pct": review_time_change,
            "trend": review_time_trend,
        },
    }


def get_velocity_trend(team: Team, start_date: date, end_date: date) -> dict:
    """Get velocity trend showing story points completed per week.

    Groups resolved Jira issues by calendar week and aggregates story points
    and issue counts. Used for velocity trend line charts.

    Args:
        team: The team to analyze
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        dict with:
            - periods: List of dicts with period_start, period_name, story_points, issues_resolved
            - total_story_points: Sum of all story points in range
            - total_issues: Count of all resolved issues in range
            - grouping: String indicating grouping type ("weekly")
    """
    from apps.metrics.models import JiraIssue

    # Query resolved issues in date range, grouped by week
    issues = JiraIssue.objects.filter(
        team=team,
        resolved_at__gte=start_of_day(start_date),
        resolved_at__lte=end_of_day(end_date),
    )

    # Group by week using TruncWeek and aggregate
    weekly_data = (
        issues.annotate(week=TruncWeek("resolved_at"))
        .values("week")
        .annotate(
            story_points=Sum("story_points"),
            issues_resolved=Count("id"),
        )
        .order_by("week")
    )

    # Build periods list
    periods = []
    total_story_points = Decimal("0")
    total_issues = 0

    for entry in weekly_data:
        week_start = entry["week"]
        if week_start is None:
            continue

        # Convert datetime to date if needed
        if hasattr(week_start, "date"):
            week_start = week_start.date()

        # Format period_name as "Week of Mon DD"
        period_name = f"Week of {week_start.strftime('%b %d').replace(' 0', ' ')}"

        # Handle None story_points (treat as 0)
        sp = entry["story_points"] if entry["story_points"] is not None else Decimal("0")
        issues_count = entry["issues_resolved"]

        periods.append(
            {
                "period_start": week_start.isoformat(),
                "period_name": period_name,
                "story_points": sp,
                "issues_resolved": issues_count,
            }
        )

        total_story_points += sp
        total_issues += issues_count

    return {
        "periods": periods,
        "total_story_points": total_story_points,
        "total_issues": total_issues,
        "grouping": "weekly",
    }
