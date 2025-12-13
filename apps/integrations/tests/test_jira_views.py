"""Tests for Jira OAuth views."""

from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.integrations.factories import (
    IntegrationCredentialFactory,
    JiraIntegrationFactory,
    UserFactory,
)
from apps.integrations.models import IntegrationCredential, JiraIntegration
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER


class JiraConnectViewTest(TestCase):
    """Tests for jira_connect view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_jira_connect_requires_login(self):
        """Test that jira_connect redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:jira_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_jira_connect_requires_team_membership(self):
        """Test that jira_connect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:jira_connect"))

        self.assertEqual(response.status_code, 404)

    def test_jira_connect_requires_admin_role(self):
        """Test that jira_connect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.get(reverse("integrations:jira_connect"))

        self.assertEqual(response.status_code, 404)

    @override_settings(JIRA_CLIENT_ID="test_client_id", JIRA_SECRET="test_secret")
    def test_jira_connect_redirects_to_atlassian_oauth(self):
        """Test that jira_connect redirects to Atlassian OAuth authorization URL."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://auth.atlassian.com/authorize"))

    @override_settings(JIRA_CLIENT_ID="test_client_id", JIRA_SECRET="test_secret")
    def test_jira_connect_includes_state_parameter(self):
        """Test that jira_connect redirect URL includes state parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("state=", response.url)

    @override_settings(JIRA_CLIENT_ID="test_client_id", JIRA_SECRET="test_secret")
    def test_jira_connect_includes_redirect_uri(self):
        """Test that jira_connect redirect URL includes redirect_uri parameter."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("redirect_uri=", response.url)

    def test_jira_connect_when_already_connected_redirects_to_integrations_home(self):
        """Test that jira_connect redirects to integrations_home if Jira is already connected."""
        # Create existing Jira integration
        JiraIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_jira_connect_when_already_connected_shows_message(self):
        """Test that jira_connect shows message if Jira is already connected."""
        # Create existing Jira integration
        JiraIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_connect"), follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("already connected" in str(m).lower() for m in messages))


class JiraCallbackViewTest(TestCase):
    """Tests for jira_callback view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_jira_callback_requires_login(self):
        """Test that jira_callback redirects to login if user is not authenticated."""
        response = self.client.get(reverse("integrations:jira_callback"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_jira_callback_requires_team_membership(self):
        """Test that jira_callback returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:jira_callback"))

        self.assertEqual(response.status_code, 404)

    def test_jira_callback_handles_access_denied_error(self):
        """Test that jira_callback handles when user denies OAuth."""
        self.client.force_login(self.admin)

        # Atlassian sends error=access_denied when user denies
        response = self.client.get(reverse("integrations:jira_callback"), {"error": "access_denied"})

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)

    def test_jira_callback_handles_missing_code_parameter(self):
        """Test that jira_callback handles missing code parameter."""
        self.client.force_login(self.admin)

        # No code parameter provided
        response = self.client.get(reverse("integrations:jira_callback"), {"state": "valid_state"})

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)

    def test_jira_callback_handles_missing_state_parameter(self):
        """Test that jira_callback handles missing state parameter."""
        self.client.force_login(self.admin)

        # No state parameter provided
        response = self.client.get(reverse("integrations:jira_callback"), {"code": "auth_code_123"})

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)

    @patch("apps.integrations.services.jira_oauth.verify_oauth_state")
    def test_jira_callback_handles_invalid_state(self, mock_verify):
        """Test that jira_callback handles invalid state parameter."""
        from apps.integrations.services.jira_oauth import JiraOAuthError

        mock_verify.side_effect = JiraOAuthError("Invalid state")
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:jira_callback"),
            {"code": "auth_code_123", "state": "invalid_state"},
        )

        # Should redirect to integrations home with error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    @override_settings(JIRA_CLIENT_ID="test_client_id", JIRA_SECRET="test_secret")
    @patch("apps.integrations.services.jira_oauth.get_accessible_resources")
    @patch("apps.integrations.services.jira_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.jira_oauth.verify_oauth_state")
    def test_jira_callback_with_single_site_creates_integration(self, mock_verify, mock_exchange, mock_get_resources):
        """Test that jira_callback creates integration when user has single site."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "jira_access_token_123",
            "refresh_token": "jira_refresh_token_456",
            "expires_in": 3600,
        }

        # Mock single site
        mock_get_resources.return_value = [
            {
                "id": "cloud-id-12345",
                "name": "Acme Corp",
                "url": "https://acme-corp.atlassian.net",
            }
        ]

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:jira_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should create IntegrationCredential
        self.assertTrue(
            IntegrationCredential.objects.filter(team=self.team, provider=IntegrationCredential.PROVIDER_JIRA).exists()
        )

        # Should create JiraIntegration
        self.assertTrue(JiraIntegration.objects.filter(team=self.team, cloud_id="cloud-id-12345").exists())

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)

    @override_settings(JIRA_CLIENT_ID="test_client_id", JIRA_SECRET="test_secret")
    @patch("apps.integrations.services.jira_oauth.get_accessible_resources")
    @patch("apps.integrations.services.jira_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.jira_oauth.verify_oauth_state")
    def test_jira_callback_with_multiple_sites_redirects_to_selection(
        self, mock_verify, mock_exchange, mock_get_resources
    ):
        """Test that jira_callback redirects to site selection when user has multiple sites."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "jira_access_token_123",
            "refresh_token": "jira_refresh_token_456",
            "expires_in": 3600,
        }

        # Mock multiple sites
        mock_get_resources.return_value = [
            {"id": "cloud-id-1", "name": "Site 1", "url": "https://site1.atlassian.net"},
            {"id": "cloud-id-2", "name": "Site 2", "url": "https://site2.atlassian.net"},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:jira_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should NOT create JiraIntegration yet
        self.assertFalse(JiraIntegration.objects.filter(team=self.team).exists())

        # Should redirect to site selection
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:jira_select_site"))

    @override_settings(JIRA_CLIENT_ID="test_client_id", JIRA_SECRET="test_secret")
    @patch("apps.integrations.services.jira_oauth.get_accessible_resources")
    @patch("apps.integrations.services.jira_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.jira_oauth.verify_oauth_state")
    def test_jira_callback_stores_encrypted_token(self, mock_verify, mock_exchange, mock_get_resources):
        """Test that jira_callback stores the access token encrypted via EncryptedTextField."""
        from django.db import connection

        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        access_token = "jira_very_secret_token_123456"
        mock_exchange.return_value = {
            "access_token": access_token,
            "refresh_token": "jira_refresh_token_456",
            "expires_in": 3600,
        }

        # Mock single site
        mock_get_resources.return_value = [
            {"id": "cloud-id-12345", "name": "Acme", "url": "https://acme.atlassian.net"}
        ]

        self.client.force_login(self.admin)

        self.client.get(
            reverse("integrations:jira_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Get the credential - access via model returns decrypted value (transparent encryption)
        credential = IntegrationCredential.objects.get(team=self.team, provider=IntegrationCredential.PROVIDER_JIRA)
        self.assertEqual(credential.access_token, access_token)

        # Verify the raw database value is encrypted (not plaintext)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT access_token FROM integrations_integrationcredential WHERE id = %s",
                [credential.id],
            )
            raw_db_value = cursor.fetchone()[0]

        # Raw DB value should be different from plaintext (encrypted)
        self.assertNotEqual(raw_db_value, access_token)
        # Encrypted value should be longer (Fernet adds overhead)
        self.assertGreater(len(raw_db_value), len(access_token))

    @override_settings(JIRA_CLIENT_ID="test_client_id", JIRA_SECRET="test_secret")
    @patch("apps.integrations.services.jira_oauth.get_accessible_resources")
    @patch("apps.integrations.services.jira_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.jira_oauth.verify_oauth_state")
    def test_jira_callback_sets_connected_by_user(self, mock_verify, mock_exchange, mock_get_resources):
        """Test that jira_callback sets connected_by to the current user."""
        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange
        mock_exchange.return_value = {
            "access_token": "jira_test_token",
            "refresh_token": "jira_refresh_token",
            "expires_in": 3600,
        }

        # Mock single site
        mock_get_resources.return_value = [
            {"id": "cloud-id-12345", "name": "Acme", "url": "https://acme.atlassian.net"}
        ]

        self.client.force_login(self.admin)

        self.client.get(
            reverse("integrations:jira_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Get the credential
        credential = IntegrationCredential.objects.get(team=self.team, provider=IntegrationCredential.PROVIDER_JIRA)

        # connected_by should be set to the current user
        self.assertEqual(credential.connected_by, self.admin)

    @override_settings(JIRA_CLIENT_ID="test_client_id", JIRA_SECRET="test_secret")
    @patch("apps.integrations.services.jira_oauth.exchange_code_for_token")
    @patch("apps.integrations.services.jira_oauth.verify_oauth_state")
    def test_jira_callback_handles_token_exchange_error(self, mock_verify, mock_exchange):
        """Test that jira_callback handles token exchange errors gracefully."""
        from apps.integrations.services.jira_oauth import JiraOAuthError

        # Mock state verification
        mock_verify.return_value = {"team_id": self.team.id}

        # Mock token exchange error
        mock_exchange.side_effect = JiraOAuthError("Token exchange failed")

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("integrations:jira_callback"),
            {"code": "auth_code_123", "state": "valid_state"},
        )

        # Should redirect to integrations home with error
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

        # Should NOT create any integration records
        self.assertFalse(IntegrationCredential.objects.filter(team=self.team).exists())


class JiraDisconnectViewTest(TestCase):
    """Tests for jira_disconnect view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_jira_disconnect_requires_login(self):
        """Test that jira_disconnect redirects to login if user is not authenticated."""
        response = self.client.post(reverse("integrations:jira_disconnect"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_jira_disconnect_requires_team_membership(self):
        """Test that jira_disconnect returns 404 if user is not a team member."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(reverse("integrations:jira_disconnect"))

        self.assertEqual(response.status_code, 404)

    def test_jira_disconnect_requires_admin_role(self):
        """Test that jira_disconnect returns 404 for non-admin team members."""
        self.client.force_login(self.member)

        response = self.client.post(reverse("integrations:jira_disconnect"))

        self.assertEqual(response.status_code, 404)

    def test_jira_disconnect_requires_post_method(self):
        """Test that jira_disconnect only accepts POST requests."""
        # Create integration
        JiraIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        # Try GET request
        response = self.client.get(reverse("integrations:jira_disconnect"))

        # Should not allow GET
        self.assertNotEqual(response.status_code, 200)

    def test_jira_disconnect_deletes_jira_integration(self):
        """Test that jira_disconnect deletes the JiraIntegration."""
        # Create integration
        integration = JiraIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        self.client.post(reverse("integrations:jira_disconnect"))

        # JiraIntegration should be deleted
        self.assertFalse(JiraIntegration.objects.filter(pk=integration.pk).exists())

    def test_jira_disconnect_deletes_integration_credential(self):
        """Test that jira_disconnect deletes the IntegrationCredential."""
        # Create integration with credential
        integration = JiraIntegrationFactory(team=self.team)
        credential = integration.credential
        self.client.force_login(self.admin)

        self.client.post(reverse("integrations:jira_disconnect"))

        # IntegrationCredential should be deleted
        self.assertFalse(IntegrationCredential.objects.filter(pk=credential.pk).exists())

    def test_jira_disconnect_redirects_to_integrations_home(self):
        """Test that jira_disconnect redirects to integrations_home after success."""
        # Create integration
        JiraIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:jira_disconnect"))

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_jira_disconnect_shows_success_message(self):
        """Test that jira_disconnect shows success message."""
        # Create integration
        JiraIntegrationFactory(team=self.team)
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:jira_disconnect"), follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("disconnect" in str(m).lower() for m in messages))

    def test_jira_disconnect_handles_no_integration_gracefully(self):
        """Test that jira_disconnect handles case where no integration exists."""
        # No integration created
        self.client.force_login(self.admin)

        response = self.client.post(reverse("integrations:jira_disconnect"))

        # Should still redirect successfully
        self.assertEqual(response.status_code, 302)


class JiraSelectSiteViewTest(TestCase):
    """Tests for jira_select_site view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.admin = UserFactory()
        self.member = UserFactory()
        self.team.members.add(self.admin, through_defaults={"role": ROLE_ADMIN})
        self.team.members.add(self.member, through_defaults={"role": ROLE_MEMBER})
        self.client = Client()

    def test_jira_select_site_get_requires_login(self):
        """Test that jira_select_site GET requires authentication."""
        response = self.client.get(reverse("integrations:jira_select_site"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_jira_select_site_get_requires_team_membership(self):
        """Test that jira_select_site GET requires team membership."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.get(reverse("integrations:jira_select_site"))

        self.assertEqual(response.status_code, 404)

    @patch("apps.integrations.services.jira_oauth.get_accessible_resources")
    def test_jira_select_site_get_shows_site_list(self, mock_get_resources):
        """Test that jira_select_site GET displays list of accessible sites."""
        # Create credential with token
        IntegrationCredentialFactory(
            team=self.team, provider=IntegrationCredential.PROVIDER_JIRA, connected_by=self.admin
        )

        # Mock accessible resources
        mock_get_resources.return_value = [
            {"id": "cloud-id-1", "name": "Site 1", "url": "https://site1.atlassian.net"},
            {"id": "cloud-id-2", "name": "Site 2", "url": "https://site2.atlassian.net"},
        ]

        self.client.force_login(self.admin)

        response = self.client.get(reverse("integrations:jira_select_site"))

        # Should show site selection page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Site 1")
        self.assertContains(response, "Site 2")

    def test_jira_select_site_post_requires_login(self):
        """Test that jira_select_site POST requires authentication."""
        response = self.client.post(
            reverse("integrations:jira_select_site"),
            {"cloud_id": "cloud-id-1", "site_name": "Site 1", "site_url": "https://site1.atlassian.net"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_jira_select_site_post_requires_team_membership(self):
        """Test that jira_select_site POST requires team membership."""
        non_member = UserFactory()
        self.client.force_login(non_member)

        response = self.client.post(
            reverse("integrations:jira_select_site"),
            {"cloud_id": "cloud-id-1", "site_name": "Site 1", "site_url": "https://site1.atlassian.net"},
        )

        self.assertEqual(response.status_code, 404)

    def test_jira_select_site_post_creates_jira_integration(self):
        """Test that jira_select_site POST creates JiraIntegration."""
        # Create credential
        IntegrationCredentialFactory(team=self.team, provider=IntegrationCredential.PROVIDER_JIRA)

        self.client.force_login(self.admin)

        self.client.post(
            reverse("integrations:jira_select_site"),
            {
                "cloud_id": "cloud-id-12345",
                "site_name": "Acme Corp",
                "site_url": "https://acme-corp.atlassian.net",
            },
        )

        # Should create JiraIntegration
        self.assertTrue(
            JiraIntegration.objects.filter(team=self.team, cloud_id="cloud-id-12345", site_name="Acme Corp").exists()
        )

    def test_jira_select_site_post_redirects_to_integrations_home(self):
        """Test that jira_select_site POST redirects to integrations_home."""
        # Create credential
        IntegrationCredentialFactory(team=self.team, provider=IntegrationCredential.PROVIDER_JIRA)

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("integrations:jira_select_site"),
            {
                "cloud_id": "cloud-id-12345",
                "site_name": "Acme Corp",
                "site_url": "https://acme-corp.atlassian.net",
            },
        )

        # Should redirect to integrations home
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("integrations:integrations_home"))

    def test_jira_select_site_post_shows_success_message(self):
        """Test that jira_select_site POST shows success message."""
        # Create credential
        IntegrationCredentialFactory(team=self.team, provider=IntegrationCredential.PROVIDER_JIRA)

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("integrations:jira_select_site"),
            {
                "cloud_id": "cloud-id-12345",
                "site_name": "Acme Corp",
                "site_url": "https://acme-corp.atlassian.net",
            },
            follow=True,
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("success" in str(m).lower() or "connected" in str(m).lower() for m in messages))
