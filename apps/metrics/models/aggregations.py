"""Aggregation models: AIUsageDaily, WeeklyMetrics, ReviewerCorrelation."""

from decimal import Decimal

from django.db import models

from apps.teams.models import BaseTeamModel

from .team import TeamMember


class AIUsageDaily(BaseTeamModel):
    """Daily AI tool usage metrics (Copilot, Cursor, etc.)."""

    SOURCE_CHOICES = [
        ("copilot", "GitHub Copilot"),
        ("cursor", "Cursor"),
    ]

    member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name="ai_usage",
        verbose_name="Team Member",
        help_text="The team member who used the AI tool",
    )
    date = models.DateField(
        verbose_name="Date",
        help_text="The date for this usage record",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        verbose_name="Source",
        help_text="AI tool source (Copilot, Cursor, etc.)",
    )

    active_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Active Hours",
        help_text="Hours the AI tool was active",
    )
    suggestions_shown = models.IntegerField(
        default=0,
        verbose_name="Suggestions Shown",
        help_text="Number of AI suggestions shown",
    )
    suggestions_accepted = models.IntegerField(
        default=0,
        verbose_name="Suggestions Accepted",
        help_text="Number of AI suggestions accepted",
    )
    acceptance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Acceptance Rate",
        help_text="Percentage of suggestions accepted",
    )

    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Synced at",
        help_text="Last time this usage data was synced",
    )

    class Meta:
        ordering = ["-date", "member"]
        verbose_name = "AI Usage Daily"
        verbose_name_plural = "AI Usage Daily"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "member", "date", "source"],
                name="unique_team_member_date_source",
            )
        ]
        indexes = [
            # Keep only the heavily-used index (1.6M uses)
            # Removed: ai_usage_date_idx (4K uses, 13MB)
            # Removed: ai_usage_source_date_idx (487 uses, 15MB)
            models.Index(fields=["member", "date"], name="ai_usage_member_date_idx"),
        ]

    def __str__(self):
        return f"{self.member} - {self.source} - {self.date}"


class WeeklyMetrics(BaseTeamModel):
    """
    Pre-computed weekly metrics for dashboard performance.

    Aggregates metrics by team member and week for efficient dashboard queries.
    """

    member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name="weekly_metrics",
        verbose_name="Team Member",
        help_text="The team member these metrics belong to",
    )
    week_start = models.DateField(
        verbose_name="Week Start",
        help_text="Monday of the week",
    )

    # Delivery metrics
    prs_merged = models.IntegerField(
        default=0,
        verbose_name="PRs Merged",
        help_text="Number of PRs merged this week",
    )
    avg_cycle_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Avg Cycle Time (hours)",
        help_text="Average time from PR creation to merge",
    )
    avg_review_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Avg Review Time (hours)",
        help_text="Average time from PR creation to first review",
    )
    commits_count = models.IntegerField(
        default=0,
        verbose_name="Commits",
        help_text="Number of commits made this week",
    )
    lines_added = models.IntegerField(
        default=0,
        verbose_name="Lines Added",
        help_text="Total lines added this week",
    )
    lines_removed = models.IntegerField(
        default=0,
        verbose_name="Lines Removed",
        help_text="Total lines removed this week",
    )

    # Quality metrics
    revert_count = models.IntegerField(
        default=0,
        verbose_name="Reverts",
        help_text="Number of revert PRs this week",
    )
    hotfix_count = models.IntegerField(
        default=0,
        verbose_name="Hotfixes",
        help_text="Number of hotfix PRs this week",
    )

    # Jira metrics
    story_points_completed = models.DecimalField(
        max_digits=10,
        decimal_places=1,
        default=0,
        verbose_name="Story Points",
        help_text="Total story points completed this week",
    )
    issues_resolved = models.IntegerField(
        default=0,
        verbose_name="Issues Resolved",
        help_text="Number of Jira issues resolved this week",
    )

    # AI metrics
    ai_assisted_prs = models.IntegerField(
        default=0,
        verbose_name="AI-Assisted PRs",
        help_text="Number of PRs created with AI assistance",
    )

    # Survey metrics
    avg_quality_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Avg Quality Rating",
        help_text="Average quality rating from PR surveys",
    )
    surveys_completed = models.IntegerField(
        default=0,
        verbose_name="Surveys Completed",
        help_text="Number of PR surveys completed this week",
    )
    guess_accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Guess Accuracy (%)",
        help_text="Percentage of correct AI usage guesses by reviewers",
    )

    class Meta:
        ordering = ["-week_start", "member"]
        verbose_name = "Weekly Metrics"
        verbose_name_plural = "Weekly Metrics"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "member", "week_start"],
                name="unique_team_member_week",
            )
        ]
        indexes = [
            # Removed: weekly_metrics_week_idx (3 uses, 1.7MB)
            # Keep the member+week index (260K uses)
            models.Index(fields=["member", "week_start"], name="weekly_metrics_member_week_idx"),
        ]

    def __str__(self):
        return f"{self.member} - Week of {self.week_start}"


