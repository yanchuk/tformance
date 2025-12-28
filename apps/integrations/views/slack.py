"""Slack integration views."""

import logging

from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse
from django_ratelimit.decorators import ratelimit

from apps.integrations.models import IntegrationCredential, SlackIntegration
from apps.teams.decorators import login_and_team_required, team_admin_required

logger = logging.getLogger(__name__)


@team_admin_required
def slack_connect(request):
    """Initiate Slack OAuth flow for connecting a team's Slack workspace.

    Redirects the user to Slack's OAuth authorization page. On success,
    Slack redirects back to the unified callback at /auth/slack/callback/.

    Requires team admin role.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team connecting to Slack.

    Returns:
        HttpResponse redirecting to Slack OAuth authorization.
    """
    from urllib.parse import urlencode

    from django.conf import settings

    from apps.auth.oauth_state import FLOW_TYPE_SLACK_INTEGRATION, create_oauth_state
    from apps.integrations.services.slack_oauth import SLACK_OAUTH_AUTHORIZE_URL, SLACK_OAUTH_SCOPES

    team = request.team

    # Check if already connected
    if SlackIntegration.objects.filter(team=team).exists():
        messages.info(request, "Slack is already connected to this team.")
        return redirect("integrations:integrations_home")

    # Create OAuth state with team_id for integration flow
    state = create_oauth_state(FLOW_TYPE_SLACK_INTEGRATION, team_id=team.id)

    # Build callback URL (use unified callback)
    callback_url = request.build_absolute_uri(reverse("tformance_auth:slack_callback"))

    # Build Slack OAuth authorization URL
    params = {
        "client_id": settings.SLACK_CLIENT_ID,
        "scope": SLACK_OAUTH_SCOPES,
        "redirect_uri": callback_url,
        "state": state,
    }
    authorization_url = f"{SLACK_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    # Redirect to Slack
    return redirect(authorization_url)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"])
@login_and_team_required
def slack_callback(request):
    """Legacy Slack OAuth callback - redirects to unified callback.

    This endpoint is kept for backwards compatibility with any in-flight OAuth flows
    that may be using the old callback URL. New flows use the unified callback at
    /auth/slack/callback/.

    Args:
        request: The HTTP request object containing OAuth callback parameters.
        team_slug: The slug of the team that initiated the OAuth flow.

    Returns:
        HttpResponse redirecting to unified callback.
    """
    # Forward all query parameters to the unified callback

    query_string = request.GET.urlencode()
    unified_url = reverse("tformance_auth:slack_callback")

    if query_string:
        unified_url = f"{unified_url}?{query_string}"

    return redirect(unified_url)


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
