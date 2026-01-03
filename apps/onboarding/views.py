"""Views for the onboarding wizard.

Users without a team are directed here after signup to:
1. Connect their GitHub account
2. Select their organization (which creates the team)
3. Select repositories to track
4. Optionally connect Jira and Slack
"""

import logging
import secrets
from datetime import UTC, datetime

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.integrations.models import GitHubIntegration, IntegrationCredential, TrackedRepository
from apps.integrations.onboarding_pipeline import start_onboarding_pipeline
from apps.integrations.services import github_oauth, member_sync
from apps.integrations.services.encryption import decrypt, encrypt
from apps.metrics.models import DailyInsight, PullRequest, WeeklyMetrics
from apps.onboarding.services.notifications import send_welcome_email
from apps.teams.helpers import get_next_unique_team_slug
from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN
from apps.utils.analytics import group_identify, track_event

logger = logging.getLogger(__name__)

# Session keys for onboarding state
ONBOARDING_TOKEN_KEY = "onboarding_github_token"
ONBOARDING_ORGS_KEY = "onboarding_github_orgs"
ONBOARDING_SELECTED_ORG_KEY = "onboarding_selected_org"


@login_required
def onboarding_start(request):
    """Start of onboarding wizard - prompts user to connect GitHub."""
    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        # Redirect to /app/ which auto-selects the team
        return redirect("web:home")

    # Check if user has a GitHub social account (signed up via GitHub OAuth)
    has_github_social = SocialAccount.objects.filter(user=request.user, provider="github").exists()

    return render(
        request,
        "onboarding/start.html",
        {"page_title": _("Connect GitHub"), "step": 1, "has_github_social": has_github_social},
    )


@login_required
def github_connect(request):
    """Initiate GitHub OAuth flow for onboarding."""
    from urllib.parse import urlencode

    from apps.auth.oauth_state import FLOW_TYPE_ONBOARDING, create_oauth_state

    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        # Redirect to /app/ which auto-selects the team
        return redirect("web:home")

    # Build callback URL - use unified auth callback
    callback_url = request.build_absolute_uri(reverse("tformance_auth:github_callback"))

    # Create state for CSRF protection
    state = create_oauth_state(FLOW_TYPE_ONBOARDING)

    # Build GitHub authorization URL
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": callback_url,
        "scope": github_oauth.GITHUB_OAUTH_SCOPES,
        "state": state,
    }
    auth_url = f"{github_oauth.GITHUB_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    return redirect(auth_url)


@login_required
def github_app_install(request):
    """Initiate GitHub App installation flow.

    Redirects to GitHub's App installation page with a signed state parameter
    containing the user_id for callback validation.

    If the user already has a team, redirects to the home page instead.
    """
    from apps.auth.oauth_state import FLOW_TYPE_GITHUB_APP_INSTALL, create_oauth_state

    # If user already has a team, redirect to dashboard
    if request.user.teams.exists():
        return redirect("web:home")

    # Create state with user_id for CSRF protection and callback validation
    state = create_oauth_state(FLOW_TYPE_GITHUB_APP_INSTALL, user_id=request.user.id)

    # Redirect to GitHub App install
    install_url = f"https://github.com/apps/{settings.GITHUB_APP_NAME}/installations/new?state={state}"
    return redirect(install_url)


