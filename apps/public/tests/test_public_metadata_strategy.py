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


class PublicMetadataKeywordTests(MetadataTestBase):
    """Step 1.1: Canonical pages must not emit keywords meta tag."""

    def test_canonical_org_page_has_no_keywords_tag(self):
        response = self.client.get("/open-source/meta-org/")
        content = response.content.decode()
        assert '<meta name="keywords"' not in content

    def test_canonical_repo_page_has_no_keywords_tag(self):
        response = self.client.get("/open-source/meta-org/repos/meta-repo/")
        content = response.content.decode()
        assert '<meta name="keywords"' not in content

    def test_directory_page_has_no_keywords_tag(self):
        response = self.client.get("/open-source/")
        content = response.content.decode()
        assert '<meta name="keywords"' not in content


class PublicMetadataTitleTests(MetadataTestBase):
    """Step 1.3: Title contains Tformance exactly once."""

    def test_page_title_contains_tformance_exactly_once(self):
        response = self.client.get("/open-source/meta-org/repos/meta-repo/")
        content = response.content.decode()
        title_start = content.find("<title>")
        title_end = content.find("</title>")
        title = content[title_start + 7 : title_end].lower()
        assert title.count("tformance") == 1


class PublicMetadataCanonicalTests(MetadataTestBase):
    """Step 6.5: Canonical URLs on support pages."""

    def test_analytics_canonical_points_to_org_detail(self):
        response = self.client.get("/open-source/meta-org/analytics/")
        canonical = response.context["page_canonical_url"]
        assert "/open-source/meta-org/" in canonical
        assert "/analytics/" not in canonical

    def test_org_pr_list_canonical_points_to_org_detail(self):
        """Step 1.4: Org PR explorer must canonical to org page, not itself."""
        response = self.client.get("/open-source/meta-org/pull-requests/")
        canonical = response.context["page_canonical_url"]
        assert "/open-source/meta-org/" in canonical
        assert "/pull-requests/" not in canonical


class PublicMetadataCiCdAbsenceTests(MetadataTestBase):
    """Review 11A: Canonical pages must not contain CI/CD content."""

    CI_CD_TERMS = ["ci/cd", "check-run", "deployment frequency", "check run", "ci_cd"]

    def _assert_no_ci_cd(self, url):
        response = self.client.get(url)
        content = response.content.decode().lower()
        for term in self.CI_CD_TERMS:
            assert term not in content, f"Found '{term}' on {url}"

    def test_org_page_has_no_ci_cd_content(self):
        self._assert_no_ci_cd("/open-source/meta-org/")

    def test_repo_page_has_no_ci_cd_content(self):
        self._assert_no_ci_cd("/open-source/meta-org/repos/meta-repo/")

    def test_directory_has_no_ci_cd_content(self):
        self._assert_no_ci_cd("/open-source/")
