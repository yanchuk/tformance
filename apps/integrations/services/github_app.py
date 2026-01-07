"""GitHub App service for handling GitHub App authentication and API access."""

import time
from datetime import datetime

import jwt
from django.conf import settings
from github import Github, GithubException, GithubIntegration


class GitHubAppError(Exception):
    """Exception raised for GitHub App errors."""

    pass


def _get_github_integration() -> GithubIntegration:
    """Create a GithubIntegration instance with app credentials.

    Returns:
        Configured GithubIntegration instance

    Requires settings:
        GITHUB_APP_ID: The GitHub App ID
        GITHUB_APP_PRIVATE_KEY: The GitHub App private key (PEM format)
    """
    return GithubIntegration(
        integration_id=int(settings.GITHUB_APP_ID),
        private_key=settings.GITHUB_APP_PRIVATE_KEY,
    )


def get_jwt() -> str:
    """Generate a JWT for GitHub App authentication.

    Creates a JWT signed with RS256 algorithm using the app's private key.
    The JWT expires in 10 minutes (600 seconds).

    Returns:
        Signed JWT string

    Requires settings:
        GITHUB_APP_ID: The GitHub App ID
        GITHUB_APP_PRIVATE_KEY: The GitHub App private key (PEM format)
    """
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + 600,  # 10 minute expiry
        "iss": settings.GITHUB_APP_ID,
    }
    return jwt.encode(payload, settings.GITHUB_APP_PRIVATE_KEY, algorithm="RS256")


def get_installation_token_with_expiry(installation_id: int) -> tuple[str, datetime]:
    """Get installation token and its expiry datetime.

    Args:
        installation_id: The GitHub App installation ID

    Returns:
        Tuple of (token string, expiry datetime)

    Raises:
        GitHubAppError: If token retrieval fails
    """
    try:
        integration = _get_github_integration()
        token = integration.get_access_token(installation_id)
        return token.token, token.expires_at
    except GithubException as e:
        raise GitHubAppError(f"Failed to get installation token: {e.status} - {e.data}") from e


def get_installation_token(installation_id: int) -> str:
    """Get an installation access token for a GitHub App installation.

    Args:
        installation_id: The GitHub App installation ID

    Returns:
        Installation access token string

    Raises:
        GitHubAppError: If token retrieval fails
    """
    token, _ = get_installation_token_with_expiry(installation_id)
    return token


def get_installation_client(installation_id: int) -> Github:
    """Get an authenticated Github client for an installation.

    Args:
        installation_id: The GitHub App installation ID

    Returns:
        Authenticated Github client instance

    Raises:
        GitHubAppError: If client creation fails
    """
    token = get_installation_token(installation_id)
    return Github(token)


def get_installation(installation_id: int) -> dict:
    """Get details about a GitHub App installation.

    Args:
        installation_id: The GitHub App installation ID

    Returns:
        Dictionary containing installation details

    Raises:
        GitHubAppError: If installation retrieval fails
    """
    try:
        integration = _get_github_integration()
        installation = integration.get_installation(installation_id)
        return {
            "id": installation.id,
            "account": {
                "login": installation.account.login,
                "id": installation.account.id,
                "type": installation.account.type,
            },
            "permissions": installation.permissions,
            "events": installation.events,
            "repository_selection": installation.repository_selection,
        }
    except GithubException as e:
        raise GitHubAppError(f"Failed to get installation: {e.status} - {e.data}") from e


def get_installation_repositories(installation_id: int) -> list[dict]:
    """Get repositories accessible to a GitHub App installation.

    Args:
        installation_id: The GitHub App installation ID

    Returns:
        List of repository dictionaries

    Raises:
        GitHubAppError: If repository retrieval fails
    """
    github = get_installation_client(installation_id)
    installation = github.get_installation(installation_id)
    repos = installation.get_repos()
    return [
        {
            "id": repo.id,
            "full_name": repo.full_name,
            "name": repo.name,
            "private": repo.private,
        }
        for repo in repos
    ]
