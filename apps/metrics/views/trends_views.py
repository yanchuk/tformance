"""Trends analytics views - Long-horizon trend charts and YoY comparison."""

import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.response import TemplateResponse

from apps.metrics.services import dashboard_service
from apps.metrics.view_utils import get_extended_date_range
from apps.metrics.views.analytics_views import _get_repos_for_team
from apps.metrics.views.chart_views import _get_repo_filter
from apps.teams.decorators import team_admin_required

# Metric configuration with colors from chart-theme.js
METRIC_CONFIG = {
    "cycle_time": {
        "name": "Cycle Time",
        "unit": "hours",
        "color": "#F97316",  # primary - coral orange
        "yAxisID": "y",
    },
    "review_time": {
        "name": "Review Time",
        "unit": "hours",
        "color": "#2DD4BF",  # success - teal
        "yAxisID": "y",
    },
    "pr_count": {
        "name": "PRs Merged",
        "unit": "count",
        "color": "#C084FC",  # AI - purple
        "yAxisID": "y2",
    },
    "ai_adoption": {
        "name": "AI Adoption",
        "unit": "%",
        "color": "#FDA4AF",  # secondary - rose
        "yAxisID": "y2",
    },
}


def _get_trends_context(request: HttpRequest) -> dict:
    """Get common context for trends pages.

    Args:
        request: The HTTP request object

    Returns:
        Dictionary with common trends context
    """
    # For trends page, default to "Last 12 Months" preset with monthly granularity
    # if no date params are explicitly provided
    has_date_params = any(request.GET.get(p) for p in ["days", "start", "end", "preset"])
    if not has_date_params:
        # Use 12_months preset as default (rolling 365 days from today)
        date_range = get_extended_date_range(request, default_preset="12_months")
        # Respect explicit granularity parameter even with default date range
        explicit_granularity = request.GET.get("granularity")
        if explicit_granularity in ("weekly", "monthly"):
            date_range["granularity"] = explicit_granularity
        default_preset = "12_months"
    else:
        date_range = get_extended_date_range(request)
        default_preset = request.GET.get("preset", "")

    # Get available repositories for the team
    repos = _get_repos_for_team(request.team)

    # Get selected repo from request (validated against available repos)
    selected_repo = request.GET.get("repo", "")
    if selected_repo and selected_repo not in repos:
        selected_repo = ""  # Invalid repo, reset to all

    return {
        "active_tab": "metrics",
        "active_page": "trends",
        "days": date_range["days"],
        "start_date": date_range["start_date"],
        "end_date": date_range["end_date"],
        "granularity": date_range["granularity"],
        "preset": default_preset,
        "compare_start": date_range.get("compare_start"),
        "compare_end": date_range.get("compare_end"),
        # Repository filter
        "repos": json.dumps(repos),  # JSON for Alpine.js component
        "selected_repo": selected_repo,
    }


