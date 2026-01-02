"""PostHog analytics wrapper functions.

Provides safe wrappers around PostHog SDK calls that handle errors gracefully
and provide consistent behavior when PostHog is unavailable or unconfigured.
"""

import logging

from django.conf import settings

try:
    import posthog
except ImportError:
    posthog = None

logger = logging.getLogger(__name__)


def _is_posthog_configured() -> bool:
    """Check if PostHog is configured with an API key."""
    return bool(getattr(settings, "POSTHOG_API_KEY", None))


def track_event(user, event: str, properties: dict | None = None) -> None:
    """Track an event via posthog.capture.

    Args:
        user: The user performing the action (can be None for anonymous events).
        event: The name of the event to track.
        properties: Optional dictionary of event properties.
    """
    if user is None:
        return

    if not _is_posthog_configured():
        return

    try:
        props = dict(properties) if properties else {}

        # Auto-add team context if user has a team membership
        if hasattr(user, "membership_set"):
            membership = user.membership_set.first()
            if membership and membership.team:
                props["team_id"] = str(membership.team.id)

        posthog.capture(
            distinct_id=str(user.id),
            event=event,
            properties=props,
        )
    except Exception:
        logger.exception("Failed to track event: %s", event)


def identify_user(user, properties: dict | None = None) -> None:
    """Identify a user via posthog.identify.

    Args:
        user: The user to identify (can be None).
        properties: Optional dictionary of user properties.
    """
    if user is None:
        return

    if not _is_posthog_configured():
        return

    try:
        props = dict(properties) if properties else {}

        # Include default user properties
        if hasattr(user, "email") and user.email:
            props.setdefault("email", user.email)
        if hasattr(user, "first_name") and user.first_name:
            props.setdefault("first_name", user.first_name)
        if hasattr(user, "last_name") and user.last_name:
            props.setdefault("last_name", user.last_name)

        posthog.identify(
            distinct_id=str(user.id),
            properties=props,
        )
    except Exception:
        logger.exception("Failed to identify user: %s", user.id)


def group_identify(team, properties: dict | None = None) -> None:
    """Identify a team group via posthog.group_identify.

    Args:
        team: The team to identify (can be None).
        properties: Optional dictionary of team properties.
    """
    if team is None:
        return

    if not _is_posthog_configured():
        return

    try:
        props = dict(properties) if properties else {}

        # Include default team properties
        if hasattr(team, "name") and team.name:
            props.setdefault("name", team.name)
        if hasattr(team, "slug") and team.slug:
            props.setdefault("slug", team.slug)

        posthog.group_identify(
            group_type="team",
            group_key=str(team.id),
            properties=props,
        )
    except Exception:
        logger.exception("Failed to identify team: %s", team.id)


def update_user_properties(user, properties: dict) -> None:
    """Update specific user properties without full identify.

    Unlike identify_user(), this function does NOT auto-add default properties
    like email, first_name, last_name. Use this for incremental property updates.

    Common use cases:
    - Setting has_connected_github, has_connected_jira, etc.
    - Updating role, teams_count after changes
    - Tracking feature usage milestones

    Args:
        user: The user to update properties for (can be None).
        properties: Dictionary of properties to set.
    """
    if user is None:
        return

    if not _is_posthog_configured():
        return

    try:
        posthog.identify(
            distinct_id=str(user.id),
            properties=properties,
        )
    except Exception:
        logger.exception("Failed to update user properties: %s", user.id)


def update_team_properties(team, properties: dict) -> None:
    """Update specific team properties without full group_identify.

    Unlike group_identify(), this function does NOT auto-add default properties
    like name, slug. Use this for incremental property updates.

    Common use cases:
    - Updating repos_tracked after repo changes
    - Setting total_prs, ai_adoption_rate from metrics
    - Tracking plan changes, member_count updates

    Args:
        team: The team to update properties for (can be None).
        properties: Dictionary of properties to set.
    """
    if team is None:
        return

    if not _is_posthog_configured():
        return

    try:
        posthog.group_identify(
            group_type="team",
            group_key=str(team.id),
            properties=properties,
        )
    except Exception:
        logger.exception("Failed to update team properties: %s", team.id)


def is_feature_enabled(feature_key: str, user=None, team=None) -> bool:
    """Check if a feature flag is enabled via posthog.feature_enabled.

    Args:
        feature_key: The feature flag key to check.
        user: Optional user for user-based feature flags.
        team: Optional team for team-based feature flags.

    Returns:
        True if the feature is enabled, False otherwise (including on errors).
    """
    if not _is_posthog_configured():
        return False

    if user is None and team is None:
        return False

    try:
        # Determine distinct_id - prefer user, fall back to team
        distinct_id = str(user.id) if user is not None else f"team:{team.id}"

        # Build groups dict if team is provided
        groups = {}
        if team is not None:
            groups["team"] = str(team.id)

        return posthog.feature_enabled(
            feature_key,
            distinct_id=distinct_id,
            groups=groups if groups else None,
        )
    except Exception:
        logger.exception("Failed to check feature flag: %s", feature_key)
        return False
