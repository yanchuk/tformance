"""Django sitemaps for public analytics pages."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import INDUSTRY_CHOICES, PublicOrgProfile, PublicOrgStats, PublicRepoProfile, PublicRepoStats
from apps.web.meta import get_protocol


class PublicDirectorySitemap(Sitemap):
    """Sitemap entry for the /open-source/ directory page."""

    changefreq = "weekly"
    priority = 1.0

    @property
    def protocol(self):
        return get_protocol()

    def items(self):
        return ["public:directory"]

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        latest = PublicOrgStats.objects.order_by("-last_computed_at").first()
        if latest and latest.last_computed_at:
            return latest.last_computed_at
        return None


class PublicOrgSitemap(Sitemap):
    """Sitemap entries for individual org detail pages."""

    changefreq = "daily"
    priority = 0.8

    @property
    def protocol(self):
        return get_protocol()

    def items(self):
        return (
            PublicOrgProfile.objects.filter(
                is_public=True,
                stats__total_prs__gte=MIN_PRS_THRESHOLD,
            )
            .select_related("stats")
            .order_by("public_slug")
        )

    def location(self, item):
        return reverse("public:org_detail", kwargs={"slug": item.public_slug})

    def lastmod(self, item):
        try:
            return item.stats.last_computed_at
        except PublicOrgStats.DoesNotExist:
            return None


class PublicRepoSitemap(Sitemap):
    """Sitemap entries for individual repo detail pages — primary canonical surface."""

    changefreq = "daily"
    priority = 0.9

    @property
    def protocol(self):
        return get_protocol()

    def items(self):
        return (
            PublicRepoProfile.objects.filter(
                is_public=True,
                is_flagship=True,
            )
            .select_related("org_profile", "stats")
            .order_by("org_profile__public_slug", "repo_slug")
        )

    def location(self, item):
        return reverse(
            "public:repo_detail",
            kwargs={"slug": item.org_profile.public_slug, "repo_slug": item.repo_slug},
        )

    def lastmod(self, item):
        try:
            return item.stats.last_computed_at
        except PublicRepoStats.DoesNotExist:
            return None


class PublicIndustrySitemap(Sitemap):
    """Sitemap entries for industry comparison pages."""

    changefreq = "weekly"
    priority = 0.7

    @property
    def protocol(self):
        return get_protocol()

    def items(self):
        return [key for key, _label in INDUSTRY_CHOICES]

    def location(self, item):
        return reverse("public:industry", kwargs={"industry": item})
