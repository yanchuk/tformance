"""PR data Celery tasks.

This module contains tasks for PR data operations:
- Fetching complete PR data (commits, files, check runs, comments)
- Posting survey comments to GitHub PRs
- Updating PR descriptions with survey links
- Refreshing repository language data
"""

import logging

from celery import shared_task
from celery.exceptions import Retry
from github import GithubException

from apps.integrations.models import GitHubIntegration, TrackedRepository
from apps.integrations.services import github_comments, github_pr_description, github_sync
from apps.metrics.models import PullRequest
from apps.metrics.services.survey_service import create_pr_survey

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


def _fetch_pr_core_data_with_graphql_or_rest(pr, tracked_repo, access_token, errors: list) -> dict:
    """Fetch PR commits, files, and reviews using GraphQL or REST.

    Uses GraphQL API if enabled for pr_complete_data operation, falling back to REST
    if GraphQL fails and fallback is enabled. Check runs and comments always use REST.

    Args:
        pr: PullRequest model instance
        tracked_repo: TrackedRepository model instance
        access_token: GitHub access token
        errors: List to append errors to

    Returns:
        dict with commits_synced, files_synced, reviews_synced counts
    """
    from asgiref.sync import async_to_sync
    from django.conf import settings

    github_config = getattr(settings, "GITHUB_API_CONFIG", {})
    use_graphql = github_config.get("USE_GRAPHQL", False)
    graphql_ops = github_config.get("GRAPHQL_OPERATIONS", {})
    pr_complete_enabled = graphql_ops.get("pr_complete_data", True)
    fallback_to_rest = github_config.get("FALLBACK_TO_REST", True)

    if use_graphql and pr_complete_enabled:
        logger.info(f"Using GraphQL API for PR complete data: {pr.github_repo}#{pr.github_pr_id}")
        try:
            from apps.integrations.services.github_graphql_sync import fetch_pr_complete_data_graphql

            # Run async function in sync context using async_to_sync (NOT asyncio.run!)
            # NOTE: asyncio.run() creates a new event loop which breaks @sync_to_async
            # decorators' thread handling, causing DB operations to silently fail
            # in Celery workers. async_to_sync properly manages the event loop.
            result = async_to_sync(fetch_pr_complete_data_graphql)(pr, tracked_repo)

            # Check if GraphQL sync had errors
            if result.get("errors") and fallback_to_rest:
                logger.warning(
                    f"GraphQL PR data fetch had errors for {pr.github_repo}#{pr.github_pr_id}: {result['errors']}, "
                    "falling back to REST"
                )
                raise Exception(f"GraphQL errors: {result['errors']}")

            return {
                "commits_synced": result.get("commits_synced", 0),
                "files_synced": result.get("files_synced", 0),
                "reviews_synced": result.get("reviews_synced", 0),
            }
        except Exception as e:
            if fallback_to_rest:
                logger.warning(
                    f"GraphQL PR data fetch failed for {pr.github_repo}#{pr.github_pr_id}: {e}, falling back to REST"
                )
            else:
                raise

    # Use REST API (default or fallback)
    logger.info(f"Using REST API for PR complete data: {pr.github_repo}#{pr.github_pr_id}")
    commits_synced = github_sync.sync_pr_commits(pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors)
    files_synced = github_sync.sync_pr_files(pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors)
    # Note: REST doesn't have a separate reviews sync here - reviews are typically synced during PR sync

    return {
        "commits_synced": commits_synced,
        "files_synced": files_synced,
        "reviews_synced": 0,  # REST path doesn't sync reviews in this task
    }


