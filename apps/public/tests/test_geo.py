from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import TeamFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats


class PublicGeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        team = TeamFactory()
        profile = PublicOrgProfile.objects.create(
            team=team,
            public_slug="geo-org",
            industry="analytics",
            display_name="Geo Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=profile,
            total_prs=MIN_PRS_THRESHOLD + 5,
            ai_assisted_pct=Decimal("28.4"),
            median_cycle_time_hours=Decimal("14.2"),
            median_review_time_hours=Decimal("3.7"),
            active_contributors_90d=11,
            last_computed_at=timezone.now(),
        )

    def test_json_ld_dataset_schema(self):
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "geo-org"}))
        content = response.content.decode()
        assert '"@type": "Dataset"' in content
        assert "variableMeasured" in content

    def test_json_ld_faq_schema(self):
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "geo-org"}))
        content = response.content.decode()
        assert '"@type": "FAQPage"' in content

    def test_citable_paragraph_contains_real_stats(self):
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "geo-org"}))
        content = response.content.decode()
        assert "None%" not in content
        assert "{{" not in content
        assert "28.4%" in content

    def test_org_hub_has_citable_stats(self):
        """Hub page shows benchmark stats in the citable paragraph."""
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "geo-org"}))
        content = response.content.decode()
        assert "28.4%" in content
        assert "14.2" in content

    def test_analytics_page_has_json_ld(self):
        response = self.client.get(reverse("public:org_analytics", kwargs={"slug": "geo-org"}))
        content = response.content.decode()
        assert response.status_code == 200
        assert '"@type": "Dataset"' in content
        assert '"@type": "FAQPage"' in content

    def test_analytics_page_has_canonical_and_citable_content(self):
        response = self.client.get(reverse("public:org_analytics", kwargs={"slug": "geo-org"}))
        content = response.content.decode()
        assert "open-source/geo-org/analytics/" in content
        assert "28.4%" in content
        assert "{{" not in content

    def test_sitemap_includes_public_urls(self):
        response = self.client.get("/sitemap.xml")
        content = response.content.decode()
        assert response.status_code == 200
        assert "/open-source/" in content
        assert "/open-source/geo-org/" in content

    def test_robots_includes_open_source_and_ai_bots(self):
        response = self.client.get(reverse("web:robots.txt"))
        content = response.content.decode()
        assert "Allow: /open-source/" in content
        assert "User-agent: GPTBot" in content
