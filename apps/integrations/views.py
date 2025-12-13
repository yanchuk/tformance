"""Views for managing external integrations (GitHub, Jira, Slack)."""

import logging
import secrets

from django.contrib import messages
from django.http import HttpResponseNotAllowed, HttpResponseNotFound, JsonResponse
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django_ratelimit.decorators import ratelimit

from apps.integrations.models import (
    GitHubIntegration,
    IntegrationCredential,
    JiraIntegration,
    SlackIntegration,
    TrackedJiraProject,
)
from apps.integrations.services import (
    github_oauth,
    github_sync,
    github_webhooks,
    jira_client,
    jira_oauth,
    member_sync,
    slack_oauth,
)
from apps.integrations.services.encryption import decrypt, encrypt
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.integrations.services.jira_client import JiraClientError
from apps.integrations.services.jira_oauth import JiraOAuthError
from apps.integrations.services.slack_oauth import SlackOAuthError
from apps.metrics.models import TeamMember
from apps.teams.decorators import login_and_team_required, team_admin_required

logger = logging.getLogger(__name__)


def _create_repository_webhook(access_token, repo_full_name, webhook_url, secret):
    """Create a GitHub webhook for a repository.

    Attempts to create a webhook and returns the webhook ID. If creation fails,
    logs the error and returns None (graceful degradation).

    Args:
        access_token: The GitHub OAuth access token.
        repo_full_name: The full name of the repository (e.g., "org/repo").
        webhook_url: The URL for the webhook endpoint.
        secret: The webhook secret for signature verification.

    Returns:
        int or None: The webhook ID if successful, None if creation failed.
    """
    try:
        return github_webhooks.create_repository_webhook(
            access_token=access_token,
            repo_full_name=repo_full_name,
            webhook_url=webhook_url,
            secret=secret,
        )
    except GitHubOAuthError as e:
        logger.error(f"Failed to create webhook for {repo_full_name}: {e}")
        return None


def _delete_repository_webhook(access_token, repo_full_name, webhook_id):
    """Delete a GitHub webhook from a repository.

    Attempts to delete a webhook. If deletion fails, logs the error but doesn't
    raise an exception (graceful degradation).

    Args:
        access_token: The GitHub OAuth access token.
        repo_full_name: The full name of the repository (e.g., "org/repo").
        webhook_id: The ID of the webhook to delete.
    """
    try:
        github_webhooks.delete_repository_webhook(
            access_token=access_token,
            repo_full_name=repo_full_name,
            webhook_id=webhook_id,
        )
    except GitHubOAuthError as e:
        logger.error(f"Failed to delete webhook for {repo_full_name}: {e}")


def _create_integration_credential(team, access_token, provider, user):
    """Create an encrypted integration credential for a team.

    Args:
        team: The team to create the credential for.
        access_token: The OAuth access token (will be encrypted).
        provider: The provider type (e.g., PROVIDER_GITHUB, PROVIDER_JIRA).
        user: The user who connected the integration.

    Returns:
        IntegrationCredential: The created credential object.
    """
    encrypted_token = encrypt(access_token)
    return IntegrationCredential.objects.create(
        team=team,
        provider=provider,
        access_token=encrypted_token,
        connected_by=user,
    )


