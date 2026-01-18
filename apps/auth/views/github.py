"""GitHub OAuth callback views.

Handles GitHub OAuth for login, onboarding, and integration flows.
"""

import logging
import secrets
from urllib.parse import urlencode

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit

from apps.auth.oauth_state import (
    FLOW_TYPE_INTEGRATION,
    FLOW_TYPE_LOGIN,
    FLOW_TYPE_ONBOARDING,
    OAuthStateError,
    create_oauth_state,
    verify_oauth_state,
)
from apps.integrations import tasks as integration_tasks
from apps.integrations.models import GitHubIntegration, IntegrationCredential
from apps.integrations.services.encryption import encrypt
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.integrations.views.helpers import _create_github_integration, _create_integration_credential
from apps.teams.helpers import get_next_unique_team_slug
from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN
from apps.users.models import CustomUser
from apps.utils.analytics import group_identify, track_event, update_user_properties

from ._helpers import (
    GITHUB_LOGIN_SCOPES,
    GITHUB_OAUTH_AUTHORIZE_URL,
    ONBOARDING_ORGS_KEY,
    ONBOARDING_TOKEN_KEY,
    get_github_error_redirect,
)

logger = logging.getLogger(__name__)


def _parse_github_name(full_name: str | None) -> tuple[str, str]:
    """Split GitHub full name into (first_name, last_name).

    GitHub provides a single 'name' field. We split on first space:
    - "Ivan" → ("Ivan", "")
    - "Ivan Yanchuk" → ("Ivan", "Yanchuk")
    - "Ivan van Yanchuk" → ("Ivan", "van Yanchuk")

    Names are truncated to 150 chars to match Django's AbstractUser field limits.
    """
    if not full_name:
        return ("", "")
    parts = full_name.strip().split(maxsplit=1)
    first_name = parts[0][:150] if parts else ""
    last_name = parts[1][:150] if len(parts) > 1 else ""
    return (first_name, last_name)


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
        return get_github_error_redirect(state_data)

    # Get authorization code
    code = request.GET.get("code")
    if not code:
        messages.error(request, _("No authorization code received from GitHub."))
        return get_github_error_redirect(state_data)

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


def _handle_login_callback(request, code: str):
    """Handle GitHub OAuth callback for login flow.

    Authenticates user via GitHub, creating account if needed.
    """
    # Late import for test mocking compatibility
    from apps.auth import views as _views

    # Build callback URL for token exchange
    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))

    try:
        # Exchange code for access token
        token_data = _views.github_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data.get("access_token")

        if not access_token:
            messages.error(request, _("Failed to get access token from GitHub."))
            return redirect("account_login")

        # Get GitHub user info
        github_user = _views.github_oauth.get_github_user(access_token)
        github_id = str(github_user["id"])
        github_login_name = github_user["login"]
        github_email = github_user.get("email")
        github_name = github_user.get("name")

        # If no public email, try to fetch primary email from /user/emails
        if github_email is None:
            github_email = _views.github_oauth.get_user_primary_email(access_token)

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
            first_name, last_name = _parse_github_name(github_name)
            user = CustomUser.objects.create(
                username=github_login_name,
                email=github_email or f"{github_login_name}@github.placeholder",
                first_name=first_name,
                last_name=last_name,
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
    # Late import for test mocking compatibility
    from apps.auth import views as _views

    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        return redirect("web:home")

    # Build callback URL for token exchange
    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))

    try:
        # Exchange code for access token
        token_data = _views.github_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data.get("access_token")

        if not access_token:
            messages.error(request, _("Failed to get access token from GitHub."))
            return redirect("onboarding:start")

        # Fetch user's organizations
        orgs = _views.github_oauth.get_user_organizations(access_token)

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
    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))

    try:
        # Exchange code for token
        token_data = _views.github_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
    except (GitHubOAuthError, KeyError) as e:
        logger.error(f"GitHub token exchange failed: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to GitHub. Please try again."))
        return redirect("integrations:integrations_home")

    # Get user's organizations
    try:
        orgs = _views.github_oauth.get_user_organizations(access_token)
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

        # Track event
        track_event(
            request.user,
            "integration_connected",
            {
                "provider": "github",
                "org_name": org_slug,
                "team_slug": team.slug,
                "is_reconnect": False,
                "flow": "integration",
            },
        )
        # Update user properties
        update_user_properties(request.user, {"has_connected_github": True})

        messages.success(request, _("Connected to {}.").format(org_slug))
        return redirect("integrations:integrations_home")

    # Multiple orgs - redirect to selection
    return redirect("integrations:github_select_org")
