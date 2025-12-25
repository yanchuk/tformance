"""Analytics views - Overview and tabbed analytics pages."""

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from apps.metrics.services import insight_service
from apps.metrics.view_utils import get_date_range_from_request
from apps.teams.decorators import team_admin_required
from apps.utils.analytics import track_event


def _get_analytics_context(request: HttpRequest, active_page: str) -> dict:
    """Get common context for analytics pages.

    Args:
        request: The HTTP request object
        active_page: Which analytics tab is active (overview, ai_adoption, etc.)

    Returns:
        Dictionary with common analytics context
    """
    days = int(request.GET.get("days", 30))
    start_date, end_date = get_date_range_from_request(request)

    return {
        "active_tab": "metrics",
        "active_page": active_page,
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
    }


@team_admin_required
def analytics_overview(request: HttpRequest) -> HttpResponse:
    """Analytics Overview - Team health dashboard.

    Shows key metrics, insights, and quick links to detailed analytics pages.
    Admin-only view.
    """
    context = _get_analytics_context(request, "overview")
    context["insights"] = insight_service.get_recent_insights(request.team)

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

    # Return partial for HTMX requests
    template = "metrics/analytics/team.html#page-content" if request.htmx else "metrics/analytics/team.html"
    return TemplateResponse(request, template, context)