@login_required
def github_app_callback(request):
    """Handle GitHub App installation callback.

    This view processes the callback from GitHub after a user installs the App:
    1. Validates the state parameter (signature, flow type, user_id match)
    2. Fetches installation details from GitHub API
    3. Creates or updates GitHubAppInstallation record
    4. Creates team if needed, or links to existing team
    5. Adds user as team admin if not already a member
    6. Syncs organization members
    7. Redirects to repository selection

    Query Parameters:
        installation_id: GitHub App installation ID (required)
        setup_action: "install" or "update" (optional)
        state: Signed OAuth state parameter (required)
    """
    from django.utils.text import slugify

    from apps.auth.oauth_state import FLOW_TYPE_GITHUB_APP_INSTALL, OAuthStateError, verify_oauth_state
    from apps.integrations.models import GitHubAppInstallation
    from apps.integrations.services.github_app import GitHubAppError, get_installation

    installation_id = request.GET.get("installation_id")

    # Validate installation_id
    if not installation_id:
        messages.error(request, _("Installation failed - no installation ID received from GitHub."))
        return redirect("onboarding:start")

    # Validate state parameter - check signature, expiry, flow type, and user match
    state = request.GET.get("state")
    try:
        state_data = verify_oauth_state(state)
    except OAuthStateError as e:
        logger.warning(f"Invalid OAuth state in GitHub App callback: {e}")
        messages.error(request, _("Invalid or expired state. Please try again."))
        return redirect("onboarding:start")

    # Verify flow type and user match
    if state_data.get("type") != FLOW_TYPE_GITHUB_APP_INSTALL or state_data.get("user_id") != request.user.id:
        logger.warning(
            f"State mismatch in GitHub App callback: type={state_data.get('type')}, "
            f"state_user={state_data.get('user_id')}, request_user={request.user.id}"
        )
        messages.error(request, _("Invalid state. Please try again."))
        return redirect("onboarding:start")

    # Fetch installation details from GitHub API
    try:
        installation_data = get_installation(int(installation_id))
    except GitHubAppError as e:
        logger.error(f"Failed to fetch GitHub App installation {installation_id}: {e}")
        messages.error(request, _("Failed to fetch installation details from GitHub. Please try again."))
        return redirect("onboarding:start")

    # Check if installation already exists (update scenario)
    existing_installation = GitHubAppInstallation.objects.filter(installation_id=int(installation_id)).first()

    account_login = installation_data["account"]["login"]

    if existing_installation:
        # Update existing installation - use its existing team
        team = existing_installation.team
        existing_installation.account_type = installation_data["account"]["type"]
        existing_installation.account_login = account_login
        existing_installation.account_id = installation_data["account"]["id"]
        existing_installation.permissions = installation_data.get("permissions", {})
        existing_installation.events = installation_data.get("events", [])
        existing_installation.repository_selection = installation_data.get("repository_selection", "selected")
        existing_installation.is_active = True
        existing_installation.save()
    else:
        # Find or create team for new installation
        team_slug = slugify(account_login)
        team, created = Team.objects.get_or_create(slug=team_slug, defaults={"name": account_login})

        # Create GitHubAppInstallation
        GitHubAppInstallation.objects.create(
            installation_id=int(installation_id),
            team=team,
            account_type=installation_data["account"]["type"],
            account_login=account_login,
            account_id=installation_data["account"]["id"],
            permissions=installation_data.get("permissions", {}),
            events=installation_data.get("events", []),
            repository_selection=installation_data.get("repository_selection", "selected"),
            is_active=True,
        )

    # Add user to team if not already
    if not team.members.filter(id=request.user.id).exists():
        Membership.objects.create(team=team, user=request.user, role=ROLE_ADMIN)

    # Sync GitHub members (fail silently to not block onboarding)
    try:
        member_sync.sync_github_members(team)
    except Exception as e:
        logger.warning(f"Failed to sync GitHub members during onboarding: {e}")

    return redirect("onboarding:select_repos")


