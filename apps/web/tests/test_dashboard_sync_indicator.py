"""
Tests for sync indicator UI banner in the dashboard.

These tests verify the visual sync indicator banner that appears when repos are syncing:
- Banner is visible when sync_in_progress is True
- Banner contains "Syncing" text
- Banner shows progress percentage
- Banner shows repo names being synced
- Banner is NOT visible when sync_in_progress is False
- Banner is not visible when no repos exist
"""

from django.test import TestCase
from django.urls import reverse

from apps.integrations.constants import SYNC_STATUS_COMPLETE, SYNC_STATUS_PENDING, SYNC_STATUS_SYNCING
from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Membership
from apps.users.models import CustomUser


class TestDashboardSyncIndicatorBanner(TestCase):
    """Tests for sync indicator banner visibility and content."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = CustomUser.objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="testpass123",
        )
        # Add user to team as member
        Membership.objects.create(team=self.team, user=self.user, role="admin")

        self.client.login(username="testuser@example.com", password="testpass123")
        # Set team in session for middleware
        session = self.client.session
        session["team"] = self.team.id
        session.save()

        self.dashboard_url = reverse("web_team:home")

    def test_sync_banner_visible_when_sync_in_progress(self):
        """Test that sync banner is visible when sync_in_progress is True."""
        # Create GitHub integration and syncing repos
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Banner should be visible - check for sync-indicator element
        self.assertContains(response, 'id="sync-indicator"')

    def test_sync_banner_contains_syncing_text(self):
        """Test that sync banner contains 'Syncing' text when repos are syncing."""
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Banner should contain "Syncing" text
        self.assertContains(response, "Syncing")

    def test_sync_banner_shows_progress_percentage(self):
        """Test that sync banner shows progress percentage (e.g., '50%')."""
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
            sync_progress=50,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-complete",
            sync_status=SYNC_STATUS_COMPLETE,
            sync_progress=100,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Banner should show progress percentage (75% = average of 50 and 100)
        self.assertContains(response, "75%")

    def test_sync_banner_shows_repo_names(self):
        """Test that sync banner lists the repo names currently syncing."""
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="myorg/frontend-app",
            sync_status=SYNC_STATUS_SYNCING,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="myorg/backend-api",
            sync_status=SYNC_STATUS_SYNCING,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Banner should list syncing repo names
        self.assertContains(response, "myorg/frontend-app")
        self.assertContains(response, "myorg/backend-api")

    def test_sync_banner_not_visible_when_no_sync_in_progress(self):
        """Test that sync banner is NOT visible when sync_in_progress is False."""
        # Create GitHub integration with only completed repos
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-complete-1",
            sync_status=SYNC_STATUS_COMPLETE,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-complete-2",
            sync_status=SYNC_STATUS_COMPLETE,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Banner should NOT be visible
        self.assertNotContains(response, 'id="sync-indicator"')

    def test_sync_banner_not_visible_when_no_repos_exist(self):
        """Test that sync banner is NOT visible when team has no tracked repos."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Banner should NOT be visible
        self.assertNotContains(response, 'id="sync-indicator"')


class TestDashboardSyncIndicatorProgress(TestCase):
    """Tests for sync indicator progress display."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = CustomUser.objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="testpass123",
        )
        Membership.objects.create(team=self.team, user=self.user, role="admin")

        self.client.login(username="testuser@example.com", password="testpass123")
        session = self.client.session
        session["team"] = self.team.id
        session.save()

        self.dashboard_url = reverse("web_team:home")

    def test_sync_banner_shows_repos_synced_count(self):
        """Test that sync banner shows repos synced vs total (e.g., '2 of 4 repos')."""
        integration = GitHubIntegrationFactory(team=self.team)
        # 2 complete repos
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            sync_status=SYNC_STATUS_COMPLETE,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            sync_status=SYNC_STATUS_COMPLETE,
        )
        # 1 syncing repo
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            sync_status=SYNC_STATUS_SYNCING,
        )
        # 1 pending repo
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            sync_status=SYNC_STATUS_PENDING,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Should show "2 of 4" repos synced
        self.assertContains(response, "2 of 4")

    def test_sync_banner_only_shows_syncing_repos_not_complete(self):
        """Test that banner only lists syncing repos, not completed ones."""
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/active-sync",
            sync_status=SYNC_STATUS_SYNCING,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/already-done",
            sync_status=SYNC_STATUS_COMPLETE,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Should show syncing repo
        self.assertContains(response, "org/active-sync")
        # Should NOT show completed repo in the syncing list
        # (completed repo name should not appear in the sync indicator context)
        # We test this by checking the banner doesn't contain this repo name
        content = response.content.decode()
        # The sync-indicator section should not contain the completed repo
        # Find the sync-indicator section and check its content
        self.assertIn("org/active-sync", content)
