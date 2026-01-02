"""GitHub client service for creating authenticated PyGithub instances."""

from github import Github

from apps.integrations.models import GitHubAppInstallation, IntegrationCredential
from apps.integrations.services.github_app import get_installation_client
from apps.teams.models import Team

__all__ = [
    "NoGitHubConnectionError",
    "get_github_client",
    "get_github_client_for_team",
]


class NoGitHubConnectionError(Exception):
    """Raised when team has no GitHub connection."""


def get_github_client(access_token: str) -> Github:
    """
    Create and return an authenticated GitHub client instance.

    Args:
        access_token: GitHub OAuth access token

    Returns:
        Authenticated Github client instance
    """
    return Github(access_token)


def get_github_client_for_team(team: Team) -> Github:
    """Get GitHub client using best available auth method.

    Priority:
    1. GitHub App installation (preferred for repo/PR access)
    2. OAuth credential (fallback for Copilot or legacy)

    Args:
        team: The team to get a client for

    Returns:
        Authenticated Github client

    Raises:
        NoGitHubConnectionError: If no auth method available
    """
    # Try GitHub App first
    try:
        installation = GitHubAppInstallation.objects.get(team=team, is_active=True)
        return get_installation_client(installation.installation_id)
    except GitHubAppInstallation.DoesNotExist:
        pass

    # Fall back to OAuth
    try:
        credential = IntegrationCredential.objects.get(team=team, provider=IntegrationCredential.PROVIDER_GITHUB)
        return Github(credential.access_token)
    except IntegrationCredential.DoesNotExist:
        pass

    raise NoGitHubConnectionError(f"Team {team.slug} has no GitHub connection")
