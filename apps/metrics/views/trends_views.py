"""Trends analytics views - Long-horizon trend charts and YoY comparison."""

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.response import TemplateResponse

from apps.metrics.services import dashboard_service
from apps.metrics.view_utils import get_extended_date_range
from apps.teams.decorators import team_admin_required


def _get_trends_context(request: HttpRequest) -> dict:
    """Get common context for trends pages.

    Args:
        request: The HTTP request object

    Returns:
        Dictionary with common trends context
    """
    date_range = get_extended_date_range(request)

    return {
        "active_tab": "metrics",
        "active_page": "trends",
        "days": date_range["days"],
        "start_date": date_range["start_date"],
        "end_date": date_range["end_date"],
        "granularity": date_range["granularity"],
        "preset": request.GET.get("preset", ""),
        "compare_start": date_range.get("compare_start"),
        "compare_end": date_range.get("compare_end"),
    }


@team_admin_required
def trends_overview(request: HttpRequest) -> HttpResponse:
    """Trends Overview - Full-width trend charts for year-long analysis.

    Main trends dashboard with metric selector and wide charts for
    viewing long-horizon trends like YoY comparison.
    Admin-only view.
    """
    context = _get_trends_context(request)

    # Default metric for initial load
    context["default_metric"] = request.GET.get("metric", "cycle_time")
    context["available_metrics"] = [
        {"id": "cycle_time", "name": "Cycle Time", "unit": "hours"},
        {"id": "review_time", "name": "Review Time", "unit": "hours"},
        {"id": "pr_count", "name": "PRs Merged", "unit": "count"},
        {"id": "ai_adoption", "name": "AI Adoption", "unit": "%"},
    ]

    # Return partial for HTMX requests
    template = "metrics/analytics/trends.html#page-content" if request.htmx else "metrics/analytics/trends.html"
    return TemplateResponse(request, template, context)


@team_admin_required
def trend_chart_data(request: HttpRequest) -> HttpResponse:
    """API endpoint for trend chart data (JSON).

    Returns chart.js compatible data structure for trend visualization.
    Supports YoY comparison when preset=yoy.

    Query params:
        metric: cycle_time | review_time | pr_count | ai_adoption
        days: Number of days (default 30)
        preset: this_year | last_year | this_quarter | yoy
        start/end: Custom date range

    Returns:
        JSON with labels, datasets, and metadata
    """
    date_range = get_extended_date_range(request)
    metric = request.GET.get("metric", "cycle_time")

    # Map metric to service function
    metric_functions = {
        "cycle_time": dashboard_service.get_monthly_cycle_time_trend,
        "review_time": dashboard_service.get_monthly_review_time_trend,
        "pr_count": dashboard_service.get_monthly_pr_count,
        "ai_adoption": dashboard_service.get_monthly_ai_adoption,
    }

    # Use weekly functions for shorter ranges
    weekly_functions = {
        "cycle_time": dashboard_service.get_cycle_time_trend,
        "review_time": dashboard_service.get_review_time_trend,
        "pr_count": None,  # No weekly PR count function
        "ai_adoption": dashboard_service.get_ai_adoption_trend,
    }

    # Determine granularity and get appropriate function
    granularity = date_range["granularity"]
    start_date = date_range["start_date"]
    end_date = date_range["end_date"]

    if granularity == "monthly":
        func = metric_functions.get(metric, metric_functions["cycle_time"])
    else:
        func = weekly_functions.get(metric) or metric_functions.get(metric)

    # Get current period data
    current_data = func(request.team, start_date, end_date)

    # Prepare chart.js format
    labels = []
    values = []
    for entry in current_data:
        # Use month or week as label
        label = entry.get("month") or entry.get("week", "")
        labels.append(label)
        values.append(entry["value"])

    datasets = [
        {
            "label": _get_metric_display_name(metric),
            "data": values,
            "borderColor": "rgb(249, 115, 22)",  # primary color
            "backgroundColor": "rgba(249, 115, 22, 0.1)",
            "fill": True,
            "tension": 0.3,
        }
    ]

    # Add comparison data if YoY preset
    if date_range.get("compare_start") and date_range.get("compare_end"):
        compare_data = func(request.team, date_range["compare_start"], date_range["compare_end"])
        compare_values = [entry["value"] for entry in compare_data]

        # Pad or trim to match current period length
        while len(compare_values) < len(values):
            compare_values.append(0)
        compare_values = compare_values[: len(values)]

        datasets.append(
            {
                "label": f"{_get_metric_display_name(metric)} (Last Year)",
                "data": compare_values,
                "borderColor": "rgba(90, 153, 151, 0.7)",  # accent color
                "backgroundColor": "rgba(90, 153, 151, 0.1)",
                "fill": True,
                "tension": 0.3,
                "borderDash": [5, 5],  # Dashed line for comparison
            }
        )

    return JsonResponse(
        {
            "labels": labels,
            "datasets": datasets,
            "granularity": granularity,
            "metric": metric,
        }
    )


def _get_metric_display_name(metric: str) -> str:
    """Get display name for a metric."""
    names = {
        "cycle_time": "Cycle Time (hours)",
        "review_time": "Review Time (hours)",
        "pr_count": "PRs Merged",
        "ai_adoption": "AI Adoption (%)",
    }
    return names.get(metric, metric)


@team_admin_required
def wide_trend_chart(request: HttpRequest) -> HttpResponse:
    """Wide trend chart partial for HTMX loading.

    Returns the wide chart template with chart data for lazy loading.

    Query params:
        metric: cycle_time | review_time | pr_count | ai_adoption
    """
    date_range = get_extended_date_range(request)
    metric = request.GET.get("metric", "cycle_time")

    # Get the appropriate data based on granularity
    metric_functions = {
        "cycle_time": dashboard_service.get_monthly_cycle_time_trend,
        "review_time": dashboard_service.get_monthly_review_time_trend,
        "pr_count": dashboard_service.get_monthly_pr_count,
        "ai_adoption": dashboard_service.get_monthly_ai_adoption,
    }

    func = metric_functions.get(metric, metric_functions["cycle_time"])
    chart_data = func(request.team, date_range["start_date"], date_range["end_date"])

    # Add comparison if YoY
    comparison_data = None
    if date_range.get("compare_start") and date_range.get("compare_end"):
        comparison_data = func(request.team, date_range["compare_start"], date_range["compare_end"])

    context = {
        "chart_data": chart_data,
        "comparison_data": comparison_data,
        "metric": metric,
        "metric_display": _get_metric_display_name(metric),
        "granularity": date_range["granularity"],
        "start_date": date_range["start_date"],
        "end_date": date_range["end_date"],
    }

    return TemplateResponse(
        request,
        "metrics/analytics/trends/wide_chart.html",
        context,
    )
