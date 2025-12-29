"""GitHub OAuth service for handling OAuth flow."""

import base64
import json
import time
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.signing import BadSignature, Signer
from github import Github, GithubException, UnknownObjectException

# OAuth state validity period in seconds (10 minutes)
OAUTH_STATE_MAX_AGE_SECONDS = 600

# GitHub API constants
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "application/vnd.github.v3+json"

# OAuth scopes required for GitHub integration
# read:org - Access organization membership and teams
# repo - Access repositories (code, PRs, commits)
# read:user - Access user profile information
# user:email - Access user email addresses (including private emails)
# manage_billing:copilot - Access GitHub Copilot usage metrics
GITHUB_OAUTH_SCOPES = " ".join(
    [
        "read:org",
        "repo",
        "read:user",
        "user:email",
        "manage_billing:copilot",
    ]
)


class GitHubOAuthError(Exception):
    """Exception raised for GitHub OAuth errors."""

    pass


def create_oauth_state(team_id: int) -> str:
    """Create a signed OAuth state parameter containing team_id and timestamp.

    Args:
        team_id: The ID of the team to encode in the state

    Returns:
        Signed state string containing the team_id and iat (issued at) timestamp
    """
    # Create JSON payload with issued-at timestamp
    payload = json.dumps({"team_id": team_id, "iat": int(time.time())})

    # Base64 encode
    encoded = base64.b64encode(payload.encode()).decode()

    # Sign with Django's Signer
    signer = Signer()
    signed_state = signer.sign(encoded)

    return signed_state


def verify_oauth_state(state: str) -> dict[str, Any]:
    """Verify and decode OAuth state parameter.

    Validates:
    - Signature is valid (not tampered)
    - Timestamp is present and not expired (max 10 minutes)

    Args:
        state: The signed state string to verify

    Returns:
        Dictionary containing team_id

    Raises:
        GitHubOAuthError: If state is invalid, tampered with, or expired
    """
    try:
        # Unsign the state
        signer = Signer()
        unsigned = signer.unsign(state)

        # Base64 decode
        decoded = base64.b64decode(unsigned).decode()

        # Parse JSON
        payload = json.loads(decoded)

        # Validate timestamp (if present - for backward compatibility)
        iat = payload.get("iat")
        if iat is not None:
            age = int(time.time()) - iat
            if age > OAUTH_STATE_MAX_AGE_SECONDS:
                raise GitHubOAuthError(f"OAuth state expired (age: {age}s, max: {OAUTH_STATE_MAX_AGE_SECONDS}s)")
            if age < 0:
                raise GitHubOAuthError("OAuth state has future timestamp")

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
        response = requests.post(GITHUB_OAUTH_TOKEN_URL, json=payload, headers=headers, timeout=30)

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
        Dictionary containing user data (login, id, email, name, avatar_url)

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create Github client with access token
        github = Github(access_token)

        # Get authenticated user
        user = github.get_user()

        # Convert PyGithub User object to dict
        return {
            "login": user.login,
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
        }
    except GithubException as e:
        raise GitHubOAuthError(f"Failed to get authenticated user: {e.status} - {e.data}") from e


# Alias for backward compatibility and cleaner API
get_github_user = get_authenticated_user


