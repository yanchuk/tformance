"""Team member model."""

from django.db import models

from apps.teams.models import BaseTeamModel


class TeamMember(BaseTeamModel):
    """
    A team member representing a developer or team member across various integrations.

    This model unifies identity across GitHub, Jira, and Slack to track a single
    developer's metrics and performance across all integrated tools.
    """

    email = models.EmailField(
        blank=True,
        verbose_name="Email address",
        help_text="Team member's email address",
    )
    display_name = models.CharField(
        max_length=255,
        verbose_name="Display name",
        help_text="How this team member's name is displayed",
    )

    # Integration identities
    github_username = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name="GitHub username",
        help_text="GitHub username for this team member",
    )
    github_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name="GitHub ID",
        help_text="GitHub user ID for this team member",
    )
    jira_account_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name="Jira account ID",
        help_text="Jira account ID for this team member",
    )
    slack_user_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name="Slack user ID",
        help_text="Slack user ID for this team member",
    )

    # Copilot activity tracking
    copilot_last_activity_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Copilot last activity",
        help_text="When this member last used GitHub Copilot",
    )
    copilot_last_editor = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Copilot last editor",
        help_text="Editor used for last Copilot activity (e.g., vscode/1.85.1)",
    )

    # Role
    ROLE_CHOICES = [
        ("developer", "Developer"),
        ("lead", "Lead"),
        ("admin", "Admin"),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="developer",
        verbose_name="Role",
        help_text="Team member's role",
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active status",
        help_text="Whether this team member is currently active",
    )

    class Meta:
        ordering = ["display_name"]
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_id"],
                condition=models.Q(github_id__gt=""),
                name="unique_team_github_id",
            ),
            models.UniqueConstraint(
                fields=["team", "email"],
                condition=models.Q(email__gt=""),
                name="unique_team_email",
            ),
        ]
        indexes = [
            # Composite indexes for sync operations (added for performance)
            models.Index(fields=["team", "github_username"], name="member_team_gh_username_idx"),
            models.Index(fields=["team", "is_active"], name="member_team_active_idx"),
        ]

    def __str__(self):
        return self.display_name

    @property
    def avatar_url(self) -> str:
        """Return GitHub avatar URL for this member.

        Uses GitHub's avatar service which returns profile pictures based on user ID.
        Returns empty string if no GitHub ID is available.
        """
        if self.github_id:
            return f"https://avatars.githubusercontent.com/u/{self.github_id}?s=80"
        return ""

    @property
    def initials(self) -> str:
        """Return initials for fallback avatar display."""
        if self.display_name:
            parts = self.display_name.split()
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[1][0]}".upper()
            return self.display_name[:2].upper()
        return "??"

    @property
    def has_recent_copilot_activity(self) -> bool:
        """Check if member has used Copilot within the last 30 days."""
        if not self.copilot_last_activity_at:
            return False
        from datetime import timedelta

        from django.utils import timezone

        threshold = timezone.now() - timedelta(days=30)
        return self.copilot_last_activity_at >= threshold
