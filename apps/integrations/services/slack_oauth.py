"""Slack OAuth service for handling OAuth flow."""

from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings

from apps.integrations.services.oauth_utils import create_oauth_state, verify_oauth_state

# Slack OAuth constants
SLACK_OAUTH_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_OAUTH_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
SLACK_OAUTH_SCOPES = "chat:write users:read users:read.email"


class SlackOAuthError(Exception):
    """Exception raised for Slack OAuth errors."""

    pass


def verify_slack_oauth_state(state: str) -> dict[str, Any]:
    """Verify and decode OAuth state parameter for Slack.

    Wrapper around shared verify_oauth_state that raises SlackOAuthError.

    Args:
        state: The signed state string to verify

    Returns:
        Dictionary containing team_id

    Raises:
        SlackOAuthError: If state is invalid or tampered with
    """
    try:
        return verify_oauth_state(state)
    except ValueError as e:
        raise SlackOAuthError(str(e)) from e


def get_authorization_url(team_id: int, redirect_uri: str) -> str:
    """Generate Slack OAuth authorization URL.

    Args:
        team_id: The ID of the team initiating OAuth
        redirect_uri: The callback URL for OAuth redirect

    Returns:
        Complete Slack authorization URL with all parameters
    """
    # Create state parameter
    state = create_oauth_state(team_id)

    # Build URL parameters
    params = {
        "client_id": settings.SLACK_CLIENT_ID,
        "scope": SLACK_OAUTH_SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
    }

    # Build full URL
    url = f"{SLACK_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    return url


def exchange_code_for_token(code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchange OAuth code for access token.

    Args:
        code: The authorization code from Slack
        redirect_uri: The redirect URI used in authorization

    Returns:
        Dictionary containing access_token, bot_user_id, and team info

    Raises:
        SlackOAuthError: If token exchange fails
    """
    payload = {
        "client_id": settings.SLACK_CLIENT_ID,
        "client_secret": settings.SLACK_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    try:
        response = requests.post(SLACK_OAUTH_TOKEN_URL, data=payload, timeout=30)
        data = response.json()

        if not data.get("ok"):
            error = data.get("error", "Unknown error")
            raise SlackOAuthError(f"Token exchange failed: {error}")

        return {
            "access_token": data["access_token"],
            "bot_user_id": data["bot_user_id"],
            "team": {
                "id": data["team"]["id"],
                "name": data["team"]["name"],
            },
        }
    except Exception as e:
        if isinstance(e, SlackOAuthError):
            raise
        raise SlackOAuthError(f"Token exchange failed: {str(e)}") from e