def get_user_organizations(access_token: str) -> list[dict[str, Any]]:
    """Get user's GitHub organizations.

    Args:
        access_token: The GitHub access token

    Returns:
        List of organization dictionaries

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create Github client with access token
        github = Github(access_token)

        # Get authenticated user and their organizations
        user = github.get_user()
        orgs = user.get_orgs()

        # Convert each PyGithub Organization object to dict
        return [
            {
                "login": org.login,
                "id": org.id,
                "description": org.description,
                "avatar_url": org.avatar_url,
            }
            for org in orgs
        ]
    except GithubException as e:
        raise GitHubOAuthError(f"Failed to get user organizations: {e.status} - {e.data}") from e


def get_organization_members(access_token: str, org_slug: str) -> list[dict[str, Any]]:
    """Get members of a GitHub organization.

    Handles pagination automatically via PyGithub's PaginatedList.

    Args:
        access_token: The GitHub access token
        org_slug: The organization slug/login

    Returns:
        List of member dictionaries with keys: id, login, avatar_url, type

    Raises:
        GitHubOAuthError: If API request fails or organization not found
    """
    try:
        # Create Github client with access token
        github = Github(access_token)

        # Get organization by slug
        org = github.get_organization(org_slug)

        # Get members - returns PaginatedList
        members = org.get_members()

        # Convert each PyGithub NamedUser object to dict
        return [
            {
                "id": member.id,
                "login": member.login,
                "avatar_url": member.avatar_url,
                "type": member.type,
            }
            for member in members
        ]
    except UnknownObjectException as e:
        raise GitHubOAuthError(f"Organization not found: {e.status} - {e.data}") from e
    except GithubException as e:
        raise GitHubOAuthError(f"Failed to get organization members: {e.status} - {e.data}") from e


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
    try:
        # Create Github client with access token
        github = Github(access_token)

        # Get specific user by username
        user = github.get_user(username)

        # Convert PyGithub User object to dict
        return {
            "login": user.login,
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "company": user.company,
            "location": user.location,
        }
    except UnknownObjectException as e:
        raise GitHubOAuthError(f"User not found: {e.status} - {e.data}") from e
    except GithubException as e:
        raise GitHubOAuthError(f"Failed to get user details: {e.status} - {e.data}") from e


def get_organization_repositories(
    access_token: str, org_slug: str, exclude_archived: bool = False
) -> list[dict[str, Any]]:
    """Get repositories of a GitHub organization.

    Handles pagination automatically via PyGithub's PaginatedList.

    Args:
        access_token: The GitHub access token
        org_slug: The organization slug/login
        exclude_archived: If True, filter out archived repositories

    Returns:
        List of repository dictionaries with keys: id, full_name, name, description,
        language, private, updated_at, archived, default_branch

    Raises:
        GitHubOAuthError: If API request fails or organization not found
    """
    try:
        # Create Github client with access token
        github = Github(access_token)

        # Get organization by slug
        org = github.get_organization(org_slug)

        # Get repos - returns PaginatedList
        repos = org.get_repos()

        # Convert each PyGithub Repository object to dict
        repo_list = [
            {
                "id": repo.id,
                "full_name": repo.full_name,
                "name": repo.name,
                "description": repo.description,
                "language": repo.language,
                "private": repo.private,
                "updated_at": repo.updated_at,
                "archived": repo.archived,
                "default_branch": repo.default_branch,
            }
            for repo in repos
        ]

        # Apply archived filter if requested
        if exclude_archived:
            repo_list = [repo for repo in repo_list if not repo["archived"]]

        return repo_list
    except UnknownObjectException as e:
        raise GitHubOAuthError(f"Organization not found: {e.status} - {e.data}") from e
    except GithubException as e:
        raise GitHubOAuthError(f"Failed to get organization repositories: {e.status} - {e.data}") from e


def get_user_primary_email(access_token: str) -> str | None:
    """Get user's primary verified email from GitHub.

    Calls /user/emails endpoint to fetch all emails including private ones.
    Returns the primary verified email, or first verified email as fallback.

    Args:
        access_token: GitHub access token with user:email scope

    Returns:
        Primary verified email address or None if unavailable

    Raises:
        GitHubOAuthError: If API request fails
    """
    try:
        # Create Github client with access token
        github = Github(access_token)

        # Get authenticated user
        user = github.get_user()

        # Get emails - returns list of email objects
        emails = user.get_emails()

        # Find primary + verified email first
        for email in emails:
            if email.primary and email.verified:
                return email.email

        # Fall back to first verified email
        for email in emails:
            if email.verified:
                return email.email

        # No verified emails found
        return None
    except GithubException as e:
        raise GitHubOAuthError(f"Failed to get user emails: {e.status} - {e.data}") from e
