"""Unified OAuth callback views.

This module handles OAuth callbacks for both onboarding and integration flows,
routing to the appropriate handler based on the state parameter.
"""

import logging
import secrets
from urllib.parse import urlencode

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit

from apps.auth.oauth_state import (
    FLOW_TYPE_INTEGRATION,
    FLOW_TYPE_JIRA_INTEGRATION,
    FLOW_TYPE_JIRA_ONBOARDING,
    FLOW_TYPE_LOGIN,
    FLOW_TYPE_ONBOARDING,
    FLOW_TYPE_SLACK_INTEGRATION,
    FLOW_TYPE_SLACK_ONBOARDING,
    OAuthStateError,
    create_oauth_state,
    verify_oauth_state,
)
from apps.integrations import tasks as integration_tasks
from apps.integrations.models import GitHubIntegration, IntegrationCredential, JiraIntegration, SlackIntegration
from apps.integrations.services import (  # noqa: F401 - member_sync for test mocking
    github_oauth,
    jira_oauth,
    member_sync,
    slack_oauth,
)
from apps.integrations.services.encryption import encrypt
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.integrations.services.jira_oauth import JiraOAuthError
from apps.integrations.services.slack_oauth import SlackOAuthError
from apps.integrations.views.helpers import _create_github_integration, _create_integration_credential
from apps.teams.helpers import get_next_unique_team_slug
from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN
from apps.users.models import CustomUser
from apps.utils.analytics import group_identify, track_event

logger = logging.getLogger(__name__)

# Session keys for onboarding state (matching onboarding app)
ONBOARDING_TOKEN_KEY = "onboarding_github_token"
ONBOARDING_ORGS_KEY = "onboarding_github_orgs"

# GitHub OAuth constants for login flow (minimal scopes)
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_LOGIN_SCOPES = "user:email"


def github_login(request):
    """Initiate GitHub OAuth flow for login.

    Uses minimal scopes (user:email) since this is just for authentication.
    """
    # Create OAuth state with login flow type
    state = create_oauth_state(FLOW_TYPE_LOGIN)

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))

    # Build GitHub OAuth URL with minimal scopes
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": callback_url,
        "scope": GITHUB_LOGIN_SCOPES,
        "state": state,
    }

    github_url = f"{GITHUB_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    return redirect(github_url)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"])
