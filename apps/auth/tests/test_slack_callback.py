"""Tests for unified Slack OAuth callback."""

from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.auth.oauth_state import FLOW_TYPE_SLACK_INTEGRATION, FLOW_TYPE_SLACK_ONBOARDING, create_oauth_state
from apps.integrations.factories import UserFactory
from apps.integrations.models import SlackIntegration
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN


class TestSlackCallbackRouting(TestCase):
    """Tests for Slack callback routing based on state type."""

    def setUp(self):
        """Set up test user with a team."""
        self.user = UserFactory()
        self.team = TeamFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:slack_callback")

    def test_missing_state_redirects_with_error(self):
        """Test that missing state parameter shows error."""
        response = self.client.get(self.callback_url)

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid OAuth state" in str(m) for m in messages))

    def test_invalid_state_redirects_with_error(self):
        """Test that invalid state parameter shows error."""
        response = self.client.get(self.callback_url, {"state": "invalid_state"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid OAuth state" in str(m) for m in messages))

    def test_slack_error_shows_message(self):
        """Test that Slack error is displayed to user."""
        state = create_oauth_state(FLOW_TYPE_SLACK_ONBOARDING, team_id=self.team.id)
        response = self.client.get(
            self.callback_url,
            {"state": state, "error": "access_denied", "error_description": "User denied access"},
        )

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("User denied access" in str(m) for m in messages))

    def test_missing_code_shows_error(self):
        """Test that missing code parameter shows error."""
        state = create_oauth_state(FLOW_TYPE_SLACK_ONBOARDING, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No authorization code" in str(m) for m in messages))


class TestSlackOnboardingCallback(TestCase):
    """Tests for Slack onboarding flow through unified callback."""

    def setUp(self):
        """Set up test user with a team."""
        self.user = UserFactory()
        self.team = TeamFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:slack_callback")

    @patch("apps.auth.views.slack_oauth")
    def test_onboarding_creates_integration(self, mock_slack_oauth):
        """Test that Slack onboarding creates integration."""
        # Mock Slack API responses
        mock_slack_oauth.exchange_code_for_token.return_value = {
            "access_token": "xoxb-test-token",
            "bot_user_id": "U12345678",
            "team": {
                "id": "T12345678",
                "name": "Test Workspace",
            },
        }

        state = create_oauth_state(FLOW_TYPE_SLACK_ONBOARDING, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Should redirect to complete
        self.assertEqual(response.status_code, 302)
        self.assertIn("complete", response.url)

        # Integration should be created
        self.assertTrue(SlackIntegration.objects.filter(team=self.team).exists())
        integration = SlackIntegration.objects.get(team=self.team)
        self.assertEqual(integration.workspace_id, "T12345678")
        self.assertEqual(integration.workspace_name, "Test Workspace")
        self.assertEqual(integration.bot_user_id, "U12345678")

    @patch("apps.auth.views.slack_oauth")
    def test_onboarding_without_team_shows_error(self, mock_slack_oauth):
        """Test that user without team is redirected."""
        # Create new user without team
        new_user = UserFactory()
        self.client.force_login(new_user)

        state = create_oauth_state(FLOW_TYPE_SLACK_ONBOARDING)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("complete GitHub setup" in str(m) for m in messages))

    @patch("apps.auth.views.slack_oauth")
    def test_onboarding_token_exchange_error(self, mock_slack_oauth):
        """Test that token exchange error is handled gracefully."""
        from apps.integrations.services.slack_oauth import SlackOAuthError

        mock_slack_oauth.exchange_code_for_token.side_effect = SlackOAuthError("Token exchange failed")

        state = create_oauth_state(FLOW_TYPE_SLACK_ONBOARDING, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Failed to connect" in str(m) for m in messages))

    @patch("apps.auth.views.slack_oauth")
    def test_onboarding_missing_access_token(self, mock_slack_oauth):
        """Test that missing access token shows error."""
        mock_slack_oauth.exchange_code_for_token.return_value = {
            "access_token": None,
            "bot_user_id": "U12345678",
            "team": {"id": "T12345678", "name": "Test"},
        }

        state = create_oauth_state(FLOW_TYPE_SLACK_ONBOARDING, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Failed to get access token" in str(m) for m in messages))


class TestSlackIntegrationCallback(TestCase):
    """Tests for Slack integration flow through unified callback."""

    def setUp(self):
        """Set up test user with a team."""
        self.user = UserFactory()
        self.team = TeamFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:slack_callback")

    @patch("apps.auth.views.slack_oauth")
    def test_integration_creates_slack_integration(self, mock_slack_oauth):
        """Test that integration flow creates Slack integration."""
        mock_slack_oauth.exchange_code_for_token.return_value = {
            "access_token": "xoxb-test-token",
            "bot_user_id": "U87654321",
            "team": {
                "id": "T87654321",
                "name": "My Workspace",
            },
        }

        state = create_oauth_state(FLOW_TYPE_SLACK_INTEGRATION, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Should redirect to Slack settings
        self.assertEqual(response.status_code, 302)
        self.assertIn("slack", response.url)

        # Integration should be created
        self.assertTrue(SlackIntegration.objects.filter(team=self.team).exists())
        integration = SlackIntegration.objects.get(team=self.team)
        self.assertEqual(integration.workspace_id, "T87654321")
        self.assertEqual(integration.workspace_name, "My Workspace")

    def test_integration_with_invalid_team_shows_error(self):
        """Test that invalid team_id shows error."""
        state = create_oauth_state(FLOW_TYPE_SLACK_INTEGRATION, team_id=99999)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Team not found" in str(m) for m in messages))

    def test_integration_without_team_access_shows_error(self):
        """Test that user without team access is rejected."""
        # Create another team that user doesn't belong to
        other_team = TeamFactory()

        state = create_oauth_state(FLOW_TYPE_SLACK_INTEGRATION, team_id=other_team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("don't have access" in str(m) for m in messages))

    @patch("apps.auth.views.slack_oauth")
    def test_integration_token_exchange_error(self, mock_slack_oauth):
        """Test that token exchange error is handled gracefully."""
        from apps.integrations.services.slack_oauth import SlackOAuthError

        mock_slack_oauth.exchange_code_for_token.side_effect = SlackOAuthError("Token exchange failed")

        state = create_oauth_state(FLOW_TYPE_SLACK_INTEGRATION, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Failed to connect" in str(m) for m in messages))


class TestSlackCallbackRequiresLogin(TestCase):
    """Tests that Slack callback requires authentication."""

    def test_unauthenticated_user_redirected_to_login(self):
        """Test that unauthenticated users are redirected to login."""
        callback_url = reverse("tformance_auth:slack_callback")
        response = self.client.get(callback_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
