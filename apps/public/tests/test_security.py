from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats


class PublicSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.public_team = TeamFactory()
        cls.public_profile = PublicOrgProfile.objects.create(
            team=cls.public_team,
            public_slug="secure-org",
            industry="analytics",
            display_name="Secure Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.public_profile,
            total_prs=MIN_PRS_THRESHOLD + 100,
            ai_assisted_pct=Decimal("40.0"),
        )

        cls.private_team = TeamFactory()
        cls.private_profile = PublicOrgProfile.objects.create(
            team=cls.private_team,
            public_slug="hidden-secure-org",
            industry="analytics",
            display_name="Hidden Secure Org",
            is_public=False,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.private_profile,
            total_prs=MIN_PRS_THRESHOLD + 100,
            ai_assisted_pct=Decimal("99.0"),
        )

    def test_post_request_returns_405(self):
        response = self.client.post(reverse("public:org_detail", kwargs={"slug": "secure-org"}))
        assert response.status_code == 405
        analytics_response = self.client.post(reverse("public:org_analytics", kwargs={"slug": "secure-org"}))
        assert analytics_response.status_code == 405

    def test_no_session_team_set(self):
        self.client.get(reverse("public:org_detail", kwargs={"slug": "secure-org"}))
        assert "team" not in self.client.session

    def test_authenticated_user_sees_public_view(self):
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "secure-org"}))
        assert response.status_code == 200
        assert b"Secure Org" in response.content
        assert b"Hidden Secure Org" not in response.content

    def test_private_org_slug_returns_404(self):
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "hidden-secure-org"}))
        assert response.status_code == 404

    def test_public_analytics_has_no_write_controls(self):
        response = self.client.get(reverse("public:org_analytics", kwargs={"slug": "secure-org"}))
        assert response.status_code == 200
        content = response.content.decode().lower()
        assert "hx-post" not in content
        assert "feedback" not in content
        assert "dismiss" not in content
        assert "export csv" not in content
