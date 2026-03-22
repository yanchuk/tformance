"""Tests for public page metadata strategy (Task 6).

Covers: robots noindex, read-only removal, entity-specific descriptions,
keyword removal, canonical URLs on support pages.
"""

from django.test import TestCase

from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile, PublicRepoStats
from apps.teams.models import Team


class MetadataTestBase(TestCase):
    """Shared setup for metadata tests."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Meta Team", slug="meta-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="meta-org",
            industry="analytics",
            display_name="Meta Org",
            is_public=True,
        )
        cls.stats = PublicOrgStats.objects.create(
            org_profile=cls.org,
            total_prs=1000,
            ai_assisted_pct=42.5,
            median_cycle_time_hours=18.3,
            median_review_time_hours=4.2,
            active_contributors_90d=25,
        )
        cls.repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="meta-org/meta-repo",
            repo_slug="meta-repo",
            display_name="Meta Repo",
            is_flagship=True,
            is_public=True,
        )
        cls.repo_stats = PublicRepoStats.objects.create(
            repo_profile=cls.repo,
            total_prs=500,
            ai_assisted_pct=35.0,
            median_cycle_time_hours=12.5,
            median_review_time_hours=3.8,
        )


class PublicMetadataRobotsTests(MetadataTestBase):
    """Step 6.1: noindex,follow on support pages."""

    def test_analytics_page_has_noindex_follow(self):
        response = self.client.get("/open-source/meta-org/analytics/")
        assert response.context["page_robots"] == "noindex,follow"

    def test_org_pr_list_has_noindex_follow(self):
        response = self.client.get("/open-source/meta-org/pull-requests/")
        assert response.context["page_robots"] == "noindex,follow"

    def test_primary_pages_have_no_robots_restriction(self):
        # Org detail should not restrict robots
        response = self.client.get("/open-source/meta-org/")
        assert response.context.get("page_robots", "") == ""

    def test_base_template_emits_robots_meta_when_set(self):
        response = self.client.get("/open-source/meta-org/analytics/")
        content = response.content.decode()
        assert '<meta name="robots" content="noindex,follow">' in content


class PublicMetadataReadOnlyRemovalTests(MetadataTestBase):
    """Step 6.2: Remove 'read-only' from all metadata and copy."""

    def test_analytics_description_no_read_only(self):
        response = self.client.get("/open-source/meta-org/analytics/")
        assert "read-only" not in response.context["page_description"].lower()

    def test_analytics_visible_copy_no_read_only(self):
        response = self.client.get("/open-source/meta-org/analytics/")
        content = response.content.decode().lower()
        # Exclude script tags (JSON-LD may have descriptions)
        # Check visible body content
        assert "read-only" not in content


class PublicMetadataDescriptionTests(MetadataTestBase):
    """Step 6.3: Entity-specific meta descriptions."""

    def test_org_detail_description_formula(self):
        response = self.client.get("/open-source/meta-org/")
        desc = response.context["page_description"]
        assert "Meta Org" in desc
        assert "1,000" in desc or "1000" in desc  # total_prs
        assert "42.5" in desc  # AI % (may be 42.5 or 42.50)
        assert "18.3" in desc  # cycle time (may be 18.3 or 18.30)

    def test_analytics_support_description(self):
        response = self.client.get("/open-source/meta-org/analytics/")
        desc = response.context["page_description"]
        assert "Meta Org" in desc
        assert "delivery" in desc.lower() or "trends" in desc.lower()


class PublicMetadataCanonicalTests(MetadataTestBase):
    """Step 6.5: Canonical URLs on support pages."""

    def test_analytics_canonical_points_to_org_detail(self):
        response = self.client.get("/open-source/meta-org/analytics/")
        canonical = response.context["page_canonical_url"]
        assert "/open-source/meta-org/" in canonical
        assert "/analytics/" not in canonical
