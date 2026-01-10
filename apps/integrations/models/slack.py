"""Slack integration models.

Contains:
- SlackIntegration: Slack OAuth integration configuration with leaderboard scheduling
"""

from datetime import time

from django.db import models

from apps.integrations.constants import (
    SYNC_STATUS_CHOICES,
    SYNC_STATUS_COMPLETE,
    SYNC_STATUS_ERROR,
    SYNC_STATUS_PENDING,
    SYNC_STATUS_SYNCING,
)
from apps.teams.models import BaseTeamModel

from .credentials import IntegrationCredential


class SlackIntegration(BaseTeamModel):
    """
    Slack integration configuration for a team.
    Links to an IntegrationCredential for OAuth tokens.
    Manages leaderboard scheduling and feature toggles.
    """

    # Import sync status constants from shared constants module
    SYNC_STATUS_PENDING = SYNC_STATUS_PENDING
    SYNC_STATUS_SYNCING = SYNC_STATUS_SYNCING
    SYNC_STATUS_COMPLETE = SYNC_STATUS_COMPLETE
    SYNC_STATUS_ERROR = SYNC_STATUS_ERROR
    SYNC_STATUS_CHOICES = SYNC_STATUS_CHOICES

    credential = models.OneToOneField(
        IntegrationCredential,
        on_delete=models.CASCADE,
        related_name="slack_integration",
        verbose_name="Credential",
        help_text="OAuth credential for this Slack integration",
    )
    workspace_id = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name="Workspace ID",
        help_text="Slack workspace/team ID (e.g., T12345678)",
    )
    workspace_name = models.CharField(
        max_length=255,
        verbose_name="Workspace name",
        help_text="Slack workspace name",
    )
    bot_user_id = models.CharField(
        max_length=20,
        verbose_name="Bot user ID",
        help_text="Slack bot user ID (e.g., U12345678)",
    )
    leaderboard_channel_id = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Leaderboard channel ID",
        help_text="Slack channel ID for leaderboard posts",
    )
    leaderboard_day = models.IntegerField(
        default=0,
        verbose_name="Leaderboard day",
        help_text="Day of week for leaderboard (0=Monday, 6=Sunday)",
    )
    leaderboard_time = models.TimeField(
        default=time(9, 0),
        verbose_name="Leaderboard time",
        help_text="Time of day to post leaderboard",
    )
    leaderboard_enabled = models.BooleanField(
        default=True,
        verbose_name="Leaderboard enabled",
        help_text="Whether weekly leaderboards are enabled",
    )
    surveys_enabled = models.BooleanField(
        default=True,
        verbose_name="Surveys enabled",
        help_text="Whether PR surveys are enabled",
    )
    reveals_enabled = models.BooleanField(
        default=True,
        verbose_name="Reveals enabled",
        help_text="Whether AI reveal prompts are enabled",
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last sync at",
        help_text="When data was last synced from Slack",
    )
    sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default=SYNC_STATUS_PENDING,
        db_index=True,
        verbose_name="Sync status",
        help_text="Current status of data synchronization",
    )
    last_sync_error = models.TextField(
        null=True,
        blank=True,
        verbose_name="Last sync error",
        help_text="Error message from the last failed sync attempt",
    )

    class Meta:
        ordering = ["workspace_name"]
        verbose_name = "Slack Integration"
        verbose_name_plural = "Slack Integrations"
        constraints = [
            models.UniqueConstraint(fields=["team", "workspace_id"], name="unique_team_workspace"),
        ]
        indexes = [
            models.Index(fields=["sync_status", "last_sync_at"], name="slack_int_sync_status_idx"),
            models.Index(fields=["workspace_id"], name="slack_int_workspace_id_idx"),
        ]

    def __str__(self):
        return f"Slack: {self.workspace_name}"
