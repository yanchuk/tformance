"""Slack Celery tasks.

This module contains tasks for Slack surveys, reveals, user sync, and leaderboards.
"""

import logging

from celery import shared_task

from apps.integrations.models import SlackIntegration
from apps.integrations.services.slack_client import get_slack_client, send_channel_message, send_dm
from apps.integrations.services.slack_leaderboard import (
    build_leaderboard_blocks,
    compute_weekly_leaderboard,
    should_post_leaderboard,
)
from apps.integrations.services.slack_surveys import (
    build_author_survey_blocks,
    build_reveal_correct_blocks,
    build_reveal_wrong_blocks,
    build_reviewer_survey_blocks,
)
from apps.integrations.services.slack_user_matching import sync_slack_users
from apps.metrics.models import PRReview, PRSurveyReview, PullRequest
from apps.metrics.services.survey_service import create_pr_survey, create_reviewer_survey, get_reviewer_accuracy_stats
from apps.teams.models import Team
from apps.utils.errors import sanitize_error

logger = logging.getLogger(__name__)


@shared_task
def send_pr_surveys_task(pull_request_id: int) -> dict:
    """Send surveys for a merged PR.

    1. Get PR and check if merged
    2. Get SlackIntegration for team (check surveys_enabled)
    3. Create PRSurvey using survey_service
    4. Send author DM (if author has slack_user_id)
    5. Send reviewer DMs (for each reviewer with slack_user_id)

    Args:
        pull_request_id: ID of the PullRequest to send surveys for

    Returns:
        Dict with keys: author_sent (bool), reviewers_sent (int), errors (list)
    """
    # Get PR by ID with related author for efficiency
    try:
        pr = PullRequest.objects.select_related("author", "team").get(id=pull_request_id)  # noqa: TEAM001 - ID from Celery task
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pull_request_id} not found")
        return {"error": f"PullRequest with id {pull_request_id} not found"}

    # Check if PR is merged
    if pr.state != "merged":
        logger.info(f"Skipping survey for non-merged PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "PR is not merged"}

    # Get SlackIntegration for team
    try:
        slack_integration = SlackIntegration.objects.get(team=pr.team)
    except SlackIntegration.DoesNotExist:
        logger.info(f"No Slack integration found for team {pr.team.name}")
        return {"skipped": True, "reason": "No Slack integration"}

    # Check if surveys are enabled
    if not slack_integration.surveys_enabled:
        logger.info(f"Surveys disabled for team {pr.team.name}")
        return {"skipped": True, "reason": "Surveys disabled"}

    # Get existing survey or create new one
    from apps.metrics.models import PRSurvey

    existing_survey = PRSurvey.objects.filter(pull_request=pr).first()  # noqa: TEAM001 - filtering by team-scoped PR
    if existing_survey:
        survey = existing_survey
        logger.info(f"Using existing survey {survey.id} for PR {pr.github_pr_id}")
    else:
        survey = create_pr_survey(pr)
        logger.info(f"Created survey {survey.id} for PR {pr.github_pr_id}")

    # Get Slack client
    client = get_slack_client(slack_integration.credential)

    # Track results
    author_sent = False
    author_skipped = False
    reviewers_sent = 0
    reviewers_skipped = 0
    errors = []

    # Send author DM if author has slack_user_id
    if pr.author and pr.author.slack_user_id:
        # Check if author already responded via GitHub (author_ai_assisted is set to a boolean value)
        if survey.has_author_responded():
            logger.info(f"Skipping author {pr.author.display_name} - already responded via GitHub")
            author_skipped = True
        else:
            try:
                blocks = build_author_survey_blocks(pr, survey)
                send_dm(client, pr.author.slack_user_id, blocks, text="PR Survey")
                author_sent = True
                logger.info(f"Sent author survey to {pr.author.display_name}")
            except Exception as e:
                error_msg = f"Failed to send author DM: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

    # Get unique reviewers from PR reviews
    reviewers = (
        PRReview.objects.filter(pull_request=pr)  # noqa: TEAM001 - filtering by team-scoped PR
        .select_related("reviewer")
        .exclude(reviewer__isnull=True)
        .values_list("reviewer", flat=True)
        .distinct()
    )
    # Convert IDs back to TeamMember objects
    from apps.metrics.models import TeamMember

    reviewers = TeamMember.objects.filter(id__in=reviewers)  # noqa: TEAM001 - IDs from team-scoped queryset

    # Optimize: Fetch all responded reviewer IDs in a single query to avoid N+1
    responded_reviewer_ids = set(
        PRSurveyReview.objects.filter(survey_id=survey.id, responded_at__isnull=False).values_list(  # noqa: TEAM001 - filtering by team-scoped survey
            "reviewer_id", flat=True
        )
    )

    # Send reviewer DMs
    for reviewer in reviewers:
        if not reviewer.slack_user_id:
            logger.info(f"Skipping reviewer {reviewer.display_name} - no slack_user_id")
            continue

        # Check if reviewer already responded via GitHub
        if reviewer.id in responded_reviewer_ids:
            logger.info(f"Skipping reviewer {reviewer.display_name} - already responded via GitHub")
            reviewers_skipped += 1
            continue

        try:
            # Create reviewer survey entry if it doesn't exist (idempotency check)
            if not PRSurveyReview.objects.filter(survey_id=survey.id, reviewer_id=reviewer.id).exists():  # noqa: TEAM001 - filtering by team-scoped survey
                create_reviewer_survey(survey, reviewer)

            # Build and send reviewer survey blocks
            blocks = build_reviewer_survey_blocks(pr, survey, reviewer)
            send_dm(client, reviewer.slack_user_id, blocks, text="PR Review Survey")
            reviewers_sent += 1
            logger.info(f"Sent reviewer survey to {reviewer.display_name}")
        except Exception as e:
            error_msg = f"Failed to send reviewer DM to {reviewer.display_name}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        "author_sent": author_sent,
        "author_skipped": author_skipped,
        "reviewers_sent": reviewers_sent,
        "reviewers_skipped": reviewers_skipped,
        "errors": errors,
    }


