"""Private helper functions for dashboard service modules.

These helpers are used across multiple dashboard metric modules.
They should not be imported directly by external code.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, Q, QuerySet
from django.db.models.functions import TruncMonth, TruncWeek

from apps.metrics.models import PullRequest
from apps.teams.models import Team
from apps.utils.date_utils import end_of_day, start_of_day


def _apply_repo_filter(qs: QuerySet, repo: str | None) -> QuerySet:
    """Apply repository filter to a queryset if repo is specified.

    Helper function to filter querysets by repository. Used across all
    dashboard service functions that support repo filtering.

    Args:
        qs: Base queryset to filter (must have github_repo field)
        repo: Repository name (owner/repo format) or None/empty for all repos

    Returns:
        Filtered queryset if repo specified, otherwise original queryset
    """
    if repo:
        return qs.filter(github_repo=repo)
    return qs


def _get_merged_prs_in_range(team: Team, start_date: date, end_date: date) -> QuerySet[PullRequest]:
    """Get merged PRs for a team within a date range.

    Helper function to avoid repeating this common query pattern.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        QuerySet of merged PullRequest objects
    """
    return PullRequest.objects.filter(
        team=team,
        state="merged",
        merged_at__gte=start_of_day(start_date),
        merged_at__lte=end_of_day(end_date),
    )


def _calculate_ai_percentage(surveys: QuerySet) -> Decimal:
    """Calculate percentage of AI-assisted surveys.

    Uses single aggregate query for efficiency (avoids 2 separate count queries).

    Args:
        surveys: QuerySet of PRSurvey objects

    Returns:
        Decimal percentage (0.00 to 100.00)
    """
    stats = surveys.aggregate(
        total=Count("id"),
        ai_count=Count("id", filter=Q(author_ai_assisted=True)),
    )
    if stats["total"] > 0:
        return Decimal(str(round(stats["ai_count"] * 100.0 / stats["total"], 2)))
    return Decimal("0.00")


def _calculate_ai_percentage_from_detection(prs: QuerySet[PullRequest]) -> Decimal:
    """Calculate percentage of AI-assisted PRs using detection data.

    Uses effective_is_ai_assisted property which prioritizes:
    1. LLM detection (llm_summary.ai.is_assisted with confidence >= 0.5)
    2. Pattern detection (is_ai_assisted field)

    Args:
        prs: QuerySet of PullRequest objects

    Returns:
        Decimal percentage (0.00 to 100.00)
    """
    total_prs = prs.count()
    if total_prs == 0:
        return Decimal("0.00")

    # Count PRs where effective_is_ai_assisted is True
    # Since this is a property, we need to iterate
    ai_count = sum(1 for pr in prs if pr.effective_is_ai_assisted)
    return Decimal(str(round(ai_count * 100.0 / total_prs, 2)))


def _get_github_url(pr: PullRequest) -> str:
    """Construct GitHub URL from PR data.

    Args:
        pr: PullRequest instance

    Returns:
        str: Full GitHub URL to the pull request
    """
    return f"https://github.com/{pr.github_repo}/pull/{pr.github_pr_id}"


def _get_author_name(pr: PullRequest) -> str:
    """Get author display name with fallback.

    Args:
        pr: PullRequest instance

    Returns:
        str: Author display name or "Unknown" if no author
    """
    return pr.author.display_name if pr.author else "Unknown"


def _compute_initials(name: str) -> str:
    """Compute 2-letter initials from a display name.

    Args:
        name: Display name string

    Returns:
        str: 2-letter uppercase initials
    """
    if not name:
        return "??"
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return name[:2].upper()


def _avatar_url_from_github_id(github_id: str | None) -> str:
    """Construct GitHub avatar URL from user ID or username.

    Args:
        github_id: GitHub user ID (numeric) or username (alphanumeric), or None

    Returns:
        str: Avatar URL or empty string if no ID
    """
    if not github_id:
        return ""
    # Numeric IDs use /u/ prefix, usernames don't
    if github_id.isdigit():
        return f"https://avatars.githubusercontent.com/u/{github_id}?s=80"
    return f"https://avatars.githubusercontent.com/{github_id}?s=80"


def _get_key_metrics_cache_key(team_id: int, start_date: date, end_date: date) -> str:
    """Generate cache key for key metrics."""
    return f"key_metrics:{team_id}:{start_date}:{end_date}"


def _get_metric_trend(
    team: Team,
    start_date: date,
    end_date: date,
    metric_field: str,
    result_key: str = "avg_metric",
    repo: str | None = None,
) -> list[dict]:
    """Get weekly trend for a given metric field.

    Generic helper to calculate weekly averages for any numeric PR field.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        metric_field: Name of the PR model field to average
        result_key: Key name for the aggregated result in the query
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - week (str): Week start date in ISO format (YYYY-MM-DD)
            - value (float): Average metric value for that week (0.0 if None)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Group by week and calculate average metric
    weekly_data = (
        prs.annotate(week=TruncWeek("merged_at"))
        .values("week")
        .annotate(**{result_key: Avg(metric_field)})
        .order_by("week")
    )

    result = []
    for entry in weekly_data:
        # Convert datetime to ISO format string for JSON serialization
        week_str = entry["week"].strftime("%Y-%m-%d") if entry["week"] else None
        # Convert Decimal to float for JSON serialization
        value = float(entry[result_key]) if entry[result_key] else 0.0
        result.append(
            {
                "week": week_str,
                "value": value,
            }
        )

    return result


