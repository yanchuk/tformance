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
