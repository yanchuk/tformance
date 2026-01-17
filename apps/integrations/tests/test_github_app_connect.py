"""Tests for GitHub App connect view for existing teams.

These tests verify the github_app_connect view that allows existing teams
to initiate GitHub App installation flow.
"""

import urllib.parse
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.auth.oauth_state import FLOW_TYPE_GITHUB_APP_TEAM, verify_oauth_state
from apps.integrations.factories import GitHubAppInstallationFactory, GitHubIntegrationFactory
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN
from apps.users.models import CustomUser
from apps.utils.tests.mixins import TeamWithAdminMemberMixin


class GitHubAppConnectViewTests(TeamWithAdminMemberMixin, TestCase):
    """Tests for github_app_connect view.

    This view initiates the GitHub App installation flow for existing teams by:
    1. Verifying user is a team admin
    2. Checking team doesn't already have GitHub App or OAuth connected
    3. Generating OAuth state with team_id
    4. Redirecting to GitHub App installation URL
    """

    def _get_url(self):
        """Get the URL for github_app_connect view."""
        return reverse("integrations:github_app_connect")

    def test_github_app_connect_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(self._get_url())

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response.url)

    def test_github_app_connect_requires_team_admin(self):
        """Test that non-admin members cannot access the view."""
        self.client.force_login(self.member_user)
        response = self.client.get(self._get_url())

        # Should get 404 (forbidden treated as 404 for security)
        self.assertEqual(response.status_code, 404)

    @override_settings(GITHUB_APP_NAME="tformance-dev")
    def test_github_app_connect_redirects_to_github(self):
        """Test that authenticated team admin is redirected to GitHub App installation page."""
        self.client.force_login(self.admin_user)

        response = self.client.get(self._get_url())

        # Should redirect to GitHub
        self.assertEqual(response.status_code, 302)
        self.assertIn("github.com/apps/tformance-dev/installations/new", response.url)

    @override_settings(GITHUB_APP_NAME="tformance-dev")
    def test_github_app_connect_includes_state_with_team_id(self):
        """Test that the redirect URL includes state parameter with team_id."""
        self.client.force_login(self.admin_user)

        response = self.client.get(self._get_url())

        # Extract state from URL
        parsed = urllib.parse.urlparse(response.url)
        query_params = urllib.parse.parse_qs(parsed.query)
        state = query_params.get("state", [None])[0]

        # Verify state contains team_id and correct flow type
        self.assertIsNotNone(state)
        payload = verify_oauth_state(state)
        self.assertEqual(payload.get("team_id"), self.team.id)
        self.assertEqual(payload.get("type"), FLOW_TYPE_GITHUB_APP_TEAM)

    def test_github_app_connect_redirects_if_already_installed(self):
        """Test that teams with existing GitHub App are redirected with info message."""
        # Create existing GitHub App installation
        GitHubAppInstallationFactory(team=self.team, is_active=True)

        self.client.force_login(self.admin_user)
        response = self.client.get(self._get_url())

        # Should redirect to integrations home
        self.assertRedirects(response, reverse("integrations:integrations_home"))

    def test_github_app_connect_redirects_if_oauth_connected(self):
        """Test that teams with existing OAuth integration are redirected with info message."""
        # Create existing OAuth integration
        GitHubIntegrationFactory(team=self.team)

        self.client.force_login(self.admin_user)
        response = self.client.get(self._get_url())

        # Should redirect to integrations home
        self.assertRedirects(response, reverse("integrations:integrations_home"))


