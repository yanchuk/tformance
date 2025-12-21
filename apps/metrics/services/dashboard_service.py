"""Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

import statistics
from datetime import date
from decimal import Decimal

from django.db.models import Avg, Case, CharField, Count, Q, QuerySet, Sum, Value, When
from django.db.models.functions import TruncWeek

from apps.metrics.models import (
    AIUsageDaily,
    Deployment,
    PRCheckRun,
    PRFile,
    PRReview,
    PRSurvey,
    PRSurveyReview,
    PullRequest,
    TeamMember,
)
from apps.teams.models import Team

# PR Size Categories
# Categories based on total lines changed (additions + deletions)
PR_SIZE_XS_MAX = 10
PR_SIZE_S_MAX = 50
PR_SIZE_M_MAX = 200
PR_SIZE_L_MAX = 500


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
        merged_at__gte=start_date,
        merged_at__lte=end_date,
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


def get_key_metrics(team: Team, start_date: date, end_date: date) -> dict:
    """Get key metrics for a team within a date range.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        dict with keys:
            - prs_merged (int): Count of merged PRs
            - avg_cycle_time (Decimal or None): Average cycle time in hours
            - avg_quality_rating (Decimal or None): Average quality rating
            - ai_assisted_pct (Decimal): Percentage of AI-assisted PRs (0.00 to 100.00)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)

    prs_merged = prs.count()

    # Calculate average cycle time
    avg_cycle_time = prs.aggregate(avg=Avg("cycle_time_hours"))["avg"]

    # Calculate average quality rating from survey reviews
    reviews = PRSurveyReview.objects.filter(survey__pull_request__in=prs)
    avg_quality_rating = reviews.aggregate(avg=Avg("quality_rating"))["avg"]

    # Calculate AI-assisted percentage
    surveys = PRSurvey.objects.filter(pull_request__in=prs)
    ai_assisted_pct = _calculate_ai_percentage(surveys)

    return {
        "prs_merged": prs_merged,
        "avg_cycle_time": avg_cycle_time,
        "avg_quality_rating": avg_quality_rating,
        "ai_assisted_pct": ai_assisted_pct,
    }


def get_ai_adoption_trend(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get AI adoption trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list of dicts with keys:
            - week (date): Week start date
            - value (float): AI adoption percentage for that week
    """
    # Get merged PRs in date range with surveys
    prs = _get_merged_prs_in_range(team, start_date, end_date).filter(survey__isnull=False)

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
        result.append({"week": entry["week"], "value": pct})

    return result


def get_ai_quality_comparison(team: Team, start_date: date, end_date: date) -> dict:
    """Get quality comparison between AI-assisted and non-AI PRs.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        dict with keys:
            - ai_avg (Decimal or None): Average quality rating for AI-assisted PRs
            - non_ai_avg (Decimal or None): Average quality rating for non-AI PRs
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)

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
    team: Team, start_date: date, end_date: date, metric_field: str, result_key: str = "avg_metric"
) -> list[dict]:
    """Get weekly trend for a given metric field.

    Generic helper to calculate weekly averages for any numeric PR field.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        metric_field: Name of the PR model field to average
        result_key: Key name for the aggregated result in the query

    Returns:
        list of dicts with keys:
            - week (date): Week start date
            - value (float): Average metric value for that week (0.0 if None)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)

    # Group by week and calculate average metric
    weekly_data = (
        prs.annotate(week=TruncWeek("merged_at"))
        .values("week")
        .annotate(**{result_key: Avg(metric_field)})
        .order_by("week")
    )

    result = []
    for entry in weekly_data:
        result.append(
            {
                "week": entry["week"],
                "value": entry[result_key] if entry[result_key] else 0.0,
            }
        )

    return result


def get_cycle_time_trend(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get cycle time trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list of dicts with keys:
            - week (date): Week start date
            - value (float): Average cycle time in hours for that week
    """
    return _get_metric_trend(team, start_date, end_date, "cycle_time_hours", "avg_cycle_time")