def _filter_by_date_range(
    queryset: QuerySet, date_field: str, start_date: date = None, end_date: date = None
) -> QuerySet:
    """Filter queryset by date range if dates are provided.

    Args:
        queryset: Django QuerySet to filter
        date_field: Name of the date field to filter on (must be a DateTimeField)
        start_date: Start date (inclusive), optional
        end_date: End date (inclusive), optional

    Returns:
        Filtered QuerySet (unchanged if no dates provided)
    """
    if start_date and end_date:
        return queryset.filter(
            **{f"{date_field}__gte": start_of_day(start_date), f"{date_field}__lte": end_of_day(end_date)}
        )
    return queryset


def _calculate_channel_percentages(stats: dict, channels: list[str]) -> dict:
    """Calculate percentage distribution for response channels.

    Args:
        stats: Dict with channel counts (keys: channel names + 'total')
        channels: List of channel names to calculate percentages for

    Returns:
        dict mapping channel names to percentage Decimals (0.00 to 100.00)
    """
    total = stats.get("total", 0)
    if total > 0:
        return {channel: Decimal(str(round(stats.get(channel, 0) * 100.0 / total, 2))) for channel in channels}
    return {channel: Decimal("0.00") for channel in channels}


def _calculate_average_response_times(response_times: list[Decimal], by_channel: dict[str, list[Decimal]]) -> tuple:
    """Calculate overall and per-channel average response times.

    Helper function to calculate average response times from a list of time values
    and a breakdown by channel.

    Args:
        response_times: List of response times in hours
        by_channel: Dict mapping channel names to lists of response times

    Returns:
        Tuple of (overall_avg, channel_avgs) where:
            - overall_avg (Decimal): Overall average response time
            - channel_avgs (dict): Dict mapping channel names to average times
    """
    # Calculate overall average
    overall_avg = (
        Decimal(str(round(sum(response_times) / len(response_times), 2))) if response_times else Decimal("0.00")
    )

    # Calculate per-channel averages
    channel_avgs = {}
    for channel in ["github", "slack", "web"]:
        times = by_channel[channel]
        channel_avgs[channel] = Decimal(str(round(sum(times) / len(times), 2))) if times else Decimal("0.00")

    return overall_avg, channel_avgs


def _get_monthly_metric_trend(
    team: Team,
    start_date: date,
    end_date: date,
    metric_field: str,
    result_key: str = "avg_metric",
    repo: str | None = None,
) -> list[dict]:
    """Get monthly trend for a given metric field.

    Generic helper to calculate monthly averages for any numeric PR field.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        metric_field: Name of the PR model field to average
        result_key: Key name for the aggregated result in the query
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - month (str): Month in YYYY-MM format
            - value (float): Average metric value for that month (0.0 if None)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Group by month and calculate average metric
    monthly_data = (
        prs.annotate(month=TruncMonth("merged_at"))
        .values("month")
        .annotate(**{result_key: Avg(metric_field)})
        .order_by("month")
    )

    result = []
    for entry in monthly_data:
        # Convert datetime to YYYY-MM format for JSON serialization
        month_str = entry["month"].strftime("%Y-%m") if entry["month"] else None
        # Convert Decimal to float for JSON serialization
        value = float(entry[result_key]) if entry[result_key] else 0.0
        result.append(
            {
                "month": month_str,
                "value": value,
            }
        )
    return result


def _is_valid_category(category: str) -> bool:
    """Check if a category is valid (not empty, not '{}', not None)."""
    if not category or isinstance(category, dict):
        return False
    category_str = str(category).strip()
    return bool(category_str) and category_str not in ("{}", "[]", "None", "null")
