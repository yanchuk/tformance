"""Tech category metrics for dashboard.

Functions for technology/file category breakdown and trends.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum

from apps.metrics.models import PRFile
from apps.metrics.services.dashboard._helpers import (
    _apply_repo_filter,
    _get_merged_prs_in_range,
    _is_valid_category,
)
from apps.teams.models import Team
from apps.utils.date_utils import end_of_day, start_of_day


def get_file_category_breakdown(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get file change breakdown by category for a team within a date range.

    Categorizes files changed in PRs to show where development effort
    is being spent (frontend, backend, tests, etc.).

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - total_files (int): Total files changed
            - total_changes (int): Total lines changed (additions + deletions)
            - by_category (list): Breakdown by file category
    """
    files = PRFile.objects.filter(
        team=team,
        pull_request__merged_at__gte=start_of_day(start_date),
        pull_request__merged_at__lte=end_of_day(end_date),
    )
    if repo:
        files = files.filter(pull_request__github_repo=repo)

    total_files = files.count()
    total_changes = files.aggregate(total=Sum("additions") + Sum("deletions"))["total"] or 0

    # Breakdown by category
    by_category = (
        files.values("file_category")
        .annotate(
            file_count=Count("id"),
            additions=Sum("additions"),
            deletions=Sum("deletions"),
        )
        .order_by("-file_count")
    )

    category_breakdown = [
        {
            "category": cat["file_category"],
            "category_display": dict(PRFile.CATEGORY_CHOICES).get(cat["file_category"], cat["file_category"]),
            "file_count": cat["file_count"],
            "additions": cat["additions"] or 0,
            "deletions": cat["deletions"] or 0,
            "total_changes": (cat["additions"] or 0) + (cat["deletions"] or 0),
            "percentage": Decimal(str(round(cat["file_count"] * 100.0 / total_files, 1)))
            if total_files > 0
            else Decimal("0.0"),
        }
        for cat in by_category
    ]

    return {
        "total_files": total_files,
        "total_changes": total_changes,
        "by_category": category_breakdown,
    }


