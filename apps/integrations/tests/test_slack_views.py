"""Tests for Slack OAuth views."""

from datetime import time
from unittest.mock import patch

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
        response = self.client.get(reverse("integrations:slack_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_slack_connect_requires_team_membership(self):
        """Test that slack_connect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:slack_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_slack_connect_requires_admin_role(self):
        """Test that slack_connect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:slack_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    def test_slack_connect_redirects_to_slack_oauth(self):
        """Test that slack_connect redirects to Slack OAuth authorization URL."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://slack.com/oauth/v2/authorize"))

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    def test_slack_connect_redirect_contains_client_id(self):
        """Test that slack_connect redirect URL includes client_id parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("client_id=test_client_id", response.url)

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    def test_slack_connect_redirect_contains_redirect_uri(self):
        """Test that slack_connect redirect URL includes redirect_uri parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("redirect_uri=", response.url)

    def test_slack_connect_when_already_connected_redirects_to_integrations_home(self):
        """Test that slack_connect redirects to integrations_home if Slack is already connected."""
        # Create existing Slack integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

    def test_slack_connect_when_already_connected_shows_message(self):
        """Test that slack_connect shows message if Slack is already connected."""
        # Create existing Slack integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_connect", args=[self.team.slug]), follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("already connected" in str(m).lower() for m in messages))


class SlackCallbackViewTest(TestCase):
    """Tests for slack_callback view."""

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
        response = self.client.get(reverse("integrations:slack_callback", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_slack_callback_requires_team_membership(self):
        """Test that slack_callback returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:slack_callback", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    @patch("apps.integrations.services.slack_oauth.verify_slack_oauth_state")
    def test_slack_callback_verifies_oauth_state(self, mock_verify):
        """Test that slack_callback verifies the OAuth state parameter."""
        mock_verify.return_value = {"team_id": self.team.id}
        self.client.force_login(self.admin)

        self.client.get(
            reverse("integrations:slack_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Verify that the state verification function was called
        mock_verify.assert_called_once_with("valid_state")

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    @patch("apps.integrations.services.slack_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.slack_oauth.verify_slack_oauth_state")
    def test_slack_callback_creates_integration_credential(self, mock_verify, mock_exchange):
        """Test that slack_callback creates IntegrationCredential with provider=slack."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "xoxb-slack-access-token",
            "bot_user_id": "U12345678",
            "team": {
                "id": "T12345678",
                "name": "Test Workspace",
            },
        }

        self.client.force_login(self.admin)

        self.client.get(
            reverse("integrations:slack_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should create IntegrationCredential
        self.assertTrue(
            IntegrationCredential.objects.filter(team=self.team, provider=IntegrationCredential.PROVIDER_SLACK).exists()
        )

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    @patch("apps.integrations.services.slack_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.slack_oauth.verify_slack_oauth_state")
    def test_slack_callback_creates_slack_integration(self, mock_verify, mock_exchange):
        """Test that slack_callback creates SlackIntegration with workspace info."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "xoxb-slack-access-token",
            "bot_user_id": "U12345678",
            "team": {
                "id": "T12345678",
                "name": "Test Workspace",
            },
        }

        self.client.force_login(self.admin)

        self.client.get(
            reverse("integrations:slack_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should create SlackIntegration
        self.assertTrue(
            SlackIntegration.objects.filter(
                team=self.team, workspace_id="T12345678", workspace_name="Test Workspace"
            ).exists()
        )

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    @patch("apps.integrations.services.slack_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.slack_oauth.verify_slack_oauth_state")
    def test_slack_callback_redirects_to_integrations_home_on_success(self, mock_verify, mock_exchange):
        """Test that slack_callback redirects to integrations_home on success."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "xoxb-slack-access-token",
            "bot_user_id": "U12345678",
            "team": {
                "id": "T12345678",
                "name": "Test Workspace",
            },
        }

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:slack_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    @patch("apps.integrations.services.slack_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.slack_oauth.verify_slack_oauth_state")
    def test_slack_callback_handles_invalid_oauth_code(self, mock_verify, mock_exchange):
        """Test that slack_callback handles invalid OAuth code gracefully."""
        from apps.integrations.services.slack_oauth import SlackOAuthError

        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange error
        mock_exchange.side_effect = SlackOAuthError("Invalid code")

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:slack_callback", args=[self.team.slug]),
            {"code": "invalid_code", "state": "valid_state"},
        )

        # Should redirect to integrations home with error
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

        # Should NOT create any integration records
        self.assertFalse(IntegrationCredential.objects.filter(team=self.team).exists())

    @override_settings(SLACK_CLIENT_ID="test_client_id", SLACK_CLIENT_SECRET="test_secret")
    @patch("apps.integrations.services.slack_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.slack_oauth.verify_slack_oauth_state")
    def test_slack_callback_handles_already_connected(self, mock_verify, mock_exchange):
        """Test that slack_callback updates existing integration when already connected."""
        # Create existing integration
        SlackIntegrationFactory(team=self.team, workspace_id="T12345678")

        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange with different workspace name
        mock_exchange.return_value = {
            "access_token": "xoxb-new-token",
            "bot_user_id": "U87654321",
            "team": {
                "id": "T12345678",
                "name": "Updated Workspace Name",
            },
        }

        self.client.force_login(self.admin)

        self.client.get(
            reverse("integrations:slack_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should update existing integration
        integration = SlackIntegration.objects.get(team=self.team, workspace_id="T12345678")
        self.assertEqual(integration.workspace_name, "Updated Workspace Name")

        # Should only have one integration for this team
        self.assertEqual(SlackIntegration.objects.filter(team=self.team).count(), 1)


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
        response = self.client.post(reverse("integrations:slack_disconnect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_slack_disconnect_requires_team_membership(self):
        """Test that slack_disconnect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:slack_disconnect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_slack_disconnect_requires_admin_role(self):
        """Test that slack_disconnect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(reverse("integrations:slack_disconnect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_slack_disconnect_requires_post_method(self):
        """Test that slack_disconnect only accepts POST requests."""
        # Create integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(reverse("integrations:slack_disconnect", args=[self.team.slug]))

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_slack_disconnect_deletes_slack_integration_and_credential(self):
        """Test that slack_disconnect deletes both SlackIntegration and IntegrationCredential."""
        # Create integration
        integration = SlackIntegrationFactory(team=self.team)
        credential = integration.credential
        self.client.force_login(self.admin)

        self.client.post(reverse("integrations:slack_disconnect", args=[self.team.slug]))

        # SlackIntegration should be deleted
        self.assertFalse(SlackIntegration.objects.filter(pk=integration.pk).exists())

        # IntegrationCredential should be deleted
        self.assertFalse(IntegrationCredential.objects.filter(pk=credential.pk).exists())

    def test_slack_disconnect_redirects_to_integrations_home(self):
        """Test that slack_disconnect redirects to integrations_home after success."""
        # Create integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:slack_disconnect", args=[self.team.slug]))

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))


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
        response = self.client.get(reverse("integrations:slack_settings", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_slack_settings_requires_team_membership(self):
        """Test that slack_settings returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:slack_settings", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_slack_settings_requires_admin_role(self):
        """Test that slack_settings returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:slack_settings", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_slack_settings_get_returns_settings_form(self):
        """Test that slack_settings GET returns settings form when Slack is connected."""
        # Create integration
        SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:slack_settings", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "leaderboard")

    def test_slack_settings_post_updates_leaderboard_settings(self):
        """Test that slack_settings POST updates leaderboard channel, day, and time."""
        # Create integration
        integration = SlackIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        self.client.post(
            reverse("integrations:slack_settings", args=[self.team.slug]),
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