def _validate_oauth_callback(request, team, verify_state_func, oauth_error_class, provider_name):
    """Validate OAuth callback parameters and state.

    Args:
        request: The HTTP request object.
        team: The team object.
        verify_state_func: Function to verify the state parameter.
        oauth_error_class: The OAuth error exception class to catch.
        provider_name: The name of the provider (e.g., "GitHub", "Jira").

    Returns:
        tuple: (code, None) if validation succeeds, (None, redirect_response) if validation fails.
    """
    # Check for OAuth denial
    if request.GET.get("error") == "access_denied":
        messages.error(request, f"{provider_name} authorization was cancelled.")
        return None, redirect("integrations:integrations_home")

    # Get code and state from query params
    code = request.GET.get("code")
    state = request.GET.get("state")

    # Validate parameters
    if not code:
        messages.error(request, f"Missing authorization code from {provider_name}.")
        return None, redirect("integrations:integrations_home")

    if not state:
        messages.error(request, f"Missing state parameter from {provider_name}.")
        return None, redirect("integrations:integrations_home")

    # Verify state
    try:
        state_data = verify_state_func(state)
        team_id = state_data.get("team_id")

        # Verify team_id matches current team
        if team_id != team.id:
            messages.error(request, "Invalid state parameter.")
            return None, redirect("integrations:integrations_home")
    except oauth_error_class:
        messages.error(request, "Invalid state parameter.")
        return None, redirect("integrations:integrations_home")

    return code, None


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
def integrations_home(request):
    """Display the integrations management page for a team.

    Shows the status of all integrations (GitHub, Jira, Slack) and provides
    connection/disconnection options.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team for which to display integrations.

    Returns:
        HttpResponse with the integrations page content.
    """
    from apps.integrations.models import TrackedJiraProject, TrackedRepository

    team = request.team

    # Check if GitHub integration exists
    try:
        github_integration = GitHubIntegration.objects.get(team=team)
        github_connected = True
        # Count members with GitHub IDs
        member_count = TeamMember.objects.filter(team=team).exclude(github_id="").count()
        # Count tracked repositories
        tracked_repo_count = TrackedRepository.objects.filter(team=team).count()
    except GitHubIntegration.DoesNotExist:
        github_integration = None
        github_connected = False
        member_count = 0
        tracked_repo_count = 0

    # Check if Jira integration exists
    try:
        jira_integration = JiraIntegration.objects.get(team=team)
        jira_connected = True
        # Count tracked Jira projects
        tracked_project_count = TrackedJiraProject.objects.filter(team=team).count()
    except JiraIntegration.DoesNotExist:
        jira_integration = None
        jira_connected = False
        tracked_project_count = 0

    # Check if Slack integration exists
    try:
        slack_integration = SlackIntegration.objects.get(team=team)
        slack_connected = True
    except SlackIntegration.DoesNotExist:
        slack_integration = None
        slack_connected = False

    context = {
        "github_connected": github_connected,
        "github_integration": github_integration,
        "member_count": member_count,
        "tracked_repo_count": tracked_repo_count,
        "jira_connected": jira_connected,
        "jira_integration": jira_integration,
        "tracked_project_count": tracked_project_count,
        "slack_connected": slack_connected,
        "slack_integration": slack_integration,
        "active_tab": "integrations",
    }

    template = "integrations/home.html#page-content" if request.htmx else "integrations/home.html"
    return TemplateResponse(request, template, context)


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

        # Sync members from GitHub
        access_token = decrypt(credential.access_token)
        member_count = _sync_github_members_after_connection(team, access_token, organization_slug)

        messages.success(request, f"Connected to {organization_slug}. Imported {member_count} members.")
        return redirect("integrations:integrations_home")

    # GET request - show organization selection form
    try:
        access_token = decrypt(credential.access_token)
        orgs = github_oauth.get_user_organizations(access_token)
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

    # Decrypt access token
    access_token = decrypt(integration.credential.access_token)

    # Call sync service
    try:
        result = member_sync.sync_github_members(team, access_token, integration.organization_slug)
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

    # Decrypt access token
    access_token = decrypt(integration.credential.access_token)

    # Fetch repos from GitHub API
    try:
        repos = github_oauth.get_organization_repositories(access_token, integration.organization_slug)
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

    # Decrypt access token for webhook operations
    access_token = decrypt(integration.credential.access_token)

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


@team_admin_required
def jira_connect(request):
    """Initiate Jira OAuth flow for connecting a team's Jira account.

    Redirects the user to Atlassian's OAuth authorization page. On success,
    Atlassian redirects back to jira_callback.

    Requires team admin role.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team connecting to Jira.

    Returns:
        HttpResponse redirecting to Atlassian OAuth authorization.
    """
    team = request.team

    # Check if already connected
    if JiraIntegration.objects.filter(team=team).exists():
        messages.info(request, "Jira is already connected to this team.")
        return redirect("integrations:integrations_home")

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:jira_callback"))

    # Get authorization URL
    authorization_url = jira_oauth.get_authorization_url(team.id, callback_url)

    # Redirect to Atlassian
    return redirect(authorization_url)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"])
