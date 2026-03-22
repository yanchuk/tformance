from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import TeamFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoProfile,
    PublicRepoStats,
)


class RepoGeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="seo-org",
            industry="analytics",
            display_name="SEO Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="seo-org/main-repo",
            repo_slug="main-repo",
            display_name="Main Repo",
            is_flagship=True,
            is_public=True,
        )
        cls.repo_stats = PublicRepoStats.objects.create(
            repo_profile=cls.repo_profile,
            total_prs=300,
            total_prs_in_window=50,
            ai_assisted_pct=Decimal("38.5"),
            median_cycle_time_hours=Decimal("12.0"),
            median_review_time_hours=Decimal("4.5"),
            active_contributors_30d=10,
            cadence_change_pct=Decimal("5.0"),
            best_signal={"metric": "ai_adoption", "label": "AI", "value": "39%", "description": "High"},
            watchout_signal={"metric": "none", "label": "None", "value": "-", "description": "-"},
            trend_data={},
            breakdown_data={},
            recent_prs=[],
            last_computed_at=timezone.now(),
        )

    def _repo_url(self):
        return reverse("public:repo_detail", kwargs={"slug": "seo-org", "repo_slug": "main-repo"})

    def _pr_list_url(self):
        return reverse("public:repo_pr_list", kwargs={"slug": "seo-org", "repo_slug": "main-repo"})

    # --- JSON-LD on repo detail ---

    def test_repo_detail_has_dataset_json_ld(self):
        response = self.client.get(self._repo_url())
        content = response.content.decode()
        assert '"@type": "Dataset"' in content
        assert "variableMeasured" in content

    def test_repo_detail_has_faq_json_ld(self):
        response = self.client.get(self._repo_url())
        content = response.content.decode()
        assert '"@type": "FAQPage"' in content

    def test_repo_detail_has_breadcrumb_json_ld(self):
        response = self.client.get(self._repo_url())
        content = response.content.decode()
        assert '"@type": "BreadcrumbList"' in content

    # --- OG / Canonical on repo detail (from base template) ---

    def test_repo_detail_has_canonical_url(self):
        response = self.client.get(self._repo_url())
        content = response.content.decode()
        assert "/open-source/seo-org/repos/main-repo/" in content
        assert 'rel="canonical"' in content

    def test_repo_detail_has_og_tags(self):
        response = self.client.get(self._repo_url())
        content = response.content.decode()
        assert 'property="og:title"' in content
        assert 'property="og:description"' in content

    # --- PR list SEO signals ---

    def test_repo_pr_list_has_noindex(self):
        response = self.client.get(self._pr_list_url())
        content = response.content.decode()
        assert "noindex" in content

    def test_repo_pr_list_canonical_points_to_repo_detail(self):
        response = self.client.get(self._pr_list_url())
        content = response.content.decode()
        assert "/open-source/seo-org/repos/main-repo/" in content
        assert 'rel="canonical"' in content

    # --- Sitemap ---

    def test_sitemap_includes_repo_pages(self):
        response = self.client.get("/sitemap.xml")
        content = response.content.decode()
        assert response.status_code == 200
        assert "/open-source/seo-org/repos/main-repo/" in content

    def test_sitemap_excludes_non_public_repos(self):
        PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="seo-org/private-repo",
            repo_slug="private-repo",
            display_name="Private Repo",
            is_flagship=True,
            is_public=False,
        )
        response = self.client.get("/sitemap.xml")
        content = response.content.decode()
        assert "/open-source/seo-org/repos/private-repo/" not in content
