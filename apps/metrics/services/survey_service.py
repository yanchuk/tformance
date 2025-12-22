"""Survey Service - Business logic for managing PR surveys.

Handles creating surveys, recording responses, and triggering reveals.
"""

from typing import TypedDict

from django.db.models import Count, Q
from django.utils import timezone

from apps.integrations.models import SlackIntegration
from apps.integrations.services.ai_detection import detect_ai_coauthor
from apps.metrics.models import PRSurvey, PRSurveyReview, PullRequest, TeamMember
from apps.metrics.services import survey_tokens


class AccuracyStats(TypedDict):
    """Type definition for reviewer accuracy statistics."""

    correct: int
    total: int
    percentage: float


def create_pr_survey(pull_request: PullRequest) -> PRSurvey:
    """Create survey for a merged PR. Sets author from PR.

    Automatically detects AI co-authors from PR commits and pre-fills
    author_ai_assisted if AI signatures are found.
    """
    # Check for AI assistance in commits
    ai_detected = _detect_ai_in_pr_commits(pull_request)

    # Create survey with auto-detection fields if AI found
    survey = PRSurvey.objects.create(
        team=pull_request.team,
        pull_request=pull_request,
        author=pull_request.author,
        author_ai_assisted=True if ai_detected else None,
        author_response_source="auto" if ai_detected else None,
        author_responded_at=timezone.now() if ai_detected else None,
    )
    survey_tokens.set_survey_token(survey)
    return survey


def _detect_ai_in_pr_commits(pull_request: PullRequest) -> bool:
    """Detect AI co-authors in PR commits.

    Checks two sources:
    1. Commit.is_ai_assisted flag (set during GitHub sync)
    2. Commit messages for AI co-author signatures (fallback detection)
    """
    # Get commits for this PR
    commits = pull_request.commits.all()  # noqa: TEAM001 - PR is team-scoped

    if not commits.exists():
        return False

    # Check if any commit already has is_ai_assisted=True
    if commits.filter(is_ai_assisted=True).exists():
        return True

    # Fallback: scan commit messages with our detection patterns
    commit_messages = [{"message": c.message} for c in commits if c.message]
    return detect_ai_coauthor(commit_messages)


def record_author_response(
    survey: PRSurvey,
    ai_assisted: bool,
    response_source: str = "web",
) -> None:
    """Record author's AI-assisted response.

    Args:
        survey: The PRSurvey to record the response for
        ai_assisted: Whether the author used AI tools
        response_source: Channel the response came from (github, slack, web)
    """
    survey.author_ai_assisted = ai_assisted
    survey.author_responded_at = timezone.now()
    survey.author_response_source = response_source
    survey.save()


def create_reviewer_survey(survey: PRSurvey, reviewer: TeamMember) -> PRSurveyReview:
    """Create reviewer survey entry for a reviewer."""
    return PRSurveyReview.objects.create(
        team=survey.team,
        survey=survey,
        reviewer=reviewer,
    )


def record_reviewer_response(
    survey_review: PRSurveyReview,
    quality: int,
    ai_guess: bool,
    response_source: str = "web",
) -> None:
    """Record reviewer's full response (quality + AI guess).

    Args:
        survey_review: The PRSurveyReview to record the response for
        quality: Quality rating (1-3)
        ai_guess: Reviewer's guess whether AI was used
        response_source: Channel the response came from (github, slack, web)
    """
    survey_review.quality_rating = quality
    survey_review.ai_guess = ai_guess
    survey_review.responded_at = timezone.now()
    survey_review.response_source = response_source

    # Calculate guess_correct if author has responded
    if survey_review.survey.author_ai_assisted is not None:
        survey_review.guess_correct = ai_guess == survey_review.survey.author_ai_assisted

    survey_review.save()


def record_reviewer_quality_vote(
    survey_review: PRSurveyReview,
    quality: int,
    response_source: str = "github",
) -> None:
    """Record reviewer's quality-only vote (one-click voting from PR description).

    This function is used for one-click voting where only quality rating
    is captured, not the AI guess. The AI guess can be provided later
    on the thank you page.

    Args:
        survey_review: The PRSurveyReview to record the vote for
        quality: Quality rating (1=Could be better, 2=OK, 3=Super)
        response_source: Channel the vote came from (typically 'github')
    """
    survey_review.quality_rating = quality
    survey_review.responded_at = timezone.now()
    survey_review.response_source = response_source
    # ai_guess is NOT set - reviewer can optionally provide on thank you page
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


def get_reviewer_accuracy_stats(reviewer: TeamMember) -> AccuracyStats:
    """Get reviewer's guess accuracy stats.

    Returns: {correct: int, total: int, percentage: float}
    """
    # Use aggregation for better performance
    stats = PRSurveyReview.objects.filter(  # noqa: TEAM001 - reviewer is team-scoped
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