@login_and_team_required
def jira_callback(request):
    """Handle Jira OAuth callback after user authorizes the app.

    Receives the authorization code from Atlassian, exchanges it for an access token,
    and stores the token for the team.

    Rate limited to 10 requests per minute per IP to prevent abuse.

    Args:
        request: The HTTP request object containing OAuth callback parameters.
        team_slug: The slug of the team that initiated the OAuth flow.

    Returns:
        HttpResponse redirecting to site selection or integrations home.
    """
    # Check if rate limited
    if getattr(request, "limited", False):
        messages.error(request, "Too many requests. Please wait and try again.")
        return redirect("integrations:integrations_home")

    team = request.team

    # Validate OAuth callback parameters
    code, error_response = _validate_oauth_callback(
        request, team, jira_oauth.verify_oauth_state, JiraOAuthError, "Jira"
    )
    if error_response:
        return error_response

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:jira_callback"))

    # Exchange code for token
    try:
        token_data = jira_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
    except (JiraOAuthError, KeyError, Exception) as e:
        logger.error(f"Jira token exchange failed: {e}", exc_info=True)
        messages.error(request, "Failed to connect to Jira. Please try again.")
        return redirect("integrations:integrations_home")

    # Get accessible resources (Jira sites)
    try:
        sites = jira_oauth.get_accessible_resources(access_token)
    except JiraOAuthError as e:
        logger.error(f"Failed to get Jira sites: {e}", exc_info=True)
        messages.error(request, "Failed to get accessible Jira sites. Please try again.")
        return redirect("integrations:integrations_home")

    # Create encrypted credential for the team
    credential = _create_integration_credential(team, access_token, IntegrationCredential.PROVIDER_JIRA, request.user)

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

        messages.success(request, f"Connected to Jira site: {site['name']}")
        return redirect("integrations:integrations_home")

    # Multiple sites - store in session and redirect to selection
    request.session["jira_sites"] = sites
    return redirect("integrations:jira_select_site")


@team_admin_required
def jira_disconnect(request):
    """Disconnect Jira integration for a team.

    Removes the stored Jira OAuth token and any associated data for the team.

    Requires team admin role and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team disconnecting from Jira.

    Returns:
        HttpResponse redirecting to integrations home with success message.
    """
    # Require POST method
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Delete JiraIntegration (this will cascade delete the credential)
    JiraIntegration.objects.filter(team=team).delete()

    # Also delete any orphaned credentials
    IntegrationCredential.objects.filter(team=team, provider=IntegrationCredential.PROVIDER_JIRA).delete()

    messages.success(request, "Jira integration disconnected successfully.")
    return redirect("integrations:integrations_home")


@login_and_team_required
def jira_select_site(request):
    """Allow user to select which Jira site to sync data from.

    Displays a list of Jira sites the authenticated user has access to,
    allowing them to choose which one to link to the team.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team selecting a Jira site.

    Returns:
        HttpResponse with site selection form or redirect after POST.
    """
    team = request.team

    # Get credential for the team
    try:
        credential = IntegrationCredential.objects.get(team=team, provider=IntegrationCredential.PROVIDER_JIRA)
    except IntegrationCredential.DoesNotExist:
        messages.error(request, "No Jira credential found. Please try connecting again.")
        return redirect("integrations:integrations_home")

    if request.method == "POST":
        # Get selected site from form
        cloud_id = request.POST.get("cloud_id")
        site_name = request.POST.get("site_name")
        site_url = request.POST.get("site_url")

        # Create JiraIntegration
        JiraIntegration.objects.create(
            team=team,
            credential=credential,
            cloud_id=cloud_id,
            site_name=site_name,
            site_url=site_url,
        )

        messages.success(request, f"Connected to Jira site: {site_name}")
        return redirect("integrations:integrations_home")

    # GET request - show site selection form
    try:
        access_token = decrypt(credential.access_token)
        sites = jira_oauth.get_accessible_resources(access_token)
    except (JiraOAuthError, Exception):
        messages.error(request, "Failed to fetch sites from Jira.")
        return redirect("integrations:integrations_home")

    context = {
        "sites": sites,
    }

    return render(request, "integrations/jira_select_site.html", context)


@team_admin_required
def jira_projects_list(request):
    """Display list of Jira projects for the team.

    Shows all projects from the connected Jira site and marks
    which ones are currently being tracked.

    Requires team admin role.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team to display projects for.

    Returns:
        HttpResponse with the Jira projects list or redirect if not connected.
    """
    team = request.team

    # Check if Jira integration exists
    try:
        jira_integration = JiraIntegration.objects.get(team=team)
    except JiraIntegration.DoesNotExist:
        messages.error(request, "Please connect Jira first.")
        return redirect("integrations:integrations_home")

    # Fetch projects from Jira API
    try:
        jira_projects = jira_client.get_accessible_projects(jira_integration.credential)
    except JiraClientError as e:
        messages.error(request, f"Failed to fetch projects: {str(e)}")
        return redirect("integrations:integrations_home")

    # Get tracked projects for this team
    tracked_project_ids = set(TrackedJiraProject.objects.filter(team=team).values_list("jira_project_id", flat=True))

    # Mark projects as tracked
    for project in jira_projects:
        project["is_tracked"] = project["id"] in tracked_project_ids

    context = {
        "projects": jira_projects,
        "jira_integration": jira_integration,
    }

    return render(request, "integrations/jira_projects_list.html", context)


