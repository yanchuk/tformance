import logging
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext
from waffle import get_setting
from waffle.models import CACHE_EMPTY, AbstractUserFlag
from waffle.utils import get_cache, keyfmt

from apps.subscriptions.models import SubscriptionModelBase
from apps.utils.models import BaseModel
from apps.web.meta import absolute_url

from . import roles
from .context import EmptyTeamContextException, get_current_team


class Team(SubscriptionModelBase, BaseModel):
    """
    A Team, with members.
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="teams", through="Membership")
    onboarding_complete = models.BooleanField(
        default=True,
        help_text="Whether the team has completed the onboarding flow. "
        "Default True for existing teams; set False during onboarding creation.",
    )

    # Onboarding pipeline tracking (Two-Phase)
    # Phase 1: Quick Start (30 days) → syncing_members → syncing → llm_processing → metrics → insights → phase1_complete
    # Phase 2: Background (31-90 days) → background_syncing → background_llm → complete
    PIPELINE_STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("syncing_members", "Syncing Team Members"),  # A-025: sync members before PRs
        ("syncing", "Syncing PRs"),
        ("llm_processing", "Analyzing with AI"),
        ("computing_metrics", "Computing Metrics"),
        ("computing_insights", "Computing Insights"),
        ("phase1_complete", "Dashboard Ready"),  # Phase 1 done, user can access dashboard
        ("background_syncing", "Background: Syncing"),  # Phase 2: syncing older data
        ("background_llm", "Background: Analyzing"),  # Phase 2: LLM on older data
        ("complete", "Complete"),
        ("failed", "Failed"),
    ]

    onboarding_pipeline_status = models.CharField(
        max_length=50,
        choices=PIPELINE_STATUS_CHOICES,
        default="not_started",
        help_text="Current status of the onboarding data processing pipeline.",
    )
    onboarding_pipeline_error = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if pipeline failed.",
    )
    onboarding_pipeline_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the pipeline started processing.",
    )
    onboarding_pipeline_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the pipeline completed (success or failure).",
    )

    # Phase 2 background progress tracking (0-100%)
    background_sync_progress = models.IntegerField(
        default=0,
        help_text="Progress of Phase 2 background sync (0-100%).",
    )
    background_llm_progress = models.IntegerField(
        default=0,
        help_text="Progress of Phase 2 background LLM analysis (0-100%).",
    )

    # your team customizations go here.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track original status for signal-based pipeline dispatch
        # This allows detecting actual status changes vs regular saves
        self._original_pipeline_status = self.onboarding_pipeline_status

    def __str__(self):
        return self.name

    @property
    def email(self):
        return self.membership_set.filter(role=roles.ROLE_ADMIN).first().user.email

    def get_quantity(self) -> int:
        # by default do per-seat billing based on the number of team members
        return self.members.count()

    @property
    def sorted_memberships(self):
        return self.membership_set.order_by("user__email")

    def pending_invitations(self):
        return self.invitations.filter(is_accepted=False)

    @property
    def dashboard_url(self) -> str:
        return reverse("teams:switch_team", kwargs={"team_slug": self.slug})

    @property
    def pipeline_in_progress(self) -> bool:
        """Return True if any onboarding pipeline phase is currently running.

        Includes both Phase 1 (quick start) and Phase 2 (background) statuses.
        """
        return self.onboarding_pipeline_status in [
            "syncing_members",
            "syncing",
            "llm_processing",
            "computing_metrics",
            "computing_insights",
            "background_syncing",
            "background_llm",
        ]

    @property
    def dashboard_accessible(self) -> bool:
        """Return True if dashboard should be accessible to the user.

        Dashboard is accessible when:
        1. onboarding_complete is True (legacy teams)
        2. Pipeline status indicates Phase 1+ is complete
        """
        if self.onboarding_complete:
            return True
        return self.onboarding_pipeline_status in [
            "phase1_complete",
            "background_syncing",
            "background_llm",
            "complete",
        ]

    @property
    def background_in_progress(self) -> bool:
        """Return True if Phase 2 background processing is running.

        Used to show progress banner in dashboard.
        """
        return self.onboarding_pipeline_status in [
            "background_syncing",
            "background_llm",
            "background_metrics",
            "background_insights",
        ]

    def update_background_progress(
        self,
        sync_progress: int | None = None,
        llm_progress: int | None = None,
    ) -> None:
        """Update Phase 2 background progress percentages.

        Args:
            sync_progress: Progress of background sync (0-100), or None to leave unchanged
            llm_progress: Progress of background LLM (0-100), or None to leave unchanged
        """
        update_fields = []

        if sync_progress is not None:
            # Clamp to 0-100
            self.background_sync_progress = max(0, min(100, sync_progress))
            update_fields.append("background_sync_progress")

        if llm_progress is not None:
            # Clamp to 0-100
            self.background_llm_progress = max(0, min(100, llm_progress))
            update_fields.append("background_llm_progress")

        if update_fields:
            self.save(update_fields=update_fields)

    def update_pipeline_status(self, status: str, error: str | None = None) -> None:
        """
        Update the pipeline status and related fields.

        Args:
            status: One of the PIPELINE_STATUS_CHOICES values
            error: Optional error message (only stored if status is 'failed')
        """
        from django.utils import timezone

        self.onboarding_pipeline_status = status

        # Set started_at when pipeline begins
        if status == "syncing" and self.onboarding_pipeline_started_at is None:
            self.onboarding_pipeline_started_at = timezone.now()

        # Set completed_at when pipeline ends (success or failure)
        if status in ["complete", "failed"]:
            self.onboarding_pipeline_completed_at = timezone.now()

        # Store error message only for failed status, clear otherwise
        if status == "failed" and error:
            self.onboarding_pipeline_error = error
        elif status != "failed":
            self.onboarding_pipeline_error = None

        self.save(
            update_fields=[
                "onboarding_pipeline_status",
                "onboarding_pipeline_error",
                "onboarding_pipeline_started_at",
                "onboarding_pipeline_completed_at",
            ]
        )


class Membership(BaseModel):
    """
    A user's team membership
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=100, choices=roles.ROLE_CHOICES)
    # your additional membership fields go here.

    def __str__(self):
        return f"{self.user}: {self.team}"

    def is_admin(self) -> bool:
        return self.role == roles.ROLE_ADMIN

    class Meta:
        # Ensure a user can only be associated with a team once.
        unique_together = ("team", "user")


