"""Survey Service - Business logic for managing PR surveys.

Handles creating surveys, recording responses, and triggering reveals.
"""

from django.db.models import Count, Q
from django.utils import timezone

from apps.integrations.models import SlackIntegration
from apps.metrics.models import PRSurvey, PRSurveyReview, PullRequest, TeamMember


def create_pr_survey(pull_request: PullRequest) -> PRSurvey:
    """Create survey for a merged PR. Sets author from PR."""
    return PRSurvey.objects.create(
        team=pull_request.team,
        pull_request=pull_request,
        author=pull_request.author,
    )


def record_author_response(survey: PRSurvey, ai_assisted: bool) -> None:
    """Record author's AI-assisted response. Sets responded_at."""
    survey.author_ai_assisted = ai_assisted
    survey.author_responded_at = timezone.now()
    survey.save()


def create_reviewer_survey(survey: PRSurvey, reviewer: TeamMember) -> PRSurveyReview:
    """Create reviewer survey entry for a reviewer."""
    return PRSurveyReview.objects.create(
        team=survey.team,
        survey=survey,
        reviewer=reviewer,
    )


def record_reviewer_response(survey_review: PRSurveyReview, quality: int, ai_guess: bool) -> None:
    """Record reviewer's response. Calculates guess_correct if author already responded."""
    survey_review.quality_rating = quality
    survey_review.ai_guess = ai_guess
    survey_review.responded_at = timezone.now()

    # Calculate guess_correct if author has responded
    if survey_review.survey.author_ai_assisted is not None:
        survey_review.guess_correct = ai_guess == survey_review.survey.author_ai_assisted

    survey_review.save()


def check_and_send_reveal(survey: PRSurvey, survey_review: PRSurveyReview) -> bool:
    """Check if reveal should be sent, send if appropriate.

    Returns True if reveal was sent. Requires:
    - Author has responded
    - Reviewer has responded
    - Team's SlackIntegration has reveals_enabled=True
    """
    if not _can_send_reveal(survey):
        return False

    # TODO: Actually send the reveal message via Slack
    # For now, just return False since we don't implement Slack sending
    return False


def _can_send_reveal(survey: PRSurvey) -> bool:
    """Check if reveal can be sent for this survey."""
    # Check if author has responded
    if survey.author_ai_assisted is None:
        return False

    # Check if team has SlackIntegration with reveals_enabled
    try:
        slack_integration = SlackIntegration.objects.get(team=survey.team)
        return slack_integration.reveals_enabled
    except SlackIntegration.DoesNotExist:
        return False


def get_reviewer_accuracy_stats(reviewer: TeamMember) -> dict:
    """Get reviewer's guess accuracy stats.

    Returns: {correct: int, total: int, percentage: float}
    """
    # Use aggregation for better performance
    stats = PRSurveyReview.objects.filter(
        reviewer=reviewer,
        guess_correct__isnull=False,
    ).aggregate(
        total=Count("id"),
        correct=Count("id", filter=Q(guess_correct=True)),
    )

    total = stats["total"]
    correct = stats["correct"]
    percentage = (correct / total * 100) if total > 0 else 0.0

    return {
        "correct": correct,
        "total": total,
        "percentage": percentage,
    }
