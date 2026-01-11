"""Shared utilities for onboarding views.

Contains helper functions and constants used across onboarding view modules.
"""

import logging

from apps.integrations.services.integration_flags import is_integration_enabled

logger = logging.getLogger(__name__)

# Session keys for onboarding state
ONBOARDING_TOKEN_KEY = "onboarding_github_token"
ONBOARDING_ORGS_KEY = "onboarding_github_orgs"
ONBOARDING_SELECTED_ORG_KEY = "onboarding_selected_org"


def _get_onboarding_flags_context(request) -> dict:
    """Get feature flag context for onboarding templates.

    Returns dict with integration flags for conditional stepper rendering.
    Used by A-002: Hide Jira/Slack/Copilot steps when flags are disabled.
    """
    return {
        "jira_enabled": is_integration_enabled(request, "jira"),
        "slack_enabled": is_integration_enabled(request, "slack"),
        "copilot_enabled": is_integration_enabled(request, "copilot"),
    }
