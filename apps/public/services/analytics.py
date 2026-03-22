"""Public analytics service layer.

Wraps aggregation functions with caching and provides view-ready data.
All methods are designed for unauthenticated public access — no team
context required.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from apps.metrics.models import DailyInsight, PullRequest
from apps.public.aggregations import (
    BOT_USERNAMES,
    MIN_PRS_THRESHOLD,
    _data_window,
    compute_ai_tools_breakdown,
    compute_industry_stats,
    compute_member_breakdown,
    compute_monthly_cycle_time,
    compute_monthly_sparklines,
    compute_monthly_trends,
    compute_pr_size_distribution,
    compute_pr_type_trends,
    compute_quality_indicators,
    compute_recent_prs,
    compute_repos_analyzed,
    compute_review_distribution,
    compute_team_summary,
    compute_tech_category_trends,
)
from apps.public.models import PublicOrgProfile, PublicOrgStats

logger = logging.getLogger(__name__)

# Cache TTL: 6 hours (stats refresh daily, so 6h reduces unnecessary cache misses)
PUBLIC_CACHE_TTL = 21600
CACHE_PREFIX = "public:"


class PublicAnalyticsService:
    """Service for public-facing OSS analytics pages.

    Design notes:
    - No team constructor — public analytics span all orgs
    - Directory queries use pre-computed PublicOrgStats (instant)
    - Detail pages compute on-the-fly with Redis caching (1h TTL)
    """

    @staticmethod
    def get_directory_data(year=None):
        """Get data for the /open-source/ directory page.

        Args:
            year: Filter stats to a specific year. None = pre-computed best-year stats.

        Returns:
            List of dicts with org info + summary stats, sorted by total_prs desc.
        """
        cache_key = f"{CACHE_PREFIX}directory" if year is None else f"{CACHE_PREFIX}directory:{year}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        profiles = PublicOrgProfile.objects.filter(is_public=True).select_related("stats", "team")

        if year is None:
            # Fast path: use pre-computed stats
            profiles = profiles.filter(stats__total_prs__gte=MIN_PRS_THRESHOLD).order_by("-stats__total_prs")
            result = []
            for profile in profiles:
                stats = profile.stats
                result.append(
                    {
                        "slug": profile.public_slug,
                        "display_name": profile.display_name,
                        "industry": profile.industry,
                        "industry_display": profile.get_industry_display(),
                        "description": profile.description,
                        "github_org_url": profile.github_org_url,
                        "logo_url": profile.logo_url,
                        "total_prs": stats.total_prs,
                        "ai_assisted_pct": stats.ai_assisted_pct,
                        "median_cycle_time_hours": stats.median_cycle_time_hours,
                        "median_review_time_hours": stats.median_review_time_hours,
                        "active_contributors_90d": stats.active_contributors_90d,
                    }
                )
        else:
            # Year-specific: compute on-the-fly per team
            result = []
            for profile in profiles:
                summary = compute_team_summary(profile.team_id, year=year)
                if summary["total_prs"] < MIN_PRS_THRESHOLD:
                    continue
                result.append(
                    {
                        "slug": profile.public_slug,
                        "display_name": profile.display_name,
                        "industry": profile.industry,
                        "industry_display": profile.get_industry_display(),
                        "description": profile.description,
                        "github_org_url": profile.github_org_url,
                        "logo_url": profile.logo_url,
                        "total_prs": summary["total_prs"],
                        "ai_assisted_pct": summary["ai_pct"],
                        "median_cycle_time_hours": summary["median_cycle_time_hours"],
                        "median_review_time_hours": summary["median_review_time_hours"],
                        "active_contributors_90d": summary["active_contributors_90d"],
                    }
                )
            result.sort(key=lambda o: o["total_prs"], reverse=True)

        cache.set(cache_key, result, PUBLIC_CACHE_TTL)
        return result

    @staticmethod
    def get_org_detail(public_slug):
        """Get full metrics for a single org's detail page.

        Combines pre-computed stats (instant) with on-the-fly aggregations
        (monthly trends, AI tools breakdown, sparklines, member breakdown,
        quality indicators, review distribution, and insights) cached for 1 hour.

        Args:
            public_slug: The org's public URL slug (e.g., "posthog").

        Returns:
            Dict with profile info, summary stats, monthly trends,
            AI tools breakdown, and enhanced metrics. Returns None if
            org not found or not public.
        """
        cache_key = f"{CACHE_PREFIX}org:{public_slug}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            profile = PublicOrgProfile.objects.select_related("stats", "team").get(
                public_slug=public_slug,
                is_public=True,
            )
        except PublicOrgProfile.DoesNotExist:
            return None

        team_id = profile.team_id
        start_date, end_date = _data_window(team_id)

        # Pre-computed summary (instant)
        try:
            stats = profile.stats
            summary = {
                "total_prs": stats.total_prs,
                "ai_assisted_pct": stats.ai_assisted_pct,
                "median_cycle_time_hours": stats.median_cycle_time_hours,
                "median_review_time_hours": stats.median_review_time_hours,
                "active_contributors_90d": stats.active_contributors_90d,
                "top_ai_tools": stats.top_ai_tools,
                "last_computed_at": stats.last_computed_at,
            }
        except PublicOrgStats.DoesNotExist:
            # Stats not yet computed — compute fresh using rolling window
            raw = compute_team_summary(team_id, start_date=start_date, end_date=end_date)
            # All-time PR count for data significance (not year-filtered)
            total_prs_all_time = (
                PullRequest.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
                    team_id=team_id, state="merged"
                )
                .exclude(author__github_username__endswith="[bot]")
                .exclude(author__github_username__in=BOT_USERNAMES)
                .count()
            )
            # Normalize keys to match the PublicOrgStats field names
            summary = {
                "total_prs": total_prs_all_time,
                "ai_assisted_pct": raw["ai_pct"],
                "median_cycle_time_hours": raw["median_cycle_time_hours"],
                "median_review_time_hours": raw["median_review_time_hours"],
                "active_contributors_90d": raw["active_contributors_90d"],
                "top_ai_tools": [],
                "last_computed_at": None,
            }

        # On-the-fly aggregations — rolling 12-month window for cross-year data
        monthly_trends = compute_monthly_trends(team_id, start_date=start_date, end_date=end_date)
        ai_tools = compute_ai_tools_breakdown(team_id, start_date=start_date, end_date=end_date)
        sparklines = compute_monthly_sparklines(team_id, start_date=start_date, end_date=end_date)
        cycle_time_trend = compute_monthly_cycle_time(team_id, start_date=start_date, end_date=end_date)
        recent_prs = compute_recent_prs(team_id, limit=10)
        member_breakdown = compute_member_breakdown(team_id, start_date=start_date, end_date=end_date)
        quality_indicators = compute_quality_indicators(team_id, start_date=start_date, end_date=end_date)
        review_distribution = compute_review_distribution(team_id, start_date=start_date, end_date=end_date)
        repos_analyzed = compute_repos_analyzed(team_id, start_date=start_date, end_date=end_date)
        pr_size_distribution = compute_pr_size_distribution(team_id, start_date=start_date, end_date=end_date)
        tech_category_trends = compute_tech_category_trends(team_id, start_date=start_date, end_date=end_date)
        pr_type_trends = compute_pr_type_trends(team_id, start_date=start_date, end_date=end_date)

        # Latest insight (last 30 days, single most important, updated weekly)
        thirty_days_ago = (timezone.now() - timedelta(days=30)).date()
        priority_order = Case(
            When(priority="high", then=Value(0)),
            When(priority="medium", then=Value(1)),
            When(priority="low", then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
        latest_insight = (
            DailyInsight.objects.filter(  # noqa: TEAM001 - cross-team for public analytics
                team_id=team_id,
                date__gte=thirty_days_ago,
                is_dismissed=False,
            )
            .annotate(priority_rank=priority_order)
            .order_by("priority_rank", "-date")
            .values("title", "description", "category", "priority", "date", "metric_type")
            .first()
        )

        result = {
            "profile": {
                "slug": profile.public_slug,
                "display_name": profile.display_name,
                "industry": profile.industry,
                "industry_display": profile.get_industry_display(),
                "description": profile.description,
                "github_org_url": profile.github_org_url,
                "logo_url": profile.logo_url,
            },
            "summary": summary,
            "monthly_trends": monthly_trends,
            "ai_tools": ai_tools,
            "sparklines": sparklines,
            "cycle_time_trend": cycle_time_trend,
            "recent_prs": recent_prs,
            "member_breakdown": member_breakdown,
            "quality_indicators": quality_indicators,
            "review_distribution": review_distribution,
            "repos_analyzed": repos_analyzed,
            "pr_size_distribution": pr_size_distribution,
            "tech_category_trends": tech_category_trends,
            "pr_type_trends": pr_type_trends,
            "latest_insight": latest_insight,
        }

        cache.set(cache_key, result, PUBLIC_CACHE_TTL)
        return result

    @staticmethod
    def get_industry_comparison(industry_key):
        """Get comparison data for all public orgs in an industry.

        Args:
            industry_key: Industry identifier (e.g., "analytics").

        Returns:
            Dict with industry-level stats and per-org breakdown.
            Returns None if no qualifying orgs in the industry.
        """
        cache_key = f"{CACHE_PREFIX}industry:{industry_key}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Aggregate industry stats
        industry_stats = compute_industry_stats(industry_key)
        if industry_stats["org_count"] == 0:
            return None

        # Per-org breakdown within industry
        profiles = (
            PublicOrgProfile.objects.filter(
                is_public=True,
                industry=industry_key,
                stats__total_prs__gte=MIN_PRS_THRESHOLD,
            )
            .select_related("stats")
            .order_by("-stats__total_prs")
        )

        orgs = []
        for profile in profiles:
            stats = profile.stats
            orgs.append(
                {
                    "slug": profile.public_slug,
                    "display_name": profile.display_name,
                    "total_prs": stats.total_prs,
                    "ai_assisted_pct": stats.ai_assisted_pct,
                    "median_cycle_time_hours": stats.median_cycle_time_hours,
                    "active_contributors_90d": stats.active_contributors_90d,
                }
            )

        # Get industry display name from choices
        industry_display = industry_key
        for key, label in PublicOrgProfile._meta.get_field("industry").choices:
            if key == industry_key:
                industry_display = label
                break

        result = {
            "industry_key": industry_key,
            "industry_display": industry_display,
            "stats": industry_stats,
            "orgs": orgs,
        }

        cache.set(cache_key, result, PUBLIC_CACHE_TTL)
        return result

    @staticmethod
    def get_global_stats():
        """Get aggregate stats across all public orgs.

        Used for the directory page header and meta descriptions.

        Returns:
            Dict with org_count, total_prs, avg_ai_pct, avg_cycle_time,
            industry_count.
        """
        cache_key = f"{CACHE_PREFIX}global"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        qualifying_stats = PublicOrgStats.objects.filter(
            org_profile__is_public=True,
            total_prs__gte=MIN_PRS_THRESHOLD,
        ).select_related("org_profile")

        stats_list = list(qualifying_stats)

        if not stats_list:
            result = {
                "org_count": 0,
                "total_prs": 0,
                "avg_ai_pct": Decimal("0"),
                "avg_cycle_time": Decimal("0"),
                "industry_count": 0,
            }
            cache.set(cache_key, result, PUBLIC_CACHE_TTL)
            return result

        total_prs = sum(s.total_prs for s in stats_list)
        avg_ai_pct = Decimal(str(round(sum(float(s.ai_assisted_pct) for s in stats_list) / len(stats_list), 2)))
        avg_cycle = Decimal(str(round(sum(float(s.median_cycle_time_hours) for s in stats_list) / len(stats_list), 2)))
        industries = {s.org_profile.industry for s in stats_list}

        result = {
            "org_count": len(stats_list),
            "total_prs": total_prs,
            "avg_ai_pct": avg_ai_pct,
            "avg_cycle_time": avg_cycle,
            "industry_count": len(industries),
        }

        cache.set(cache_key, result, PUBLIC_CACHE_TTL)
        return result
