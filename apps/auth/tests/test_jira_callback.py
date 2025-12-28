"""Tests for unified Jira OAuth callback."""

from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.auth.oauth_state import FLOW_TYPE_JIRA_INTEGRATION, FLOW_TYPE_JIRA_ONBOARDING, create_oauth_state
from apps.integrations.factories import UserFactory
from apps.integrations.models import JiraIntegration
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN


class TestJiraCallbackRouting(TestCase):
    """Tests for Jira callback routing based on state type."""

    def setUp(self):
        """Set up test user with a team."""
        self.user = UserFactory()
        self.team = TeamFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:jira_callback")

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

    def test_jira_error_shows_message(self):
        """Test that Jira error is displayed to user."""
        state = create_oauth_state(FLOW_TYPE_JIRA_ONBOARDING, team_id=self.team.id)
        response = self.client.get(
            self.callback_url,
            {"state": state, "error": "access_denied", "error_description": "User denied access"},
        )

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("User denied access" in str(m) for m in messages))

    def test_missing_code_shows_error(self):
        """Test that missing code parameter shows error."""
        state = create_oauth_state(FLOW_TYPE_JIRA_ONBOARDING, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No authorization code" in str(m) for m in messages))


class TestJiraOnboardingCallback(TestCase):
    """Tests for Jira onboarding flow through unified callback."""

    def setUp(self):
        """Set up test user with a team."""
        self.user = UserFactory()
        self.team = TeamFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:jira_callback")

    @patch("apps.auth.views.jira_oauth")
    def test_onboarding_creates_integration(self, mock_jira_oauth):
        """Test that Jira onboarding creates integration."""
        # Mock Jira API responses
        mock_jira_oauth.exchange_code_for_token.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
        }
        mock_jira_oauth.get_accessible_resources.return_value = [
            {"id": "cloud-123", "name": "Test Site", "url": "https://test.atlassian.net"}
        ]

        state = create_oauth_state(FLOW_TYPE_JIRA_ONBOARDING, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Should redirect to project selection
        self.assertEqual(response.status_code, 302)
        self.assertIn("jira/projects", response.url)

        # Integration should be created
        self.assertTrue(JiraIntegration.objects.filter(team=self.team).exists())

    @patch("apps.auth.views.jira_oauth")
    def test_onboarding_with_no_sites_shows_error(self, mock_jira_oauth):
        """Test that no Jira sites returns error message."""
        mock_jira_oauth.exchange_code_for_token.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
        }
        mock_jira_oauth.get_accessible_resources.return_value = []

        state = create_oauth_state(FLOW_TYPE_JIRA_ONBOARDING, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No Jira sites found" in str(m) for m in messages))

    @patch("apps.auth.views.jira_oauth")
    def test_onboarding_token_exchange_error(self, mock_jira_oauth):
        """Test that token exchange error is handled gracefully."""
        from apps.integrations.services.jira_oauth import JiraOAuthError

        mock_jira_oauth.exchange_code_for_token.side_effect = JiraOAuthError("Token exchange failed")

        state = create_oauth_state(FLOW_TYPE_JIRA_ONBOARDING, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Failed to connect" in str(m) for m in messages))


class TestJiraIntegrationCallback(TestCase):
    """Tests for Jira integration flow through unified callback."""

    def setUp(self):
        """Set up test user with a team."""
        self.user = UserFactory()
        self.team = TeamFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:jira_callback")

    @patch("apps.auth.views.jira_oauth")
    def test_integration_creates_jira_integration(self, mock_jira_oauth):
        """Test that integration flow creates Jira integration."""
        mock_jira_oauth.exchange_code_for_token.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
        }
        mock_jira_oauth.get_accessible_resources.return_value = [
            {"id": "cloud-456", "name": "My Site", "url": "https://mysite.atlassian.net"}
        ]

        state = create_oauth_state(FLOW_TYPE_JIRA_INTEGRATION, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertIn("integrations", response.url)

        # Integration should be created
        self.assertTrue(JiraIntegration.objects.filter(team=self.team).exists())

    def test_integration_with_invalid_team_shows_error(self):
        """Test that invalid team_id shows error."""
        state = create_oauth_state(FLOW_TYPE_JIRA_INTEGRATION, team_id=99999)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Team not found" in str(m) for m in messages))

    def test_integration_without_team_access_shows_error(self):
        """Test that user without team access is rejected."""
        # Create another team that user doesn't belong to
        other_team = TeamFactory()

        state = create_oauth_state(FLOW_TYPE_JIRA_INTEGRATION, team_id=other_team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("don't have access" in str(m) for m in messages))


class TestJiraCallbackRequiresLogin(TestCase):
    """Tests that Jira callback requires authentication."""

    def test_unauthenticated_user_redirected_to_login(self):
        """Test that unauthenticated users are redirected to login."""
        callback_url = reverse("tformance_auth:jira_callback")
        response = self.client.get(callback_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