def get_tech_breakdown(
    team: Team, start_date: date, end_date: date, ai_assisted: str = "all", repo: str | None = None
) -> list[dict]:
    """Get PR breakdown by technology category (frontend, backend, devops, etc.).

    Uses LLM-detected categories from llm_summary.tech.categories,
    falling back to PRFile pattern-based detection.

    Note: A single PR can have multiple categories, so totals may exceed PR count.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        ai_assisted: Filter by AI assistance - "all", "yes", or "no"
        repo: Optional repository filter (owner/repo format)

    Returns:
        list of dicts with keys:
            - category (str): Tech category (frontend, backend, devops, etc.)
            - count (int): Number of PRs touching that category
            - percentage (float): Percentage of total PRs
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Use Python to iterate since we need the effective_tech_categories property
    category_counts: dict[str, int] = {}
    total_prs = 0

    for pr in prs.only("id", "llm_summary", "is_ai_assisted").prefetch_related("files"):
        # Apply AI filter using effective_is_ai_assisted property (LLM takes priority)
        if ai_assisted == "yes" and not pr.effective_is_ai_assisted:
            continue
        if ai_assisted == "no" and pr.effective_is_ai_assisted:
            continue

        categories = pr.effective_tech_categories
        # Filter out invalid categories (empty, {}, etc.)
        valid_categories = [c for c in categories if _is_valid_category(c)] if categories else []
        if not valid_categories:
            valid_categories = ["other"]
        for category in valid_categories:
            category_counts[category] = category_counts.get(category, 0) + 1
        total_prs += 1

    if total_prs == 0:
        return []

    # Build result sorted by count descending
    result = []
    for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        result.append(
            {
                "category": category,
                "count": count,
                "percentage": round(count / total_prs * 100, 1),
            }
        )

    return result


def get_monthly_tech_trend(
    team: Team, start_date: date, end_date: date, ai_assisted: str = "all", repo: str | None = None
) -> dict[str, list[dict]]:
    """Get tech category breakdown trend by month.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        ai_assisted: Filter by AI assistance - "all", "yes", or "no"
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict mapping category to list of monthly counts:
        {
            "frontend": [{"month": "2024-01", "value": 10}, ...],
            "backend": [{"month": "2024-01", "value": 5}, ...],
            ...
        }
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Group by month and category using Python
    monthly_category_counts: dict[str, dict[str, int]] = {}  # {month: {category: count}}

    for pr in prs.only("id", "merged_at", "llm_summary", "is_ai_assisted").prefetch_related("files"):
        if not pr.merged_at:
            continue

        # Apply AI filter using effective_is_ai_assisted property (LLM takes priority)
        if ai_assisted == "yes" and not pr.effective_is_ai_assisted:
            continue
        if ai_assisted == "no" and pr.effective_is_ai_assisted:
            continue

        month_str = pr.merged_at.strftime("%Y-%m")
        categories = pr.effective_tech_categories
        # Filter out invalid categories (empty, {}, etc.)
        valid_categories = [c for c in categories if _is_valid_category(c)] if categories else []
        if not valid_categories:
            valid_categories = ["other"]

        if month_str not in monthly_category_counts:
            monthly_category_counts[month_str] = {}

        for category in valid_categories:
            monthly_category_counts[month_str][category] = monthly_category_counts[month_str].get(category, 0) + 1

    # Get all months in order
    months = sorted(monthly_category_counts.keys())

    # Get all categories
    all_categories = set()
    for counts in monthly_category_counts.values():
        all_categories.update(counts.keys())

    # Build result with all categories having data for all months
    result: dict[str, list[dict]] = {}
    for category in sorted(all_categories):
        result[category] = []
        for month in months:
            count = monthly_category_counts.get(month, {}).get(category, 0)
            result[category].append({"month": month, "value": count})

    return result


def get_weekly_tech_trend(
    team: Team, start_date: date, end_date: date, ai_assisted: str = "all", repo: str | None = None
) -> dict[str, list[dict]]:
    """Get tech category breakdown trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        ai_assisted: Filter by AI assistance - "all", "yes", or "no"
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict mapping category to list of weekly counts:
        {
            "frontend": [{"week": "2024-W01", "value": 3}, ...],
            "backend": [{"week": "2024-W01", "value": 2}, ...],
            ...
        }
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Group by week and category using Python
    weekly_category_counts: dict[str, dict[str, int]] = {}  # {week: {category: count}}

    for pr in prs.only("id", "merged_at", "llm_summary", "is_ai_assisted").prefetch_related("files"):
        if not pr.merged_at:
            continue

        # Apply AI filter using effective_is_ai_assisted property (LLM takes priority)
        if ai_assisted == "yes" and not pr.effective_is_ai_assisted:
            continue
        if ai_assisted == "no" and pr.effective_is_ai_assisted:
            continue

        week_str = pr.merged_at.strftime("%Y-W%V")
        categories = pr.effective_tech_categories
        # Filter out invalid categories (empty, {}, etc.)
        valid_categories = [c for c in categories if _is_valid_category(c)] if categories else []
        if not valid_categories:
            valid_categories = ["other"]

        if week_str not in weekly_category_counts:
            weekly_category_counts[week_str] = {}

        for category in valid_categories:
            weekly_category_counts[week_str][category] = weekly_category_counts[week_str].get(category, 0) + 1

    # Get all weeks in order
    weeks = sorted(weekly_category_counts.keys())

    # Get all categories
    all_categories = set()
    for counts in weekly_category_counts.values():
        all_categories.update(counts.keys())

    # Build result with all categories having data for all weeks
    result: dict[str, list[dict]] = {}
    for category in sorted(all_categories):
        result[category] = []
        for week in weeks:
            count = weekly_category_counts.get(week, {}).get(category, 0)
            result[category].append({"week": week, "value": count})

    return result
