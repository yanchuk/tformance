import re
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.metrics.factories import TeamFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats


class PublicNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        team = TeamFactory()
        profile = PublicOrgProfile.objects.create(
            team=team,
            public_slug="nav-org",
            industry="analytics",
            display_name="Nav Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
            ai_assisted_pct=Decimal("22.2"),
        )

    def _assert_tabs_present(self, content: str):
        assert reverse("public:org_detail", kwargs={"slug": "nav-org"}) in content
        assert reverse("public:org_analytics", kwargs={"slug": "nav-org"}) in content
        assert reverse("public:org_pr_list", kwargs={"slug": "nav-org"}) in content

    def _assert_active_tab(self, content: str, expected_url: str):
        pattern = rf'href="{re.escape(expected_url)}"\s+class="tab tab-active"'
        assert re.search(pattern, content), f"Expected active tab for {expected_url}"

    def test_overview_page_renders_tabs_with_overview_active(self):
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "nav-org"}))
        assert response.status_code == 200
        content = response.content.decode()
        self._assert_tabs_present(content)
        self._assert_active_tab(content, reverse("public:org_detail", kwargs={"slug": "nav-org"}))

    def test_analytics_page_renders_tabs_with_analytics_active(self):
        response = self.client.get(reverse("public:org_analytics", kwargs={"slug": "nav-org"}))
        assert response.status_code == 200
        content = response.content.decode()
        self._assert_tabs_present(content)
        self._assert_active_tab(content, reverse("public:org_analytics", kwargs={"slug": "nav-org"}))

    def test_pr_list_page_renders_tabs_with_prs_active(self):
        response = self.client.get(reverse("public:org_pr_list", kwargs={"slug": "nav-org"}))
        assert response.status_code == 200
        content = response.content.decode()
        self._assert_tabs_present(content)
        self._assert_active_tab(content, reverse("public:org_pr_list", kwargs={"slug": "nav-org"}))
