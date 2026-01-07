"""Copilot metrics Celery tasks.

This module contains tasks for syncing GitHub Copilot usage metrics.
Tasks respect feature flags and skip execution when flags are disabled.
"""

import logging

from celery import shared_task
from celery.exceptions import Retry

from apps.integrations.models import GitHubIntegration
from apps.integrations.services.copilot_metrics import (
    CopilotMetricsError,
    fetch_copilot_metrics,
    map_copilot_to_ai_usage,
    parse_metrics_response,
)
from apps.integrations.services.integration_flags import COPILOT_FEATURE_FLAGS
from apps.teams.models import Team
from apps.utils.errors import sanitize_error

logger = logging.getLogger(__name__)


def is_copilot_sync_enabled(team: Team) -> bool:
    """Check if Copilot sync is enabled for a team.

    Uses the copilot_enabled feature flag to determine if sync should run.
    For Celery tasks (no request context), we check the flag globally.

    Args:
        team: The team to check

    Returns:
        True if Copilot sync is enabled, False otherwise
    """
    # Check if master flag is enabled globally (for superusers or everyone)
    from apps.teams.models import Flag

    flag_name = COPILOT_FEATURE_FLAGS.get("copilot_enabled")
    if not flag_name:
        return False

    try:
        flag = Flag.objects.get(name=flag_name)
        # For Celery tasks, check if flag is enabled for everyone or superusers
        # Since we don't have a request context, we use global flag state
        return flag.everyone or flag.superusers
    except Flag.DoesNotExist:
        logger.warning(f"Copilot feature flag '{flag_name}' not found")
        return False


def is_copilot_sync_globally_enabled() -> bool:
    """Check if Copilot sync is globally enabled (for scheduled tasks).

    This is used by sync_all_copilot_metrics to check before dispatching tasks.

    Returns:
        True if Copilot sync is globally enabled, False otherwise
    """
    from apps.teams.models import Flag

    flag_name = COPILOT_FEATURE_FLAGS.get("copilot_enabled")
    if not flag_name:
        return False

    try:
        flag = Flag.objects.get(name=flag_name)
        return flag.everyone or flag.superusers
    except Flag.DoesNotExist:
        logger.warning(f"Copilot feature flag '{flag_name}' not found")
        return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=180, time_limit=240)
