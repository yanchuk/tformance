from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats


class PublicAnalyticsViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)

        cls.profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="analytics-org",
            industry="analytics",
            display_name="Analytics Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.profile,
            total_prs=MIN_PRS_THRESHOLD + 20,
            ai_assisted_pct=Decimal("34.5"),
            median_cycle_time_hours=Decimal("16.4"),
            median_review_time_hours=Decimal("3.2"),
            active_contributors_90d=14,
            last_computed_at=timezone.now(),
        )

        cls.private_team = TeamFactory()
        cls.private_profile = PublicOrgProfile.objects.create(
            team=cls.private_team,
            public_slug="private-analytics-org",
            industry="analytics",
            display_name="Private Analytics Org",
            is_public=False,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.private_profile,
            total_prs=MIN_PRS_THRESHOLD + 20,
            ai_assisted_pct=Decimal("10.0"),
        )

        for index in range(10):
            PullRequestFactory(
                team=cls.team,
                author=cls.member,
                state="merged",
                title=f"Analytics PR {index}",
                is_ai_assisted=index % 2 == 0,
                cycle_time_hours=Decimal("10.0") + index,
                review_time_hours=Decimal("2.0") + Decimal(index) / 10,
                additions=30 + index,
                deletions=5,
                pr_created_at=timezone.now() - timedelta(days=20 - index),
                merged_at=timezone.now() - timedelta(days=19 - index),
            )

    def test_org_analytics_200_valid_slug(self):
        response = self.client.get(reverse("public:org_analytics", kwargs={"slug": "analytics-org"}))
        assert response.status_code == 200
        assert b"Analytics Org Analytics" in response.content

    def test_org_analytics_404_private_org(self):
        response = self.client.get(reverse("public:org_analytics", kwargs={"slug": "private-analytics-org"}))
        assert response.status_code == 404

    def test_org_analytics_contains_expected_reused_endpoints(self):
        response = self.client.get(reverse("public:org_analytics", kwargs={"slug": "analytics-org"}))
        assert response.status_code == 200
        self.assertContains(response, reverse("public:cards_metrics", kwargs={"slug": "analytics-org"}))
        self.assertContains(response, reverse("public:chart_ai_adoption", kwargs={"slug": "analytics-org"}))
        self.assertContains(response, reverse("public:chart_cycle_time", kwargs={"slug": "analytics-org"}))
        self.assertContains(response, reverse("public:chart_ai_quality", kwargs={"slug": "analytics-org"}))
        self.assertContains(response, reverse("public:chart_ai_tools", kwargs={"slug": "analytics-org"}))
        self.assertContains(response, reverse("public:cards_team_health", kwargs={"slug": "analytics-org"}))
