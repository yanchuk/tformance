"""Views for the onboarding wizard.

Users without a team are directed here after signup to:
1. Connect their GitHub account
2. Select their organization (which creates the team)
3. Select repositories to track
4. Optionally connect Jira and Slack
"""

import logging
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.integrations.models import GitHubIntegration, IntegrationCredential, TrackedRepository
from apps.integrations.services import github_oauth, member_sync
from apps.integrations.services.encryption import decrypt, encrypt
from apps.integrations.tasks import sync_historical_data_task
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

    return render(
        request,
        "onboarding/start.html",
        {"page_title": _("Connect GitHub"), "step": 1},
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
            # Start background sync task
            task = sync_historical_data_task.delay(team.id, repo_ids)
            # Store task_id in session for progress tracking
            request.session["sync_task_id"] = task.id
            logger.info(f"Started background sync task {task.id} for team {team.name}")

        # Track step completion
        track_event(
            request.user,
            "onboarding_step_completed",
            {"step": "repos", "team_slug": team.slug, "repos_count": len(selected_repo_ids)},
        )
        return redirect("onboarding:connect_jira")

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
        messages.warning(request, _("Could not fetch repositories. You can skip this step and add repos later."))

    return render(
        request,
        "onboarding/select_repos.html",
        {
            "team": team,
            "integration": integration,
            "repos": repos,
            "page_title": _("Select Repositories"),
            "step": 2,
        },
    )


@login_required
def sync_progress(request):
    """Show sync progress page with Celery progress tracking."""
    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Get tracked repositories for this team
    repos = TrackedRepository.objects.filter(team=team).select_related("integration")

    return render(
        request,
        "onboarding/sync_progress.html",
        {
            "team": team,
            "repos": repos,
            "page_title": _("Syncing Data"),
            "step": 3,
        },
    )


@login_required
@require_POST
def start_sync(request):
    """Start the historical sync task and return task ID.

    Returns:
        JSON response with task_id for progress polling
    """
    if not request.user.teams.exists():
        return JsonResponse({"error": "No team found"}, status=400)

    team = request.user.teams.first()

    # Get all tracked repo IDs for this team
    repo_ids = list(TrackedRepository.objects.filter(team=team).values_list("id", flat=True))

    # Start the Celery task
    task = sync_historical_data_task.delay(team.id, repo_ids)

    return JsonResponse({"task_id": task.id})


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
            "sync_task_id": request.session.get("sync_task_id"),
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
            "sync_task_id": request.session.get("sync_task_id"),
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

    # Get sync task info for progress indicator
    sync_task_id = request.session.get("sync_task_id")

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
        },
    )
