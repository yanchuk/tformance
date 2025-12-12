"""Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, Q, QuerySet
from django.db.models.functions import TruncWeek

from apps.metrics.models import PRSurvey, PRSurveyReview, PullRequest, TeamMember
from apps.teams.models import Team


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
    prs = _get_merged_prs_in_range(team, start_date, end_date)

    # Group by week and calculate average cycle time
    weekly_data = (
        prs.annotate(week=TruncWeek("merged_at"))
        .values("week")
        .annotate(avg_cycle_time=Avg("cycle_time_hours"))
        .order_by("week")
    )

    result = []
    for entry in weekly_data:
        result.append(
            {
                "week": entry["week"],
                "value": entry["avg_cycle_time"] if entry["avg_cycle_time"] else 0.0,
            }
        )

    return result


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
