"""GitHub OAuth service for handling OAuth flow."""

import base64
import json
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.signing import BadSignature, Signer

# GitHub API constants
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "application/vnd.github.v3+json"
GITHUB_OAUTH_SCOPES = "read:org repo read:user"


class GitHubOAuthError(Exception):
    """Exception raised for GitHub OAuth errors."""

    pass


def create_oauth_state(team_id: int) -> str:
    """Create a signed OAuth state parameter containing team_id.

    Args:
        team_id: The ID of the team to encode in the state

    Returns:
        Signed state string containing the team_id
    """
    # Create JSON payload
    payload = json.dumps({"team_id": team_id})

    # Base64 encode
    encoded = base64.b64encode(payload.encode()).decode()

    # Sign with Django's Signer
    signer = Signer()
    signed_state = signer.sign(encoded)

    return signed_state


def verify_oauth_state(state: str) -> dict[str, Any]:
    """Verify and decode OAuth state parameter.

    Args:
        state: The signed state string to verify

    Returns:
        Dictionary containing team_id

    Raises:
        GitHubOAuthError: If state is invalid or tampered with
    """
    try:
        # Unsign the state
        signer = Signer()
        unsigned = signer.unsign(state)

        # Base64 decode
        decoded = base64.b64decode(unsigned).decode()

        # Parse JSON
        payload = json.loads(decoded)

        return payload
    except (BadSignature, ValueError, KeyError) as e:
        raise GitHubOAuthError(f"Invalid OAuth state: {str(e)}") from e


def get_authorization_url(team_id: int, redirect_uri: str) -> str:
    """Generate GitHub OAuth authorization URL.

    Args:
        team_id: The ID of the team initiating OAuth
        redirect_uri: The callback URL for OAuth redirect

    Returns:
        Complete GitHub authorization URL with all parameters
    """
    # Create state parameter
    state = create_oauth_state(team_id)

    # Build URL parameters
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": GITHUB_OAUTH_SCOPES,
        "state": state,
    }

    # Build full URL
    url = f"{GITHUB_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    return url


def _make_github_api_request(endpoint: str, access_token: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Make an authenticated request to GitHub API.

    Args:
        endpoint: The API endpoint path (e.g., '/user', '/user/orgs')
        access_token: The GitHub access token

    Returns:
        JSON response data (dict or list)

    Raises:
        GitHubOAuthError: If API request fails
    """
    url = f"{GITHUB_API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": GITHUB_API_VERSION,
    }

    try:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise GitHubOAuthError(f"GitHub API error: {response.status_code}")

        return response.json()
    except Exception as e:
        if isinstance(e, GitHubOAuthError):
            raise
        raise GitHubOAuthError(f"Failed to make GitHub API request to {endpoint}: {str(e)}") from e


def exchange_code_for_token(code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchange OAuth code for access token.

    Args:
        code: The authorization code from GitHub
        redirect_uri: The redirect URI used in authorization

    Returns:
        Dictionary containing access_token and other token data

    Raises:
        GitHubOAuthError: If token exchange fails
    """
    payload = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_SECRET_ID,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    headers = {"Accept": "application/json"}

    try:
        response = requests.post(GITHUB_OAUTH_TOKEN_URL, json=payload, headers=headers)

        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get("error", "Unknown error")
            raise GitHubOAuthError(f"Token exchange failed: {error_msg}")

        return response.json()
    except Exception as e:
        if isinstance(e, GitHubOAuthError):
            raise
        raise GitHubOAuthError(f"Token exchange failed: {str(e)}") from e


def get_authenticated_user(access_token: str) -> dict[str, Any]:
    """Get authenticated user data from GitHub API.

    Args:
        access_token: The GitHub access token

    Returns:
        Dictionary containing user data

    Raises:
        GitHubOAuthError: If API request fails
    """
    return _make_github_api_request("/user", access_token)


def get_user_organizations(access_token: str) -> list[dict[str, Any]]:
    """Get user's GitHub organizations.

    Args:
        access_token: The GitHub access token

    Returns:
        List of organization dictionaries

    Raises:
        GitHubOAuthError: If API request fails
    """
    return _make_github_api_request("/user/orgs", access_token)


def _make_paginated_github_api_request(endpoint: str, access_token: str) -> list[dict[str, Any]]:
    """Make an authenticated paginated request to GitHub API.

    Automatically fetches all pages by following the 'next' link in the Link header.

    Args:
        endpoint: The API endpoint path (e.g., '/orgs/{org}/members')
        access_token: The GitHub access token

    Returns:
        List of all items from all pages combined

    Raises:
        GitHubOAuthError: If API request fails
    """
    all_items = []
    url = f"{GITHUB_API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": GITHUB_API_VERSION,
    }

    try:
        while url:
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                raise GitHubOAuthError(f"GitHub API error: {response.status_code}")

            # Add items from this page
            all_items.extend(response.json())

            # Check for next page in Link header
            link_header = response.headers.get("Link", "")
            url = _parse_next_link(link_header)

        return all_items
    except Exception as e:
        if isinstance(e, GitHubOAuthError):
            raise
        raise GitHubOAuthError(f"Failed to make paginated GitHub API request to {endpoint}: {str(e)}") from e


def get_organization_members(access_token: str, org_slug: str) -> list[dict[str, Any]]:
    """Get members of a GitHub organization.

    Handles pagination by following the 'next' link in the Link header.

    Args:
        access_token: The GitHub access token
        org_slug: The organization slug/login

    Returns:
        List of member dictionaries from all pages

    Raises:
        GitHubOAuthError: If API request fails
    """
    return _make_paginated_github_api_request(f"/orgs/{org_slug}/members", access_token)


def _parse_next_link(link_header: str) -> str | None:
    """Parse the Link header to extract the 'next' URL.

    Args:
        link_header: The Link header string from GitHub API response

    Returns:
        The next URL if it exists, None otherwise
    """
    if not link_header:
        return None

    # Link header format: '<url>; rel="next", <url>; rel="last"'
    links = link_header.split(",")
    for link in links:
        parts = link.strip().split(";")
        if len(parts) >= 2:
            url = parts[0].strip()[1:-1]  # Remove < and >
            rel = parts[1].strip()
            if 'rel="next"' in rel:
                return url

    return None


def get_user_details(access_token: str, username: str) -> dict[str, Any]:
    """Get detailed information about a specific GitHub user.

    Args:
        access_token: The GitHub access token
        username: The GitHub username to fetch details for

    Returns:
        Dictionary containing user data (id, login, name, email, avatar_url, etc.)

    Raises:
        GitHubOAuthError: If API request fails
    """
    return _make_github_api_request(f"/users/{username}", access_token)


def get_organization_repositories(
    access_token: str, org_slug: str, exclude_archived: bool = False
) -> list[dict[str, Any]]:
    """Get repositories of a GitHub organization.

    Handles pagination by following the 'next' link in the Link header.

    Args:
        access_token: The GitHub access token
        org_slug: The organization slug/login
        exclude_archived: If True, filter out archived repositories

    Returns:
        List of repository dictionaries from all pages

    Raises:
        GitHubOAuthError: If API request fails
    """
    repos = _make_paginated_github_api_request(f"/orgs/{org_slug}/repos", access_token)

    if exclude_archived:
        repos = [repo for repo in repos if not repo.get("archived", False)]

    return repos
