from django.db import models

from apps.metrics.seeding.real_projects import INDUSTRIES
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.teams.models import Team
from apps.utils.models import BaseModel

INDUSTRY_CHOICES = [(key, label) for key, label in INDUSTRIES.items()]

ROLE_CHOICES = [
    ("maintainer", "Maintainer"),
    ("contributor", "Contributor"),
    ("fan", "Fan"),
]

REQUEST_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]


class PublicOrgProfile(BaseModel):
    """Profile for organizations whose metrics are publicly visible.

    Extends BaseModel (not BaseTeamModel) because public analytics
    intentionally cross team boundaries.
    """

    team = models.OneToOneField(
        Team,
        on_delete=models.CASCADE,
        related_name="public_profile",
    )
    public_slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Clean URL slug (e.g., 'posthog' not 'posthog-demo')",
    )
    industry = models.CharField(
        max_length=50,
        choices=INDUSTRY_CHOICES,
        help_text="Industry category for benchmarking",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Short description from GitHub org",
    )
    github_org_url = models.URLField(
        blank=True,
        default="",
        help_text="GitHub organization URL",
    )
    logo_url = models.URLField(
        blank=True,
        default="",
        help_text="Organization logo URL",
    )
    is_public = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this org appears on public pages",
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Clean organization name for display",
    )

    class Meta:
        verbose_name = "Public Org Profile"
        verbose_name_plural = "Public Org Profiles"

    def __str__(self):
        return self.display_name

    @property
    def avatar_url(self):
        """Return logo_url if set, else derive from github_org_url."""
        if self.logo_url:
            return self.logo_url
        if self.github_org_url:
            org_name = self.github_org_url.rstrip("/").split("/")[-1]
            return f"https://github.com/{org_name}.png?size=160"
        return f"https://github.com/{self.public_slug}.png?size=160"

    @property
    def has_sufficient_data(self):
        """Return True when org has enough PR data for public pages."""
        try:
            stats = self.stats
        except PublicOrgStats.DoesNotExist:
            return False
        return stats.total_prs >= MIN_PRS_THRESHOLD


class PublicOrgStats(BaseModel):
    """Pre-computed statistics for a public organization.

    Refreshed by Celery after each daily sync. Directory page queries
    this model directly for instant response times (~70 rows).
    """

    org_profile = models.OneToOneField(
        PublicOrgProfile,
        on_delete=models.CASCADE,
        related_name="stats",
    )
    total_prs = models.IntegerField(
        default=0,
        help_text="Total merged PRs analyzed",
    )
    ai_assisted_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage of PRs that are AI-assisted",
    )
    median_cycle_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Median cycle time in hours",
    )
    median_review_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Median review time in hours",
    )
    active_contributors_90d = models.IntegerField(
        default=0,
        help_text="Unique PR authors in last 90 days",
    )
    top_ai_tools = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {tool, count, pct} dicts",
    )
    last_computed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When stats were last computed",
    )

    class Meta:
        verbose_name = "Public Org Stats"
        verbose_name_plural = "Public Org Stats"

    def __str__(self):
        return f"Stats for {self.org_profile.display_name}"


class PublicRepoProfileManager(models.Manager):
    """Custom manager with DRY queryset filters for common catalog queries."""

    def sync_eligible(self):
        """Repos eligible for daily sync: public + sync enabled."""
        return self.filter(
            is_public=True,
            sync_enabled=True,
        ).select_related("team", "org_profile", "sync_state")

    def snapshot_eligible(self):
        """Repos eligible for snapshot building: public repo + public org."""
        return self.filter(
            is_public=True,
            org_profile__is_public=True,
        ).select_related("org_profile", "team")


class PublicRepoProfile(BaseModel):
    """Profile for a public repository within an organization.

    Uses BaseModel (not BaseTeamModel) because public analytics
    intentionally cross team boundaries. The team FK provides
    data access for queries against PullRequest.
    """

    org_profile = models.ForeignKey(
        PublicOrgProfile,
        on_delete=models.CASCADE,
        related_name="repos",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="public_repo_profiles",
    )
    github_repo = models.CharField(
        max_length=200,
        help_text="Full owner/repo format matching PullRequest.github_repo",
    )
    repo_slug = models.SlugField(
        max_length=100,
        help_text="URL slug for the repo (e.g., 'posthog')",
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Clean repository name for display",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Short description from GitHub",
    )
    github_url = models.URLField(
        blank=True,
        default="",
        help_text="GitHub repository URL",
    )
    is_flagship = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this is a flagship repo shown prominently",
    )
    is_public = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this repo appears on public pages",
    )

    objects = PublicRepoProfileManager()

    sync_enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether future syncs run for this repo",
    )
    insights_enabled = models.BooleanField(
        default=False,
        help_text="Whether weekly LLM insights are generated",
    )
    initial_backfill_days = models.PositiveIntegerField(
        default=180,
        help_text="Days of history to backfill on first sync",
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order in listings (lower = first)",
    )

    class Meta:
        verbose_name = "Public Repo Profile"
        verbose_name_plural = "Public Repo Profiles"
        unique_together = [("org_profile", "repo_slug")]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        # Team derivation: always sync from org_profile
        if self.org_profile_id:
            self.team = self.org_profile.team
        is_new = self._state.adding
        super().save(*args, **kwargs)
        # Auto-create sync state for new profiles
        if is_new:
            PublicRepoSyncState.objects.get_or_create(repo_profile=self)


