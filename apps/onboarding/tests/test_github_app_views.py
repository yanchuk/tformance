"""Tests for GitHub App onboarding views.

These tests verify the GitHub App installation flow for onboarding:
1. github_app_install - Initiates GitHub App installation
2. github_app_callback - Handles the callback after installation

TDD RED PHASE: These tests are written before the views exist.
They should all FAIL until the views are implemented.
"""

from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.integrations.factories import GitHubAppInstallationFactory
from apps.integrations.models import GitHubAppInstallation
from apps.metrics.factories import TeamFactory
from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN
from apps.users.models import CustomUser


class GitHubAppInstallViewTests(TestCase):
    """Tests for github_app_install view.

    This view initiates the GitHub App installation flow by:
    1. Generating OAuth state with timestamp and user_id
    2. Redirecting to GitHub App installation URL
    """

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="app_install@example.com",
            email="app_install@example.com",
            password="testpassword123",
        )

    def _get_url(self):
        """Get the URL for github_app_install view."""
        return reverse("onboarding:github_app_install")

    def test_github_app_install_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        url = self._get_url()
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response.url)

    @override_settings(GITHUB_APP_NAME="tformance-dev")
    def test_github_app_install_redirects_to_github(self):
        """Test that authenticated users are redirected to GitHub App installation page."""
        self.client.login(username="app_install@example.com", password="testpassword123")

        response = self.client.get(self._get_url())

        # Should redirect to GitHub
        self.assertEqual(response.status_code, 302)
        self.assertIn("github.com/apps/tformance-dev/installations/new", response.url)

    @override_settings(GITHUB_APP_NAME="tformance-dev")
    def test_github_app_install_includes_state(self):
        """Test that the redirect URL includes a state parameter."""
        self.client.login(username="app_install@example.com", password="testpassword123")

        response = self.client.get(self._get_url())

        # Should include state parameter for CSRF protection
        self.assertIn("state=", response.url)

    @override_settings(GITHUB_APP_NAME="tformance-dev")
    def test_github_app_install_state_includes_user_id(self):
        """Test that the state parameter includes the user_id for callback validation."""
        import urllib.parse

        from apps.auth.oauth_state import verify_oauth_state

        self.client.login(username="app_install@example.com", password="testpassword123")

        response = self.client.get(self._get_url())

        # Extract state from URL
        parsed = urllib.parse.urlparse(response.url)
        query_params = urllib.parse.parse_qs(parsed.query)
        state = query_params.get("state", [None])[0]

        # Verify state contains user_id
        self.assertIsNotNone(state)
        payload = verify_oauth_state(state)
        self.assertEqual(payload.get("user_id"), self.user.id)

    def test_github_app_install_redirects_to_home_if_has_team(self):
        """Test that users with existing teams are redirected to home."""
        self.client.login(username="app_install@example.com", password="testpassword123")

        # Create a team for the user
        team = TeamFactory()
        team.members.add(self.user)

        response = self.client.get(self._get_url())

        # Should redirect to home
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)