@shared_task
def send_reveal_task(survey_review_id: int) -> dict:
    """Send reveal message to a reviewer.

    1. Get PRSurveyReview
    2. Check if reveal should be sent (author responded, reveals_enabled)
    3. Calculate accuracy stats
    4. Send reveal message

    Args:
        survey_review_id: ID of the PRSurveyReview to send reveal for

    Returns:
        Dict with keys: sent (bool), error (str | None)
    """
    # Get PRSurveyReview
    try:
        survey_review = PRSurveyReview.objects.select_related("survey", "reviewer", "survey__team").get(  # noqa: TEAM001 - ID from Celery task
            id=survey_review_id
        )
    except PRSurveyReview.DoesNotExist:
        logger.warning(f"PRSurveyReview with id {survey_review_id} not found")
        return {"sent": False, "error": f"PRSurveyReview with id {survey_review_id} not found"}

    survey = survey_review.survey
    reviewer = survey_review.reviewer

    # Check if author has responded
    if survey.author_ai_assisted is None:
        logger.info(f"Skipping reveal for survey {survey.id} - author has not responded")
        return {"sent": False, "error": "Author has not responded yet"}

    # Check if reviewer is valid
    if not reviewer:
        logger.warning(f"Skipping reveal for survey_review {survey_review_id} - no reviewer")
        return {"sent": False, "error": "No reviewer found"}

    # Check if reviewer has slack_user_id
    if not reviewer.slack_user_id:
        logger.info(f"Skipping reveal for reviewer {reviewer.display_name} - no slack_user_id")
        return {"sent": False, "error": "Reviewer has no slack_user_id"}

    # Get SlackIntegration and check reveals_enabled
    try:
        slack_integration = SlackIntegration.objects.get(team=survey.team)
    except SlackIntegration.DoesNotExist:
        logger.info(f"No Slack integration found for team {survey.team.name}")
        return {"sent": False, "error": "No Slack integration"}

    if not slack_integration.reveals_enabled:
        logger.info(f"Reveals disabled for team {survey.team.name}")
        return {"sent": False, "error": "Reveals disabled"}

    # Calculate accuracy stats
    accuracy_stats = get_reviewer_accuracy_stats(reviewer)

    # Get Slack client
    client = get_slack_client(slack_integration.credential)

    # Build reveal blocks based on correctness
    was_ai_assisted = survey.author_ai_assisted
    guess_correct = survey_review.ai_guess == was_ai_assisted

    if guess_correct:
        blocks = build_reveal_correct_blocks(reviewer, was_ai_assisted, accuracy_stats)
    else:
        blocks = build_reveal_wrong_blocks(reviewer, was_ai_assisted, accuracy_stats)

    # Send reveal message
    try:
        send_dm(client, reviewer.slack_user_id, blocks, text="Survey Reveal")
        logger.info(f"Sent reveal to {reviewer.display_name} for survey {survey.id}")
        return {"sent": True, "error": None}
    except Exception as e:
        error_msg = f"Failed to send reveal DM: {e}"
        logger.error(error_msg)
        return {"sent": False, "error": error_msg}