@team_admin_required
def jira_project_toggle(request):
    """Toggle project tracking on/off.

    Allows admins to track or untrack Jira projects.

    Requires team admin role and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.

    Returns:
        JsonResponse with success or error message.
    """
    from django.shortcuts import get_object_or_404

    # Require POST method
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team

    # Get required fields
    action = request.POST.get("action")
    project_id = request.POST.get("project_id")
    project_key = request.POST.get("project_key")
    name = request.POST.get("name")

    # Validate required fields
    if not all([action, project_id, project_key, name]):
        return JsonResponse({"error": "Missing required fields"}, status=400)

    # Get Jira integration or return 404
    jira_integration = get_object_or_404(JiraIntegration, team=team)

    if action == "add":
        # Create or get tracked project
        TrackedJiraProject.objects.get_or_create(
            team=team,
            jira_project_id=project_id,
            defaults={
                "integration": jira_integration,
                "jira_project_key": project_key,
                "name": name,
            },
        )
        return JsonResponse({"success": True, "message": f"Now tracking {project_key}"})

    elif action == "remove":
        # Delete tracked project
        TrackedJiraProject.objects.filter(team=team, jira_project_id=project_id).delete()
        return JsonResponse({"success": True, "message": f"Stopped tracking {project_key}"})

    return JsonResponse({"error": "Invalid action"}, status=400)


@team_admin_required
def slack_connect(request):
    """Initiate Slack OAuth flow for connecting a team's Slack workspace.

    Redirects the user to Slack's OAuth authorization page. On success,
    Slack redirects back to slack_callback.

    Requires team admin role.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team connecting to Slack.

    Returns:
        HttpResponse redirecting to Slack OAuth authorization.
    """
    team = request.team

    # Check if already connected
    if SlackIntegration.objects.filter(team=team).exists():
        messages.info(request, "Slack is already connected to this team.")
        return redirect("integrations:integrations_home")

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:slack_callback"))

    # Get authorization URL
    authorization_url = slack_oauth.get_authorization_url(team.id, callback_url)

    # Redirect to Slack
    return redirect(authorization_url)


@ratelimit(key="ip", rate="10/m", method=["GET", "POST"])
@login_and_team_required
def slack_callback(request):
    """Handle Slack OAuth callback after user authorizes the app.

    Receives the authorization code from Slack, exchanges it for an access token,
    and stores the token for the team.

    Rate limited to 10 requests per minute per IP to prevent abuse.

    Args:
        request: The HTTP request object containing OAuth callback parameters.
        team_slug: The slug of the team that initiated the OAuth flow.

    Returns:
        HttpResponse redirecting to integrations home.
    """
    # Check if rate limited
    if getattr(request, "limited", False):
        messages.error(request, "Too many requests. Please wait and try again.")
        return redirect("integrations:integrations_home")

    team = request.team

    # Validate OAuth callback parameters
    code, error_response = _validate_oauth_callback(
        request, team, slack_oauth.verify_slack_oauth_state, SlackOAuthError, "Slack"
    )
    if error_response:
        return error_response

    # Build callback URL
    callback_url = request.build_absolute_uri(reverse("integrations:slack_callback"))

    # Exchange code for token
    try:
        token_data = slack_oauth.exchange_code_for_token(code, callback_url)
        access_token = token_data["access_token"]
        bot_user_id = token_data["bot_user_id"]
        workspace_id = token_data["team"]["id"]
        workspace_name = token_data["team"]["name"]
    except (SlackOAuthError, KeyError, Exception) as e:
        logger.error(f"Slack token exchange failed: {e}", exc_info=True)
        messages.error(request, "Failed to connect to Slack. Please try again.")
        return redirect("integrations:integrations_home")

    # Check if this workspace is already connected (update if so)
    existing_integration = SlackIntegration.objects.filter(team=team, workspace_id=workspace_id).first()

    if existing_integration:
        # Update existing integration
        existing_integration.workspace_name = workspace_name
        existing_integration.bot_user_id = bot_user_id
        existing_integration.save()

        # Update credential
        existing_integration.credential.access_token = encrypt(access_token)
        existing_integration.credential.connected_by = request.user
        existing_integration.credential.save()

        messages.success(request, f"Reconnected to Slack workspace: {workspace_name}")
    else:
        # Create credential for the team
        credential = _create_integration_credential(
            team, access_token, IntegrationCredential.PROVIDER_SLACK, request.user
        )

        # Create SlackIntegration
        SlackIntegration.objects.create(
            team=team,
            credential=credential,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            bot_user_id=bot_user_id,
        )

        messages.success(request, f"Connected to Slack workspace: {workspace_name}")

    return redirect("integrations:integrations_home")


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
