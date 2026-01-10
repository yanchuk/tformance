"""Integration credentials model.

Stores OAuth credentials for external integrations (GitHub, Jira, Slack).
"""

from django.db import models

from apps.teams.models import BaseTeamModel
from apps.users.models import CustomUser
from apps.utils.fields import EncryptedTextField


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
    access_token = EncryptedTextField(
        verbose_name="Access token",
        help_text="OAuth access token for the integration (encrypted at rest)",
    )
    refresh_token = EncryptedTextField(
        blank=True,
        verbose_name="Refresh token",
        help_text="OAuth refresh token for renewing access (encrypted at rest)",
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

    # EC-17: Revocation tracking fields
    is_revoked = models.BooleanField(
        default=False,
        verbose_name="Is revoked",
        help_text="Whether the OAuth token has been revoked",
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Revoked at",
        help_text="When the token was detected as revoked",
    )
    revocation_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Revocation reason",
        help_text="Reason for token revocation (e.g., user revoked in GitHub settings)",
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
