"""Jira OAuth service for handling OAuth flow."""

import base64
import json
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.signing import BadSignature, Signer
from django.utils import timezone

# Note: encrypt/decrypt no longer needed - EncryptedTextField handles this automatically

# Jira OAuth constants
JIRA_AUTH_URL = "https://auth.atlassian.com/authorize"
JIRA_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
JIRA_API_BASE_URL = "https://api.atlassian.com"
JIRA_ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
JIRA_OAUTH_SCOPES = "read:jira-work read:jira-user offline_access"

# Token refresh buffer time - refresh tokens that expire within this timeframe
TOKEN_REFRESH_BUFFER = timedelta(minutes=5)


class JiraOAuthError(Exception):
    """Exception raised for Jira OAuth errors."""

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
        JiraOAuthError: If state is invalid or tampered with
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
        raise JiraOAuthError(f"Invalid OAuth state: {str(e)}") from e


def get_authorization_url(team_id: int, redirect_uri: str) -> str:
    """Generate Jira OAuth authorization URL.

    Args:
        team_id: The ID of the team initiating OAuth
        redirect_uri: The callback URL for OAuth redirect

    Returns:
        Complete Jira authorization URL with all parameters
    """
    # Create state parameter
    state = create_oauth_state(team_id)

    # Build URL parameters
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.JIRA_CLIENT_ID,
        "scope": JIRA_OAUTH_SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }

    # Build full URL
    url = f"{JIRA_AUTH_URL}?{urlencode(params)}"

    return url


def _make_token_request(payload: dict[str, str], error_context: str) -> dict[str, Any]:
    """Make a POST request to Jira token endpoint with error handling.

    Args:
        payload: The request payload
        error_context: Context string for error messages (e.g., "Token exchange", "Token refresh")

    Returns:
        Dictionary containing token response data

    Raises:
        JiraOAuthError: If the request fails
    """
    headers = {"Accept": "application/json"}

    try:
        response = requests.post(JIRA_TOKEN_URL, json=payload, headers=headers, timeout=30)

        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get("error", "Unknown error")
            raise JiraOAuthError(f"{error_context} failed: {error_msg}")

        return response.json()
    except Exception as e:
        if isinstance(e, JiraOAuthError):
            raise
        raise JiraOAuthError(f"{error_context} failed: {str(e)}") from e


def exchange_code_for_token(code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchange OAuth code for access token.

    Args:
        code: The authorization code from Jira
        redirect_uri: The redirect URI used in authorization

    Returns:
        Dictionary containing access_token, refresh_token, and other token data

    Raises:
        JiraOAuthError: If token exchange fails
    """
    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.JIRA_CLIENT_ID,
        "client_secret": settings.JIRA_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    return _make_token_request(payload, "Token exchange")


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh Jira access token using refresh token.

    Args:
        refresh_token: The refresh token

    Returns:
        Dictionary containing new access_token, refresh_token, and other token data

    Raises:
        JiraOAuthError: If token refresh fails
    """
    payload = {
        "grant_type": "refresh_token",
        "client_id": settings.JIRA_CLIENT_ID,
        "client_secret": settings.JIRA_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }

    return _make_token_request(payload, "Token refresh")


def get_accessible_resources(access_token: str) -> list[dict[str, Any]]:
    """Get accessible Jira resources/sites for the authenticated user.

    Args:
        access_token: The Jira access token

    Returns:
        List of accessible site dictionaries with keys: id, name, url, scopes, avatarUrl

    Raises:
        JiraOAuthError: If API request fails
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(JIRA_ACCESSIBLE_RESOURCES_URL, headers=headers, timeout=30)

        if response.status_code != 200:
            raise JiraOAuthError(f"Failed to get accessible resources: {response.status_code}")

        return response.json()
    except Exception as e:
        if isinstance(e, JiraOAuthError):
            raise
        raise JiraOAuthError(f"Failed to get accessible resources: {str(e)}") from e


def ensure_valid_jira_token(credential: "IntegrationCredential") -> str:  # noqa: F821
    """Ensure Jira token is valid, refreshing if needed.

    Args:
        credential: IntegrationCredential instance

    Returns:
        Decrypted access token

    Raises:
        JiraOAuthError: If token refresh fails
    """
    # Check if token needs refresh (expired or expiring within buffer time)
    now = timezone.now()
    needs_refresh = credential.token_expires_at is None or credential.token_expires_at <= now + TOKEN_REFRESH_BUFFER

    if not needs_refresh:
        # Token is valid, EncryptedTextField auto-decrypts
        return credential.access_token

    # Refresh the token (EncryptedTextField auto-decrypts refresh_token)
    token_data = refresh_access_token(credential.refresh_token)

    # Update credential with new tokens (EncryptedTextField auto-encrypts on save)
    credential.access_token = token_data["access_token"]
    credential.refresh_token = token_data["refresh_token"]
    credential.token_expires_at = now + timedelta(seconds=token_data["expires_in"])
    credential.save(update_fields=["access_token", "refresh_token", "token_expires_at"])

    return token_data["access_token"]
