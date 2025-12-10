"""Views for managing external integrations (GitHub, Jira, Slack)."""

import logging
import secrets

from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse

from apps.integrations.models import GitHubIntegration, IntegrationCredential
from apps.integrations.services import github_oauth, member_sync
from apps.integrations.services.encryption import decrypt, encrypt
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.metrics.models import TeamMember
from apps.teams.decorators import login_and_team_required, team_admin_required

logger = logging.getLogger(__name__)


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


def _sync_github_members_after_connection(team, access_token, org_slug):
    """Sync GitHub organization members after connecting an integration.

    This is called after successfully creating a GitHubIntegration to import
    team members from the GitHub organization.

    Args:
        team: The team to sync members for.
        access_token: The GitHub OAuth access token.
        org_slug: The GitHub organization slug.

    Returns:
        int: The number of members created, or 0 if sync fails.
    """
    try:
        result = member_sync.sync_github_members(team, access_token, org_slug)
        return result["created"]
    except Exception as e:
        # Log error but don't fail the OAuth flow
        logger.error(f"Failed to sync GitHub members for team {team.slug}: {e}")
        return 0


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
        # Count members with GitHub IDs
        member_count = TeamMember.objects.filter(team=team).exclude(github_id="").count()
    except GitHubIntegration.DoesNotExist:
        github_integration = None
        github_connected = False
        member_count = 0

    context = {
        "github_connected": github_connected,
        "github_integration": github_integration,
        "member_count": member_count,
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
        org_slug = org["login"]
        _create_github_integration(team, credential, org)

        # Sync members from GitHub
        member_count = _sync_github_members_after_connection(team, access_token, org_slug)

        messages.success(request, f"Connected to {org_slug}. Imported {member_count} members.")
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

        # Sync members from GitHub
        access_token = decrypt(credential.access_token)
        member_count = _sync_github_members_after_connection(team, access_token, organization_slug)

        messages.success(request, f"Connected to {organization_slug}. Imported {member_count} members.")
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


@login_and_team_required
def github_members(request, team_slug):
    """Display list of GitHub members discovered for the team.

    Shows all team members that have been imported from GitHub (those with github_id populated).

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team to display members for.

    Returns:
        HttpResponse with the GitHub members list or redirect if not connected.
    """
    from apps.metrics.models import TeamMember

    team = request.team

    # Check if GitHub integration exists
    try:
        GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        messages.error(request, "Please connect GitHub first.")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # Query members with github_id populated
    members = TeamMember.objects.filter(team=team).exclude(github_id="")

    context = {
        "members": members,
    }

    return render(request, "integrations/github_members.html", context)


@team_admin_required
def github_members_sync(request, team_slug):
    """Trigger manual re-sync of GitHub members.

    Re-imports team members from the connected GitHub organization.

    Requires team admin role and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team to sync members for.

    Returns:
        HttpResponse redirecting to github_members with success message.
    """
    # Require POST method
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Get GitHub integration
    try:
        integration = GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        messages.error(request, "GitHub integration not found. Please connect GitHub first.")
        return redirect("integrations:integrations_home", team_slug=team.slug)

    # Decrypt access token
    access_token = decrypt(integration.credential.access_token)

    # Call sync service
    try:
        result = member_sync.sync_github_members(team, access_token, integration.organization_slug)
    except Exception as e:
        logger.error(f"Failed to sync GitHub members for team {team.slug}: {e}")
        messages.error(request, "Failed to sync GitHub members. Please try again.")
        return redirect("integrations:github_members", team_slug=team.slug)

    # Show success message with results
    msg = (
        f"Synced GitHub members: {result['created']} created, "
        f"{result['updated']} updated, {result['unchanged']} unchanged."
    )
    messages.success(request, msg)

    return redirect("integrations:github_members", team_slug=team.slug)


@team_admin_required
def github_member_toggle(request, team_slug, member_id):
    """Toggle a team member's active/inactive status.

    Allows admins to activate or deactivate team members.

    Requires team admin role and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.
        member_id: The ID of the team member to toggle.

    Returns:
        HttpResponse with partial template for HTMX or redirect for non-HTMX.
    """
    from apps.metrics.models import TeamMember

    # Require POST method
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Get member and toggle status
    try:
        member = TeamMember.objects.get(id=member_id, team=team)
    except TeamMember.DoesNotExist:
        messages.error(request, "Team member not found.")
        return redirect("integrations:github_members", team_slug=team.slug)

    member.is_active = not member.is_active
    member.save()

    # Check if HTMX request
    if request.htmx:
        # Return partial template for HTMX
        context = {"member": member}
        return render(request, "integrations/components/member_row.html", context)

    # Non-HTMX: redirect to members page
    return redirect("integrations:github_members", team_slug=team.slug)