SYNC_STATUS_CHOICES = [
    ("pending_backfill", "Pending Backfill"),
    ("ready", "Ready"),
    ("syncing", "Syncing"),
    ("failed", "Failed"),
]


class PublicRepoSyncState(BaseModel):
    """Tracks sync lifecycle for a public repository.

    Created automatically when a PublicRepoProfile is saved for the first time.
    """

    repo_profile = models.OneToOneField(
        PublicRepoProfile,
        on_delete=models.CASCADE,
        related_name="sync_state",
    )
    status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default="pending_backfill",
    )
    last_successful_sync_at = models.DateTimeField(null=True, blank=True)
    last_attempted_sync_at = models.DateTimeField(null=True, blank=True)
    last_synced_updated_at = models.DateTimeField(null=True, blank=True)
    checkpoint_payload = models.JSONField(default=dict, blank=True)
    last_error = models.TextField(blank=True, default="")
    last_backfill_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Public Repo Sync State"
        verbose_name_plural = "Public Repo Sync States"

    def __str__(self):
        return f"SyncState for {self.repo_profile.display_name} ({self.status})"


class PublicRepoStats(BaseModel):
    """Pre-computed statistics for a public repository.

    Stores all data needed to render the canonical repo page.
    Refreshed daily by the snapshot service after PR sync.
    """

    repo_profile = models.OneToOneField(
        PublicRepoProfile,
        on_delete=models.CASCADE,
        related_name="stats",
    )
    summary_window_days = models.IntegerField(
        default=30,
        help_text="Number of days in summary window",
    )
    trend_window_days = models.IntegerField(
        default=90,
        help_text="Number of days in trend window",
    )
    total_prs = models.IntegerField(
        default=0,
        help_text="Total merged PRs (all-time)",
    )
    total_prs_in_window = models.IntegerField(
        default=0,
        help_text="Merged PRs in summary window",
    )
    ai_assisted_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="AI-assisted PR percentage in window",
    )
    median_cycle_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Median cycle time in hours",
    )
    median_review_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Median review time in hours",
    )
    active_contributors_30d = models.IntegerField(
        default=0,
        help_text="Unique PR authors in last 30 days",
    )
    cadence_change_pct = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text="Period-over-period PR volume change %",
    )
    best_signal = models.JSONField(
        default=dict,
        blank=True,
        help_text="Most positive metric signal",
    )
    watchout_signal = models.JSONField(
        default=dict,
        blank=True,
        help_text="Most concerning metric signal",
    )
    trend_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="90-day trend series for charts",
    )
    breakdown_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tech/AI tools/PR type breakdowns",
    )
    recent_prs = models.JSONField(
        default=list,
        blank=True,
        help_text="Recent merged PRs for proof block",
    )
    benchmark_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Industry/peer benchmark context",
    )
    last_computed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When stats were last computed",
    )

    class Meta:
        verbose_name = "Public Repo Stats"
        verbose_name_plural = "Public Repo Stats"

    def __str__(self):
        return f"Stats for {self.repo_profile.display_name}"


class PublicRepoInsight(BaseModel):
    """LLM-generated narrative insight for a public repository.

    Generated weekly via Groq Batch. Only the latest successful
    insight has is_current=True; previous ones are kept for history.
    """

    repo_profile = models.ForeignKey(
        PublicRepoProfile,
        on_delete=models.CASCADE,
        related_name="insights",
    )
    content = models.TextField(
        help_text="LLM-generated insight narrative",
    )
    insight_type = models.CharField(
        max_length=50,
        help_text="Type of insight (e.g., 'weekly')",
    )
    is_current = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this is the active insight",
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this insight was generated",
    )
    batch_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Groq batch ID for traceability",
    )

    class Meta:
        verbose_name = "Public Repo Insight"
        verbose_name_plural = "Public Repo Insights"

    def __str__(self):
        return f"Insight for {self.repo_profile.display_name} ({self.insight_type})"


class PublicRepoRequest(BaseModel):
    """Request from an OSS maintainer to add their repo to public analytics."""

    github_url = models.URLField(
        help_text="GitHub repository URL",
    )
    email = models.EmailField(
        help_text="Contact email",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="Requester's relationship to the project",
    )
    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS_CHOICES,
        default="pending",
        help_text="Review status",
    )

    class Meta:
        verbose_name = "Public Repo Request"
        verbose_name_plural = "Public Repo Requests"

    def __str__(self):
        return f"{self.github_url} ({self.status})"