# =============================================================================
# PR Data Fetch Tasks
# =============================================================================


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=180, time_limit=240)
def fetch_pr_complete_data_task(self, pr_id: int) -> dict:
    """Fetch complete PR data (commits, files, check runs, comments) after merge.

    A-006: Added soft_time_limit=180s, time_limit=240s to prevent GitHub API hangs.

    Args:
        self: Celery task instance (bound task)
        pr_id: ID of the PullRequest to fetch data for

    Returns:
        Dict with sync counts and errors list
    """
    # Get PullRequest by id
    try:
        pr = PullRequest.objects.get(id=pr_id)  # noqa: TEAM001 - ID from Celery task queue
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pr_id} not found")
        return {"error": f"PullRequest with id {pr_id} not found"}

    # Find TrackedRepository matching team, repo, and is_active=True
    try:
        tracked_repo = TrackedRepository.objects.get(
            team=pr.team,
            full_name=pr.github_repo,
            is_active=True,
        )
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository not found for team={pr.team.id}, repo={pr.github_repo}, is_active=True")
        return {"error": f"TrackedRepository not found for team={pr.team.name}, repo={pr.github_repo}, is_active=True"}

    # Get access token from integration credential
    access_token = tracked_repo.integration.credential.access_token

    # Initialize errors list
    errors = []

    # Sync all PR data
    logger.info(f"Starting complete data fetch for PR {pr.github_pr_id}")

    # Fetch commits, files (and reviews if using GraphQL) - uses GraphQL or REST based on config
    core_data = _fetch_pr_core_data_with_graphql_or_rest(pr, tracked_repo, access_token, errors)
    commits_synced = core_data["commits_synced"]
    files_synced = core_data["files_synced"]

    # These always use REST (not supported by our GraphQL queries yet)
    check_runs_synced = github_sync.sync_pr_check_runs(
        pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors
    )

    issue_comments_synced = github_sync.sync_pr_issue_comments(
        pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors
    )

    review_comments_synced = github_sync.sync_pr_review_comments(
        pr, pr.github_pr_id, access_token, pr.github_repo, pr.team, errors
    )

    # Calculate iteration metrics after all data is synced
    github_sync.calculate_pr_iteration_metrics(pr)

    logger.info(f"Completed data fetch for PR {pr.github_pr_id}")

    return {
        "commits_synced": commits_synced,
        "files_synced": files_synced,
        "check_runs_synced": check_runs_synced,
        "issue_comments_synced": issue_comments_synced,
        "review_comments_synced": review_comments_synced,
        "errors": errors,
    }


