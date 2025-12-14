"""Integration status service for fetching team integration status."""

from typing import TypedDict

from apps.integrations.models import (
    GitHubIntegration,
    JiraIntegration,
    SlackIntegration,
    TrackedJiraProject,
    TrackedRepository,
)
from apps.metrics.models import PRSurvey, PullRequest, TeamMember
from apps.teams.models import Team


class GitHubStatus(TypedDict):
    """GitHub integration status."""

    connected: bool
    org_name: str | None
    member_count: int
    repo_count: int


class JiraStatus(TypedDict):
    """Jira integration status."""

    connected: bool
    site_name: str | None
    project_count: int


class SlackStatus(TypedDict):
    """Slack integration status."""

    connected: bool
    workspace_name: str | None


class TeamIntegrationStatus(TypedDict):
    """Team integration status."""

    github: GitHubStatus
    jira: JiraStatus
    slack: SlackStatus
    has_data: bool
    pr_count: int
    survey_count: int


def get_team_integration_status(team: Team) -> TeamIntegrationStatus:
    """
    Get the integration status for a team.

    Args:
        team: Team object to get integration status for

    Returns:
        dict: Integration status with the following structure:
            {
                'github': {
                    'connected': bool,
                    'org_name': str | None,
                    'member_count': int,
                    'repo_count': int,
                },
                'jira': {
                    'connected': bool,
                    'site_name': str | None,
                    'project_count': int,
                },
                'slack': {
                    'connected': bool,
                    'workspace_name': str | None,
                },
                'has_data': bool,
                'pr_count': int,
                'survey_count': int,
            }
    """
    # GitHub integration status
    github_integration = GitHubIntegration.objects.filter(team=team).first()
    github_status = {
        "connected": github_integration is not None,
        "org_name": github_integration.organization_slug if github_integration else None,
        "member_count": TeamMember.objects.filter(team=team, github_id__isnull=False).exclude(github_id="").count(),
        "repo_count": TrackedRepository.objects.filter(team=team).count() if github_integration else 0,
    }

    # Jira integration status
    jira_integration = JiraIntegration.objects.filter(team=team).first()
    jira_status = {
        "connected": jira_integration is not None,
        "site_name": jira_integration.site_name if jira_integration else None,
        "project_count": TrackedJiraProject.objects.filter(team=team).count() if jira_integration else 0,
    }

    # Slack integration status
    slack_integration = SlackIntegration.objects.filter(team=team).first()
    slack_status = {
        "connected": slack_integration is not None,
        "workspace_name": slack_integration.workspace_name if slack_integration else None,
    }

    # Data counts
    pr_count = PullRequest.objects.filter(team=team).count()
    survey_count = PRSurvey.objects.filter(team=team).count()
    has_data = pr_count > 0

    return {
        "github": github_status,
        "jira": jira_status,
        "slack": slack_status,
        "has_data": has_data,
        "pr_count": pr_count,
        "survey_count": survey_count,
    }