@login_required
def select_organization(request):
    """Select which GitHub organization to use for the team."""
    # If user has a team that completed onboarding, redirect to dashboard
    existing_team = request.user.teams.first()
    if existing_team and existing_team.onboarding_complete:
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
        # Create team from org name (onboarding_complete=False until they finish)
        team_name = org["login"]
        team_slug = get_next_unique_team_slug(team_name)
        team = Team.objects.create(name=team_name, slug=team_slug, onboarding_complete=False)

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

        # Send welcome email (fail silently to not block onboarding)
        try:
            send_welcome_email(team, request.user)
        except Exception as e:
            logger.warning(f"Failed to send welcome email during onboarding: {e}")

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
    from apps.integrations.models import GitHubAppInstallation

    # Get user's team
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Check if GitHub is connected (OAuth or App)
    integration = None
    app_installation = None
    try:
        integration = GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        # Check for GitHub App installation
        app_installation = GitHubAppInstallation.objects.filter(team=team, is_active=True).first()
        if not app_installation:
            messages.error(request, _("GitHub not connected."))
            return redirect("onboarding:start")

    if request.method == "POST":
        # Get selected repository IDs from form
        selected_repo_ids = request.POST.getlist("repos")

        if selected_repo_ids:
            # Fetch repos from GitHub to get full_name for each
            try:
                all_repos = github_oauth.get_organization_repositories(
                    integration.credential.access_token,
                    integration.organization_slug,
                    exclude_archived=True,
                )
                repo_map = {str(repo["id"]): repo for repo in all_repos}

                # Create TrackedRepository for each selected repo
                for repo_id in selected_repo_ids:
                    repo_data = repo_map.get(repo_id)
                    if repo_data:
                        TrackedRepository.objects.get_or_create(
                            team=team,
                            github_repo_id=int(repo_id),
                            defaults={
                                "integration": integration,
                                "full_name": repo_data["full_name"],
                                "is_active": True,
                            },
                        )
            except Exception as e:
                logger.error(f"Failed to create tracked repos during onboarding: {e}")
                messages.error(request, _("Failed to save repository selection. Please try again."))
                return redirect("onboarding:select_repos")

        # Start sync in background and continue to next step
        repo_ids = list(TrackedRepository.objects.filter(team=team).values_list("id", flat=True))
        if repo_ids:
            # Start the full onboarding pipeline (sync + LLM + metrics + insights)
            task = start_onboarding_pipeline(team.id, repo_ids)
            # Store task_id in session for progress tracking
            request.session["sync_task_id"] = task.id
            logger.info(f"Started onboarding pipeline task {task.id} for team {team.name}")

        # Track step completion
        track_event(
            request.user,
            "onboarding_step_completed",
            {"step": "repos", "team_slug": team.slug, "repos_count": len(selected_repo_ids)},
        )
        return redirect("onboarding:sync_progress")

    # Render the page with loading state - repos will be fetched via HTMX
    return render(
        request,
        "onboarding/select_repos.html",
        {
            "team": team,
            "integration": integration,
            "app_installation": app_installation,
            "page_title": _("Select Repositories"),
            "step": 2,
        },
    )


@login_required
def fetch_repos(request):
    """HTMX endpoint to fetch repositories from GitHub API.

    Returns a partial HTML template with the repository list.
    """
    if not request.user.teams.exists():
        return render(request, "onboarding/partials/repos_error.html", {"error": "No team found"})

    team = request.user.teams.first()

    try:
        integration = GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        return render(request, "onboarding/partials/repos_error.html", {"error": "GitHub not connected"})

    # Fetch repositories from GitHub API
    repos = []
    try:
        repos = github_oauth.get_organization_repositories(
            integration.credential.access_token,
            integration.organization_slug,
            exclude_archived=True,
        )
    except Exception as e:
        logger.error(f"Failed to fetch repos during onboarding: {e}")
        return render(request, "onboarding/partials/repos_error.html", {"error": str(e)})

    # Sort repos by updated_at descending (most recent first), None values at end
    repos = sorted(repos, key=lambda r: r.get("updated_at") or datetime.min.replace(tzinfo=UTC), reverse=True)

    return render(
        request,
        "onboarding/partials/repos_list.html",
        {"repos": repos},
    )


@login_required
def sync_progress(request):
    """Show sync progress page with Celery progress tracking.

    Uses request.default_team which respects:
    1. Session team (if user navigated from a specific team's dashboard)
    2. User's first team (fallback)
    """
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    # Use default_team to respect session team context (ISS-005 fix)
    team = request.default_team

    # Get tracked repositories for this team
    repos = TrackedRepository.objects.filter(team=team).select_related("integration")

    # Check if team has any PR data (quick sync has produced results)
    first_insights_ready = PullRequest.objects.filter(team=team).exists()

    return render(
        request,
        "onboarding/sync_progress.html",
        {
            "team": team,
            "repos": repos,
            "page_title": _("Syncing Data"),
            "step": 3,
            "first_insights_ready": first_insights_ready,
        },
    )


@login_required
@require_POST
def start_sync(request):
    """Start the historical sync task and return task ID.

    Uses request.default_team which respects:
    1. Session team (if user navigated from a specific team's dashboard)
    2. User's first team (fallback)

    Returns:
        JSON response with task_id for progress polling
    """
    if not request.user.teams.exists():
        return JsonResponse({"error": "No team found"}, status=400)

    # Use default_team to respect session team context (ISS-005 fix)
    team = request.default_team

    # Get all tracked repo IDs for this team
    repo_ids = list(TrackedRepository.objects.filter(team=team).values_list("id", flat=True))

    # Start the full onboarding pipeline (sync + LLM + metrics + insights)
    task = start_onboarding_pipeline(team.id, repo_ids)

    return JsonResponse({"task_id": task.id})


