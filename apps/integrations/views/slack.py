"""Slack integration views."""

import logging

from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse
from django_ratelimit.decorators import ratelimit

from apps.integrations.models import IntegrationCredential, SlackIntegration
from apps.integrations.services import slack_oauth
from apps.integrations.services.slack_oauth import SlackOAuthError
from apps.teams.decorators import login_and_team_required, team_admin_required

from .helpers import _create_integration_credential, _validate_oauth_callback

logger = logging.getLogger(__name__)


@team_admin_required
def slack_connect(request):
    """Initiate Slack OAuth flow for connecting a team's Slack workspace.

    Redirects the user to Slack's OAuth authorization page. On success,
    Slack redirects back to slack_callback.

    Requires team admin role.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team connecting to Slack.

    Returns:
        HttpResponse redirecting to Slack OAuth authorization.
    """
    team = request.team

    # Check if already connected
    if SlackIntegration.objects.filter(team=team).exists():
        messages.info(request, "Slack is already connected to this team.")
        return redirect("integrations:integrations_home")

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:slack_callback"))

    # Get authorization URL
    authorization_url = slack_oauth.get_authorization_url(team.id, callback_url)

    # Redirect to Slack
    return redirect(authorization_url)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"])
@login_and_team_required
def slack_callback(request):
    """Handle Slack OAuth callback after user authorizes the app.

    Receives the authorization code from Slack, exchanges it for an access token,
    and stores the token for the team.

    Rate limited to 10 requests per minute per IP to prevent abuse.

    Args:
        request: The HTTP request object containing OAuth callback parameters.
        team_slug: The slug of the team that initiated the OAuth flow.

    Returns:
        HttpResponse redirecting to integrations home.
    """
    # Check if rate limited
    if getattr(request, "limited", False):
        messages.error(request, "Too many requests. Please wait and try again.")
        return redirect("integrations:integrations_home")

    team = request.team

    # Validate OAuth callback parameters
    code, error_response = _validate_oauth_callback(
        request, team, slack_oauth.verify_slack_oauth_state, SlackOAuthError, "Slack"
    )
    if error_response:
        return error_response

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:slack_callback"))

    # Exchange code for token
    try:
        token_data = slack_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
        bot_user_id = token_data["bot_user_id"]
        workspace_id = token_data["team"]["id"]
        workspace_name = token_data["team"]["name"]
    except (SlackOAuthError, KeyError, Exception) as e:
        logger.error(f"Slack token exchange failed: {e}", exc_info=True)
        messages.error(request, "Failed to connect to Slack. Please try again.")
        return redirect("integrations:integrations_home")

    # Check if this workspace is already connected (update if so)
    existing_integration = SlackIntegration.objects.filter(team=team, workspace_id=workspace_id).first()

    if existing_integration:
        # Update existing integration
        existing_integration.workspace_name = workspace_name
        existing_integration.bot_user_id = bot_user_id
        existing_integration.save()

        # Update credential (EncryptedTextField auto-encrypts on save)
        existing_integration.credential.access_token = access_token
        existing_integration.credential.connected_by = request.user
        existing_integration.credential.save()

        messages.success(request, f"Reconnected to Slack workspace: {workspace_name}")
    else:
        # Create credential for the team
        credential = _create_integration_credential(
            team, access_token, IntegrationCredential.PROVIDER_SLACK, request.user
        )

        # Create SlackIntegration
        SlackIntegration.objects.create(
            team=team,
            credential=credential,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            bot_user_id=bot_user_id,
        )

        messages.success(request, f"Connected to Slack workspace: {workspace_name}")

    return redirect("integrations:integrations_home")


@team_admin_required
def slack_disconnect(request):
    """Disconnect Slack integration for a team.

    Removes the stored Slack OAuth token and any associated data for the team.

    Requires team admin role and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team disconnecting from Slack.

    Returns:
        HttpResponse redirecting to integrations home with success message.
    """
    # Require POST method
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Delete SlackIntegration (this will cascade delete the credential)
    SlackIntegration.objects.filter(team=team).delete()

    # Also delete any orphaned credentials
    IntegrationCredential.objects.filter(team=team, provider=IntegrationCredential.PROVIDER_SLACK).delete()

    messages.success(request, "Slack integration disconnected successfully.")
    return redirect("integrations:integrations_home")


@team_admin_required
def slack_settings(request):
    """Configure Slack integration settings.

    GET: Display settings form
    POST: Update leaderboard settings

    Requires team admin role.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.

    Returns:
        HttpResponse with settings form or redirect after update.
    """
    from datetime import time

    team = request.team

    # Get Slack integration
    try:
        integration = SlackIntegration.objects.get(team=team)
    except SlackIntegration.DoesNotExist:
        messages.error(request, "Slack integration not found. Please connect Slack first.")
        return redirect("integrations:integrations_home")

    if request.method == "POST":
        # Update leaderboard settings
        integration.leaderboard_channel_id = request.POST.get("leaderboard_channel_id", "")
        try:
            integration.leaderboard_day = int(request.POST.get("leaderboard_day", 0))
        except (ValueError, TypeError):
            integration.leaderboard_day = 0

        # Parse time string (format: "HH:MM")
        time_str = request.POST.get("leaderboard_time", "09:00")
        try:
            hour, minute = map(int, time_str.split(":"))
            integration.leaderboard_time = time(hour, minute)
        except (ValueError, AttributeError):
            integration.leaderboard_time = time(9, 0)

        # Update enabled flags
        integration.leaderboard_enabled = request.POST.get("leaderboard_enabled") == "True"
        integration.surveys_enabled = request.POST.get("surveys_enabled") == "True"
        integration.reveals_enabled = request.POST.get("reveals_enabled") == "True"

        integration.save()

        messages.success(request, "Slack settings updated successfully.")
        return redirect("integrations:slack_settings")

    # GET request - show settings form
    context = {
        "integration": integration,
        "active_tab": "integrations",
    }

    return render(request, "integrations/slack_settings.html", context)
