"""GitHub integration views."""

import logging

from django.contrib import messages
from django.http import HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.integrations.models import GitHubIntegration, IntegrationCredential
from apps.integrations.services import github_oauth, member_sync
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.teams.decorators import login_and_team_required, team_admin_required

from .helpers import (
    _create_github_integration,
    _delete_repository_webhook,
    _sync_github_members_after_connection,
)

logger = logging.getLogger(__name__)


@team_admin_required
def github_connect(request):
    """Initiate GitHub OAuth flow for connecting a team's GitHub account.

    Redirects the user to GitHub's OAuth authorization page. On success,
    GitHub redirects back to the unified auth callback.

    Requires team admin role.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team connecting to GitHub.

    Returns:
        HttpResponse redirecting to GitHub OAuth authorization.
    """
    from urllib.parse import urlencode

    from django.conf import settings

    from apps.auth.oauth_state import FLOW_TYPE_INTEGRATION, create_oauth_state

    team = request.team

    # Check if already connected
    if GitHubIntegration.objects.filter(team=team).exists():
        messages.info(request, "GitHub is already connected to this team.")
        return redirect("integrations:integrations_home")

    # Build callback URL - use unified auth callback
    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))

    # Create state for CSRF protection with team_id
    state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=team.id)

    # Build GitHub authorization URL
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": callback_url,
        "scope": github_oauth.GITHUB_OAUTH_SCOPES,
        "state": state,
    }
    authorization_url = f"{github_oauth.GITHUB_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    # Redirect to GitHub
    return redirect(authorization_url)


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

    # Mark repos as tracked and include webhook_id, last_sync_at, tracked_repo_id, and sync status
    for repo in repos:
        tracked = tracked_repo_map.get(repo["id"])
        repo["is_tracked"] = tracked is not None
        repo["webhook_id"] = tracked.webhook_id if tracked else None
        repo["last_sync_at"] = tracked.last_sync_at if tracked else None
        repo["tracked_repo_id"] = tracked.id if tracked else None
        repo["sync_status"] = tracked.sync_status if tracked else None
        repo["sync_progress"] = tracked.sync_progress if tracked else 0
        repo["sync_prs_completed"] = tracked.sync_prs_completed if tracked else 0
        repo["sync_prs_total"] = tracked.sync_prs_total if tracked else None

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
            # Create tracked repository first (webhook_id will be set by async task)
            tracked_repo = TrackedRepository.objects.create(
                team=team,
                integration=integration,
                github_repo_id=repo_id,
                full_name=full_name,
                is_active=True,
                webhook_id=None,  # Set asynchronously by task
            )
            is_tracked = True

            # Queue async webhook creation (non-blocking)
            from apps.integrations.tasks import create_repository_webhook_task

            webhook_url = request.build_absolute_uri("/webhooks/github/")
            create_repository_webhook_task.delay(tracked_repo.id, webhook_url)

            # Parse days_back parameter
            days_back_str = request.POST.get("days_back", "")
            days_back = 30  # default
            if days_back_str:
                try:
                    parsed = int(days_back_str)
                    if parsed >= 0:
                        days_back = parsed
                except (ValueError, TypeError):
                    pass  # keep default

            # Queue background sync task (async, non-blocking)
            from apps.integrations.tasks import sync_repository_initial_task

            sync_repository_initial_task.delay(tracked_repo.id, days_back=days_back)
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

    Queues an async Celery task and returns the progress partial immediately
    so the user sees feedback. HTMX polling will show progress updates.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.
        repo_id: The ID of the tracked repository to sync.

    Returns:
        HttpResponse with sync progress partial (for HTMX swap).
    """
    from django.utils import timezone

    from apps.integrations.models import TrackedRepository
    from apps.integrations.tasks import sync_repository_manual_task

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Find the TrackedRepository
    try:
        tracked_repo = TrackedRepository.objects.get(team=team, id=repo_id)
    except TrackedRepository.DoesNotExist:
        return HttpResponseNotFound("Repository not found")

    # Set status to syncing immediately (so HTMX polling sees it)
    tracked_repo.sync_status = TrackedRepository.SYNC_STATUS_SYNCING
    tracked_repo.sync_started_at = timezone.now()
    tracked_repo.save(update_fields=["sync_status", "sync_started_at"])

    # Queue async task (non-blocking)
    sync_repository_manual_task.delay(repo_id)
    logger.info(f"Queued manual sync task for repository: {tracked_repo.full_name}")

    # Return progress partial for HTMX swap
    return render(request, "integrations/partials/sync_progress.html", {"repo": tracked_repo})


@login_and_team_required
def github_repo_sync_progress(request, repo_id):
    """Return sync progress partial for HTMX polling.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.
        repo_id: The ID of the tracked repository.

    Returns:
        HttpResponse with sync progress partial template.
    """
    from django.shortcuts import get_object_or_404

    from apps.integrations.models import TrackedRepository

    tracked_repo = get_object_or_404(TrackedRepository, id=repo_id, team=request.team)
    return render(request, "integrations/partials/sync_progress.html", {"repo": tracked_repo})
