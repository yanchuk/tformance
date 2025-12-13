"""Celery tasks for integrations."""

import logging

from celery import shared_task
from celery.exceptions import Retry
from github import GithubException

from apps.integrations.models import (
    GitHubIntegration,
    JiraIntegration,
    SlackIntegration,
    TrackedJiraProject,
    TrackedRepository,
)
from apps.integrations.services import github_comments
from apps.integrations.services.github_sync import sync_repository_incremental
from apps.integrations.services.jira_sync import sync_project_issues
from apps.integrations.services.jira_user_matching import sync_jira_users
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

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_repository_task(self, repo_id: int) -> dict:
    """Sync a single tracked repository.

    Args:
        self: Celery task instance (bound task)
        repo_id: ID of the TrackedRepository to sync

    Returns:
        Dict with sync results (prs_synced, reviews_synced, errors) or error/skip status
    """
    # Get TrackedRepository by id
    try:
        tracked_repo = TrackedRepository.objects.get(id=repo_id)
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository with id {repo_id} not found")
        return {"error": f"TrackedRepository with id {repo_id} not found"}

    # Check if repo is active
    if not tracked_repo.is_active:
        logger.info(f"Skipping inactive repository: {tracked_repo.full_name}")
        return {"skipped": True, "reason": "Repository is not active"}

    # Set status to syncing
    tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_SYNCING
    tracked_repo.save(update_fields=["sync_status"])

    # Sync the repository
    logger.info(f"Starting sync for repository: {tracked_repo.full_name}")
    try:
        result = sync_repository_incremental(tracked_repo)
        logger.info(f"Successfully synced repository: {tracked_repo.full_name}")

        # Set status to complete and clear error
        tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_COMPLETE
        tracked_repo.last_sync_error = None
        tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

        return result
    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff
            logger.warning(f"Sync failed for {tracked_repo.full_name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted or retry failed - log to Sentry and return error
            from sentry_sdk import capture_exception

            logger.error(f"Sync failed permanently for {tracked_repo.full_name}: {exc}")
            capture_exception(exc)

            # Set status to error and save error message
            tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_ERROR
            tracked_repo.last_sync_error = str(exc)
            tracked_repo.save(update_fields=["sync_status", "last_sync_error"])

            return {"error": str(exc)}


@shared_task
def sync_all_repositories_task() -> dict:
    """Dispatch sync tasks for all active tracked repositories.

    Returns:
        Dict with counts: repos_dispatched, repos_skipped
    """
    logger.info("Starting sync for all repositories")

    # Query all tracked repositories with optimized counts
    active_repos = TrackedRepository.objects.filter(is_active=True)
    repos_skipped = TrackedRepository.objects.filter(is_active=False).count()

    repos_dispatched = 0

    # Dispatch sync task for each active repo
    for repo in active_repos:
        try:
            sync_repository_task.delay(repo.id)
            repos_dispatched += 1
        except Exception as e:
            # Log dispatch errors and continue with remaining repos
            logger.error(f"Failed to dispatch sync task for repository {repo.full_name}: {e}")
            continue

    logger.info(f"Finished dispatching sync tasks. Dispatched: {repos_dispatched}, Skipped: {repos_skipped}")

    return {
        "repos_dispatched": repos_dispatched,
        "repos_skipped": repos_skipped,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_jira_project_task(self, project_id: int) -> dict:
    """Sync a single tracked Jira project.

    Args:
        self: Celery task instance (bound task)
        project_id: ID of the TrackedJiraProject to sync

    Returns:
        Dict with sync results (issues_created, issues_updated, errors) or error/skip status
    """
    # Get TrackedJiraProject by id
    try:
        tracked_project = TrackedJiraProject.objects.get(id=project_id)
    except TrackedJiraProject.DoesNotExist:
        logger.warning(f"TrackedJiraProject with id {project_id} not found")
        return {"error": f"TrackedJiraProject with id {project_id} not found"}

    # Check if project is active
    if not tracked_project.is_active:
        logger.info(f"Skipping inactive Jira project: {tracked_project.jira_project_key}")
        return {"skipped": True, "reason": "Project is not active"}

    # Set status to syncing
    tracked_project.sync_status = TrackedJiraProject.SYNC_STATUS_SYNCING
    tracked_project.save(update_fields=["sync_status"])

    # Sync the project
    logger.info(f"Starting sync for Jira project: {tracked_project.jira_project_key}")
    try:
        result = sync_project_issues(tracked_project)
        logger.info(f"Successfully synced Jira project: {tracked_project.jira_project_key}")

        # Set status to complete and clear error
        tracked_project.sync_status = TrackedJiraProject.SYNC_STATUS_COMPLETE
        tracked_project.last_sync_error = None
        tracked_project.save(update_fields=["sync_status", "last_sync_error"])

        return result
    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff
            logger.warning(f"Sync failed for {tracked_project.jira_project_key}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted - log to Sentry and return error
            from sentry_sdk import capture_exception

            logger.error(f"Sync failed permanently for {tracked_project.jira_project_key}: {exc}")
            capture_exception(exc)

            # Set status to error and save error message
            tracked_project.sync_status = TrackedJiraProject.SYNC_STATUS_ERROR
            tracked_project.last_sync_error = str(exc)
            tracked_project.save(update_fields=["sync_status", "last_sync_error"])

            return {"error": str(exc)}


@shared_task
def sync_all_jira_projects_task() -> dict:
    """Dispatch sync tasks for all active tracked Jira projects.

    Returns:
        Dict with counts: projects_dispatched, projects_skipped
    """
    logger.info("Starting sync for all Jira projects")

    # Query all tracked Jira projects
    active_projects = TrackedJiraProject.objects.filter(is_active=True)
    projects_skipped = TrackedJiraProject.objects.filter(is_active=False).count()

    projects_dispatched = 0

    # Dispatch sync task for each active project
    for project in active_projects:
        try:
            sync_jira_project_task.delay(project.id)
            projects_dispatched += 1
        except Exception as e:
            # Log dispatch errors and continue with remaining projects
            logger.error(f"Failed to dispatch sync task for Jira project {project.jira_project_key}: {e}")
            continue

    logger.info(f"Finished dispatching Jira sync tasks. Dispatched: {projects_dispatched}, Skipped: {projects_skipped}")

    return {
        "projects_dispatched": projects_dispatched,
        "projects_skipped": projects_skipped,
    }


@shared_task
def sync_jira_users_task(team_id: int) -> dict:
    """Sync Jira users to TeamMembers for a team.

    Args:
        team_id: ID of the Team to sync users for

    Returns:
        Dict with sync results or error status
    """
    # Get Team by id
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": f"Team with id {team_id} not found"}

    # Get Jira integration for team
    try:
        jira_integration = JiraIntegration.objects.get(team=team)
        credential = jira_integration.credential
    except JiraIntegration.DoesNotExist:
        logger.warning(f"No Jira integration found for team {team.name}")
        return {"error": f"No Jira integration found for team {team.name}"}

    # Sync users
    logger.info(f"Starting Jira user sync for team: {team.name}")
    try:
        result = sync_jira_users(team, credential)
        logger.info(f"Successfully synced Jira users for team: {team.name}")
        return result
    except Exception as exc:
        logger.error(f"Failed to sync Jira users for team {team.name}: {exc}")
        return {"error": str(exc)}


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
        pr = PullRequest.objects.select_related("author", "team").get(id=pull_request_id)
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

    # Create PRSurvey
    survey = create_pr_survey(pr)
    logger.info(f"Created survey {survey.id} for PR {pr.github_pr_id}")

    # Get Slack client
    client = get_slack_client(slack_integration.credential)

    # Track results
    author_sent = False
    reviewers_sent = 0
    errors = []

    # Send author DM if author has slack_user_id
    if pr.author and pr.author.slack_user_id:
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
        PRReview.objects.filter(pull_request=pr)
        .select_related("reviewer")
        .exclude(reviewer__isnull=True)
        .values_list("reviewer", flat=True)
        .distinct()
    )
    # Convert IDs back to TeamMember objects
    from apps.metrics.models import TeamMember

    reviewers = TeamMember.objects.filter(id__in=reviewers)

    # Send reviewer DMs
    for reviewer in reviewers:
        if not reviewer.slack_user_id:
            logger.info(f"Skipping reviewer {reviewer.display_name} - no slack_user_id")
            continue

        try:
            # Create reviewer survey entry (side effect - record in DB)
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
        "reviewers_sent": reviewers_sent,
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
        survey_review = PRSurveyReview.objects.select_related("survey", "reviewer", "survey__team").get(
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
        return {"error": str(exc)}


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
    integrations = SlackIntegration.objects.select_related("team", "credential").all()

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def post_survey_comment_task(self, pull_request_id: int) -> dict:
    """Post survey comment to merged PR.

    Creates a PRSurvey and posts survey invitation comment to GitHub.
    Retries up to 3 times with exponential backoff on transient errors.

    Args:
        self: Celery task instance (bound task)
        pull_request_id: ID of the PullRequest to create survey for

    Returns:
        dict with survey_id and comment_id on success
        or dict with skipped/error status and reason
    """
    # Get PR by ID
    try:
        pr = PullRequest.objects.get(id=pull_request_id)
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pull_request_id} not found")
        return {"error": "PR not found"}

    # Skip non-merged PRs
    if pr.state != "merged":
        logger.info(f"Skipping survey comment for non-merged PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "PR not merged"}

    # Skip if survey already exists (idempotent)
    from apps.metrics.models import PRSurvey

    if PRSurvey.objects.filter(pull_request=pr).exists():
        logger.info(f"Skipping survey comment - survey already exists for PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "Survey already exists"}

    # Check for GitHub integration
    try:
        github_integration = GitHubIntegration.objects.get(team=pr.team)
    except GitHubIntegration.DoesNotExist:
        logger.info(f"Skipping survey comment - no GitHub integration for team {pr.team.name}")
        return {"skipped": True, "reason": "No GitHub integration"}

    # Create survey (this sets token and expiry)
    survey = create_pr_survey(pr)
    logger.info(f"Starting to post survey comment for PR {pr.github_pr_id} (survey {survey.id})")

    # Post comment to GitHub with retry logic
    try:
        comment_id = github_comments.post_survey_comment(pr, survey, github_integration.credential.access_token)

        # Store comment ID on survey (in case post_survey_comment didn't persist it)
        survey.github_comment_id = comment_id
        survey.save(update_fields=["github_comment_id"])

        logger.info(f"Successfully posted survey comment {comment_id} for PR {pr.github_pr_id}")
        return {"survey_id": survey.id, "comment_id": comment_id}
    except GithubException as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff for transient errors
            logger.warning(f"Failed to post survey comment for PR {pr.github_pr_id}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted - log to Sentry and return error
            from sentry_sdk import capture_exception

            error_msg = f"GitHub API error: {exc}"
            logger.error(f"Failed permanently to post survey comment for PR {pr.github_pr_id}: {error_msg}")
            capture_exception(exc)

            return {"error": error_msg, "survey_id": survey.id}
