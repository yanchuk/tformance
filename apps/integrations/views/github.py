"""GitHub integration views."""

import logging

from django.contrib import messages
from django.http import HttpResponseNotAllowed, HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django_ratelimit.decorators import ratelimit

from apps.integrations.models import GitHubIntegration, IntegrationCredential
from apps.integrations.services import github_oauth, github_sync, member_sync
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.teams.decorators import login_and_team_required, team_admin_required

from .helpers import (
    _create_github_integration,
    _create_integration_credential,
    _create_repository_webhook,
    _delete_repository_webhook,
    _sync_github_members_after_connection,
    _validate_oauth_callback,
)

logger = logging.getLogger(__name__)


@team_admin_required
def github_connect(request):
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
        return redirect("integrations:integrations_home")

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:github_callback"))

    # Get authorization URL
    authorization_url = github_oauth.get_authorization_url(team.id, callback_url)

    # Redirect to GitHub
    return redirect(authorization_url)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"])
@login_and_team_required
def github_callback(request):
    """Handle GitHub OAuth callback after user authorizes the app.

    Receives the authorization code from GitHub, exchanges it for an access token,
    and stores the token for the team.

    Rate limited to 10 requests per minute per IP to prevent abuse.

    Args:
        request: The HTTP request object containing OAuth callback parameters.
        team_slug: The slug of the team that initiated the OAuth flow.

    Returns:
        HttpResponse redirecting to organization selection or integrations home.
    """
    # Check if rate limited
    if getattr(request, "limited", False):
        messages.error(request, "Too many requests. Please wait and try again.")
        return redirect("integrations:integrations_home")

    team = request.team

    # Validate OAuth callback parameters
    code, error_response = _validate_oauth_callback(
        request, team, github_oauth.verify_oauth_state, GitHubOAuthError, "GitHub"
    )
    if error_response:
        return error_response

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:github_callback"))

    # Exchange code for token
    try:
        token_data = github_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
    except (GitHubOAuthError, KeyError, Exception) as e:
        logger.error(f"GitHub token exchange failed: {e}", exc_info=True)
        messages.error(request, "Failed to connect to GitHub. Please try again.")
        return redirect("integrations:integrations_home")

    # Get user's organizations
    try:
        orgs = github_oauth.get_user_organizations(access_token)
    except GitHubOAuthError as e:
        logger.error(f"Failed to get GitHub organizations: {e}", exc_info=True)
        messages.error(request, "Failed to get organizations from GitHub. Please try again.")
        return redirect("integrations:integrations_home")

    # Create credential for the team
    credential = _create_integration_credential(team, access_token, IntegrationCredential.PROVIDER_GITHUB, request.user)

    # If single org, create integration immediately
    if len(orgs) == 1:
        org = orgs[0]
        org_slug = org["login"]
        _create_github_integration(team, credential, org)

        # Sync members from GitHub
        member_count = _sync_github_members_after_connection(team, access_token, org_slug)

        messages.success(request, f"Connected to {org_slug}. Imported {member_count} members.")
        return redirect("integrations:integrations_home")

    # Multiple orgs - redirect to selection
    return redirect("integrations:github_select_org")


@team_admin_required
def github_disconnect(request):
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
    return redirect("integrations:integrations_home")


@login_and_team_required
def github_select_org(request):
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
        return redirect("integrations:integrations_home")

    if request.method == "POST":
        # Get selected org from form
        organization_slug = request.POST.get("organization_slug")
        organization_id = request.POST.get("organization_id")

        # Create GitHubIntegration using helper
        org_data = {"login": organization_slug, "id": int(organization_id)}
        _create_github_integration(team, credential, org_data)

        # Sync members from GitHub (EncryptedTextField auto-decrypts)
        member_count = _sync_github_members_after_connection(team, credential.access_token, organization_slug)

        messages.success(request, f"Connected to {organization_slug}. Imported {member_count} members.")
        return redirect("integrations:integrations_home")

    # GET request - show organization selection form
    try:
        # EncryptedTextField auto-decrypts access_token
        orgs = github_oauth.get_user_organizations(credential.access_token)
    except (GitHubOAuthError, Exception):
        messages.error(request, "Failed to fetch organizations from GitHub.")
        return redirect("integrations:integrations_home")

    context = {
        "organizations": orgs,
    }

    return render(request, "integrations/select_org.html", context)


@login_and_team_required
def github_members(request):
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
        return redirect("integrations:integrations_home")

    # Query members with github_id populated
    members = TeamMember.objects.filter(team=team).exclude(github_id="")

    context = {
        "members": members,
    }

    return render(request, "integrations/github_members.html", context)


@team_admin_required
def github_members_sync(request):
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
        return redirect("integrations:integrations_home")

    # Call sync service (EncryptedTextField auto-decrypts access_token)
    try:
        result = member_sync.sync_github_members(
            team, integration.credential.access_token, integration.organization_slug
        )
    except Exception as e:
        logger.error(f"Failed to sync GitHub members for team {team.slug}: {e}")
        messages.error(request, "Failed to sync GitHub members. Please try again.")
        return redirect("integrations:github_members")

    # Show success message with results
    msg = (
        f"Synced GitHub members: {result['created']} created, "
        f"{result['updated']} updated, {result['unchanged']} unchanged."
    )
    messages.success(request, msg)

    return redirect("integrations:github_members")


@team_admin_required
def github_member_toggle(request, member_id):
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
        return redirect("integrations:github_members")

    member.is_active = not member.is_active
    member.save()

    # Check if HTMX request
    if request.htmx:
        # Return partial template for HTMX
        context = {"member": member}
        return render(request, "integrations/components/member_row.html", context)

    # Non-HTMX: redirect to members page
    return redirect("integrations:github_members")


