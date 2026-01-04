"""Jira-related onboarding views.

Contains views for Jira OAuth connection and project selection.
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.integrations.services.integration_flags import get_next_onboarding_step, is_integration_enabled
from apps.utils.analytics import track_event

from ._helpers import _get_onboarding_flags_context

logger = logging.getLogger(__name__)


@login_required
def connect_jira(request):
    """Optional step to connect Jira.

    GET with action=connect: Initiate Jira OAuth flow
    POST: Skip Jira and continue to Slack

    If the integration_jira_enabled flag is off, automatically skip to the next step.
    """
    from apps.auth.oauth_state import FLOW_TYPE_JIRA_ONBOARDING, create_oauth_state
    from apps.integrations.models import JiraIntegration
    from apps.integrations.services import jira_oauth

    if not request.user.teams.exists():
        return redirect("onboarding:start")

    team = request.user.teams.first()

    # Check if Jira integration is enabled via feature flag
    if not is_integration_enabled(request, "jira"):
        # Skip to next step (slack if enabled, otherwise complete)
        next_step = get_next_onboarding_step(request, "jira")
        if next_step == "slack":
            return redirect("onboarding:connect_slack")
        else:
            return redirect("onboarding:complete")

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
            **_get_onboarding_flags_context(request),
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
            **_get_onboarding_flags_context(request),
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
