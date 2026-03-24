from datetime import date, timedelta
from typing import Any

from django.core.paginator import Paginator
from django.db.models import F, QuerySet
from django.utils import timezone

from apps.metrics.models import PullRequest
from apps.metrics.services.pr_list_service import get_filter_options, get_pr_stats, get_prs_queryset

PAGE_SIZE = 50
MIN_PUBLIC_DAYS = 7
MAX_PUBLIC_DAYS = 90

PUBLIC_SUMMARY_WINDOW_DAYS = 30
PUBLIC_TREND_WINDOW_DAYS = 90

SORT_FIELDS = {
    "cycle_time": "cycle_time_hours",
    "review_time": "review_time_hours",
    "lines": "additions",
    "comments": "total_comments",
    "merged": "merged_at",
}


def parse_public_days(request, default_days: int = 30) -> int:
    """Parse and clamp public days filter to a safe read-only range."""
    days = default_days
    raw = request.GET.get("days")
    if raw:
        try:
            parsed = int(raw)
            if parsed > 0:
                days = parsed
        except (TypeError, ValueError):
            pass
    return max(MIN_PUBLIC_DAYS, min(days, MAX_PUBLIC_DAYS))


def get_public_date_range(request, default_days: int = 30) -> tuple[int, date, date]:
    """Return (days, start_date, end_date) for public read-only pages."""
    days = parse_public_days(request, default_days=default_days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    return days, start_date, end_date


def get_public_summary_date_range() -> tuple[int, date, date]:
    """Return fixed 30-day (days, start_date, end_date) for public summary metrics."""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=PUBLIC_SUMMARY_WINDOW_DAYS)
    return PUBLIC_SUMMARY_WINDOW_DAYS, start_date, end_date


def get_public_trend_date_range() -> tuple[int, date, date]:
    """Return fixed 90-day (days, start_date, end_date) for public trend charts."""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=PUBLIC_TREND_WINDOW_DAYS)
    return PUBLIC_TREND_WINDOW_DAYS, start_date, end_date


def build_org_base_context(request, slug: str, active_public_tab: str) -> dict[str, Any]:
    """Build shared public org context for overview and analytics pages."""
    from apps.public.services import PublicAnalyticsService

    profile = request.public_profile
    stats = profile.stats
    days, _start_date, _end_date = get_public_date_range(request)

    industry_data = PublicAnalyticsService.get_industry_comparison(profile.industry)
    industry_stats = industry_data["stats"] if industry_data else {}

    return {
        "org_profile": profile,
        "public_stats": stats,
        "public_slug": slug,
        "days": days,
        "industry_stats": industry_stats,
        "active_public_tab": active_public_tab,
    }


def extract_pr_filters(request, default_days: int = 30) -> dict[str, Any]:
    filter_keys = [
        "repo",
        "author",
        "reviewer",
        "ai",
        "size",
        "state",
        "has_jira",
        "date_from",
        "date_to",
    ]
    filters = {key: request.GET[key] for key in filter_keys if request.GET.get(key)}

    days_param = request.GET.get("days")
    if filters.get("date_from") or filters.get("date_to"):
        return filters

    days = default_days
    if days_param:
        try:
            parsed_days = int(days_param)
            if parsed_days > 0:
                days = parsed_days
        except (TypeError, ValueError):
            pass

    today = date.today()
    filters["date_from"] = (today - timedelta(days=days)).isoformat()
    filters["date_to"] = today.isoformat()
    return filters


def extract_sort(request) -> tuple[str, str]:
    sort = request.GET.get("sort", "merged")
    order = request.GET.get("order", "desc")
    if sort not in SORT_FIELDS:
        sort = "merged"
    if order not in ("asc", "desc"):
        order = "desc"
    return sort, order


def apply_sort(queryset: QuerySet[PullRequest], sort: str, order: str) -> QuerySet[PullRequest]:
    sort_field = SORT_FIELDS.get(sort, "merged_at")
    if order == "desc":
        return queryset.order_by(F(sort_field).desc(nulls_last=True), "-pr_created_at")
    return queryset.order_by(F(sort_field).asc(nulls_last=True), "-pr_created_at")


def build_pr_list_context(request, github_repo: str | None = None) -> dict[str, Any]:
    """Build shared PR list context for both org and repo PR explorers.

    Args:
        request: Django HttpRequest with team set by decorator.
        github_repo: Optional owner/repo string to scope PRs to a specific repo.

    Returns:
        Dict with prs, page_obj, stats, filters, sort, order, days, filter_options,
        and selected_repo context variables.
    """
    filters = extract_pr_filters(request)
    sort, order = extract_sort(request)
    page_number = request.GET.get("page", 1)
    days, _start_date, _end_date = get_public_date_range(request)

    # If scoping to a specific repo, force the repo filter
    if github_repo:
        filters["repo"] = github_repo

    prs_qs = get_prs_queryset(request.team, filters)

    # Only show PRs from public repos in public views
    if hasattr(request, "public_profile") and request.public_profile:
        public_repos = request.public_profile.public_github_repos
        if public_repos:
            prs_qs = prs_qs.filter(github_repo__in=public_repos)

    prs_qs = apply_sort(prs_qs, sort, order)

    stats = get_pr_stats(prs_qs)
    paginator = Paginator(prs_qs, PAGE_SIZE)
    page_obj = paginator.get_page(page_number)

    return {
        "prs": page_obj,
        "page_obj": page_obj,
        "stats": stats,
        "filters": filters,
        "sort": sort,
        "order": order,
        "days": days,
        "filter_options": get_filter_options(request.team),
        "selected_repo": request.GET.get("repo", ""),
    }
