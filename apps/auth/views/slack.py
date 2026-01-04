"""Slack OAuth callback views.

Handles Slack OAuth for onboarding and integration flows.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit

from apps.auth.oauth_state import (
    FLOW_TYPE_SLACK_INTEGRATION,
    FLOW_TYPE_SLACK_ONBOARDING,
    OAuthStateError,
    verify_oauth_state,
)
from apps.integrations.models import IntegrationCredential, SlackIntegration
from apps.integrations.services.encryption import encrypt
from apps.integrations.services.slack_oauth import SlackOAuthError
from apps.teams.models import Team
from apps.utils.analytics import track_event, update_user_properties

from ._helpers import SLACK_ONBOARDING_INTEGRATION_KEY, get_slack_error_redirect

logger = logging.getLogger(__name__)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"])
@login_required
def slack_callback(request):
    """Unified Slack OAuth callback handler.

    Routes to appropriate handler based on flow type in state parameter.
    Rate limited to 10 requests per minute per IP.
    """
    # Check if rate limited
    if getattr(request, "limited", False):
        messages.error(request, _("Too many requests. Please wait and try again."))
        return redirect("web:home")

    # Validate state parameter
    state = request.GET.get("state")
    try:
        state_data = verify_oauth_state(state)
    except OAuthStateError as e:
        logger.warning(f"Invalid Slack OAuth state: {e}")
        messages.error(request, _("Invalid OAuth state. Please try again."))
        return redirect("web:home")

    # Check for errors from Slack
    error = request.GET.get("error")
    if error:
        error_description = request.GET.get("error_description", "Unknown error")
        messages.error(request, _("Slack authorization failed: {}").format(error_description))
        return get_slack_error_redirect(state_data)

    # Get authorization code
    code = request.GET.get("code")
    if not code:
        messages.error(request, _("No authorization code received from Slack."))
        return get_slack_error_redirect(state_data)

    # Route to appropriate handler
    flow_type = state_data["type"]

    if flow_type == FLOW_TYPE_SLACK_ONBOARDING:
        team_id = state_data.get("team_id")
        return _handle_slack_onboarding_callback(request, code, team_id)
    elif flow_type == FLOW_TYPE_SLACK_INTEGRATION:
        team_id = state_data["team_id"]
        return _handle_slack_integration_callback(request, code, team_id)
    else:
        logger.error(f"Unknown Slack flow type: {flow_type}")
        messages.error(request, _("Invalid OAuth flow. Please try again."))
        return redirect("web:home")


def _handle_slack_onboarding_callback(request, code: str, team_id: int | None):
    """Handle Slack OAuth callback for onboarding flow.

    Creates SlackIntegration and redirects to completion.
    """
    # Late import for test mocking compatibility
    from apps.auth import views as _views

    # Get user's team (should exist from GitHub onboarding step)
    if not request.user.teams.exists():
        messages.error(request, _("Please complete GitHub setup first."))
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Verify team_id if provided
    if team_id and team.id != team_id:
        messages.error(request, _("Invalid team context."))
        return redirect("onboarding:connect_slack")

    # Build callback URL for token exchange
    callback_url = request.build_absolute_uri(reverse("tformance_auth:slack_callback"))

    try:
        # Exchange code for access token
        token_data = _views.slack_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data.get("access_token")
        bot_user_id = token_data.get("bot_user_id")
        slack_team = token_data.get("team", {})

        if not access_token:
            messages.error(request, _("Failed to get access token from Slack."))
            return redirect("onboarding:connect_slack")

        # Create or update credential
        credential, _created = IntegrationCredential.objects.update_or_create(
            team=team,
            provider=IntegrationCredential.PROVIDER_SLACK,
            defaults={
                "access_token": encrypt(access_token),
                "connected_by": request.user,
            },
        )

        # Create or update Slack integration
        integration, _created = SlackIntegration.objects.update_or_create(
            team=team,
            defaults={
                "credential": credential,
                "workspace_id": slack_team.get("id", ""),
                "workspace_name": slack_team.get("name", ""),
                "bot_user_id": bot_user_id or "",
                "surveys_enabled": True,
                "leaderboard_enabled": False,  # Default to disabled during onboarding
            },
        )

        # Store in session for later steps if needed
        request.session[SLACK_ONBOARDING_INTEGRATION_KEY] = integration.id

        # Track event
        track_event(
            request.user,
            "slack_connected",
            {
                "workspace_name": slack_team.get("name", ""),
                "team_slug": team.slug,
                "flow": "onboarding",
            },
        )
        track_event(
            request.user,
            "onboarding_step_completed",
            {"step": "slack", "team_slug": team.slug},
        )

        messages.success(request, _("Connected to Slack: {}").format(slack_team.get("name", "Workspace")))
        return redirect("onboarding:complete")

    except SlackOAuthError as e:
        logger.error(f"Slack OAuth error during onboarding: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to Slack. Please try again."))
        return redirect("onboarding:connect_slack")


def _handle_slack_integration_callback(request, code: str, team_id: int):
    """Handle Slack OAuth callback for integration flow (existing team).

    Adds Slack integration to an existing team.
    """
    # Late import for test mocking compatibility
    from apps.auth import views as _views

    # Get team and verify access
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        messages.error(request, _("Team not found."))
        return redirect("web:home")

    # Verify user has access to this team
    if not request.user.teams.filter(id=team_id).exists():
        messages.error(request, _("You don't have access to this team."))
        return redirect("web:home")

    # Build callback URL for token exchange
    callback_url = request.build_absolute_uri(reverse("tformance_auth:slack_callback"))

    try:
        # Exchange code for token
        token_data = _views.slack_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
        bot_user_id = token_data.get("bot_user_id", "")
        slack_team = token_data.get("team", {})
    except (SlackOAuthError, KeyError) as e:
        logger.error(f"Slack token exchange failed: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to Slack. Please try again."))
        return redirect("integrations:integrations_home")

    # Create or update credential
    credential, _created = IntegrationCredential.objects.update_or_create(
        team=team,
        provider=IntegrationCredential.PROVIDER_SLACK,
        defaults={
            "access_token": encrypt(access_token),
            "connected_by": request.user,
        },
    )

    # Create or update Slack integration
    SlackIntegration.objects.update_or_create(
        team=team,
        defaults={
            "credential": credential,
            "workspace_id": slack_team.get("id", ""),
            "workspace_name": slack_team.get("name", ""),
            "bot_user_id": bot_user_id,
            "surveys_enabled": True,
            "leaderboard_enabled": True,
        },
    )

    # Track events
    track_event(
        request.user,
        "slack_connected",
        {
            "workspace_name": slack_team.get("name", ""),
            "team_slug": team.slug,
            "flow": "integration",
        },
    )
    track_event(
        request.user,
        "integration_connected",
        {
            "provider": "slack",
            "workspace_name": slack_team.get("name", ""),
            "team_slug": team.slug,
            "is_reconnect": False,
            "flow": "integration",
        },
    )
    # Update user properties
    update_user_properties(request.user, {"has_connected_slack": True})

    messages.success(request, _("Connected to Slack: {}").format(slack_team.get("name", "Workspace")))
    return redirect("integrations:slack_settings")
