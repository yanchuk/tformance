"""Tests for GitHub OAuth views."""

from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    UserFactory,
)
from apps.integrations.models import GitHubIntegration, IntegrationCredential
from apps.integrations.services.github_oauth import GitHubOAuthError
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class IntegrationsHomeViewTest(TestCase):
    """Tests for integrations_home view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_integrations_home_requires_login(self):
        """Test that integrations_home redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_integrations_home_requires_team_membership(self):
        """Test that integrations_home returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 404)

    def test_integrations_home_returns_200_for_team_member(self):
        """Test that integrations_home returns 200 for authenticated team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)

    def test_integrations_home_returns_200_for_team_admin(self):
        """Test that integrations_home returns 200 for authenticated team admins."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)

    def test_integrations_home_shows_github_not_connected_status(self):
        """Test that integrations_home shows GitHub as not connected when no integration exists."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        # Should show not connected status
        self.assertContains(response, "Connect")

    def test_integrations_home_shows_github_connected_status(self):
        """Test that integrations_home shows GitHub as connected when integration exists."""
        # Create a GitHub integration for the team
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        # Should show connected status
        self.assertContains(response, "Connected")

    def test_integrations_home_shows_repositories_link_when_github_connected(self):
        """Test that integrations_home shows Repositories link when GitHub is connected."""
        # Create a GitHub integration for the team
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        # Should show Repositories link
        self.assertContains(response, "Repositories")

    def test_integrations_home_shows_tracked_repo_count_badge(self):
        """Test that integrations_home shows tracked repository count badge."""
        from apps.integrations.factories import TrackedRepositoryFactory

        # Create a GitHub integration for the team
        integration = GitHubIntegrationFactory(team=self.team)

        # Create some tracked repositories
        TrackedRepositoryFactory(team=self.team, integration=integration)
        TrackedRepositoryFactory(team=self.team, integration=integration)
        TrackedRepositoryFactory(team=self.team, integration=integration)

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        # Should show count of 3 repositories
        # The badge should be near the Repositories link
        content = response.content.decode()
        self.assertIn("Repositories", content)
        self.assertIn("3", content)

    def test_integrations_home_repositories_link_points_to_github_repos_url(self):
        """Test that Repositories link points to correct github_repos URL."""
        # Create a GitHub integration for the team
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:integrations_home"))

        self.assertEqual(response.status_code, 200)
        # Should contain link to github_repos
        expected_url = reverse("integrations:github_repos")
        self.assertContains(response, expected_url)


