"""Tests for unified GitHub OAuth callback."""

from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.auth.oauth_state import FLOW_TYPE_INTEGRATION, FLOW_TYPE_ONBOARDING, create_oauth_state
from apps.integrations.factories import UserFactory
from apps.integrations.models import GitHubIntegration
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN


class TestGitHubCallbackRouting(TestCase):
    """Tests for callback routing based on state type."""

    def setUp(self):
        """Set up test user."""
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:github_callback")

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

    def test_github_error_shows_message(self):
        """Test that GitHub error is displayed to user."""
        state = create_oauth_state(FLOW_TYPE_ONBOARDING)
        response = self.client.get(
            self.callback_url,
            {"state": state, "error": "access_denied", "error_description": "User denied access"},
        )

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("User denied access" in str(m) for m in messages))

    def test_missing_code_shows_error(self):
        """Test that missing code parameter shows error."""
        state = create_oauth_state(FLOW_TYPE_ONBOARDING)
        response = self.client.get(self.callback_url, {"state": state})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No authorization code" in str(m) for m in messages))


class TestOnboardingCallback(TestCase):
    """Tests for onboarding flow through unified callback."""

    def setUp(self):
        """Set up test user without a team."""
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:github_callback")

    @patch("apps.auth.views.github_oauth")
    def test_onboarding_with_single_org_creates_team(self, mock_github_oauth):
        """Test that onboarding with single org creates team automatically."""
        # Mock GitHub API responses
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "test-org", "id": 12345, "description": "Test Org", "avatar_url": ""}
        ]

        state = create_oauth_state(FLOW_TYPE_ONBOARDING)

        with patch("apps.auth.views.member_sync.sync_github_members"):
            response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Should redirect to repo selection
        self.assertEqual(response.status_code, 302)
        self.assertIn("repos", response.url)

        # Team should be created
        from apps.teams.models import Team

        self.assertTrue(Team.objects.filter(name="test-org").exists())
        team = Team.objects.get(name="test-org")

        # User should be member
        self.assertTrue(team.members.filter(id=self.user.id).exists())

        # GitHub integration should be created
        self.assertTrue(GitHubIntegration.objects.filter(team=team).exists())

    @patch("apps.auth.views.github_oauth")
    def test_onboarding_with_multiple_orgs_redirects_to_selection(self, mock_github_oauth):
        """Test that onboarding with multiple orgs redirects to org selection."""
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "org-1", "id": 1, "description": "", "avatar_url": ""},
            {"login": "org-2", "id": 2, "description": "", "avatar_url": ""},
        ]

        state = create_oauth_state(FLOW_TYPE_ONBOARDING)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Should redirect to org selection
        self.assertEqual(response.status_code, 302)
        self.assertIn("org", response.url)

    @patch("apps.auth.views.github_oauth")
    def test_onboarding_with_no_orgs_shows_error(self, mock_github_oauth):
        """Test that no orgs returns error message."""
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = []

        state = create_oauth_state(FLOW_TYPE_ONBOARDING)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No GitHub organizations found" in str(m) for m in messages))

    def test_onboarding_with_existing_team_redirects_home(self):
        """Test that user with existing team is redirected to home."""
        # Create a team for user
        team = TeamFactory()
        team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})

        state = create_oauth_state(FLOW_TYPE_ONBOARDING)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Should redirect to home, not create another team
        self.assertEqual(response.status_code, 302)


class TestIntegrationCallback(TestCase):
    """Tests for integration flow through unified callback."""

    def setUp(self):
        """Set up test user with a team."""
        self.user = UserFactory()
        self.team = TeamFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:github_callback")

    @patch("apps.auth.views.github_oauth")
    @patch("apps.auth.views.member_sync")
    def test_integration_with_single_org_creates_integration(self, mock_member_sync, mock_github_oauth):
        """Test that integration flow creates GitHub integration."""
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "my-org", "id": 999, "description": "", "avatar_url": ""}
        ]
        mock_member_sync.sync_github_members.return_value = {"created": 5, "updated": 0}

        state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertIn("integrations", response.url)

        # Integration should be created
        self.assertTrue(GitHubIntegration.objects.filter(team=self.team).exists())
        integration = GitHubIntegration.objects.get(team=self.team)
        self.assertEqual(integration.organization_slug, "my-org")

    @patch("apps.auth.views.github_oauth")
    def test_integration_with_multiple_orgs_redirects_to_selection(self, mock_github_oauth):
        """Test that multiple orgs redirects to org selection."""
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "org-a", "id": 1, "description": "", "avatar_url": ""},
            {"login": "org-b", "id": 2, "description": "", "avatar_url": ""},
        ]

        state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=self.team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Should redirect to org selection
        self.assertEqual(response.status_code, 302)
        self.assertIn("select-org", response.url)

    def test_integration_with_invalid_team_shows_error(self):
        """Test that invalid team_id shows error."""
        state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=99999)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Team not found" in str(m) for m in messages))

    def test_integration_without_team_access_shows_error(self):
        """Test that user without team access is rejected."""
        # Create another team that user doesn't belong to
        other_team = TeamFactory()

        state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=other_team.id)
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("don't have access" in str(m) for m in messages))


class TestCallbackWithoutState(TestCase):
    """Tests callback behavior when state is missing or invalid."""

    def test_unauthenticated_user_without_state_redirects_to_home(self):
        """Test that unauthenticated users without state are redirected to home.

        Note: The callback no longer uses @login_required to allow login flow
        to work for unauthenticated users. When state is missing/invalid, we
        redirect to home since we don't know the intended flow type.
        """
        callback_url = reverse("tformance_auth:github_callback")
        response = self.client.get(callback_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
