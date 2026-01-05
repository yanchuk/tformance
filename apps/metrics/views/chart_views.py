"""Chart partial views for HTMX endpoints."""

from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from apps.metrics.services import chart_formatters, dashboard_service
from apps.metrics.view_utils import get_date_range_from_request
from apps.teams.decorators import login_and_team_required, team_admin_required


def _get_repo_filter(request: HttpRequest) -> str | None:
    """Extract repository filter from request.

    Args:
        request: HTTP request

    Returns:
        Repository name (owner/repo format) or None if not specified
    """
    repo = request.GET.get("repo", "")
    return repo if repo else None


@team_admin_required
def ai_adoption_chart(request: HttpRequest) -> HttpResponse:
    """AI adoption trend line chart (admin only)."""
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    data = dashboard_service.get_ai_adoption_trend(request.team, start_date, end_date, repo=repo)
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
    repo = _get_repo_filter(request)
    chart_data = dashboard_service.get_ai_quality_comparison(request.team, start_date, end_date, repo=repo)
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
    repo = _get_repo_filter(request)
    data = dashboard_service.get_cycle_time_trend(request.team, start_date, end_date, repo=repo)
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
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_key_metrics(request.team, start_date, end_date, repo=repo)

    # Calculate previous period for comparison
    period_length = (end_date - start_date).days
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length)
    previous_metrics = dashboard_service.get_key_metrics(request.team, prev_start, prev_end, repo=repo)

    # Get sparkline data (12 weeks of weekly data)
    sparkline_end = end_date
    sparkline_start = end_date - timedelta(days=84)  # 12 weeks
    sparklines = dashboard_service.get_sparkline_data(request.team, sparkline_start, sparkline_end, repo=repo)

    return TemplateResponse(
        request,
        "metrics/partials/key_metrics_cards.html",
        {
            "metrics": metrics,
            "previous_metrics": previous_metrics,
            "sparklines": sparklines,
        },
    )


@team_admin_required
def team_breakdown_table(request: HttpRequest) -> HttpResponse:
    """Team breakdown table (admin only)."""
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    days = int(request.GET.get("days") or 30)
    sort = request.GET.get("sort", "prs_merged")
    order = request.GET.get("order", "desc")

    # Validate sort field (must match dashboard_service.get_team_breakdown SORT_FIELDS)
    ALLOWED_SORT_FIELDS = {"prs_merged", "cycle_time", "ai_pct", "name", "pr_size", "reviews", "response_time"}
    if sort not in ALLOWED_SORT_FIELDS:
        sort = "prs_merged"

    # Validate order
    if order not in ("asc", "desc"):
        order = "desc"

    rows = dashboard_service.get_team_breakdown(
        request.team, start_date, end_date, sort_by=sort, order=order, repo=repo
    )
    team_averages = dashboard_service.get_team_averages(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/team_breakdown_table.html",
        {
            "rows": rows,
            "sort": sort,
            "order": order,
            "days": days,
            "selected_repo": repo or "",
            "team_averages": team_averages,
        },
    )


@login_and_team_required
def leaderboard_table(request: HttpRequest) -> HttpResponse:
    """AI detective leaderboard (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    rows = dashboard_service.get_ai_detective_leaderboard(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/leaderboard_table.html",
        {
            "rows": rows,
        },
    )


@login_and_team_required
def review_distribution_chart(request: HttpRequest) -> HttpResponse:
    """Review distribution by reviewer (all members).

    Displays top 5 reviewers by default for a cleaner dashboard view.
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    limit = int(request.GET.get("limit") or 5)  # Default to top 5 reviewers
    days = int(request.GET.get("days") or 30)

    # Get all reviewers first for total count, then slice for display
    all_data = dashboard_service.get_review_distribution(request.team, start_date, end_date, repo=repo)
    total_count = len(all_data)
    data = all_data[:limit] if limit else all_data

    # Check for bottleneck (reviewer with >3x average pending reviews)
    bottleneck = dashboard_service.detect_review_bottleneck(request.team, start_date, end_date, repo=repo)

    return TemplateResponse(
        request,
        "metrics/partials/review_distribution_chart.html",
        {
            "chart_data": data,
            "bottleneck": bottleneck,
            "total_count": total_count,
            "showing_count": len(data),
            "has_more": total_count > len(data),
            "days": days,
        },
    )


