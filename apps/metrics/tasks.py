"""Celery tasks for computing daily insights."""

import logging
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