@shared_task
def sync_slack_users_task(team_id: int) -> dict:
    """Sync Slack users to TeamMembers for a team.

    Args:
        team_id: ID of the Team to sync users for

    Returns:
        Dict with sync results: matched_count, unmatched_count, unmatched_users
    """
    # Get Team by id
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": f"Team with id {team_id} not found"}

    # Get Slack integration for team
    try:
        slack_integration = SlackIntegration.objects.get(team=team)
        credential = slack_integration.credential
    except SlackIntegration.DoesNotExist:
        logger.warning(f"No Slack integration found for team {team.name}")
        return {"error": f"No Slack integration found for team {team.name}"}

    # Sync users
    logger.info(f"Starting Slack user sync for team: {team.name}")
    try:
        result = sync_slack_users(team, credential)
        logger.info(f"Successfully synced Slack users for team: {team.name}")
        return result
    except Exception as exc:
        logger.error(f"Failed to sync Slack users for team {team.name}: {exc}")
        return {"error": sanitize_error(exc)}


@shared_task
def post_weekly_leaderboards_task() -> dict:
    """Check all teams and post leaderboards where appropriate.

    Returns: {teams_checked: int, leaderboards_posted: int, errors: list}
    """
    from datetime import date, timedelta

    logger.info("Starting weekly leaderboard check")

    teams_checked = 0
    leaderboards_posted = 0
    errors = []

    # Get all SlackIntegrations
    integrations = SlackIntegration.objects.select_related("team", "credential").all()  # noqa: TEAM001 - System job iterating all integrations

    for integration in integrations:
        teams_checked += 1

        # Check if we should post now
        if not should_post_leaderboard(integration):
            logger.debug(f"Skipping leaderboard for team {integration.team.name} - not scheduled for now")
            continue

        # Check if channel is configured
        if not integration.leaderboard_channel_id:
            logger.warning(f"Skipping leaderboard for team {integration.team.name} - no channel configured")
            errors.append(f"{integration.team.name}: No leaderboard channel configured")
            continue

        try:
            # Calculate week start (last Monday)
            today = date.today()
            week_start = today - timedelta(days=today.weekday() + 7)  # Previous Monday

            # Compute leaderboard data
            leaderboard_data = compute_weekly_leaderboard(integration.team, week_start)

            # Build date range string
            week_end = week_start + timedelta(days=6)
            date_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"

            # Build blocks
            blocks = build_leaderboard_blocks(leaderboard_data, date_range)

            # Get Slack client and send message
            client = get_slack_client(integration.credential)
            send_channel_message(
                client, integration.leaderboard_channel_id, blocks, text=f"Weekly Leaderboard - {date_range}"
            )

            leaderboards_posted += 1
            logger.info(f"Posted leaderboard for team {integration.team.name}")

        except Exception as e:
            error_msg = f"{integration.team.name}: {str(e)}"
            logger.error(f"Failed to post leaderboard for team {integration.team.name}: {e}")
            errors.append(error_msg)

    logger.info(
        f"Leaderboard check complete. Checked: {teams_checked}, Posted: {leaderboards_posted}, Errors: {len(errors)}"
    )

    return {
        "teams_checked": teams_checked,
        "leaderboards_posted": leaderboards_posted,
        "errors": errors,
    }


@shared_task
def schedule_slack_survey_fallback_task(pull_request_id: int) -> dict:
    """Schedule Slack surveys as fallback for users who haven't responded via GitHub.

    This task schedules send_pr_surveys_task with a 1-hour countdown, giving users
    time to respond via GitHub one-click voting before receiving Slack messages.

    Args:
        pull_request_id: ID of the PullRequest to send surveys for

    Returns:
        Dict with keys: scheduled (bool), task_id (str), countdown (int)
    """
    # Schedule send_pr_surveys_task with 1-hour countdown
    countdown = 3600  # 1 hour in seconds

    async_result = send_pr_surveys_task.apply_async(
        (pull_request_id,),
        countdown=countdown,
    )

    logger.info(f"Scheduled Slack survey fallback for PR {pull_request_id} in {countdown} seconds")

    return {
        "scheduled": True,
        "task_id": async_result.id,
        "countdown": countdown,
    }
