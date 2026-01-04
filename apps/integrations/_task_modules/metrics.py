"""Metrics aggregation Celery tasks.

This module contains tasks for metrics processing:
- Weekly metrics aggregation
- LLM batch analysis for PRs
"""

import logging

from celery import shared_task

from apps.integrations.models import GitHubIntegration
from apps.integrations.services.groq_batch import GroqBatchProcessor
from apps.metrics.models import PullRequest
from apps.metrics.services.aggregation_service import aggregate_team_weekly_metrics
from apps.teams.models import Team

logger = logging.getLogger(__name__)


@shared_task
def aggregate_team_weekly_metrics_task(team_id: int):
    """Aggregate weekly metrics for a single team.

    Args:
        team_id: ID of the Team to aggregate metrics for

    Returns:
        int: Count of WeeklyMetrics records created/updated, or None/0 if error
    """
    from datetime import date, timedelta

    # Get Team by id
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return None

    # Calculate previous week's Monday
    today = date.today()
    days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
    this_monday = today - timedelta(days=days_since_monday)
    previous_monday = this_monday - timedelta(days=7)

    # Call aggregation service
    logger.info(f"Starting weekly metrics aggregation for team {team.name} (week starting {previous_monday})")
    try:
        weekly_metrics = aggregate_team_weekly_metrics(team, previous_monday)
        count = len(weekly_metrics)
        logger.info(f"Successfully aggregated {count} weekly metrics for team {team.name}")
        return count
    except Exception as exc:
        from sentry_sdk import capture_exception

        logger.error(f"Failed to aggregate weekly metrics for team {team.name}: {exc}")
        capture_exception(exc)
        return 0


@shared_task
def aggregate_all_teams_weekly_metrics_task():
    """Aggregate weekly metrics for all teams with GitHub integration.

    Returns:
        int: Count of teams processed
    """
    logger.info("Starting weekly metrics aggregation for all teams")

    # Find all teams with GitHubIntegration
    integrations = GitHubIntegration.objects.select_related("team").all()  # noqa: TEAM001 - System job iterating all integrations

    teams_processed = 0

    # Dispatch aggregate_team_weekly_metrics_task for each team
    for integration in integrations:
        try:
            aggregate_team_weekly_metrics_task.delay(integration.team.id)
            teams_processed += 1
        except Exception as e:
            logger.error(f"Failed to dispatch weekly metrics aggregation for team {integration.team.id}: {e}")
            continue

    logger.info(f"Finished dispatching weekly metrics aggregation tasks. Processed: {teams_processed}")

    return teams_processed


@shared_task(bind=True, soft_time_limit=600, time_limit=660)
def queue_llm_analysis_batch_task(self, team_id: int, batch_size: int = 50) -> dict:
    """Process PRs missing LLM analysis in batches.

    A-006: Added soft_time_limit=600s (10 min), time_limit=660s (11 min) for LLM batch processing.

    Args:
        self: Celery task instance (bound task)
        team_id: The team to process PRs for
        batch_size: Number of PRs to process per batch (default 50)

    Returns:
        Dict with prs_processed count or error status
    """
    # Verify team exists
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": "Team not found", "prs_processed": 0}

    # Find PRs missing llm_summary for this team
    prs_to_process = list(
        PullRequest.objects.filter(
            team=team,
            llm_summary__isnull=True,
        )
        .select_related("author")
        .prefetch_related("files", "commits", "reviews__reviewer", "comments__author")[:batch_size]
    )

    if not prs_to_process:
        logger.info(f"No PRs need LLM processing for team {team.name}")
        return {"prs_processed": 0, "message": "No PRs need processing"}

    logger.info(f"Starting LLM batch analysis for {len(prs_to_process)} PRs for team {team.name}")

    # Process with LLM using GroqBatchProcessor
    processor = GroqBatchProcessor()
    results, stats = processor.submit_batch_with_fallback(prs_to_process)

    # Update PRs with results
    prs_updated = 0
    for result in results:
        if result.error:
            logger.warning(f"LLM analysis failed for PR {result.pr_id}: {result.error}")
            continue

        try:
            pr = PullRequest.objects.get(id=result.pr_id)  # noqa: TEAM001 - ID from LLM batch result
            pr.llm_summary = result.llm_summary
            pr.save(update_fields=["llm_summary"])
            prs_updated += 1
        except PullRequest.DoesNotExist:
            logger.warning(f"PR {result.pr_id} not found when updating LLM results")

    logger.info(f"Successfully updated {prs_updated} PRs with LLM analysis for team {team.name}")

    return {"prs_processed": prs_updated}
