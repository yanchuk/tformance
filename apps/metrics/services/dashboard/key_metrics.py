"""Key metrics for dashboard overview.

Core KPIs displayed at the top of the dashboard.
"""

from datetime import date

from django.core.cache import cache
from django.db.models import Avg

from apps.metrics.models import PRSurvey, PRSurveyReview
from apps.metrics.services.dashboard._helpers import (
    _apply_repo_filter,
    _calculate_ai_percentage,
    _calculate_ai_percentage_from_detection,
    _get_key_metrics_cache_key,
    _get_merged_prs_in_range,
)
from apps.teams.models import Team

# Cache TTL for dashboard metrics (5 minutes)
DASHBOARD_CACHE_TTL = 300


def get_key_metrics(
    team: Team,
    start_date: date,
    end_date: date,
    repo: str | None = None,
    use_survey_data: bool | None = None,
) -> dict:
    """Get key metrics for a team within a date range.

    Results are cached for 5 minutes to improve dashboard performance.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)
        use_survey_data: If True, use survey data for AI adoption percentage.
            If False, use detection data (effective_is_ai_assisted).
            If None, defaults to False (detection-based).

    Returns:
        dict with keys:
            - prs_merged (int): Count of merged PRs
            - avg_cycle_time (Decimal or None): Average cycle time in hours
            - avg_review_time (Decimal or None): Average review time in hours
            - avg_quality_rating (Decimal or None): Average quality rating
            - ai_assisted_pct (Decimal): Percentage of AI-assisted PRs (0.00 to 100.00)
    """
    # Default to detection-based when use_survey_data is None
    use_surveys = use_survey_data if use_survey_data is not None else False

    # Check cache first (include repo and data source in cache key)
    data_source = "survey" if use_surveys else "detection"
    cache_key = _get_key_metrics_cache_key(team.id, start_date, end_date) + f":{repo or 'all'}:{data_source}"
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

    # Calculate AI-assisted percentage based on data source
    if use_surveys:
        surveys = PRSurvey.objects.filter(pull_request__in=prs)
        ai_assisted_pct = _calculate_ai_percentage(surveys)
    else:
        ai_assisted_pct = _calculate_ai_percentage_from_detection(prs)

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