@login_and_team_required
def recent_prs_table(request: HttpRequest) -> HttpResponse:
    """Recent PRs with AI status (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    rows = dashboard_service.get_recent_prs(request.team, start_date, end_date, limit=10, repo=repo)
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
    repo = _get_repo_filter(request)
    data = dashboard_service.get_review_time_trend(request.team, start_date, end_date, repo=repo)
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
    repo = _get_repo_filter(request)
    data = dashboard_service.get_pr_size_distribution(request.team, start_date, end_date, repo=repo)
    max_count = max((item["count"] for item in data), default=1)
    return TemplateResponse(
        request,
        "metrics/partials/pr_size_chart.html",
        {
            "chart_data": data,
            "max_count": max_count,
            "selected_repo": repo or "",
        },
    )


@login_and_team_required
def revert_rate_card(request: HttpRequest) -> HttpResponse:
    """Revert and hotfix rate stats (all members)."""
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    stats = dashboard_service.get_revert_hotfix_stats(request.team, start_date, end_date, repo=repo)
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
    repo = _get_repo_filter(request)
    rows = dashboard_service.get_unlinked_prs(request.team, start_date, end_date, limit=10, repo=repo)
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
    repo = _get_repo_filter(request)
    rows = dashboard_service.get_reviewer_workload(request.team, start_date, end_date, repo=repo)
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
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_copilot_metrics(request.team, start_date, end_date, repo=repo)
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
    repo = _get_repo_filter(request)
    data = dashboard_service.get_copilot_trend(request.team, start_date, end_date, repo=repo)
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
    repo = _get_repo_filter(request)
    rows = dashboard_service.get_copilot_by_member(request.team, start_date, end_date, repo=repo)
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
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_iteration_metrics(request.team, start_date, end_date, repo=repo)
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


@login_and_team_required
def cicd_pass_rate_card(request: HttpRequest) -> HttpResponse:
    """CI/CD pass rate metrics card (all members).

    Shows overall CI/CD health including pass rate and top failing checks.
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_cicd_pass_rate(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/cicd_pass_rate_card.html",
        {
            "metrics": metrics,
        },
    )


@login_and_team_required
def deployment_metrics_card(request: HttpRequest) -> HttpResponse:
    """Deployment metrics card (all members).

    Shows DORA-style deployment frequency and success metrics.
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_deployment_metrics(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/deployment_metrics_card.html",
        {
            "metrics": metrics,
        },
    )


@login_and_team_required
def file_category_card(request: HttpRequest) -> HttpResponse:
    """File category breakdown card (all members).

    Shows distribution of file changes by category (frontend, backend, etc).
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_file_category_breakdown(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/file_category_card.html",
        {
            "metrics": metrics,
        },
    )


# =============================================================================
# AI Detection Metrics (from PR content analysis)
# =============================================================================


@team_admin_required
def ai_detected_metrics_card(request: HttpRequest) -> HttpResponse:
    """AI detection metrics card (admin only).

    Shows AI-assisted PRs detected from content analysis (PR body, commit messages).
    Distinct from survey-based AI tracking.
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_ai_detected_metrics(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/ai_detected_metrics_card.html",
        {
            "metrics": metrics,
        },
    )


@team_admin_required
def ai_tool_breakdown_chart(request: HttpRequest) -> HttpResponse:
    """AI tool breakdown chart (admin only).

    Shows which AI tools are being used (Claude, Copilot, Cursor, etc.)
    based on detected signatures in PR content.
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    chart_data = dashboard_service.get_ai_tool_breakdown(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/ai_tool_breakdown_chart.html",
        {
            "chart_data": chart_data,
        },
    )


@team_admin_required
def ai_bot_reviews_card(request: HttpRequest) -> HttpResponse:
    """AI bot reviews card (admin only).

    Shows statistics about AI bot reviewers (CodeRabbit, Copilot, etc.)
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_ai_bot_review_stats(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/ai_bot_reviews_card.html",
        {
            "metrics": metrics,
        },
    )


# =============================================================================
# Survey Channel Metrics (from PR survey system)
# =============================================================================


@team_admin_required
def survey_channel_distribution_card(request: HttpRequest) -> HttpResponse:
    """Survey response channel distribution card (admin only).

    Shows breakdown of survey responses by channel (GitHub, Slack, Web, Auto-detected).
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_response_channel_distribution(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/survey_channel_distribution_card.html",
        {
            "metrics": metrics,
        },
    )


