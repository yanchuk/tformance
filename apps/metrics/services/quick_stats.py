"""Service for calculating quick team statistics."""

from datetime import timedelta
from typing import Any

from django.db.models import Avg, Prefetch
from django.utils import timezone

from apps.metrics.models import PRSurvey, PRSurveyReview, PullRequest


def _calculate_percentage_change(current: int | float, previous: int | float) -> float:
    """Calculate percentage change between two values.

    Args:
        current: Current period value
        previous: Previous period value

    Returns:
        Percentage change. Returns 100.0 if previous is 0 and current > 0,
        otherwise returns 0.0 if both are 0.
    """
    if previous > 0:
        return ((current - previous) / previous) * 100
    elif current > 0:
        return 100.0
    else:
        return 0.0


def get_team_quick_stats(team, days: int = 7) -> dict[str, Any]:
    """Calculate quick stats for a team over a specified period.

    Args:
        team: The team to calculate stats for
        days: Number of days to look back (default: 7)

    Returns:
        Dictionary containing:
        - prs_merged: Count of PRs merged in period
        - prs_merged_change: % change vs previous period
        - avg_cycle_time_hours: Average cycle time, None if no data
        - cycle_time_change: % change vs previous period
        - ai_assisted_percent: % of PRs with AI assistance
        - ai_percent_change: Change in percentage points
        - avg_quality_rating: Average quality (1-3 scale), None if no data
        - quality_change: Change vs previous period
        - recent_activity: Last 5 activities
    """
    now = timezone.now()
    current_start = now - timedelta(days=days)
    previous_start = now - timedelta(days=days * 2)

    # Current period PRs
    current_prs = PullRequest.objects.filter(
        team=team,
        state="merged",
        merged_at__gte=current_start,
        merged_at__lt=now,
    )

    # Previous period PRs
    previous_prs = PullRequest.objects.filter(
        team=team,
        state="merged",
        merged_at__gte=previous_start,
        merged_at__lt=current_start,
    )

    # Calculate PR counts
    prs_merged = current_prs.count()
    previous_prs_count = previous_prs.count()

    # Calculate PR change
    prs_merged_change = _calculate_percentage_change(prs_merged, previous_prs_count)

    # Calculate average cycle time
    current_cycle_avg = current_prs.filter(cycle_time_hours__isnull=False).aggregate(avg=Avg("cycle_time_hours"))["avg"]
    previous_cycle_avg = previous_prs.filter(cycle_time_hours__isnull=False).aggregate(avg=Avg("cycle_time_hours"))[
        "avg"
    ]

    # Convert Decimal to float if not None
    avg_cycle_time_hours = float(current_cycle_avg) if current_cycle_avg is not None else None

    # Calculate cycle time change
    if current_cycle_avg is not None and previous_cycle_avg is not None:
        cycle_time_change = _calculate_percentage_change(float(current_cycle_avg), float(previous_cycle_avg))
    else:
        cycle_time_change = None

    # Calculate AI assisted percentage from surveys
    current_surveys = PRSurvey.objects.filter(
        team=team,
        pull_request__in=current_prs,
        author_ai_assisted__isnull=False,
    )
    previous_surveys = PRSurvey.objects.filter(
        team=team,
        pull_request__in=previous_prs,
        author_ai_assisted__isnull=False,
    )

    current_survey_count = current_surveys.count()
    current_ai_count = current_surveys.filter(author_ai_assisted=True).count()

    previous_survey_count = previous_surveys.count()
    previous_ai_count = previous_surveys.filter(author_ai_assisted=True).count()

    ai_assisted_percent = (current_ai_count / current_survey_count) * 100 if current_survey_count > 0 else 0.0
    previous_ai_percent = (previous_ai_count / previous_survey_count) * 100 if previous_survey_count > 0 else 0.0
    ai_percent_change = ai_assisted_percent - previous_ai_percent

    # Calculate quality ratings from survey reviews
    current_reviews = PRSurveyReview.objects.filter(
        team=team,
        survey__pull_request__in=current_prs,
        quality_rating__isnull=False,
    )
    previous_reviews = PRSurveyReview.objects.filter(
        team=team,
        survey__pull_request__in=previous_prs,
        quality_rating__isnull=False,
    )

    current_quality_avg = current_reviews.aggregate(avg=Avg("quality_rating"))["avg"]
    previous_quality_avg = previous_reviews.aggregate(avg=Avg("quality_rating"))["avg"]

    avg_quality_rating = float(current_quality_avg) if current_quality_avg is not None else None

    if current_quality_avg is not None and previous_quality_avg is not None:
        quality_change = float(current_quality_avg - previous_quality_avg)
    else:
        quality_change = None

    # Build recent activity
    recent_activity = []

    # Get recent merged PRs with prefetched surveys
    # Note: PRSurvey filter is safe because it's prefetching related objects from already team-filtered PRs
    survey_prefetch = Prefetch(
        "survey",
        queryset=PRSurvey.objects.filter(author_ai_assisted__isnull=False),  # noqa: TEAM001
    )
    recent_prs = current_prs.select_related("author").prefetch_related(survey_prefetch).order_by("-merged_at")[:10]

    for pr in recent_prs:
        ai_assisted = None
        try:
            if pr.survey.author_ai_assisted is not None:
                ai_assisted = pr.survey.author_ai_assisted
        except PRSurvey.DoesNotExist:
            pass

        recent_activity.append(
            {
                "type": "pr_merged",
                "title": pr.title,
                "author": pr.author.display_name if pr.author else "Unknown",
                "ai_assisted": ai_assisted,
                "timestamp": pr.merged_at,
            }
        )

    # Get recent completed surveys
    recent_surveys = (
        PRSurvey.objects.filter(
            team=team,
            pull_request__merged_at__gte=current_start,
            pull_request__merged_at__lt=now,
            author_ai_assisted__isnull=False,
            author_responded_at__isnull=False,
        )
        .select_related("pull_request", "author")
        .order_by("-author_responded_at")[:10]
    )

    for survey in recent_surveys:
        recent_activity.append(
            {
                "type": "survey_completed",
                "title": f"Survey for PR: {survey.pull_request.title}",
                "author": survey.author.display_name if survey.author else "Unknown",
                "ai_assisted": survey.author_ai_assisted,
                "timestamp": survey.author_responded_at,
            }
        )

    # Sort all activity by timestamp and take top 5
    recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
    recent_activity = recent_activity[:5]

    return {
        "prs_merged": {
            "count": prs_merged,
            "change_percent": prs_merged_change if previous_prs_count > 0 else None,
        },
        "avg_cycle_time": {
            "hours": avg_cycle_time_hours,
            "change_percent": cycle_time_change,
        },
        "ai_assisted": {
            "percent": ai_assisted_percent if current_survey_count > 0 else None,
            "change_points": ai_percent_change if previous_survey_count > 0 else None,
        },
        "avg_quality": {
            "rating": avg_quality_rating,
            "change": quality_change,
        },
        "recent_activity": recent_activity,
    }
