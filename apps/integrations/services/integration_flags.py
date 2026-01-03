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

# Mapping of integration slugs to flag names
INTEGRATION_FLAGS = {
    "jira": FLAG_JIRA,
    "copilot": FLAG_COPILOT,
    "slack": FLAG_SLACK,
    "google_workspace": FLAG_GOOGLE_WORKSPACE,
}

# Integration metadata for UI rendering
INTEGRATION_METADATA = {
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
        "description": "PR surveys and leaderboards",
        "benefits": [
            {
                "title": "PR surveys via DM",
                "description": "Quick 1-click surveys to capture AI-assisted PRs",
            },
            {
                "title": "Weekly leaderboards",
                "description": "Gamified AI Detective rankings",
            },
            {
                "title": "Higher response rates",
                "description": "Meet developers where they work",
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
    Jira and Slack are the optional steps controlled by flags.

    Args:
        request: The HTTP request object

    Returns:
        List of enabled step names (e.g., ["jira", "slack"])
    """
    steps = []

    if is_integration_enabled(request, "jira"):
        steps.append("jira")

    if is_integration_enabled(request, "slack"):
        steps.append("slack")

    return steps


def get_next_onboarding_step(request: HttpRequest, current_step: str) -> str:
    """Get the next onboarding step based on current step and enabled flags.

    Flow: sync_progress → [jira if enabled] → [slack if enabled] → complete

    Args:
        request: The HTTP request object
        current_step: The current step name

    Returns:
        The next step name
    """
    enabled_steps = get_enabled_onboarding_steps(request)

    if current_step == "sync_progress":
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
