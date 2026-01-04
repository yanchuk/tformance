"""PR-related metrics for dashboard.

Functions for PR lists, size distribution, type breakdown, and attention tracking.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Case, CharField, Count, F, Q, Value, When

from apps.integrations.models import JiraIntegration
from apps.metrics.models import PRSurvey, PullRequest
from apps.metrics.services.dashboard._helpers import (
    _apply_repo_filter,
    _get_author_name,
    _get_github_url,
    _get_merged_prs_in_range,
)
from apps.teams.models import Team

# PR Size Categories
# Categories based on total lines changed (additions + deletions)
PR_SIZE_XS_MAX = 10
PR_SIZE_S_MAX = 50
PR_SIZE_M_MAX = 200
PR_SIZE_L_MAX = 500


def get_recent_prs(
    team: Team, start_date: date, end_date: date, limit: int = 10, repo: str | None = None
) -> list[dict]:
    """Get recent PRs with AI status and quality scores.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum number of PRs to return (default 10)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - id (int): PR database ID
            - title (str): PR title
            - author (str): Author display name
            - merged_at (datetime): Merge timestamp
            - ai_assisted (bool or None): Whether AI-assisted (survey), None if no survey
            - is_ai_detected (bool): Whether AI detected from PR content
            - ai_tools (list): List of detected AI tools
            - avg_quality (float or None): Average quality rating, None if no reviews
            - url (str): PR URL
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)
    prs = prs.select_related("author").prefetch_related("survey", "survey__reviews").order_by("-merged_at")[:limit]

    result = []
    for pr in prs:
        # Get survey data if exists
        ai_assisted = None
        avg_quality = None

        try:
            survey = pr.survey
            ai_assisted = survey.author_ai_assisted
            reviews = survey.reviews.all()
            if reviews:
                total_rating = sum(r.quality_rating for r in reviews if r.quality_rating is not None)
                count = sum(1 for r in reviews if r.quality_rating is not None)
                if count > 0:
                    avg_quality = total_rating / count
        except PRSurvey.DoesNotExist:
            pass

        result.append(
            {
                "id": pr.id,
                "title": pr.title,
                "author": _get_author_name(pr),
                "author_avatar_url": pr.author.avatar_url if pr.author else "",
                "author_initials": pr.author.initials if pr.author else "??",
                "merged_at": pr.merged_at,
                "ai_assisted": ai_assisted,
                "is_ai_detected": pr.is_ai_assisted,
                "ai_tools": pr.ai_tools_detected,
                "avg_quality": avg_quality,
                "url": _get_github_url(pr),
            }
        )

    return result


