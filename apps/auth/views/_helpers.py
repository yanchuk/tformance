"""Shared helpers and constants for OAuth callback views.

Contains session keys, constants, and error redirect functions used
across GitHub, Jira, and Slack OAuth handlers.
"""

from django.shortcuts import redirect

from apps.auth.oauth_state import (
    FLOW_TYPE_INTEGRATION,
    FLOW_TYPE_JIRA_INTEGRATION,
    FLOW_TYPE_JIRA_ONBOARDING,
    FLOW_TYPE_LOGIN,
    FLOW_TYPE_ONBOARDING,
    FLOW_TYPE_SLACK_INTEGRATION,
    FLOW_TYPE_SLACK_ONBOARDING,
)

# Session keys for onboarding state (matching onboarding app)
ONBOARDING_TOKEN_KEY = "onboarding_github_token"
ONBOARDING_ORGS_KEY = "onboarding_github_orgs"

# GitHub OAuth constants for login flow (minimal scopes)
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_LOGIN_SCOPES = "user:email"

# Session keys for Jira onboarding
JIRA_ONBOARDING_CREDENTIAL_KEY = "jira_onboarding_credential_id"
JIRA_ONBOARDING_INTEGRATION_KEY = "jira_onboarding_integration_id"

# Session keys for Slack onboarding
SLACK_ONBOARDING_INTEGRATION_KEY = "slack_onboarding_integration_id"


def get_github_error_redirect(state_data: dict):
    """Get appropriate error redirect based on GitHub flow type."""
    flow_type = state_data.get("type")
    if flow_type == FLOW_TYPE_LOGIN:
        return redirect("account_login")
    elif flow_type == FLOW_TYPE_ONBOARDING:
        return redirect("onboarding:start")
    elif flow_type == FLOW_TYPE_INTEGRATION:
        return redirect("integrations:integrations_home")
    return redirect("web:home")


def get_jira_error_redirect(state_data: dict):
    """Get appropriate error redirect based on Jira flow type."""
    flow_type = state_data.get("type")
    if flow_type == FLOW_TYPE_JIRA_ONBOARDING:
        return redirect("onboarding:connect_jira")
    elif flow_type == FLOW_TYPE_JIRA_INTEGRATION:
        return redirect("integrations:integrations_home")
    return redirect("web:home")


def get_slack_error_redirect(state_data: dict):
    """Get appropriate error redirect based on Slack flow type."""
    flow_type = state_data.get("type")
    if flow_type == FLOW_TYPE_SLACK_ONBOARDING:
        return redirect("onboarding:connect_slack")
    elif flow_type == FLOW_TYPE_SLACK_INTEGRATION:
        return redirect("integrations:integrations_home")
    return redirect("web:home")
