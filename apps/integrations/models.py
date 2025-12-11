from django.db import models

from apps.integrations.constants import (
    SYNC_STATUS_CHOICES,
    SYNC_STATUS_COMPLETE,
    SYNC_STATUS_ERROR,
    SYNC_STATUS_PENDING,
    SYNC_STATUS_SYNCING,
)
from apps.teams.models import BaseTeamModel
from apps.users.models import CustomUser


class IntegrationCredential(BaseTeamModel):
    """
    OAuth credentials for external integrations (GitHub, Jira, Slack).
    One credential per provider per team.
    """

    PROVIDER_GITHUB = "github"
    PROVIDER_JIRA = "jira"
    PROVIDER_SLACK = "slack"

    PROVIDER_CHOICES = [
        (PROVIDER_GITHUB, "GitHub"),
        (PROVIDER_JIRA, "Jira"),
        (PROVIDER_SLACK, "Slack"),
    ]

    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        db_index=True,
        verbose_name="Provider",
        help_text="The integration provider (GitHub, Jira, or Slack)",
    )
    access_token = models.TextField(
        verbose_name="Access token",
        help_text="OAuth access token for the integration",
    )
    refresh_token = models.TextField(
        blank=True,
        verbose_name="Refresh token",
        help_text="OAuth refresh token for renewing access",
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Token expires at",
        help_text="When the access token expires",
    )
    scopes = models.JSONField(
        default=list,
        verbose_name="Scopes",
        help_text="OAuth scopes granted for this integration",
    )
    connected_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="connected_integrations",
        verbose_name="Connected by",
        help_text="The user who connected this integration",
    )

    class Meta:
        ordering = ["provider"]
        verbose_name = "Integration Credential"
        verbose_name_plural = "Integration Credentials"
        constraints = [
            models.UniqueConstraint(fields=["team", "provider"], name="unique_team_provider"),
        ]

    def __str__(self):
        return f"{self.provider} for {self.team.name}"


class GitHubIntegration(BaseTeamModel):
    """
    GitHub integration configuration for a team.
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
        related_name="github_integration",
        verbose_name="Credential",
        help_text="OAuth credential for this GitHub integration",
    )
    organization_slug = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Organization slug",
        help_text="GitHub organization login/slug",
    )
    organization_id = models.BigIntegerField(
        verbose_name="Organization ID",
        help_text="GitHub organization ID",
    )
    webhook_secret = models.CharField(
        max_length=100,
        verbose_name="Webhook secret",
        help_text="Secret for validating GitHub webhook payloads",
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last sync at",
        help_text="When data was last synced from GitHub",
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
        ordering = ["organization_slug"]
        verbose_name = "GitHub Integration"
        verbose_name_plural = "GitHub Integrations"
        indexes = [
            models.Index(fields=["sync_status", "last_sync_at"], name="github_int_sync_status_idx"),
            models.Index(fields=["organization_slug"], name="github_int_org_slug_idx"),
        ]

    def __str__(self):
        return f"GitHub: {self.organization_slug}"


class TrackedRepository(BaseTeamModel):
    """
    Repositories being tracked for metrics collection.
    Each repository belongs to a GitHubIntegration.
    """

    # Import sync status constants from shared constants module
    SYNC_STATUS_PENDING = SYNC_STATUS_PENDING
    SYNC_STATUS_SYNCING = SYNC_STATUS_SYNCING
    SYNC_STATUS_COMPLETE = SYNC_STATUS_COMPLETE
    SYNC_STATUS_ERROR = SYNC_STATUS_ERROR
    SYNC_STATUS_CHOICES = SYNC_STATUS_CHOICES

    integration = models.ForeignKey(
        GitHubIntegration,
        on_delete=models.CASCADE,
        related_name="tracked_repositories",
        verbose_name="Integration",
        help_text="GitHub integration this repository belongs to",
    )
    github_repo_id = models.BigIntegerField(
        verbose_name="GitHub repository ID",
        help_text="GitHub repository ID",
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name="Full name",
        help_text="Repository full name in owner/repo format",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is active",
        help_text="Whether this repository is actively being tracked",
    )
    webhook_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Webhook ID",
        help_text="GitHub webhook ID for this repository",
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last sync at",
        help_text="When data was last synced from this repository",
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
        ordering = ["full_name"]
        verbose_name = "Tracked Repository"
        verbose_name_plural = "Tracked Repositories"
        constraints = [
            models.UniqueConstraint(fields=["team", "github_repo_id"], name="unique_team_github_repo"),
        ]
        indexes = [
            models.Index(fields=["full_name"], name="tracked_repo_name_idx"),
            models.Index(fields=["github_repo_id"], name="tracked_repo_gh_id_idx"),
            models.Index(fields=["is_active", "last_sync_at"], name="tracked_repo_active_sync_idx"),
            models.Index(fields=["integration", "is_active"], name="tracked_repo_int_active_idx"),
            models.Index(fields=["sync_status", "last_sync_at"], name="tracked_repo_sync_status_idx"),
        ]

    def __str__(self):
        return self.full_name