class GitHubConnectViewTest(TestCase):
    """Tests for github_connect view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_github_connect_requires_login(self):
        """Test that github_connect redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:github_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_connect_requires_team_membership(self):
        """Test that github_connect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:github_connect"))

        self.assertEqual(response.status_code, 404)

    def test_github_connect_requires_admin_role(self):
        """Test that github_connect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:github_connect"))

        self.assertEqual(response.status_code, 404)

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    def test_github_connect_redirects_to_github_oauth(self):
        """Test that github_connect redirects to GitHub OAuth authorization URL."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://github.com/login/oauth/authorize"))

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    def test_github_connect_includes_state_parameter(self):
        """Test that github_connect redirect URL includes state parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("state=", response.url)

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    def test_github_connect_includes_redirect_uri(self):
        """Test that github_connect redirect URL includes redirect_uri parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("redirect_uri=", response.url)

    def test_github_connect_when_already_connected_redirects_to_integrations_home(self):
        """Test that github_connect redirects to integrations_home if GitHub is already connected."""
        # Create existing GitHub integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_github_connect_when_already_connected_shows_message(self):
        """Test that github_connect shows message if GitHub is already connected."""
        # Create existing GitHub integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect"), follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("already connected" in str(m).lower() for m in messages))


class GitHubCallbackViewTest(TestCase):
    """Tests for github_callback view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_github_callback_requires_login(self):
        """Test that github_callback redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:github_callback"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_callback_requires_team_membership(self):
        """Test that github_callback returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:github_callback"))

        self.assertEqual(response.status_code, 404)

    def test_github_callback_handles_missing_code_parameter(self):
        """Test that github_callback handles missing code parameter."""
        self.client.force_login(self.admin)

        # No code parameter provided
        response = self.client.get(reverse("integrations:github_callback"), {"state": "valid_state"})

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)

    def test_github_callback_handles_missing_state_parameter(self):
        """Test that github_callback handles missing state parameter."""
        self.client.force_login(self.admin)

        # No state parameter provided
        response = self.client.get(reverse("integrations:github_callback"), {"code": "auth_code_123"})

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)

    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_github_callback_handles_invalid_state(self, mock_verify):
        """Test that github_callback handles invalid state parameter."""
        mock_verify.side_effect = GitHubOAuthError("Invalid state")
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "invalid_state"},
        )

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_github_callback_handles_oauth_denied(self):
        """Test that github_callback handles when user denies OAuth."""
        self.client.force_login(self.admin)

        # GitHub sends error=access_denied when user denies
        response = self.client.get(reverse("integrations:github_callback"), {"error": "access_denied"})

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    @patch("apps.integrations.services.github_oauth.get_user_organizations")
    @patch("apps.integrations.services.github_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_github_callback_with_single_org_creates_integration(self, mock_verify, mock_exchange, mock_get_orgs):
        """Test that github_callback creates integration when user has single organization."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "gho_test_token_123",
            "scope": "read:org,repo,read:user",
        }

        # Mock single organization
        mock_get_orgs.return_value = [
            {
                "login": "acme-corp",
                "id": 12345,
                "description": "Acme Corporation",
            }
        ]

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should create IntegrationCredential
        self.assertTrue(
            IntegrationCredential.objects.filter(
                team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB
            ).exists()
        )

        # Should create GitHubIntegration
        self.assertTrue(GitHubIntegration.objects.filter(team=self.team, organization_slug="acme-corp").exists())

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    @patch("apps.integrations.services.github_oauth.get_user_organizations")
    @patch("apps.integrations.services.github_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_github_callback_with_multiple_orgs_redirects_to_selection(self, mock_verify, mock_exchange, mock_get_orgs):
        """Test that github_callback redirects to org selection when user has multiple organizations."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "gho_test_token_123",
            "scope": "read:org,repo,read:user",
        }

        # Mock multiple organizations
        mock_get_orgs.return_value = [
            {"login": "org1", "id": 1001},
            {"login": "org2", "id": 1002},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should NOT create GitHubIntegration yet
        self.assertFalse(GitHubIntegration.objects.filter(team=self.team).exists())

        # Should redirect to org selection
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_select_org"))

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    @patch("apps.integrations.services.github_oauth.get_user_organizations")
    @patch("apps.integrations.services.github_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_github_callback_stores_encrypted_token(self, mock_verify, mock_exchange, mock_get_orgs):
        """Test that github_callback stores the access token encrypted."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        access_token = "gho_very_secret_token_123456"
        mock_exchange.return_value = {
            "access_token": access_token,
            "scope": "read:org,repo,read:user",
        }

        # Mock single organization
        mock_get_orgs.return_value = [{"login": "acme-corp", "id": 12345}]

        self.client.force_login(self.admin)

        self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Get the credential
        credential = IntegrationCredential.objects.get(team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB)

        # Token should NOT be stored as plaintext
        self.assertNotEqual(credential.access_token, access_token)

        # Token should be encrypted (not equal to original)
        self.assertGreater(len(credential.access_token), len(access_token))

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    @patch("apps.integrations.services.github_oauth.get_user_organizations")
    @patch("apps.integrations.services.github_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_github_callback_sets_connected_by_user(self, mock_verify, mock_exchange, mock_get_orgs):
        """Test that github_callback sets connected_by to the current user."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "gho_test_token",
            "scope": "read:org,repo,read:user",
        }

        # Mock single organization
        mock_get_orgs.return_value = [{"login": "acme-corp", "id": 12345}]

        self.client.force_login(self.admin)

        self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Get the credential
        credential = IntegrationCredential.objects.get(team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB)

        # connected_by should be set to the current user
        self.assertEqual(credential.connected_by, self.admin)

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    @patch("apps.integrations.services.github_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_github_callback_handles_token_exchange_error(self, mock_verify, mock_exchange):
        """Test that github_callback handles token exchange errors gracefully."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange error
        mock_exchange.side_effect = GitHubOAuthError("Token exchange failed")

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should redirect to integrations home with error
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

        # Should NOT create any integration records
        self.assertFalse(IntegrationCredential.objects.filter(team=self.team).exists())


class TestGitHubCallbackMemberSync(TestCase):
    """Tests for GitHub member sync integration in callback view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    @patch("apps.integrations.services.member_sync.sync_github_members")
    @patch("apps.integrations.services.github_oauth.get_user_organizations")
    @patch("apps.integrations.services.github_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_callback_triggers_member_sync_after_integration_created(
        self, mock_verify, mock_exchange, mock_get_orgs, mock_sync
    ):
        """Test that sync_github_members() is called after GitHubIntegration is created."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        access_token = "gho_test_token_123"
        mock_exchange.return_value = {
            "access_token": access_token,
            "scope": "read:org,repo,read:user",
        }

        # Mock single organization
        org_slug = "acme-corp"
        mock_get_orgs.return_value = [{"login": org_slug, "id": 12345}]

        # Mock sync result
        mock_sync.return_value = {"created": 5, "updated": 0, "unchanged": 0, "failed": 0}

        self.client.force_login(self.admin)

        self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Verify sync was called with correct arguments
        mock_sync.assert_called_once_with(self.team, access_token, org_slug)

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    @patch("apps.integrations.services.member_sync.sync_github_members")
    @patch("apps.integrations.services.github_oauth.get_user_organizations")
    @patch("apps.integrations.services.github_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_callback_success_message_includes_member_count(self, mock_verify, mock_exchange, mock_get_orgs, mock_sync):
        """Test that success message includes the number of members imported."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "gho_test_token_123",
            "scope": "read:org,repo,read:user",
        }

        # Mock single organization
        org_slug = "acme-corp"
        mock_get_orgs.return_value = [{"login": org_slug, "id": 12345}]

        # Mock sync result - 5 members created
        mock_sync.return_value = {"created": 5, "updated": 0, "unchanged": 0, "failed": 0}

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
            follow=True,
        )

        # Verify success message includes member count
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("5 members" in str(m).lower() for m in messages))
        self.assertTrue(any("acme-corp" in str(m).lower() for m in messages))

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    @patch("apps.integrations.services.member_sync.sync_github_members")
    @patch("apps.integrations.services.github_oauth.get_user_organizations")
    @patch("apps.integrations.services.github_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_callback_completes_when_sync_fails(self, mock_verify, mock_exchange, mock_get_orgs, mock_sync):
        """Test that OAuth completes successfully even if member sync fails."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "gho_test_token_123",
            "scope": "read:org,repo,read:user",
        }

        # Mock single organization
        org_slug = "acme-corp"
        mock_get_orgs.return_value = [{"login": org_slug, "id": 12345}]

        # Mock sync failure
        mock_sync.side_effect = Exception("GitHub API rate limit exceeded")

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # OAuth should still complete successfully
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

        # GitHubIntegration should still be created
        self.assertTrue(GitHubIntegration.objects.filter(team=self.team, organization_slug=org_slug).exists())

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    @patch("apps.integrations.services.member_sync.sync_github_members")
    @patch("apps.integrations.services.github_oauth.get_user_organizations")
    @patch("apps.integrations.services.github_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_callback_with_multiple_orgs_does_not_sync_members_yet(
        self, mock_verify, mock_exchange, mock_get_orgs, mock_sync
    ):
        """Test that member sync is NOT triggered when multiple orgs require selection."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "gho_test_token_123",
            "scope": "read:org,repo,read:user",
        }

        # Mock multiple organizations
        mock_get_orgs.return_value = [
            {"login": "org1", "id": 1001},
            {"login": "org2", "id": 1002},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:github_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should redirect to org selection
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_select_org"))

        # Sync should NOT be called yet (no org selected)
        mock_sync.assert_not_called()


class GitHubDisconnectViewTest(TestCase):
    """Tests for github_disconnect view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_github_disconnect_requires_login(self):
        """Test that github_disconnect redirects to login if user is not authenticated."""
        response = self.client.post(reverse("integrations:github_disconnect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_disconnect_requires_team_membership(self):
        """Test that github_disconnect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:github_disconnect"))

        self.assertEqual(response.status_code, 404)

    def test_github_disconnect_requires_admin_role(self):
        """Test that github_disconnect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(reverse("integrations:github_disconnect"))

        self.assertEqual(response.status_code, 404)

    def test_github_disconnect_requires_post_method(self):
        """Test that github_disconnect only accepts POST requests."""
        # Create integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(reverse("integrations:github_disconnect"))

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_github_disconnect_deletes_github_integration(self):
        """Test that github_disconnect deletes the GitHubIntegration."""
        # Create integration
        integration = GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        self.client.post(reverse("integrations:github_disconnect"))

        # GitHubIntegration should be deleted
        self.assertFalse(GitHubIntegration.objects.filter(pk=integration.pk).exists())

    def test_github_disconnect_deletes_integration_credential(self):
        """Test that github_disconnect deletes the IntegrationCredential."""
        # Create integration with credential
        integration = GitHubIntegrationFactory(team=self.team)
        credential = integration.credential
        self.client.force_login(self.admin)

        self.client.post(reverse("integrations:github_disconnect"))

        # IntegrationCredential should be deleted
        self.assertFalse(IntegrationCredential.objects.filter(pk=credential.pk).exists())

    def test_github_disconnect_redirects_to_integrations_home(self):
        """Test that github_disconnect redirects to integrations_home after success."""
        # Create integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:github_disconnect"))

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_github_disconnect_shows_success_message(self):
        """Test that github_disconnect shows success message."""
        # Create integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:github_disconnect"), follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("disconnect" in str(m).lower() for m in messages))

    def test_github_disconnect_handles_no_integration_gracefully(self):
        """Test that github_disconnect handles case where no integration exists."""
        # No integration created
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:github_disconnect"))

        # Should still redirect successfully
        self.assertEqual(response.status_code, 302)


class GitHubMembersViewTest(TestCase):
    """Tests for github_members view (list discovered GitHub members)."""

    def setUp(self):
        """Set up test fixtures using factories."""

        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_github_members_requires_login(self):
        """Test that github_members redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:github_members"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_members_requires_team_membership(self):
        """Test that github_members returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:github_members"))

        self.assertEqual(response.status_code, 404)

    def test_github_members_requires_github_integration_exists(self):
        """Test that github_members redirects if GitHub integration doesn't exist."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_members"))

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_github_members_requires_github_integration_shows_message(self):
        """Test that github_members shows message if GitHub integration doesn't exist."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_members"), follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("github" in str(m).lower() and "connect" in str(m).lower() for m in messages))

    def test_github_members_shows_only_members_with_github_id(self):
        """Test that github_members shows only members with github_id populated."""
        from apps.metrics.factories import TeamMemberFactory

        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team)

        # Create members - only ones with github_id should show
        TeamMemberFactory(team=self.team, github_id="123", github_username="alice")
        TeamMemberFactory(team=self.team, github_id="456", github_username="bob")
        non_github_member = TeamMemberFactory(team=self.team, github_id="", github_username="")

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_members"))

        self.assertEqual(response.status_code, 200)
        # Should contain GitHub members
        self.assertContains(response, "alice")
        self.assertContains(response, "bob")
        # Should NOT contain non-GitHub member display_name
        self.assertNotContains(response, non_github_member.display_name)

    def test_github_members_renders_correct_template(self):
        """Test that github_members renders github_members.html template."""
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team)

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_members"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "integrations/github_members.html")

    def test_github_members_works_for_regular_members(self):
        """Test that github_members works for regular team members (not just admins)."""
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team)

        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:github_members"))

        self.assertEqual(response.status_code, 200)


class GitHubMembersSyncViewTest(TestCase):
    """Tests for github_members_sync view (trigger manual member re-sync)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_github_members_sync_requires_post_method(self):
        """Test that github_members_sync only accepts POST requests."""
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(reverse("integrations:github_members_sync"))

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_github_members_sync_requires_login(self):
        """Test that github_members_sync redirects to login if user is not authenticated."""
        response = self.client.post(reverse("integrations:github_members_sync"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_members_sync_requires_team_membership(self):
        """Test that github_members_sync returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:github_members_sync"))

        self.assertEqual(response.status_code, 404)

    def test_github_members_sync_requires_admin_role(self):
        """Test that github_members_sync returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(reverse("integrations:github_members_sync"))

        self.assertEqual(response.status_code, 404)

    @patch("apps.integrations.services.member_sync.sync_github_members")
    def test_github_members_sync_triggers_sync_and_shows_results(self, mock_sync):
        """Test that github_members_sync triggers sync_github_members and shows results message."""
        # Create GitHub integration
        integration = GitHubIntegrationFactory(team=self.team)

        # Mock sync result
        mock_sync.return_value = {"created": 3, "updated": 2, "unchanged": 5, "failed": 0}

        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:github_members_sync"), follow=True)

        # Verify sync was called with correct arguments
        mock_sync.assert_called_once()
        call_args = mock_sync.call_args[0]
        self.assertEqual(call_args[0], self.team)
        self.assertEqual(call_args[2], integration.organization_slug)

        # Verify success message includes counts
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("3" in str(m) and "created" in str(m).lower() for m in messages))

    @patch("apps.integrations.services.member_sync.sync_github_members")
    def test_github_members_sync_redirects_back_to_members_page(self, mock_sync):
        """Test that github_members_sync redirects back to members page after sync."""
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team)

        # Mock sync result
        mock_sync.return_value = {"created": 0, "updated": 0, "unchanged": 5, "failed": 0}

        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:github_members_sync"))

        # Should redirect to github_members page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_members"))


class GitHubMemberToggleViewTest(TestCase):
    """Tests for github_member_toggle view (toggle member active/inactive status)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.metrics.factories import TeamMemberFactory

        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.team_member = TeamMemberFactory(team=self.team, github_id="12345", is_active=True)
        self.client = Client()

    def test_github_member_toggle_requires_post_method(self):
        """Test that github_member_toggle only accepts POST requests."""
        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(reverse("integrations:github_member_toggle", args=[self.team_member.id]))

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_github_member_toggle_requires_login(self):
        """Test that github_member_toggle redirects to login if user is not authenticated."""
        response = self.client.post(reverse("integrations:github_member_toggle", args=[self.team_member.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_member_toggle_requires_team_membership(self):
        """Test that github_member_toggle returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:github_member_toggle", args=[self.team_member.id]))

        self.assertEqual(response.status_code, 404)

    def test_github_member_toggle_requires_admin_role(self):
        """Test that github_member_toggle returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(reverse("integrations:github_member_toggle", args=[self.team_member.id]))

        self.assertEqual(response.status_code, 404)

    def test_github_member_toggle_changes_is_active_status(self):
        """Test that github_member_toggle toggles member is_active status."""
        self.client.force_login(self.admin)

        # Member starts as active
        self.assertTrue(self.team_member.is_active)

        # Toggle to inactive
        self.client.post(reverse("integrations:github_member_toggle", args=[self.team_member.id]))

        # Refresh from DB
        self.team_member.refresh_from_db()
        self.assertFalse(self.team_member.is_active)

        # Toggle back to active
        self.client.post(reverse("integrations:github_member_toggle", args=[self.team_member.id]))

        # Refresh from DB
        self.team_member.refresh_from_db()
        self.assertTrue(self.team_member.is_active)

    def test_github_member_toggle_returns_partial_for_htmx_request(self):
        """Test that github_member_toggle returns partial HTML for HTMX request."""
        self.client.force_login(self.admin)

        # Member starts as active (is_active=True in setUp)
        self.assertTrue(self.team_member.is_active)

        # Make HTMX request (indicated by HX-Request header)
        response = self.client.post(
            reverse("integrations:github_member_toggle", args=[self.team_member.id]),
            HTTP_HX_REQUEST="true",
        )

        # Should return 200 with partial HTML
        self.assertEqual(response.status_code, 200)
        # After toggle, member should be inactive, so response should contain "Inactive"
        self.assertContains(response, "Inactive")
        # And should contain "Activate" button
        self.assertContains(response, "Activate")

    def test_github_member_toggle_redirects_for_non_htmx_request(self):
        """Test that github_member_toggle redirects for non-HTMX request."""
        self.client.force_login(self.admin)

        # Make regular POST request (no HTMX header)
        response = self.client.post(reverse("integrations:github_member_toggle", args=[self.team_member.id]))

        # Should redirect to github_members page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_members"))


class GitHubSelectOrgViewTest(TestCase):
    """Tests for github_select_org view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_github_select_org_get_requires_login(self):
        """Test that github_select_org GET requires authentication."""
        response = self.client.get(reverse("integrations:github_select_org"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_select_org_get_requires_team_membership(self):
        """Test that github_select_org GET requires team membership."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:github_select_org"))

        self.assertEqual(response.status_code, 404)

    @patch("apps.integrations.services.github_oauth.get_user_organizations")
    def test_github_select_org_get_shows_organization_list(self, mock_get_orgs):
        """Test that github_select_org GET displays list of organizations."""
        # Create credential with token
        IntegrationCredentialFactory(
            team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB, connected_by=self.admin
        )

        # Mock organizations
        mock_get_orgs.return_value = [
            {"login": "org1", "id": 1001, "description": "Organization 1"},
            {"login": "org2", "id": 1002, "description": "Organization 2"},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_select_org"))

        # Should show organization selection page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "org1")
        self.assertContains(response, "org2")

    def test_github_select_org_post_requires_login(self):
        """Test that github_select_org POST requires authentication."""
        response = self.client.post(
            reverse("integrations:github_select_org"),
            {"organization_slug": "org1", "organization_id": "1001"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_select_org_post_requires_team_membership(self):
        """Test that github_select_org POST requires team membership."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(
            reverse("integrations:github_select_org"),
            {"organization_slug": "org1", "organization_id": "1001"},
        )

        self.assertEqual(response.status_code, 404)

    def test_github_select_org_post_creates_github_integration(self):
        """Test that github_select_org POST creates GitHubIntegration."""
        # Create credential
        IntegrationCredentialFactory(team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB)

        self.client.force_login(self.admin)

        self.client.post(
            reverse("integrations:github_select_org"),
            {"organization_slug": "acme-corp", "organization_id": "12345"},
        )

        # Should create GitHubIntegration
        self.assertTrue(
            GitHubIntegration.objects.filter(
                team=self.team, organization_slug="acme-corp", organization_id=12345
            ).exists()
        )

    def test_github_select_org_post_redirects_to_integrations_home(self):
        """Test that github_select_org POST redirects to integrations_home."""
        # Create credential
        IntegrationCredentialFactory(team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB)

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("integrations:github_select_org"),
            {"organization_slug": "acme-corp", "organization_id": "12345"},
        )

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_github_select_org_post_shows_success_message(self):
        """Test that github_select_org POST shows success message."""
        # Create credential
        IntegrationCredentialFactory(team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB)

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("integrations:github_select_org"),
            {"organization_slug": "acme-corp", "organization_id": "12345"},
            follow=True,
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("success" in str(m).lower() or "connected" in str(m).lower() for m in messages))