@team_admin_required
def survey_ai_detection_card(request: HttpRequest) -> HttpResponse:
    """Survey AI detection metrics card (admin only).

    Shows auto-detected vs self-reported AI usage stats from surveys.
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_ai_detection_metrics(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/survey_ai_detection_card.html",
        {
            "metrics": metrics,
        },
    )


@team_admin_required
def survey_response_time_card(request: HttpRequest) -> HttpResponse:
    """Survey response time metrics card (admin only).

    Shows average survey response times by channel.
    """
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)
    metrics = dashboard_service.get_response_time_metrics(request.team, start_date, end_date, repo=repo)
    return TemplateResponse(
        request,
        "metrics/partials/survey_response_time_card.html",
        {
            "metrics": metrics,
        },
    )


# =============================================================================
# Industry Benchmarks API
# =============================================================================


@login_and_team_required
def benchmark_data(request: HttpRequest, metric: str) -> HttpResponse:
    """Get benchmark comparison data for a metric (JSON API).

    Args:
        metric: One of 'cycle_time', 'review_time', 'pr_count', 'ai_adoption'

    Returns:
        JSON response with team value, percentile, benchmark data, and interpretation
    """
    from django.http import JsonResponse

    from apps.metrics.services import benchmark_service

    valid_metrics = ["cycle_time", "review_time", "pr_count", "ai_adoption", "deployment_freq"]
    if metric not in valid_metrics:
        return JsonResponse({"error": f"Invalid metric: {metric}"}, status=400)

    days = int(request.GET.get("days") or 30)
    result = benchmark_service.get_benchmark_for_team(request.team, metric, days)

    # Convert Decimal to float for JSON serialization
    if result["team_value"] is not None:
        result["team_value"] = float(result["team_value"])

    return JsonResponse(result)


@login_and_team_required
def benchmark_panel(request: HttpRequest, metric: str) -> HttpResponse:
    """Render benchmark panel HTML partial for HTMX.

    Args:
        metric: One of 'cycle_time', 'review_time', 'pr_count', 'ai_adoption'

    Returns:
        HTML partial with benchmark visualization
    """
    from apps.metrics.services import benchmark_service

    valid_metrics = ["cycle_time", "review_time", "pr_count", "ai_adoption", "deployment_freq"]
    if metric not in valid_metrics:
        return TemplateResponse(
            request,
            "metrics/analytics/trends/benchmark_panel.html",
            {"benchmark": None, "metric": metric},
        )

    days = int(request.GET.get("days") or 30)

    try:
        result = benchmark_service.get_benchmark_for_team(request.team, metric, days)
    except Exception:
        # Return empty state on any service error
        return TemplateResponse(
            request,
            "metrics/analytics/trends/benchmark_panel.html",
            {"benchmark": None, "metric": metric},
        )

    # Convert Decimal to float for display
    if result["team_value"] is not None:
        result["team_value"] = float(result["team_value"])

    # Extract benchmark data and add has_data flag
    benchmark_data = result.get("benchmark", {})
    if benchmark_data:
        # Convert any numeric values to float
        benchmark_data = {k: float(v) if isinstance(v, (int, float)) else v for k, v in benchmark_data.items()}

    # Build template-friendly context
    # Template expects: benchmark.has_data, benchmark.benchmarks (plural),
    # benchmark.team_size_bucket, benchmark.source
    has_data = result["team_value"] is not None and bool(benchmark_data)

    # Add unit based on metric type
    unit_map = {
        "cycle_time": "hours",
        "review_time": "hours",
        "pr_count": "PRs/week",
        "ai_adoption": "%",
        "deployment_freq": "/week",
    }

    template_context = {
        "has_data": has_data,
        "team_value": result["team_value"],
        "percentile": result["percentile"],
        "interpretation": result["interpretation"],
        "unit": unit_map.get(metric, ""),
        # Flatten benchmark data to top level for template
        "benchmarks": benchmark_data,  # Template uses plural "benchmarks"
        "team_size_bucket": benchmark_data.get("team_size_bucket", "small"),
        "source": benchmark_data.get("source", "DORA"),
    }

    return TemplateResponse(
        request,
        "metrics/analytics/trends/benchmark_panel.html",
        {"benchmark": template_context, "metric": metric},
    )


@login_and_team_required
def jira_linkage_chart(request: HttpRequest) -> HttpResponse:
    """Jira PR linkage donut chart with trend."""
    start_date, end_date = get_date_range_from_request(request)
    linkage_data = dashboard_service.get_pr_jira_correlation(request.team, start_date, end_date)
    trend_data = dashboard_service.get_linkage_trend(request.team, weeks=4)
    return TemplateResponse(
        request,
        "metrics/partials/jira_linkage_chart.html",
        {
            "linkage_data": linkage_data,
            "trend_data": trend_data,
        },
    )


@login_and_team_required
def sp_correlation_chart(request: HttpRequest) -> HttpResponse:
    """Story Point correlation chart - shows estimated vs actual hours by SP bucket."""
    start_date, end_date = get_date_range_from_request(request)
    correlation_data = dashboard_service.get_story_point_correlation(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/sp_correlation_chart.html",
        {"correlation_data": correlation_data},
    )


@team_admin_required
def needs_attention_view(request: HttpRequest) -> HttpResponse:
    """Needs attention PR list (admin only).

    Returns summary badges showing counts by issue type, with expandable details.
    Option A approach: Quick glance at totals, click to see PRs.
    """
    start_date, end_date = get_date_range_from_request(request)

    # Get all flagged PRs (up to 100 for counting)
    result = dashboard_service.get_needs_attention_prs(request.team, start_date, end_date, page=1, per_page=100)

    # Group by issue type for summary badges
    issue_counts = {}
    for pr in result["items"]:
        issue_type = pr["issue_type"]
        if issue_type not in issue_counts:
            issue_counts[issue_type] = 0
        issue_counts[issue_type] += 1

    # Get days param for links
    days = int(request.GET.get("days") or 30)

    # Define badge order, labels, colors, and tooltips for horizontal bar
    badge_config = {
        "revert": {
            "label": "Reverts",
            "priority": 1,
            "color": "#ef4444",  # red
            "tooltip": "Reverted PRs indicate rolled-back changes",
        },
        "hotfix": {
            "label": "Hotfixes",
            "priority": 2,
            "color": "#f59e0b",  # amber
            "tooltip": "Emergency fixes that bypassed normal review",
        },
        "long_cycle": {
            "label": "Slow",
            "priority": 3,
            "color": "#06b6d4",  # cyan
            "tooltip": "PRs with cycle time >2x team average",
        },
        "large_pr": {
            "label": "Large",
            "priority": 4,
            "color": "#8b5cf6",  # violet
            "tooltip": "Large PRs (>500 lines) are harder to review",
        },
        "missing_jira": {
            "label": "No Jira",
            "priority": 5,
            "color": "#6b7280",  # gray
            "tooltip": "PRs without linked Jira tickets",
        },
    }

    # Build ordered summary for template with percentages
    total = result["total"] or 1  # avoid division by zero
    summary = []
    for issue_type, config in sorted(badge_config.items(), key=lambda x: x[1]["priority"]):
        count = issue_counts.get(issue_type, 0)
        if count > 0:
            summary.append(
                {
                    "type": issue_type,
                    "label": config["label"],
                    "color": config["color"],
                    "tooltip": config["tooltip"],
                    "count": count,
                    "percent": round(count / total * 100, 1),
                }
            )

    # Top 5 PRs for expanded view
    top_prs = result["items"][:5]

    return TemplateResponse(
        request,
        "metrics/partials/needs_attention.html",
        {
            "summary": summary,
            "prs": top_prs,
            "total_count": result["total"],
            "days": days,
        },
    )


@team_admin_required
def ai_impact_view(request: HttpRequest) -> HttpResponse:
    """AI impact stats comparison (admin only).

    Returns AI adoption % and cycle time comparison.
    """
    start_date, end_date = get_date_range_from_request(request)

    stats = dashboard_service.get_ai_impact_stats(request.team, start_date, end_date)

    return TemplateResponse(
        request,
        "metrics/partials/ai_impact.html",
        {
            "stats": stats,
        },
    )


@team_admin_required
def team_velocity_view(request: HttpRequest) -> HttpResponse:
    """Team velocity / top contributors (admin only).

    Returns top N contributors by PR count with avg cycle time.
    """
    start_date, end_date = get_date_range_from_request(request)
    limit = int(request.GET.get("limit") or 5)
    days = int(request.GET.get("days") or 30)

    contributors = dashboard_service.get_team_velocity(request.team, start_date, end_date, limit=limit)

    return TemplateResponse(
        request,
        "metrics/partials/team_velocity.html",
        {
            "contributors": contributors,
            "days": days,
        },
    )


@login_and_team_required
def velocity_trend_chart(request: HttpRequest) -> HttpResponse:
    """Velocity trend chart - shows story points completed over time."""
    start_date, end_date = get_date_range_from_request(request)
    velocity_data = dashboard_service.get_velocity_trend(request.team, start_date, end_date)
    return TemplateResponse(
        request,
        "metrics/partials/velocity_trend_chart.html",
        {"velocity_data": velocity_data},
    )