@login_required
def sync_status(request):
    """Return real-time sync status from database.

    Returns JSON with sync status for all tracked repos and overall status.
    This allows the frontend to compare with Celery task state for discrepancies.
    """
    if not request.user.teams.exists():
        return JsonResponse({"error": "No team found"}, status=400)

    team = request.user.teams.first()

    # Get all tracked repositories with their sync status
    repos = TrackedRepository.objects.filter(team=team).values(
        "id", "full_name", "sync_status", "sync_progress", "last_sync_at", "last_sync_error"
    )

    repo_list = []
    statuses = set()
    for repo in repos:
        repo_list.append(
            {
                "id": repo["id"],
                "full_name": repo["full_name"],
                "sync_status": repo["sync_status"],
                "sync_progress": repo["sync_progress"] or 0,
                "last_sync_at": repo["last_sync_at"].isoformat() if repo["last_sync_at"] else None,
                "last_sync_error": repo["last_sync_error"],
            }
        )
        statuses.add(repo["sync_status"])

    # Determine overall status
    if not repo_list:
        overall_status = "no_repos"
    elif "syncing" in statuses:
        overall_status = "syncing"
    elif "failed" in statuses and "completed" not in statuses:
        overall_status = "failed"
    elif "pending" in statuses and "completed" not in statuses:
        overall_status = "pending"
    elif all(s == "completed" for s in statuses):
        overall_status = "completed"
    else:
        # Mixed states - some completed, some failed/pending
        overall_status = "partial"

    # Get PR counts in a single query: total and LLM-processed
    pr_counts = PullRequest.objects.filter(team=team).aggregate(
        total=Count("id"),
        llm_processed=Count("id", filter=Q(llm_summary__isnull=False)),
    )
    prs_synced = pr_counts["total"]
    llm_processed = pr_counts["llm_processed"]

    # Check if metrics and insights are ready
    metrics_ready = WeeklyMetrics.objects.filter(team=team).exists()
    insights_ready = DailyInsight.objects.filter(team=team).exists()

    return JsonResponse(
        {
            "repos": repo_list,
            "overall_status": overall_status,
            "prs_synced": prs_synced,
            "pipeline_status": team.onboarding_pipeline_status,
            "pipeline_stage": team.get_onboarding_pipeline_status_display(),
            "llm_progress": {
                "processed": llm_processed,
                "total": prs_synced,
            },
            "metrics_ready": metrics_ready,
            "insights_ready": insights_ready,
        }
    )


@login_required
def connect_jira(request):
    """Optional step to connect Jira.

    GET with action=connect: Initiate Jira OAuth flow
    POST: Skip Jira and continue to Slack
    """
    from urllib.parse import urlencode

    from apps.auth.oauth_state import FLOW_TYPE_JIRA_ONBOARDING, create_oauth_state
    from apps.integrations.models import JiraIntegration
    from apps.integrations.services import jira_oauth

    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Check if Jira is already connected
    jira_connected = JiraIntegration.objects.filter(team=team).exists()
    if jira_connected:
        # Already connected, go to project selection
        return redirect("onboarding:select_jira_projects")

    # Handle OAuth initiation
    if request.GET.get("action") == "connect":
        # Build callback URL - use unified auth callback
        callback_url = request.build_absolute_uri(reverse("tformance_auth:jira_callback"))

        # Create state for CSRF protection with team_id
        state = create_oauth_state(FLOW_TYPE_JIRA_ONBOARDING, team_id=team.id)

        # Build Jira authorization URL
        params = {
            "audience": "api.atlassian.com",
            "client_id": settings.JIRA_CLIENT_ID,
            "scope": jira_oauth.JIRA_OAUTH_SCOPES,
            "redirect_uri": callback_url,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        auth_url = f"{jira_oauth.JIRA_AUTH_URL}?{urlencode(params)}"

        return redirect(auth_url)

    if request.method == "POST":
        # Track skip (Jira connection tracking happens in OAuth callback)
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
            "sync_task_id": request.session.get("sync_task_id"),
        },
    )


