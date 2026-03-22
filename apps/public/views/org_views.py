from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from apps.metrics.services.benchmark_service import get_benchmark_for_team
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
    all_public_repos = (
        PublicRepoProfile.objects.filter(
            org_profile=profile,
            is_public=True,
        )
        .select_related("stats")
        .order_by("display_order", "display_name")
    )
    # Benchmark comparisons for cycle_time and ai_adoption
    cycle_time_benchmark = get_benchmark_for_team(request.team, "cycle_time")
    ai_adoption_benchmark = get_benchmark_for_team(request.team, "ai_adoption")

    # Recent-change narrative from AI impact trends
    ai_impact = stats.ai_impact_data if stats.ai_impact_data else {}
    narrative = _build_recent_change_narrative(stats, ai_impact)

    context.update(
        {
            "repos": repos,
            "combined_trend_data": stats.combined_trend_data if stats.combined_trend_data else {},
            "ai_impact_data": ai_impact,
            "all_public_repos": all_public_repos,
            "cycle_time_benchmark": cycle_time_benchmark,
            "ai_adoption_benchmark": ai_adoption_benchmark,
            "recent_narrative": narrative,
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
            "page_canonical_url": absolute_url(reverse("public:org_detail", kwargs={"slug": slug})),
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


def _build_recent_change_narrative(stats, ai_impact: dict) -> str:
    """Build a short narrative about what changed recently for the org."""
    parts = []

    # Cadence change
    cadence = getattr(stats, "cadence_change_pct", None)
    if cadence and float(cadence) > 10:
        parts.append(f"PR volume is up {float(cadence):.0f}% compared to the prior period")
    elif cadence and float(cadence) < -10:
        parts.append(f"PR volume is down {abs(float(cadence)):.0f}% compared to the prior period")

    # AI impact on cycle time
    diff_pct = ai_impact.get("cycle_time_difference_pct")
    if diff_pct is not None and diff_pct < -10:
        parts.append(f"AI-assisted PRs ship {abs(diff_pct):.0f}% faster than non-AI PRs")
    elif diff_pct is not None and diff_pct > 10:
        parts.append(f"AI-assisted PRs take {diff_pct:.0f}% longer than non-AI PRs")

    return ". ".join(parts) + "." if parts else ""
