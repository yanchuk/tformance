"""Tests for dynamic OG image generation (Task 7).

Covers: Pillow rendering, pre-generation in pipeline, view serving, meta tag wiring.
"""

import tempfile

from django.test import TestCase, override_settings

from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile, PublicRepoStats
from apps.teams.models import Team


class OGImageServiceTests(TestCase):
    """Step 7.1: OG image service Pillow rendering."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="OG Team", slug="og-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="og-org",
            industry="analytics",
            display_name="OG Org",
            is_public=True,
        )
        cls.org_stats = PublicOrgStats.objects.create(
            org_profile=cls.org,
            total_prs=5000,
            ai_assisted_pct=45.2,
            median_cycle_time_hours=16.5,
        )
        cls.repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="og-org/og-repo",
            repo_slug="og-repo",
            display_name="OG Repo",
            is_flagship=True,
            is_public=True,
        )
        cls.repo_stats = PublicRepoStats.objects.create(
            repo_profile=cls.repo,
            total_prs=1200,
            ai_assisted_pct=38.5,
            median_cycle_time_hours=12.0,
            median_review_time_hours=3.5,
        )

    def test_generate_org_og_image_returns_png_bytes(self):
        from apps.public.services.og_image_service import OGImageService

        data = OGImageService.generate_org_image(self.org, self.org_stats)
        assert isinstance(data, bytes)
        assert data[:4] == b"\x89PNG"

    def test_generate_repo_og_image_returns_png_bytes(self):
        from apps.public.services.og_image_service import OGImageService

        data = OGImageService.generate_repo_image(self.repo, self.repo_stats, self.org)
        assert isinstance(data, bytes)
        assert data[:4] == b"\x89PNG"


class OGImageViewTests(TestCase):
    """Step 7.3: OG image view endpoints serve pre-generated files."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="OGV Team", slug="ogv-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="ogv-org",
            industry="analytics",
            display_name="OGV Org",
            is_public=True,
        )
        cls.org_stats = PublicOrgStats.objects.create(
            org_profile=cls.org,
            total_prs=2000,
            ai_assisted_pct=40,
            median_cycle_time_hours=15,
        )
        cls.repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="ogv-org/ogv-repo",
            repo_slug="ogv-repo",
            display_name="OGV Repo",
            is_flagship=True,
            is_public=True,
        )
        cls.repo_stats = PublicRepoStats.objects.create(
            repo_profile=cls.repo,
            total_prs=500,
            ai_assisted_pct=35,
            median_cycle_time_hours=10,
        )

    def test_og_image_404_when_not_yet_generated(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            response = self.client.get("/og/open-source/ogv-org.png")
            assert response.status_code == 404

    def test_og_org_image_endpoint_returns_png(self):
        import os

        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            # Pre-generate the image
            from apps.public.services.og_image_service import OGImageService

            og_dir = os.path.join(tmp, "public_og")
            os.makedirs(og_dir, exist_ok=True)
            data = OGImageService.generate_org_image(self.org, self.org_stats)
            with open(os.path.join(og_dir, "ogv-org.png"), "wb") as f:
                f.write(data)

            response = self.client.get("/og/open-source/ogv-org.png")
            assert response.status_code == 200
            assert response["Content-Type"] == "image/png"

    def test_og_image_404_for_nonexistent_org(self):
        response = self.client.get("/og/open-source/nonexistent.png")
        assert response.status_code == 404


class OGRepoImageEndpointTests(TestCase):
    """Step 7.1: Repo OG image endpoint exists and returns PNG."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="OGR Team", slug="ogr-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="ogr-org",
            industry="analytics",
            display_name="OGR Org",
            is_public=True,
        )
        cls.org_stats = PublicOrgStats.objects.create(
            org_profile=cls.org,
            total_prs=2000,
            ai_assisted_pct=40,
            median_cycle_time_hours=15,
        )
        cls.repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="ogr-org/ogr-repo",
            repo_slug="ogr-repo",
            display_name="OGR Repo",
            is_flagship=True,
            is_public=True,
        )
        cls.repo_stats = PublicRepoStats.objects.create(
            repo_profile=cls.repo,
            total_prs=800,
            ai_assisted_pct=42,
            median_cycle_time_hours=11,
            median_review_time_hours=3.0,
        )

    def test_og_repo_image_endpoint_returns_png(self):
        import os

        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            from apps.public.services.og_image_service import OGImageService

            og_dir = os.path.join(tmp, "public_og")
            os.makedirs(og_dir, exist_ok=True)
            data = OGImageService.generate_repo_image(self.repo, self.repo_stats, self.org)
            with open(os.path.join(og_dir, "ogr-org_ogr-repo.png"), "wb") as f:
                f.write(data)

            response = self.client.get("/og/open-source/ogr-org/ogr-repo.png")
            assert response.status_code == 200
            assert response["Content-Type"] == "image/png"


class OGImageMetaIntegrationTests(TestCase):
    """Step 7.4: OG image URLs in meta tags."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="OGM Team", slug="ogm-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="ogm-org",
            industry="analytics",
            display_name="OGM Org",
            is_public=True,
        )
        cls.org_stats = PublicOrgStats.objects.create(
            org_profile=cls.org,
            total_prs=3000,
            ai_assisted_pct=45,
            median_cycle_time_hours=14,
        )
        cls.repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="ogm-org/ogm-repo",
            repo_slug="ogm-repo",
            display_name="OGM Repo",
            is_flagship=True,
            is_public=True,
        )
        cls.repo_stats = PublicRepoStats.objects.create(
            repo_profile=cls.repo,
            total_prs=600,
            ai_assisted_pct=38,
            median_cycle_time_hours=13,
            median_review_time_hours=4.0,
        )

    def test_org_detail_sets_page_image_to_og_url(self):
        response = self.client.get("/open-source/ogm-org/")
        page_image = response.context.get("page_image", "")
        assert "/og/open-source/ogm-org.png" in page_image

    def test_repo_detail_page_image_points_to_og_url(self):
        """Step 7.2: Repo page meta must reference repo OG image."""
        response = self.client.get("/open-source/ogm-org/repos/ogm-repo/")
        page_image = response.context.get("page_image", "")
        assert "/og/open-source/ogm-org/ogm-repo.png" in page_image
