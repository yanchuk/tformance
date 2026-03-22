from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import TeamFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoProfile,
    PublicRepoStats,
)


class OrgHubViewTests(TestCase):
    """Tests for the org detail page acting as a discovery hub with repo cards."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="hubtest",
            industry="analytics",
            display_name="Hub Test Org",
            is_public=True,
        )
        cls.org_stats = PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 100,
            ai_assisted_pct=Decimal("32.5"),
            median_cycle_time_hours=Decimal("18.0"),
            median_review_time_hours=Decimal("4.2"),
            active_contributors_90d=25,
            last_computed_at=timezone.now(),
        )
        # Flagship + public repo
        cls.flagship_repo = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="hubtest/main-app",
            repo_slug="main-app",
            display_name="Main App",
            is_flagship=True,
            is_public=True,
        )
        PublicRepoStats.objects.create(
            repo_profile=cls.flagship_repo,
            total_prs=300,
            total_prs_in_window=50,
            ai_assisted_pct=Decimal("40.0"),
            median_cycle_time_hours=Decimal("12.5"),
            active_contributors_30d=10,
            last_computed_at=timezone.now(),
        )
        # Second flagship repo
        cls.flagship_repo2 = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="hubtest/api-server",
            repo_slug="api-server",
            display_name="API Server",
            is_flagship=True,
            is_public=True,
        )
        PublicRepoStats.objects.create(
            repo_profile=cls.flagship_repo2,
            total_prs=200,
            total_prs_in_window=30,
            ai_assisted_pct=Decimal("55.0"),
            median_cycle_time_hours=Decimal("8.3"),
            active_contributors_30d=7,
            last_computed_at=timezone.now(),
        )
        # Non-flagship repo (should NOT appear)
        cls.non_flagship_repo = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="hubtest/docs",
            repo_slug="docs",
            display_name="Documentation",
            is_flagship=False,
            is_public=True,
        )
        # Non-public repo (should NOT appear)
        cls.non_public_repo = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="hubtest/internal",
            repo_slug="internal",
            display_name="Internal Tool",
            is_flagship=True,
            is_public=False,
        )

    def _url(self):
        return reverse("public:org_detail", kwargs={"slug": "hubtest"})

    def test_org_hub_shows_flagship_repos(self):
        """Org detail page includes display names of flagship public repos."""
        response = self.client.get(self._url())
        assert response.status_code == 200
        content = response.content.decode()
        assert "Main App" in content
        assert "API Server" in content

    def test_org_hub_repo_cards_link_to_repo_detail(self):
        """Each repo card contains a link to the repo detail page."""
        response = self.client.get(self._url())
        content = response.content.decode()
        main_app_url = reverse(
            "public:repo_detail",
            kwargs={"slug": "hubtest", "repo_slug": "main-app"},
        )
        api_server_url = reverse(
            "public:repo_detail",
            kwargs={"slug": "hubtest", "repo_slug": "api-server"},
        )
        assert main_app_url in content
        assert api_server_url in content

    def test_org_hub_hides_non_public_repos(self):
        """Repos with is_public=False should not appear on the hub page."""
        response = self.client.get(self._url())
        content = response.content.decode()
        assert "Internal Tool" not in content

    def test_org_hub_hides_non_flagship_repos(self):
        """Repos with is_flagship=False should not appear on the hub page."""
        response = self.client.get(self._url())
        content = response.content.decode()
        assert "Documentation" not in content

    def test_org_hub_shows_org_stats(self):
        """Org-level benchmark sentence with stats should still be present."""
        response = self.client.get(self._url())
        content = response.content.decode()
        # Check org-level stats are still rendered
        assert "32.5" in content  # ai_assisted_pct
        assert "18.0" in content  # median_cycle_time_hours


class OrgHubEmptyReposTests(TestCase):
    """Tests for the org hub when there are no flagship repos."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="emptyorg",
            industry="devtools",
            display_name="Empty Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 50,
            ai_assisted_pct=Decimal("10.0"),
            median_cycle_time_hours=Decimal("20.0"),
            median_review_time_hours=Decimal("5.0"),
            active_contributors_90d=8,
            last_computed_at=timezone.now(),
        )

    def test_org_hub_shows_empty_message_when_no_repos(self):
        """When org has no flagship repos, show an appropriate message."""
        url = reverse("public:org_detail", kwargs={"slug": "emptyorg"})
        response = self.client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "No flagship repositories" in content
