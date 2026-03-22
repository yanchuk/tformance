from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.public.decorators import public_repo_required
from apps.public.models import PublicRepoInsight, PublicRepoStats
from apps.web.meta import absolute_url

from .helpers import build_pr_list_context


@require_http_methods(["GET"])
@public_repo_required
def repo_detail(request: HttpRequest, slug: str, repo_slug: str) -> HttpResponse:
    """Canonical repo landing page — server-rendered from stored snapshots."""
    repo_profile = request.repo_profile
    org_profile = request.public_profile

    # Load pre-computed stats (the only query needed)
    try:
        stats = repo_profile.stats
    except PublicRepoStats.DoesNotExist:
        stats = None

    # Load current insight
    insight = PublicRepoInsight.objects.filter(
        repo_profile=repo_profile,
        is_current=True,
    ).first()

    canonical_url = absolute_url(reverse("public:repo_detail", kwargs={"slug": slug, "repo_slug": repo_slug}))

    context = {
        "repo_profile": repo_profile,
        "org_profile": org_profile,
        "stats": stats,
        "insight": insight,
        "public_slug": slug,
        "repo_slug": repo_slug,
        "is_repo_page": True,
        "page_title": f"{repo_profile.display_name} Engineering Metrics",
        "page_description": _build_meta_description(repo_profile, stats),
        "page_canonical_url": canonical_url,
        "page_image": absolute_url(f"/og/open-source/{slug}/{repo_slug}.png"),
        "combined_trend_data": stats.combined_trend_data if stats else {},
        "correlation_data": stats.correlation_data if stats else {},
        "ai_impact_data": stats.ai_impact_data if stats else {},
        "comparison_data": stats.comparison_data if stats else {},
    }
    return TemplateResponse(request, "public/repo_detail.html", context)


@require_http_methods(["GET"])
@public_repo_required
def repo_pr_list(request: HttpRequest, slug: str, repo_slug: str) -> HttpResponse:
    """Repo-level PR explorer — scoped to a single repository."""
    repo_profile = request.repo_profile
    org_profile = request.public_profile

    context = build_pr_list_context(request, github_repo=repo_profile.github_repo)
    context.update(
        {
            "public_slug": slug,
            "repo_slug": repo_slug,
            "repo_profile": repo_profile,
            "org_profile": org_profile,
            "is_repo_page": True,
            "page_title": f"{repo_profile.display_name} Pull Requests",
            "page_description": f"Pull request explorer for {repo_profile.display_name}.",
            "page_robots": "noindex,follow",
            "page_canonical_url": absolute_url(
                reverse("public:repo_detail", kwargs={"slug": slug, "repo_slug": repo_slug})
            ),
        }
    )
    return TemplateResponse(request, "public/repo_pr_list.html", context)


@require_http_methods(["GET"])
@public_repo_required
def repo_pr_list_table(request: HttpRequest, slug: str, repo_slug: str) -> HttpResponse:
    """HTMX partial for repo PR table refresh (filtering/pagination)."""
    repo_profile = request.repo_profile

    context = build_pr_list_context(request, github_repo=repo_profile.github_repo)
    context.update(
        {
            "public_slug": slug,
            "repo_slug": repo_slug,
            "is_repo_page": True,
        }
    )
    return TemplateResponse(request, "public/partials/repo_pr_table.html", context)


def _build_meta_description(repo_profile, stats) -> str:
    if not stats:
        return f"Engineering metrics for {repo_profile.display_name}."
    return (
        f"{float(stats.ai_assisted_pct):.0f}% of {repo_profile.display_name} PRs are AI-assisted. "
        f"Median cycle time: {float(stats.median_cycle_time_hours):.0f}h. "
        f"Based on {stats.total_prs} merged pull requests."
    )