class GitHubAppCallbackViewTests(TestCase):
    """Tests for github_app_callback view.

    This view handles the callback from GitHub after App installation:
    1. Validates the state parameter
    2. Fetches installation details from GitHub
    3. Creates GitHubAppInstallation record
    4. Links to existing team or creates new team
    5. Syncs organization members
    6. Redirects to repository selection
    """

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="app_callback@example.com",
            email="app_callback@example.com",
            password="testpassword123",
        )

    def _get_url(self):
        """Get the URL for github_app_callback view."""
        return reverse("onboarding:github_app_callback")

    def _create_state(self, user_id: int) -> str:
        """Create a valid OAuth state for testing.

        Note: This requires the github_app_install flow type to be added
        to the oauth_state module.
        """
        from apps.auth.oauth_state import create_oauth_state

        return create_oauth_state("github_app_install", user_id=user_id)

    def test_github_app_callback_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(
            self._get_url(),
            {"installation_id": "12345", "setup_action": "install"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response.url)

    def test_github_app_callback_requires_installation_id(self):
        """Test that callback requires installation_id parameter."""
        self.client.login(username="app_callback@example.com", password="testpassword123")

        response = self.client.get(
            self._get_url(),
            {"setup_action": "install"},  # Missing installation_id
        )

        # Should redirect to start with error
        self.assertRedirects(response, reverse("onboarding:start"))

    @patch("apps.integrations.services.github_app.get_installation")
    def test_github_app_callback_creates_installation(self, mock_get_installation):
        """Test that callback creates GitHubAppInstallation record."""
        mock_get_installation.return_value = {
            "id": 12345678,
            "account": {
                "login": "test-org",
                "id": 98765432,
                "type": "Organization",
            },
            "permissions": {"contents": "read", "pull_requests": "write"},
            "events": ["pull_request", "push"],
            "repository_selection": "selected",
        }

        self.client.login(username="app_callback@example.com", password="testpassword123")

        # Create valid state
        state = self._create_state(self.user.id)

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "12345678",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should redirect after successful installation
        self.assertEqual(response.status_code, 302)

        # Should create installation
        self.assertTrue(GitHubAppInstallation.objects.filter(installation_id=12345678).exists())

        installation = GitHubAppInstallation.objects.get(installation_id=12345678)
        self.assertEqual(installation.account_login, "test-org")
        self.assertEqual(installation.account_id, 98765432)
        self.assertEqual(installation.account_type, "Organization")

    @patch("apps.integrations.services.github_app.get_installation")
    def test_github_app_callback_creates_team_from_org(self, mock_get_installation):
        """Test that callback creates a team from the organization name."""
        mock_get_installation.return_value = {
            "id": 22222222,
            "account": {
                "login": "awesome-org",
                "id": 11111111,
                "type": "Organization",
            },
            "permissions": {"contents": "read"},
            "events": ["pull_request"],
            "repository_selection": "all",
        }

        self.client.login(username="app_callback@example.com", password="testpassword123")
        state = self._create_state(self.user.id)

        self.client.get(
            self._get_url(),
            {
                "installation_id": "22222222",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should create team
        self.assertTrue(Team.objects.filter(name="awesome-org").exists())
        team = Team.objects.get(name="awesome-org")

        # User should be admin of the team
        membership = Membership.objects.get(team=team, user=self.user)
        self.assertEqual(membership.role, ROLE_ADMIN)

    @patch("apps.integrations.services.github_app.get_installation")
    def test_github_app_callback_links_installation_to_team(self, mock_get_installation):
        """Test that callback links the installation to the created team."""
        mock_get_installation.return_value = {
            "id": 33333333,
            "account": {
                "login": "linked-org",
                "id": 44444444,
                "type": "Organization",
            },
            "permissions": {},
            "events": [],
            "repository_selection": "selected",
        }

        self.client.login(username="app_callback@example.com", password="testpassword123")
        state = self._create_state(self.user.id)

        self.client.get(
            self._get_url(),
            {
                "installation_id": "33333333",
                "setup_action": "install",
                "state": state,
            },
        )

        # Installation should be linked to team
        installation = GitHubAppInstallation.objects.get(installation_id=33333333)
        self.assertIsNotNone(installation.team)
        self.assertEqual(installation.team.name, "linked-org")

    @patch("apps.integrations.services.github_app.get_installation")
    def test_github_app_callback_links_to_existing_team(self, mock_get_installation):
        """Test that callback links to existing team if org matches."""
        # Create existing team with matching name
        existing_team = TeamFactory(name="existing-org", slug="existing-org")
        existing_team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})

        mock_get_installation.return_value = {
            "id": 55555555,
            "account": {
                "login": "existing-org",
                "id": 66666666,
                "type": "Organization",
            },
            "permissions": {},
            "events": [],
            "repository_selection": "selected",
        }

        self.client.login(username="app_callback@example.com", password="testpassword123")
        state = self._create_state(self.user.id)

        self.client.get(
            self._get_url(),
            {
                "installation_id": "55555555",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should link to existing team, not create new one
        installation = GitHubAppInstallation.objects.get(installation_id=55555555)
        self.assertEqual(installation.team.id, existing_team.id)
        # Verify no duplicate team was created
        self.assertEqual(Team.objects.filter(name="existing-org").count(), 1)

    @patch("apps.integrations.services.github_app.get_installation")
    def test_github_app_callback_invalid_installation_id(self, mock_get_installation):
        """Test that callback handles invalid installation_id gracefully."""
        from apps.integrations.services.github_app import GitHubAppError

        mock_get_installation.side_effect = GitHubAppError("Installation not found")

        self.client.login(username="app_callback@example.com", password="testpassword123")
        state = self._create_state(self.user.id)

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "99999999",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should redirect to start with error message
        self.assertRedirects(response, reverse("onboarding:start"))
        # Should not create installation
        self.assertFalse(GitHubAppInstallation.objects.filter(installation_id=99999999).exists())

    @patch("apps.integrations.services.github_app.get_installation")
    def test_github_app_callback_redirects_to_repos(self, mock_get_installation):
        """Test that successful callback redirects to repository selection."""
        mock_get_installation.return_value = {
            "id": 77777777,
            "account": {
                "login": "redirect-org",
                "id": 88888888,
                "type": "Organization",
            },
            "permissions": {},
            "events": [],
            "repository_selection": "selected",
        }

        self.client.login(username="app_callback@example.com", password="testpassword123")
        state = self._create_state(self.user.id)

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "77777777",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should redirect to select_repos
        self.assertRedirects(response, reverse("onboarding:select_repos"))

    @patch("apps.integrations.services.github_app.get_installation")
    @patch("apps.integrations.tasks.sync_github_app_members_task.delay")
    def test_github_app_callback_queues_member_sync_task(self, mock_task_delay, mock_get_installation):
        """Test that callback queues sync_github_app_members_task for async member sync (A-007)."""
        mock_get_installation.return_value = {
            "id": 11112222,
            "account": {
                "login": "sync-org",
                "id": 33334444,
                "type": "Organization",
            },
            "permissions": {},
            "events": [],
            "repository_selection": "selected",
        }

        self.client.login(username="app_callback@example.com", password="testpassword123")
        state = self._create_state(self.user.id)

        self.client.get(
            self._get_url(),
            {
                "installation_id": "11112222",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should queue async member sync task for GitHub App installation
        mock_task_delay.assert_called_once()
        # The task should receive the installation ID (not GitHubIntegration ID)
        from apps.integrations.models import GitHubAppInstallation

        team = Team.objects.get(name="sync-org")
        installation = GitHubAppInstallation.objects.get(team=team)
        mock_task_delay.assert_called_with(installation.id)

    def test_github_app_callback_invalid_state(self):
        """Test that callback rejects invalid state parameter."""
        self.client.login(username="app_callback@example.com", password="testpassword123")

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "12345678",
                "setup_action": "install",
                "state": "invalid_state_value",
            },
        )

        # Should redirect to start with error
        self.assertRedirects(response, reverse("onboarding:start"))

    def test_github_app_callback_state_user_mismatch(self):
        """Test that callback rejects state with different user_id."""
        # Create another user
        other_user = CustomUser.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpassword123",
        )

        # Create state for other user
        state = self._create_state(other_user.id)

        self.client.login(username="app_callback@example.com", password="testpassword123")

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "12345678",
                "setup_action": "install",
                "state": state,
            },
        )

        # Should redirect to start with error
        self.assertRedirects(response, reverse("onboarding:start"))


