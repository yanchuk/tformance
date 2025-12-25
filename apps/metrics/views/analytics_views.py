"""Analytics views - Overview and tabbed analytics pages."""

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from apps.metrics.services import insight_service
from apps.metrics.view_utils import get_extended_date_range
from apps.teams.decorators import team_admin_required


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
    }


@team_admin_required
def analytics_overview(request: HttpRequest) -> HttpResponse:
    """Analytics Overview - Team health dashboard.

    Shows key metrics, insights, and quick links to detailed analytics pages.
    Admin-only view.
    """
    context = _get_analytics_context(request, "overview")
    context["insights"] = insight_service.get_recent_insights(request.team)

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
