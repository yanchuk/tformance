from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats


class PublicOrgViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)
        cls.profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="posthog",
            industry="analytics",
            display_name="PostHog",
            is_public=True,
            github_org_url="https://github.com/PostHog",
        )
        PublicOrgStats.objects.create(
            org_profile=cls.profile,
            total_prs=MIN_PRS_THRESHOLD + 20,
            ai_assisted_pct=Decimal("21.0"),
            median_cycle_time_hours=Decimal("17.2"),
            median_review_time_hours=Decimal("3.1"),
            active_contributors_90d=12,
            last_computed_at=timezone.now(),
        )

        for index in range(8):
            PullRequestFactory(
                team=cls.team,
                author=cls.member,
                state="merged",
                title=f"Public PR {index}",
                is_ai_assisted=index % 2 == 0,
                cycle_time_hours=Decimal("12.0") + index,
                review_time_hours=Decimal("2.0"),
                additions=20 + index,
                deletions=10,
                pr_created_at=timezone.now() - timedelta(days=15 - index),
                merged_at=timezone.now() - timedelta(days=14 - index),
            )

    def test_org_detail_200_valid_slug(self):
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "posthog"}))
        assert response.status_code == 200
        assert b"PostHog Engineering Metrics" in response.content

    def test_org_detail_links_to_analytics_and_pr_list(self):
        """Hub page should link to analytics and PR list pages."""
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "posthog"}))
        self.assertContains(response, reverse("public:org_analytics", kwargs={"slug": "posthog"}))
        self.assertContains(response, reverse("public:org_pr_list", kwargs={"slug": "posthog"}))

    def test_pr_list_200_with_filters(self):
        response = self.client.get(reverse("public:org_pr_list", kwargs={"slug": "posthog"}), {"ai": "yes"})
        assert response.status_code == 200
        assert b"Pull Request Explorer" in response.content

    def test_pr_list_table_htmx_urls_correct(self):
        response = self.client.get(reverse("public:pr_list_table", kwargs={"slug": "posthog"}))
        assert response.status_code == 200
        self.assertContains(response, reverse("public:pr_list_table", kwargs={"slug": "posthog"}))

    def test_no_export_link_in_public_view(self):
        response = self.client.get(reverse("public:org_pr_list", kwargs={"slug": "posthog"}))
        assert response.status_code == 200
        assert b"Export CSV" in response.content
        assert b"disabled" in response.content

    def test_no_notes_or_feedback_ui(self):
        response = self.client.get(reverse("public:org_pr_list", kwargs={"slug": "posthog"}))
        content = response.content.decode().lower()
        assert "note_icon" not in content
        assert "feedback" not in content
