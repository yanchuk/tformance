from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import TeamFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoInsight,
    PublicRepoProfile,
    PublicRepoStats,
)


class RepoDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="vieworg",
            industry="analytics",
            display_name="View Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="vieworg/main-repo",
            repo_slug="main-repo",
            display_name="Main Repo",
            is_flagship=True,
            is_public=True,
        )
        cls.repo_stats = PublicRepoStats.objects.create(
            repo_profile=cls.repo_profile,
            total_prs=500,
            total_prs_in_window=80,
            ai_assisted_pct=Decimal("45.50"),
            median_cycle_time_hours=Decimal("14.2"),
            median_review_time_hours=Decimal("5.8"),
            active_contributors_30d=15,
            cadence_change_pct=Decimal("12.5"),
            best_signal={"metric": "ai_adoption", "label": "AI Adoption", "value": "46%", "description": "46% AI"},
            watchout_signal={"metric": "none", "label": "No Concerns", "value": "-", "description": "Stable"},
            trend_data={"adoption": [], "cycle_time": []},
            breakdown_data={"ai_tools": [], "pr_sizes": []},
            recent_prs=[{"title": "Fix auth bug", "author_name": "dev1", "github_pr_id": 123}],
            last_computed_at=timezone.now(),
        )
        cls.insight = PublicRepoInsight.objects.create(
            repo_profile=cls.repo_profile,
            content="Main Repo shows strong AI adoption at 45.5%.",
            insight_type="weekly",
            is_current=True,
            batch_id="test-batch",
        )

    def _url(self):
        return reverse("public:repo_detail", kwargs={"slug": "vieworg", "repo_slug": "main-repo"})

    def test_repo_detail_200(self):
        response = self.client.get(self._url())
        assert response.status_code == 200

    def test_repo_detail_renders_citable_summary(self):
        response = self.client.get(self._url())
        content = response.content.decode()
        assert "based on" in content.lower()
        assert "45.5" in content

    def test_repo_detail_renders_primary_cta(self):
        response = self.client.get(self._url())
        content = response.content.decode()
        assert "Start Free Trial" in content or "Connect Repos" in content

    def test_repo_detail_renders_insight(self):
        response = self.client.get(self._url())
        content = response.content.decode()
        assert "strong AI adoption" in content

    def test_repo_detail_is_meaningful_without_js(self):
        """Page must have inline data tables, not just HTMX skeletons."""
        response = self.client.get(self._url())
        content = response.content.decode()
        # Must have a table or methodology section — not depend on JS
        assert "<table" in content or "Methodology" in content

    def test_repo_detail_has_methodology_section(self):
        response = self.client.get(self._url())
        content = response.content.decode()
        assert "Methodology" in content or "Source" in content

    def test_repo_detail_links_to_pr_explorer(self):
        response = self.client.get(self._url())
        content = response.content.decode()
        pr_list_url = reverse("public:repo_pr_list", kwargs={"slug": "vieworg", "repo_slug": "main-repo"})
        assert pr_list_url in content

    def test_repo_detail_404_for_nonexistent_repo(self):
        url = reverse("public:repo_detail", kwargs={"slug": "vieworg", "repo_slug": "nonexistent"})
        response = self.client.get(url)
        assert response.status_code == 404

    def test_repo_detail_404_for_nonpublic_repo(self):
        PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="vieworg/private-repo",
            repo_slug="private-repo",
            display_name="Private Repo",
            is_public=False,
        )
        url = reverse("public:repo_detail", kwargs={"slug": "vieworg", "repo_slug": "private-repo"})
        response = self.client.get(url)
        assert response.status_code == 404

    def test_repo_detail_no_tabs(self):
        """Repo pages should NOT show org-level tabs."""
        response = self.client.get(self._url())
        content = response.content.decode()
        assert 'role="tablist"' not in content
