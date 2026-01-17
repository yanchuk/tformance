"""GitHub integration views."""

import logging

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.auth.oauth_state import FLOW_TYPE_GITHUB_APP_TEAM, create_oauth_state
from apps.integrations.models import GitHubAppInstallation, GitHubIntegration, IntegrationCredential
from apps.integrations.services import github_oauth
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.teams.decorators import login_and_team_required, team_admin_required
from apps.utils.analytics import track_event

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
def github_app_connect(request):
    """Initiate GitHub App installation for an existing team.

    Redirects to GitHub's App installation page with a signed state parameter
    containing the team_id for callback validation.

    Requires team admin role.
    """
    team = request.team

    # Check if already connected via GitHub App
    if GitHubAppInstallation.objects.filter(team=team, is_active=True).exists():
        messages.info(request, "GitHub App is already installed for this team.")
        return redirect("integrations:integrations_home")

    # Check if connected via OAuth (GitHubIntegration)
    if GitHubIntegration.objects.filter(team=team).exists():
        messages.info(request, "GitHub is already connected via OAuth. Disconnect first to switch to GitHub App.")
        return redirect("integrations:integrations_home")

    # Create state with team_id for CSRF protection and callback validation
    state = create_oauth_state(FLOW_TYPE_GITHUB_APP_TEAM, team_id=team.id)

    # Redirect to GitHub App installation page
    install_url = f"https://github.com/apps/{settings.GITHUB_APP_NAME}/installations/new?state={state}"
    return redirect(install_url)


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

    # Get integration info before deleting for tracking
    integration = GitHubIntegration.objects.filter(team=team).first()
    org_name = integration.organization_slug if integration else None

    # Delete GitHubIntegration (this will cascade delete the credential)
    GitHubIntegration.objects.filter(team=team).delete()

    # Also delete any orphaned credentials
    IntegrationCredential.objects.filter(team=team, provider=IntegrationCredential.PROVIDER_GITHUB).delete()

    # Track disconnection event
    track_event(
        request.user,
        "integration_disconnected",
        {
            "provider": "github",
            "org_name": org_name,
            "team_slug": team.slug,
        },
    )

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

        # Validate organization_id is a valid integer (security fix)
        try:
            org_id_int = int(organization_id)
        except (ValueError, TypeError):
            messages.error(request, "Invalid organization ID. Please try again.")
            return redirect("integrations:integrations_home")

        # Create GitHubIntegration using helper
        org_data = {"login": organization_slug, "id": org_id_int}
        _create_github_integration(team, credential, org_data)

        # Queue async member sync task
        _sync_github_members_after_connection(team)

        messages.success(request, f"Connected to {organization_slug}. Members syncing in background.")
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

    # Check if GitHub integration exists (OAuth or App installation)
    integration = GitHubIntegration.objects.filter(team=team).first()
    app_installation = GitHubAppInstallation.objects.filter(team=team, is_active=True).first()

    if not integration and not app_installation:
        messages.error(request, "Please connect GitHub first.")
        return redirect("integrations:integrations_home")

    # Query members with github_id populated
    members = TeamMember.objects.filter(team=team).exclude(github_id="")

    context = {
        "members": members,
        "integration": integration,
        "app_installation": app_installation,
    }

    return render(request, "integrations/github_members.html", context)


