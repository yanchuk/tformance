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
        response = self.client.get(reverse("integrations:integrations_home", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_integrations_home_requires_team_membership(self):
        """Test that integrations_home returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:integrations_home", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_integrations_home_returns_200_for_team_member(self):
        """Test that integrations_home returns 200 for authenticated team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:integrations_home", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)

    def test_integrations_home_returns_200_for_team_admin(self):
        """Test that integrations_home returns 200 for authenticated team admins."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:integrations_home", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)

    def test_integrations_home_shows_github_not_connected_status(self):
        """Test that integrations_home shows GitHub as not connected when no integration exists."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:integrations_home", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        # Should show not connected status
        self.assertContains(response, "Connect")

    def test_integrations_home_shows_github_connected_status(self):
        """Test that integrations_home shows GitHub as connected when integration exists."""
        # Create a GitHub integration for the team
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:integrations_home", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        # Should show connected status
        self.assertContains(response, "Connected")


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
        response = self.client.get(reverse("integrations:github_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_connect_requires_team_membership(self):
        """Test that github_connect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:github_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_github_connect_requires_admin_role(self):
        """Test that github_connect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:github_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    def test_github_connect_redirects_to_github_oauth(self):
        """Test that github_connect redirects to GitHub OAuth authorization URL."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://github.com/login/oauth/authorize"))

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    def test_github_connect_includes_state_parameter(self):
        """Test that github_connect redirect URL includes state parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("state=", response.url)

    @override_settings(GITHUB_CLIENT_ID="test_client_id", GITHUB_SECRET_ID="test_secret")
    def test_github_connect_includes_redirect_uri(self):
        """Test that github_connect redirect URL includes redirect_uri parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("redirect_uri=", response.url)

    def test_github_connect_when_already_connected_redirects_to_integrations_home(self):
        """Test that github_connect redirects to integrations_home if GitHub is already connected."""
        # Create existing GitHub integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

    def test_github_connect_when_already_connected_shows_message(self):
        """Test that github_connect shows message if GitHub is already connected."""
        # Create existing GitHub integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_connect", args=[self.team.slug]), follow=True)

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
        response = self.client.get(reverse("integrations:github_callback", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_callback_requires_team_membership(self):
        """Test that github_callback returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:github_callback", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_github_callback_handles_missing_code_parameter(self):
        """Test that github_callback handles missing code parameter."""
        self.client.force_login(self.admin)

        # No code parameter provided
        response = self.client.get(
            reverse("integrations:github_callback", args=[self.team.slug]), {"state": "valid_state"}
        )

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)

    def test_github_callback_handles_missing_state_parameter(self):
        """Test that github_callback handles missing state parameter."""
        self.client.force_login(self.admin)

        # No state parameter provided
        response = self.client.get(
            reverse("integrations:github_callback", args=[self.team.slug]), {"code": "auth_code_123"}
        )

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)

    @patch("apps.integrations.services.github_oauth.verify_oauth_state")
    def test_github_callback_handles_invalid_state(self, mock_verify):
        """Test that github_callback handles invalid state parameter."""
        mock_verify.side_effect = GitHubOAuthError("Invalid state")
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:github_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "invalid_state"},
        )

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

    def test_github_callback_handles_oauth_denied(self):
        """Test that github_callback handles when user denies OAuth."""
        self.client.force_login(self.admin)

        # GitHub sends error=access_denied when user denies
        response = self.client.get(
            reverse("integrations:github_callback", args=[self.team.slug]), {"error": "access_denied"}
        )

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
            reverse("integrations:github_callback", args=[self.team.slug]),
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
            reverse("integrations:github_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should NOT create GitHubIntegration yet
        self.assertFalse(GitHubIntegration.objects.filter(team=self.team).exists())

        # Should redirect to org selection
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_select_org", args=[self.team.slug]))

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
            reverse("integrations:github_callback", args=[self.team.slug]),
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
            reverse("integrations:github_callback", args=[self.team.slug]),
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
            reverse("integrations:github_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should redirect to integrations home with error
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

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
            reverse("integrations:github_callback", args=[self.team.slug]),
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
            reverse("integrations:github_callback", args=[self.team.slug]),
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
            reverse("integrations:github_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # OAuth should still complete successfully
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

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
            reverse("integrations:github_callback", args=[self.team.slug]),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should redirect to org selection
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_select_org", args=[self.team.slug]))

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
        response = self.client.post(reverse("integrations:github_disconnect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_disconnect_requires_team_membership(self):
        """Test that github_disconnect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:github_disconnect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_github_disconnect_requires_admin_role(self):
        """Test that github_disconnect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(reverse("integrations:github_disconnect", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_github_disconnect_requires_post_method(self):
        """Test that github_disconnect only accepts POST requests."""
        # Create integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(reverse("integrations:github_disconnect", args=[self.team.slug]))

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_github_disconnect_deletes_github_integration(self):
        """Test that github_disconnect deletes the GitHubIntegration."""
        # Create integration
        integration = GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        self.client.post(reverse("integrations:github_disconnect", args=[self.team.slug]))

        # GitHubIntegration should be deleted
        self.assertFalse(GitHubIntegration.objects.filter(pk=integration.pk).exists())

    def test_github_disconnect_deletes_integration_credential(self):
        """Test that github_disconnect deletes the IntegrationCredential."""
        # Create integration with credential
        integration = GitHubIntegrationFactory(team=self.team)
        credential = integration.credential
        self.client.force_login(self.admin)

        self.client.post(reverse("integrations:github_disconnect", args=[self.team.slug]))

        # IntegrationCredential should be deleted
        self.assertFalse(IntegrationCredential.objects.filter(pk=credential.pk).exists())

    def test_github_disconnect_redirects_to_integrations_home(self):
        """Test that github_disconnect redirects to integrations_home after success."""
        # Create integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:github_disconnect", args=[self.team.slug]))

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

    def test_github_disconnect_shows_success_message(self):
        """Test that github_disconnect shows success message."""
        # Create integration
        GitHubIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:github_disconnect", args=[self.team.slug]), follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("disconnect" in str(m).lower() for m in messages))

    def test_github_disconnect_handles_no_integration_gracefully(self):
        """Test that github_disconnect handles case where no integration exists."""
        # No integration created
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:github_disconnect", args=[self.team.slug]))

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
        response = self.client.get(reverse("integrations:github_members", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_members_requires_team_membership(self):
        """Test that github_members returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:github_members", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_github_members_requires_github_integration_exists(self):
        """Test that github_members redirects if GitHub integration doesn't exist."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_members", args=[self.team.slug]))

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

    def test_github_members_requires_github_integration_shows_message(self):
        """Test that github_members shows message if GitHub integration doesn't exist."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:github_members", args=[self.team.slug]), follow=True)

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

        response = self.client.get(reverse("integrations:github_members", args=[self.team.slug]))

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

        response = self.client.get(reverse("integrations:github_members", args=[self.team.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "integrations/github_members.html")

    def test_github_members_works_for_regular_members(self):
        """Test that github_members works for regular team members (not just admins)."""
        # Create GitHub integration
        GitHubIntegrationFactory(team=self.team)

        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:github_members", args=[self.team.slug]))

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
        response = self.client.get(reverse("integrations:github_members_sync", args=[self.team.slug]))

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_github_members_sync_requires_login(self):
        """Test that github_members_sync redirects to login if user is not authenticated."""
        response = self.client.post(reverse("integrations:github_members_sync", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_members_sync_requires_team_membership(self):
        """Test that github_members_sync returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:github_members_sync", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    def test_github_members_sync_requires_admin_role(self):
        """Test that github_members_sync returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(reverse("integrations:github_members_sync", args=[self.team.slug]))

        self.assertEqual(response.status_code, 404)

    @patch("apps.integrations.services.member_sync.sync_github_members")
    def test_github_members_sync_triggers_sync_and_shows_results(self, mock_sync):
        """Test that github_members_sync triggers sync_github_members and shows results message."""
        # Create GitHub integration
        integration = GitHubIntegrationFactory(team=self.team)

        # Mock sync result
        mock_sync.return_value = {"created": 3, "updated": 2, "unchanged": 5, "failed": 0}

        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:github_members_sync", args=[self.team.slug]), follow=True)

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

        response = self.client.post(reverse("integrations:github_members_sync", args=[self.team.slug]))

        # Should redirect to github_members page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_members", args=[self.team.slug]))


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
        response = self.client.get(
            reverse("integrations:github_member_toggle", args=[self.team.slug, self.team_member.id])
        )

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_github_member_toggle_requires_login(self):
        """Test that github_member_toggle redirects to login if user is not authenticated."""
        response = self.client.post(
            reverse("integrations:github_member_toggle", args=[self.team.slug, self.team_member.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_member_toggle_requires_team_membership(self):
        """Test that github_member_toggle returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(
            reverse("integrations:github_member_toggle", args=[self.team.slug, self.team_member.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_github_member_toggle_requires_admin_role(self):
        """Test that github_member_toggle returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(
            reverse("integrations:github_member_toggle", args=[self.team.slug, self.team_member.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_github_member_toggle_changes_is_active_status(self):
        """Test that github_member_toggle toggles member is_active status."""
        self.client.force_login(self.admin)

        # Member starts as active
        self.assertTrue(self.team_member.is_active)

        # Toggle to inactive
        self.client.post(reverse("integrations:github_member_toggle", args=[self.team.slug, self.team_member.id]))

        # Refresh from DB
        self.team_member.refresh_from_db()
        self.assertFalse(self.team_member.is_active)

        # Toggle back to active
        self.client.post(reverse("integrations:github_member_toggle", args=[self.team.slug, self.team_member.id]))

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
            reverse("integrations:github_member_toggle", args=[self.team.slug, self.team_member.id]),
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
        response = self.client.post(
            reverse("integrations:github_member_toggle", args=[self.team.slug, self.team_member.id])
        )

        # Should redirect to github_members page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:github_members", args=[self.team.slug]))


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
        response = self.client.get(reverse("integrations:github_select_org", args=[self.team.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_select_org_get_requires_team_membership(self):
        """Test that github_select_org GET requires team membership."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:github_select_org", args=[self.team.slug]))

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

        response = self.client.get(reverse("integrations:github_select_org", args=[self.team.slug]))

        # Should show organization selection page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "org1")
        self.assertContains(response, "org2")

    def test_github_select_org_post_requires_login(self):
        """Test that github_select_org POST requires authentication."""
        response = self.client.post(
            reverse("integrations:github_select_org", args=[self.team.slug]),
            {"organization_slug": "org1", "organization_id": "1001"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_github_select_org_post_requires_team_membership(self):
        """Test that github_select_org POST requires team membership."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(
            reverse("integrations:github_select_org", args=[self.team.slug]),
            {"organization_slug": "org1", "organization_id": "1001"},
        )

        self.assertEqual(response.status_code, 404)

    def test_github_select_org_post_creates_github_integration(self):
        """Test that github_select_org POST creates GitHubIntegration."""
        # Create credential
        IntegrationCredentialFactory(team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB)

        self.client.force_login(self.admin)

        self.client.post(
            reverse("integrations:github_select_org", args=[self.team.slug]),
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
            reverse("integrations:github_select_org", args=[self.team.slug]),
            {"organization_slug": "acme-corp", "organization_id": "12345"},
        )

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home", args=[self.team.slug]))

    def test_github_select_org_post_shows_success_message(self):
        """Test that github_select_org POST shows success message."""
        # Create credential
        IntegrationCredentialFactory(team=self.team, provider=IntegrationCredential.PROVIDER_GITHUB)

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("integrations:github_select_org", args=[self.team.slug]),
            {"organization_slug": "acme-corp", "organization_id": "12345"},
            follow=True,
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("success" in str(m).lower() or "connected" in str(m).lower() for m in messages))