# =============================================================================
# Survey Tasks (GitHub PR integration)
# =============================================================================


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=60, time_limit=90)
def post_survey_comment_task(self, pull_request_id: int) -> dict:
    """Post survey comment to merged PR.

    A-006: Added soft_time_limit=60s, time_limit=90s to prevent GitHub API hangs.

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
        pr = PullRequest.objects.get(id=pull_request_id)  # noqa: TEAM001 - ID from Celery task
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pull_request_id} not found")
        return {"error": "PR not found"}

    # Skip non-merged PRs
    if pr.state != "merged":
        logger.info(f"Skipping survey comment for non-merged PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "PR not merged"}

    # Skip if survey already exists (idempotent)
    from apps.metrics.models import PRSurvey

    if PRSurvey.objects.filter(pull_request=pr).exists():  # noqa: TEAM001 - filtering by team-scoped PR
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=60, time_limit=90)
def update_pr_description_survey_task(self, pull_request_id: int) -> dict:
    """Update PR description with survey voting links.

    A-006: Added soft_time_limit=60s, time_limit=90s to prevent GitHub API hangs.

    Creates a PRSurvey and updates the PR description with survey links.
    This is the preferred approach (vs comments) as it's more visible.
    Retries up to 3 times with exponential backoff on transient errors.

    Args:
        self: Celery task instance (bound task)
        pull_request_id: ID of the PullRequest to create survey for

    Returns:
        dict with survey_id on success
        or dict with skipped/error status and reason
    """
    from django.conf import settings

    # Import here to avoid circular imports - this is a Slack task
    from apps.integrations.tasks import schedule_slack_survey_fallback_task

    # Get PR by ID
    try:
        pr = PullRequest.objects.get(id=pull_request_id)  # noqa: TEAM001 - ID from Celery task
    except PullRequest.DoesNotExist:
        logger.warning(f"PullRequest with id {pull_request_id} not found")
        return {"error": "PR not found"}

    # Skip non-merged PRs
    if pr.state != "merged":
        logger.info(f"Skipping PR description update for non-merged PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "PR not merged"}

    # Skip if survey already exists (idempotent)
    from apps.metrics.models import PRSurvey

    if PRSurvey.objects.filter(pull_request=pr).exists():  # noqa: TEAM001 - filtering by team-scoped PR
        logger.info(f"Skipping PR description update - survey already exists for PR: {pr.github_pr_id}")
        return {"skipped": True, "reason": "Survey already exists"}

    # Check for GitHub integration
    try:
        github_integration = GitHubIntegration.objects.get(team=pr.team)
    except GitHubIntegration.DoesNotExist:
        logger.info(f"Skipping PR description update - no GitHub integration for team {pr.team.name}")
        return {"skipped": True, "reason": "No GitHub integration"}

    # Create survey (this includes AI auto-detection)
    survey = create_pr_survey(pr)
    logger.info(f"Created survey {survey.id} for PR {pr.github_pr_id}, AI detected: {survey.author_ai_assisted}")

    # Get base URL from settings
    base_url = getattr(settings, "SITE_URL", "https://app.tformance.com")

    # Update PR description with survey links
    try:
        github_pr_description.update_pr_description_with_survey(
            survey=survey,
            access_token=github_integration.credential.access_token,
            base_url=base_url,
        )

        logger.info(f"Successfully updated PR description with survey for PR {pr.github_pr_id}")

        # Schedule Slack fallback survey (runs after 1 hour delay)
        schedule_slack_survey_fallback_task.delay(pull_request_id)
        logger.info(f"Scheduled Slack fallback survey for PR {pr.github_pr_id}")

        return {"survey_id": survey.id, "success": True, "slack_fallback_scheduled": True}
    except GithubException as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff for transient errors
            logger.warning(f"Failed to update PR description for PR {pr.github_pr_id}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted - log to Sentry and return error
            from sentry_sdk import capture_exception

            error_msg = f"GitHub API error: {exc}"
            logger.error(f"Failed permanently to update PR description for PR {pr.github_pr_id}: {error_msg}")
            capture_exception(exc)

            return {"error": error_msg, "survey_id": survey.id}


# =============================================================================
# Repository Language Tasks
# =============================================================================


@shared_task
def refresh_repo_languages_task(repo_id: int) -> dict:
    """Refresh language breakdown for a single repository.

    Args:
        repo_id: ID of the TrackedRepository to refresh

    Returns:
        Dict with language count and primary language
    """
    from apps.integrations.services.github_repo_languages import update_repo_languages

    try:
        repo = TrackedRepository.objects.get(id=repo_id)  # noqa: TEAM001 - ID from Celery task queue
    except TrackedRepository.DoesNotExist:
        logger.warning(f"TrackedRepository with id {repo_id} not found")
        return {"error": f"TrackedRepository with id {repo_id} not found"}

    if not repo.is_active:
        return {"skipped": True, "reason": "Repository is not active"}

    try:
        languages = update_repo_languages(repo)
        return {
            "repo": repo.full_name,
            "languages_count": len(languages),
            "primary_language": repo.primary_language,
        }
    except Exception as e:
        logger.exception(f"Failed to refresh languages for {repo.full_name}")
        return {"error": str(e)}


@shared_task
def refresh_all_repo_languages_task() -> dict:
    """Refresh language breakdown for all active repositories.

    Scheduled monthly to keep language data current.

    Returns:
        Dict with count of repos updated and errors
    """
    from datetime import timedelta

    from django.db.models import Q
    from django.utils import timezone

    from apps.integrations.services.github_repo_languages import update_repo_languages

    # Find repos that need refresh (never updated or updated > 30 days ago)
    threshold = timezone.now() - timedelta(days=30)
    repos = TrackedRepository.objects.filter(  # noqa: TEAM001 - Background task for all teams
        is_active=True,
    ).filter(Q(languages_updated_at__isnull=True) | Q(languages_updated_at__lt=threshold))

    updated = 0
    errors = []

    for repo in repos:
        try:
            update_repo_languages(repo)
            updated += 1
        except Exception as e:
            logger.warning(f"Failed to update languages for {repo.full_name}: {e}")
            errors.append({"repo": repo.full_name, "error": str(e)})

    logger.info(f"Refreshed languages for {updated} repos, {len(errors)} errors")

    return {
        "repos_updated": updated,
        "errors_count": len(errors),
        "errors": errors[:10],  # First 10 errors only
    }