@login_and_team_required
def github_repos(request):
    """Display list of GitHub repositories for the organization.

    Shows all repositories from the connected GitHub organization and marks
    which ones are currently being tracked.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team to display repos for.

    Returns:
        HttpResponse with the GitHub repos list or redirect if not connected.
    """
    from apps.integrations.models import TrackedRepository

    team = request.team

    # Check if GitHub integration exists
    try:
        integration = GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        messages.error(request, "Please connect GitHub first.")
        return redirect("integrations:integrations_home")

    # Fetch repos from GitHub API (EncryptedTextField auto-decrypts access_token)
    try:
        repos = github_oauth.get_organization_repositories(
            integration.credential.access_token, integration.organization_slug
        )
    except GitHubOAuthError as e:
        logger.error(f"Failed to fetch GitHub repositories: {e}", exc_info=True)
        messages.error(request, "Failed to fetch repositories from GitHub. Please try again.")
        return redirect("integrations:integrations_home")

    # Get tracked repos with webhook_id
    tracked_repos = TrackedRepository.objects.filter(team=team)
    tracked_repo_map = {tr.github_repo_id: tr for tr in tracked_repos}

    # Mark repos as tracked and include webhook_id, last_sync_at, and tracked_repo_id
    for repo in repos:
        tracked = tracked_repo_map.get(repo["id"])
        repo["is_tracked"] = tracked is not None
        repo["webhook_id"] = tracked.webhook_id if tracked else None
        repo["last_sync_at"] = tracked.last_sync_at if tracked else None
        repo["tracked_repo_id"] = tracked.id if tracked else None

    context = {
        "repos": repos,
        "integration": integration,
    }

    return render(request, "integrations/github_repos.html", context)


@team_admin_required
def github_repo_toggle(request, repo_id):
    """Toggle repository tracking on/off.

    Allows admins to track or untrack repositories.

    Requires team admin role and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.
        repo_id: The GitHub repository ID to toggle.

    Returns:
        HttpResponse with partial template for HTMX or redirect for non-HTMX.
    """
    from django.shortcuts import get_object_or_404

    from apps.integrations.models import TrackedRepository

    # Require POST method
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Get GitHub integration or return 404
    integration = get_object_or_404(GitHubIntegration, team=team)

    # Get full_name from POST data
    full_name = request.POST.get("full_name", "")

    # EncryptedTextField auto-decrypts access_token
    access_token = integration.credential.access_token

    # Check if repo is already tracked
    webhook_id = None
    try:
        tracked_repo = TrackedRepository.objects.get(team=team, github_repo_id=repo_id)
        # Already tracked - delete webhook and repository
        if tracked_repo.webhook_id is not None:
            _delete_repository_webhook(access_token, tracked_repo.full_name, tracked_repo.webhook_id)
        tracked_repo.delete()
        is_tracked = False
    except TrackedRepository.DoesNotExist:
        # Not tracked - create it (only if full_name provided)
        if full_name:
            # Build webhook URL and create webhook
            webhook_url = request.build_absolute_uri("/webhooks/github/")
            webhook_id = _create_repository_webhook(access_token, full_name, webhook_url, integration.webhook_secret)

            # Create tracked repository with webhook_id (or None if webhook creation failed)
            tracked_repo = TrackedRepository.objects.create(
                team=team,
                integration=integration,
                github_repo_id=repo_id,
                full_name=full_name,
                is_active=True,
                webhook_id=webhook_id,
            )
            is_tracked = True

            # Trigger historical sync after tracking
            try:
                github_sync.sync_repository_history(tracked_repo)
            except Exception as e:
                logger.error(f"Failed to sync historical data for {full_name}: {e}")
                # Don't fail the toggle - repo is tracked, sync can happen later
        else:
            is_tracked = False

    # Build repo data for template
    # Parse name from full_name (e.g., "acme-corp/repo-1" -> "repo-1")
    name = full_name.split("/")[-1] if full_name else ""

    # Get tracked_repo_id and last_sync_at if repo is tracked
    tracked_repo_id = None
    last_sync_at = None
    if is_tracked:
        try:
            tracked_repo = TrackedRepository.objects.get(team=team, github_repo_id=repo_id)
            tracked_repo_id = tracked_repo.id
            last_sync_at = tracked_repo.last_sync_at
        except TrackedRepository.DoesNotExist:
            pass

    context = {
        "repo": {
            "id": repo_id,
            "name": name,
            "full_name": full_name,
            "description": "",  # Not available after toggle
            "is_tracked": is_tracked,
            "webhook_id": webhook_id,
            "tracked_repo_id": tracked_repo_id,
            "last_sync_at": last_sync_at,
        }
    }

    # Check if HTMX request
    if request.htmx:
        # Return partial template for HTMX
        return render(request, "integrations/components/repo_card.html", context)

    # Non-HTMX: redirect to repos page
    return redirect("integrations:github_repos")


@login_and_team_required
def github_repo_sync(request, repo_id):
    """Manually trigger historical sync for a tracked repository.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.
        repo_id: The ID of the tracked repository to sync.

    Returns:
        JsonResponse with sync results or error.
    """
    from apps.integrations.models import TrackedRepository

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Find the TrackedRepository
    try:
        tracked_repo = TrackedRepository.objects.get(team=team, id=repo_id)
    except TrackedRepository.DoesNotExist:
        return HttpResponseNotFound("Repository not found")

    # Trigger sync
    try:
        result = github_sync.sync_repository_history(tracked_repo)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Failed to sync repository {tracked_repo.full_name}: {e}", exc_info=True)
        return JsonResponse({"error": "Failed to sync repository. Please try again."}, status=500)