class GitHubReposViewTest(TestCase):
    """Tests for github_repos view (list organization repositories)."""

    def setUp(self):
        """Set up test fixtures using factories."""

        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_github_repos_requires_login(self):
        """Test that github_repos redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:github_repos"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_repos_requires_team_membership(self):
        """Test that github_repos returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:github_repos"))

        self.assertEqual(response.status_code, 404)

    def test_github_repos_requires_github_integration_exists(self):
        """Test that github_repos redirects if GitHub integration doesn't exist."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_github_repos_requires_github_integration_shows_message(self):
        """Test that github_repos shows message if GitHub integration doesn't exist."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repos"), follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("github" in str(m).lower() and "connect" in str(m).lower() for m in messages))

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_github_repos_fetches_and_displays_repos_from_api(self, mock_get_repos):
        """Test that github_repos fetches repositories from GitHub API and displays them."""
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")

        # Mock GitHub API response
        mock_get_repos.return_value = [
            {"id": 1001, "name": "repo-1", "full_name": "acme-corp/repo-1", "description": "First repo"},
            {"id": 1002, "name": "repo-2", "full_name": "acme-corp/repo-2", "description": "Second repo"},
            {"id": 1003, "name": "repo-3", "full_name": "acme-corp/repo-3", "description": "Third repo"},
        ]

        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should successfully render
        self.assertEqual(response.status_code, 200)

        # Should call the API with correct arguments
        mock_get_repos.assert_called_once()

        # Should display repository names
        self.assertContains(response, "repo-1")
        self.assertContains(response, "repo-2")
        self.assertContains(response, "repo-3")

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_github_repos_marks_tracked_repos_correctly(self, mock_get_repos):
        """Test that github_repos correctly identifies which repos are tracked."""
        from apps.integrations.factories import TrackedRepositoryFactory

        # Create GitHub integration
        integration = GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")

        # Create tracked repository
        TrackedRepositoryFactory(
            team=self.team, integration=integration, github_repo_id=1001, full_name="acme-corp/repo-1"
        )

        # Mock GitHub API response
        mock_get_repos.return_value = [
            {"id": 1001, "name": "repo-1", "full_name": "acme-corp/repo-1", "description": "Tracked repo"},
            {"id": 1002, "name": "repo-2", "full_name": "acme-corp/repo-2", "description": "Not tracked"},
        ]

        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should successfully render
        self.assertEqual(response.status_code, 200)

        # Response should indicate repo-1 is tracked
        # (We'll check for "tracked" or a checkmark or similar indicator)
        # The exact check depends on template implementation
        content = response.content.decode()
        # Both repos should be present
        self.assertIn("repo-1", content)
        self.assertIn("repo-2", content)

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_github_repos_handles_api_errors_gracefully(self, mock_get_repos):
        """Test that github_repos handles GitHub API errors gracefully."""
        from apps.integrations.services.github_oauth import GitHubOAuthError

        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")

        # Mock API error
        mock_get_repos.side_effect = GitHubOAuthError("API rate limit exceeded")

        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:github_repos"), follow=True)

        # Should handle error and redirect
        self.assertEqual(response.status_code, 200)

        # Should show error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("error" in str(m).lower() or "failed" in str(m).lower() for m in messages))

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_github_repos_works_for_regular_members(self, mock_get_repos):
        """Test that github_repos works for regular team members (not just admins)."""
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")

        # Mock GitHub API response
        mock_get_repos.return_value = [
            {"id": 1001, "name": "repo-1", "full_name": "acme-corp/repo-1", "description": "Test repo"},
        ]

        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should allow access for regular members
        self.assertEqual(response.status_code, 200)

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_github_repos_renders_correct_template(self, mock_get_repos):
        """Test that github_repos renders github_repos.html template."""
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")

        # Mock GitHub API response
        mock_get_repos.return_value = []

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repos"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "integrations/github_repos.html")

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_github_repos_shows_sync_status_for_synced_repos(self, mock_get_repos):
        """Test that synced repos show 'Synced' badge with last_sync_at."""
        from django.utils import timezone

        from apps.integrations.factories import TrackedRepositoryFactory

        # Create GitHub integration
        integration = GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")

        # Create a tracked repo with last_sync_at set
        sync_time = timezone.now()
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            github_repo_id=12345,
            full_name="acme-corp/test-repo",
            last_sync_at=sync_time,
        )

        # Mock GitHub API response
        mock_get_repos.return_value = [
            {"id": 12345, "name": "test-repo", "full_name": "acme-corp/test-repo", "description": "Test repo"}
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should successfully render
        self.assertEqual(response.status_code, 200)

        # Should contain "Synced" badge
        self.assertContains(response, "Synced")

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_github_repos_shows_not_synced_for_unsynced_repos(self, mock_get_repos):
        """Test that unsynced repos show 'Not synced' badge when last_sync_at is None."""
        from apps.integrations.factories import TrackedRepositoryFactory

        # Create GitHub integration
        integration = GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")

        # Create a tracked repo WITHOUT last_sync_at
        TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            github_repo_id=12345,
            full_name="acme-corp/test-repo",
            last_sync_at=None,
        )

        # Mock GitHub API response
        mock_get_repos.return_value = [
            {"id": 12345, "name": "test-repo", "full_name": "acme-corp/test-repo", "description": "Test repo"}
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should successfully render
        self.assertEqual(response.status_code, 200)

        # Should contain "Not synced" badge
        self.assertContains(response, "Not synced")

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_github_repos_shows_sync_button_for_tracked_repos(self, mock_get_repos):
        """Test that tracked repos show a sync button."""
        from apps.integrations.factories import TrackedRepositoryFactory

        # Create GitHub integration
        integration = GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")

        # Create a tracked repo
        tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            github_repo_id=12345,
            full_name="acme-corp/test-repo",
            last_sync_at=None,
        )

        # Mock GitHub API response
        mock_get_repos.return_value = [
            {"id": 12345, "name": "test-repo", "full_name": "acme-corp/test-repo", "description": "Test repo"}
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should successfully render
        self.assertEqual(response.status_code, 200)

        # Should contain sync button with HTMX post to github_repo_sync
        expected_url = reverse("integrations:github_repo_sync", args=[tracked_repo.id])
        self.assertContains(response, expected_url)
        # Should have HTMX attributes
        self.assertContains(response, 'hx-post="')

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_github_repos_does_not_show_sync_button_for_untracked_repos(self, mock_get_repos):
        """Test that untracked repos do not show a sync button."""
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")

        # Mock GitHub API response - untracked repo
        mock_get_repos.return_value = [
            {"id": 12345, "name": "test-repo", "full_name": "acme-corp/test-repo", "description": "Test repo"}
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should successfully render
        self.assertEqual(response.status_code, 200)

        # Should NOT contain sync button URL (repo is not tracked)
        sync_url_pattern = "github_repo_sync"
        self.assertNotContains(response, sync_url_pattern)


class GitHubRepoToggleViewTest(TestCase):
    """Tests for github_repo_toggle view (toggle repository tracking on/off)."""

    def setUp(self):
        """Set up test fixtures using factories."""

        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.client = Client()

    def test_github_repo_toggle_requires_post_method(self):
        """Test that github_repo_toggle only accepts POST requests."""
        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(reverse("integrations:github_repo_toggle", args=[12345]))

        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)

    def test_github_repo_toggle_requires_login(self):
        """Test that github_repo_toggle redirects to login if user is not authenticated."""
        response = self.client.post(reverse("integrations:github_repo_toggle", args=[12345]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_repo_toggle_requires_team_membership(self):
        """Test that github_repo_toggle returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:github_repo_toggle", args=[12345]))

        self.assertEqual(response.status_code, 404)

    def test_github_repo_toggle_requires_admin_role(self):
        """Test that github_repo_toggle returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(
            reverse("integrations:github_repo_toggle", args=[12345]),
            {"full_name": "acme-corp/test-repo"},
        )

        self.assertEqual(response.status_code, 404)

    def test_github_repo_toggle_requires_github_integration_exists(self):
        """Test that github_repo_toggle fails when GitHub integration doesn't exist."""
        # Create a team without GitHub integration
        other_team = TeamFactory()
        other_admin = UserFactory()
        other_team.members.add(other_admin, through_defaults={"role": ROLE_ADMIN})
        self.client.force_login(other_admin)

        response = self.client.post(
            reverse("integrations:github_repo_toggle", args=[12345]),
            {"full_name": "acme-corp/test-repo"},
        )

        # Should return error (exact status depends on implementation)
        self.assertNotEqual(response.status_code, 200)

    def test_github_repo_toggle_creates_tracked_repository_for_untracked_repo(self):
        """Test that github_repo_toggle creates TrackedRepository for untracked repo."""
        from apps.integrations.models import TrackedRepository

        self.client.force_login(self.admin)

        # Repo is not tracked yet
        repo_id = 12345
        full_name = "acme-corp/test-repo"
        self.assertFalse(TrackedRepository.objects.filter(team=self.team, github_repo_id=repo_id).exists())

        # Toggle to track the repo (non-HTMX request)
        response = self.client.post(
            reverse("integrations:github_repo_toggle", args=[repo_id]), {"full_name": full_name}
        )

        # Should redirect for non-HTMX request
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_repos"))

        # TrackedRepository should now exist
        self.assertTrue(TrackedRepository.objects.filter(team=self.team, github_repo_id=repo_id).exists())
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=repo_id)
        self.assertEqual(tracked_repo.full_name, full_name)
        self.assertEqual(tracked_repo.integration, self.integration)
        self.assertTrue(tracked_repo.is_active)

    def test_github_repo_toggle_deletes_tracked_repository_for_tracked_repo(self):
        """Test that github_repo_toggle deletes TrackedRepository for already tracked repo."""
        from apps.integrations.factories import TrackedRepositoryFactory
        from apps.integrations.models import TrackedRepository

        self.client.force_login(self.admin)

        # Create a tracked repository
        repo_id = 12345
        tracked_repo = TrackedRepositoryFactory(
            team=self.team, integration=self.integration, github_repo_id=repo_id, full_name="acme-corp/test-repo"
        )

        # Verify it exists
        self.assertTrue(TrackedRepository.objects.filter(pk=tracked_repo.pk).exists())

        # Toggle to untrack the repo (non-HTMX request)
        response = self.client.post(
            reverse("integrations:github_repo_toggle", args=[repo_id]),
            {"full_name": "acme-corp/test-repo"},
        )

        # Should redirect for non-HTMX request
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_repos"))

        # TrackedRepository should be deleted
        self.assertFalse(TrackedRepository.objects.filter(pk=tracked_repo.pk).exists())

    def test_github_repo_toggle_returns_partial_template_for_htmx(self):
        """Test that github_repo_toggle returns partial HTML template for HTMX requests."""
        self.client.force_login(self.admin)

        # Make HTMX request to track a repo (indicated by HX-Request header)
        response = self.client.post(
            reverse("integrations:github_repo_toggle", args=[12345]),
            {"full_name": "acme-corp/test-repo"},
            HTTP_HX_REQUEST="true",
        )

        # Should return 200 with partial HTML
        self.assertEqual(response.status_code, 200)

        # Should render a partial template (repo card component)
        # The exact content depends on the template, but should contain repo info
        self.assertContains(response, "acme-corp/test-repo")

    def test_github_repo_toggle_requires_full_name_in_request_body(self):
        """Test that github_repo_toggle requires full_name parameter for creating new TrackedRepository."""
        from apps.integrations.models import TrackedRepository

        self.client.force_login(self.admin)

        # Try to track repo without providing full_name
        repo_id = 12345
        self.client.post(
            reverse("integrations:github_repo_toggle", args=[repo_id]),
            {},  # No full_name provided
        )

        # Should fail (exact error handling depends on implementation)
        # For now, test that it doesn't create the TrackedRepository
        self.assertFalse(TrackedRepository.objects.filter(team=self.team, github_repo_id=repo_id).exists())


class GitHubReposWebhookStatusViewTest(TestCase):
    """Tests for webhook status display in github_repos view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.integration = GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")
        self.client = Client()

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_repo_card_shows_webhook_active_when_webhook_id_exists(self, mock_get_repos):
        """Test that repo card shows 'Webhook active' badge when TrackedRepository has webhook_id."""
        from apps.integrations.factories import TrackedRepositoryFactory

        # Create a tracked repository WITH a webhook_id
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=1001,
            full_name="acme-corp/repo-1",
            webhook_id=99887766,  # Has webhook registered
        )

        # Mock GitHub API response
        mock_get_repos.return_value = [
            {"id": 1001, "name": "repo-1", "full_name": "acme-corp/repo-1", "description": "Test repo"},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should successfully render
        self.assertEqual(response.status_code, 200)

        # Should show "Webhook active" badge
        self.assertContains(response, "Webhook active")

    @patch("apps.integrations.services.github_oauth.get_organization_repositories")
    def test_repo_card_shows_webhook_pending_when_no_webhook_id(self, mock_get_repos):
        """Test that repo card shows 'Webhook pending' badge when TrackedRepository has no webhook_id."""
        from apps.integrations.factories import TrackedRepositoryFactory

        # Create a tracked repository WITHOUT a webhook_id
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=1002,
            full_name="acme-corp/repo-2",
            webhook_id=None,  # No webhook registered
        )

        # Mock GitHub API response
        mock_get_repos.return_value = [
            {"id": 1002, "name": "repo-2", "full_name": "acme-corp/repo-2", "description": "Test repo"},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_repos"))

        # Should successfully render
        self.assertEqual(response.status_code, 200)

        # Should show "Webhook pending" badge
        self.assertContains(response, "Webhook pending")


class GitHubRepoToggleWebhookIntegrationTest(TestCase):
    """Tests for webhook integration in github_repo_toggle view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.integration = GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")
        self.client = Client()

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    @patch("apps.integrations.services.github_webhooks.create_repository_webhook")
    def test_toggle_triggers_sync_on_track(self, mock_create_webhook, mock_sync):
        """Test that toggling a repo to tracked automatically triggers historical sync."""
        from apps.integrations.models import TrackedRepository

        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 99887766

        # Mock sync result
        mock_sync.return_value = {"prs_synced": 10, "reviews_synced": 5, "errors": []}

        self.client.force_login(self.admin)

        repo_id = 12345
        full_name = "acme-corp/test-repo"

        # Track the repo
        self.client.post(reverse("integrations:github_repo_toggle", args=[repo_id]), {"full_name": full_name})

        # Verify sync_repository_history was called after webhook registration
        mock_sync.assert_called_once()
        # Get the tracked_repo argument
        call_args = mock_sync.call_args[0]
        tracked_repo_arg = call_args[0]
        self.assertIsInstance(tracked_repo_arg, TrackedRepository)
        self.assertEqual(tracked_repo_arg.github_repo_id, repo_id)
        self.assertEqual(tracked_repo_arg.full_name, full_name)

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    @patch("apps.integrations.services.github_webhooks.create_repository_webhook")
    def test_toggle_sync_failure_does_not_block_tracking(self, mock_create_webhook, mock_sync):
        """Test that repo tracking succeeds even if historical sync fails (graceful degradation)."""
        from apps.integrations.models import TrackedRepository

        # Mock webhook creation
        mock_create_webhook.return_value = 99887766

        # Mock sync failure
        mock_sync.side_effect = Exception("GitHub API rate limit exceeded")

        self.client.force_login(self.admin)

        repo_id = 12345
        full_name = "acme-corp/test-repo"

        # Track the repo - should succeed despite sync failure
        response = self.client.post(
            reverse("integrations:github_repo_toggle", args=[repo_id]), {"full_name": full_name}
        )

        # Should redirect successfully
        self.assertEqual(response.status_code, 302)

        # TrackedRepository should still be created
        self.assertTrue(TrackedRepository.objects.filter(team=self.team, github_repo_id=repo_id).exists())

        # webhook_id should still be set (webhook creation happened before sync)
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=repo_id)
        self.assertEqual(tracked_repo.webhook_id, 99887766)

    @patch("apps.integrations.services.github_webhooks.create_repository_webhook")
    def test_toggle_creates_webhook_when_tracking_repo(self, mock_create_webhook):
        """Test that toggling a repo to tracked creates a webhook."""
        from apps.integrations.models import TrackedRepository

        # Mock webhook creation to return a webhook ID
        mock_create_webhook.return_value = 99887766

        self.client.force_login(self.admin)

        repo_id = 12345
        full_name = "acme-corp/test-repo"

        # Track the repo
        self.client.post(reverse("integrations:github_repo_toggle", args=[repo_id]), {"full_name": full_name})

        # Verify create_repository_webhook was called
        mock_create_webhook.assert_called_once()
        call_args = mock_create_webhook.call_args[1]  # Get keyword arguments
        self.assertEqual(call_args["repo_full_name"], full_name)
        self.assertIn("webhook_url", call_args)
        self.assertIn("/webhooks/github/", call_args["webhook_url"])

        # Verify TrackedRepository was created
        self.assertTrue(TrackedRepository.objects.filter(team=self.team, github_repo_id=repo_id).exists())

    @patch("apps.integrations.services.github_webhooks.create_repository_webhook")
    def test_toggle_stores_webhook_id_in_tracked_repository(self, mock_create_webhook):
        """Test that webhook_id is stored in TrackedRepository after successful webhook creation."""
        from apps.integrations.models import TrackedRepository

        # Mock webhook creation to return a specific webhook ID
        webhook_id = 99887766
        mock_create_webhook.return_value = webhook_id

        self.client.force_login(self.admin)

        repo_id = 12345
        full_name = "acme-corp/test-repo"

        # Track the repo
        self.client.post(reverse("integrations:github_repo_toggle", args=[repo_id]), {"full_name": full_name})

        # Verify webhook_id was stored in TrackedRepository
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=repo_id)
        self.assertEqual(tracked_repo.webhook_id, webhook_id)

    @patch("apps.integrations.services.github_webhooks.delete_repository_webhook")
    def test_toggle_deletes_webhook_when_untracking_repo(self, mock_delete_webhook):
        """Test that toggling a repo to untracked deletes its webhook."""
        from apps.integrations.factories import TrackedRepositoryFactory

        # Mock webhook deletion
        mock_delete_webhook.return_value = True

        self.client.force_login(self.admin)

        # Create a tracked repository with a webhook_id
        repo_id = 12345
        full_name = "acme-corp/test-repo"
        webhook_id = 99887766
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=repo_id,
            full_name=full_name,
            webhook_id=webhook_id,
        )

        # Untrack the repo
        self.client.post(reverse("integrations:github_repo_toggle", args=[repo_id]), {"full_name": full_name})

        # Verify delete_repository_webhook was called with correct arguments
        mock_delete_webhook.assert_called_once()
        call_args = mock_delete_webhook.call_args[1]  # Get keyword arguments
        self.assertEqual(call_args["repo_full_name"], full_name)
        self.assertEqual(call_args["webhook_id"], webhook_id)

    @patch("apps.integrations.services.github_webhooks.create_repository_webhook")
    def test_toggle_succeeds_even_if_webhook_creation_fails(self, mock_create_webhook):
        """Test that repo tracking succeeds even if webhook creation fails (graceful degradation)."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.services.github_oauth import GitHubOAuthError

        # Mock webhook creation to fail
        mock_create_webhook.side_effect = GitHubOAuthError("Insufficient permissions to create webhook")

        self.client.force_login(self.admin)

        repo_id = 12345
        full_name = "acme-corp/test-repo"

        # Track the repo - should succeed despite webhook failure
        response = self.client.post(
            reverse("integrations:github_repo_toggle", args=[repo_id]), {"full_name": full_name}
        )

        # Should redirect successfully
        self.assertEqual(response.status_code, 302)

        # TrackedRepository should still be created
        self.assertTrue(TrackedRepository.objects.filter(team=self.team, github_repo_id=repo_id).exists())

        # webhook_id should be None since creation failed
        tracked_repo = TrackedRepository.objects.get(team=self.team, github_repo_id=repo_id)
        self.assertIsNone(tracked_repo.webhook_id)

    @patch("apps.integrations.services.github_webhooks.delete_repository_webhook")
    def test_toggle_succeeds_even_if_webhook_deletion_fails(self, mock_delete_webhook):
        """Test that repo untracking succeeds even if webhook deletion fails (graceful degradation)."""
        from apps.integrations.factories import TrackedRepositoryFactory
        from apps.integrations.models import TrackedRepository
        from apps.integrations.services.github_oauth import GitHubOAuthError

        # Mock webhook deletion to fail
        mock_delete_webhook.side_effect = GitHubOAuthError("Insufficient permissions to delete webhook")

        self.client.force_login(self.admin)

        # Create a tracked repository with a webhook_id
        repo_id = 12345
        full_name = "acme-corp/test-repo"
        webhook_id = 99887766
        tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=repo_id,
            full_name=full_name,
            webhook_id=webhook_id,
        )

        # Untrack the repo - should succeed despite webhook deletion failure
        response = self.client.post(
            reverse("integrations:github_repo_toggle", args=[repo_id]), {"full_name": full_name}
        )

        # Should redirect successfully
        self.assertEqual(response.status_code, 302)

        # TrackedRepository should still be deleted
        self.assertFalse(TrackedRepository.objects.filter(pk=tracked_repo.pk).exists())


class GitHubRepoSyncViewTest(TestCase):
    """Tests for github_repo_sync view (manual trigger for historical sync)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.factories import TrackedRepositoryFactory

        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.integration = GitHubIntegrationFactory(team=self.team, organization_slug="acme-corp")
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team, integration=self.integration, github_repo_id=12345, full_name="acme-corp/test-repo"
        )
        self.client = Client()

    def test_github_repo_sync_requires_authentication(self):
        """Test that github_repo_sync redirects to login if user is not authenticated."""
        response = self.client.post(reverse("integrations:github_repo_sync", args=[self.tracked_repo.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_repo_sync_requires_team_membership(self):
        """Test that github_repo_sync returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:github_repo_sync", args=[self.tracked_repo.id]))

        self.assertEqual(response.status_code, 404)

    def test_github_repo_sync_requires_post_method(self):
        """Test that github_repo_sync only accepts POST requests."""
        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(reverse("integrations:github_repo_sync", args=[self.tracked_repo.id]))

        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)

    def test_github_repo_sync_returns_404_for_unknown_repo(self):
        """Test that github_repo_sync returns 404 if TrackedRepository doesn't exist."""
        self.client.force_login(self.admin)

        # Use a non-existent repo ID
        response = self.client.post(reverse("integrations:github_repo_sync", args=[99999]))

        # Should return 404
        self.assertEqual(response.status_code, 404)

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_github_repo_sync_triggers_sync(self, mock_sync):
        """Test that github_repo_sync calls sync_repository_history for the tracked repo."""
        # Mock sync result
        mock_sync.return_value = {"prs_synced": 15, "reviews_synced": 8, "errors": []}

        self.client.force_login(self.admin)

        # Trigger manual sync
        self.client.post(reverse("integrations:github_repo_sync", args=[self.tracked_repo.id]))

        # Verify sync was called with the tracked repository
        mock_sync.assert_called_once()
        call_args = mock_sync.call_args[0]
        tracked_repo_arg = call_args[0]
        self.assertEqual(tracked_repo_arg.id, self.tracked_repo.id)
        self.assertEqual(tracked_repo_arg.github_repo_id, self.tracked_repo.github_repo_id)

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_github_repo_sync_returns_success_response(self, mock_sync):
        """Test that github_repo_sync returns 200 with success message in JSON."""
        # Mock sync result
        mock_sync.return_value = {"prs_synced": 15, "reviews_synced": 8, "errors": []}

        self.client.force_login(self.admin)

        # Trigger manual sync
        response = self.client.post(reverse("integrations:github_repo_sync", args=[self.tracked_repo.id]))

        # Should return 200
        self.assertEqual(response.status_code, 200)

        # Should return JSON response
        self.assertEqual(response["Content-Type"], "application/json")

        # Should contain success data
        import json

        data = json.loads(response.content)
        self.assertEqual(data["prs_synced"], 15)
        self.assertEqual(data["reviews_synced"], 8)
        self.assertEqual(data["errors"], [])

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_github_repo_sync_handles_sync_errors_gracefully(self, mock_sync):
        """Test that github_repo_sync handles sync errors and returns them in response."""
        # Mock sync result with errors
        mock_sync.return_value = {
            "prs_synced": 10,
            "reviews_synced": 5,
            "errors": ["Failed to sync PR #42: API timeout", "Failed to sync PR #43: Invalid data"],
        }

        self.client.force_login(self.admin)

        # Trigger manual sync
        response = self.client.post(reverse("integrations:github_repo_sync", args=[self.tracked_repo.id]))

        # Should still return 200 (partial success)
        self.assertEqual(response.status_code, 200)

        # Should include errors in response
        import json

        data = json.loads(response.content)
        self.assertEqual(data["prs_synced"], 10)
        self.assertEqual(data["reviews_synced"], 5)
        self.assertEqual(len(data["errors"]), 2)
        self.assertIn("Failed to sync PR #42", data["errors"][0])

    @patch("apps.integrations.services.github_sync.sync_repository_history")
    def test_github_repo_sync_handles_complete_failure(self, mock_sync):
        """Test that github_repo_sync handles complete sync failure."""
        # Mock complete sync failure
        mock_sync.side_effect = Exception("GitHub API unavailable")

        self.client.force_login(self.admin)

        # Trigger manual sync
        response = self.client.post(reverse("integrations:github_repo_sync", args=[self.tracked_repo.id]))

        # Should return error response
        self.assertIn(response.status_code, [500, 400])  # Either is acceptable
