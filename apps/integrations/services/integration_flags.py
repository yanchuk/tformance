"""Integration feature flag helpers.

Provides functions to check if integrations are enabled via feature flags
and get integration status information for UI rendering.
"""

from dataclasses import dataclass

import waffle
from django.http import HttpRequest

# Flag names for each integration
FLAG_JIRA = "integration_jira_enabled"
FLAG_COPILOT = "integration_copilot_enabled"
FLAG_SLACK = "integration_slack_enabled"
FLAG_GOOGLE_WORKSPACE = "integration_google_workspace_enabled"

# Global feature flags
FLAG_CICD = "cicd_enabled"

# Copilot feature flags - hierarchical structure
# Master flag controls all Copilot features, sub-flags control individual features
COPILOT_FEATURE_FLAGS = {
    "copilot_enabled": "copilot_enabled",  # Master switch
    "copilot_seat_utilization": "copilot_seat_utilization",  # ROI & seat analytics
    "copilot_language_insights": "copilot_language_insights",  # Language/editor breakdown
    "copilot_delivery_impact": "copilot_delivery_impact",  # PR comparison metrics
    "copilot_llm_insights": "copilot_llm_insights",  # Include Copilot in LLM prompts
}

# Mapping of integration slugs to flag names
INTEGRATION_FLAGS = {
    "jira": FLAG_JIRA,
    "copilot": FLAG_COPILOT,
    "slack": FLAG_SLACK,
    "google_workspace": FLAG_GOOGLE_WORKSPACE,
}

# Integration metadata for UI rendering
INTEGRATION_METADATA = {
    "github": {
        "name": "GitHub",
        "icon_color": "text-base-content",
        "description": "Pull requests, commits, and reviews",
        "benefits": [
            {
                "title": "Privacy first",
                "description": "We never read or store your source code",
            },
            {
                "title": "Metadata only",
                "description": "We analyze PR metadata, not code content",
            },
            {
                "title": "Read-only access",
                "description": "We can't modify your repositories",
            },
        ],
        "always_coming_soon": False,
    },
    "jira": {
        "name": "Jira",
        "icon_color": "text-blue-500",
        "description": "Issues and sprint tracking",
        "benefits": [
            {
                "title": "Sprint velocity",
                "description": "Track story points delivered per sprint",
            },
            {
                "title": "Issue cycle time",
                "description": "Measure time from start to done",
            },
            {
                "title": "PR-to-issue linking",
                "description": "Connect code changes to business outcomes",
            },
        ],
        "always_coming_soon": False,
    },
    "copilot": {
        "name": "GitHub Copilot",
        "icon_color": "text-violet-500",
        "description": "AI coding assistant metrics",
        "benefits": [
            {
                "title": "Acceptance rate",
                "description": "Track how often suggestions are accepted",
            },
            {
                "title": "Lines of code",
                "description": "Measure AI-generated code volume",
            },
            {
                "title": "Time savings",
                "description": "Estimate productivity gains from AI",
            },
        ],
        "always_coming_soon": False,
    },
    "slack": {
        "name": "Slack",
        "icon_color": "text-pink-500",
        "description": "Communication analytics and surveys",
        "benefits": [
            {
                "title": "Communication insights",
                "description": "Track time spent on chats and huddles",
            },
            {
                "title": "Team effectiveness",
                "description": "Correlate communication with delivery metrics",
            },
            {
                "title": "PR surveys via DM",
                "description": "Quick 1-click surveys in Slack",
            },
        ],
        "always_coming_soon": False,
    },
    "google_workspace": {
        "name": "Google Workspace",
        "icon_color": "text-green-500",
        "description": "Track communication workload in calendars",
        "benefits": [
            {
                "title": "Meeting time analysis",
                "description": "Track time spent in meetings vs coding",
            },
            {
                "title": "Focus time patterns",
                "description": "Identify optimal deep work windows",
            },
            {
                "title": "Team availability",
                "description": "Optimize collaboration windows",
            },
        ],
        "always_coming_soon": True,  # Always shows Coming Soon
    },
}


@dataclass
class IntegrationStatus:
    """Status and metadata for an integration."""

    name: str
    slug: str
    enabled: bool
    coming_soon: bool
    icon_color: str
    description: str
    benefits: list[dict]


def is_integration_enabled(request: HttpRequest, integration_slug: str) -> bool:
    """Check if an integration is enabled via feature flag.

    Args:
        request: The HTTP request object (used for flag evaluation)
        integration_slug: The integration identifier (jira, copilot, slack, google_workspace)

    Returns:
        True if the integration is enabled, False otherwise
    """
    flag_name = INTEGRATION_FLAGS.get(integration_slug)
    if not flag_name:
        return False

    # Google Workspace is always disabled (coming soon)
    metadata = INTEGRATION_METADATA.get(integration_slug, {})
    if metadata.get("always_coming_soon"):
        return False

    return waffle.flag_is_active(request, flag_name)


