"""GitHub App service for handling GitHub App authentication and API access."""

import time
from datetime import datetime

import jwt
from django.conf import settings
from github import Github, GithubException, GithubIntegration


class GitHubAppError(Exception):
    """Exception raised for GitHub App errors."""

    pass


def _get_private_key() -> str:
    """Get the GitHub App private key with proper newline handling.

    Handles the case where the private key in .env has escaped newlines (\\n)
    instead of actual newline characters.

    Returns:
        Private key string with proper newlines
    """
    key = settings.GITHUB_APP_PRIVATE_KEY
    # Convert escaped newlines to actual newlines if needed
    if "\\n" in key:
        key = key.replace("\\n", "\n")
    return key


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
        private_key=_get_private_key(),
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
    return jwt.encode(payload, _get_private_key(), algorithm="RS256")


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

    Uses the GitHub REST API directly since PyGithub's GithubIntegration.get_installation()
    has a different signature in 2.x (requires owner, repo instead of installation_id).

    Args:
        installation_id: The GitHub App installation ID

    Returns:
        Dictionary containing installation details

    Raises:
        GitHubAppError: If installation retrieval fails
    """
    import requests

    try:
        # Use JWT to authenticate as the App
        app_jwt = get_jwt()

        # Call GitHub REST API to get installation details
        response = requests.get(
            f"https://api.github.com/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        return {
            "id": data["id"],
            "account": {
                "login": data["account"]["login"],
                "id": data["account"]["id"],
                "type": data["account"]["type"],
            },
            "permissions": data.get("permissions", {}),
            "events": data.get("events", []),
            "repository_selection": data.get("repository_selection", "selected"),
        }
    except requests.RequestException as e:
        raise GitHubAppError(f"Failed to get installation: {e}") from e


def get_installation_repositories(installation_id: int) -> list[dict]:
    """Get repositories accessible to a GitHub App installation.

    Uses the installation token which is already scoped to the repos granted
    to that installation.

    Args:
        installation_id: The GitHub App installation ID

    Returns:
        List of repository dictionaries with id, full_name, name, private, updated_at

    Raises:
        GitHubAppError: If repository retrieval fails
    """

    import requests

    try:
        # Get installation token
        token = get_installation_token(installation_id)

        # Use REST API to list installation repos (handles pagination)
        repos = []
        url = "https://api.github.com/installation/repositories"

        while url:
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                params={"per_page": 100} if "?" not in url else None,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            for repo in data.get("repositories", []):
                # Parse updated_at to datetime if present
                updated_at = None
                if repo.get("updated_at"):
                    from datetime import datetime

                    updated_at = datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))

                repos.append(
                    {
                        "id": repo["id"],
                        "full_name": repo["full_name"],
                        "name": repo["name"],
                        "private": repo["private"],
                        "updated_at": updated_at,
                    }
                )

            # Handle pagination via Link header
            url = None
            if "Link" in response.headers:
                links = response.headers["Link"].split(", ")
                for link in links:
                    if 'rel="next"' in link:
                        url = link[link.index("<") + 1 : link.index(">")]
                        break

        return repos
    except requests.RequestException as e:
        raise GitHubAppError(f"Failed to get installation repositories: {e}") from e
