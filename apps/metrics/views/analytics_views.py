"""Analytics views - Overview and tabbed analytics pages."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from apps.integrations.services.integration_flags import is_cicd_enabled, is_integration_enabled
from apps.metrics.models import PullRequest
from apps.metrics.view_utils import get_extended_date_range
from apps.teams.decorators import team_admin_required
from apps.utils.analytics import track_event


def _get_repos_for_team(team) -> list[str]:
    """Get distinct repository names for a team.

    Args:
        team: Team instance

    Returns:
        Sorted list of repository names (owner/repo format)
    """
    repos = (
        PullRequest.objects.filter(team=team)
        .exclude(github_repo__isnull=True)
        .exclude(github_repo="")
        .values_list("github_repo", flat=True)
        .distinct()
        .order_by("github_repo")
    )
    return list(repos)


def _get_analytics_context(request: HttpRequest, active_page: str) -> dict:
    """Get common context for analytics pages.

    Args:
        request: The HTTP request object
        active_page: Which analytics tab is active (overview, ai_adoption, etc.)

    Returns:
        Dictionary with common analytics context
    """
    # Use extended date range for full preset support
    date_range = get_extended_date_range(request)

    # Get available repositories for the team
    repos = _get_repos_for_team(request.team)

    # Get selected repo from request (validated against available repos)
    selected_repo = request.GET.get("repo", "")
    if selected_repo and selected_repo not in repos:
        selected_repo = ""  # Invalid repo, reset to all

    return {
        "active_tab": "metrics",
        "active_page": active_page,
        "days": date_range["days"],
        "start_date": date_range["start_date"],
        "end_date": date_range["end_date"],
        "granularity": date_range["granularity"],
        "preset": request.GET.get("preset", ""),
        # For YoY comparison
        "compare_start": date_range.get("compare_start"),
        "compare_end": date_range.get("compare_end"),
        # Repository filter
        "repos": repos,  # List for template logic and json_script filter
        "repos_count": len(repos),  # Count for conditional display
        "selected_repo": selected_repo,
        # Feature flags
        "cicd_enabled": is_cicd_enabled(request),
    }


def _track_filter_events(request: HttpRequest, context: dict, tab: str) -> None:
    """Track filter change events for analytics.

    Args:
        request: The HTTP request object
        context: The analytics context dictionary
        tab: The current analytics tab name
    """
    team_slug = request.team.slug

    # Track repo filter if applied
    if context.get("selected_repo"):
        track_event(
            request.user,
            "repo_filter_applied",
            {
                "tab": tab,
                "repo_name": context["selected_repo"],
                "team_slug": team_slug,
            },
        )


@team_admin_required
def analytics_overview(request: HttpRequest) -> HttpResponse:
    """Analytics Overview - Team health dashboard.

    Shows key metrics and quick links to detailed analytics pages.
    Admin-only view.

    Access is blocked during Phase 1 of onboarding (syncing, llm_processing,
    computing_metrics, computing_insights, failed). Dashboard becomes accessible
    once Phase 1 completes (phase1_complete, background_*, complete).
    """
    # Block dashboard during Phase 1 of onboarding
    if not request.team.dashboard_accessible:
        return redirect("onboarding:sync_progress")

    context = _get_analytics_context(request, "overview")

    # Track first dashboard view (once per session)
    if not request.session.get("_posthog_dashboard_viewed"):
        track_event(
            request.user,
            "dashboard_first_view",
            {"team_slug": request.team.slug},
        )
        request.session["_posthog_dashboard_viewed"] = True

    # Track page view
    track_event(
        request.user,
        "analytics_viewed",
        {"tab": "overview", "date_range": context["days"], "team_slug": request.team.slug},
    )

    # Track filter events
    _track_filter_events(request, context, "overview")

    # Return partial for HTMX requests
    template = "metrics/analytics/overview.html#page-content" if request.htmx else "metrics/analytics/overview.html"
    return TemplateResponse(request, template, context)


@team_admin_required
def analytics_ai_adoption(request: HttpRequest) -> HttpResponse:
    """AI Adoption analytics page.

    Shows AI adoption trends, AI vs non-AI comparison metrics, and tool breakdown.
    Admin-only view.
    """
    from apps.metrics.services import dashboard_service

    context = _get_analytics_context(request, "ai_adoption")

    # Get AI vs non-AI comparison data
    context["comparison"] = dashboard_service.get_ai_quality_comparison(
        request.team, context["start_date"], context["end_date"]
    )

    # Track page view
    track_event(
        request.user,
        "analytics_viewed",
        {"tab": "ai_adoption", "date_range": context["days"], "team_slug": request.team.slug},
    )

    # Track filter events
    _track_filter_events(request, context, "ai_adoption")

    # Return partial for HTMX requests
    template = (
        "metrics/analytics/ai_adoption.html#page-content" if request.htmx else "metrics/analytics/ai_adoption.html"
    )
    return TemplateResponse(request, template, context)


@team_admin_required
def analytics_delivery(request: HttpRequest) -> HttpResponse:
    """Delivery analytics page.

    Shows PR throughput, cycle time trends, PR size distribution, and velocity.
    Admin-only view.
    """
    context = _get_analytics_context(request, "delivery")

    # Track page view
    track_event(
        request.user,
        "analytics_viewed",
        {"tab": "delivery", "date_range": context["days"], "team_slug": request.team.slug},
    )

    # Track filter events
    _track_filter_events(request, context, "delivery")

    # Return partial for HTMX requests
    template = "metrics/analytics/delivery.html#page-content" if request.htmx else "metrics/analytics/delivery.html"
    return TemplateResponse(request, template, context)


@team_admin_required
def analytics_quality(request: HttpRequest) -> HttpResponse:
    """Quality analytics page.

    Shows review time trends, reviewer workload, CI/CD metrics, and iteration data.
    Admin-only view.
    """
    context = _get_analytics_context(request, "quality")

    # Track page view
    track_event(
        request.user,
        "analytics_viewed",
        {"tab": "quality", "date_range": context["days"], "team_slug": request.team.slug},
    )

    # Track filter events
    _track_filter_events(request, context, "quality")

    # Return partial for HTMX requests
    template = "metrics/analytics/quality.html#page-content" if request.htmx else "metrics/analytics/quality.html"
    return TemplateResponse(request, template, context)


@team_admin_required
def analytics_team(request: HttpRequest) -> HttpResponse:
    """Team performance analytics page.

    Shows team member comparison, individual trends, and performance breakdown.
    Admin-only view.
    """
    context = _get_analytics_context(request, "team")

    # Check if integrations are enabled (for conditional sections)
    context["slack_enabled"] = is_integration_enabled(request, "slack")
    context["copilot_enabled"] = is_integration_enabled(request, "copilot")

    # Track page view
    track_event(
        request.user,
        "analytics_viewed",
        {"tab": "team", "date_range": context["days"], "team_slug": request.team.slug},
    )

    # Track filter events
    _track_filter_events(request, context, "team")

    # Return partial for HTMX requests
    template = "metrics/analytics/team.html#page-content" if request.htmx else "metrics/analytics/team.html"
    return TemplateResponse(request, template, context)
