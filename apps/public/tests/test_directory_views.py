from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.metrics.factories import TeamFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoRequest
from apps.teams.models import Team


class PublicDirectoryViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.public_team = TeamFactory()
        cls.public_profile = PublicOrgProfile.objects.create(
            team=cls.public_team,
            public_slug="visible-org",
            industry="analytics",
            display_name="Visible Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.public_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
            ai_assisted_pct=Decimal("45.0"),
            median_cycle_time_hours=Decimal("12.5"),
        )

        cls.private_team = TeamFactory()
        cls.private_profile = PublicOrgProfile.objects.create(
            team=cls.private_team,
            public_slug="hidden-org",
            industry="analytics",
            display_name="Hidden Org",
            is_public=False,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.private_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
            ai_assisted_pct=Decimal("60.0"),
        )

    def setUp(self):
        cache.clear()

    def test_directory_loads_for_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse("public:directory"))
        assert response.status_code == 200

    def test_private_team_not_in_directory(self):
        response = self.client.get(reverse("public:directory"))
        assert b"Visible Org" in response.content
        assert b"Hidden Org" not in response.content

    def test_directory_htmx_returns_partial(self):
        response = self.client.get(reverse("public:directory"), HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "<!DOCTYPE" not in content
        assert "Visible Org" in content

    def test_directory_htmx_partial_not_poisoned_by_cached_full_page(self):
        full_page = self.client.get(reverse("public:directory"))
        assert full_page.status_code == 200

        response = self.client.get(reverse("public:directory"), HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "<!DOCTYPE" not in content
        assert "Visible Org" in content

    def test_industry_page_loads(self):
        response = self.client.get(reverse("public:industry", kwargs={"industry": "analytics"}))
        assert response.status_code == 200
        assert b"Visible Org" in response.content

    def test_request_repo_form_submit_success(self):
        response = self.client.post(
            reverse("public:request_repo"),
            {
                "github_url": "https://github.com/test-org/test-repo",
                "email": "maintainer@example.com",
                "role": "maintainer",
            },
        )
        assert response.status_code == 302
        assert response.url == reverse("public:request_success")
        assert PublicRepoRequest.objects.count() == 1


class DirectoryBenchmarkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for i, (name, ai_pct, cycle, review, prs, contributors, industry) in enumerate(
            [
                ("Alpha", 40, 18, 4, 2000, 20, "analytics"),
                ("Beta", 60, 12, 3, 1500, 15, "devops"),
                ("Gamma", 25, 30, 8, 3000, 30, "analytics"),
            ]
        ):
            team = Team.objects.create(name=name, slug=f"bench-{i}")
            org = PublicOrgProfile.objects.create(
                team=team,
                public_slug=f"bench-{i}",
                industry=industry,
                display_name=name,
                is_public=True,
            )
            PublicOrgStats.objects.create(
                org_profile=org,
                total_prs=prs,
                ai_assisted_pct=ai_pct,
                median_cycle_time_hours=cycle,
                median_review_time_hours=review,
                active_contributors_90d=contributors,
            )

    def setUp(self):
        cache.clear()

    def test_directory_context_has_scatter_chart_data(self):
        response = self.client.get("/open-source/")
        assert "scatter_data" in response.context

    def test_directory_context_has_industry_benchmarks(self):
        response = self.client.get("/open-source/")
        assert "industry_benchmarks" in response.context

    def test_directory_context_has_aggregate_trend(self):
        response = self.client.get("/open-source/")
        assert "aggregate_trend" in response.context

    def test_directory_has_no_ci_cd_content(self):
        """Review 11A: Directory must not mention CI/CD."""
        response = self.client.get("/open-source/")
        content = response.content.decode().lower()
        for term in ["ci/cd", "check-run", "deployment frequency"]:
            assert term not in content, f"Found '{term}' on directory"