def sync_copilot_metrics_task(self, team_id: int) -> dict:
    """Sync Copilot metrics for a team.

    A-006: Added soft_time_limit=180s, time_limit=240s to prevent GitHub API hangs.

    Args:
        self: Celery task instance (bound task)
        team_id: ID of the Team to sync Copilot metrics for

    Returns:
        Dict with sync results (metrics_synced) or error/skip status
    """
    from apps.metrics.models import AIUsageDaily, TeamMember

    # Get Team by id
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": f"Team with id {team_id} not found"}

    # Check feature flag before proceeding
    if not is_copilot_sync_enabled(team):
        logger.info(f"Copilot sync skipped for team {team.name} - flag disabled")
        return {"status": "skipped", "reason": "flag_disabled"}

    # Get GitHubIntegration for team
    try:
        github_integration = GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        logger.info(f"No GitHub integration found for team {team.name}")
        return {"skipped": True, "reason": "No GitHub integration"}

    # Get access token and org_slug
    access_token = github_integration.credential.access_token
    org_slug = github_integration.organization_slug

    if not org_slug:
        logger.info(f"No organization selected for team {team.name}")
        return {"skipped": True, "reason": "No organization selected"}

    # Fetch Copilot metrics
    logger.info(f"Starting Copilot metrics sync for team: {team.name} (org: {org_slug})")
    try:
        raw_metrics = fetch_copilot_metrics(access_token, org_slug, since=None, until=None)
        parsed_metrics = parse_metrics_response(raw_metrics)

        metrics_synced = 0

        # Batch fetch all TeamMembers for per-user data (fix N+1 query)
        all_usernames = set()
        for day_data in parsed_metrics:
            if "per_user_data" in day_data:
                for user_data in day_data["per_user_data"]:
                    username = user_data.get("github_username")
                    if username:
                        all_usernames.add(username)

        # Single query to fetch all team members by username
        members_by_username = {
            m.github_username: m for m in TeamMember.objects.filter(team=team, github_username__in=all_usernames)
        }

        # Process each day's metrics
        for day_data in parsed_metrics:
            # Check if there's per-user data
            if "per_user_data" in day_data:
                # Create records for each user
                for user_data in day_data["per_user_data"]:
                    github_username = user_data.get("github_username")
                    if not github_username:
                        continue

                    # Find matching TeamMember from pre-fetched dict (O(1) lookup)
                    member = members_by_username.get(github_username)
                    if not member:
                        logger.warning(
                            f"No TeamMember found with github_username={github_username} for team {team.name}"
                        )
                        continue

                    # Map user data to AIUsageDaily fields
                    mapped_data = map_copilot_to_ai_usage(user_data, github_username=github_username)

                    # Store in AIUsageDaily
                    AIUsageDaily.objects.update_or_create(
                        team=team,
                        member=member,
                        date=mapped_data["date"],
                        source=mapped_data["source"],
                        defaults={
                            "suggestions_shown": mapped_data["suggestions_shown"],
                            "suggestions_accepted": mapped_data["suggestions_accepted"],
                            "acceptance_rate": mapped_data.get("acceptance_rate"),
                        },
                    )
                    metrics_synced += 1
            else:
                # Org-level data - store with first available team member
                members = TeamMember.objects.filter(team=team).first()
                if not members:
                    logger.warning(f"No team members found for team {team.name}")
                    continue

                # Map org data to AIUsageDaily fields
                mapped_data = map_copilot_to_ai_usage(day_data)

                # Store in AIUsageDaily
                AIUsageDaily.objects.update_or_create(
                    team=team,
                    member=members,
                    date=mapped_data["date"],
                    source=mapped_data["source"],
                    defaults={
                        "suggestions_shown": mapped_data["suggestions_shown"],
                        "suggestions_accepted": mapped_data["suggestions_accepted"],
                        "acceptance_rate": mapped_data.get("acceptance_rate"),
                    },
                )
                metrics_synced += 1

        logger.info(f"Successfully synced {metrics_synced} Copilot metrics for team {team.name}")
        return {"metrics_synced": metrics_synced}

    except CopilotMetricsError as exc:
        # Check if it's a 403 error (Copilot not available)
        if "403" in str(exc):
            logger.info(f"Copilot not available for team {team.name}: {exc}")
            return {"error": sanitize_error(exc), "copilot_available": False}
        # For other CopilotMetricsError, treat as transient and retry
        countdown = self.default_retry_delay * (2**self.request.retries)
        try:
            logger.warning(f"Copilot sync failed for {team.name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            raise
        except Exception:
            from sentry_sdk import capture_exception

            logger.error(f"Copilot sync failed permanently for {team.name}: {exc}")
            capture_exception(exc)
            return {"error": sanitize_error(exc)}

    except Exception as exc:
        # Calculate exponential backoff
        countdown = self.default_retry_delay * (2**self.request.retries)

        try:
            # Retry with exponential backoff
            logger.warning(f"Copilot sync failed for {team.name}, retrying in {countdown}s: {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        except Retry:
            # Re-raise Retry exception to allow Celery to retry
            raise
        except Exception:
            # Max retries exhausted - log to Sentry and return error
            from sentry_sdk import capture_exception

            logger.error(f"Copilot sync failed permanently for {team.name}: {exc}")
            capture_exception(exc)
            return {"error": sanitize_error(exc)}


@shared_task
def sync_all_copilot_metrics() -> dict:
    """Dispatch Copilot sync tasks for all teams with GitHub integration.

    Returns:
        Dict with count of dispatched tasks: teams_dispatched
    """
    # Check global feature flag before dispatching any tasks
    if not is_copilot_sync_globally_enabled():
        logger.info("Copilot sync skipped - global flag disabled")
        return {"status": "skipped", "reason": "flag_disabled"}

    logger.info("Starting Copilot metrics sync for all teams")

    # Query all teams with GitHub integrations
    integrations = GitHubIntegration.objects.exclude(organization_slug__isnull=True).exclude(  # noqa: TEAM001 - System job iterating all integrations
        organization_slug=""
    )

    teams_dispatched = 0

    # Dispatch sync task for each team
    for integration in integrations:
        try:
            sync_copilot_metrics_task.delay(integration.team_id)
            teams_dispatched += 1
        except Exception as e:
            # Log dispatch errors and continue with remaining teams
            logger.error(f"Failed to dispatch Copilot sync task for team {integration.team_id}: {e}")
            continue

    logger.info(f"Finished dispatching Copilot sync tasks. Dispatched: {teams_dispatched}")

    return {
        "teams_dispatched": teams_dispatched,
    }
