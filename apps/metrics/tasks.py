"""Celery tasks for computing daily insights and LLM analysis."""

import json
import logging
import os
import time
from datetime import date

from celery import shared_task

from apps.metrics.insights import engine
from apps.metrics.insights.rules import (
    AIAdoptionTrendRule,
    CIFailureRateRule,
    CycleTimeTrendRule,
    HotfixSpikeRule,
    RedundantReviewerRule,
    RevertSpikeRule,
    UnlinkedPRsRule,
)
from apps.metrics.models import PullRequest
from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
    PROMPT_VERSION,
    get_user_prompt,
)
from apps.teams.models import Team

logger = logging.getLogger(__name__)


# Conditionally assign register_rule and compute_insights only if not already set (allows mocking)
if "register_rule" not in globals():
    register_rule = engine.register_rule
if "compute_insights" not in globals():
    compute_insights = engine.compute_insights

# Register all insight rules when module is imported
register_rule(AIAdoptionTrendRule)
register_rule(CycleTimeTrendRule)
register_rule(HotfixSpikeRule)
register_rule(RevertSpikeRule)
register_rule(CIFailureRateRule)
register_rule(RedundantReviewerRule)
register_rule(UnlinkedPRsRule)


@shared_task
def compute_team_insights(team_id: int) -> int:
    """Compute insights for a single team.

    Args:
        team_id: The ID of the team to compute insights for

    Returns:
        Count of insights created

    Raises:
        Team.DoesNotExist: If the team_id does not exist
    """
    team = Team.objects.get(id=team_id)
    insights = compute_insights(team, date.today())
    return len(insights)


@shared_task
def compute_all_team_insights() -> dict:
    """Compute insights for all teams by dispatching individual tasks.

    Returns:
        Dictionary with count of teams dispatched
    """
    teams = Team.objects.all()
    teams_dispatched = 0

    for team in teams:
        try:
            compute_team_insights.delay(team.id)
            teams_dispatched += 1
        except Exception as e:
            logger.exception("Failed to dispatch compute_team_insights for team %s: %s", team.id, e)
            continue

    return {"teams_dispatched": teams_dispatched}


# Import Groq lazily to avoid import errors when not installed
def Groq(*args, **kwargs):
    """Lazy import of Groq client."""
    from groq import Groq as GroqClient

    return GroqClient(*args, **kwargs)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def run_llm_analysis_batch(self, team_id: int, limit: int = 50, rate_limit_delay: float = 2.1) -> dict:
    """Run LLM analysis on PRs for a team to populate llm_summary.

    Processes PRs that either:
    - Don't have llm_summary yet
    - Have an older llm_summary_version than current PROMPT_VERSION

    Args:
        self: Celery task instance (bound task)
        team_id: ID of the team to process PRs for
        limit: Maximum number of PRs to process per run (default: 50)
        rate_limit_delay: Seconds between API calls (default: 2.1 for 30 req/min)

    Returns:
        Dict with processed count, error count, and skipped count
    """
    # Check for API key
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY environment variable not set")
        return {"error": "GROQ_API_KEY not set"}

    # Get team
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        logger.warning(f"Team with id {team_id} not found")
        return {"error": f"Team with id {team_id} not found"}

    # Find PRs that need processing
    qs = PullRequest.objects.filter(  # noqa: TEAM001 - team filter applied below
        team=team,
        body__isnull=False,
    ).exclude(body="")

    # Only process PRs without llm_summary or with older version
    qs = qs.filter(llm_summary__isnull=True) | qs.exclude(llm_summary_version=PROMPT_VERSION)

    # Prefetch related data for v6.1.0 - avoid N+1 queries
    prs = list(
        qs.select_related("author")
        .prefetch_related("files", "commits", "reviews__reviewer")
        .order_by("-pr_created_at")[:limit]
    )

    if not prs:
        logger.info(f"No PRs need LLM analysis for team {team.name}")
        return {"processed": 0, "errors": 0, "skipped": 0}

    logger.info(f"Processing {len(prs)} PRs for team {team.name} with LLM analysis")

    # Initialize Groq client
    client = Groq(api_key=api_key)

    processed = 0
    errors = 0

    for pr in prs:
        try:
            # Extract related data (v6.1.0)
            file_paths = list(pr.files.values_list("filename", flat=True))
            commit_messages = list(pr.commits.values_list("message", flat=True))
            reviewers = list(
                set(r.reviewer.display_name for r in pr.reviews.all() if r.reviewer and r.reviewer.display_name)
            )

            # Build user prompt with full PR context
            user_prompt = get_user_prompt(
                pr_body=pr.body or "",
                pr_title=pr.title or "",
                additions=pr.additions or 0,
                deletions=pr.deletions or 0,
                comment_count=pr.total_comments or 0,
                state=pr.state or "",
                labels=pr.labels or [],
                is_draft=pr.is_draft or False,
                is_hotfix=pr.is_hotfix or False,
                is_revert=pr.is_revert or False,
                cycle_time_hours=pr.cycle_time_hours,
                review_time_hours=pr.review_time_hours,
                commits_after_first_review=pr.commits_after_first_review,
                review_rounds=pr.review_rounds,
                # v6.1.0 - Additional context
                file_paths=file_paths,
                commit_messages=commit_messages,
                reviewers=reviewers,
                milestone=pr.milestone_title or None,
                assignees=pr.assignees or [],
                linked_issues=[str(i) for i in pr.linked_issues] if pr.linked_issues else [],
                jira_key=pr.jira_key or None,
                author_name=pr.author.display_name if pr.author else None,
            )

            # Call Groq API
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": PR_ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=800,
            )

            # Parse and store response
            content = response.choices[0].message.content
            llm_summary = json.loads(content)

            pr.llm_summary = llm_summary
            pr.llm_summary_version = PROMPT_VERSION
            pr.save(update_fields=["llm_summary", "llm_summary_version"])

            processed += 1
            logger.debug(f"Processed PR #{pr.github_pr_id}: {pr.title[:50]}")

            # Rate limiting
            time.sleep(rate_limit_delay)

        except Exception as e:
            logger.warning(f"Error processing PR #{pr.github_pr_id}: {e}")
            errors += 1
            # Back off on errors
            time.sleep(rate_limit_delay * 2)

    logger.info(f"LLM analysis complete for team {team.name}: {processed} processed, {errors} errors")
    return {"processed": processed, "errors": errors, "skipped": len(prs) - processed - errors}


@shared_task
def run_all_teams_llm_analysis(limit_per_team: int = 50) -> dict:
    """Run LLM analysis for all teams by dispatching individual tasks.

    Args:
        limit_per_team: Max PRs to process per team (default: 50)

    Returns:
        Dictionary with count of teams dispatched
    """
    teams = Team.objects.all()
    teams_dispatched = 0

    for team in teams:
        try:
            run_llm_analysis_batch.delay(team_id=team.id, limit=limit_per_team)
            teams_dispatched += 1
        except Exception as e:
            logger.exception(f"Failed to dispatch run_llm_analysis_batch for team {team.id}: {e}")
            continue

    logger.info(f"Dispatched LLM analysis tasks for {teams_dispatched} teams")
    return {"teams_dispatched": teams_dispatched}
