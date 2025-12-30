"""
Tests for partial data display during sync.

Phase 3.3 - Partial Data Display
These tests verify that the dashboard correctly shows data as it becomes available
during a sync operation, rather than waiting for sync to complete.

Key behaviors:
- Dashboard shows quick_stats when some PRs exist and sync is in progress
- has_data=True while sync_in_progress=True (both can be true simultaneously)
- "Waiting for data" view shows sync indicator when syncing but no PRs yet
- Quick stats show correct values from partially synced data
- Dashboard transitions from waiting state to data view as soon as first PR arrives
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.integrations.constants import (
    SYNC_STATUS_COMPLETE,
    SYNC_STATUS_PENDING,
    SYNC_STATUS_SYNCING,
)
from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.teams.models import Membership
from apps.users.models import CustomUser


class TestDashboardPartialDataDisplay(TestCase):
    """Tests for partial data display during sync."""

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

    def test_dashboard_shows_quick_stats_when_prs_exist_and_sync_in_progress(self):
        """Test that quick_stats are displayed when PRs exist even during sync."""
        # Arrange: Create GitHub integration with syncing repos
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
        )

        # Create some PRs (partial data)
        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=1),
        )
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=2),
        )

        # Act
        response = self.client.get(self.dashboard_url)

        # Assert
        self.assertEqual(response.status_code, 200)
        # Both conditions should be true
        self.assertTrue(response.context["integration_status"]["has_data"])
        self.assertTrue(response.context["sync_in_progress"])
        # Quick stats should be present in context
        self.assertIn("quick_stats", response.context)

    def test_has_data_and_sync_in_progress_can_both_be_true(self):
        """Test that has_data=True and sync_in_progress=True are not mutually exclusive."""
        # Arrange: Create integration with partial sync state
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-complete",
            sync_status=SYNC_STATUS_COMPLETE,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
        )

        # Create PRs from the completed repo
        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=1),
        )

        # Act
        response = self.client.get(self.dashboard_url)

        # Assert - both flags should be True
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["integration_status"]["has_data"])
        self.assertTrue(response.context["sync_in_progress"])

    def test_waiting_for_data_view_shows_sync_indicator_when_syncing(self):
        """Test that 'Waiting for data' state shows sync indicator when repos are syncing."""
        # Arrange: Create integration with syncing repos but no PRs yet
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
            sync_progress=30,
        )

        # Act
        response = self.client.get(self.dashboard_url)

        # Assert
        self.assertEqual(response.status_code, 200)
        # Should be in waiting state (has_data=False)
        self.assertFalse(response.context["integration_status"]["has_data"])
        # But sync should be in progress
        self.assertTrue(response.context["sync_in_progress"])
        # Should show the sync indicator
        self.assertContains(response, 'id="sync-indicator"')

    def test_quick_stats_show_correct_values_from_partial_data(self):
        """Test that quick stats accurately reflect partially synced PR data."""
        # Arrange
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
        )

        member = TeamMemberFactory(team=self.team)
        # Create 3 merged PRs in the last 7 days
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i + 1),
            )

        # Act
        response = self.client.get(self.dashboard_url)

        # Assert
        self.assertEqual(response.status_code, 200)
        quick_stats = response.context.get("quick_stats")
        self.assertIsNotNone(quick_stats)
        # Should show 3 merged PRs
        self.assertEqual(quick_stats["prs_merged"]["count"], 3)

    def test_dashboard_transitions_to_data_view_when_first_pr_arrives(self):
        """Test that dashboard shows data view as soon as first PR is synced."""
        # Arrange: Start with syncing but no data
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-syncing",
            sync_status=SYNC_STATUS_SYNCING,
        )

        # Verify initially in waiting state
        response = self.client.get(self.dashboard_url)
        self.assertFalse(response.context["integration_status"]["has_data"])
        self.assertContains(response, "Waiting for Data")

        # Create the first PR (simulate sync progress)
        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=1),
        )

        # Act: Fetch dashboard again
        response = self.client.get(self.dashboard_url)

        # Assert: Should now be in data view
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["integration_status"]["has_data"])
        # Should show the dashboard layout instead of "Waiting for Data"
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "key-metrics-container")  # HTMX lazy-loaded section
        self.assertNotContains(response, "Waiting for Data")


class TestDashboardPartialDataSyncProgress(TestCase):
    """Tests for sync progress display with partial data."""

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

    def test_sync_indicator_visible_on_data_view_when_syncing(self):
        """Test that sync indicator banner is visible on data view during sync."""
        # Arrange: Data exists and sync is in progress
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/completed-repo",
            sync_status=SYNC_STATUS_COMPLETE,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/syncing-repo",
            sync_status=SYNC_STATUS_SYNCING,
        )

        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=1),
        )

        # Act
        response = self.client.get(self.dashboard_url)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["integration_status"]["has_data"])
        self.assertContains(response, 'id="sync-indicator"')

    def test_quick_stats_update_as_more_prs_sync(self):
        """Test that quick stats update correctly as more PRs are synced."""
        # Arrange: Start with some PRs
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            sync_status=SYNC_STATUS_SYNCING,
        )

        member = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=1),
        )

        # First check
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.context["quick_stats"]["prs_merged"]["count"], 1)

        # Add more PRs (simulate ongoing sync)
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=2),
        )
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=3),
        )

        # Act: Check stats again
        response = self.client.get(self.dashboard_url)

        # Assert: Should show updated count
        self.assertEqual(response.context["quick_stats"]["prs_merged"]["count"], 3)

    def test_partial_data_shows_pr_count_in_team_overview(self):
        """Test that team overview shows correct PR count from partial data."""
        # Arrange
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            sync_status=SYNC_STATUS_SYNCING,
        )

        member = TeamMemberFactory(team=self.team)
        # Create 5 PRs
        PullRequestFactory.create_batch(5, team=self.team, author=member, state="merged")

        # Act
        response = self.client.get(self.dashboard_url)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["integration_status"]["pr_count"], 5)


class TestDashboardWaitingForDataState(TestCase):
    """Tests for the 'Waiting for Data' state display."""

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

    def test_waiting_state_shows_sync_progress_info(self):
        """Test that waiting state displays sync progress information."""
        # Arrange: GitHub connected, repos syncing, no data yet
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-1",
            sync_status=SYNC_STATUS_SYNCING,
            sync_progress=50,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-2",
            sync_status=SYNC_STATUS_PENDING,
            sync_progress=0,
        )

        # Act
        response = self.client.get(self.dashboard_url)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["integration_status"]["has_data"])
        self.assertTrue(response.context["sync_in_progress"])
        # Verify sync status details
        self.assertEqual(response.context["repos_total"], 2)
        self.assertEqual(response.context["repos_synced"], 0)
        self.assertIn("org/repo-1", response.context["repos_syncing"])

    def test_waiting_state_without_sync_shows_no_sync_indicator(self):
        """Test that waiting state without active sync doesn't show sync indicator."""
        # Arrange: GitHub connected, repos completed sync, but no data (edge case)
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            full_name="org/repo-complete",
            sync_status=SYNC_STATUS_COMPLETE,
        )

        # Act
        response = self.client.get(self.dashboard_url)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["integration_status"]["has_data"])
        self.assertFalse(response.context["sync_in_progress"])
        # Should NOT show sync indicator
        self.assertNotContains(response, 'id="sync-indicator"')

    def test_quick_stats_not_present_when_no_data(self):
        """Test that quick_stats context is not present when has_data=False."""
        # Arrange: GitHub connected, syncing, no PRs
        integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            sync_status=SYNC_STATUS_SYNCING,
        )

        # Act
        response = self.client.get(self.dashboard_url)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["integration_status"]["has_data"])
        # quick_stats should NOT be in context when no data
        self.assertNotIn("quick_stats", response.context)