def get_revert_hotfix_stats(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get revert and hotfix statistics.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - total_prs (int): Total merged PRs
            - revert_count (int): Count of revert PRs
            - hotfix_count (int): Count of hotfix PRs
            - revert_pct (float): Percentage of reverts (0.0 to 100.0)
            - hotfix_pct (float): Percentage of hotfixes (0.0 to 100.0)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Use DB aggregation to count total, revert, and hotfix PRs in a single query
    stats = prs.aggregate(
        total_prs=Count("id"),
        revert_count=Count("id", filter=Q(is_revert=True)),
        hotfix_count=Count("id", filter=Q(is_hotfix=True)),
    )

    total_prs = stats["total_prs"]
    revert_count = stats["revert_count"]
    hotfix_count = stats["hotfix_count"]

    revert_pct = round(revert_count * 100.0 / total_prs, 2) if total_prs > 0 else 0.0
    hotfix_pct = round(hotfix_count * 100.0 / total_prs, 2) if total_prs > 0 else 0.0

    return {
        "total_prs": total_prs,
        "revert_count": revert_count,
        "hotfix_count": hotfix_count,
        "revert_pct": revert_pct,
        "hotfix_pct": hotfix_pct,
    }


def get_pr_size_distribution(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get PR size distribution by category.

    Categories based on additions + deletions:
    - XS: 1-10 lines
    - S: 11-50 lines
    - M: 51-200 lines
    - L: 201-500 lines
    - XL: 500+ lines

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - category (str): Size category (XS, S, M, L, XL)
            - count (int): Number of PRs in this category
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Use database aggregation to count PRs by size category
    # Annotate each PR with its size category, then count by category
    categorized = prs.annotate(
        total_lines=F("additions") + F("deletions"),
        size_category=Case(
            When(total_lines__lte=PR_SIZE_XS_MAX, then=Value("XS")),
            When(total_lines__lte=PR_SIZE_S_MAX, then=Value("S")),
            When(total_lines__lte=PR_SIZE_M_MAX, then=Value("M")),
            When(total_lines__lte=PR_SIZE_L_MAX, then=Value("L")),
            default=Value("XL"),
            output_field=CharField(),
        ),
    )

    # Count PRs by category
    category_counts = categorized.values("size_category").annotate(count=Count("id"))

    # Convert to dict for easy lookup
    counts_by_category = {item["size_category"]: item["count"] for item in category_counts}

    # Return all categories in order, with 0 for missing categories
    return [{"category": cat, "count": counts_by_category.get(cat, 0)} for cat in ["XS", "S", "M", "L", "XL"]]


def get_unlinked_prs(
    team: Team, start_date: date, end_date: date, limit: int = 10, repo: str | None = None
) -> list[dict]:
    """Get merged PRs without Jira links.

    Returns PRs that have been merged within the date range but lack a Jira issue
    key association. Useful for identifying PRs that may need to be linked to
    work items for tracking purposes.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum number of PRs to return (default 10)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - title (str): PR title
            - author (str): Author display name
            - merged_at (datetime): Merge timestamp
            - url (str): PR URL
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)
    prs = prs.filter(jira_key="").select_related("author").order_by("-merged_at")[:limit]

    return [
        {
            "title": pr.title,
            "author": _get_author_name(pr),
            "merged_at": pr.merged_at,
            "url": _get_github_url(pr),
        }
        for pr in prs
    ]


def get_iteration_metrics(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get iteration metrics averages for merged PRs within a date range.

    Aggregates iteration metrics (review rounds, fix response time, etc.)
    from PRs that have been analyzed by the sync pipeline.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - avg_review_rounds (Decimal or None): Average review rounds
            - avg_fix_response_hours (Decimal or None): Average fix response time
            - avg_commits_after_first_review (Decimal or None): Average commits after first review
            - avg_total_comments (Decimal or None): Average total comments
            - prs_with_metrics (int): Count of PRs with iteration metrics
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Get PRs with at least one non-null iteration metric
    prs_with_metrics = prs.filter(review_rounds__isnull=False)

    # Aggregate averages
    stats = prs_with_metrics.aggregate(
        avg_review_rounds=Avg("review_rounds"),
        avg_fix_response_hours=Avg("avg_fix_response_hours"),
        avg_commits_after_first_review=Avg("commits_after_first_review"),
        avg_total_comments=Avg("total_comments"),
        prs_count=Count("id"),
    )

    # Convert to Decimal with 2 decimal places
    def to_decimal(value):
        if value is None:
            return None
        return Decimal(str(round(float(value), 2)))

    return {
        "avg_review_rounds": to_decimal(stats["avg_review_rounds"]),
        "avg_fix_response_hours": to_decimal(stats["avg_fix_response_hours"]),
        "avg_commits_after_first_review": to_decimal(stats["avg_commits_after_first_review"]),
        "avg_total_comments": to_decimal(stats["avg_total_comments"]),
        "prs_with_metrics": stats["prs_count"],
    }


def get_pr_type_breakdown(
    team: Team, start_date: date, end_date: date, ai_assisted: str = "all", repo: str | None = None
) -> list[dict]:
    """Get PR breakdown by type (feature, bugfix, refactor, etc.).

    Uses LLM-detected PR types from llm_summary.summary.type,
    falling back to label inference.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        ai_assisted: Filter by AI assistance - "all", "yes", or "no"
        repo: Optional repository filter (owner/repo format)

    Returns:
        list of dicts with keys:
            - type (str): PR type (feature, bugfix, refactor, docs, test, chore, ci, unknown)
            - count (int): Number of PRs of that type
            - percentage (float): Percentage of total PRs
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Use Python to iterate since we need the effective_pr_type property
    type_counts: dict[str, int] = {}
    total = 0

    for pr in prs.only("id", "llm_summary", "labels", "is_ai_assisted"):
        # Apply AI filter using effective_is_ai_assisted property (LLM takes priority)
        if ai_assisted == "yes" and not pr.effective_is_ai_assisted:
            continue
        if ai_assisted == "no" and pr.effective_is_ai_assisted:
            continue

        pr_type = pr.effective_pr_type
        type_counts[pr_type] = type_counts.get(pr_type, 0) + 1
        total += 1

    if total == 0:
        return []

    # Build result sorted by count descending
    result = []
    for pr_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        result.append(
            {
                "type": pr_type,
                "count": count,
                "percentage": round(count / total * 100, 1),
            }
        )

    return result


def get_monthly_pr_type_trend(
    team: Team, start_date: date, end_date: date, ai_assisted: str = "all", repo: str | None = None
) -> dict[str, list[dict]]:
    """Get PR type breakdown trend by month.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        ai_assisted: Filter by AI assistance - "all", "yes", or "no"
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict mapping PR type to list of monthly counts:
        {
            "feature": [{"month": "2024-01", "value": 10}, ...],
            "bugfix": [{"month": "2024-01", "value": 5}, ...],
            ...
        }
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Group by month and type using Python (need effective_pr_type property)
    monthly_type_counts: dict[str, dict[str, int]] = {}  # {month: {type: count}}

    for pr in prs.only("id", "merged_at", "llm_summary", "labels", "is_ai_assisted"):
        if not pr.merged_at:
            continue

        # Apply AI filter using effective_is_ai_assisted property (LLM takes priority)
        if ai_assisted == "yes" and not pr.effective_is_ai_assisted:
            continue
        if ai_assisted == "no" and pr.effective_is_ai_assisted:
            continue

        month_str = pr.merged_at.strftime("%Y-%m")
        pr_type = pr.effective_pr_type

        if month_str not in monthly_type_counts:
            monthly_type_counts[month_str] = {}
        monthly_type_counts[month_str][pr_type] = monthly_type_counts[month_str].get(pr_type, 0) + 1

    # Get all months in order
    months = sorted(monthly_type_counts.keys())

    # Get all types
    all_types = set()
    for counts in monthly_type_counts.values():
        all_types.update(counts.keys())

    # Build result with all types having data for all months
    result: dict[str, list[dict]] = {}
    for pr_type in sorted(all_types):
        result[pr_type] = []
        for month in months:
            count = monthly_type_counts.get(month, {}).get(pr_type, 0)
            result[pr_type].append({"month": month, "value": count})

    return result


def get_weekly_pr_type_trend(
    team: Team, start_date: date, end_date: date, ai_assisted: str = "all", repo: str | None = None
) -> dict[str, list[dict]]:
    """Get PR type breakdown trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        ai_assisted: Filter by AI assistance - "all", "yes", or "no"
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict mapping PR type to list of weekly counts:
        {
            "feature": [{"week": "2024-W01", "value": 3}, ...],
            "bugfix": [{"week": "2024-W01", "value": 2}, ...],
            ...
        }
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Group by week and type using Python
    weekly_type_counts: dict[str, dict[str, int]] = {}  # {week: {type: count}}

    for pr in prs.only("id", "merged_at", "llm_summary", "labels", "is_ai_assisted"):
        if not pr.merged_at:
            continue

        # Apply AI filter using effective_is_ai_assisted property (LLM takes priority)
        if ai_assisted == "yes" and not pr.effective_is_ai_assisted:
            continue
        if ai_assisted == "no" and pr.effective_is_ai_assisted:
            continue

        week_str = pr.merged_at.strftime("%Y-W%V")
        pr_type = pr.effective_pr_type

        if week_str not in weekly_type_counts:
            weekly_type_counts[week_str] = {}
        weekly_type_counts[week_str][pr_type] = weekly_type_counts[week_str].get(pr_type, 0) + 1

    # Get all weeks in order
    weeks = sorted(weekly_type_counts.keys())

    # Get all types
    all_types = set()
    for counts in weekly_type_counts.values():
        all_types.update(counts.keys())

    # Build result with all types having data for all weeks
    result: dict[str, list[dict]] = {}
    for pr_type in sorted(all_types):
        result[pr_type] = []
        for week in weeks:
            count = weekly_type_counts.get(week, {}).get(pr_type, 0)
            result[pr_type].append({"week": week, "value": count})

    return result


def get_needs_attention_prs(
    team: Team,
    start_date: date,
    end_date: date,
    page: int = 1,
    per_page: int = 10,
) -> dict:
    """Get PRs that need attention, prioritized by issue severity.

    Identifies PRs with potential issues and returns them sorted by priority:
    1. Reverts (is_revert=True) - Priority 1
    2. Hotfixes (is_hotfix=True) - Priority 2
    3. Long cycle time (> 2x team average) - Priority 3
    4. Large PRs (> 500 lines changed) - Priority 4
    5. Missing Jira link (only if team has Jira connected) - Priority 5

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        page: Page number (1-indexed)
        per_page: Number of items per page

    Returns:
        dict with keys:
            - items: list of PR dicts with issue info
            - total: total count of flagged PRs
            - page: current page number
            - per_page: items per page
            - has_next: True if more pages exist
            - has_prev: True if previous pages exist
    """
    # Get all merged PRs in range
    prs = _get_merged_prs_in_range(team, start_date, end_date).select_related("author")

    # Calculate team average cycle time for long cycle detection
    avg_cycle_result = prs.filter(cycle_time_hours__isnull=False).aggregate(avg_cycle=Avg("cycle_time_hours"))
    team_avg_cycle = avg_cycle_result["avg_cycle"] or Decimal("0")
    long_cycle_threshold = team_avg_cycle * 2

    # Check if team has Jira connected
    has_jira = JiraIntegration.objects.filter(team=team).exists()

    # Identify PRs with issues and assign priority
    flagged_prs = []
    for pr in prs:
        issue_type = None
        issue_priority = None

        # Check issues in priority order (first match wins)
        if pr.is_revert:
            issue_type = "revert"
            issue_priority = 1
        elif pr.is_hotfix:
            issue_type = "hotfix"
            issue_priority = 2
        elif pr.cycle_time_hours and long_cycle_threshold > 0 and pr.cycle_time_hours > long_cycle_threshold:
            issue_type = "long_cycle"
            issue_priority = 3
        elif (pr.additions or 0) + (pr.deletions or 0) > 500:
            issue_type = "large_pr"
            issue_priority = 4
        elif has_jira and not pr.jira_key:
            issue_type = "missing_jira"
            issue_priority = 5

        if issue_type:
            flagged_prs.append(
                {
                    "id": pr.id,
                    "title": pr.title,
                    "url": _get_github_url(pr),
                    "author": _get_author_name(pr),
                    "author_avatar_url": pr.author.avatar_url if pr.author else "",
                    "issue_type": issue_type,
                    "issue_priority": issue_priority,
                    "merged_at": pr.merged_at,
                }
            )

    # Sort by priority (ascending), then by merged_at (descending)
    flagged_prs.sort(key=lambda x: (x["issue_priority"], -x["merged_at"].timestamp()))

    # Pagination
    total = len(flagged_prs)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    items = flagged_prs[start_idx:end_idx]

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_next": end_idx < total,
        "has_prev": page > 1,
    }


def get_open_prs_stats(team: Team, repo: str | None = None) -> dict:
    """Get statistics about open PRs, distinguishing draft from ready-to-review.

    Args:
        team: Team instance
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with:
            - total_open: int - Total open PRs
            - draft_count: int - Open PRs in draft state (WIP)
            - ready_for_review: int - Open non-draft PRs (actionable)
            - draft_pct: float - Percentage of open PRs that are drafts
    """
    filters = {
        "team": team,
        "state": "open",
    }
    if repo:
        filters["github_repo"] = repo

    # Count all open PRs
    total_open = PullRequest.objects.filter(**filters).count()  # noqa: TEAM001 - team in filters

    # Count drafts
    draft_count = PullRequest.objects.filter(**filters, is_draft=True).count()  # noqa: TEAM001 - team in filters

    ready_for_review = total_open - draft_count
    draft_pct = (draft_count * 100.0 / total_open) if total_open > 0 else 0.0

    return {
        "total_open": total_open,
        "draft_count": draft_count,
        "ready_for_review": ready_for_review,
        "draft_pct": round(draft_pct, 1),
    }