def get_team_breakdown(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get team breakdown with metrics per member.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list of dicts with keys:
            - member_name (str): Team member display name
            - prs_merged (int): Count of merged PRs
            - avg_cycle_time (Decimal): Average cycle time in hours (0.00 if None)
            - ai_pct (float): AI adoption percentage (0.0 to 100.0)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)

    # Get unique authors
    member_ids = prs.values_list("author_id", flat=True).distinct()
    members = TeamMember.objects.filter(id__in=member_ids)

    result = []
    for member in members:
        # Get PRs for this member
        member_prs = prs.filter(author=member)
        prs_merged = member_prs.count()

        # Calculate average cycle time
        avg_cycle_time = member_prs.aggregate(avg=Avg("cycle_time_hours"))["avg"]

        # Calculate AI percentage
        member_surveys = PRSurvey.objects.filter(pull_request__in=member_prs)
        ai_pct = float(_calculate_ai_percentage(member_surveys))

        result.append(
            {
                "member_name": member.display_name,
                "prs_merged": prs_merged,
                "avg_cycle_time": avg_cycle_time if avg_cycle_time else Decimal("0.00"),
                "ai_pct": ai_pct,
            }
        )

    return result


def get_ai_detective_leaderboard(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get AI detective leaderboard data.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list of dicts with keys:
            - member_name (str): Reviewer display name
            - correct (int): Number of correct guesses
            - total (int): Total number of guesses
            - percentage (float): Accuracy percentage (0.0 to 100.0)
    """
    # Query PRSurveyReview for guess accuracy
    reviews = (
        PRSurveyReview.objects.filter(
            team=team,
            responded_at__gte=start_date,
            responded_at__lte=end_date,
            guess_correct__isnull=False,
        )
        .values("reviewer__display_name")
        .annotate(
            total=Count("id"),
            correct=Count("id", filter=Q(guess_correct=True)),
        )
        .order_by("-correct")
    )

    return [
        {
            "member_name": r["reviewer__display_name"],
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
            responded_at__gte=start_date,
            responded_at__lte=end_date,
        )
        .values("reviewer__display_name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return [
        {
            "reviewer_name": r["reviewer__display_name"],
            "count": r["count"],
        }
        for r in reviews
    ]


def get_review_time_trend(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get review time trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list of dicts with keys:
            - week (date): Week start date
            - value (float): Average review time in hours for that week
    """
    return _get_metric_trend(team, start_date, end_date, "review_time_hours", "avg_review_time")


def get_recent_prs(team: Team, start_date: date, end_date: date, limit: int = 10) -> list[dict]:
    """Get recent PRs with AI status and quality scores.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum number of PRs to return (default 10)

    Returns:
        list of dicts with keys:
            - id (int): PR database ID
            - title (str): PR title
            - author (str): Author display name
            - merged_at (datetime): Merge timestamp
            - ai_assisted (bool or None): Whether AI-assisted, None if no survey
            - avg_quality (float or None): Average quality rating, None if no reviews
            - url (str): PR URL
    """
    prs = (
        _get_merged_prs_in_range(team, start_date, end_date)
        .select_related("author")
        .prefetch_related("survey", "survey__reviews")
        .order_by("-merged_at")[:limit]
    )

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
                "merged_at": pr.merged_at,
                "ai_assisted": ai_assisted,
                "avg_quality": avg_quality,
                "url": _get_github_url(pr),
            }
        )

    return result


def get_revert_hotfix_stats(team: Team, start_date: date, end_date: date) -> dict:
    """Get revert and hotfix statistics.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        dict with keys:
            - total_prs (int): Total merged PRs
            - revert_count (int): Count of revert PRs
            - hotfix_count (int): Count of hotfix PRs
            - revert_pct (float): Percentage of reverts (0.0 to 100.0)
            - hotfix_pct (float): Percentage of hotfixes (0.0 to 100.0)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)

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


def get_pr_size_distribution(team: Team, start_date: date, end_date: date) -> list[dict]:
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

    Returns:
        list of dicts with keys:
            - category (str): Size category (XS, S, M, L, XL)
            - count (int): Number of PRs in this category
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)

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


def get_unlinked_prs(team: Team, start_date: date, end_date: date, limit: int = 10) -> list[dict]:
    """Get merged PRs without Jira links.

    Returns PRs that have been merged within the date range but lack a Jira issue
    key association. Useful for identifying PRs that may need to be linked to
    work items for tracking purposes.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum number of PRs to return (default 10)

    Returns:
        list of dicts with keys:
            - title (str): PR title
            - author (str): Author display name
            - merged_at (datetime): Merge timestamp
            - url (str): PR URL
    """
    prs = (
        _get_merged_prs_in_range(team, start_date, end_date)
        .filter(jira_key="")
        .select_related("author")
        .order_by("-merged_at")[:limit]
    )

    return [
        {
            "title": pr.title,
            "author": _get_author_name(pr),
            "merged_at": pr.merged_at,
            "url": _get_github_url(pr),
        }
        for pr in prs
    ]


def get_reviewer_workload(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get reviewer workload with classification.

    Uses PRReview model (GitHub reviews). Classifies workload as:
    - low: below 25th percentile
    - normal: 25th-75th percentile
    - high: above 75th percentile

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list of dicts with keys:
            - reviewer_name (str): Reviewer display name
            - review_count (int): Number of reviews
            - workload_level (str): Classification (low, normal, high)
    """
    reviews = (
        PRReview.objects.filter(
            team=team,
            submitted_at__gte=start_date,
            submitted_at__lte=end_date,
        )
        .values("reviewer__display_name")
        .annotate(review_count=Count("id"))
        .order_by("-review_count")
    )

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


