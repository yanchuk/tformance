"""Tests for Bug 12: Public analytics must not leak private repo PR data.

When a public org's team has both public and private repos, the public
analytics pages should only show data from repos marked is_public=True
in PublicRepoProfile.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD, _base_pr_queryset
from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile


class PublicDataLeakTests(TestCase):
    """Verify private repo PRs are excluded from public views."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="mixed-org",
            industry="analytics",
            display_name="Mixed Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org,
            total_prs=MIN_PRS_THRESHOLD + 100,
            ai_assisted_pct=Decimal("30.0"),
        )

        # Public repo
        cls.public_repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="mixed-org/public-repo",
            repo_slug="public-repo",
            display_name="Public Repo",
            is_public=True,
            sync_enabled=True,
        )

        # Private repo (is_public=False)
        cls.private_repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="mixed-org/private-repo",
            repo_slug="private-repo",
            display_name="Private Repo",
            is_public=False,
            sync_enabled=True,
        )

        author = TeamMemberFactory(team=cls.team)

        # Create PRs for public repo
        now = datetime.now(tz=UTC)
        for i in range(3):
            PullRequestFactory(
                team=cls.team,
                github_repo="mixed-org/public-repo",
                title=f"Public PR {i}",
                state="merged",
                merged_at=now - timedelta(days=i + 1),
                author=author,
            )

        # Create PRs for private repo — these should NOT appear in public views
        for i in range(2):
            PullRequestFactory(
                team=cls.team,
                github_repo="mixed-org/private-repo",
                title=f"SECRET PRIVATE PR {i}",
                state="merged",
                merged_at=now - timedelta(days=i + 1),
                author=author,
            )

    def test_base_pr_queryset_with_allowed_repos_filters_correctly(self):
        """_base_pr_queryset with allowed_repos should only return PRs from those repos."""
        qs = _base_pr_queryset(
            self.team.id,
            allowed_repos=["mixed-org/public-repo"],
        )
        repos = set(qs.values_list("github_repo", flat=True))
        assert repos == {"mixed-org/public-repo"}, f"Expected only public repo, got {repos}"
        assert qs.count() == 3

    def test_base_pr_queryset_without_allowed_repos_returns_all(self):
        """_base_pr_queryset without allowed_repos returns all repos (backward compat)."""
        qs = _base_pr_queryset(self.team.id)
        repos = set(qs.values_list("github_repo", flat=True))
        assert "mixed-org/private-repo" in repos
        assert qs.count() == 5

    def test_public_pr_explorer_excludes_private_repos(self):
        """The public org PR explorer page must not show private repo PRs."""
        response = self.client.get(reverse("public:org_pr_list", kwargs={"slug": "mixed-org"}))
        assert response.status_code == 200
        content = response.content.decode()
        assert "SECRET PRIVATE PR" not in content, "Private PR title leaked in public view!"
        assert "Public PR" in content

    def test_public_org_overview_excludes_private_repos(self):
        """The public org overview page must not leak private repo data."""
        response = self.client.get(reverse("public:org_detail", kwargs={"slug": "mixed-org"}))
        assert response.status_code == 200
        content = response.content.decode()
        assert "mixed-org/private-repo" not in content


class PublicOrgProfilePropertyTests(TestCase):
    """Test the public_github_repos helper property."""

    def test_public_github_repos_returns_only_public(self):
        team = TeamFactory()
        org = PublicOrgProfile.objects.create(
            team=team,
            public_slug="prop-test",
            industry="analytics",
            display_name="Prop Test",
            is_public=True,
        )
        PublicRepoProfile.objects.create(
            org_profile=org,
            github_repo="org/repo-a",
            repo_slug="repo-a",
            display_name="Repo A",
            is_public=True,
        )
        PublicRepoProfile.objects.create(
            org_profile=org,
            github_repo="org/repo-b",
            repo_slug="repo-b",
            display_name="Repo B",
            is_public=False,
        )

        result = org.public_github_repos
        assert result == ["org/repo-a"], f"Expected only public repo, got {result}"
