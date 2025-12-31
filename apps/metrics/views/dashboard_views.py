from datetime import date

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.metrics.models import DailyInsight
from apps.metrics.services import insight_service
from apps.metrics.services.insight_llm import resolve_action_url
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


@login_and_team_required
def engineering_insights(request: HttpRequest) -> HttpResponse:
    """Render LLM-generated engineering insights (HTMX endpoint).

    Query params:
        days: Number of days for the insight period (7, 30, or 90)
    """
    days = int(request.GET.get("days", 30))

    # Get the most recent cached insight for this days period
    # Uses days as comparison_period (e.g., "7", "30", "90")
    insight_record = (
        DailyInsight.objects.filter(
            team=request.team,
            category="llm_insight",
            comparison_period=str(days),
        )
        .order_by("-date")
        .first()
    )

    context = {
        "days": days,
        "insight": None,
        "error": None,
    }

    if insight_record and insight_record.metric_value:
        # Parse the stored JSON insight
        insight_data = insight_record.metric_value

        # Resolve action URLs
        raw_actions = insight_data.get("actions", [])
        resolved_actions = [{"label": a.get("label", ""), "url": resolve_action_url(a, days)} for a in raw_actions]

        context["insight"] = {
            "headline": insight_data.get("headline", ""),
            "detail": insight_data.get("detail", ""),
            "possible_causes": insight_data.get("possible_causes", []),
            "recommendation": insight_data.get("recommendation", ""),
            "metric_cards": insight_data.get("metric_cards", []),
            "actions": resolved_actions,
            "is_fallback": insight_data.get("is_fallback", False),
            "generated_at": insight_record.updated_at,
        }

    return TemplateResponse(
        request,
        "metrics/partials/engineering_insights.html",
        context,
    )


@require_POST
@login_and_team_required
def refresh_insight(request: HttpRequest) -> HttpResponse:
    """Regenerate an insight on demand (HTMX endpoint).

    Query params:
        cadence: "weekly" or "monthly" (default: weekly)
    """
    from datetime import timedelta

    from apps.metrics.services.insight_llm import (
        cache_insight,
        gather_insight_data,
        generate_insight,
    )

    cadence = request.GET.get("cadence", "weekly")
    days = int(request.GET.get("days", 30))
    today = date.today()

    # Determine period based on cadence
    period_days = 30 if cadence == "monthly" else 7
    start_date = today - timedelta(days=period_days)

    context = {
        "cadence": cadence,
        "days": days,
        "insight": None,
        "error": None,
    }

    try:
        # Generate fresh insight
        data = gather_insight_data(
            team=request.team,
            start_date=start_date,
            end_date=today,
        )
        insight = generate_insight(data)

        # Cache it
        cache_insight(
            team=request.team,
            insight=insight,
            target_date=today,
            cadence=cadence,
        )

        context["insight"] = {
            "headline": insight.get("headline", ""),
            "detail": insight.get("detail", ""),
            "recommendation": insight.get("recommendation", ""),
            "metric_cards": insight.get("metric_cards", []),
            "is_fallback": insight.get("is_fallback", False),
            "generated_at": timezone.now(),
        }
    except Exception as e:
        context["error"] = str(e)

    return TemplateResponse(
        request,
        "metrics/partials/engineering_insights.html",
        context,
    )
