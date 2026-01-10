"""GitHub integration models.

Contains:
- GitHubIntegration: GitHub OAuth integration configuration
- GitHubAppInstallation: GitHub App installation with token caching
- TrackedRepository: Repositories being tracked for metrics
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
from apps.utils.fields import EncryptedTextField

from .credentials import IntegrationCredential


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
    webhook_secret = EncryptedTextField(
        verbose_name="Webhook secret",
        help_text="Secret for validating GitHub webhook payloads (encrypted at rest)",
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

    # Member sync fields - track status of GitHub org member sync to TeamMember records
    member_sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default=SYNC_STATUS_PENDING,
        verbose_name="Member sync status",
        help_text="Current status of member synchronization from GitHub org",
    )
    member_sync_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Member sync started at",
        help_text="When member sync was started",
    )
    member_sync_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Member sync completed at",
        help_text="When member sync was completed",
    )
    member_sync_error = models.TextField(
        blank=True,
        default="",
        verbose_name="Member sync error",
        help_text="Error message from the last failed member sync attempt",
    )
    member_sync_result = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Member sync result",
        help_text="JSON result data from the last member sync (e.g., counts of created/updated members)",
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


class GitHubAppInstallation(BaseTeamModel):
    """
    GitHub App installation for a team.
    Stores installation metadata and cached access tokens.

    Note: team is nullable because the installation is created before the team
    is linked during the onboarding callback.
    """

    # Override team to allow null - installation created before team linkage
    team = models.ForeignKey(
        "teams.Team",
        verbose_name="Team",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    installation_id = models.BigIntegerField(
        unique=True,
        verbose_name="Installation ID",
        help_text="GitHub App installation ID",
    )
    account_type = models.CharField(
        max_length=20,
        verbose_name="Account type",
        help_text="Type of GitHub account (Organization or User)",
    )
    account_login = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Account login",
        help_text="GitHub account login/username",
    )
    account_id = models.BigIntegerField(
        verbose_name="Account ID",
        help_text="GitHub account ID",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is active",
        help_text="Whether this installation is active",
    )
    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Suspended at",
        help_text="When the installation was suspended",
    )
    permissions = models.JSONField(
        default=dict,
        verbose_name="Permissions",
        help_text="Permissions granted to the GitHub App",
    )
    events = models.JSONField(
        default=list,
        verbose_name="Events",
        help_text="Events the GitHub App is subscribed to",
    )
    repository_selection = models.CharField(
        max_length=20,
        default="selected",
        verbose_name="Repository selection",
        help_text="Repository access selection (all or selected)",
    )
    cached_token = EncryptedTextField(
        blank=True,
        verbose_name="Cached token",
        help_text="Cached installation access token (encrypted at rest)",
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Token expires at",
        help_text="When the cached token expires",
    )

    class Meta:
        db_table = "integrations_github_app_installation"
        verbose_name = "GitHub App Installation"
        verbose_name_plural = "GitHub App Installations"

    def __str__(self):
        return f"GitHub App: {self.account_login} ({self.installation_id})"

    def _token_is_valid(self) -> bool:
        """Check if cached token is valid (not within 5-minute buffer of expiry)."""
        from datetime import timedelta

        from django.utils import timezone

        if not self.cached_token or not self.token_expires_at:
            return False
        return self.token_expires_at > timezone.now() + timedelta(minutes=5)

    def _get_deactivated_error_message(self) -> str:
        """Get appropriate error message for deactivated installation.

        Edge case #9: Distinguishes between suspended and deleted installations
        to provide appropriate guidance to users.
        """
        if self.suspended_at:
            # Suspended by GitHub - user should contact org admin
            return (
                f"GitHub App installation for {self.account_login} was suspended by GitHub. "
                f"Please contact your organization administrator to resolve this issue."
            )
        else:
            # Deleted/removed - user should reinstall
            return (
                f"GitHub App installation for {self.account_login} was removed. "
                f"Please reinstall the GitHub App to continue syncing."
            )

    def get_access_token(self) -> str:
        """Get valid access token, refreshing if expired.

        Returns cached token if valid (not within 5-minute buffer of expiry).
        Otherwise fetches a new token, caches it, and returns it.

        Uses database locking (select_for_update) to prevent race conditions
        when multiple concurrent requests try to refresh the token simultaneously.

        Returns:
            Valid installation access token string

        Raises:
            GitHubAppDeactivatedError: If installation is not active
            GitHubAppError: If token retrieval fails
        """
        from django.db import transaction

        from apps.integrations.exceptions import GitHubAppDeactivatedError
        from apps.integrations.services.github_app import get_installation_token_with_expiry

        # EC-12: Refresh is_active from DB to detect webhook deactivation
        # This handles race where webhook deactivates installation during sync task
        self.refresh_from_db(fields=["is_active", "suspended_at"])

        # Check is_active first (Edge case #7)
        if not self.is_active:
            raise GitHubAppDeactivatedError(self._get_deactivated_error_message())

        # Quick check without lock - return cached if valid
        if self._token_is_valid():
            return self.cached_token

        # Acquire database lock before refreshing (Edge case #1)
        # This prevents multiple concurrent requests from all calling GitHub API
        with transaction.atomic():
            # Re-fetch with lock to get fresh state
            locked_self = GitHubAppInstallation.objects.select_for_update().get(  # noqa: TEAM001 - Self pk lookup
                pk=self.pk
            )

            # Check is_active again after acquiring lock
            if not locked_self.is_active:
                raise GitHubAppDeactivatedError(locked_self._get_deactivated_error_message())

            # Check if another thread already refreshed the token
            if locked_self._token_is_valid():
                # Update self with the fresh values
                self.cached_token = locked_self.cached_token
                self.token_expires_at = locked_self.token_expires_at
                return locked_self.cached_token

            # Fetch new token from GitHub API
            token, expires_at = get_installation_token_with_expiry(locked_self.installation_id)

            # Save to the locked instance
            locked_self.cached_token = token
            locked_self.token_expires_at = expires_at
            locked_self.save(update_fields=["cached_token", "token_expires_at"])

            # Update self with new values
            self.cached_token = token
            self.token_expires_at = expires_at

            return token


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
        help_text="GitHub OAuth integration (deprecated, use app_installation)",
        null=True,
        blank=True,
    )
    app_installation = models.ForeignKey(
        GitHubAppInstallation,
        on_delete=models.CASCADE,
        related_name="tracked_repositories",
        verbose_name="App Installation",
        help_text="GitHub App installation for accessing this repository",
        null=True,
        blank=True,
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

    # Rate limit tracking (Phase 1)
    rate_limit_remaining = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Rate limit remaining",
        help_text="Remaining API requests for this sync",
    )
    rate_limit_reset_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Rate limit reset at",
        help_text="When rate limit resets",
    )

    # Language detection (for LLM tech detection)
    languages = models.JSONField(
        default=dict,
        verbose_name="Languages",
        help_text="Language breakdown from GitHub API (e.g., {'Python': 150000, 'JavaScript': 5000})",
    )
    primary_language = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Primary language",
        help_text="Most-used language in this repository",
    )
    languages_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Languages updated at",
        help_text="When language data was last fetched from GitHub",
    )

    # Progress tracking (Phase 2)
    sync_progress = models.IntegerField(
        default=0,
        verbose_name="Sync progress",
        help_text="Sync progress percentage (0-100)",
    )
    sync_prs_total = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Total PRs to sync",
        help_text="Total PRs to sync",
    )
    sync_prs_completed = models.IntegerField(
        default=0,
        verbose_name="PRs synced",
        help_text="PRs synced so far",
    )
    sync_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Sync started at",
        help_text="When sync started",
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

    @property
    def access_token(self) -> str:
        """Get access token for GitHub API access.

        Edge case #10: Implements auth fallback logic:
        1. Try App installation first (when available and active)
        2. Fall back to OAuth credential if App unavailable/inactive
        3. Raise GitHubAuthError if neither available

        Returns:
            Valid access token (from App installation or OAuth)

        Raises:
            GitHubAuthError: If no valid authentication is available
        """
        from apps.integrations.exceptions import GitHubAppDeactivatedError, GitHubAuthError

        # Try App installation first (preferred)
        if self.app_installation is not None:
            try:
                return self.app_installation.get_access_token()
            except GitHubAppDeactivatedError:
                # App is inactive, try OAuth fallback
                pass

        # Fall back to OAuth credential
        if self.integration is not None and self.integration.credential is not None:
            return self.integration.credential.access_token

        # Neither auth method available
        raise GitHubAuthError(
            f"Repository {self.full_name} has no valid authentication. Please reconnect via Integrations settings."
        )
