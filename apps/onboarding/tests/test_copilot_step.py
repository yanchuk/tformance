"""Tests for Copilot onboarding step.

TDD RED Phase: These tests define the expected behavior of the
connect_copilot view before implementation.

Uses waffle's override_flag for thread-safe flag testing in parallel execution.
"""

from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory
from apps.teams.models import Flag, Membership
from apps.teams.roles import ROLE_ADMIN


class TestCopilotStepSkip(TestCase):
    """Tests for skipping Copilot step when flag is off."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(onboarding_complete=False)
        self.user = UserFactory()
        Membership.objects.create(team=self.team, user=self.user, role=ROLE_ADMIN)
        self.client = Client()
        self.client.force_login(self.user)

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_copilot_enabled")
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

    def test_connect_copilot_redirects_to_complete_when_disabled(self):
        """Test that connect_copilot redirects to complete when flag is off."""
        with (
            override_flag("integration_copilot_enabled", active=False),
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
        ):
            response = self.client.get(reverse("onboarding:connect_copilot"))

            # Should redirect to complete step
            self.assertRedirects(
                response,
                reverse("onboarding:complete"),
                fetch_redirect_response=False,
            )

    def test_connect_copilot_shows_page_when_flag_enabled(self):
        """Test that connect_copilot shows the page normally when flag is on."""
        with (
            override_flag("integration_copilot_enabled", active=True),
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
        ):
            response = self.client.get(reverse("onboarding:connect_copilot"))

            # Should show the page, not redirect
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "onboarding/copilot.html")


class TestCopilotStepConnect(TestCase):
    """Tests for Copilot connection action."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(onboarding_complete=False, copilot_status="disabled")
        self.user = UserFactory()
        Membership.objects.create(team=self.team, user=self.user, role=ROLE_ADMIN)
        self.client = Client()
        self.client.force_login(self.user)

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_copilot_enabled")
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

    def test_post_connect_activates_copilot_and_redirects(self):
        """Test that POST with action=connect activates Copilot and redirects to complete."""
        with (
            override_flag("integration_copilot_enabled", active=True),
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
            patch("apps.onboarding.views.copilot.activate_copilot_for_team") as mock_activate,
        ):
            mock_activate.return_value = {"status": "activated", "team_id": self.team.id}

            response = self.client.post(
                reverse("onboarding:connect_copilot"),
                {"action": "connect"},
            )

            # Should call activation service
            mock_activate.assert_called_once()

            # Should redirect to complete
            self.assertRedirects(
                response,
                reverse("onboarding:complete"),
                fetch_redirect_response=False,
            )

    def test_post_skip_redirects_without_activating(self):
        """Test that POST with action=skip redirects without activating Copilot."""
        with (
            override_flag("integration_copilot_enabled", active=True),
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
            patch("apps.onboarding.views.copilot.activate_copilot_for_team") as mock_activate,
        ):
            response = self.client.post(
                reverse("onboarding:connect_copilot"),
                {"action": "skip"},
            )

            # Should NOT call activation service
            mock_activate.assert_not_called()

            # Should redirect to complete
            self.assertRedirects(
                response,
                reverse("onboarding:complete"),
                fetch_redirect_response=False,
            )

    def test_post_skip_tracks_event(self):
        """Test that skipping Copilot tracks an analytics event."""
        with (
            override_flag("integration_copilot_enabled", active=True),
            override_flag("integration_jira_enabled", active=False),
            override_flag("integration_slack_enabled", active=False),
            patch("apps.onboarding.views.copilot.track_event") as mock_track,
        ):
            self.client.post(
                reverse("onboarding:connect_copilot"),
                {"action": "skip"},
            )

            # Should track onboarding_skipped event
            mock_track.assert_called_once()
            call_args = mock_track.call_args
            self.assertEqual(call_args[0][1], "onboarding_skipped")
            self.assertEqual(call_args[0][2]["step"], "copilot")


class TestCopilotStepContext(TestCase):
    """Tests for Copilot step template context."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(onboarding_complete=False, copilot_status="disabled")
        self.user = UserFactory()
        Membership.objects.create(team=self.team, user=self.user, role=ROLE_ADMIN)
        self.client = Client()
        self.client.force_login(self.user)

        # Ensure flags exist
        Flag.objects.get_or_create(name="integration_copilot_enabled")
        Flag.objects.get_or_create(name="integration_jira_enabled")
        Flag.objects.get_or_create(name="integration_slack_enabled")

    def test_context_includes_team(self):
        """Test that template context includes team."""
        with override_flag("integration_copilot_enabled", active=True):
            response = self.client.get(reverse("onboarding:connect_copilot"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["team"], self.team)

    def test_context_includes_copilot_enabled_flag(self):
        """Test that template context includes copilot_enabled flag."""
        with override_flag("integration_copilot_enabled", active=True):
            response = self.client.get(reverse("onboarding:connect_copilot"))

            self.assertEqual(response.status_code, 200)
            self.assertIn("copilot_enabled", response.context)
            self.assertTrue(response.context["copilot_enabled"])

    def test_context_includes_page_title(self):
        """Test that template context includes page_title."""
        with override_flag("integration_copilot_enabled", active=True):
            response = self.client.get(reverse("onboarding:connect_copilot"))

            self.assertEqual(response.status_code, 200)
            self.assertIn("page_title", response.context)


class TestCopilotStepNoTeam(TestCase):
    """Tests for Copilot step when user has no team."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = UserFactory()
        self.client = Client()
        self.client.force_login(self.user)

        # Ensure flag exists
        Flag.objects.get_or_create(name="integration_copilot_enabled")

    def test_redirects_to_start_when_no_team(self):
        """Test that user with no team is redirected to onboarding start."""
        with override_flag("integration_copilot_enabled", active=True):
            response = self.client.get(reverse("onboarding:connect_copilot"))

            self.assertRedirects(
                response,
                reverse("onboarding:start"),
                fetch_redirect_response=False,
            )


class TestCopilotStepAuth(TestCase):
    """Tests for Copilot step authentication."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()

    def test_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse("onboarding:connect_copilot"))

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