@team_admin_required
def github_members_sync(request):
    """Trigger manual re-sync of GitHub members.

    Queues an async Celery task and returns the progress partial immediately
    so the user sees feedback. HTMX polling will show progress updates.

    Requires team admin role and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team to sync members for.

    Returns:
        HttpResponse with member sync progress partial (for HTMX swap).
    """
    from django.utils import timezone

    from apps.integrations.tasks import sync_github_members_task

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

    # Set status to syncing immediately (so HTMX polling sees it)
    integration.member_sync_status = "syncing"
    integration.member_sync_started_at = timezone.now()
    integration.save(update_fields=["member_sync_status", "member_sync_started_at"])

    # Queue async task (non-blocking)
    sync_github_members_task.delay(integration.id)
    logger.info(f"Queued member sync task for team: {team.slug}")

    # Return progress partial for HTMX swap
    return render(request, "integrations/partials/member_sync_progress.html", {"integration": integration})


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

    Supports both OAuth and GitHub App installations.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team to display repos for.

    Returns:
        HttpResponse with the GitHub repos list or redirect if not connected.
    """
    from apps.integrations.models import TrackedRepository
    from apps.integrations.services.github_app import GitHubAppError, get_installation_repositories

    team = request.team

    # Check if GitHub integration exists (OAuth or App installation)
    integration = GitHubIntegration.objects.filter(team=team).first()
    app_installation = GitHubAppInstallation.objects.filter(team=team, is_active=True).first()

    if not integration and not app_installation:
        messages.error(request, "Please connect GitHub first.")
        return redirect("integrations:integrations_home")

    # Fetch repos from GitHub API
    # Prefer App installation if available (more limited, explicit scope)
    repos = []
    try:
        if app_installation:
            repos = get_installation_repositories(app_installation.installation_id)
        elif integration:
            repos = github_oauth.get_organization_repositories(
                integration.credential.access_token, integration.organization_slug
            )
    except (GitHubOAuthError, GitHubAppError) as e:
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

    # Sort repos: tracked ones first, then alphabetically by name
    repos.sort(key=lambda r: (not r["is_tracked"], r["name"].lower()))

    context = {
        "repos": repos,
        "integration": integration,
        "app_installation": app_installation,
        "github_oauth_connected": integration is not None,  # For webhook status display
    }

    return render(request, "integrations/github_repos.html", context)


@team_admin_required
def github_repo_toggle(request, repo_id):
    """Toggle repository tracking on/off.

    Allows admins to track or untrack repositories.
    Supports both OAuth and GitHub App installations.

    Requires team admin role and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.
        repo_id: The GitHub repository ID to toggle.

    Returns:
        HttpResponse with partial template for HTMX or redirect for non-HTMX.
    """
    from apps.integrations.models import TrackedRepository

    # Require POST method
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Check for GitHub integration (OAuth or App installation)
    integration = GitHubIntegration.objects.filter(team=team).first()
    app_installation = GitHubAppInstallation.objects.filter(team=team, is_active=True).first()

    if not integration and not app_installation:
        messages.error(request, "Please connect GitHub first.")
        return redirect("integrations:integrations_home")

    # Get full_name from POST data
    full_name = request.POST.get("full_name", "")

    # Get access token for webhook operations (OAuth only - App doesn't have write permissions)
    access_token = integration.credential.access_token if integration else None

    # Check if repo is already tracked
    webhook_id = None
    try:
        tracked_repo = TrackedRepository.objects.get(team=team, github_repo_id=repo_id)
        # Already tracked - delete webhook and repository
        if tracked_repo.webhook_id is not None and access_token:
            _delete_repository_webhook(access_token, tracked_repo.full_name, tracked_repo.webhook_id)
        tracked_repo.delete()
        is_tracked = False
    except TrackedRepository.DoesNotExist:
        # Not tracked - create it (only if full_name provided)
        if full_name:
            # Create tracked repository first (webhook_id will be set by async task)
            tracked_repo = TrackedRepository.objects.create(
                team=team,
                integration=integration,  # May be None for App-only
                app_installation=app_installation,  # May be None for OAuth-only
                github_repo_id=repo_id,
                full_name=full_name,
                is_active=True,
                webhook_id=None,  # Set asynchronously by task (OAuth only)
            )
            is_tracked = True

            # Queue async webhook creation (OAuth only - App doesn't have write permissions)
            if access_token:
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

            # Start onboarding pipeline if not already started
            # This triggers LLM analysis, metrics aggregation, and insights
            # after the initial sync completes
            if team.onboarding_pipeline_status == "not_started":
                from apps.integrations.onboarding_pipeline import start_onboarding_pipeline

                logger.info(f"Starting onboarding pipeline for team {team.slug} via repo toggle")
                start_onboarding_pipeline(team.id, [tracked_repo.id])
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


@login_and_team_required
def github_members_sync_progress(request):
    """Return member sync progress partial for HTMX polling.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.

    Returns:
        HttpResponse with member sync progress partial template.
    """
    team = request.team

    # Get GitHub integration
    try:
        integration = GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        return HttpResponseNotFound("GitHub integration not found")

    return render(request, "integrations/partials/member_sync_progress.html", {"integration": integration})
