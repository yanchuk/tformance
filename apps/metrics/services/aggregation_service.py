"""
Service for aggregating weekly metrics per team member.

This service provides functions to compute and store weekly metrics for dashboards.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from apps.metrics.models import (
    Commit,
    PRSurvey,
    PRSurveyReview,
    PullRequest,
    TeamMember,
    WeeklyMetrics,
)


def get_week_boundaries(target_date: date) -> tuple[date, date]:
    """
    Get the Monday-Sunday boundaries for the week containing the given date.

    Args:
        target_date: Any date within the week

    Returns:
        Tuple of (week_start, week_end) where week_start is Monday and week_end is Sunday
    """
    # Get the weekday (0=Monday, 6=Sunday)
    weekday = target_date.weekday()

    # Calculate Monday of the week
    week_start = target_date - timedelta(days=weekday)

    # Calculate Sunday of the week
    week_end = week_start + timedelta(days=6)

    return week_start, week_end


def _get_week_datetime_range(week_start: date, week_end: date) -> tuple:
    """
    Convert week date boundaries to timezone-aware datetime range.

    Args:
        week_start: Start of the week (Monday)
        week_end: End of the week (Sunday)

    Returns:
        Tuple of (start_datetime, end_datetime) as timezone-aware datetimes
    """
    start_datetime = timezone.make_aware(timezone.datetime.combine(week_start, timezone.datetime.min.time()))
    end_datetime = timezone.make_aware(timezone.datetime.combine(week_end, timezone.datetime.max.time()))
    return start_datetime, end_datetime


def compute_member_weekly_metrics(
    team, member: TeamMember, week_start: date, week_end: date, use_survey_data: bool = False
) -> dict:
    """
    Compute weekly metrics for a single team member.

    Args:
        team: The team to filter data by
        member: The team member to compute metrics for
        week_start: Start of the week (Monday)
        week_end: End of the week (Sunday)
        use_survey_data: When True, use PRSurvey data for AI metrics.
                        When False (default), use effective_is_ai_assisted (detection).

    Returns:
        Dictionary with computed metrics
    """
    # Convert dates to timezone-aware datetime range for filtering
    start_datetime, end_datetime = _get_week_datetime_range(week_start, week_end)

    # Query merged PRs in the week
    merged_prs = PullRequest.objects.filter(
        team=team,
        author=member,
        state="merged",
        merged_at__gte=start_datetime,
        merged_at__lte=end_datetime,
    )

    # Aggregate PR metrics
    pr_aggregates = merged_prs.aggregate(
        prs_merged=Count("id"),
        avg_cycle_time_hours=Avg("cycle_time_hours"),
        avg_review_time_hours=Avg("review_time_hours"),
        lines_added=Sum("additions"),
        lines_removed=Sum("deletions"),
        revert_count=Count("id", filter=Q(is_revert=True)),
        hotfix_count=Count("id", filter=Q(is_hotfix=True)),
    )

    # Query commits in the week
    commits_count = Commit.objects.filter(
        team=team,
        author=member,
        committed_at__gte=start_datetime,
        committed_at__lte=end_datetime,
    ).count()

    # Calculate AI-assisted PRs based on data source
    if use_survey_data:
        # Use PRSurvey data for AI metrics
        surveys = PRSurvey.objects.filter(
            team=team,
            author=member,
            pull_request__merged_at__gte=start_datetime,
            pull_request__merged_at__lte=end_datetime,
        ).select_related("pull_request")
        ai_assisted_prs = surveys.filter(author_ai_assisted=True).count()
        surveys_completed = surveys.filter(author_responded_at__isnull=False).count()
    else:
        # Use detection data (effective_is_ai_assisted) for AI metrics
        ai_assisted_prs = sum(1 for pr in merged_prs if pr.effective_is_ai_assisted)
        # Query surveys only for completion count
        surveys = PRSurvey.objects.filter(
            team=team,
            author=member,
            pull_request__merged_at__gte=start_datetime,
            pull_request__merged_at__lte=end_datetime,
        )
        surveys_completed = surveys.filter(author_responded_at__isnull=False).count()

    # Query survey reviews for quality ratings (with select_related for optimization)
    reviews = PRSurveyReview.objects.filter(
        team=team,
        survey__author=member,
        survey__pull_request__merged_at__gte=start_datetime,
        survey__pull_request__merged_at__lte=end_datetime,
    ).select_related("survey__pull_request")

    review_aggregates = reviews.aggregate(
        avg_quality_rating=Avg("quality_rating"),
        total_guesses=Count("id", filter=Q(ai_guess__isnull=False)),
        correct_guesses=Count("id", filter=Q(guess_correct=True)),
    )

    # Calculate guess accuracy percentage
    guess_accuracy = None
    if review_aggregates["total_guesses"] and review_aggregates["total_guesses"] > 0:
        guess_accuracy = Decimal(
            (review_aggregates["correct_guesses"] / review_aggregates["total_guesses"]) * 100
        ).quantize(Decimal("0.01"))

    return {
        "prs_merged": pr_aggregates["prs_merged"] or 0,
        "avg_cycle_time_hours": pr_aggregates["avg_cycle_time_hours"],
        "avg_review_time_hours": pr_aggregates["avg_review_time_hours"],
        "commits_count": commits_count,
        "lines_added": pr_aggregates["lines_added"] or 0,
        "lines_removed": pr_aggregates["lines_removed"] or 0,
        "revert_count": pr_aggregates["revert_count"] or 0,
        "hotfix_count": pr_aggregates["hotfix_count"] or 0,
        "ai_assisted_prs": ai_assisted_prs,
        "avg_quality_rating": review_aggregates["avg_quality_rating"],
        "surveys_completed": surveys_completed,
        "guess_accuracy": guess_accuracy,
    }


def _batch_fetch_pr_metrics(team, member_ids: list[int], start_datetime, end_datetime) -> dict:
    """Batch fetch PR metrics for all members in a single query."""
    pr_aggregates = (
        PullRequest.objects.filter(
            team=team,
            author_id__in=member_ids,
            state="merged",
            merged_at__gte=start_datetime,
            merged_at__lte=end_datetime,
        )
        .values("author_id")
        .annotate(
            prs_merged=Count("id"),
            avg_cycle_time_hours=Avg("cycle_time_hours"),
            avg_review_time_hours=Avg("review_time_hours"),
            lines_added=Sum("additions"),
            lines_removed=Sum("deletions"),
            revert_count=Count("id", filter=Q(is_revert=True)),
            hotfix_count=Count("id", filter=Q(is_hotfix=True)),
        )
    )
    return {row["author_id"]: row for row in pr_aggregates}


def _batch_fetch_commit_counts(team, member_ids: list[int], start_datetime, end_datetime) -> dict:
    """Batch fetch commit counts for all members in a single query."""
    commit_counts = (
        Commit.objects.filter(
            team=team,
            author_id__in=member_ids,
            committed_at__gte=start_datetime,
            committed_at__lte=end_datetime,
        )
        .values("author_id")
        .annotate(count=Count("id"))
    )
    return {row["author_id"]: row["count"] for row in commit_counts}


def _batch_fetch_survey_metrics(team, member_ids: list[int], start_datetime, end_datetime) -> dict:
    """Batch fetch survey metrics (AI assisted, completed) for all members in a single query."""
    survey_aggregates = (
        PRSurvey.objects.filter(
            team=team,
            author_id__in=member_ids,
            pull_request__merged_at__gte=start_datetime,
            pull_request__merged_at__lte=end_datetime,
        )
        .values("author_id")
        .annotate(
            ai_assisted_prs=Count("id", filter=Q(author_ai_assisted=True)),
            surveys_completed=Count("id", filter=Q(author_responded_at__isnull=False)),
        )
    )
    return {row["author_id"]: row for row in survey_aggregates}


def _batch_fetch_review_metrics(team, member_ids: list[int], start_datetime, end_datetime) -> dict:
    """Batch fetch review metrics (quality rating, guess accuracy) for all members in a single query."""
    review_aggregates = (
        PRSurveyReview.objects.filter(
            team=team,
            survey__author_id__in=member_ids,
            survey__pull_request__merged_at__gte=start_datetime,
            survey__pull_request__merged_at__lte=end_datetime,
        )
        .values("survey__author_id")
        .annotate(
            avg_quality_rating=Avg("quality_rating"),
            total_guesses=Count("id", filter=Q(ai_guess__isnull=False)),
            correct_guesses=Count("id", filter=Q(guess_correct=True)),
        )
    )
    return {row["survey__author_id"]: row for row in review_aggregates}


def aggregate_team_weekly_metrics(team, week_start: date) -> list[WeeklyMetrics]:
    """
    Aggregate weekly metrics for all active team members.

    Creates or updates WeeklyMetrics records for each active member.
    Optimized to use batch queries instead of N+1 per-member queries.

    Args:
        team: The team to aggregate metrics for
        week_start: Start of the week (Monday)

    Returns:
        List of created/updated WeeklyMetrics records
    """
    week_start, week_end = get_week_boundaries(week_start)
    start_datetime, end_datetime = _get_week_datetime_range(week_start, week_end)

    # Get all active team members
    active_members = list(TeamMember.objects.filter(team=team, is_active=True))
    if not active_members:
        return []

    member_ids = [m.id for m in active_members]

    # Batch fetch all metrics in 4 queries (instead of 5 queries per member)
    pr_metrics = _batch_fetch_pr_metrics(team, member_ids, start_datetime, end_datetime)
    commit_counts = _batch_fetch_commit_counts(team, member_ids, start_datetime, end_datetime)
    survey_metrics = _batch_fetch_survey_metrics(team, member_ids, start_datetime, end_datetime)
    review_metrics = _batch_fetch_review_metrics(team, member_ids, start_datetime, end_datetime)

    results = []
    for member in active_members:
        # Get metrics from batch-fetched data (O(1) dict lookups)
        pr_data = pr_metrics.get(member.id, {})
        commit_count = commit_counts.get(member.id, 0)
        survey_data = survey_metrics.get(member.id, {})
        review_data = review_metrics.get(member.id, {})

        # Calculate guess accuracy percentage
        guess_accuracy = None
        total_guesses = review_data.get("total_guesses", 0)
        if total_guesses and total_guesses > 0:
            correct_guesses = review_data.get("correct_guesses", 0)
            guess_accuracy = Decimal((correct_guesses / total_guesses) * 100).quantize(Decimal("0.01"))

        # Build metrics dict
        metrics = {
            "prs_merged": pr_data.get("prs_merged", 0) or 0,
            "avg_cycle_time_hours": pr_data.get("avg_cycle_time_hours"),
            "avg_review_time_hours": pr_data.get("avg_review_time_hours"),
            "commits_count": commit_count,
            "lines_added": pr_data.get("lines_added", 0) or 0,
            "lines_removed": pr_data.get("lines_removed", 0) or 0,
            "revert_count": pr_data.get("revert_count", 0) or 0,
            "hotfix_count": pr_data.get("hotfix_count", 0) or 0,
            "ai_assisted_prs": survey_data.get("ai_assisted_prs", 0) or 0,
            "avg_quality_rating": review_data.get("avg_quality_rating"),
            "surveys_completed": survey_data.get("surveys_completed", 0) or 0,
            "guess_accuracy": guess_accuracy,
        }

        # Create or update WeeklyMetrics record
        weekly_metric, created = WeeklyMetrics.objects.update_or_create(
            team=team,
            member=member,
            week_start=week_start,
            defaults=metrics,
        )
        results.append(weekly_metric)

    return results
