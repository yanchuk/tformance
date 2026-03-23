"""Tests for repo-level PR explorer views (T8).

Verifies that:
- repo_pr_list loads with correct status
- PRs are scoped to the specific repo only
- SEO meta tags (noindex, canonical) are present
- Org-level tabs are hidden on repo pages
- HTMX table partial works for filtering/pagination
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoProfile,
)


class RepoPrExplorerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="testorg",
            industry="analytics",
            display_name="Test Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="testorg/main-repo",
            repo_slug="main-repo",
            display_name="Main Repo",
            is_flagship=True,
            is_public=True,
        )

        # Create PRs for the target repo
        now = timezone.now()
        for i in range(3):
            PullRequestFactory(
                team=cls.team,
                author=cls.member,
                github_repo="testorg/main-repo",
                state="merged",
                title=f"Main repo PR {i}",
                is_ai_assisted=i == 0,
                cycle_time_hours=Decimal("10.0"),
                review_time_hours=Decimal("2.0"),
                additions=20,
                deletions=10,
                pr_created_at=now - timedelta(days=10 - i),
                merged_at=now - timedelta(days=9 - i),
            )

        # Create PRs for a DIFFERENT repo (should NOT appear)
        for i in range(2):
            PullRequestFactory(
                team=cls.team,
                author=cls.member,
                github_repo="testorg/other-repo",
                state="merged",
                title=f"Other repo PR {i}",
                is_ai_assisted=False,
                cycle_time_hours=Decimal("15.0"),
                review_time_hours=Decimal("3.0"),
                additions=30,
                deletions=15,
                pr_created_at=now - timedelta(days=10 - i),
                merged_at=now - timedelta(days=9 - i),
            )

        cls.pr_list_url = reverse(
            "public:repo_pr_list",
            kwargs={"slug": "testorg", "repo_slug": "main-repo"},
        )
        cls.pr_list_table_url = reverse(
            "public:repo_pr_list_table",
            kwargs={"slug": "testorg", "repo_slug": "main-repo"},
        )
        cls.repo_detail_url = reverse(
            "public:repo_detail",
            kwargs={"slug": "testorg", "repo_slug": "main-repo"},
        )

    def test_repo_pr_list_200(self):
        """Page loads successfully with HTTP 200."""
        response = self.client.get(self.pr_list_url)
        assert response.status_code == 200

    def test_repo_pr_list_scoped_to_repo(self):
        """Only PRs for the specific repo appear, not PRs from other repos."""
        response = self.client.get(self.pr_list_url)
        content = response.content.decode()
        assert "Main repo PR" in content
        assert "Other repo PR" not in content

    def test_repo_pr_list_has_noindex_meta(self):
        """Page must contain noindex robot meta tag for SEO."""
        response = self.client.get(self.pr_list_url)
        content = response.content.decode()
        assert 'content="noindex,follow"' in content or 'content="noindex, follow"' in content

    def test_repo_pr_list_has_canonical_to_repo_detail(self):
        """Canonical URL must point to the repo detail page."""
        response = self.client.get(self.pr_list_url)
        content = response.content.decode()
        # The canonical link should contain the repo_detail URL path
        assert self.repo_detail_url in content

    def test_repo_pr_list_is_repo_page(self):
        """Repo PR list should NOT show org-level tabs."""
        response = self.client.get(self.pr_list_url)
        content = response.content.decode()
        assert 'role="tablist"' not in content

    def test_repo_pr_list_table_htmx(self):
        """HTMX table partial endpoint returns 200."""
        response = self.client.get(
            self.pr_list_table_url,
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