def get_copilot_metrics(team: Team, start_date: date, end_date: date) -> dict:
    """Get Copilot metrics summary for a team within a date range.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        dict with keys:
            - total_suggestions (int): Total suggestions shown
            - total_accepted (int): Total suggestions accepted
            - acceptance_rate (Decimal): Acceptance rate percentage (0.00 to 100.00)
            - active_users (int): Count of distinct members using Copilot
    """
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


def get_copilot_trend(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get Copilot acceptance rate trend by week.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list of dicts with keys:
            - week (date): Week start date
            - acceptance_rate (Decimal): Acceptance rate percentage for that week
    """
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


def get_iteration_metrics(team: Team, start_date: date, end_date: date) -> dict:
    """Get iteration metrics averages for merged PRs within a date range.

    Aggregates iteration metrics (review rounds, fix response time, etc.)
    from PRs that have been analyzed by the sync pipeline.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        dict with keys:
            - avg_review_rounds (Decimal or None): Average review rounds
            - avg_fix_response_hours (Decimal or None): Average fix response time
            - avg_commits_after_first_review (Decimal or None): Average commits after first review
            - avg_total_comments (Decimal or None): Average total comments
            - prs_with_metrics (int): Count of PRs with iteration metrics
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)

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


def get_copilot_by_member(team: Team, start_date: date, end_date: date) -> list[dict]:
    """Get Copilot metrics breakdown by member.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        list of dicts with keys:
            - member_name (str): Team member display name
            - suggestions (int): Total suggestions shown
            - accepted (int): Total suggestions accepted
            - acceptance_rate (Decimal): Acceptance rate percentage
    """
    copilot_usage = AIUsageDaily.objects.filter(
        team=team,
        source="copilot",
        date__gte=start_date,
        date__lte=end_date,
    )

    # Group by member and calculate totals
    member_data = (
        copilot_usage.values("member__display_name")
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
                "suggestions": suggestions,
                "accepted": accepted,
                "acceptance_rate": acceptance_rate,
            }
        )

    return result


def get_cicd_pass_rate(team: Team, start_date: date, end_date: date) -> dict:
    """Get CI/CD pass rate metrics for a team within a date range.

    Aggregates check run results to show overall CI/CD health and
    identifies the most problematic checks.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

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
        pull_request__merged_at__gte=start_date,
        pull_request__merged_at__lte=end_date,
        status="completed",
    )

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


def get_deployment_metrics(team: Team, start_date: date, end_date: date) -> dict:
    """Get DORA-style deployment metrics for a team within a date range.

    Calculates deployment frequency and success rate, key DevOps metrics.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

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
        deployed_at__gte=start_date,
        deployed_at__lte=end_date,
    )

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


def get_file_category_breakdown(team: Team, start_date: date, end_date: date) -> dict:
    """Get file change breakdown by category for a team within a date range.

    Categorizes files changed in PRs to show where development effort
    is being spent (frontend, backend, tests, etc.).

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        dict with keys:
            - total_files (int): Total files changed
            - total_changes (int): Total lines changed (additions + deletions)
            - by_category (list): Breakdown by file category
    """
    files = PRFile.objects.filter(
        team=team,
        pull_request__merged_at__gte=start_date,
        pull_request__merged_at__lte=end_date,
    )

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
