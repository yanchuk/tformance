"""Copilot activation service.

This module provides functions for activating and deactivating
GitHub Copilot integration for a team.
"""

import logging
from typing import TYPE_CHECKING

from apps.integrations._task_modules.copilot import sync_copilot_metrics_task

if TYPE_CHECKING:
    from apps.teams.models import Team

logger = logging.getLogger(__name__)


def activate_copilot_for_team(team: "Team") -> dict:
    """Activate Copilot integration for a team.

    Sets copilot_status to 'connected' and dispatches the sync task
    to fetch initial metrics from GitHub.

    Args:
        team: The team to activate Copilot for

    Returns:
        dict with keys:
            - status: "activated" or "already_connected"
            - team_id: The team's ID
    """
    # Check if already connected
    if team.copilot_status == "connected":
        logger.info(f"Copilot already connected for team {team.name}")
        return {
            "status": "already_connected",
            "team_id": team.id,
        }

    # Update status to connected
    team.copilot_status = "connected"
    team.save(update_fields=["copilot_status"])

    logger.info(f"Copilot activated for team {team.name}")

    # Dispatch sync task to fetch metrics
    sync_copilot_metrics_task.delay(team.id)

    return {
        "status": "activated",
        "team_id": team.id,
    }


def deactivate_copilot_for_team(team: "Team") -> dict:
    """Deactivate Copilot integration for a team.

    Sets copilot_status to 'disabled'. Does not delete existing data.

    Args:
        team: The team to deactivate Copilot for

    Returns:
        dict with keys:
            - status: "deactivated" or "already_disabled"
            - team_id: The team's ID
    """
    # Check if already disabled
    if team.copilot_status == "disabled":
        logger.info(f"Copilot already disabled for team {team.name}")
        return {
            "status": "already_disabled",
            "team_id": team.id,
        }

    # Update status to disabled
    team.copilot_status = "disabled"
    team.save(update_fields=["copilot_status"])

    logger.info(f"Copilot deactivated for team {team.name}")

    return {
        "status": "deactivated",
        "team_id": team.id,
    }
