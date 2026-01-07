"""Integration status service for fetching team integration status."""

from typing import TypedDict

from django.db.models import Avg

from apps.integrations.constants import SYNC_STATUS_COMPLETE, SYNC_STATUS_SYNCING
from apps.integrations.models import (
    GitHubAppInstallation,
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
    # EC-18: Revocation status fields
    is_revoked: bool
    error: str | None


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

    # EC-18: Check for revocation status
    is_revoked = False
    error = None

    # Check if App installation is inactive (uninstalled)
    app_installation = GitHubAppInstallation.objects.filter(team=team).first()
    if app_installation and not app_installation.is_active:
        is_revoked = True
        error = "GitHub App was uninstalled. Please reconnect."

    # Check if OAuth credential is revoked
    if github_integration and github_integration.credential and github_integration.credential.is_revoked:
        is_revoked = True
        error = "OAuth access was revoked. Please reconnect."

    github_status = {
        "connected": github_integration is not None,
        "org_name": github_integration.organization_slug if github_integration else None,
        "member_count": TeamMember.objects.filter(team=team, github_id__isnull=False).exclude(github_id="").count(),
        "repo_count": TrackedRepository.objects.filter(team=team).count() if github_integration else 0,
        "is_revoked": is_revoked,
        "error": error,
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


class SyncStatus(TypedDict):
    """Repository sync status for a team."""

    sync_in_progress: bool
    sync_progress_percent: int
    repos_syncing: list[str]
    repos_total: int
    repos_synced: int
    pipeline_status: str | None


def get_team_sync_status(team: Team) -> SyncStatus:
    """
    Get the repository sync status for a team.

    Args:
        team: Team object to get sync status for

    Returns:
        SyncStatus dict with:
            - sync_in_progress: True if any repos are syncing OR pipeline is active
            - sync_progress_percent: Average progress across all repos (0-100)
            - repos_syncing: List of full_name for repos currently syncing
            - repos_total: Total number of tracked repositories
            - repos_synced: Number of repos that have completed sync
            - pipeline_status: Current pipeline status (for display purposes)
    """
    team_repos = TrackedRepository.objects.filter(team=team)

    # Get syncing repo names
    repos_syncing = list(team_repos.filter(sync_status=SYNC_STATUS_SYNCING).values_list("full_name", flat=True))

    # Get counts
    repos_total = team_repos.count()
    repos_synced = team_repos.filter(sync_status=SYNC_STATUS_COMPLETE).count()

    # Calculate average sync progress
    if repos_total > 0:
        avg_progress = team_repos.aggregate(avg=Avg("sync_progress"))["avg"]
        sync_progress_percent = int(avg_progress) if avg_progress else 0
    else:
        sync_progress_percent = 0

    # Check if pipeline is actively running (not in terminal states)
    # Widget should show during both Phase 1 and Phase 2
    terminal_states = {"complete", "failed", "not_started", None}
    pipeline_status = team.onboarding_pipeline_status
    pipeline_active = pipeline_status not in terminal_states

    # Sync in progress if repos syncing OR pipeline active
    sync_in_progress = len(repos_syncing) > 0 or pipeline_active

    return {
        "sync_in_progress": sync_in_progress,
        "sync_progress_percent": sync_progress_percent,
        "repos_syncing": repos_syncing,
        "repos_total": repos_total,
        "repos_synced": repos_synced,
        "pipeline_status": pipeline_status,
    }
