"""Tests for Slack OAuth views."""

from datetime import time

from django.contrib.messages import get_messages
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.integrations.factories import (
    SlackIntegrationFactory,
    UserFactory,
)
from apps.integrations.models import IntegrationCredential, SlackIntegration
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class SlackConnectViewTest(TestCase):
    """Tests for slack_connect view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_slack_connect_requires_login(self):
        """Test that slack_connect redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:slack_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_slack_connect_requires_team_membership(self):
        """Test that slack_connect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:slack_connect"))

        self.assertEqual(response.status_code, 404)

    def test_slack_connect_requires_admin_role(self):
        """Test that slack_connect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:slack_connect"))

        self.assertEqual(response.status_code, 404)

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    def test_slack_connect_redirects_to_slack_oauth(self):
        """Test that slack_connect redirects to Slack OAuth authorization URL."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://slack.com/oauth/v2/authorize"))

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    def test_slack_connect_redirect_contains_client_id(self):
        """Test that slack_connect redirect URL includes client_id parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("client_id=test_client_id", response.url)

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    def test_slack_connect_redirect_contains_redirect_uri(self):
        """Test that slack_connect redirect URL includes redirect_uri parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("redirect_uri=", response.url)

    def test_slack_connect_when_already_connected_redirects_to_integrations_home(self):
        """Test that slack_connect redirects to integrations_home if Slack is already connected."""
        # Create existing Slack integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_slack_connect_when_already_connected_shows_message(self):
        """Test that slack_connect shows message if Slack is already connected."""
        # Create existing Slack integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect"), follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("already connected" in str(m).lower() for m in messages))


class SlackCallbackViewTest(TestCase):
    """Tests for slack_callback view (legacy redirect to unified callback).

    Note: This view now redirects to the unified callback at tformance_auth:slack_callback.
    The actual OAuth flow tests are in apps/auth/tests/test_slack_callback.py.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_slack_callback_requires_login(self):
        """Test that slack_callback redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:slack_callback"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_slack_callback_requires_team_membership(self):
        """Test that slack_callback returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:slack_callback"))

        self.assertEqual(response.status_code, 404)

    def test_slack_callback_redirects_to_unified_callback(self):
        """Test that slack_callback redirects to the unified auth callback."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_callback"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/slack/callback/", response.url)

    def test_slack_callback_preserves_query_params(self):
        """Test that slack_callback preserves OAuth query parameters in redirect."""
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:slack_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("code=auth_code_123", response.url)
        self.assertIn("state=valid_state", response.url)

    def test_slack_callback_preserves_error_params(self):
        """Test that slack_callback preserves error parameters in redirect."""
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:slack_callback"),
            {"error": "access_denied", "error_description": "User denied"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("error=access_denied", response.url)


class SlackDisconnectViewTest(TestCase):
    """Tests for slack_disconnect view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_slack_disconnect_requires_login(self):
        """Test that slack_disconnect redirects to login if user is not authenticated."""
        response = self.client.post(reverse("integrations:slack_disconnect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_slack_disconnect_requires_team_membership(self):
        """Test that slack_disconnect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:slack_disconnect"))

        self.assertEqual(response.status_code, 404)

    def test_slack_disconnect_requires_admin_role(self):
        """Test that slack_disconnect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(reverse("integrations:slack_disconnect"))

        self.assertEqual(response.status_code, 404)

    def test_slack_disconnect_requires_post_method(self):
        """Test that slack_disconnect only accepts POST requests."""
        # Create integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(reverse("integrations:slack_disconnect"))

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_slack_disconnect_deletes_slack_integration_and_credential(self):
        """Test that slack_disconnect deletes both SlackIntegration and IntegrationCredential."""
        # Create integration
        integration = SlackIntegrationFactory(team=self.team)
        credential = integration.credential
        self.client.force_login(self.admin)

        self.client.post(reverse("integrations:slack_disconnect"))

        # SlackIntegration should be deleted
        self.assertFalse(SlackIntegration.objects.filter(pk=integration.pk).exists())

        # IntegrationCredential should be deleted
        self.assertFalse(IntegrationCredential.objects.filter(pk=credential.pk).exists())

    def test_slack_disconnect_redirects_to_integrations_home(self):
        """Test that slack_disconnect redirects to integrations_home after success."""
        # Create integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:slack_disconnect"))

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))


class SlackSettingsViewTest(TestCase):
    """Tests for slack_settings view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_slack_settings_requires_login(self):
        """Test that slack_settings redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:slack_settings"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_slack_settings_requires_team_membership(self):
        """Test that slack_settings returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:slack_settings"))

        self.assertEqual(response.status_code, 404)

    def test_slack_settings_requires_admin_role(self):
        """Test that slack_settings returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:slack_settings"))

        self.assertEqual(response.status_code, 404)

    def test_slack_settings_get_returns_settings_form(self):
        """Test that slack_settings GET returns settings form when Slack is connected."""
        # Create integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "leaderboard")

    def test_slack_settings_post_updates_leaderboard_settings(self):
        """Test that slack_settings POST updates leaderboard channel, day, and time."""
        # Create integration
        integration = SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        self.client.post(
            reverse("integrations:slack_settings"),
            {
                "leaderboard_channel_id": "C12345678",
                "leaderboard_day": 4,  # Friday
                "leaderboard_time": "14:30",
                "leaderboard_enabled": True,
            },
        )

        # Refresh integration from database
        integration.refresh_from_db()

        # Should update settings
        self.assertEqual(integration.leaderboard_channel_id, "C12345678")
        self.assertEqual(integration.leaderboard_day, 4)
        self.assertEqual(integration.leaderboard_time, time(14, 30))
        self.assertTrue(integration.leaderboard_enabled)
