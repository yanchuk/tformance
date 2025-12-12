"""Chart partial views for HTMX endpoints."""

from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from apps.metrics.services import chart_formatters, dashboard_service
from apps.metrics.view_utils import get_date_range_from_request
from apps.teams.decorators import login_and_team_required, team_admin_required


@team_admin_required
def ai_adoption_chart(request: HttpRequest, team_slug: str) -> HttpResponse:
    """AI adoption trend line chart (admin only)."""
    start_date, end_date = get_date_range_from_request(request)
    data = dashboard_service.get_ai_adoption_trend(request.team, start_date, end_date)
    chart_data = chart_formatters.format_time_series(data)
    return TemplateResponse(
        request,
        "metrics/partials/ai_adoption_chart.html",
        {
            "chart_data": chart_data,
        },
    )


@team_admin_required
def ai_quality_chart(request: HttpRequest, team_slug: str) -> HttpResponse:
    """AI vs non-AI quality comparison (admin only)."""
    start_date, end_date = get_date_range_from_request(request)
    chart_data = dashboard_service.get_ai_quality_comparison(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/ai_quality_chart.html",
        {
            "chart_data": chart_data,
        },
    )


@login_and_team_required
def cycle_time_chart(request: HttpRequest, team_slug: str) -> HttpResponse:
    """Cycle time trend (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    data = dashboard_service.get_cycle_time_trend(request.team, start_date, end_date)
    chart_data = chart_formatters.format_time_series(data)
    return TemplateResponse(
        request,
        "metrics/partials/cycle_time_chart.html",
        {
            "chart_data": chart_data,
        },
    )


@team_admin_required
def key_metrics_cards(request: HttpRequest, team_slug: str) -> HttpResponse:
    """Key metrics stat cards (admin only)."""
    start_date, end_date = get_date_range_from_request(request)
    metrics = dashboard_service.get_key_metrics(request.team, start_date, end_date)

    # Calculate previous period for comparison
    period_length = (end_date - start_date).days
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length)
    previous_metrics = dashboard_service.get_key_metrics(request.team, prev_start, prev_end)

    return TemplateResponse(
        request,
        "metrics/partials/key_metrics_cards.html",
        {
            "metrics": metrics,
            "previous_metrics": previous_metrics,
        },
    )


@team_admin_required
def team_breakdown_table(request: HttpRequest, team_slug: str) -> HttpResponse:
    """Team breakdown table (admin only)."""
    start_date, end_date = get_date_range_from_request(request)
    rows = dashboard_service.get_team_breakdown(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/team_breakdown_table.html",
        {
            "rows": rows,
        },
    )


@login_and_team_required
def leaderboard_table(request: HttpRequest, team_slug: str) -> HttpResponse:
    """AI detective leaderboard (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    rows = dashboard_service.get_ai_detective_leaderboard(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/leaderboard_table.html",
        {
            "rows": rows,
        },
    )
