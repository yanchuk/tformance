"""Jira integration models.

Contains:
- JiraIntegration: Jira OAuth integration configuration
- TrackedJiraProject: Jira projects being tracked for metrics
"""

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


class JiraIntegration(BaseTeamModel):
    """
    Jira integration configuration for a team.
    Links to an IntegrationCredential for OAuth tokens.
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
        related_name="jira_integration",
        verbose_name="Credential",
        help_text="OAuth credential for this Jira integration",
    )
    cloud_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Cloud ID",
        help_text="Atlassian cloud ID",
    )
    site_name = models.CharField(
        max_length=255,
        verbose_name="Site name",
        help_text="Jira site name",
    )
    site_url = models.URLField(
        verbose_name="Site URL",
        help_text="Jira site URL",
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last sync at",
        help_text="When data was last synced from Jira",
    )
    sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default=SYNC_STATUS_PENDING,
        db_index=True,
        verbose_name="Sync status",
        help_text="Current status of data synchronization",
    )

    class Meta:
        ordering = ["site_name"]
        verbose_name = "Jira Integration"
        verbose_name_plural = "Jira Integrations"
        indexes = [
            models.Index(fields=["sync_status", "last_sync_at"], name="jira_int_sync_status_idx"),
            models.Index(fields=["cloud_id"], name="jira_int_cloud_id_idx"),
        ]

    def __str__(self):
        return f"Jira: {self.site_name}"


class TrackedJiraProject(BaseTeamModel):
    """
    Jira projects being tracked for metrics collection.
    Each project belongs to a JiraIntegration.
    """

    # Import sync status constants from shared constants module
    SYNC_STATUS_PENDING = SYNC_STATUS_PENDING
    SYNC_STATUS_SYNCING = SYNC_STATUS_SYNCING
    SYNC_STATUS_COMPLETE = SYNC_STATUS_COMPLETE
    SYNC_STATUS_ERROR = SYNC_STATUS_ERROR
    SYNC_STATUS_CHOICES = SYNC_STATUS_CHOICES

    integration = models.ForeignKey(
        JiraIntegration,
        on_delete=models.CASCADE,
        related_name="tracked_jira_projects",
        verbose_name="Integration",
        help_text="Jira integration this project belongs to",
    )
    jira_project_id = models.CharField(
        max_length=50,
        verbose_name="Jira project ID",
        help_text="Jira project ID",
    )
    jira_project_key = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name="Project key",
        help_text="Jira project key (e.g., PROJ, ACME)",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Project name",
        help_text="Jira project name",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is active",
        help_text="Whether this project is actively being tracked",
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last sync at",
        help_text="When data was last synced from this project",
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
        ordering = ["name"]
        verbose_name = "Tracked Jira Project"
        verbose_name_plural = "Tracked Jira Projects"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "jira_project_id"],
                name="unique_team_jira_project",
            )
        ]
        indexes = [
            models.Index(fields=["jira_project_key"], name="tracked_jira_proj_key_idx"),
            models.Index(fields=["is_active", "last_sync_at"], name="tracked_jira_active_sync_idx"),
            models.Index(fields=["integration", "is_active"], name="tracked_jira_int_active_idx"),
            models.Index(fields=["sync_status", "last_sync_at"], name="tracked_jira_sync_status_idx"),
        ]

    def __str__(self):
        return f"{self.jira_project_key}: {self.name}"
