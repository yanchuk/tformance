from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from apps.public.forms import RepoRequestForm
from apps.public.models import INDUSTRY_CHOICES
from apps.public.services import PublicAnalyticsService
from apps.web.meta import absolute_url


@require_http_methods(["GET"])
def directory(request) -> HttpResponse:
    year_param = request.GET.get("year", "")
    year = int(year_param) if year_param.isdigit() else None

    orgs = PublicAnalyticsService.get_directory_data(year=year)
    global_stats = PublicAnalyticsService.get_global_stats()

    industry_filter = request.GET.get("industry", "")
    if industry_filter:
        orgs = [org for org in orgs if org["industry"] == industry_filter]

    sort_by = request.GET.get("sort", "total_prs")
    order = request.GET.get("order", "")
    sort_options = {
        "total_prs": lambda org: org["total_prs"],
        "ai_adoption": lambda org: org["ai_assisted_pct"],
        "cycle_time": lambda org: org["median_cycle_time_hours"],
        "review_time": lambda org: org["median_review_time_hours"],
        "contributors": lambda org: org["active_contributors_90d"],
        "name": lambda org: org["display_name"].lower(),
    }
    sort_fn = sort_options.get(sort_by, sort_options["total_prs"])
    # Default order: desc for numeric, asc for name
    if not order:
        order = "asc" if sort_by == "name" else "desc"
    reverse_sort = order == "desc"
    orgs = sorted(orgs, key=sort_fn, reverse=reverse_sort)

    # Build scatter chart data (review 16A -- inline, no separate method)
    scatter_data = [
        {
            "x": float(org["ai_assisted_pct"]),
            "y": float(org["median_cycle_time_hours"]),
            "label": org["display_name"],
            "prs": org["total_prs"],
            "industry": org["industry"],
        }
        for org in orgs
    ]

    current_year = timezone.now().year
    context = {
        "orgs": orgs,
        "global_stats": global_stats,
        "industries": INDUSTRY_CHOICES,
        "current_industry": industry_filter,
        "current_sort": sort_by,
        "current_order": order,
        "current_year": year_param,
        "year_options": [
            ("", "All Years"),
            (str(current_year), str(current_year)),
            (str(current_year - 1), str(current_year - 1)),
        ],
        "sort_options": [
            ("total_prs", "Most PRs"),
            ("ai_adoption", "AI Adoption"),
            ("cycle_time", "Cycle Time"),
            ("review_time", "Review Time"),
            ("contributors", "Contributors"),
            ("name", "Name"),
        ],
        "scatter_data": scatter_data,
        "industry_benchmarks": PublicAnalyticsService.get_industry_benchmarks(),
        "aggregate_trend": PublicAnalyticsService.get_directory_aggregate_trend(),
        "page_title": "Open Source Engineering Benchmarks",
        "page_description": (
            f"Engineering metrics from {global_stats['org_count']} open source projects. "
            "Compare AI adoption, cycle time, and team velocity across industries."
        ),
        "page_canonical_url": absolute_url(reverse("public:directory")),
    }

    if request.headers.get("HX-Request"):
        return TemplateResponse(request, "public/_directory_list.html", context)
    return TemplateResponse(request, "public/directory.html", context)


@cache_page(3600)
@require_http_methods(["GET"])
def industry_comparison(request, industry) -> HttpResponse:
    data = PublicAnalyticsService.get_industry_comparison(industry)
    if data is None:
        raise Http404

    context = {
        "data": data,
        "industry_key": data["industry_key"],
        "industry_display": data["industry_display"],
        "stats": data["stats"],
        "orgs": data["orgs"],
        "page_title": f"{data['industry_display']} Engineering Benchmarks",
        "page_description": (
            f"{data['industry_display']} engineering benchmarks: "
            f"{data['stats']['org_count']} projects, {data['stats']['avg_ai_pct']}% average AI adoption."
        ),
        "page_canonical_url": absolute_url(reverse("public:industry", kwargs={"industry": industry})),
    }
    return TemplateResponse(request, "public/industry.html", context)


@require_http_methods(["GET", "POST"])
def request_repo(request) -> HttpResponse:
    if request.method == "POST":
        form = RepoRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("public:request_success")
    else:
        form = RepoRequestForm()

    return TemplateResponse(
        request,
        "public/request_repo.html",
        {
            "form": form,
            "page_title": "Request Your Repository",
            "page_description": "Request your open source repository be added to Tformance public analytics.",
            "page_canonical_url": absolute_url(reverse("public:request_repo")),
        },
    )


@cache_page(3600)
@require_http_methods(["GET"])
def request_success(request) -> HttpResponse:
    return TemplateResponse(
        request,
        "public/request_success.html",
        {
            "page_title": "Request Submitted",
            "page_description": "Your repository request was submitted successfully.",
            "page_canonical_url": absolute_url(reverse("public:request_success")),
        },
    )
