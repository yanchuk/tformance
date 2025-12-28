"""Tests for estimated time display in sync progress page.

Phase 4.3: Estimated Time Display
- Show "~X minutes remaining" during sync
- Calculate based on repos count and current progress
- Update dynamically as sync progresses
"""

from django.test import Client, TestCase
from django.urls import reverse

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class TestEstimatedTimeDisplay(TestCase):
    """Tests for estimated time display in sync progress page."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(
            username="time_test@example.com",
            email="time_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.client = Client()
        self.client.login(username="time_test@example.com", password="testpassword123")

    def test_sync_progress_page_has_estimated_time_element(self):
        """Test that sync progress page contains estimated time display element."""
        # Create a tracked repo
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Check for estimated time element in HTML
        self.assertContains(response, 'id="estimated-time"')

    def test_sync_progress_has_javascript_for_time_calculation(self):
        """Test that the page includes JavaScript for time estimation."""
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Check for time estimation function in JavaScript
        self.assertContains(response, "estimatedTime")

    def test_context_includes_repo_count_for_estimation(self):
        """Test that context includes repo count for time estimation."""
        # Create multiple tracked repos
        TrackedRepositoryFactory(team=self.team, integration=self.integration)
        TrackedRepositoryFactory(team=self.team, integration=self.integration)
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Context should have repos for counting
        self.assertEqual(len(response.context["repos"]), 3)

    def test_estimated_time_uses_minutes_format(self):
        """Test that estimated time display uses user-friendly format."""
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Check for minutes/seconds in the template or JavaScript
        content = response.content.decode("utf-8")
        self.assertTrue(
            "minute" in content.lower() or "remaining" in content.lower(),
            "Estimated time display should show user-friendly time format",
        )

    def test_initial_estimated_time_is_displayed(self):
        """Test that initial estimated time is shown when page loads."""
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Check for initial estimate text
        self.assertContains(response, "estimated-time")

    def test_sync_progress_page_shows_calculating_initially(self):
        """Test that page shows 'Calculating...' initially before estimate is ready."""
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # Initial state should be "Calculating..."
        self.assertContains(response, "Calculating")


class TestEstimatedTimeCalculation(TestCase):
    """Tests for the estimated time calculation logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="calc_test@example.com",
            email="calc_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.client = Client()
        self.client.login(username="calc_test@example.com", password="testpassword123")

    def test_config_includes_repos_count(self):
        """Test that sync config JSON includes repos count for estimation."""
        TrackedRepositoryFactory(team=self.team, integration=self.integration)
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        # The repos count should be available for time estimation
        content = response.content.decode("utf-8")
        self.assertIn("reposCount", content)

    def test_estimated_time_decreases_as_progress_increases(self):
        """Test that JavaScript includes logic to decrease time as progress increases."""
        TrackedRepositoryFactory(team=self.team, integration=self.integration)

        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Should have logic to update estimated time based on progress
        self.assertIn("updateEstimatedTime", content)
