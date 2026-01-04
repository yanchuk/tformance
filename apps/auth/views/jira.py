"""Jira OAuth callback views.

Handles Jira OAuth for onboarding and integration flows.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit

from apps.auth.oauth_state import (
    FLOW_TYPE_JIRA_INTEGRATION,
    FLOW_TYPE_JIRA_ONBOARDING,
    OAuthStateError,
    verify_oauth_state,
)
from apps.integrations.models import IntegrationCredential, JiraIntegration
from apps.integrations.services.encryption import encrypt
from apps.integrations.services.jira_oauth import JiraOAuthError
from apps.integrations.views.helpers import _create_integration_credential
from apps.teams.models import Team
from apps.utils.analytics import track_event, update_user_properties

from ._helpers import (
    JIRA_ONBOARDING_CREDENTIAL_KEY,
    JIRA_ONBOARDING_INTEGRATION_KEY,
    get_jira_error_redirect,
)

logger = logging.getLogger(__name__)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"])
@login_required
def jira_callback(request):
    """Unified Jira OAuth callback handler.

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
        logger.warning(f"Invalid Jira OAuth state: {e}")
        messages.error(request, _("Invalid OAuth state. Please try again."))
        return redirect("web:home")

    # Check for errors from Atlassian
    error = request.GET.get("error")
    if error:
        error_description = request.GET.get("error_description", "Unknown error")
        messages.error(request, _("Jira authorization failed: {}").format(error_description))
        return get_jira_error_redirect(state_data)

    # Get authorization code
    code = request.GET.get("code")
    if not code:
        messages.error(request, _("No authorization code received from Jira."))
        return get_jira_error_redirect(state_data)

    # Route to appropriate handler
    flow_type = state_data["type"]

    if flow_type == FLOW_TYPE_JIRA_ONBOARDING:
        team_id = state_data.get("team_id")
        return _handle_jira_onboarding_callback(request, code, team_id)
    elif flow_type == FLOW_TYPE_JIRA_INTEGRATION:
        team_id = state_data["team_id"]
        return _handle_jira_integration_callback(request, code, team_id)
    else:
        logger.error(f"Unknown Jira flow type: {flow_type}")
        messages.error(request, _("Invalid OAuth flow. Please try again."))
        return redirect("web:home")


def _handle_jira_onboarding_callback(request, code: str, team_id: int | None):
    """Handle Jira OAuth callback for onboarding flow.

    Creates Jira integration and redirects to project selection.
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
        return redirect("onboarding:connect_jira")

    # Build callback URL for token exchange
    callback_url = request.build_absolute_uri(reverse("tformance_auth:jira_callback"))

    try:
        # Exchange code for access token
        token_data = _views.jira_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        if not access_token:
            messages.error(request, _("Failed to get access token from Jira."))
            return redirect("onboarding:connect_jira")

        # Get accessible Jira sites
        sites = _views.jira_oauth.get_accessible_resources(access_token)

        if not sites:
            messages.error(request, _("No Jira sites found. Please ensure you have access to at least one Jira site."))
            return redirect("onboarding:connect_jira")

        # Create or update credential
        credential, _created = IntegrationCredential.objects.update_or_create(
            team=team,
            provider=IntegrationCredential.PROVIDER_JIRA,
            defaults={
                "access_token": encrypt(access_token),
                "refresh_token": encrypt(refresh_token) if refresh_token else "",
                "connected_by": request.user,
            },
        )

        # For now, use the first site (most users have one)
        # TODO: Add site selection if multiple sites
        site = sites[0]

        # Create or update Jira integration
        integration, _created = JiraIntegration.objects.update_or_create(
            team=team,
            defaults={
                "credential": credential,
                "cloud_id": site["id"],
                "site_name": site["name"],
                "site_url": site["url"],
            },
        )

        # Store in session for project selection step
        request.session[JIRA_ONBOARDING_CREDENTIAL_KEY] = credential.id
        request.session[JIRA_ONBOARDING_INTEGRATION_KEY] = integration.id

        # Track event
        track_event(
            request.user,
            "jira_connected",
            {"site_name": site["name"], "team_slug": team.slug, "flow": "onboarding"},
        )

        messages.success(request, _("Connected to Jira: {}").format(site["name"]))
        return redirect("onboarding:select_jira_projects")

    except JiraOAuthError as e:
        logger.error(f"Jira OAuth error during onboarding: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to Jira. Please try again."))
        return redirect("onboarding:connect_jira")


def _handle_jira_integration_callback(request, code: str, team_id: int):
    """Handle Jira OAuth callback for integration flow (existing team).

    Adds Jira integration to an existing team.
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
    callback_url = request.build_absolute_uri(reverse("tformance_auth:jira_callback"))

    try:
        # Exchange code for token
        token_data = _views.jira_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
    except (JiraOAuthError, KeyError) as e:
        logger.error(f"Jira token exchange failed: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to Jira. Please try again."))
        return redirect("integrations:integrations_home")

    # Get accessible Jira sites
    try:
        sites = _views.jira_oauth.get_accessible_resources(access_token)
    except JiraOAuthError as e:
        logger.error(f"Failed to get Jira sites: {e}", exc_info=True)
        messages.error(request, _("Failed to get Jira sites. Please try again."))
        return redirect("integrations:integrations_home")

    if not sites:
        messages.error(request, _("No Jira sites found."))
        return redirect("integrations:integrations_home")

    # Create credential
    credential = _create_integration_credential(team, access_token, IntegrationCredential.PROVIDER_JIRA, request.user)
    if refresh_token:
        credential.refresh_token = encrypt(refresh_token)
        credential.save()

    # If single site, create integration immediately
    if len(sites) == 1:
        site = sites[0]
        JiraIntegration.objects.create(
            team=team,
            credential=credential,
            cloud_id=site["id"],
            site_name=site["name"],
            site_url=site["url"],
        )

        # Track event
        track_event(
            request.user,
            "integration_connected",
            {
                "provider": "jira",
                "site_name": site["name"],
                "team_slug": team.slug,
                "is_reconnect": False,
                "flow": "integration",
            },
        )
        # Update user properties
        update_user_properties(request.user, {"has_connected_jira": True})

        messages.success(request, _("Connected to Jira: {}").format(site["name"]))
        return redirect("integrations:jira_projects_list")

    # Multiple sites - store in session and redirect to selection
    request.session["jira_sites"] = sites
    return redirect("integrations:jira_select_site")