class ReviewerCorrelation(BaseTeamModel):
    """
    Tracks agreement/disagreement patterns between pairs of reviewers.

    Used to identify:
    - Redundant reviewer pairings (always agree, adding one to both doesn't add value)
    - Complementary reviewers (different perspectives, catch different issues)
    """

    # Reviewer pair
    reviewer_1 = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name="correlations_as_reviewer_1",
        verbose_name="Reviewer 1",
        help_text="First reviewer in the pair",
    )
    reviewer_2 = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name="correlations_as_reviewer_2",
        verbose_name="Reviewer 2",
        help_text="Second reviewer in the pair",
    )

    # Statistics
    prs_reviewed_together = models.IntegerField(
        default=0,
        verbose_name="PRs reviewed together",
        help_text="Number of PRs where both reviewers submitted reviews",
    )
    agreements = models.IntegerField(
        default=0,
        verbose_name="Agreements",
        help_text="Number of PRs where both approved or both requested changes",
    )
    disagreements = models.IntegerField(
        default=0,
        verbose_name="Disagreements",
        help_text="Number of PRs where one approved and the other requested changes",
    )

    # Thresholds for redundancy detection
    REDUNDANCY_THRESHOLD = 95  # 95% agreement rate
    MIN_SAMPLE_SIZE = 10  # Minimum PRs reviewed together

    class Meta:
        ordering = ["-prs_reviewed_together"]
        verbose_name = "Reviewer Correlation"
        verbose_name_plural = "Reviewer Correlations"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "reviewer_1", "reviewer_2"],
                name="unique_team_reviewer_pair",
            )
        ]
        indexes = [
            models.Index(fields=["reviewer_1", "reviewer_2"], name="correlation_pair_idx"),
            models.Index(fields=["prs_reviewed_together"], name="correlation_count_idx"),
        ]

    @property
    def agreement_rate(self):
        """Calculate agreement rate as a percentage."""
        if self.prs_reviewed_together == 0:
            return Decimal("0.00")
        rate = (self.agreements / self.prs_reviewed_together) * 100
        return Decimal(str(round(rate, 2)))

    @property
    def is_redundant(self):
        """Check if this reviewer pair is potentially redundant.

        A pair is considered redundant if:
        - They have reviewed at least MIN_SAMPLE_SIZE PRs together
        - Their agreement rate is >= REDUNDANCY_THRESHOLD
        """
        return self.prs_reviewed_together >= self.MIN_SAMPLE_SIZE and self.agreement_rate >= self.REDUNDANCY_THRESHOLD

    def __str__(self):
        return f"{self.reviewer_1.display_name} ↔ {self.reviewer_2.display_name}: {self.agreement_rate:.2f}% agreement"


# Copilot seat pricing constant
COPILOT_SEAT_PRICE = Decimal("19.00")  # Monthly cost per seat in USD


class CopilotSeatSnapshot(BaseTeamModel):
    """Daily snapshot of Copilot seat utilization for a team.

    Tracks seat counts and utilization for ROI analysis and cost tracking.
    Data is synced from GitHub Billing/Seats API.
    """

    date = models.DateField(
        verbose_name="Date",
        help_text="Date of this snapshot",
    )
    total_seats = models.IntegerField(
        verbose_name="Total Seats",
        help_text="Total number of Copilot seats allocated",
    )
    active_this_cycle = models.IntegerField(
        verbose_name="Active This Cycle",
        help_text="Number of seats with activity this billing cycle",
    )
    inactive_this_cycle = models.IntegerField(
        verbose_name="Inactive This Cycle",
        help_text="Number of seats with no activity this billing cycle",
    )
    pending_cancellation = models.IntegerField(
        default=0,
        verbose_name="Pending Cancellation",
        help_text="Number of seats pending cancellation",
    )
    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Synced At",
        help_text="When this snapshot was last synced",
    )

    class Meta:
        ordering = ["-date"]
        verbose_name = "Copilot Seat Snapshot"
        verbose_name_plural = "Copilot Seat Snapshots"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "date"],
                name="unique_team_copilot_seat_date",
            )
        ]
        indexes = [
            models.Index(fields=["date"], name="copilot_seat_date_idx"),
        ]

    def __str__(self):
        return f"{self.team.name} - {self.date}: {self.active_this_cycle}/{self.total_seats} active"

    @property
    def utilization_rate(self) -> Decimal:
        """Calculate seat utilization rate as a percentage.

        Returns:
            Decimal: Utilization rate (0-100), two decimal places.
        """
        if self.total_seats == 0:
            return Decimal("0.00")
        rate = (Decimal(self.active_this_cycle) / Decimal(self.total_seats)) * 100
        return rate.quantize(Decimal("0.01"))

    @property
    def monthly_cost(self) -> Decimal:
        """Calculate monthly cost based on total seats.

        Returns:
            Decimal: Total monthly cost in USD.
        """
        return (Decimal(self.total_seats) * COPILOT_SEAT_PRICE).quantize(Decimal("0.01"))

    @property
    def wasted_spend(self) -> Decimal:
        """Calculate wasted spend on inactive seats.

        Returns:
            Decimal: Monthly cost of inactive seats in USD.
        """
        return (Decimal(self.inactive_this_cycle) * COPILOT_SEAT_PRICE).quantize(Decimal("0.01"))

    @property
    def cost_per_active_user(self) -> Decimal | None:
        """Calculate effective cost per active user.

        Returns:
            Decimal: Cost per active user in USD, or None if no active users.
        """
        if self.active_this_cycle == 0:
            return None
        return (self.monthly_cost / Decimal(self.active_this_cycle)).quantize(Decimal("0.01"))


