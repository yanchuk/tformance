"""Views for the onboarding wizard.

Users without a team are directed here after signup to:
1. Connect their GitHub account
2. Select their organization (which creates the team)
3. Select repositories to track
4. Optionally connect Jira and Slack
"""

import base64
import json
import logging
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature, Signer
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit

from apps.integrations.models import GitHubIntegration, IntegrationCredential
from apps.integrations.services import github_oauth, member_sync
from apps.integrations.services.encryption import decrypt, encrypt
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.teams.helpers import get_next_unique_team_slug
from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN
from apps.utils.analytics import group_identify, track_event

logger = logging.getLogger(__name__)

# Session keys for onboarding state
ONBOARDING_TOKEN_KEY = "onboarding_github_token"
ONBOARDING_ORGS_KEY = "onboarding_github_orgs"
ONBOARDING_SELECTED_ORG_KEY = "onboarding_selected_org"


def _create_onboarding_state() -> str:
    """Create a signed OAuth state for onboarding (no team_id).

    Returns:
        Signed state string for CSRF protection
    """
    payload = json.dumps({"type": "onboarding"})
    encoded = base64.b64encode(payload.encode()).decode()
    signer = Signer()
    return signer.sign(encoded)


def _verify_onboarding_state(state: str) -> bool:
    """Verify the onboarding OAuth state.

    Args:
        state: The signed state string to verify

    Returns:
        True if state is valid, False otherwise
    """
    try:
        signer = Signer()
        unsigned = signer.unsign(state)
        decoded = base64.b64decode(unsigned).decode()
        payload = json.loads(decoded)
        return payload.get("type") == "onboarding"
    except (BadSignature, ValueError, KeyError):
        return False


@login_required
def onboarding_start(request):
    """Start of onboarding wizard - prompts user to connect GitHub."""
    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        # Redirect to /app/ which auto-selects the team
        return redirect("web:home")

    return render(
        request,
        "onboarding/start.html",
        {"page_title": _("Connect GitHub"), "step": 1},
    )


@login_required
def github_connect(request):
    """Initiate GitHub OAuth flow for onboarding."""
    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        # Redirect to /app/ which auto-selects the team
        return redirect("web:home")

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("onboarding:github_callback"))

    # Create state for CSRF protection
    state = _create_onboarding_state()

    # Build GitHub authorization URL (reusing the URL builder logic)
    from urllib.parse import urlencode

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": callback_url,
        "scope": github_oauth.GITHUB_OAUTH_SCOPES,
        "state": state,
    }
    auth_url = f"{github_oauth.GITHUB_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    return redirect(auth_url)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"])
@login_required
def github_callback(request):
    """Handle GitHub OAuth callback during onboarding.

    Rate limited to 10 requests per minute per IP to prevent abuse.
    """
    # Check if rate limited
    if getattr(request, "limited", False):
        messages.error(request, _("Too many requests. Please wait and try again."))
        return redirect("onboarding:start")

    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        # Redirect to /app/ which auto-selects the team
        return redirect("web:home")

    # Validate state parameter
    state = request.GET.get("state")
    if not state or not _verify_onboarding_state(state):
        messages.error(request, _("Invalid OAuth state. Please try again."))
        return redirect("onboarding:start")

    # Check for errors from GitHub
    error = request.GET.get("error")
    if error:
        error_description = request.GET.get("error_description", "Unknown error")
        messages.error(request, _("GitHub authorization failed: {}").format(error_description))
        return redirect("onboarding:start")

    # Get authorization code
    code = request.GET.get("code")
    if not code:
        messages.error(request, _("No authorization code received from GitHub."))
        return redirect("onboarding:start")

    # Build callback URL for token exchange
    callback_url = request.build_absolute_uri(reverse("onboarding:github_callback"))

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
        # Token is encrypted for defense-in-depth even in session storage
        request.session[ONBOARDING_TOKEN_KEY] = encrypt(access_token)
        request.session[ONBOARDING_ORGS_KEY] = orgs

        # If only one org, auto-select it and create team
        if len(orgs) == 1:
            return _create_team_from_org(request, orgs[0])

        # Multiple orgs - redirect to selection page
        return redirect("onboarding:select_org")

    except GitHubOAuthError as e:
        logger.error(f"GitHub OAuth error during onboarding: {e}", exc_info=True)
        messages.error(request, _("Failed to connect to GitHub. Please try again."))
        return redirect("onboarding:start")


@login_required
def select_organization(request):
    """Select which GitHub organization to use for the team."""
    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        # Redirect to /app/ which auto-selects the team
        return redirect("web:home")

    # Get orgs from session
    orgs = request.session.get(ONBOARDING_ORGS_KEY, [])
    if not orgs:
        messages.error(request, _("Please connect GitHub first."))
        return redirect("onboarding:start")

    if request.method == "POST":
        org_login = request.POST.get("organization")
        selected_org = next((org for org in orgs if org["login"] == org_login), None)

        if not selected_org:
            messages.error(request, _("Invalid organization selected."))
            return redirect("onboarding:select_org")

        return _create_team_from_org(request, selected_org)

    return render(
        request,
        "onboarding/select_org.html",
        {
            "organizations": orgs,
            "page_title": _("Select Organization"),
            "step": 1,
        },
    )