class Invitation(BaseModel):
    """
    An invitation for new team members.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=100, choices=roles.ROLE_CHOICES, default=roles.ROLE_MEMBER)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invitations")
    is_accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accepted_invitations", null=True, blank=True
    )

    def get_url(self) -> str:
        return absolute_url(reverse("teams:accept_invitation", args=[self.id]))


class TeamScopedManager(models.Manager):
    """Model manager that will automatically filter the queryset using the team from the global
    team context. If no team is set in the context, it will return an empty queryset unless
    the `STRICT_TEAM_CONTEXT` setting is `True` in which case it will raise an exception.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        team = get_current_team()
        if team is None:
            if getattr(settings, "STRICT_TEAM_CONTEXT", False):
                raise EmptyTeamContextException("Team missing from context")
            else:
                logging.warning("Team not available in filtered context. Use `set_current_team()`.")
            return queryset.none()
        return queryset.filter(team=team)


class BaseTeamModel(BaseModel):
    """
    Abstract model for objects that are part of a team.
    """

    team = models.ForeignKey(Team, verbose_name=gettext("Team"), on_delete=models.CASCADE)

    # Default unfiltered manager
    # Having the default manager unfiltered is import and for Django Admin and anywhere
    # else where the queryset is not easily customizable.
    # See https://docs.djangoproject.com/en/stable/topics/db/managers/#default-managers
    objects = models.Manager()

    # pre-filtered to the current team
    for_team = TeamScopedManager()

    class Meta:
        abstract = True


class Flag(AbstractUserFlag):
    """Custom Waffle flag to support usage with teams.

    See https://waffle.readthedocs.io/en/stable/types/flag.html#custom-flag-models"""

    FLAG_TEAMS_CACHE_KEY = "FLAG_TEAMS_CACHE_KEY"
    FLAG_TEAMS_CACHE_KEY_DEFAULT = "flag:%s:teams"

    teams = models.ManyToManyField(
        Team,
        blank=True,
        help_text=gettext("Activate this flag for these teams."),
    )

    def get_flush_keys(self, flush_keys=None):
        flush_keys = super().get_flush_keys(flush_keys)
        teams_cache_key = get_setting(Flag.FLAG_TEAMS_CACHE_KEY, Flag.FLAG_TEAMS_CACHE_KEY_DEFAULT)
        flush_keys.append(keyfmt(teams_cache_key, self.name))
        return flush_keys

    def is_active(self, request, read_only=False):
        is_active = super().is_active(request, read_only)
        if is_active:
            return is_active

        if not self.pk:
            # flag not created
            return False

        team = request.team
        if team:
            team_ids = self._get_team_ids()
            return team.pk in team_ids

    def _get_team_ids(self):
        cache = get_cache()
        cache_key = keyfmt(get_setting(Flag.FLAG_TEAMS_CACHE_KEY, Flag.FLAG_TEAMS_CACHE_KEY_DEFAULT), self.name)
        cached = cache.get(cache_key)
        if cached == CACHE_EMPTY:
            return set()
        if cached:
            return cached

        team_ids = set(self.teams.all().values_list("pk", flat=True))
        cache.add(cache_key, team_ids or CACHE_EMPTY)
        return team_ids
