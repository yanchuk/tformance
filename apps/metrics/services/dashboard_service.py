"""Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

import statistics
from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Avg, Case, CharField, Count, Q, QuerySet, Sum, Value, When
from django.db.models.functions import TruncMonth, TruncWeek

from apps.integrations.models import JiraIntegration
from apps.metrics.models import (
    AIUsageDaily,
    Deployment,
    PRCheckRun,
    PRFile,
    PRReview,
    PRSurvey,
    PRSurveyReview,
    PullRequest,
)
from apps.teams.models import Team
from apps.utils.date_utils import end_of_day, start_of_day

# Cache TTL for dashboard metrics (5 minutes)
DASHBOARD_CACHE_TTL = 300

# PR Size Categories
# Categories based on total lines changed (additions + deletions)
PR_SIZE_XS_MAX = 10
PR_SIZE_S_MAX = 50
PR_SIZE_M_MAX = 200
PR_SIZE_L_MAX = 500


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


def _calculate_ai_percentage(surveys: QuerySet[PRSurvey]) -> Decimal:
    """Calculate percentage of AI-assisted surveys.

    Args:
        surveys: QuerySet of PRSurvey objects

    Returns:
        Decimal percentage (0.00 to 100.00)
    """
    total_surveys = surveys.count()
    if total_surveys > 0:
        ai_assisted_count = surveys.filter(author_ai_assisted=True).count()
        return Decimal(str(round(ai_assisted_count * 100.0 / total_surveys, 2)))
    return Decimal("0.00")


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


def get_key_metrics(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get key metrics for a team within a date range.

    Results are cached for 5 minutes to improve dashboard performance.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - prs_merged (int): Count of merged PRs
            - avg_cycle_time (Decimal or None): Average cycle time in hours
            - avg_review_time (Decimal or None): Average review time in hours
            - avg_quality_rating (Decimal or None): Average quality rating
            - ai_assisted_pct (Decimal): Percentage of AI-assisted PRs (0.00 to 100.00)
    """
    # Check cache first (include repo in cache key)
    cache_key = _get_key_metrics_cache_key(team.id, start_date, end_date) + f":{repo or 'all'}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # Compute metrics
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    prs_merged = prs.count()

    # Calculate average cycle time
    avg_cycle_time = prs.aggregate(avg=Avg("cycle_time_hours"))["avg"]

    # Calculate average review time
    avg_review_time = prs.aggregate(avg=Avg("review_time_hours"))["avg"]

    # Calculate average quality rating from survey reviews
    reviews = PRSurveyReview.objects.filter(survey__pull_request__in=prs)
    avg_quality_rating = reviews.aggregate(avg=Avg("quality_rating"))["avg"]

    # Calculate AI-assisted percentage
    surveys = PRSurvey.objects.filter(pull_request__in=prs)
    ai_assisted_pct = _calculate_ai_percentage(surveys)

    result = {
        "prs_merged": prs_merged,
        "avg_cycle_time": avg_cycle_time,
        "avg_review_time": avg_review_time,
        "avg_quality_rating": avg_quality_rating,
        "ai_assisted_pct": ai_assisted_pct,
    }

    # Cache for 5 minutes
    cache.set(cache_key, result, DASHBOARD_CACHE_TTL)

    return result