class GitHubAppCallbackSetupActionTests(TestCase):
    """Tests for different setup_action values in github_app_callback."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="setup_action@example.com",
            email="setup_action@example.com",
            password="testpassword123",
        )

    def _get_url(self):
        """Get the URL for github_app_callback view."""
        return reverse("onboarding:github_app_callback")

    def _create_state(self, user_id: int) -> str:
        """Create a valid OAuth state for testing."""
        from apps.auth.oauth_state import create_oauth_state

        return create_oauth_state("github_app_install", user_id=user_id)

    @patch("apps.integrations.services.github_app.get_installation")
    def test_github_app_callback_handles_update_action(self, mock_get_installation):
        """Test that callback handles setup_action=update for reinstalls."""
        # Create existing installation
        team = TeamFactory(name="update-org")
        team.members.add(self.user)
        existing_installation = GitHubAppInstallationFactory(
            team=team,
            installation_id=44445555,
            account_login="update-org",
        )

        mock_get_installation.return_value = {
            "id": 44445555,
            "account": {
                "login": "update-org",
                "id": 66667777,
                "type": "Organization",
            },
            "permissions": {"contents": "write"},  # Updated permissions
            "events": ["push"],
            "repository_selection": "all",
        }

        self.client.login(username="setup_action@example.com", password="testpassword123")
        state = self._create_state(self.user.id)

        response = self.client.get(
            self._get_url(),
            {
                "installation_id": "44445555",
                "setup_action": "update",
                "state": state,
            },
        )

        # Should update existing installation
        existing_installation.refresh_from_db()
        self.assertEqual(existing_installation.permissions, {"contents": "write"})
        self.assertEqual(existing_installation.repository_selection, "all")

        # Should redirect to repos
        self.assertRedirects(response, reverse("onboarding:select_repos"))
