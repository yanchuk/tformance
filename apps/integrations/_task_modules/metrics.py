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


def _advance_llm_pipeline_status(team):
    """Advance pipeline status after LLM processing (success or max retries).

    Handles both Phase 1 (llm_processing → computing_metrics) and
    Phase 2 (background_llm → background_metrics) transitions.
    """
    team.refresh_from_db()
    current_status = team.onboarding_pipeline_status
    if current_status == "llm_processing":
        team.update_pipeline_status("computing_metrics")
    elif current_status == "background_llm":
        team.update_pipeline_status("background_metrics")


def _advance_metrics_pipeline_status(team):
    """Advance pipeline status after metrics aggregation (success or failure).

    Handles both Phase 1 (computing_metrics → computing_insights) and
    Phase 2 (background_metrics → background_insights) transitions.
    """
    team.refresh_from_db()
    current_status = team.onboarding_pipeline_status
    if current_status == "computing_metrics":
        team.update_pipeline_status("computing_insights")
    elif current_status == "background_metrics":
        team.update_pipeline_status("background_insights")


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

        # Signal-based pipeline: update status to trigger next task
        _advance_metrics_pipeline_status(team)

        return count
    except Exception as exc:
        from sentry_sdk import capture_exception

        logger.error(f"Failed to aggregate weekly metrics for team {team.name}: {exc}")
        capture_exception(exc)

        # Even on failure, advance pipeline to avoid getting stuck
        # The next stage (computing_insights) can still run with partial/empty data
        logger.warning(f"Advancing pipeline for team {team.name} despite metrics aggregation failure")
        _advance_metrics_pipeline_status(team)

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=900, time_limit=960)
def queue_llm_analysis_batch_task(self, team_id: int, batch_size: int = 50) -> dict:
    """Process PRs missing LLM analysis in batches.

    Time limits increased to 15/16 min to handle batch API polling + retry:
    - First batch submission + polling (~5-10 min)
    - Retry batch for failures (~5 min)
    - Results download and saving (~1 min)

    Args:
        self: Celery task instance (bound task)
        team_id: The team to process PRs for
        batch_size: Number of PRs to process per batch (default 50)

    Returns:
        Dict with prs_processed count or error status
    """
    from celery.exceptions import SoftTimeLimitExceeded

    # Verify team exists
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": "Team not found", "prs_processed": 0}

    # Mark PRs without body - they can't be analyzed by LLM
    # This prevents them from being re-queried on every batch
    prs_without_body = PullRequest.objects.filter(
        team=team,
        llm_summary__isnull=True,
        body="",
    )
    no_body_count = prs_without_body.count()
    if no_body_count > 0:
        # Mark with placeholder so they aren't re-queried
        prs_without_body.update(llm_summary={"skipped": True, "reason": "no_body"})
        logger.info(f"Marked {no_body_count} PRs without body as skipped for team {team.name}")

    # Find PRs with body missing llm_summary for this team
    prs_to_process = list(
        PullRequest.objects.filter(
            team=team,
            llm_summary__isnull=True,
        )
        .exclude(body="")  # Only process PRs with body content
        .select_related("author")
        .prefetch_related("files", "commits", "reviews__reviewer", "comments__author")[:batch_size]
    )

    if not prs_to_process:
        logger.info(f"No PRs need LLM processing for team {team.name}")
        _advance_llm_pipeline_status(team)
        return {"prs_processed": 0, "message": "No PRs need processing"}

    logger.info(f"Starting LLM batch analysis for {len(prs_to_process)} PRs for team {team.name}")

    # Process with LLM using GroqBatchProcessor
    # Wrap in try/except to catch time limit and other errors
    processor = GroqBatchProcessor()
    try:
        results, stats = processor.submit_batch_with_fallback(prs_to_process)
        logger.info(f"Batch completed for team {team.name}: stats={stats}")
    except SoftTimeLimitExceeded:
        logger.error(f"LLM batch task timed out for team {team.name}")
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying LLM batch for team {team.name} (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(countdown=60) from None
        else:
            # Max retries exhausted - advance pipeline with partial results
            logger.warning(f"LLM batch max retries exhausted for team {team.name}, advancing pipeline")
            _advance_llm_pipeline_status(team)
            return {"error": "timeout_max_retries", "prs_processed": 0}
    except Exception as e:
        logger.exception(f"LLM batch failed for team {team.name}: {e}")
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying LLM batch for team {team.name} (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=e, countdown=60) from None
        else:
            # Max retries exhausted - advance pipeline with partial results
            logger.warning(f"LLM batch max retries exhausted for team {team.name}, advancing pipeline")
            _advance_llm_pipeline_status(team)
            return {"error": str(e), "prs_processed": 0}

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

    # Check if there are more PRs to process
    remaining_prs = PullRequest.objects.filter(
        team=team,
        llm_summary__isnull=True,
    ).count()

    if remaining_prs > 0:
        # More PRs to process - requeue self
        logger.info(f"{remaining_prs} PRs still need LLM processing for team {team.name}, requeueing...")
        self.apply_async(args=[team_id], kwargs={"batch_size": batch_size}, countdown=2)
    else:
        # All PRs processed - update status to trigger next task
        _advance_llm_pipeline_status(team)
        logger.info(f"LLM processing complete for team {team.name}, advanced to next phase")

    return {"prs_processed": prs_updated, "remaining": remaining_prs}