def github_callback(request):
    """Unified GitHub OAuth callback handler.

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
        logger.warning(f"Invalid OAuth state: {e}")
        messages.error(request, _("Invalid OAuth state. Please try again."))
        return redirect("web:home")

    # Check for errors from GitHub
    error = request.GET.get("error")
    if error:
        error_description = request.GET.get("error_description", "Unknown error")
        messages.error(request, _("GitHub authorization failed: {}").format(error_description))
        return _get_error_redirect(state_data)

    # Get authorization code
    code = request.GET.get("code")
    if not code:
        messages.error(request, _("No authorization code received from GitHub."))
        return _get_error_redirect(state_data)

    # Route to appropriate handler
    flow_type = state_data["type"]

    if flow_type == FLOW_TYPE_LOGIN:
        return _handle_login_callback(request, code)
    elif flow_type == FLOW_TYPE_ONBOARDING:
        # Onboarding requires user to be logged in
        if not request.user.is_authenticated:
            messages.error(request, _("Please log in first."))
            return redirect("account_login")
        return _handle_onboarding_callback(request, code)
    elif flow_type == FLOW_TYPE_INTEGRATION:
        # Integration requires user to be logged in
        if not request.user.is_authenticated:
            messages.error(request, _("Please log in first."))
            return redirect("account_login")
        team_id = state_data["team_id"]
        return _handle_integration_callback(request, code, team_id)
    else:
        logger.error(f"Unknown flow type: {flow_type}")
        messages.error(request, _("Invalid OAuth flow. Please try again."))
        return redirect("web:home")


def _get_error_redirect(state_data: dict):
    """Get appropriate error redirect based on flow type."""
    flow_type = state_data.get("type")
    if flow_type == FLOW_TYPE_LOGIN:
        return redirect("account_login")
    elif flow_type == FLOW_TYPE_ONBOARDING:
        return redirect("onboarding:start")
    elif flow_type == FLOW_TYPE_INTEGRATION:
        return redirect("integrations:integrations_home")
    return redirect("web:home")


def _handle_login_callback(request, code: str):
    """Handle GitHub OAuth callback for login flow.

    Authenticates user via GitHub, creating account if needed.
    """
    # Build callback URL for token exchange
    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))

    try:
        # Exchange code for access token
        token_data = github_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data.get("access_token")

        if not access_token:
            messages.error(request, _("Failed to get access token from GitHub."))
            return redirect("account_login")

        # Get GitHub user info
        github_user = github_oauth.get_github_user(access_token)
        github_id = str(github_user["id"])
        github_login_name = github_user["login"]
        github_email = github_user.get("email")
        github_name = github_user.get("name")

        # Try to find existing user
        user = None

        # First: Try to match by GitHub ID via SocialAccount
        try:
            social_account = SocialAccount.objects.get(provider="github", uid=github_id)
            user = social_account.user
        except SocialAccount.DoesNotExist:
            pass

        # Second: Try to match by email if we have one
        if user is None and github_email:
            try:
                user = CustomUser.objects.get(email=github_email)
                # Create SocialAccount to link the accounts
                SocialAccount.objects.create(
                    user=user,
                    provider="github",
                    uid=github_id,
                    extra_data={"login": github_login_name, "name": github_name},
                )
            except CustomUser.DoesNotExist:
                pass

        # Third: Create new user if not found
        if user is None:
            user = CustomUser.objects.create(
                username=github_login_name,
                email=github_email or f"{github_login_name}@github.placeholder",
            )
            # Create SocialAccount
            SocialAccount.objects.create(
                user=user,
                provider="github",
                uid=github_id,
                extra_data={"login": github_login_name, "name": github_name},
            )

        # Log the user in
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        # Redirect based on team membership
        if user.teams.exists():
            return redirect("web:home")
        else:
            return redirect("onboarding:start")

    except GitHubOAuthError as e:
        logger.error(f"GitHub OAuth error during login: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to GitHub. Please try again."))
        return redirect("account_login")


def _handle_onboarding_callback(request, code: str):
    """Handle GitHub OAuth callback for onboarding flow.

    Creates a new team from the user's GitHub organization.
    """
    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        return redirect("web:home")

    # Build callback URL for token exchange
    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))

    try:
        # Exchange code for access token
        token_data = github_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data.get("access_token")

        if not access_token:
            messages.error(request, _("Failed to get access token from GitHub."))
            return redirect("onboarding:start")

        # Fetch user's organizations
        orgs = github_oauth.get_user_organizations(access_token)

        if not orgs:
            messages.error(
                request,
                _("No GitHub organizations found. You need to be a member of at least one organization."),
            )
            return redirect("onboarding:start")

        # Store token (encrypted) and orgs in session for next step
        request.session[ONBOARDING_TOKEN_KEY] = encrypt(access_token)
        request.session[ONBOARDING_ORGS_KEY] = orgs

        # If only one org, auto-select it and create team
        if len(orgs) == 1:
            return _create_team_from_org(request, orgs[0], access_token)

        # Multiple orgs - redirect to selection page
        return redirect("onboarding:select_org")

    except GitHubOAuthError as e:
        logger.error(f"GitHub OAuth error during onboarding: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to GitHub. Please try again."))
        return redirect("onboarding:start")


def _create_team_from_org(request, org: dict, access_token: str):
    """Create team from GitHub organization during onboarding."""
    try:
        # Create team from org name
        team_name = org["login"]
        team_slug = get_next_unique_team_slug(team_name)
        team = Team.objects.create(name=team_name, slug=team_slug)

        # Add user as admin
        Membership.objects.create(team=team, user=request.user, role=ROLE_ADMIN)

        # Create encrypted credential
        encrypted_token = encrypt(access_token)
        credential = IntegrationCredential.objects.create(
            team=team,
            provider=IntegrationCredential.PROVIDER_GITHUB,
            access_token=encrypted_token,
            connected_by=request.user,
        )

        # Create GitHub integration
        webhook_secret = secrets.token_hex(32)
        integration = GitHubIntegration.objects.create(
            team=team,
            credential=credential,
            organization_slug=org["login"],
            organization_id=org["id"],
            webhook_secret=webhook_secret,
        )

        # Queue async member sync task
        try:
            integration_tasks.sync_github_members_task.delay(integration.id)
        except Exception as e:
            logger.warning(f"Failed to queue GitHub member sync task during onboarding: {e}")
            # Don't block onboarding if task dispatch fails

        # Clear session token/orgs
        request.session.pop(ONBOARDING_TOKEN_KEY, None)
        request.session.pop(ONBOARDING_ORGS_KEY, None)

        # Track events
        group_identify(team)
        track_event(
            request.user,
            "github_connected",
            {
                "org_name": org["login"],
                "member_count": team.members.count(),
                "team_slug": team.slug,
            },
        )
        track_event(
            request.user,
            "onboarding_step_completed",
            {"step": "github", "team_slug": team.slug},
        )

        messages.success(request, _("Team '{}' created successfully!").format(team_name))
        return redirect("onboarding:select_repos")

    except Exception as e:
        logger.error(f"Failed to create team from org during onboarding: {e}")
        messages.error(request, _("Failed to create team. Please try again."))
        return redirect("onboarding:start")


def _handle_integration_callback(request, code: str, team_id: int):
    """Handle GitHub OAuth callback for integration flow.

    Adds GitHub integration to an existing team.
    """
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
    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))

    try:
        # Exchange code for token
        token_data = github_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
    except (GitHubOAuthError, KeyError) as e:
        logger.error(f"GitHub token exchange failed: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to GitHub. Please try again."))
        return redirect("integrations:integrations_home")

    # Get user's organizations
    try:
        orgs = github_oauth.get_user_organizations(access_token)
    except GitHubOAuthError as e:
        logger.error(f"Failed to get GitHub organizations: {e}", exc_info=True)
        messages.error(request, _("Failed to get organizations from GitHub. Please try again."))
        return redirect("integrations:integrations_home")

    # Create credential for the team
    credential = _create_integration_credential(team, access_token, IntegrationCredential.PROVIDER_GITHUB, request.user)

    # If single org, create integration immediately
    if len(orgs) == 1:
        org = orgs[0]
        org_slug = org["login"]
        integration = _create_github_integration(team, credential, org)

        # Queue async member sync task
        try:
            integration_tasks.sync_github_members_task.delay(integration.id)
        except Exception as e:
            logger.warning(f"Failed to queue GitHub member sync task: {e}")
            # Don't block callback if task dispatch fails

        messages.success(request, _("Connected to {}.").format(org_slug))
        return redirect("integrations:integrations_home")

    # Multiple orgs - redirect to selection
    return redirect("integrations:github_select_org")


# Session keys for Jira onboarding
JIRA_ONBOARDING_CREDENTIAL_KEY = "jira_onboarding_credential_id"
JIRA_ONBOARDING_INTEGRATION_KEY = "jira_onboarding_integration_id"


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
        return _get_jira_error_redirect(state_data)

    # Get authorization code
    code = request.GET.get("code")
    if not code:
        messages.error(request, _("No authorization code received from Jira."))
        return _get_jira_error_redirect(state_data)

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


def _get_jira_error_redirect(state_data: dict):
    """Get appropriate error redirect based on Jira flow type."""
    flow_type = state_data.get("type")
    if flow_type == FLOW_TYPE_JIRA_ONBOARDING:
        return redirect("onboarding:connect_jira")
    elif flow_type == FLOW_TYPE_JIRA_INTEGRATION:
        return redirect("integrations:integrations_home")
    return redirect("web:home")


def _handle_jira_onboarding_callback(request, code: str, team_id: int | None):
    """Handle Jira OAuth callback for onboarding flow.

    Creates Jira integration and redirects to project selection.
    """
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
        token_data = jira_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        if not access_token:
            messages.error(request, _("Failed to get access token from Jira."))
            return redirect("onboarding:connect_jira")

        # Get accessible Jira sites
        sites = jira_oauth.get_accessible_resources(access_token)

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
        token_data = jira_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
    except (JiraOAuthError, KeyError) as e:
        logger.error(f"Jira token exchange failed: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to Jira. Please try again."))
        return redirect("integrations:integrations_home")

    # Get accessible Jira sites
    try:
        sites = jira_oauth.get_accessible_resources(access_token)
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
        messages.success(request, _("Connected to Jira: {}").format(site["name"]))
        return redirect("integrations:jira_projects_list")

    # Multiple sites - store in session and redirect to selection
    request.session["jira_sites"] = sites
    return redirect("integrations:jira_select_site")


# Session keys for Slack onboarding
SLACK_ONBOARDING_INTEGRATION_KEY = "slack_onboarding_integration_id"


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
        return _get_slack_error_redirect(state_data)

    # Get authorization code
    code = request.GET.get("code")
    if not code:
        messages.error(request, _("No authorization code received from Slack."))
        return _get_slack_error_redirect(state_data)

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


def _get_slack_error_redirect(state_data: dict):
    """Get appropriate error redirect based on Slack flow type."""
    flow_type = state_data.get("type")
    if flow_type == FLOW_TYPE_SLACK_ONBOARDING:
        return redirect("onboarding:connect_slack")
    elif flow_type == FLOW_TYPE_SLACK_INTEGRATION:
        return redirect("integrations:integrations_home")
    return redirect("web:home")


def _handle_slack_onboarding_callback(request, code: str, team_id: int | None):
    """Handle Slack OAuth callback for onboarding flow.

    Creates SlackIntegration and redirects to completion.
    """
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
        token_data = slack_oauth.exchange_code_for_token(code, callback_url)
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
        token_data = slack_oauth.exchange_code_for_token(code, callback_url)
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

    # Track event
    track_event(
        request.user,
        "slack_connected",
        {
            "workspace_name": slack_team.get("name", ""),
            "team_slug": team.slug,
            "flow": "integration",
        },
    )

    messages.success(request, _("Connected to Slack: {}").format(slack_team.get("name", "Workspace")))
    return redirect("integrations:slack_settings")