@login_required
def select_jira_projects(request):
    """Select which Jira projects to track.

    GET: Display list of available projects with checkboxes
    POST: Create TrackedJiraProject records for selected projects
    """
    from apps.integrations.models import JiraIntegration, TrackedJiraProject
    from apps.integrations.services import jira_client
    from apps.integrations.services.jira_client import JiraClientError

    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Check if Jira is connected
    try:
        jira_integration = JiraIntegration.objects.get(team=team)
    except JiraIntegration.DoesNotExist:
        messages.error(request, _("Please connect Jira first."))
        return redirect("onboarding:connect_jira")

    if request.method == "POST":
        # Get selected project IDs from form
        selected_project_ids = request.POST.getlist("projects")

        # Get all available projects to look up details
        try:
            all_projects = jira_client.get_accessible_projects(jira_integration.credential)
            project_map = {proj["id"]: proj for proj in all_projects}
        except JiraClientError as e:
            logger.error(f"Failed to fetch Jira projects: {e}")
            messages.error(request, _("Failed to fetch Jira projects. Please try again."))
            return redirect("onboarding:select_jira_projects")

        # Create TrackedJiraProject for each selected project
        created_count = 0
        for project_id in selected_project_ids:
            proj_data = project_map.get(project_id)
            if proj_data:
                obj, created = TrackedJiraProject.objects.get_or_create(
                    team=team,
                    jira_project_id=project_id,
                    defaults={
                        "integration": jira_integration,
                        "jira_project_key": proj_data["key"],
                        "name": proj_data["name"],
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1

        # Track event
        track_event(
            request.user,
            "onboarding_step_completed",
            {"step": "jira_projects", "team_slug": team.slug, "projects_count": len(selected_project_ids)},
        )

        if created_count > 0:
            messages.success(request, _("Now tracking {} Jira project(s).").format(created_count))
        else:
            messages.info(request, _("No new projects selected."))

        # Start Jira sync pipeline if projects were selected
        project_ids = list(TrackedJiraProject.objects.filter(team=team, is_active=True).values_list("id", flat=True))
        if project_ids:
            from apps.integrations.onboarding_pipeline import start_jira_onboarding_pipeline

            task = start_jira_onboarding_pipeline(team.id, project_ids)
            request.session["jira_sync_task_id"] = task.id
            logger.info(f"Started Jira pipeline for team {team.id}: {len(project_ids)} projects")

        return redirect("onboarding:connect_slack")

    # GET: Fetch projects and display selection form
    projects = []
    try:
        projects = jira_client.get_accessible_projects(jira_integration.credential)
    except JiraClientError as e:
        logger.error(f"Failed to fetch Jira projects during onboarding: {e}")
        messages.warning(request, _("Could not fetch Jira projects. You can add them later from settings."))

    # Mark which projects are already tracked
    tracked_project_ids = set(TrackedJiraProject.objects.filter(team=team).values_list("jira_project_id", flat=True))
    for project in projects:
        project["is_tracked"] = project["id"] in tracked_project_ids

    return render(
        request,
        "onboarding/select_jira_projects.html",
        {
            "team": team,
            "jira_integration": jira_integration,
            "projects": projects,
            "page_title": _("Select Jira Projects"),
            "step": 3,
            "sync_task_id": request.session.get("sync_task_id"),
        },
    )


@login_required
def jira_sync_status(request):
    """Return Jira sync status for polling.

    Used by inline progress indicator on select_jira_projects page
    to show real-time sync status.

    Returns:
        JsonResponse with overall_status, projects list, and issues_synced count.
    """
    from django.http import JsonResponse

    from apps.integrations.models import TrackedJiraProject
    from apps.metrics.models import JiraIssue

    if not request.user.teams.exists():
        return JsonResponse({"error": "No team found"}, status=400)

    team = request.user.teams.first()

    # Get all active tracked projects
    projects = list(
        TrackedJiraProject.objects.filter(team=team, is_active=True).values(
            "id", "name", "jira_project_key", "sync_status", "last_sync_at"
        )
    )

    # Get total issues synced for this team
    issues_count = JiraIssue.objects.filter(team=team).count()

    # Determine overall status from project statuses
    statuses = [p["sync_status"] for p in projects]
    if "syncing" in statuses:
        overall = "syncing"
    elif "pending" in statuses:
        overall = "pending"
    elif all(s == "complete" for s in statuses) and statuses:
        overall = "completed"
    elif "error" in statuses:
        overall = "error"
    elif not statuses:
        overall = "pending"
    else:
        overall = "completed"

    return JsonResponse(
        {
            "overall_status": overall,
            "projects": projects,
            "issues_synced": issues_count,
        }
    )


@login_required
def connect_slack(request):
    """Optional step to connect Slack."""
    from urllib.parse import urlencode

    from django.conf import settings

    from apps.auth.oauth_state import FLOW_TYPE_SLACK_ONBOARDING, create_oauth_state
    from apps.integrations.models import SlackIntegration
    from apps.integrations.services.slack_oauth import SLACK_OAUTH_AUTHORIZE_URL, SLACK_OAUTH_SCOPES

    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Check if Slack is already connected
    slack_integration = SlackIntegration.objects.filter(team=team).first()

    # Handle OAuth initiation
    if request.GET.get("action") == "connect":
        # Create OAuth state with team_id
        state = create_oauth_state(FLOW_TYPE_SLACK_ONBOARDING, team_id=team.id)

        # Build callback URL
        callback_url = request.build_absolute_uri(reverse("tformance_auth:slack_callback"))

        # Build Slack OAuth authorization URL
        params = {
            "client_id": settings.SLACK_CLIENT_ID,
            "scope": SLACK_OAUTH_SCOPES,
            "redirect_uri": callback_url,
            "state": state,
        }
        auth_url = f"{SLACK_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

        return redirect(auth_url)

    if request.method == "POST":
        if slack_integration:
            # Save Slack configuration
            from datetime import time

            # Update feature toggles (checkboxes return 'on' or are absent)
            slack_integration.surveys_enabled = request.POST.get("surveys_enabled") == "on"
            slack_integration.leaderboard_enabled = request.POST.get("leaderboard_enabled") == "on"
            slack_integration.reveals_enabled = request.POST.get("reveals_enabled") == "on"

            # Update schedule
            if request.POST.get("leaderboard_day"):
                slack_integration.leaderboard_day = int(request.POST.get("leaderboard_day"))
            if request.POST.get("leaderboard_time"):
                time_str = request.POST.get("leaderboard_time")
                try:
                    hours, minutes = map(int, time_str.split(":"))
                    slack_integration.leaderboard_time = time(hours, minutes)
                except (ValueError, AttributeError):
                    pass  # Keep existing value on parse error

            # Update channel
            if request.POST.get("leaderboard_channel_id"):
                slack_integration.leaderboard_channel_id = request.POST.get("leaderboard_channel_id")

            slack_integration.save()

            track_event(
                request.user,
                "slack_configured",
                {
                    "team_slug": team.slug,
                    "surveys_enabled": slack_integration.surveys_enabled,
                    "leaderboard_enabled": slack_integration.leaderboard_enabled,
                    "reveals_enabled": slack_integration.reveals_enabled,
                },
            )
        else:
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
            "sync_task_id": request.session.get("sync_task_id"),
            "jira_sync_task_id": request.session.get("jira_sync_task_id"),
            "slack_integration": slack_integration,
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

    # Send welcome email (fail silently to not block onboarding)
    try:
        send_welcome_email(team, request.user)
    except Exception as e:
        logger.warning(f"Failed to send welcome email during onboarding skip: {e}")

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
    from apps.integrations.models import JiraIntegration, SlackIntegration

    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Clear onboarding session data
    request.session.pop(ONBOARDING_SELECTED_ORG_KEY, None)

    # Get sync task info for progress indicator
    sync_task_id = request.session.get("sync_task_id")

    # Check integration status
    jira_connected = JiraIntegration.objects.filter(team=team).exists()
    slack_connected = SlackIntegration.objects.filter(team=team).exists()

    # Mark onboarding as complete
    if not team.onboarding_complete:
        team.onboarding_complete = True
        team.save(update_fields=["onboarding_complete"])

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
            "sync_task_id": sync_task_id,
            "jira_sync_task_id": request.session.get("jira_sync_task_id"),
            "jira_connected": jira_connected,
            "slack_connected": slack_connected,
        },
    )