class GitHubAppCallbackTeamFlowTests(TestCase):
    """Tests for github_app_callback view with FLOW_TYPE_GITHUB_APP_TEAM.

    This flow is used when an existing team connects GitHub App.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="team_callback@example.com",
            email="team_callback@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory(name="callback-team", slug="callback-team")
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})

    def _get_url(self):
        """Get the URL for github_app_callback view."""
        return reverse("onboarding:github_app_callback")

    def _create_state(self, team_id: int) -> str:
        """Create a valid OAuth state for team flow testing."""
        from apps.auth.oauth_state import create_oauth_state

        return create_oauth_state(FLOW_TYPE_GITHUB_APP_TEAM, team_id=team_id)

    @patch("apps.integrations.services.github_app.get_installation")
    @patch("apps.integrations.tasks.sync_github_app_members_task.delay")
    def test_github_app_callback_team_flow_creates_installation(self, mock_task_delay, mock_get_installation):
        """Test that team flow callback creates GitHubAppInstallation for existing team."""
        mock_get_installation.return_value = {
            "id": 99990001,
            "account": {
                "login": "callback-team-org",
                "id": 11112222,
                "type": "Organization",
            },
            "permissions": {"contents": "read", "pull_requests": "write"},
            "events": ["pull_request", "push"],
            "repository_selection": "selected",
        }

        self.client.login(username="team_callback@example.com", password="testpassword123")
        state = self._create_state(self.team.id)

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "99990001",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should create installation linked to the existing team
        from apps.integrations.models import GitHubAppInstallation

        self.assertTrue(GitHubAppInstallation.objects.filter(installation_id=99990001).exists())
        installation = GitHubAppInstallation.objects.get(installation_id=99990001)
        self.assertEqual(installation.team.id, self.team.id)
        self.assertEqual(installation.account_login, "callback-team-org")

        # Should redirect to repos page (not onboarding)
        self.assertRedirects(response, reverse("integrations:github_repos"), fetch_redirect_response=False)

    @patch("apps.integrations.services.github_app.get_installation")
    @patch("apps.integrations.tasks.sync_github_app_members_task.delay")
    def test_github_app_callback_team_flow_does_not_create_new_team(self, mock_task_delay, mock_get_installation):
        """Test that team flow uses existing team, doesn't create new one."""
        mock_get_installation.return_value = {
            "id": 99990002,
            "account": {
                "login": "different-org-name",  # Different from team name
                "id": 33334444,
                "type": "Organization",
            },
            "permissions": {},
            "events": [],
            "repository_selection": "all",
        }

        from apps.teams.models import Team

        initial_team_count = Team.objects.count()

        self.client.login(username="team_callback@example.com", password="testpassword123")
        state = self._create_state(self.team.id)

        self.client.get(
            self._get_url(),
            {
                "installation_id": "99990002",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should not create any new teams
        self.assertEqual(Team.objects.count(), initial_team_count)

        # Installation should be linked to existing team
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.get(installation_id=99990002)
        self.assertEqual(installation.team.id, self.team.id)

    def test_github_app_callback_team_flow_rejects_invalid_team(self):
        """Test that callback rejects state with non-existent team_id."""
        self.client.login(username="team_callback@example.com", password="testpassword123")

        # Create state with non-existent team_id
        state = self._create_state(99999)

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "99990003",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should redirect to home with error
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)

    def test_github_app_callback_team_flow_rejects_non_member(self):
        """Test that callback rejects if user is not a member of the team."""
        # Create another user who is not a member
        CustomUser.objects.create_user(
            username="nonmember@example.com",
            email="nonmember@example.com",
            password="testpassword123",
        )

        self.client.login(username="nonmember@example.com", password="testpassword123")
        state = self._create_state(self.team.id)

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "99990004",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should redirect to home with error
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)

    @patch("apps.integrations.services.github_app.get_installation")
    def test_github_app_callback_team_flow_rejects_if_already_linked_to_other_team(self, mock_get_installation):
        """Test that callback rejects if installation already belongs to different team."""
        mock_get_installation.return_value = {
            "id": 99990005,
            "account": {
                "login": "other-org",
                "id": 55556666,
                "type": "Organization",
            },
            "permissions": {},
            "events": [],
            "repository_selection": "selected",
        }

        # Create existing installation for a different team
        other_team = TeamFactory(name="other-team")
        GitHubAppInstallationFactory(
            team=other_team,
            installation_id=99990005,
            account_login="other-org",
        )

        self.client.login(username="team_callback@example.com", password="testpassword123")
        state = self._create_state(self.team.id)

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "99990005",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should redirect to integrations home with error
        self.assertRedirects(
            response,
            reverse("integrations:integrations_home"),
            fetch_redirect_response=False,
        )

    @patch("apps.integrations.services.github_app.get_installation")
    @patch("apps.integrations.tasks.sync_github_app_members_task.delay")
    def test_github_app_callback_team_flow_queues_member_sync(self, mock_task_delay, mock_get_installation):
        """Test that team flow callback queues member sync task."""
        mock_get_installation.return_value = {
            "id": 99990006,
            "account": {
                "login": "sync-test-org",
                "id": 77778888,
                "type": "Organization",
            },
            "permissions": {},
            "events": [],
            "repository_selection": "all",
        }

        self.client.login(username="team_callback@example.com", password="testpassword123")
        state = self._create_state(self.team.id)

        self.client.get(
            self._get_url(),
            {
                "installation_id": "99990006",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should queue member sync task
        mock_task_delay.assert_called_once()