def _create_team_from_org(request, org: dict):
    """Create team from GitHub organization.

    Args:
        request: The HTTP request
        org: Organization dict with 'login' and 'id' keys

    Returns:
        Redirect response to next step
    """
    encrypted_token = request.session.get(ONBOARDING_TOKEN_KEY)
    if not encrypted_token:
        messages.error(request, _("Session expired. Please connect GitHub again."))
        return redirect("onboarding:start")

    # Decrypt token from session
    try:
        access_token = decrypt(encrypted_token)
    except Exception:
        logger.error("Failed to decrypt session token during onboarding")
        messages.error(request, _("Session error. Please connect GitHub again."))
        return redirect("onboarding:start")

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
        GitHubIntegration.objects.create(
            team=team,
            credential=credential,
            organization_slug=org["login"],
            organization_id=org["id"],
            webhook_secret=webhook_secret,
        )

        # Sync organization members
        try:
            member_sync.sync_github_members(team)
        except Exception as e:
            logger.warning(f"Failed to sync GitHub members during onboarding: {e}")
            # Don't block onboarding if member sync fails

        # Store selected org in session and clear token/orgs
        request.session[ONBOARDING_SELECTED_ORG_KEY] = org
        request.session.pop(ONBOARDING_TOKEN_KEY, None)
        request.session.pop(ONBOARDING_ORGS_KEY, None)

        # Track GitHub connection and team creation in PostHog
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


@login_required
def select_repositories(request):
    """Select which repositories to track."""
    # Get user's team
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Check if GitHub is connected
    try:
        integration = GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        messages.error(request, _("GitHub not connected."))
        return redirect("onboarding:start")

    if request.method == "POST":
        # Handle repository selection - for now just skip to next step
        # This will be implemented when we add the full repo tracking logic
        track_event(
            request.user,
            "onboarding_step_completed",
            {"step": "repos", "team_slug": team.slug},
        )
        return redirect("onboarding:connect_jira")

    # Fetch repositories (we'll implement this in the template)
    return render(
        request,
        "onboarding/select_repos.html",
        {
            "team": team,
            "integration": integration,
            "page_title": _("Select Repositories"),
            "step": 2,
        },
    )


@login_required
def connect_jira(request):
    """Optional step to connect Jira."""
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    if request.method == "POST":
        # Track skip (Jira connection tracking would go in the OAuth callback)
        track_event(
            request.user,
            "onboarding_skipped",
            {"step": "jira", "team_slug": team.slug},
        )
        return redirect("onboarding:connect_slack")

    return render(
        request,
        "onboarding/connect_jira.html",
        {
            "team": team,
            "page_title": _("Connect Jira"),
            "step": 3,
        },
    )


@login_required
def connect_slack(request):
    """Optional step to connect Slack."""
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    if request.method == "POST":
        # Track skip (Slack connection tracking would go in the OAuth callback)
        track_event(
            request.user,
            "onboarding_skipped",
            {"step": "slack", "team_slug": team.slug},
        )
        return redirect("onboarding:complete")

    return render(
        request,
        "onboarding/connect_slack.html",
        {
            "team": team,
            "page_title": _("Connect Slack"),
            "step": 4,
        },
    )


@login_required
def skip_onboarding(request):
    """Allow users to skip GitHub connection and create a basic team.

    Creates a team using the user's email prefix as the team name.
    The user can connect GitHub later from the integrations settings.
    """
    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        return redirect("web:home")

    # Create team from user's email prefix
    email_prefix = request.user.email.split("@")[0]
    team_name = f"{email_prefix}'s Team"
    team_slug = get_next_unique_team_slug(team_name)

    team = Team.objects.create(name=team_name, slug=team_slug)

    # Add user as admin
    Membership.objects.create(team=team, user=request.user, role=ROLE_ADMIN)

    # Clear any onboarding session data
    request.session.pop(ONBOARDING_TOKEN_KEY, None)
    request.session.pop(ONBOARDING_ORGS_KEY, None)
    request.session.pop(ONBOARDING_SELECTED_ORG_KEY, None)

    # Track onboarding skip in PostHog
    group_identify(team)
    track_event(
        request.user,
        "onboarding_skipped",
        {"step": "github", "team_slug": team.slug, "reason": "skip_button"},
    )

    messages.success(
        request,
        _("Team '{}' created! Connect GitHub from Integrations to unlock all features.").format(team_name),
    )
    return redirect("web:home")


@login_required
def onboarding_complete(request):
    """Final step showing sync status and dashboard link."""
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Clear onboarding session data
    request.session.pop(ONBOARDING_SELECTED_ORG_KEY, None)

    # Track onboarding completion
    track_event(
        request.user,
        "onboarding_completed",
        {"team_slug": team.slug},
    )

    return render(
        request,
        "onboarding/complete.html",
        {
            "team": team,
            "page_title": _("Setup Complete"),
            "step": 5,
        },
    )
