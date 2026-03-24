from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.public.decorators import public_repo_required
from apps.public.models import PublicRepoInsight, PublicRepoStats
from apps.web.meta import absolute_url

from .helpers import build_pr_list_context, get_repo_og_image_url


@require_GET
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
        "insight_text": _normalize_public_insight_text(insight.content) if insight else "",
        "public_slug": slug,
        "repo_slug": repo_slug,
        "is_repo_page": True,
        "page_title": f"{repo_profile.display_name} Engineering Benchmarks",
        "page_description": _build_meta_description(repo_profile, stats),
        "page_canonical_url": canonical_url,
        "page_image": get_repo_og_image_url(slug, repo_slug),
        "combined_trend_data": stats.combined_trend_data if stats else {},
        "correlation_data": stats.correlation_data if stats else {},
        "ai_impact_data": stats.ai_impact_data if stats else {},
        "comparison_data": stats.comparison_data if stats else {},
    }
    return TemplateResponse(request, "public/repo_detail.html", context)


@require_GET
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
            "page_image": get_repo_og_image_url(slug, repo_slug),
        }
    )
    return TemplateResponse(request, "public/repo_pr_list.html", context)


@require_GET
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

    org_name = repo_profile.org_profile.display_name
    contributors = getattr(stats, "active_contributors_30d", None)
    contributors_text = f", {contributors} active contributors" if contributors else ""

    trend_text = ""
    cadence_change = getattr(stats, "cadence_change_pct", None)
    if cadence_change is not None and float(cadence_change) >= 10:
        trend_text = f" PR volume is up {float(cadence_change):.0f}% versus the prior period."
    elif cadence_change is not None and float(cadence_change) <= -10:
        trend_text = f" PR volume is down {abs(float(cadence_change)):.0f}% versus the prior period."

    return (
        f"{org_name}/{repo_profile.display_name} delivery benchmarks from {stats.total_prs:,} merged pull requests: "
        f"{_format_hours(stats.median_cycle_time_hours)} median cycle time, "
        f"{_format_hours(stats.median_review_time_hours)} median review time"
        f"{contributors_text}. "
        f"AI-related signals appear on {float(stats.ai_assisted_pct):.1f}% of recent work."
        f"{trend_text}"
    )


def _format_hours(value) -> str:
    from apps.public.formatting import format_duration

    return format_duration(value)


def _normalize_public_insight_text(text: str) -> str:
    return (
        text.replace("AI-assisted", "showing AI-related signals")
        .replace("with AI", "with AI-related signals")
        .replace("without AI", "baseline")
    )