def get_integration_status(request: HttpRequest, integration_slug: str) -> IntegrationStatus:
    """Get the status and metadata for a single integration.

    Args:
        request: The HTTP request object
        integration_slug: The integration identifier

    Returns:
        IntegrationStatus dataclass with all integration info
    """
    metadata = INTEGRATION_METADATA.get(integration_slug, {})
    enabled = is_integration_enabled(request, integration_slug)
    always_coming_soon = metadata.get("always_coming_soon", False)

    # Show as coming soon if disabled OR if always_coming_soon
    coming_soon = not enabled or always_coming_soon

    return IntegrationStatus(
        name=metadata.get("name", integration_slug.title()),
        slug=integration_slug,
        enabled=enabled,
        coming_soon=coming_soon,
        icon_color=metadata.get("icon_color", "text-gray-500"),
        description=metadata.get("description", ""),
        benefits=metadata.get("benefits", []),
    )


def get_all_integration_statuses(request: HttpRequest) -> list[IntegrationStatus]:
    """Get status for all integrations.

    Args:
        request: The HTTP request object

    Returns:
        List of IntegrationStatus for all integrations
    """
    return [get_integration_status(request, slug) for slug in INTEGRATION_METADATA]


def get_enabled_onboarding_steps(request: HttpRequest) -> list[str]:
    """Get list of enabled optional onboarding steps.

    Only returns steps that have their feature flag enabled.
    Copilot, Jira, and Slack are optional steps controlled by flags.

    Flow order: copilot → jira → slack (all optional)

    Args:
        request: The HTTP request object

    Returns:
        List of enabled step names (e.g., ["copilot", "jira", "slack"])
    """
    steps = []

    if is_integration_enabled(request, "copilot"):
        steps.append("copilot")

    if is_integration_enabled(request, "jira"):
        steps.append("jira")

    if is_integration_enabled(request, "slack"):
        steps.append("slack")

    return steps


def get_next_onboarding_step(request: HttpRequest, current_step: str) -> str:
    """Get the next onboarding step based on current step and enabled flags.

    Flow: sync_progress → [copilot if enabled] → [jira if enabled] → [slack if enabled] → complete

    Args:
        request: The HTTP request object
        current_step: The current step name

    Returns:
        The next step name
    """
    enabled_steps = get_enabled_onboarding_steps(request)

    if current_step == "sync_progress":
        if "copilot" in enabled_steps:
            return "copilot"
        elif "jira" in enabled_steps:
            return "jira"
        elif "slack" in enabled_steps:
            return "slack"
        else:
            return "complete"

    if current_step == "copilot":
        if "jira" in enabled_steps:
            return "jira"
        elif "slack" in enabled_steps:
            return "slack"
        else:
            return "complete"

    if current_step == "jira":
        if "slack" in enabled_steps:
            return "slack"
        else:
            return "complete"

    if current_step == "slack":
        return "complete"

    # Default to complete for unknown steps
    return "complete"


def is_cicd_enabled(request: HttpRequest) -> bool:
    """Check if CI/CD features are enabled via feature flag.

    Args:
        request: The HTTP request object (used for flag evaluation)

    Returns:
        True if CI/CD features should be shown, False otherwise
    """
    return waffle.flag_is_active(request, FLAG_CICD)


def is_copilot_feature_active(request: HttpRequest, flag_name: str) -> bool:
    """Check if a Copilot feature flag is active.

    Implements hierarchical flag checking - the master flag (copilot_enabled)
    must be active for any sub-flag to be considered active.

    Args:
        request: The HTTP request object (used for flag evaluation)
        flag_name: The Copilot feature flag name (from COPILOT_FEATURE_FLAGS)

    Returns:
        True if the feature is enabled, False otherwise
    """
    # Validate flag name exists
    if flag_name not in COPILOT_FEATURE_FLAGS:
        return False

    # For master flag, just check it directly
    if flag_name == "copilot_enabled":
        return waffle.flag_is_active(request, COPILOT_FEATURE_FLAGS["copilot_enabled"])

    # For sub-flags, check master first
    if not waffle.flag_is_active(request, COPILOT_FEATURE_FLAGS["copilot_enabled"]):
        return False

    # Then check the specific sub-flag
    return waffle.flag_is_active(request, COPILOT_FEATURE_FLAGS[flag_name])
