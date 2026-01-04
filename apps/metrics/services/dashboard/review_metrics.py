"""Review-related metrics for dashboard.

Functions for review distribution, workload, correlations, and response times.
"""

import statistics
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Count, Q

from apps.metrics.models import PRReview, PRSurvey, PRSurveyReview
from apps.metrics.services.dashboard._helpers import (
    _avatar_url_from_github_id,
    _calculate_average_response_times,
    _calculate_channel_percentages,
    _compute_initials,
    _filter_by_date_range,
)
from apps.teams.models import Team
from apps.utils.date_utils import end_of_day, start_of_day


def get_review_distribution(
    team: Team, start_date: date, end_date: date, repo: str | None = None, limit: int | None = None
) -> list[dict]:
    """Get review distribution by reviewer (for bar chart).

    Uses actual GitHub PR reviews (not survey responses) filtered by review submission date.
    Counts unique PRs reviewed (not total review submissions) to match PR list semantics.
    Only counts PRs that were merged within the date range.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)
        limit: Optional maximum number of reviewers to return (default: all)

    Returns:
        list of dicts with keys:
            - reviewer_name (str): Reviewer display name
            - avatar_url (str): GitHub avatar URL
            - initials (str): Initials for fallback display
            - count (int): Number of unique PRs reviewed
    """
    filters = {
        "team": team,
        "submitted_at__gte": start_of_day(start_date),
        "submitted_at__lte": end_of_day(end_date),
        # Also filter by PR merged_at to match PR list semantics
        "pull_request__merged_at__date__gte": start_date,
        "pull_request__merged_at__date__lte": end_date,
    }
    if repo:
        filters["pull_request__github_repo"] = repo

    reviews = (
        PRReview.objects.filter(**filters)  # noqa: TEAM001 - team in filters
        .exclude(reviewer__isnull=True)  # Filter out reviews without matched reviewer
        .values("reviewer__id", "reviewer__display_name", "reviewer__github_id")
        .annotate(count=Count("pull_request", distinct=True))  # Count unique PRs, not review submissions
        .order_by("-count")
    )

    # Apply limit if specified
    if limit is not None:
        reviews = reviews[:limit]

    return [
        {
            "reviewer_id": r["reviewer__id"],
            "reviewer_name": r["reviewer__display_name"],
            "avatar_url": _avatar_url_from_github_id(r["reviewer__github_id"]),
            "initials": _compute_initials(r["reviewer__display_name"]),
            "count": r["count"],
        }
        for r in reviews
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
    ).exclude(reviewer__isnull=True)  # Filter out reviews without matched reviewer
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


def detect_review_bottleneck(
    team: Team,
    start_date: date,  # noqa: ARG001
    end_date: date,  # noqa: ARG001
    repo: str | None = None,
) -> dict | None:
    """Detect if any reviewer has > 3x average PRs awaiting their approval.

    "PRs awaiting approval" are open, non-draft PRs where the reviewer's
    LATEST review is NOT "approved". These are PRs the reviewer has reviewed
    (changes_requested, commented, dismissed) but not yet approved.

    This is NOT about PRs they haven't reviewed yet - it's about PRs stuck
    in their review queue awaiting final approval.

    Note: Date parameters are accepted for API consistency but not used.
    We look at ALL currently open PRs since pending work is independent of
    when the PR was created.

    Args:
        team: Team instance
        start_date: Unused (kept for API consistency)
        end_date: Unused (kept for API consistency)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with bottleneck info if detected:
            - reviewer_name: str display name of bottleneck reviewer
            - pending_count: int number of PRs awaiting their approval
            - team_avg: float average PRs awaiting approval across all reviewers
        None if no bottleneck detected (no one exceeds 3x threshold)
    """
    # Get all reviews on open, non-draft PRs
    # Exclude reviews with NULL reviewer (external collaborators/bots not synced)
    filters = {
        "team": team,
        "pull_request__state": "open",
        "pull_request__is_draft": False,
        "reviewer__isnull": False,  # Exclude reviews without linked reviewer
    }
    if repo:
        filters["pull_request__github_repo"] = repo

    reviews = list(
        PRReview.objects.filter(**filters)  # noqa: TEAM001 - team in filters
        .select_related("reviewer")
        .order_by("submitted_at")  # Oldest first, we'll take the last one per (reviewer, PR)
        .values(
            "reviewer_id",
            "reviewer__display_name",
            "reviewer__github_username",
            "pull_request_id",
            "state",
            "submitted_at",
        )
    )

    if not reviews:
        return None

    # Group reviews by (reviewer_id, pull_request_id) and find the latest review state
    # A PR is "pending" for a reviewer only if their latest review is NOT "approved"
    latest_reviews: dict[tuple[int, int], dict] = {}
    for review in reviews:
        key = (review["reviewer_id"], review["pull_request_id"])
        # Keep updating - last one wins (since ordered by submitted_at asc)
        latest_reviews[key] = review

    # Count pending PRs per reviewer (where latest review state != "approved")
    pending_counts: dict[int, dict] = defaultdict(
        lambda: {"reviewer_name": "", "github_username": "", "pending_count": 0}
    )

    for (reviewer_id, _pr_id), review in latest_reviews.items():
        # Only count if latest review is NOT "approved"
        if review["state"] != "approved":
            pending_counts[reviewer_id]["reviewer_name"] = review["reviewer__display_name"] or "Unknown"
            pending_counts[reviewer_id]["github_username"] = review["reviewer__github_username"] or "unknown"
            pending_counts[reviewer_id]["pending_count"] += 1

    # Filter out reviewers with 0 pending (all their reviews were approved)
    reviewer_counts = [r for r in pending_counts.values() if r["pending_count"] > 0]

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
        "github_username": worst["github_username"],
        "pending_count": worst["pending_count"],
        "team_avg": round(team_avg, 1),
    }
