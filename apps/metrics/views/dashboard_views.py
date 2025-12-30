from datetime import date

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.metrics.models import DailyInsight
from apps.metrics.services import insight_service
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
        return redirect("metrics:analytics_overview")
    return redirect("metrics:team_dashboard")


@team_admin_required
def cto_overview(request: HttpRequest) -> HttpResponse:
    """CTO Overview Dashboard - Admin only."""
    context = _get_date_range_context(request)
    context["insights"] = insight_service.get_recent_insights(request.team)
    # Return partial for HTMX requests (e.g., days filter changes)
    template = "metrics/cto_overview.html#page-content" if request.htmx else "metrics/cto_overview.html"
    return TemplateResponse(request, template, context)


@login_and_team_required
def team_dashboard(request: HttpRequest) -> HttpResponse:
    """Team Dashboard - Redirects to unified dashboard at /app/.

    The old team_dashboard URL (/app/metrics/dashboard/team/) is deprecated.
    All dashboard functionality is now available at /app/ (unified dashboard).
    """
    # Preserve days query parameter in redirect
    days = request.GET.get("days")
    if days:
        return redirect(f"/app/?days={days}")
    return redirect("web_team:home")


@require_POST
@login_and_team_required
def dismiss_insight(request: HttpRequest, insight_id: int) -> HttpResponse:
    """Dismiss an insight (HTMX endpoint)."""
    insight = get_object_or_404(DailyInsight, id=insight_id, team=request.team)
    insight.is_dismissed = True
    insight.dismissed_at = timezone.now()
    insight.save()
    return HttpResponse(status=200)
