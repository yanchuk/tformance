"""Tests for P2 and P3 onboarding UX improvements.

These tests verify the remaining UX improvements:
- P2: Mobile step indicator responsiveness (CSS classes)
- P2: Enhanced floating sync indicator
- P2: Focus states for interactive cards
- P3: Loading states on OAuth buttons
- P3: Celebration animation on complete page
"""

from django.test import TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from apps.integrations.factories import GitHubIntegrationFactory, TrackedRepositoryFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Flag
from apps.users.models import CustomUser


class MobileStepIndicatorTests(TestCase):
    """Tests for mobile-responsive step indicator."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="mobile@example.com",
            email="mobile@example.com",
            password="testpassword123",
        )
        self.client.login(username="mobile@example.com", password="testpassword123")

    def test_step_labels_have_mobile_hiding_class(self):
        """Test that step labels have classes to hide on mobile."""
        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Labels should be hidden on mobile (hidden sm:block or similar)
        self.assertIn("hidden sm:block", content)


class EnhancedSyncIndicatorTests(TestCase):
    """Tests for enhanced floating sync indicator."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="sync_enhanced@example.com",
            email="sync_enhanced@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.integration = GitHubIntegrationFactory(team=self.team)
        TrackedRepositoryFactory(team=self.team, integration=self.integration)
        self.client.login(username="sync_enhanced@example.com", password="testpassword123")

    def test_sync_indicator_has_entrance_animation(self):
        """Test that sync indicator has animation class."""
        response = self.client.get(reverse("onboarding:sync_progress"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have animation class (fa-spin for spinner, or animate-* for others)
        self.assertTrue(
            "fa-spin" in content or "animate-" in content,
            "Expected animation class (fa-spin or animate-*) not found",
        )


@override_flag("integration_jira_enabled", active=True)
class FocusStatesTests(TestCase):
    """Tests for focus states on interactive elements."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure flags exist for override_flag to work
        Flag.objects.get_or_create(name="integration_jira_enabled")

        self.user = CustomUser.objects.create_user(
            username="focus@example.com",
            email="focus@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.client.login(username="focus@example.com", password="testpassword123")

    def test_jira_connect_button_has_focus_ring(self):
        """Test that Jira connect button has focus ring styles."""
        response = self.client.get(reverse("onboarding:connect_jira"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Primary buttons should have focus ring (defined in design-system.css)
        self.assertIn("app-btn-primary", content)


@override_flag("integration_jira_enabled", active=True)
@override_flag("integration_slack_enabled", active=True)
class OAuthLoadingStateTests(TestCase):
    """Tests for loading states on OAuth buttons."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure flags exist for override_flag to work
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

        self.user = CustomUser.objects.create_user(
            username="oauth_loading@example.com",
            email="oauth_loading@example.com",
            password="testpassword123",
        )
        self.client.login(username="oauth_loading@example.com", password="testpassword123")

    def test_github_button_has_loading_state_handler(self):
        """Test that GitHub connect button has Alpine.js loading state."""
        response = self.client.get(reverse("onboarding:start"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have x-data for Alpine state and loading indicator
        self.assertIn("x-data", content)
        self.assertIn("loading", content.lower())

    def test_jira_button_has_loading_state_handler(self):
        """Test that Jira connect button has Alpine.js loading state."""
        self.team = TeamFactory()
        self.team.members.add(self.user)

        response = self.client.get(reverse("onboarding:connect_jira"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have loading state mechanism
        self.assertIn("x-data", content)

    def test_slack_button_has_loading_state_handler(self):
        """Test that Slack connect button has Alpine.js loading state."""
        self.team = TeamFactory()
        self.team.members.add(self.user)

        response = self.client.get(reverse("onboarding:connect_slack"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have loading state mechanism
        self.assertIn("x-data", content)


class CelebrationAnimationTests(TestCase):
    """Tests for celebration animation on complete page."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="celebrate@example.com",
            email="celebrate@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)
        self.client.login(username="celebrate@example.com", password="testpassword123")

    def test_complete_page_has_celebration_element(self):
        """Test that complete page has celebration visual element."""
        response = self.client.get(reverse("onboarding:complete"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have some celebration indicator (confetti, animation, or celebratory icon)
        # Check for celebration-related content
        self.assertTrue(
            "confetti" in content.lower()
            or "celebrate" in content.lower()
            or "fa-party" in content
            or "fa-sparkles" in content
            or "🎉" in content
        )

    def test_complete_page_shows_personalized_welcome(self):
        """Test that complete page shows personalized welcome message."""
        self.user.first_name = "Jordan"
        self.user.save()

        response = self.client.get(reverse("onboarding:complete"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should show personalized greeting
        self.assertIn("Jordan", content)
