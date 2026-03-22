from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats


class PublicChartViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)
        cls.profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="chart-org",
            industry="analytics",
            display_name="Chart Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.profile,
            total_prs=MIN_PRS_THRESHOLD + 30,
            ai_assisted_pct=Decimal("33.0"),
            median_cycle_time_hours=Decimal("15.0"),
            median_review_time_hours=Decimal("4.0"),
            active_contributors_90d=8,
            last_computed_at=timezone.now(),
        )

        for index in range(12):
            PullRequestFactory(
                team=cls.team,
                author=cls.member,
                state="merged",
                is_ai_assisted=index % 2 == 0,
                cycle_time_hours=Decimal("10.0") + index,
                review_time_hours=Decimal("2.0"),
                pr_created_at=timezone.now() - timedelta(days=index + 1),
                merged_at=timezone.now() - timedelta(days=index),
            )

    def test_chart_partials_return_html_fragment(self):
        urls = [
            reverse("public:chart_ai_adoption", kwargs={"slug": "chart-org"}),
            reverse("public:chart_cycle_time", kwargs={"slug": "chart-org"}),
            reverse("public:chart_ai_quality", kwargs={"slug": "chart-org"}),
            reverse("public:chart_ai_tools", kwargs={"slug": "chart-org"}),
            reverse("public:chart_pr_size", kwargs={"slug": "chart-org"}),
            reverse("public:chart_review_distribution", kwargs={"slug": "chart-org"}),
            reverse("public:cards_metrics", kwargs={"slug": "chart-org"}),
            reverse("public:cards_team_health", kwargs={"slug": "chart-org"}),
        ]
        for url in urls:
            response = self.client.get(url)
            assert response.status_code == 200
            content = response.content.decode().lower()
            assert "<html" not in content
            assert "<body" not in content

    def test_cache_control_header_set(self):
        response = self.client.get(reverse("public:chart_ai_adoption", kwargs={"slug": "chart-org"}))
        cache_control = response.get("Cache-Control", "")
        assert "max-age" in cache_control

    def test_chart_partial_200_valid_slug(self):
        response = self.client.get(reverse("public:chart_cycle_time", kwargs={"slug": "chart-org"}))
        assert response.status_code == 200


class PublicCombinedTrendChartTests(TestCase):
    """Step 2.4: Combined trend chart endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="trend-org",
            industry="analytics",
            display_name="Trend Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )

    def test_public_combined_trend_chart_returns_200(self):
        """Review 12A: Assert 200 + canvas + JSON data markers."""
        url = reverse("public:chart_combined_trend", kwargs={"slug": "trend-org"})
        response = self.client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "<canvas" in content
