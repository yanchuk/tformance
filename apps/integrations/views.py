"""Views for managing external integrations (GitHub, Jira, Slack)."""

import secrets

from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse

from apps.integrations.models import GitHubIntegration, IntegrationCredential
from apps.integrations.services import github_oauth
from apps.integrations.services.encryption import decrypt, encrypt
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.teams.decorators import login_and_team_required, team_admin_required


def _create_github_credential(team, access_token, user):
    """Create an encrypted GitHub credential for a team.

    Args:
        team: The team to create the credential for.
        access_token: The GitHub OAuth access token (will be encrypted).
        user: The user who connected the integration.

    Returns:
        IntegrationCredential: The created credential object.
    """
    encrypted_token = encrypt(access_token)
    return IntegrationCredential.objects.create(
        team=team,
        provider=IntegrationCredential.PROVIDER_GITHUB,
        access_token=encrypted_token,
        connected_by=user,
    )


def _create_github_integration(team, credential, org):
    """Create a GitHub integration for a team.

    Args:
        team: The team to create the integration for.
        credential: The IntegrationCredential to associate.
        org: Dictionary with 'login' and 'id' keys for the GitHub organization.

    Returns:
        GitHubIntegration: The created integration object.
    """
    return GitHubIntegration.objects.create(
        team=team,
        credential=credential,
        organization_slug=org["login"],
        organization_id=org["id"],
        webhook_secret=secrets.token_urlsafe(32),
    )


@login_and_team_required
def integrations_home(request, team_slug):
    """Display the integrations management page for a team.

    Shows the status of all integrations (GitHub, Jira, Slack) and provides
    connection/disconnection options.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team for which to display integrations.

    Returns:
        HttpResponse with the integrations page content.
    """
    team = request.team

    # Check if GitHub integration exists
    try:
        github_integration = GitHubIntegration.objects.get(team=team)
        github_connected = True
    except GitHubIntegration.DoesNotExist:
        github_integration = None
        github_connected = False

    context = {
        "github_connected": github_connected,
        "github_integration": github_integration,
        "active_tab": "integrations",
    }

    template = "integrations/home.html#page-content" if request.htmx else "integrations/home.html"
    return TemplateResponse(request, template, context)


@team_admin_required
def github_connect(request, team_slug):
    """Initiate GitHub OAuth flow for connecting a team's GitHub account.

    Redirects the user to GitHub's OAuth authorization page. On success,
    GitHub redirects back to github_callback.

    Requires team admin role.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team connecting to GitHub.

    Returns:
        HttpResponse redirecting to GitHub OAuth authorization.
    """
    team = request.team

    # Check if already connected
    if GitHubIntegration.objects.filter(team=team).exists():
        messages.info(request, "GitHub is already connected to this team.")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:github_callback", args=[team.slug]))

    # Get authorization URL
    authorization_url = github_oauth.get_authorization_url(team.id, callback_url)

    # Redirect to GitHub
    return redirect(authorization_url)


@login_and_team_required
def github_callback(request, team_slug):
    """Handle GitHub OAuth callback after user authorizes the app.

    Receives the authorization code from GitHub, exchanges it for an access token,
    and stores the token for the team.

    Args:
        request: The HTTP request object containing OAuth callback parameters.
        team_slug: The slug of the team that initiated the OAuth flow.

    Returns:
        HttpResponse redirecting to organization selection or integrations home.
    """
    team = request.team

    # Check for OAuth denial
    if request.GET.get("error") == "access_denied":
        messages.error(request, "GitHub authorization was cancelled.")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # Get code and state from query params
    code = request.GET.get("code")
    state = request.GET.get("state")

    # Validate parameters
    if not code:
        messages.error(request, "Missing authorization code from GitHub.")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    if not state:
        messages.error(request, "Missing state parameter from GitHub.")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # Verify state
    try:
        state_data = github_oauth.verify_oauth_state(state)
        team_id = state_data.get("team_id")

        # Verify team_id matches current team
        if team_id != team.id:
            messages.error(request, "Invalid state parameter.")
            return redirect("integrations:integrations_home", team_slug=team.slug)
    except GitHubOAuthError:
        messages.error(request, "Invalid state parameter.")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:github_callback", args=[team.slug]))

    # Exchange code for token
    try:
        token_data = github_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
    except (GitHubOAuthError, KeyError, Exception) as e:
        messages.error(request, f"Failed to exchange authorization code: {str(e)}")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # Get user's organizations
    try:
        orgs = github_oauth.get_user_organizations(access_token)
    except GitHubOAuthError as e:
        messages.error(request, f"Failed to get organizations: {str(e)}")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # Create credential for the team
    credential = _create_github_credential(team, access_token, request.user)

    # If single org, create integration immediately
    if len(orgs) == 1:
        org = orgs[0]
        _create_github_integration(team, credential, org)

        messages.success(request, f"Successfully connected to GitHub organization: {org['login']}")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # Multiple orgs - redirect to selection
    return redirect("integrations:github_select_org", team_slug=team.slug)


@team_admin_required
def github_disconnect(request, team_slug):
    """Disconnect GitHub integration for a team.

    Removes the stored GitHub OAuth token and any associated data for the team.

    Requires team admin role and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team disconnecting from GitHub.

    Returns:
        HttpResponse redirecting to integrations home with success message.
    """
    # Require POST method
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Delete GitHubIntegration (this will cascade delete the credential)
    GitHubIntegration.objects.filter(team=team).delete()

    # Also delete any orphaned credentials
    IntegrationCredential.objects.filter(team=team, provider=IntegrationCredential.PROVIDER_GITHUB).delete()

    messages.success(request, "GitHub integration disconnected successfully.")
    return redirect("integrations:integrations_home", team_slug=team.slug)


@login_and_team_required
def github_select_org(request, team_slug):
    """Allow user to select which GitHub organization to sync data from.

    Displays a list of GitHub organizations the authenticated user has access to,
    allowing them to choose which one to link to the team.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team selecting a GitHub organization.

    Returns:
        HttpResponse with organization selection form or redirect after POST.
    """
    team = request.team

    # Get credential for the team
    try:
        credential = IntegrationCredential.objects.get(team=team, provider=IntegrationCredential.PROVIDER_GITHUB)
    except IntegrationCredential.DoesNotExist:
        messages.error(request, "No GitHub credential found. Please try connecting again.")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    if request.method == "POST":
        # Get selected org from form
        organization_slug = request.POST.get("organization_slug")
        organization_id = request.POST.get("organization_id")

        # Create GitHubIntegration using helper
        org_data = {"login": organization_slug, "id": int(organization_id)}
        _create_github_integration(team, credential, org_data)

        messages.success(request, f"Successfully connected to GitHub organization: {organization_slug}")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # GET request - show organization selection form
    try:
        access_token = decrypt(credential.access_token)
        orgs = github_oauth.get_user_organizations(access_token)
    except (GitHubOAuthError, Exception):
        messages.error(request, "Failed to fetch organizations from GitHub.")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    context = {
        "organizations": orgs,
    }

    return render(request, "integrations/select_org.html", context)