@team_admin_required
def trends_overview(request: HttpRequest) -> HttpResponse:
    """Trends Overview - Full-width trend charts for year-long analysis.

    Main trends dashboard with metric selector and wide charts for
    viewing long-horizon trends like YoY comparison.
    Admin-only view.
    """
    context = _get_trends_context(request)

    # Default metrics for initial load (support comma-separated list)
    metrics_param = request.GET.get("metrics", "cycle_time")
    selected_metrics = [m.strip() for m in metrics_param.split(",") if m.strip() in METRIC_CONFIG]
    if not selected_metrics:
        selected_metrics = ["cycle_time"]

    context["selected_metrics"] = selected_metrics
    context["default_metric"] = selected_metrics[0]  # For backward compatibility
    context["available_metrics"] = [
        {"id": key, "name": cfg["name"], "unit": cfg["unit"], "color": cfg["color"]}
        for key, cfg in METRIC_CONFIG.items()
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
        "pr_count": dashboard_service.get_weekly_pr_count,
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

    # Get repo filter
    repo = _get_repo_filter(request)

    # Get current period data
    current_data = func(request.team, start_date, end_date, repo=repo)

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
        compare_data = func(request.team, date_range["compare_start"], date_range["compare_end"], repo=repo)
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
    Supports multiple metrics for comparison.

    Query params:
        metric: single metric (backward compat)
        metrics: comma-separated list of metrics (e.g., cycle_time,review_time)
    """
    date_range = get_extended_date_range(request)

    # Support both single metric and comma-separated metrics
    metrics_param = request.GET.get("metrics", request.GET.get("metric", "cycle_time"))
    metrics = [m.strip() for m in metrics_param.split(",") if m.strip() in METRIC_CONFIG]
    if not metrics:
        metrics = ["cycle_time"]
    # Limit to 3 metrics for visual clarity
    metrics = metrics[:3]

    # Get granularity from request
    granularity = date_range["granularity"]

    # Get the appropriate data based on granularity
    if granularity == "weekly":
        metric_functions = {
            "cycle_time": dashboard_service.get_cycle_time_trend,
            "review_time": dashboard_service.get_review_time_trend,
            "pr_count": dashboard_service.get_weekly_pr_count,
            "ai_adoption": dashboard_service.get_ai_adoption_trend,
        }
    else:  # monthly
        metric_functions = {
            "cycle_time": dashboard_service.get_monthly_cycle_time_trend,
            "review_time": dashboard_service.get_monthly_review_time_trend,
            "pr_count": dashboard_service.get_monthly_pr_count,
            "ai_adoption": dashboard_service.get_monthly_ai_adoption,
        }

    # Get repo filter
    repo = _get_repo_filter(request)

    # Build multi-metric chart data
    all_datasets = []
    labels = None
    has_y2_axis = False

    for metric in metrics:
        config = METRIC_CONFIG.get(metric, METRIC_CONFIG["cycle_time"])
        func = metric_functions.get(metric, metric_functions["cycle_time"])
        data = func(request.team, date_range["start_date"], date_range["end_date"], repo=repo)

        # Use first metric's labels
        if labels is None:
            labels = [entry.get("month") or entry.get("week", "") for entry in data]

        values = [entry["value"] for entry in data]

        # Check if we need secondary Y axis
        if config["yAxisID"] == "y2":
            has_y2_axis = True

        all_datasets.append(
            {
                "metric": metric,
                "label": config["name"],
                "unit": config["unit"],
                "color": config["color"],
                "yAxisID": config["yAxisID"],
                "data": values,
            }
        )

    # Build chart data structure for JavaScript
    chart_data = {
        "labels": labels or [],
        "datasets": all_datasets,
        "hasY2Axis": has_y2_axis,
    }

    # Add comparison if YoY (only for first metric to avoid clutter)
    comparison_data = None
    if date_range.get("compare_start") and date_range.get("compare_end") and len(metrics) == 1:
        metric = metrics[0]
        func = metric_functions.get(metric, metric_functions["cycle_time"])
        comparison_data = func(request.team, date_range["compare_start"], date_range["compare_end"], repo=repo)

    # Build display info
    if len(metrics) == 1:
        metric_display = _get_metric_display_name(metrics[0])
    else:
        metric_display = " vs ".join(METRIC_CONFIG[m]["name"] for m in metrics)

    context = {
        "chart_data": chart_data,  # json_script filter will serialize in template
        "comparison_data": comparison_data,
        "metrics": metrics,
        "metric": metrics[0],  # backward compat
        "metric_display": metric_display,
        "granularity": date_range["granularity"],
        "start_date": date_range["start_date"],
        "end_date": date_range["end_date"],
        "is_multi_metric": len(metrics) > 1,
    }

    return TemplateResponse(
        request,
        "metrics/analytics/trends/wide_chart.html",
        context,
    )


# PR Type configuration with colors
PR_TYPE_CONFIG = {
    "feature": {"name": "Feature", "color": "#F97316"},  # primary orange
    "bugfix": {"name": "Bugfix", "color": "#F87171"},  # soft red
    "refactor": {"name": "Refactor", "color": "#2DD4BF"},  # teal
    "docs": {"name": "Docs", "color": "#60A5FA"},  # blue
    "test": {"name": "Test", "color": "#C084FC"},  # purple
    "chore": {"name": "Chore", "color": "#A3A3A3"},  # gray
    "ci": {"name": "CI/CD", "color": "#FBBF24"},  # amber
    "unknown": {"name": "Other", "color": "#6B7280"},  # dark gray
}


@team_admin_required
def pr_type_breakdown_chart(request: HttpRequest) -> HttpResponse:
    """PR type breakdown chart partial for HTMX loading.

    Shows stacked bar chart of PR types over time.
    """
    date_range = get_extended_date_range(request)
    granularity = date_range["granularity"]

    # Get and validate AI filter parameter
    ai_filter = request.GET.get("ai_filter", "all")
    if ai_filter not in ("all", "yes", "no"):
        ai_filter = "all"

    # Get repo filter
    repo = _get_repo_filter(request)

    # Get type trend data based on granularity
    if granularity == "weekly":
        type_data = dashboard_service.get_weekly_pr_type_trend(
            request.team, date_range["start_date"], date_range["end_date"], ai_assisted=ai_filter, repo=repo
        )
    else:
        type_data = dashboard_service.get_monthly_pr_type_trend(
            request.team, date_range["start_date"], date_range["end_date"], ai_assisted=ai_filter, repo=repo
        )

    # Build datasets for chart
    datasets = []
    labels = None
    for pr_type, entries in type_data.items():
        config = PR_TYPE_CONFIG.get(pr_type, PR_TYPE_CONFIG["unknown"])
        if labels is None and entries:
            labels = [e.get("month") or e.get("week", "") for e in entries]
        datasets.append(
            {
                "type": pr_type,
                "label": config["name"],
                "color": config["color"],
                "data": [e["value"] for e in entries],
            }
        )

    chart_data = {
        "labels": labels or [],
        "datasets": datasets,
    }

    # Get overall breakdown for the period (also filtered)
    breakdown = dashboard_service.get_pr_type_breakdown(
        request.team, date_range["start_date"], date_range["end_date"], ai_assisted=ai_filter, repo=repo
    )

    context = {
        "chart_data": chart_data,
        "breakdown": breakdown,
        "granularity": granularity,
        "start_date": date_range["start_date"],
        "end_date": date_range["end_date"],
        "pr_type_config": PR_TYPE_CONFIG,
        "ai_filter": ai_filter,
    }

    return TemplateResponse(
        request,
        "metrics/analytics/trends/pr_type_chart.html",
        context,
    )


# Technology category configuration with colors
TECH_CONFIG = {
    "frontend": {"name": "Frontend", "color": "#60A5FA"},  # blue
    "backend": {"name": "Backend", "color": "#2DD4BF"},  # teal
    "devops": {"name": "DevOps", "color": "#FBBF24"},  # amber
    "mobile": {"name": "Mobile", "color": "#C084FC"},  # purple
    "data": {"name": "Data", "color": "#F97316"},  # orange
    "test": {"name": "Test", "color": "#A3A3A3"},  # gray
    "docs": {"name": "Docs", "color": "#FDA4AF"},  # rose
    "config": {"name": "Config", "color": "#6B7280"},  # dark gray
    "javascript": {"name": "JS/TS", "color": "#FACC15"},  # yellow
    "other": {"name": "Other", "color": "#9CA3AF"},  # neutral gray
    # LLM sometimes returns PR types as tech categories - handle gracefully
    "chore": {"name": "Chore", "color": "#78716C"},  # stone
    "ci": {"name": "CI/CD", "color": "#F59E0B"},  # amber (matches devops family)
}


@team_admin_required
def tech_breakdown_chart(request: HttpRequest) -> HttpResponse:
    """Technology breakdown chart partial for HTMX loading.

    Shows stacked bar chart of tech categories over time.
    """
    date_range = get_extended_date_range(request)
    granularity = date_range["granularity"]

    # Get and validate AI filter parameter
    ai_filter = request.GET.get("ai_filter", "all")
    if ai_filter not in ("all", "yes", "no"):
        ai_filter = "all"

    # Get repo filter
    repo = _get_repo_filter(request)

    # Get tech trend data based on granularity
    if granularity == "weekly":
        tech_data = dashboard_service.get_weekly_tech_trend(
            request.team, date_range["start_date"], date_range["end_date"], ai_assisted=ai_filter, repo=repo
        )
    else:
        tech_data = dashboard_service.get_monthly_tech_trend(
            request.team, date_range["start_date"], date_range["end_date"], ai_assisted=ai_filter, repo=repo
        )

    # Build datasets for chart
    datasets = []
    labels = None
    for category, entries in tech_data.items():
        config = TECH_CONFIG.get(category, TECH_CONFIG["other"])
        if labels is None and entries:
            labels = [e.get("month") or e.get("week", "") for e in entries]
        datasets.append(
            {
                "category": category,
                "label": config["name"],
                "color": config["color"],
                "data": [e["value"] for e in entries],
            }
        )

    chart_data = {
        "labels": labels or [],
        "datasets": datasets,
    }

    # Get overall breakdown for the period (also filtered)
    breakdown = dashboard_service.get_tech_breakdown(
        request.team, date_range["start_date"], date_range["end_date"], ai_assisted=ai_filter, repo=repo
    )

    context = {
        "chart_data": chart_data,
        "breakdown": breakdown,
        "granularity": granularity,
        "start_date": date_range["start_date"],
        "end_date": date_range["end_date"],
        "tech_config": TECH_CONFIG,
        "ai_filter": ai_filter,
    }

    return TemplateResponse(
        request,
        "metrics/analytics/trends/tech_chart.html",
        context,
    )
