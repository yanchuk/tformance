from datetime import date

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from apps.metrics.view_utils import get_date_range_from_request
from apps.teams.decorators import login_and_team_required, team_admin_required


def _get_date_range_context(request: HttpRequest) -> dict[str, int | date]:
    """Extract common date range context from request query parameters.

    Args:
        request: The HTTP request object

    Returns:
        Dictionary containing days, start_date, end_date, and active_tab
    """
    days = int(request.GET.get("days", 30))
    start_date, end_date = get_date_range_from_request(request)

    return {
        "active_tab": "metrics",
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
    }


@login_and_team_required
def home(request: HttpRequest) -> HttpResponse:
    template = "metrics/metrics_home.html#page-content" if request.htmx else "metrics/metrics_home.html"

    return TemplateResponse(request, template, {"active_tab": "metrics"})


@login_and_team_required
def dashboard_redirect(request: HttpRequest) -> HttpResponse:
    """Redirect to appropriate dashboard based on user role."""
    membership = request.team_membership
    if membership.role == "admin":
        return redirect("metrics:cto_overview")
    return redirect("metrics:team_dashboard")


@team_admin_required
def cto_overview(request: HttpRequest) -> HttpResponse:
    """CTO Overview Dashboard - Admin only."""
    context = _get_date_range_context(request)
    # Return partial for HTMX requests (e.g., days filter changes)
    template = "metrics/cto_overview.html#page-content" if request.htmx else "metrics/cto_overview.html"
    return TemplateResponse(request, template, context)


@login_and_team_required
def team_dashboard(request: HttpRequest) -> HttpResponse:
    """Team Dashboard - All team members."""
    context = _get_date_range_context(request)
    # Return partial for HTMX requests (e.g., days filter changes)
    template = "metrics/team_dashboard.html#page-content" if request.htmx else "metrics/team_dashboard.html"
    return TemplateResponse(request, template, context)
