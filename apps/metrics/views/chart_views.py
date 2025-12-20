"""Chart partial views for HTMX endpoints."""

from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from apps.metrics.services import chart_formatters, dashboard_service
from apps.metrics.view_utils import get_date_range_from_request
from apps.teams.decorators import login_and_team_required, team_admin_required


@team_admin_required
def ai_adoption_chart(request: HttpRequest) -> HttpResponse:
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
def ai_quality_chart(request: HttpRequest) -> HttpResponse:
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
def cycle_time_chart(request: HttpRequest) -> HttpResponse:
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


@login_and_team_required
def key_metrics_cards(request: HttpRequest) -> HttpResponse:
    """Key metrics stat cards (all team members)."""
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
def team_breakdown_table(request: HttpRequest) -> HttpResponse:
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
def leaderboard_table(request: HttpRequest) -> HttpResponse:
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


@login_and_team_required
def review_distribution_chart(request: HttpRequest) -> HttpResponse:
    """Review distribution by reviewer (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    data = dashboard_service.get_review_distribution(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/review_distribution_chart.html",
        {
            "chart_data": data,
        },
    )


@login_and_team_required
def recent_prs_table(request: HttpRequest) -> HttpResponse:
    """Recent PRs with AI status (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    rows = dashboard_service.get_recent_prs(request.team, start_date, end_date, limit=10)
    return TemplateResponse(
        request,
        "metrics/partials/recent_prs_table.html",
        {
            "rows": rows,
        },
    )


@login_and_team_required
def review_time_chart(request: HttpRequest) -> HttpResponse:
    """Review time trend (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    data = dashboard_service.get_review_time_trend(request.team, start_date, end_date)
    chart_data = chart_formatters.format_time_series(data)
    return TemplateResponse(
        request,
        "metrics/partials/review_time_chart.html",
        {
            "chart_data": chart_data,
        },
    )


@login_and_team_required
def pr_size_chart(request: HttpRequest) -> HttpResponse:
    """PR size distribution (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    data = dashboard_service.get_pr_size_distribution(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/pr_size_chart.html",
        {
            "chart_data": data,
        },
    )


@login_and_team_required
def revert_rate_card(request: HttpRequest) -> HttpResponse:
    """Revert and hotfix rate stats (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    stats = dashboard_service.get_revert_hotfix_stats(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/revert_rate_card.html",
        {
            "stats": stats,
        },
    )


@login_and_team_required
def unlinked_prs_table(request: HttpRequest) -> HttpResponse:
    """PRs without Jira links (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    rows = dashboard_service.get_unlinked_prs(request.team, start_date, end_date, limit=10)
    return TemplateResponse(
        request,
        "metrics/partials/unlinked_prs_table.html",
        {
            "rows": rows,
        },
    )


@login_and_team_required
def reviewer_workload_table(request: HttpRequest) -> HttpResponse:
    """Reviewer workload analysis (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    rows = dashboard_service.get_reviewer_workload(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/reviewer_workload_table.html",
        {
            "rows": rows,
        },
    )


@team_admin_required
def copilot_metrics_card(request: HttpRequest) -> HttpResponse:
    """Copilot metrics card (admin only)."""
    start_date, end_date = get_date_range_from_request(request)
    metrics = dashboard_service.get_copilot_metrics(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/copilot_metrics_card.html",
        {
            "metrics": metrics,
        },
    )


@team_admin_required
def copilot_trend_chart(request: HttpRequest) -> HttpResponse:
    """Copilot usage trend chart (admin only)."""
    start_date, end_date = get_date_range_from_request(request)
    data = dashboard_service.get_copilot_trend(request.team, start_date, end_date)
    chart_data = chart_formatters.format_time_series(data, date_key="week", value_key="acceptance_rate")
    return TemplateResponse(
        request,
        "metrics/partials/copilot_trend_chart.html",
        {
            "chart_data": chart_data,
        },
    )


@team_admin_required
def copilot_members_table(request: HttpRequest) -> HttpResponse:
    """Copilot usage by member table (admin only)."""
    start_date, end_date = get_date_range_from_request(request)
    rows = dashboard_service.get_copilot_by_member(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/copilot_members_table.html",
        {
            "rows": rows,
        },
    )


@login_and_team_required
def iteration_metrics_card(request: HttpRequest) -> HttpResponse:
    """Iteration metrics card (all members).

    Shows average review rounds, fix response time, commits after first review,
    and total comments for PRs in the date range.
    """
    start_date, end_date = get_date_range_from_request(request)
    metrics = dashboard_service.get_iteration_metrics(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/iteration_metrics_card.html",
        {
            "metrics": metrics,
        },
    )


@team_admin_required
def reviewer_correlations_table(request: HttpRequest) -> HttpResponse:
    """Reviewer correlations table (admin only).

    Shows agreement rates between reviewer pairs to identify
    potentially redundant review assignments.
    """
    rows = dashboard_service.get_reviewer_correlations(request.team)
    return TemplateResponse(
        request,
        "metrics/partials/reviewer_correlations_table.html",
        {
            "rows": rows,
        },
    )
