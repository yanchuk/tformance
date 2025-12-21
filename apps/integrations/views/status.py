"""Integration status and overview views."""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST

from apps.integrations.models import (
    GitHubIntegration,
    JiraIntegration,
    SlackIntegration,
    TrackedJiraProject,
    TrackedRepository,
)
from apps.metrics.models import AIUsageDaily, TeamMember
from apps.teams.decorators import login_and_team_required


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

    # Check Copilot availability and last sync
    copilot_available = github_connected
    copilot_last_sync = None
    if copilot_available:
        copilot_last_sync = AIUsageDaily.objects.filter(team=team, source="copilot").order_by("-created_at").first()

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
        "copilot_available": copilot_available,
        "copilot_last_sync": copilot_last_sync,
        "active_tab": "integrations",
    }

    template = "integrations/home.html#page-content" if request.htmx else "integrations/home.html"
    return TemplateResponse(request, template, context)


@login_and_team_required
@require_POST
def copilot_sync(request):
    """Trigger manual Copilot metrics sync.

    Triggers a background task to sync Copilot usage metrics from GitHub.

    Requires team with GitHub integration and POST method.

    Args:
        request: The HTTP request object.
        team_slug: The slug of the team.

    Returns:
        HttpResponse redirecting to integrations home with success message.
    """
    team = request.team

    # Check if GitHub integration exists
    try:
        GitHubIntegration.objects.get(team=team)
    except GitHubIntegration.DoesNotExist:
        raise Http404("GitHub integration not found") from None

    # Trigger sync task
    from apps.integrations.tasks import sync_copilot_metrics_task

    sync_copilot_metrics_task.delay(team.id)

    messages.success(request, "Copilot metrics sync started")
    return redirect("integrations:integrations_home")
