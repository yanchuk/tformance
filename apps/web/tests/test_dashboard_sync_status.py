"""
Tests for sync status information in dashboard context.

These tests verify that the dashboard view includes sync status info:
- sync_in_progress: Boolean - are any repos syncing?
- sync_progress_percent: Int - overall progress (0-100)
- repos_syncing: List - names of repos currently syncing
- repos_total: Int - total tracked repos
- repos_synced: Int - repos that completed sync
"""

from django.test import TestCase
from django.urls import reverse

from apps.integrations.constants import SYNC_STATUS_COMPLETE, SYNC_STATUS_PENDING, SYNC_STATUS_SYNCING
from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Membership
from apps.users.models import CustomUser


class TestDashboardSyncStatus(TestCase):
    """Tests for sync status in dashboard context."""

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

    def test_dashboard_context_includes_sync_in_progress_field(self):
        """Test that dashboard context includes sync_in_progress field."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("sync_in_progress", response.context)

    def test_sync_in_progress_true_when_repos_syncing(self):
        """Test that sync_in_progress is True when any repos are syncing."""
        # Create GitHub integration and repos
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-complete",
            sync_status=SYNC_STATUS_COMPLETE,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["sync_in_progress"])

    def test_sync_in_progress_false_when_no_repos_syncing(self):
        """Test that sync_in_progress is False when no repos are syncing."""
        # Create GitHub integration and repos - all complete
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-1",
            sync_status=SYNC_STATUS_COMPLETE,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-2",
            sync_status=SYNC_STATUS_COMPLETE,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["sync_in_progress"])

    def test_sync_in_progress_false_when_no_repos(self):
        """Test that sync_in_progress is False when team has no tracked repos."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["sync_in_progress"])

    def test_dashboard_context_includes_sync_progress_percent(self):
        """Test that dashboard context includes sync_progress_percent field."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("sync_progress_percent", response.context)

    def test_sync_progress_percent_calculation(self):
        """Test that sync_progress_percent is calculated correctly.

        With 3 repos: 1 syncing at 50%, 1 complete (100%), 1 pending (0%)
        Average should be (50 + 100 + 0) / 3 = 50%
        """
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
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-pending",
            sync_status=SYNC_STATUS_PENDING,
            sync_progress=0,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sync_progress_percent"], 50)

    def test_dashboard_context_includes_repos_syncing_list(self):
        """Test that dashboard context includes repos_syncing list with repo names."""
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/syncing-repo-1",
            sync_status=SYNC_STATUS_SYNCING,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/syncing-repo-2",
            sync_status=SYNC_STATUS_SYNCING,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/complete-repo",
            sync_status=SYNC_STATUS_COMPLETE,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("repos_syncing", response.context)

        repos_syncing = response.context["repos_syncing"]
        self.assertIsInstance(repos_syncing, list)
        self.assertEqual(len(repos_syncing), 2)
        self.assertIn("org/syncing-repo-1", repos_syncing)
        self.assertIn("org/syncing-repo-2", repos_syncing)
        self.assertNotIn("org/complete-repo", repos_syncing)

    def test_dashboard_context_includes_repos_total(self):
        """Test that dashboard context includes repos_total count."""
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory.create_batch(
            3,
            team=self.team,
            integration=integration,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("repos_total", response.context)
        self.assertEqual(response.context["repos_total"], 3)

    def test_dashboard_context_includes_repos_synced(self):
        """Test that dashboard context includes repos_synced count."""
        integration = GitHubIntegrationFactory(team=self.team)
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
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            sync_status=SYNC_STATUS_SYNCING,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            sync_status=SYNC_STATUS_PENDING,
        )

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("repos_synced", response.context)
        self.assertEqual(response.context["repos_synced"], 2)


class TestDashboardSyncStatusTeamIsolation(TestCase):
    """Tests for team isolation of sync status in dashboard."""

    def setUp(self):
        """Set up test fixtures with two teams."""
        # Team A
        self.team_a = TeamFactory(name="Team A", slug="team-a")
        self.user_a = CustomUser.objects.create_user(
            username="user_a@example.com",
            email="user_a@example.com",
            password="testpass123",
        )
        Membership.objects.create(team=self.team_a, user=self.user_a, role="admin")

        # Team B
        self.team_b = TeamFactory(name="Team B", slug="team-b")
        self.user_b = CustomUser.objects.create_user(
            username="user_b@example.com",
            email="user_b@example.com",
            password="testpass123",
        )
        Membership.objects.create(team=self.team_b, user=self.user_b, role="admin")

        # Create repos for each team
        self.integration_a = GitHubIntegrationFactory(team=self.team_a)
        self.integration_b = GitHubIntegrationFactory(team=self.team_b)

        # Team A: 2 repos, 1 syncing
        TrackedRepositoryFactory(
            team=self.team_a,
            integration=self.integration_a,
            full_name="team-a/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
        )
        TrackedRepositoryFactory(
            team=self.team_a,
            integration=self.integration_a,
            full_name="team-a/repo-complete",
            sync_status=SYNC_STATUS_COMPLETE,
        )

        # Team B: 3 repos, all complete
        TrackedRepositoryFactory.create_batch(
            3,
            team=self.team_b,
            integration=self.integration_b,
            sync_status=SYNC_STATUS_COMPLETE,
        )

        self.dashboard_url = reverse("web_team:home")

    def test_sync_status_only_shows_own_team_repos(self):
        """Test that sync status only includes repos from the user's team."""
        self.client.login(username="user_a@example.com", password="testpass123")
        # Set team A in session
        session = self.client.session
        session["team"] = self.team_a.id
        session.save()

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Team A has 2 repos total
        self.assertEqual(response.context["repos_total"], 2)
        # Team A has 1 syncing repo
        self.assertTrue(response.context["sync_in_progress"])
        self.assertEqual(len(response.context["repos_syncing"]), 1)
        self.assertIn("team-a/repo-syncing", response.context["repos_syncing"])
        # Team A has 1 complete repo
        self.assertEqual(response.context["repos_synced"], 1)

    def test_other_team_repos_not_visible(self):
        """Test that repos from other teams are not included in sync status."""
        self.client.login(username="user_b@example.com", password="testpass123")
        # Set team B in session
        session = self.client.session
        session["team"] = self.team_b.id
        session.save()

        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Team B has 3 repos total, all complete
        self.assertEqual(response.context["repos_total"], 3)
        self.assertFalse(response.context["sync_in_progress"])
        self.assertEqual(len(response.context["repos_syncing"]), 0)
        self.assertEqual(response.context["repos_synced"], 3)

        # Team A's syncing repo should not be visible
        self.assertNotIn("team-a/repo-syncing", response.context["repos_syncing"])
