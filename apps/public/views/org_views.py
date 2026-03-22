from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from apps.public.decorators import public_org_required
from apps.public.models import PublicRepoProfile
from apps.web.meta import absolute_url

from .helpers import (
    build_org_base_context,
    build_pr_list_context,
)


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def org_detail(request, slug) -> HttpResponse:
    context = build_org_base_context(request, slug, active_public_tab="overview")
    profile = context["org_profile"]
    stats = context["public_stats"]
    repos = PublicRepoProfile.objects.filter(
        org_profile=profile,
        is_flagship=True,
        is_public=True,
    ).select_related("stats")
    context.update(
        {
            "repos": repos,
            "page_title": f"{profile.display_name} Engineering Metrics",
            "page_description": (
                f"See {profile.display_name} engineering benchmarks from "
                f"{stats.total_prs:,} merged PRs: {stats.ai_assisted_pct}% AI-assisted, "
                f"{stats.median_cycle_time_hours}h median cycle time, and flagship repo performance."
            ),
            "page_canonical_url": absolute_url(reverse("public:org_detail", kwargs={"slug": slug})),
            "page_image": absolute_url(f"/og/open-source/{slug}.png"),
        }
    )
    return TemplateResponse(request, "public/org_detail.html", context)


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def org_pr_list(request, slug) -> HttpResponse:
    context = build_pr_list_context(request)
    context.update(
        {
            "public_slug": slug,
            "active_public_tab": "pull_requests",
            "page_title": f"{request.public_profile.display_name} Pull Requests",
            "page_description": f"Public pull request explorer for {request.public_profile.display_name}.",
            "page_canonical_url": absolute_url(reverse("public:org_pr_list", kwargs={"slug": slug})),
            "page_robots": "noindex,follow",
        }
    )
    return TemplateResponse(request, "public/org_pr_list.html", context)


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def pr_list_table(request, slug) -> HttpResponse:
    context = build_pr_list_context(request)
    context["public_slug"] = slug
    return TemplateResponse(request, "public/partials/pr_table.html", context)
