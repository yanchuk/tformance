"""PR list views - Pull Requests data explorer page."""

import csv

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.template.response import TemplateResponse

from apps.metrics.services.pr_list_service import (
    get_filter_options,
    get_pr_stats,
    get_prs_queryset,
)
from apps.teams.decorators import login_and_team_required

# Default page size for PR list
PAGE_SIZE = 50


def _get_filters_from_request(request: HttpRequest) -> dict:
    """Extract filter parameters from request GET params.

    Args:
        request: The HTTP request object

    Returns:
        Dictionary of filter parameters
    """
    # Define all supported filter keys
    filter_keys = [
        "repo",
        "author",
        "reviewer",
        "ai",
        "ai_tool",
        "size",
        "state",
        "has_jira",
        "date_from",
        "date_to",
    ]

    # Extract only filters that are present in GET params
    return {key: request.GET[key] for key in filter_keys if request.GET.get(key)}


def _get_pr_list_context(team, filters: dict, page_number: int = 1) -> dict:
    """Get common context data for PR list views.

    Args:
        team: The team to filter PRs for
        filters: Dictionary of filter parameters
        page_number: Page number for pagination

    Returns:
        Dictionary with prs, page_obj, stats, and filters
    """
    # Get filtered queryset
    prs = get_prs_queryset(team, filters).order_by("-merged_at", "-pr_created_at")

    # Get aggregate stats
    stats = get_pr_stats(prs)

    # Paginate
    paginator = Paginator(prs, PAGE_SIZE)
    page_obj = paginator.get_page(page_number)

    return {
        "prs": page_obj,
        "page_obj": page_obj,
        "stats": stats,
        "filters": filters,
    }


@login_and_team_required
def pr_list(request: HttpRequest) -> HttpResponse:
    """Main PR list page with filters and pagination."""
    team = request.team
    filters = _get_filters_from_request(request)
    page_number = request.GET.get("page", 1)

    # Get common context
    context = _get_pr_list_context(team, filters, page_number)

    # Add page-specific context
    context["active_page"] = "pull_requests"  # For tab highlighting
    context["days"] = 30  # Default for date filter in tabs
    context["filter_options"] = get_filter_options(team)

    # Return partial for HTMX requests
    if request.headers.get("HX-Request"):
        return TemplateResponse(
            request,
            "metrics/analytics/pull_requests.html#page-content",
            context,
        )

    return TemplateResponse(request, "metrics/analytics/pull_requests.html", context)


@login_and_team_required
def pr_list_table(request: HttpRequest) -> HttpResponse:
    """HTMX partial for PR list table - used for filter/pagination updates."""
    team = request.team
    filters = _get_filters_from_request(request)
    page_number = request.GET.get("page", 1)

    # Get common context
    context = _get_pr_list_context(team, filters, page_number)

    return TemplateResponse(
        request,
        "metrics/pull_requests/partials/table.html",
        context,
    )


class Echo:
    """An object that implements just the write method of the file-like interface."""

    def write(self, value):
        """Write the value by returning it."""
        return value


@login_and_team_required
def pr_list_export(request: HttpRequest) -> HttpResponse:
    """Export PR list to CSV."""
    team = request.team
    filters = _get_filters_from_request(request)

    # Get filtered queryset (no pagination for export)
    prs = get_prs_queryset(team, filters).order_by("-merged_at", "-pr_created_at")

    # CSV headers
    headers = [
        "Title",
        "Repository",
        "Author",
        "State",
        "Cycle Time (hours)",
        "Review Time (hours)",
        "Lines Added",
        "Lines Deleted",
        "Review Rounds",
        "Comments",
        "AI Assisted",
        "AI Tools",
        "Jira Key",
        "Created At",
        "Merged At",
        "GitHub URL",
    ]

    def generate_csv():
        """Generator for streaming CSV rows."""
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)

        # Write header
        yield writer.writerow(headers)

        # Write data rows
        for pr in prs.iterator():
            yield writer.writerow(
                [
                    pr.title,
                    pr.github_repo,
                    pr.author.display_name if pr.author else "",
                    pr.state,
                    str(pr.cycle_time_hours) if pr.cycle_time_hours else "",
                    str(pr.review_time_hours) if pr.review_time_hours else "",
                    pr.additions,
                    pr.deletions,
                    pr.review_rounds or 0,
                    pr.total_comments or 0,
                    "Yes" if pr.is_ai_assisted else "No",
                    ", ".join(pr.ai_tools_detected or []),
                    pr.jira_key or "",
                    pr.pr_created_at.isoformat() if pr.pr_created_at else "",
                    pr.merged_at.isoformat() if pr.merged_at else "",
                    pr.github_url or "",
                ]
            )

    response = StreamingHttpResponse(generate_csv(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="pull_requests.csv"'
    return response
