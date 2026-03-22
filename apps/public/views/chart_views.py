import json
from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from apps.metrics.services import chart_formatters, dashboard_service
from apps.metrics.services.dashboard.velocity_metrics import get_team_health_indicators
from apps.public.decorators import public_org_required

from .helpers import get_public_date_range


def _get_repo_filter(request: HttpRequest) -> str | None:
    repo = request.GET.get("repo", "")
    return repo if repo else None


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def public_ai_adoption_chart(request: HttpRequest, slug: str) -> HttpResponse:
    _days, start_date, end_date = get_public_date_range(request)
    repo = _get_repo_filter(request)
    data = dashboard_service.get_ai_adoption_trend(request.team, start_date, end_date, repo=repo)
    chart_data = chart_formatters.format_time_series(data)
    return TemplateResponse(request, "metrics/partials/ai_adoption_chart.html", {"chart_data": chart_data})


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def public_cycle_time_chart(request: HttpRequest, slug: str) -> HttpResponse:
    _days, start_date, end_date = get_public_date_range(request)
    repo = _get_repo_filter(request)
    data = dashboard_service.get_cycle_time_trend(request.team, start_date, end_date, repo=repo)
    chart_data = chart_formatters.format_time_series(data)
    return TemplateResponse(request, "metrics/partials/cycle_time_chart.html", {"chart_data": chart_data})


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def public_ai_quality_chart(request: HttpRequest, slug: str) -> HttpResponse:
    _days, start_date, end_date = get_public_date_range(request)
    repo = _get_repo_filter(request)
    impact_data = dashboard_service.get_ai_impact_stats(request.team, start_date, end_date, repo=repo)
    impact_data["non_ai_prs"] = impact_data["total_prs"] - impact_data["ai_prs"]
    return TemplateResponse(request, "metrics/partials/ai_quality_chart.html", {"impact_data": impact_data})


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def public_ai_tools_chart(request: HttpRequest, slug: str) -> HttpResponse:
    _days, start_date, end_date = get_public_date_range(request)
    repo = _get_repo_filter(request)
    chart_data = dashboard_service.get_ai_tool_breakdown(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(request, "metrics/partials/ai_tool_breakdown_chart.html", {"chart_data": chart_data})


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def public_pr_size_chart(request: HttpRequest, slug: str) -> HttpResponse:
    _days, start_date, end_date = get_public_date_range(request)
    repo = _get_repo_filter(request)
    data = dashboard_service.get_pr_size_distribution(request.team, start_date, end_date, repo=repo)
    max_count = max((item["count"] for item in data), default=1)
    return TemplateResponse(
        request,
        "public/partials/pr_size_chart.html",
        {"chart_data": data, "max_count": max_count, "selected_repo": repo or ""},
    )


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def public_review_distribution_chart(request: HttpRequest, slug: str) -> HttpResponse:
    days, start_date, end_date = get_public_date_range(request)
    repo = _get_repo_filter(request)
    limit = int(request.GET.get("limit") or 5)
    all_data = dashboard_service.get_review_distribution(request.team, start_date, end_date, repo=repo)
    total_count = len(all_data)
    data = all_data[:limit] if limit else all_data
    return TemplateResponse(
        request,
        "public/partials/review_distribution_chart.html",
        {
            "chart_data": data,
            "total_count": total_count,
            "showing_count": len(data),
            "has_more": total_count > len(data),
            "days": days,
        },
    )


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def public_key_metrics_cards(request: HttpRequest, slug: str) -> HttpResponse:
    _days, start_date, end_date = get_public_date_range(request)
    repo = _get_repo_filter(request)

    metrics = dashboard_service.get_key_metrics(request.team, start_date, end_date, repo=repo)

    period_length = (end_date - start_date).days
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length)
    previous_metrics = dashboard_service.get_key_metrics(request.team, prev_start, prev_end, repo=repo)

    sparkline_end = end_date
    sparkline_start = end_date - timedelta(days=84)
    sparklines = dashboard_service.get_sparkline_data(request.team, sparkline_start, sparkline_end, repo=repo)

    return TemplateResponse(
        request,
        "metrics/partials/key_metrics_cards.html",
        {"metrics": metrics, "previous_metrics": previous_metrics, "sparklines": sparklines},
    )


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def public_team_health_cards(request: HttpRequest, slug: str) -> HttpResponse:
    _days, start_date, end_date = get_public_date_range(request)
    indicators = get_team_health_indicators(request.team, start_date, end_date)
    # Public mode shows aggregate signals only, not individual reviewer identities.
    review_bottleneck = indicators.get("review_bottleneck", {})
    if review_bottleneck.get("detected"):
        review_bottleneck["reviewer"] = ""
    return TemplateResponse(request, "metrics/partials/team_health_indicators_card.html", {"indicators": indicators})


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def public_combined_trend_chart(request: HttpRequest, slug: str) -> HttpResponse:
    """HTMX partial for dual-axis AI adoption + delivery trend chart."""
    from apps.public.services.public_trends import build_combined_trend

    _days, start_date, end_date = get_public_date_range(request, default_days=90)
    repo = _get_repo_filter(request)
    secondary = request.GET.get("secondary", "cycle_time")
    if secondary not in ("cycle_time", "review_time"):
        secondary = "cycle_time"
    chart_data = build_combined_trend(request.team, start_date, end_date, secondary=secondary, repo=repo)
    return TemplateResponse(
        request,
        "public/partials/combined_trend_chart.html",
        {
            "chart_data": chart_data,
            "chart_data_json": json.dumps(chart_data),
        },
    )