class CopilotLanguageDaily(BaseTeamModel):
    """Daily Copilot metrics broken down by programming language.

    Stores language-specific acceptance rates to help CTOs understand
    which languages benefit most from Copilot. Data is synced from
    GitHub Copilot Metrics API.
    """

    date = models.DateField(
        verbose_name="Date",
        help_text="Date of this metrics record",
    )
    language = models.CharField(
        max_length=50,
        verbose_name="Language",
        help_text="Programming language name (e.g., Python, TypeScript)",
    )
    suggestions_shown = models.IntegerField(
        verbose_name="Suggestions Shown",
        help_text="Number of Copilot suggestions shown",
    )
    suggestions_accepted = models.IntegerField(
        verbose_name="Suggestions Accepted",
        help_text="Number of Copilot suggestions accepted",
    )
    lines_suggested = models.IntegerField(
        default=0,
        verbose_name="Lines Suggested",
        help_text="Total lines of code suggested by Copilot",
    )
    lines_accepted = models.IntegerField(
        default=0,
        verbose_name="Lines Accepted",
        help_text="Total lines of suggested code accepted",
    )
    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Synced At",
        help_text="When this record was last synced",
    )

    class Meta:
        ordering = ["-date", "language"]
        verbose_name = "Copilot Language Daily"
        verbose_name_plural = "Copilot Language Daily"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "date", "language"],
                name="unique_team_copilot_language_date",
            )
        ]
        indexes = [
            models.Index(fields=["date"], name="copilot_lang_date_idx"),
        ]

    def __str__(self):
        return f"{self.team.name} - {self.date} - {self.language}: {self.acceptance_rate}%"

    @property
    def acceptance_rate(self) -> Decimal:
        """Calculate acceptance rate as a percentage.

        Returns:
            Decimal: Acceptance rate (0-100), two decimal places.
        """
        if self.suggestions_shown == 0:
            return Decimal("0.00")
        rate = (Decimal(self.suggestions_accepted) / Decimal(self.suggestions_shown)) * 100
        return rate.quantize(Decimal("0.01"))


class CopilotEditorDaily(BaseTeamModel):
    """Daily Copilot metrics broken down by IDE/editor.

    Stores editor-specific usage data from the GitHub Copilot Metrics API
    to help CTOs understand which IDEs are most effective with Copilot.
    """

    date = models.DateField(
        verbose_name="Date",
        help_text="Date of this metrics record",
    )
    editor = models.CharField(
        max_length=100,
        verbose_name="Editor",
        help_text="IDE/editor name (e.g., vscode, jetbrains, neovim)",
    )
    suggestions_shown = models.IntegerField(
        verbose_name="Suggestions Shown",
        help_text="Number of Copilot suggestions shown",
    )
    suggestions_accepted = models.IntegerField(
        verbose_name="Suggestions Accepted",
        help_text="Number of Copilot suggestions accepted",
    )
    active_users = models.IntegerField(
        default=0,
        verbose_name="Active Users",
        help_text="Number of users actively using Copilot in this editor",
    )
    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Synced At",
        help_text="When this record was last synced",
    )

    class Meta:
        ordering = ["-date", "editor"]
        verbose_name = "Copilot Editor Daily"
        verbose_name_plural = "Copilot Editor Daily"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "date", "editor"],
                name="unique_team_copilot_editor_date",
            )
        ]
        indexes = [
            models.Index(fields=["date"], name="copilot_editor_date_idx"),
        ]

    def __str__(self):
        return f"{self.team.name} - {self.date} - {self.editor}: {self.acceptance_rate}%"

    @property
    def acceptance_rate(self) -> Decimal:
        """Calculate acceptance rate as a percentage.

        Returns:
            Decimal: Acceptance rate (0-100), two decimal places.
        """
        if self.suggestions_shown == 0:
            return Decimal("0.00")
        rate = (Decimal(self.suggestions_accepted) / Decimal(self.suggestions_shown)) * 100
        return rate.quantize(Decimal("0.01"))
