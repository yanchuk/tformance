"""Slack leaderboard service for weekly AI Detective leaderboard posts."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.integrations.models import SlackIntegration
from apps.metrics.models import PRSurvey, PRSurveyReview, PullRequest
from apps.teams.models import Team


def _calculate_percentage(numerator: int, denominator: int) -> int:
    """Calculate percentage, returning 0 if denominator is 0."""
    return int(numerator / denominator * 100) if denominator > 0 else 0


def _get_week_date_range(week_start: date) -> tuple[datetime, datetime]:
    """Get datetime range for a week (Monday to Sunday)."""
    week_end = week_start + timedelta(days=7)
    start_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=UTC)
    end_dt = datetime.combine(week_end, datetime.min.time(), tzinfo=UTC)
    return start_dt, end_dt


def _compute_team_stats(merged_prs, surveys, survey_reviews) -> dict:
    """Compute team statistics for the week."""
    prs_merged = merged_prs.count()

    # Calculate AI percentage (author responded)
    surveys_with_response = surveys.filter(author_ai_assisted__isnull=False)
    ai_assisted_count = surveys_with_response.filter(author_ai_assisted=True).count()
    total_responses = surveys_with_response.count()
    ai_percentage = _calculate_percentage(ai_assisted_count, total_responses)

    # Calculate detection rate (guess correct)
    reviews_with_guess = survey_reviews.filter(guess_correct__isnull=False)
    correct_guesses = reviews_with_guess.filter(guess_correct=True).count()
    total_guesses = reviews_with_guess.count()
    detection_rate = _calculate_percentage(correct_guesses, total_guesses)

    # Calculate average quality rating
    avg_rating_raw = survey_reviews.filter(quality_rating__isnull=False).aggregate(Avg("quality_rating"))[
        "quality_rating__avg"
    ]
    avg_rating = Decimal(str(round(avg_rating_raw, 2))) if avg_rating_raw else None

    return {
        "prs_merged": prs_merged,
        "ai_percentage": ai_percentage,
        "detection_rate": detection_rate,
        "avg_rating": avg_rating,
    }


def _compute_top_guessers(survey_reviews) -> list[dict]:
    """Compute top 3 guessers by accuracy."""
    guesser_stats = (
        survey_reviews.filter(guess_correct__isnull=False)
        .values("reviewer__display_name")
        .annotate(
            correct=Count("id", filter=Q(guess_correct=True)),
            total=Count("id"),
        )
        .order_by("-correct", "reviewer__display_name")[:3]  # Top 3 only
    )

    top_guessers = []
    for stats in guesser_stats:
        percentage = _calculate_percentage(stats["correct"], stats["total"])
        top_guessers.append(
            {
                "name": stats["reviewer__display_name"],
                "correct": stats["correct"],
                "total": stats["total"],
                "percentage": percentage,
            }
        )
    return top_guessers


def _compute_quality_champions(merged_prs, survey_reviews) -> dict:
    """Compute quality champions (super reviewer and fastest review)."""
    quality_champions = {}

    # Super champion (most quality_rating=3)
    super_stats = (
        survey_reviews.filter(quality_rating=3)
        .values("reviewer__display_name")
        .annotate(super_count=Count("id"))
        .order_by("-super_count")
        .first()
    )
    if super_stats:
        quality_champions["super_champion"] = {
            "name": super_stats["reviewer__display_name"],
            "super_count": super_stats["super_count"],
        }

    # Fast reviewer (fastest review_time_hours)
    fastest_pr = (
        merged_prs.filter(review_time_hours__isnull=False)
        .select_related("author")
        .order_by("review_time_hours")
        .first()
    )
    if fastest_pr and fastest_pr.author:
        quality_champions["fast_reviewer"] = {
            "name": fastest_pr.author.display_name,
            "fastest_review_hours": fastest_pr.review_time_hours,
        }

    return quality_champions


def compute_weekly_leaderboard(team: Team, week_start: date) -> dict:
    """Compute leaderboard data for a week.

    Returns: {
        top_guessers: [{name, correct, total, percentage}],  # Top 3
        team_stats: {prs_merged, ai_percentage, detection_rate, avg_rating},
        quality_champions: {super_champion, fast_reviewer}
    }
    """
    start_dt, end_dt = _get_week_date_range(week_start)

    # Get PRs merged in the week
    merged_prs = PullRequest.objects.filter(
        team=team,
        state="merged",
        merged_at__gte=start_dt,
        merged_at__lt=end_dt,
    )

    # Get surveys and reviews for these PRs
    surveys = PRSurvey.objects.filter(pull_request__in=merged_prs)
    survey_reviews = PRSurveyReview.objects.filter(survey__in=surveys)

    return {
        "top_guessers": _compute_top_guessers(survey_reviews),
        "team_stats": _compute_team_stats(merged_prs, surveys, survey_reviews),
        "quality_champions": _compute_quality_champions(merged_prs, survey_reviews),
    }


def build_leaderboard_blocks(leaderboard_data: dict, date_range: str) -> list:
    """Build Block Kit blocks for leaderboard message.

    Format from SLACK-BOT.md:
    🏆 *AI Detective Leaderboard* (Week of {date_range})

    *Top Guessers:*
    1. {name} - {correct}/{total} ({percentage}%)
    ...

    📊 *Team Stats This Week:*
    • {prs_merged} PRs merged
    • {ai_percentage}% were AI-assisted
    ...
    """
    blocks = []

    # Header
    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🏆 AI Detective Leaderboard (Week of {date_range})",
            },
        }
    )

    # Top Guessers
    top_guessers = leaderboard_data.get("top_guessers", [])
    if top_guessers:
        guesser_lines = ["*Top Guessers:*"]
        for i, guesser in enumerate(top_guessers, 1):
            guesser_lines.append(
                f"{i}. {guesser['name']} - {guesser['correct']}/{guesser['total']} ({guesser['percentage']}%)"
            )
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(guesser_lines)}})

    # Team Stats
    stats = leaderboard_data.get("team_stats", {})
    stats_lines = [
        "*📊 Team Stats This Week:*",
        f"• {stats['prs_merged']} PRs merged",
        f"• {stats['ai_percentage']}% were AI-assisted",
        f"• {stats['detection_rate']}% detection rate",
    ]
    if stats.get("avg_rating"):
        stats_lines.append(f"• {stats['avg_rating']} avg quality rating")

    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(stats_lines)}})

    # Quality Champions
    champions = leaderboard_data.get("quality_champions", {})
    if champions:
        champion_lines = ["*🌟 Quality Champions:*"]
        if "super_champion" in champions:
            champion_lines.append(
                f"• {champions['super_champion']['name']} - {champions['super_champion']['super_count']} Super ratings"
            )
        if "fast_reviewer" in champions:
            fast_reviewer = champions["fast_reviewer"]
            champion_lines.append(
                f"• {fast_reviewer['name']} - Fastest review ({fast_reviewer['fastest_review_hours']}h)"
            )
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(champion_lines)}})

    return blocks


def should_post_leaderboard(integration: SlackIntegration) -> bool:
    """Check if leaderboard should be posted now.

    Returns True if:
    - leaderboard_enabled is True
    - Current day matches leaderboard_day
    - Current hour matches leaderboard_time.hour
    """
    if not integration.leaderboard_enabled:
        return False

    now = timezone.now()
    return now.weekday() == integration.leaderboard_day and now.hour == integration.leaderboard_time.hour
