"""AI-related metrics for dashboard.

Functions for AI adoption, tool breakdown, quality comparison, and impact analysis.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncWeek

from apps.metrics.models import PRReview, PRSurvey, PRSurveyReview
from apps.metrics.services.dashboard._helpers import (
    _apply_repo_filter,
    _avatar_url_from_github_id,
    _compute_initials,
    _filter_by_date_range,
    _get_merged_prs_in_range,
)
from apps.teams.models import Team
from apps.utils.date_utils import end_of_day, start_of_day


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

    # Use .only() to limit fields fetched - we only need llm_summary and ai_tools_detected
    # for effective_ai_tools property. Avoids loading large 'body' column.
    prs = (
        _get_merged_prs_in_range(team, start_date, end_date)
        .filter(is_ai_assisted=True)
        .only("id", "llm_summary", "ai_tools_detected")
    )
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


def get_ai_impact_stats(
    team: Team,
    start_date: date,
    end_date: date,
    use_survey_data: bool | None = None,
    repo: str | None = None,
) -> dict:
    """Get AI impact statistics comparing AI-assisted vs non-AI PRs.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        use_survey_data: If True, use survey data (PRSurvey.author_ai_assisted) with
            detection fallback. If False/None (default), use only detection data
            (effective_is_ai_assisted which prioritizes LLM > pattern detection).
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - ai_adoption_pct: Decimal percentage of AI-assisted PRs (0.00 to 100.00)
            - avg_cycle_with_ai: Decimal average cycle time in hours for AI PRs (or None)
            - avg_cycle_without_ai: Decimal average cycle time in hours for non-AI PRs (or None)
            - cycle_time_difference_pct: Decimal percentage difference (negative = AI faster)
            - total_prs: int total PRs in period
            - ai_prs: int count of AI-assisted PRs
    """
    # Default to detection data; use survey data when use_survey_data=True
    use_surveys = use_survey_data if use_survey_data is not None else False

    # Get all merged PRs in range with survey data prefetched
    prs_qs = _get_merged_prs_in_range(team, start_date, end_date)
    prs_qs = _apply_repo_filter(prs_qs, repo)
    prs = list(prs_qs.prefetch_related("survey"))

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

    # Separate PRs by AI status based on data source
    ai_prs = []
    non_ai_prs = []

    for pr in prs:
        if use_surveys:
            # Survey-based: Use survey data with detection fallback
            try:
                survey = pr.survey
                if survey.author_ai_assisted is True:
                    ai_prs.append(pr)
                elif survey.author_ai_assisted is False:
                    non_ai_prs.append(pr)
                else:
                    # Survey exists but author_ai_assisted is None - use fallback
                    if pr.effective_is_ai_assisted:
                        ai_prs.append(pr)
                    else:
                        non_ai_prs.append(pr)
            except PRSurvey.DoesNotExist:
                # No survey - fall back to effective_is_ai_assisted
                if pr.effective_is_ai_assisted:
                    ai_prs.append(pr)
                else:
                    non_ai_prs.append(pr)
        else:
            # Detection-based: Use only effective_is_ai_assisted
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
