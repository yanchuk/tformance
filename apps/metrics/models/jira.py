"""Jira-related models."""

from django.db import models

from apps.teams.models import BaseTeamModel

from .team import TeamMember


class JiraIssue(BaseTeamModel):
    """
    A Jira issue from the team's Jira workspace.

    Tracks sprint assignments, story points, and cycle time for planning metrics.
    """

    # Jira identifiers
    jira_key = models.CharField(
        max_length=50,
        verbose_name="Jira Key",
        help_text="e.g., PROJ-123",
    )
    jira_id = models.CharField(
        max_length=50,
        verbose_name="Jira ID",
        help_text="Jira's internal ID",
    )

    # Issue details
    summary = models.TextField(
        blank=True,
        verbose_name="Summary",
        help_text="Issue summary/title",
    )
    issue_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Issue Type",
        help_text="Story, Bug, Task, etc.",
    )
    status = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Status",
        help_text="Current issue status",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
        help_text="Full issue description",
    )
    labels = models.JSONField(
        default=list,
        verbose_name="Labels",
        help_text="Issue labels as list",
    )
    priority = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Priority",
        help_text="Issue priority (High, Medium, Low)",
    )
    parent_issue_key = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Parent Issue Key",
        help_text="Parent epic/story key",
    )
    assignee = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jira_issues",
        verbose_name="Assignee",
        help_text="The team member assigned to this issue",
    )

    # Sprint and estimation
    story_points = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="Story Points",
        help_text="Estimated story points",
    )
    sprint_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Sprint ID",
        help_text="The sprint this issue belongs to",
    )
    sprint_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Sprint Name",
        help_text="Human-readable sprint name",
    )

    # Timestamps
    issue_created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Created At",
        help_text="When the issue was created in Jira",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Resolved At",
        help_text="When the issue was resolved",
    )

    # Calculated metrics
    cycle_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cycle Time (hours)",
        help_text="Time from creation to resolution",
    )

    # Sync tracking
    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Synced at",
        help_text="Last time this issue data was synced",
    )

    class Meta:
        ordering = ["-issue_created_at"]
        verbose_name = "Jira Issue"
        verbose_name_plural = "Jira Issues"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "jira_id"],
                name="unique_team_jira_issue",
            )
        ]
        indexes = [
            models.Index(fields=["jira_key"], name="jira_issue_key_idx"),
            models.Index(fields=["resolved_at"], name="jira_resolved_at_idx"),
            models.Index(fields=["assignee", "status"], name="jira_assignee_status_idx"),
            models.Index(fields=["sprint_id"], name="jira_sprint_idx"),
        ]

    def __str__(self):
        return self.jira_key

    @property
    def related_prs(self):
        """Get all PRs that reference this Jira issue via jira_key."""
        from .github import PullRequest

        return PullRequest.objects.filter(team=self.team, jira_key=self.jira_key)