def get_ai_adoption_trend(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get AI adoption trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - week (str): Week start date in ISO format (YYYY-MM-DD)
            - value (float): AI adoption percentage for that week
    """
    # Get merged PRs in date range with surveys
    prs = _get_merged_prs_in_range(team, start_date, end_date).filter(survey__isnull=False)
    prs = _apply_repo_filter(prs, repo)

    # Group by week and calculate AI percentage
    weekly_data = (
        prs.annotate(week=TruncWeek("merged_at"))
        .values("week")
        .annotate(
            total=Count("id"),
            ai_count=Count("id", filter=Q(survey__author_ai_assisted=True)),
        )
        .order_by("week")
    )

    result = []
    for entry in weekly_data:
        pct = round(entry["ai_count"] * 100.0 / entry["total"], 2) if entry["total"] > 0 else 0.0
        # Convert datetime to ISO format string for JSON serialization
        week_str = entry["week"].strftime("%Y-%m-%d") if entry["week"] else None
        result.append({"week": week_str, "value": pct})

    return result


def get_ai_quality_comparison(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get quality comparison between AI-assisted and non-AI PRs.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - ai_avg (Decimal or None): Average quality rating for AI-assisted PRs
            - non_ai_avg (Decimal or None): Average quality rating for non-AI PRs
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Get quality ratings for AI-assisted PRs
    ai_reviews = PRSurveyReview.objects.filter(survey__pull_request__in=prs, survey__author_ai_assisted=True)
    ai_avg = ai_reviews.aggregate(avg=Avg("quality_rating"))["avg"]

    # Get quality ratings for non-AI PRs
    non_ai_reviews = PRSurveyReview.objects.filter(survey__pull_request__in=prs, survey__author_ai_assisted=False)
    non_ai_avg = non_ai_reviews.aggregate(avg=Avg("quality_rating"))["avg"]

    return {
        "ai_avg": ai_avg,
        "non_ai_avg": non_ai_avg,
    }


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


def get_team_breakdown(
    team: Team,
    start_date: date,
    end_date: date,
    sort_by: str = "prs_merged",
    order: str = "desc",
    repo: str | None = None,
) -> list[dict]:
    """Get team breakdown with metrics per member.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        sort_by: Field to sort by (prs_merged, cycle_time, ai_pct, name)
        order: Sort order (asc or desc)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - member_id (int): Team member ID
            - member_name (str): Team member display name
            - prs_merged (int): Count of merged PRs
            - avg_cycle_time (Decimal): Average cycle time in hours (0.00 if None)
            - ai_pct (float): AI adoption percentage (0.0 to 100.0)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Map sort_by to actual field names
    SORT_FIELDS = {
        "prs_merged": "prs_merged",
        "cycle_time": "avg_cycle_time",
        "ai_pct": None,  # Sort in Python after aggregation
        "name": "author__display_name",
    }

    # Determine database sort field
    db_sort_field = SORT_FIELDS.get(sort_by, "prs_merged")

    # Build order_by clause
    order_by_clause = []
    if db_sort_field:
        prefix = "-" if order == "desc" else ""
        order_by_clause = [f"{prefix}{db_sort_field}"]

    # Single aggregated query for PR metrics per author (replaces N+1 loop)
    query = (
        prs.exclude(author__isnull=True)
        .values(
            "author__id",
            "author__display_name",
            "author__github_id",
        )
        .annotate(
            prs_merged=Count("id"),
            avg_cycle_time=Avg("cycle_time_hours"),
        )
    )

    # Apply DB sorting if applicable
    if order_by_clause:
        query = query.order_by(*order_by_clause)

    pr_aggregates = list(query)

    # Get all author IDs for batch survey lookup
    author_ids = [row["author__id"] for row in pr_aggregates]

    # Single aggregated query for AI percentages per author (replaces N+1 loop)
    survey_aggregates = (
        PRSurvey.objects.filter(
            team=team,
            pull_request__in=prs,
            pull_request__author_id__in=author_ids,
        )
        .values("pull_request__author_id")
        .annotate(
            total_surveys=Count("id"),
            ai_assisted_count=Count("id", filter=Q(author_ai_assisted=True)),
        )
    )

    # Build lookup dict for AI percentages
    ai_pct_by_author = {}
    for row in survey_aggregates:
        author_id = row["pull_request__author_id"]
        total = row["total_surveys"]
        ai_count = row["ai_assisted_count"]
        ai_pct_by_author[author_id] = round(ai_count * 100.0 / total, 2) if total > 0 else 0.0

    # Build result list from aggregated data
    result = []
    for row in pr_aggregates:
        author_id = row["author__id"]
        display_name = row["author__display_name"]
        github_id = row["author__github_id"]

        # Compute avatar_url and initials from aggregated data
        avatar_url = _avatar_url_from_github_id(github_id)
        initials = _compute_initials(display_name) if display_name else "??"

        result.append(
            {
                "member_id": author_id,
                "member_name": display_name,
                "avatar_url": avatar_url,
                "initials": initials,
                "prs_merged": row["prs_merged"],
                "avg_cycle_time": row["avg_cycle_time"] if row["avg_cycle_time"] else Decimal("0.00"),
                "ai_pct": ai_pct_by_author.get(author_id, 0.0),
            }
        )

    # Apply Python-based sorting if needed (for ai_pct which can't be sorted in DB)
    if sort_by == "ai_pct":
        result.sort(key=lambda x: x["ai_pct"], reverse=(order == "desc"))

    return result


def get_ai_detective_leaderboard(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get AI detective leaderboard data.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository filter (owner/repo format)

    Returns:
        list of dicts with keys:
            - member_name (str): Reviewer display name
            - correct (int): Number of correct guesses
            - total (int): Total number of guesses
            - percentage (float): Accuracy percentage (0.0 to 100.0)
    """
    # Query PRSurveyReview for guess accuracy
    reviews = PRSurveyReview.objects.filter(
        team=team,
        responded_at__gte=start_of_day(start_date),
        responded_at__lte=end_of_day(end_date),
        guess_correct__isnull=False,
    )
    if repo:
        reviews = reviews.filter(survey__pull_request__github_repo=repo)
    reviews = (
        reviews.values("reviewer__display_name", "reviewer__github_id")
        .annotate(
            total=Count("id"),
            correct=Count("id", filter=Q(guess_correct=True)),
        )
        .order_by("-correct")
    )

    return [
        {
            "member_name": r["reviewer__display_name"],
            "avatar_url": _avatar_url_from_github_id(r["reviewer__github_id"]),
            "initials": _compute_initials(r["reviewer__display_name"]),
            "correct": r["correct"],
            "total": r["total"],
            "percentage": round((r["correct"] / r["total"]) * 100, 1) if r["total"] > 0 else 0.0,
        }
        for r in reviews
    ]


def get_review_distribution(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get review distribution by reviewer (for pie chart).

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list of dicts with keys:
            - reviewer_name (str): Reviewer display name
            - count (int): Number of reviews
    """
    reviews = (
        PRSurveyReview.objects.filter(
            team=team,
            responded_at__gte=start_of_day(start_date),
            responded_at__lte=end_of_day(end_date),
        )
        .values("reviewer__display_name", "reviewer__github_id")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return [
        {
            "reviewer_name": r["reviewer__display_name"],
            "avatar_url": _avatar_url_from_github_id(r["reviewer__github_id"]),
            "initials": _compute_initials(r["reviewer__display_name"]),
            "count": r["count"],
        }
        for r in reviews
    ]


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
    from django.db.models import F

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


def get_reviewer_workload(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get reviewer workload with classification.

    Uses PRReview model (GitHub reviews). Classifies workload as:
    - low: below 25th percentile
    - normal: 25th-75th percentile
    - high: above 75th percentile

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - reviewer_name (str): Reviewer display name
            - review_count (int): Number of reviews
            - workload_level (str): Classification (low, normal, high)
    """
    reviews = PRReview.objects.filter(
        team=team,
        submitted_at__gte=start_of_day(start_date),
        submitted_at__lte=end_of_day(end_date),
    )
    # Filter by repository through the pull_request relationship
    if repo:
        reviews = reviews.filter(pull_request__github_repo=repo)
    reviews = reviews.values("reviewer__display_name").annotate(review_count=Count("id")).order_by("-review_count")

    if not reviews:
        return []

    # Calculate percentiles for workload classification
    counts = [r["review_count"] for r in reviews]
    p25 = statistics.quantiles(counts, n=4)[0] if len(counts) >= 2 else counts[0]
    p75 = statistics.quantiles(counts, n=4)[2] if len(counts) >= 2 else counts[0]

    def classify(count):
        if count < p25:
            return "low"
        elif count > p75:
            return "high"
        return "normal"

    return [
        {
            "reviewer_name": r["reviewer__display_name"],
            "review_count": r["review_count"],
            "workload_level": classify(r["review_count"]),
        }
        for r in reviews
    ]


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


def get_reviewer_correlations(team: Team) -> list[dict]:
    """Get reviewer correlation data for a team.

    Returns all reviewer pairs with their agreement statistics, ordered by
    the number of PRs reviewed together (most active pairs first).

    Args:
        team: Team instance

    Returns:
        list of dicts with keys:
            - reviewer_1_name (str): First reviewer display name
            - reviewer_2_name (str): Second reviewer display name
            - prs_reviewed_together (int): Count of PRs reviewed together
            - agreement_rate (Decimal): Agreement percentage (0.00 to 100.00)
            - is_redundant (bool): Whether the pair shows redundancy (95%+ agreement on 10+ PRs)
    """
    from apps.metrics.models import ReviewerCorrelation

    correlations = (
        ReviewerCorrelation.objects.filter(team=team)
        .select_related("reviewer_1", "reviewer_2")
        .order_by("-prs_reviewed_together")
    )

    return [
        {
            "reviewer_1_name": c.reviewer_1.display_name,
            "reviewer_2_name": c.reviewer_2.display_name,
            "prs_reviewed_together": c.prs_reviewed_together,
            "agreement_rate": c.agreement_rate,
            "is_redundant": c.is_redundant,
        }
        for c in correlations
    ]


def get_copilot_by_member(
    team: Team, start_date: date, end_date: date, limit: int = 5, repo: str | None = None
) -> list[dict]:
    """Get Copilot metrics breakdown by member.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum number of members to return (default 5)
        repo: Optional repository filter (not applicable - Copilot data is not repo-specific)

    Returns:
        list of dicts with keys:
            - member_name (str): Team member display name
            - suggestions (int): Total suggestions shown
            - accepted (int): Total suggestions accepted
            - acceptance_rate (Decimal): Acceptance rate percentage

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

    # Group by member and calculate totals
    member_data = (
        copilot_usage.values("member__display_name", "member__github_id")
        .annotate(
            suggestions=Sum("suggestions_shown"),
            accepted=Sum("suggestions_accepted"),
        )
        .order_by("-suggestions")
    )

    result = []
    for entry in member_data:
        suggestions = entry["suggestions"] or 0
        accepted = entry["accepted"] or 0

        acceptance_rate = Decimal(str(round(accepted / suggestions * 100, 2))) if suggestions > 0 else Decimal("0.00")

        result.append(
            {
                "member_name": entry["member__display_name"],
                "avatar_url": _avatar_url_from_github_id(entry["member__github_id"]),
                "initials": _compute_initials(entry["member__display_name"]),
                "suggestions": suggestions,
                "accepted": accepted,
                "acceptance_rate": acceptance_rate,
            }
        )

    return result[:limit] if limit else result


def get_cicd_pass_rate(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get CI/CD pass rate metrics for a team within a date range.

    Aggregates check run results to show overall CI/CD health and
    identifies the most problematic checks.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - total_runs (int): Total check runs
            - pass_rate (Decimal): Percentage of successful runs (0.00 to 100.00)
            - success_count (int): Number of successful runs
            - failure_count (int): Number of failed runs
            - top_failing_checks (list): Top 5 checks with highest failure rates
    """
    check_runs = PRCheckRun.objects.filter(
        team=team,
        pull_request__merged_at__gte=start_of_day(start_date),
        pull_request__merged_at__lte=end_of_day(end_date),
        status="completed",
    )
    if repo:
        check_runs = check_runs.filter(pull_request__github_repo=repo)

    total_runs = check_runs.count()
    success_count = check_runs.filter(conclusion="success").count()
    failure_count = check_runs.filter(conclusion="failure").count()

    pass_rate = Decimal(str(round(success_count * 100.0 / total_runs, 2))) if total_runs > 0 else Decimal("0.00")

    # Get top failing checks
    check_stats = (
        check_runs.values("name")
        .annotate(
            total=Count("id"),
            failures=Count("id", filter=Q(conclusion="failure")),
        )
        .filter(failures__gt=0)
        .order_by("-failures")[:5]
    )

    top_failing_checks = [
        {
            "name": stat["name"],
            "total": stat["total"],
            "failures": stat["failures"],
            "failure_rate": Decimal(str(round(stat["failures"] * 100.0 / stat["total"], 2))),
        }
        for stat in check_stats
    ]

    return {
        "total_runs": total_runs,
        "pass_rate": pass_rate,
        "success_count": success_count,
        "failure_count": failure_count,
        "top_failing_checks": top_failing_checks,
    }


def get_deployment_metrics(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get DORA-style deployment metrics for a team within a date range.

    Calculates deployment frequency and success rate, key DevOps metrics.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - total_deployments (int): Total deployments
            - production_deployments (int): Production deployments
            - success_rate (Decimal): Percentage of successful deployments
            - deployments_per_week (Decimal): Average deployments per week
            - by_environment (list): Breakdown by environment
    """
    deployments = Deployment.objects.filter(
        team=team,
        deployed_at__gte=start_of_day(start_date),
        deployed_at__lte=end_of_day(end_date),
    )
    if repo:
        deployments = deployments.filter(github_repo=repo)

    total = deployments.count()
    production = deployments.filter(environment="production").count()
    successful = deployments.filter(status="success").count()

    success_rate = Decimal(str(round(successful * 100.0 / total, 2))) if total > 0 else Decimal("0.00")

    # Calculate deployments per week
    days = (end_date - start_date).days or 1
    weeks = max(days / 7, 1)
    deployments_per_week = Decimal(str(round(total / weeks, 2)))

    # Breakdown by environment
    by_environment = (
        deployments.values("environment")
        .annotate(
            total=Count("id"),
            successful=Count("id", filter=Q(status="success")),
        )
        .order_by("-total")
    )

    env_breakdown = [
        {
            "environment": env["environment"],
            "total": env["total"],
            "successful": env["successful"],
            "success_rate": Decimal(str(round(env["successful"] * 100.0 / env["total"], 2)))
            if env["total"] > 0
            else Decimal("0.00"),
        }
        for env in by_environment
    ]

    return {
        "total_deployments": total,
        "production_deployments": production,
        "success_rate": success_rate,
        "deployments_per_week": deployments_per_week,
        "by_environment": env_breakdown,
    }


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


# =============================================================================
# AI Detection Metrics (from PR content analysis)
# =============================================================================
# These functions use the new is_ai_assisted, ai_tools_detected, is_ai_review,
# and ai_reviewer_type fields populated by the ai_detector service during seeding.


def get_ai_detected_metrics(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get AI detection metrics based on PR content analysis.

    Unlike get_key_metrics which uses survey responses, this uses direct
    detection from PR body, commit messages, and co-authors.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - total_prs (int): Total merged PRs
            - ai_assisted_prs (int): PRs detected as AI-assisted
            - ai_assisted_pct (Decimal): Percentage (0.00 to 100.00)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    stats = prs.aggregate(
        total_prs=Count("id"),
        ai_assisted_prs=Count("id", filter=Q(is_ai_assisted=True)),
    )

    total_prs = stats["total_prs"]
    ai_assisted_prs = stats["ai_assisted_prs"]

    ai_assisted_pct = Decimal(str(round(ai_assisted_prs * 100.0 / total_prs, 2))) if total_prs > 0 else Decimal("0.00")

    return {
        "total_prs": total_prs,
        "ai_assisted_prs": ai_assisted_prs,
        "ai_assisted_pct": ai_assisted_pct,
    }


def get_ai_tool_breakdown(team: Team, start_date: date, end_date: date, repo: str | None = None) -> list[dict]:
    """Get breakdown of AI tools detected in PRs.

    Counts how many PRs used each AI tool (claude_code, copilot, cursor, etc.)
    based on the ai_tools_detected JSONField. Includes category information.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - tool (str): AI tool identifier
            - count (int): Number of PRs using this tool
            - category (str | None): "code", "review", or None if excluded
        Sorted by category then count descending.
    """
    from apps.metrics.services.ai_categories import get_tool_category, is_excluded_tool

    prs = _get_merged_prs_in_range(team, start_date, end_date).filter(is_ai_assisted=True)
    prs = _apply_repo_filter(prs, repo)

    # Count occurrences of each tool
    tool_counts: dict[str, int] = {}
    for pr in prs:
        for tool in pr.ai_tools_detected:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

    # Convert to list with category, excluding excluded tools
    result = []
    for tool, count in tool_counts.items():
        if is_excluded_tool(tool):
            continue  # Skip excluded tools like snyk, mintlify
        category = get_tool_category(tool)
        result.append({"tool": tool, "count": count, "category": category})

    # Sort by category (code first, then review) then by count descending
    category_order = {"code": 0, "review": 1}
    result.sort(key=lambda x: (category_order.get(x["category"], 2), -x["count"]))

    return result


def get_ai_category_breakdown(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get breakdown of PRs by AI category (code vs review).

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - total_ai_prs (int): Total AI-assisted PRs
            - code_ai_count (int): PRs with code AI tools
            - review_ai_count (int): PRs with review AI tools
            - both_ai_count (int): PRs with both code and review tools
            - code_ai_pct (float): Percentage with code AI
            - review_ai_pct (float): Percentage with review AI
    """
    from apps.metrics.services.ai_categories import (
        CATEGORY_BOTH,
        CATEGORY_CODE,
        CATEGORY_REVIEW,
        get_ai_category,
    )

    prs = _get_merged_prs_in_range(team, start_date, end_date).filter(is_ai_assisted=True)
    prs = _apply_repo_filter(prs, repo)

    code_count = 0
    review_count = 0
    both_count = 0

    for pr in prs:
        # Use effective_ai_tools for LLM priority
        tools = pr.effective_ai_tools
        category = get_ai_category(tools)
        if category == CATEGORY_CODE:
            code_count += 1
        elif category == CATEGORY_REVIEW:
            review_count += 1
        elif category == CATEGORY_BOTH:
            both_count += 1

    total = prs.count()

    return {
        "total_ai_prs": total,
        "code_ai_count": code_count,
        "review_ai_count": review_count,
        "both_ai_count": both_count,
        "code_ai_pct": round(code_count * 100.0 / total, 1) if total > 0 else 0.0,
        "review_ai_pct": round(review_count * 100.0 / total, 1) if total > 0 else 0.0,
        "both_ai_pct": round(both_count * 100.0 / total, 1) if total > 0 else 0.0,
    }


def get_ai_bot_review_stats(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get statistics about AI bot reviews.

    Uses the is_ai_review and ai_reviewer_type fields on PRReview model
    to track reviews from CodeRabbit, Copilot, Dependabot, etc.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - total_reviews (int): Total reviews in date range
            - ai_reviews (int): Reviews by AI bots
            - ai_review_pct (Decimal): Percentage of AI reviews
            - by_bot (list): Breakdown by bot type with count
    """
    reviews = PRReview.objects.filter(
        team=team,
        submitted_at__gte=start_of_day(start_date),
        submitted_at__lte=end_of_day(end_date),
    )
    # Filter by repository through the pull_request relationship
    if repo:
        reviews = reviews.filter(pull_request__github_repo=repo)

    stats = reviews.aggregate(
        total_reviews=Count("id"),
        ai_reviews=Count("id", filter=Q(is_ai_review=True)),
    )

    total_reviews = stats["total_reviews"]
    ai_reviews = stats["ai_reviews"]

    ai_review_pct = Decimal(str(round(ai_reviews * 100.0 / total_reviews, 2))) if total_reviews > 0 else Decimal("0.00")

    # Get breakdown by bot type
    bot_breakdown = (
        reviews.filter(is_ai_review=True).values("ai_reviewer_type").annotate(count=Count("id")).order_by("-count")
    )

    by_bot = [{"bot_type": b["ai_reviewer_type"], "count": b["count"]} for b in bot_breakdown]

    return {
        "total_reviews": total_reviews,
        "ai_reviews": ai_reviews,
        "ai_review_pct": ai_review_pct,
        "by_bot": by_bot,
    }


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


def get_response_channel_distribution(
    team: Team, start_date: date = None, end_date: date = None, repo: str | None = None
) -> dict:
    """Get survey response channel distribution for authors and reviewers.

    Counts responses by channel (github, slack, web, auto) to show which
    channels users are responding from.

    Args:
        team: Team instance
        start_date: Start date (inclusive), optional
        end_date: End date (inclusive), optional
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - author_responses: dict with counts by channel (github, slack, web, auto, total)
            - reviewer_responses: dict with counts by channel (github, slack, web, total)
            - percentages: dict with author and reviewer percentage breakdowns
    """
    # Build base queryset for surveys filtered by date range
    surveys_qs = PRSurvey.objects.filter(team=team)
    surveys_qs = _filter_by_date_range(surveys_qs, "pull_request__merged_at", start_date, end_date)
    if repo:
        surveys_qs = surveys_qs.filter(pull_request__github_repo=repo)

    # Count author responses by channel (only where author_responded_at is not null)
    author_responses_qs = surveys_qs.filter(author_responded_at__isnull=False)
    author_stats = author_responses_qs.aggregate(
        github=Count("id", filter=Q(author_response_source="github")),
        slack=Count("id", filter=Q(author_response_source="slack")),
        web=Count("id", filter=Q(author_response_source="web")),
        auto=Count("id", filter=Q(author_response_source="auto")),
        total=Count("id"),
    )

    # Build base queryset for reviewer responses filtered by date range
    reviews_qs = PRSurveyReview.objects.filter(team=team)
    reviews_qs = _filter_by_date_range(reviews_qs, "survey__pull_request__merged_at", start_date, end_date)
    if repo:
        reviews_qs = reviews_qs.filter(survey__pull_request__github_repo=repo)

    # Count reviewer responses by channel (only where responded_at is not null)
    reviewer_responses_qs = reviews_qs.filter(responded_at__isnull=False)
    reviewer_stats = reviewer_responses_qs.aggregate(
        github=Count("id", filter=Q(response_source="github")),
        slack=Count("id", filter=Q(response_source="slack")),
        web=Count("id", filter=Q(response_source="web")),
        total=Count("id"),
    )

    # Calculate percentages using helper function
    author_percentages = _calculate_channel_percentages(author_stats, ["github", "slack", "web", "auto"])
    reviewer_percentages = _calculate_channel_percentages(reviewer_stats, ["github", "slack", "web"])

    return {
        "author_responses": {
            "github": author_stats["github"],
            "slack": author_stats["slack"],
            "web": author_stats["web"],
            "auto": author_stats["auto"],
            "total": author_stats["total"],
        },
        "reviewer_responses": {
            "github": reviewer_stats["github"],
            "slack": reviewer_stats["slack"],
            "web": reviewer_stats["web"],
            "total": reviewer_stats["total"],
        },
        "percentages": {
            "author": author_percentages,
            "reviewer": reviewer_percentages,
        },
    }


def get_ai_detection_metrics(
    team: Team, start_date: date = None, end_date: date = None, repo: str | None = None
) -> dict:
    """Get AI auto-detection metrics for dashboard analytics.

    Analyzes survey responses to show how well AI auto-detection performs
    compared to self-reported AI usage. Used to track AI detection coverage.

    Args:
        team: Team instance
        start_date: Start date (inclusive), optional
        end_date: End date (inclusive), optional
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - auto_detected_count (int): PRs where AI was auto-detected
            - self_reported_count (int): PRs where author self-reported AI
            - not_ai_count (int): PRs where author reported no AI usage
            - no_response_count (int): Surveys without author response
            - total_surveys (int): Total surveys in date range
            - auto_detection_rate (Decimal): % of AI PRs that were auto-detected
            - ai_usage_rate (Decimal): % of all surveys that used AI
    """
    # Build base queryset for surveys filtered by date range
    surveys_qs = PRSurvey.objects.filter(team=team)
    surveys_qs = _filter_by_date_range(surveys_qs, "pull_request__merged_at", start_date, end_date)
    if repo:
        surveys_qs = surveys_qs.filter(pull_request__github_repo=repo)

    # Aggregate counts using conditional aggregation
    stats = surveys_qs.aggregate(
        auto_detected_count=Count("id", filter=Q(author_response_source="auto", author_ai_assisted=True)),
        self_reported_count=Count(
            "id",
            filter=Q(author_ai_assisted=True, author_response_source__in=["github", "slack", "web"]),
        ),
        not_ai_count=Count("id", filter=Q(author_ai_assisted=False, author_responded_at__isnull=False)),
        no_response_count=Count("id", filter=Q(author_responded_at__isnull=True)),
        total_surveys=Count("id"),
    )

    auto_detected_count = stats["auto_detected_count"]
    self_reported_count = stats["self_reported_count"]
    total_ai_count = auto_detected_count + self_reported_count
    total_surveys = stats["total_surveys"]

    # Calculate auto-detection rate (what % of AI PRs were auto-detected)
    if total_ai_count > 0:
        auto_detection_rate = Decimal(str(round(auto_detected_count * 100.0 / total_ai_count, 2)))
    else:
        auto_detection_rate = Decimal("0.00")

    # Calculate AI usage rate (what % of all surveys used AI)
    if total_surveys > 0:
        ai_usage_rate = Decimal(str(round(total_ai_count * 100.0 / total_surveys, 2)))
    else:
        ai_usage_rate = Decimal("0.00")

    return {
        "auto_detected_count": auto_detected_count,
        "self_reported_count": self_reported_count,
        "not_ai_count": stats["not_ai_count"],
        "no_response_count": stats["no_response_count"],
        "total_surveys": total_surveys,
        "auto_detection_rate": auto_detection_rate,
        "ai_usage_rate": ai_usage_rate,
    }


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


def get_response_time_metrics(
    team: Team, start_date: date = None, end_date: date = None, repo: str | None = None
) -> dict:
    """Get survey response time metrics for authors and reviewers.

    Calculates average response times from PR merge to survey response,
    broken down by channel (github, slack, web). Excludes auto-detected
    author responses as they don't represent real response times.

    Args:
        team: Team instance
        start_date: Start date (inclusive), optional
        end_date: End date (inclusive), optional
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - author_avg_response_time (Decimal): Average author response time in hours
            - reviewer_avg_response_time (Decimal): Average reviewer response time in hours
            - by_channel (dict): Response times by channel for authors and reviewers
            - total_author_responses (int): Count of author responses (excluding auto)
            - total_reviewer_responses (int): Count of reviewer responses
    """
    # Build base queryset for surveys filtered by date range
    surveys_qs = PRSurvey.objects.filter(team=team)
    surveys_qs = _filter_by_date_range(surveys_qs, "pull_request__merged_at", start_date, end_date)
    if repo:
        surveys_qs = surveys_qs.filter(pull_request__github_repo=repo)

    # Get author responses (excluding auto-detected, only real responses from github/slack/web)
    author_responses = surveys_qs.filter(
        author_responded_at__isnull=False, author_response_source__in=["github", "slack", "web"]
    ).select_related("pull_request")

    # Calculate author response times
    author_times = []
    author_times_by_channel = {"github": [], "slack": [], "web": []}

    for survey in author_responses:
        if survey.pull_request.merged_at and survey.author_responded_at:
            time_diff = survey.author_responded_at - survey.pull_request.merged_at
            hours = Decimal(str(round(time_diff.total_seconds() / 3600, 2)))
            author_times.append(hours)

            channel = survey.author_response_source
            if channel in author_times_by_channel:
                author_times_by_channel[channel].append(hours)

    # Calculate author averages using helper function
    author_avg_response_time, author_channel_avgs = _calculate_average_response_times(
        author_times, author_times_by_channel
    )

    # Build base queryset for reviewer responses filtered by date range
    reviews_qs = PRSurveyReview.objects.filter(team=team)
    reviews_qs = _filter_by_date_range(reviews_qs, "survey__pull_request__merged_at", start_date, end_date)
    if repo:
        reviews_qs = reviews_qs.filter(survey__pull_request__github_repo=repo)

    # Get reviewer responses
    reviewer_responses = reviews_qs.filter(responded_at__isnull=False).select_related("survey__pull_request")

    # Calculate reviewer response times
    reviewer_times = []
    reviewer_times_by_channel = {"github": [], "slack": [], "web": []}

    for review in reviewer_responses:
        if review.survey.pull_request.merged_at and review.responded_at:
            time_diff = review.responded_at - review.survey.pull_request.merged_at
            hours = Decimal(str(round(time_diff.total_seconds() / 3600, 2)))
            reviewer_times.append(hours)

            channel = review.response_source
            if channel in reviewer_times_by_channel:
                reviewer_times_by_channel[channel].append(hours)

    # Calculate reviewer averages using helper function
    reviewer_avg_response_time, reviewer_channel_avgs = _calculate_average_response_times(
        reviewer_times, reviewer_times_by_channel
    )

    return {
        "author_avg_response_time": author_avg_response_time,
        "reviewer_avg_response_time": reviewer_avg_response_time,
        "by_channel": {
            "author": author_channel_avgs,
            "reviewer": reviewer_channel_avgs,
        },
        "total_author_responses": len(author_times),
        "total_reviewer_responses": len(reviewer_times),
    }


# =============================================================================
# Monthly Aggregation Functions (for Trend Charts)
# =============================================================================


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


# =============================================================================
# Sparkline Data (for Key Metric Cards)
# =============================================================================


def get_sparkline_data(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get sparkline data for key metric cards.

    Returns 12 weeks of data for each metric, along with change percentage
    and trend direction for display in small inline charts.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository filter (owner/repo format)

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
    ai_adoption_data = (
        prs.annotate(week=TruncWeek("merged_at"))
        .values("week")
        .annotate(
            total=Count("id"),
            ai_count=Count("id", filter=Q(is_ai_assisted=True)),
        )
        .order_by("week")
    )
    ai_adoption_values = [
        round((entry["ai_count"] / entry["total"]) * 100, 1) if entry["total"] > 0 else 0.0
        for entry in ai_adoption_data
    ]

    # Get weekly review time averages
    review_time_data = (
        prs.annotate(week=TruncWeek("merged_at")).values("week").annotate(avg=Avg("review_time_hours")).order_by("week")
    )
    review_time_values = [float(entry["avg"]) if entry["avg"] else 0.0 for entry in review_time_data]

    def _calculate_change_and_trend(values: list) -> tuple[int, str]:
        """Calculate change percentage and trend direction from values list."""
        if len(values) < 2:
            return 0, "flat"

        first_val = values[0]
        last_val = values[-1]

        if first_val == 0:
            if last_val > 0:
                return 100, "up"
            return 0, "flat"

        change_pct = int(round(((last_val - first_val) / first_val) * 100))

        if change_pct > 0:
            trend = "up"
        elif change_pct < 0:
            trend = "down"
        else:
            trend = "flat"

        return change_pct, trend

    prs_merged_change, prs_merged_trend = _calculate_change_and_trend(prs_merged_values)
    cycle_time_change, cycle_time_trend = _calculate_change_and_trend(cycle_time_values)
    ai_adoption_change, ai_adoption_trend = _calculate_change_and_trend(ai_adoption_values)
    review_time_change, review_time_trend = _calculate_change_and_trend(review_time_values)

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


def _is_valid_category(category: str) -> bool:
    """Check if a category is valid (not empty, not '{}', not None)."""
    if not category or isinstance(category, dict):
        return False
    category_str = str(category).strip()
    return bool(category_str) and category_str not in ("{}", "[]", "None", "null")


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


# =============================================================================
# Dashboard Merge: Needs Attention & AI Impact Functions
# =============================================================================


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


def get_ai_impact_stats(team: Team, start_date: date, end_date: date) -> dict:
    """Get AI impact statistics comparing AI-assisted vs non-AI PRs.

    Uses the `effective_is_ai_assisted` property which prioritizes:
    LLM detection > pattern detection > survey data

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        dict with keys:
            - ai_adoption_pct: Decimal percentage of AI-assisted PRs (0.00 to 100.00)
            - avg_cycle_with_ai: Decimal average cycle time in hours for AI PRs (or None)
            - avg_cycle_without_ai: Decimal average cycle time in hours for non-AI PRs (or None)
            - cycle_time_difference_pct: Decimal percentage difference (negative = AI faster)
            - total_prs: int total PRs in period
            - ai_prs: int count of AI-assisted PRs
    """
    # Get all merged PRs in range
    prs = list(_get_merged_prs_in_range(team, start_date, end_date))

    total_prs = len(prs)

    if total_prs == 0:
        return {
            "ai_adoption_pct": Decimal("0.00"),
            "avg_cycle_with_ai": None,
            "avg_cycle_without_ai": None,
            "cycle_time_difference_pct": None,
            "total_prs": 0,
            "ai_prs": 0,
        }

    # Separate PRs by AI status using effective_is_ai_assisted property
    ai_prs = []
    non_ai_prs = []

    for pr in prs:
        if pr.effective_is_ai_assisted:
            ai_prs.append(pr)
        else:
            non_ai_prs.append(pr)

    ai_count = len(ai_prs)

    # Calculate adoption percentage
    ai_adoption_pct = Decimal(str(round(ai_count * 100.0 / total_prs, 2)))

    # Calculate average cycle times (only PRs with cycle_time_hours)
    ai_cycle_times = [pr.cycle_time_hours for pr in ai_prs if pr.cycle_time_hours is not None]
    non_ai_cycle_times = [pr.cycle_time_hours for pr in non_ai_prs if pr.cycle_time_hours is not None]

    avg_cycle_with_ai = None
    avg_cycle_without_ai = None
    cycle_time_difference_pct = None

    if ai_cycle_times:
        avg_cycle_with_ai = Decimal(str(round(sum(ai_cycle_times) / len(ai_cycle_times), 2)))

    if non_ai_cycle_times:
        avg_cycle_without_ai = Decimal(str(round(sum(non_ai_cycle_times) / len(non_ai_cycle_times), 2)))

    # Calculate difference percentage if both averages are available
    if avg_cycle_with_ai is not None and avg_cycle_without_ai is not None and avg_cycle_without_ai > 0:
        diff = ((avg_cycle_with_ai - avg_cycle_without_ai) / avg_cycle_without_ai) * 100
        cycle_time_difference_pct = Decimal(str(round(float(diff), 2)))

    return {
        "ai_adoption_pct": ai_adoption_pct,
        "avg_cycle_with_ai": avg_cycle_with_ai,
        "avg_cycle_without_ai": avg_cycle_without_ai,
        "cycle_time_difference_pct": cycle_time_difference_pct,
        "total_prs": total_prs,
        "ai_prs": ai_count,
    }


def get_team_velocity(team: Team, start_date: date, end_date: date, limit: int = 5) -> list[dict]:
    """Get top contributors by PR count with average cycle time.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum number of contributors to return (default 5)

    Returns:
        list of dicts ordered by PR count descending, then display_name alphabetically:
            - member_id: int TeamMember ID
            - display_name: str member's display name
            - avatar_url: str member's avatar URL
            - pr_count: int number of PRs merged
            - avg_cycle_time: Decimal average cycle time in hours (or None)
    """
    # Get all merged PRs in range with author info
    prs = _get_merged_prs_in_range(team, start_date, end_date).select_related("author")

    # Group PRs by author
    author_prs: dict[int, list] = {}
    author_info: dict[int, dict] = {}

    for pr in prs:
        if not pr.author:
            continue

        author_id = pr.author.id
        if author_id not in author_prs:
            author_prs[author_id] = []
            author_info[author_id] = {
                "member_id": pr.author.id,
                "display_name": pr.author.display_name or "Unknown",
                "avatar_url": _avatar_url_from_github_id(pr.author.github_id),
            }
        author_prs[author_id].append(pr)

    # Calculate stats for each author
    results = []
    for author_id, prs_list in author_prs.items():
        pr_count = len(prs_list)

        # Calculate avg cycle time (only PRs with cycle_time_hours)
        cycle_times = [pr.cycle_time_hours for pr in prs_list if pr.cycle_time_hours is not None]
        avg_cycle_time = None
        if cycle_times:
            avg = sum(cycle_times) / len(cycle_times)
            avg_cycle_time = Decimal(str(round(float(avg), 1)))

        results.append(
            {
                **author_info[author_id],
                "pr_count": pr_count,
                "avg_cycle_time": avg_cycle_time,
            }
        )

    # Sort by pr_count descending, then display_name ascending
    results.sort(key=lambda x: (-x["pr_count"], x["display_name"]))

    return results[:limit]


def detect_review_bottleneck(
    team: Team,
    start_date: date,
    end_date: date,  # noqa: ARG001
) -> dict | None:
    """Detect if any reviewer has > 3x average pending reviews.

    "Pending reviews" are defined as open PRs that a reviewer has reviewed.
    This represents ongoing review work where PRs haven't been merged yet.

    Note: Date parameters are accepted for API consistency but not used.
    We look at ALL currently open PRs since pending work is independent of
    when the PR was created.

    Args:
        team: Team instance
        start_date: Unused (kept for API consistency)
        end_date: Unused (kept for API consistency)

    Returns:
        dict with bottleneck info if detected:
            - reviewer_name: str display name of bottleneck reviewer
            - pending_count: int number of open PRs they've reviewed
            - team_avg: float average pending reviews across all reviewers
        None if no bottleneck detected (no one exceeds 3x threshold)
    """
    # Get distinct open PRs per reviewer
    # Count distinct PRs (not reviews) - a reviewer might review same PR multiple times
    reviewer_stats = list(
        PRReview.objects.filter(
            team=team,
            pull_request__state="open",
        )
        .values("reviewer__id", "reviewer__display_name")
        .annotate(pending_count=Count("pull_request", distinct=True))
    )

    if not reviewer_stats:
        return None

    # Build list of reviewer counts
    reviewer_counts = [
        {
            "reviewer_name": stat["reviewer__display_name"] or "Unknown",
            "pending_count": stat["pending_count"],
        }
        for stat in reviewer_stats
    ]

    if len(reviewer_counts) < 2:
        # Can't have a bottleneck with only 1 reviewer (no comparison)
        return None

    # Calculate team average
    total = sum(r["pending_count"] for r in reviewer_counts)
    team_avg = total / len(reviewer_counts)
    threshold = team_avg * 3

    # Find bottlenecks (> 3x threshold)
    bottlenecks = [r for r in reviewer_counts if r["pending_count"] > threshold]

    if not bottlenecks:
        return None

    # Return the worst bottleneck (highest pending count)
    worst = max(bottlenecks, key=lambda x: x["pending_count"])

    return {
        "reviewer_name": worst["reviewer_name"],
        "pending_count": worst["pending_count"],
        "team_avg": round(team_avg, 1),
    }
