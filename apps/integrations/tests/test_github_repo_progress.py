"""Tests for GitHub repository sync progress endpoint."""

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory, UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class GitHubRepoSyncProgressViewTest(TestCase):
    """Tests for github_repo_sync_progress view (HTMX polling endpoint)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.integration = GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=12345,
            full_name="acme-corp/test-repo",
            sync_status="syncing",
            sync_progress=50,
            sync_prs_total=100,
            sync_prs_completed=50,
        )
        self.client = Client()

    def test_progress_returns_200_for_valid_repo(self):
        """Test that progress endpoint returns 200 for a valid tracked repository."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repo_sync_progress", args=[self.tracked_repo.id]))

        self.assertEqual(response.status_code, 200)

    def test_progress_returns_404_for_invalid_repo(self):
        """Test that progress endpoint returns 404 for non-existent repository."""
        self.client.force_login(self.admin)

        # Use a non-existent repo ID
        response = self.client.get(reverse("integrations:github_repo_sync_progress", args=[99999]))

        self.assertEqual(response.status_code, 404)

    def test_progress_includes_sync_status(self):
        """Test that progress response includes sync_status field."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repo_sync_progress", args=[self.tracked_repo.id]))

        self.assertEqual(response.status_code, 200)
        # Response should contain the sync status
        content = response.content.decode()
        self.assertIn("syncing", content.lower())

    def test_progress_includes_progress_fields(self):
        """Test that progress response includes sync_progress, sync_prs_completed, and sync_prs_total."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repo_sync_progress", args=[self.tracked_repo.id]))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Should include progress percentage
        self.assertIn("50", content)  # sync_progress = 50

        # Should include completed/total counts
        self.assertIn("100", content)  # sync_prs_total = 100
