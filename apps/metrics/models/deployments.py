"""Deployment model."""

from django.db import models

from apps.teams.models import BaseTeamModel

from .pull_requests import PullRequest
from .team import TeamMember


class Deployment(BaseTeamModel):
    """
    A deployment from GitHub.

    Tracks deployment events to production and staging environments,
    including status, creator, and associated pull requests.
    """

    STATUS_CHOICES = [
        ("success", "Success"),
        ("failure", "Failure"),
        ("pending", "Pending"),
        ("error", "Error"),
    ]

    ENVIRONMENT_CHOICES = [
        ("production", "Production"),
        ("staging", "Staging"),
    ]

    github_deployment_id = models.BigIntegerField(
        verbose_name="GitHub Deployment ID",
        help_text="The deployment ID from GitHub",
    )
    github_repo = models.CharField(
        max_length=255,
        verbose_name="GitHub repository",
        help_text="Repository name (e.g., 'owner/repo')",
    )
    environment = models.CharField(
        max_length=100,
        choices=ENVIRONMENT_CHOICES,
        verbose_name="Environment",
        help_text="Deployment environment",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name="Status",
        help_text="Deployment status",
    )
    creator = models.ForeignKey(
        TeamMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deployments",
        verbose_name="Creator",
        help_text="The team member who created the deployment",
    )
    deployed_at = models.DateTimeField(
        verbose_name="Deployed at",
        help_text="When the deployment occurred",
    )
    pull_request = models.ForeignKey(
        PullRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deployments",
        verbose_name="Pull request",
        help_text="The PR associated with this deployment",
    )
    sha = models.CharField(
        max_length=40,
        verbose_name="Git SHA",
        help_text="The commit SHA deployed",
    )

    class Meta:
        ordering = ["-deployed_at"]
        verbose_name = "Deployment"
        verbose_name_plural = "Deployments"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_deployment_id"],
                name="unique_team_deployment",
            )
        ]
        indexes = [
            models.Index(fields=["github_repo", "environment"], name="deployment_repo_env_idx"),
            models.Index(fields=["deployed_at"], name="deployment_deployed_at_idx"),
            models.Index(fields=["status"], name="deployment_status_idx"),
            models.Index(fields=["pull_request"], name="deployment_pr_idx"),
            models.Index(fields=["creator", "status"], name="deployment_creator_status_idx"),
        ]

    def __str__(self):
        return f"{self.github_repo} - {self.environment}"
