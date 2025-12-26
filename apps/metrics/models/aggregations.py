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
