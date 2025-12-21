"""Jira integration views."""

import logging

from django.contrib import messages
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django_ratelimit.decorators import ratelimit

from apps.integrations.models import IntegrationCredential, JiraIntegration, TrackedJiraProject
from apps.integrations.services import jira_client, jira_oauth
from apps.integrations.services.jira_client import JiraClientError
from apps.integrations.services.jira_oauth import JiraOAuthError
from apps.teams.decorators import login_and_team_required, team_admin_required

from .helpers import _create_integration_credential, _validate_oauth_callback

logger = logging.getLogger(__name__)


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
        # EncryptedTextField auto-decrypts access_token
        sites = jira_oauth.get_accessible_resources(credential.access_token)
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
