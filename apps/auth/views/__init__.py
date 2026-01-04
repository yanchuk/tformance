"""Views for OAuth callbacks.

This package handles OAuth callbacks for GitHub, Jira, and Slack integrations,
routing to appropriate handlers based on flow type (login, onboarding, integration).

All public views are re-exported here for backward compatibility.
"""

# ruff: noqa: F401 - these imports are re-exports for backward compatibility
# Re-export external dependencies used by tests that patch at apps.auth.views.*
from apps.integrations.services import github_oauth, jira_oauth, member_sync, slack_oauth

# Re-export constants
from ._helpers import (
    GITHUB_LOGIN_SCOPES,
    GITHUB_OAUTH_AUTHORIZE_URL,
    JIRA_ONBOARDING_CREDENTIAL_KEY,
    JIRA_ONBOARDING_INTEGRATION_KEY,
    ONBOARDING_ORGS_KEY,
    ONBOARDING_TOKEN_KEY,
    SLACK_ONBOARDING_INTEGRATION_KEY,
)

# Re-export GitHub views
from .github import (
    _create_team_from_org,
    _handle_integration_callback,
    _handle_login_callback,
    _handle_onboarding_callback,
    github_callback,
    github_login,
)

# Re-export Jira views
from .jira import (
    _handle_jira_integration_callback,
    _handle_jira_onboarding_callback,
    jira_callback,
)

# Re-export Slack views
from .slack import (
    _handle_slack_integration_callback,
    _handle_slack_onboarding_callback,
    slack_callback,
)

__all__ = [
    # External services (for test mocking)
    "github_oauth",
    "jira_oauth",
    "slack_oauth",
    "member_sync",
    # Constants
    "ONBOARDING_TOKEN_KEY",
    "ONBOARDING_ORGS_KEY",
    "GITHUB_OAUTH_AUTHORIZE_URL",
    "GITHUB_LOGIN_SCOPES",
    "JIRA_ONBOARDING_CREDENTIAL_KEY",
    "JIRA_ONBOARDING_INTEGRATION_KEY",
    "SLACK_ONBOARDING_INTEGRATION_KEY",
    # GitHub views
    "github_login",
    "github_callback",
    "_handle_login_callback",
    "_handle_onboarding_callback",
    "_create_team_from_org",
    "_handle_integration_callback",
    # Jira views
    "jira_callback",
    "_handle_jira_onboarding_callback",
    "_handle_jira_integration_callback",
    # Slack views
    "slack_callback",
    "_handle_slack_onboarding_callback",
    "_handle_slack_integration_callback",
]
