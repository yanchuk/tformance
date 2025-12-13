"""Tests for Jira OAuth service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.integrations.services.jira_oauth import (
    JiraOAuthError,
    create_oauth_state,
    ensure_valid_jira_token,
    exchange_code_for_token,
    get_accessible_resources,
    get_authorization_url,
    refresh_access_token,
    verify_oauth_state,
)
from apps.metrics.factories import TeamFactory


class TestOAuthStateGeneration(TestCase):
    """Tests for OAuth state parameter creation and verification."""

    def test_jira_oauth_error_can_be_raised(self):
        """Test that JiraOAuthError can be raised and caught."""
        with self.assertRaises(JiraOAuthError):
            raise JiraOAuthError("Test error")

    def test_create_oauth_state_returns_string(self):
        """Test that create_oauth_state returns a non-empty string."""
        team = TeamFactory()
        state = create_oauth_state(team.id)

        self.assertIsInstance(state, str)
        self.assertGreater(len(state), 0)

    def test_verify_oauth_state_returns_team_id(self):
        """Test that verify_oauth_state correctly decodes team_id from state."""
        team = TeamFactory()
        state = create_oauth_state(team.id)

        result = verify_oauth_state(state)

        self.assertIsInstance(result, dict)
        self.assertIn("team_id", result)
        self.assertEqual(result["team_id"], team.id)

    def test_verify_oauth_state_raises_error_for_invalid_state(self):
        """Test that verify_oauth_state raises JiraOAuthError for invalid state."""
        invalid_states = [
            "not_a_valid_state",
            "random_garbage",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
        ]

        for invalid_state in invalid_states:
            with self.subTest(invalid_state=invalid_state), self.assertRaises(JiraOAuthError):
                verify_oauth_state(invalid_state)

    def test_verify_oauth_state_raises_error_for_tampered_state(self):
        """Test that verify_oauth_state raises error if state signature is tampered."""
        team = TeamFactory()
        state = create_oauth_state(team.id)

        # Tamper with the state by modifying a character
        tampered_state = state[:-1] + ("X" if state[-1] != "X" else "Y")

        with self.assertRaises(JiraOAuthError):
            verify_oauth_state(tampered_state)

    def test_create_oauth_state_with_different_teams_produces_different_states(self):
        """Test that different team_ids produce different state strings."""
        team1 = TeamFactory()
        team2 = TeamFactory()

        state1 = create_oauth_state(team1.id)
        state2 = create_oauth_state(team2.id)

        self.assertNotEqual(state1, state2)

    def test_verify_oauth_state_roundtrip(self):
        """Test that state can be created and verified in roundtrip."""
        team = TeamFactory()
        state = create_oauth_state(team.id)
        result = verify_oauth_state(state)

        self.assertEqual(result["team_id"], team.id)


@override_settings(
    JIRA_CLIENT_ID="test_jira_client_id_123",
    JIRA_CLIENT_SECRET="test_jira_secret_456",
)
class TestAuthorizationURL(TestCase):
    """Tests for Jira authorization URL generation."""

    def test_get_authorization_url_returns_string(self):
        """Test that get_authorization_url returns a URL string."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith("https://auth.atlassian.com/authorize"))

    def test_authorization_url_includes_client_id(self):
        """Test that authorization URL includes the correct client_id."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("client_id=test_jira_client_id_123", url)

    def test_authorization_url_includes_redirect_uri(self):
        """Test that authorization URL includes the correct redirect_uri."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("redirect_uri=", url)
        # URL encoding check
        self.assertIn("http", url)

    def test_authorization_url_includes_audience(self):
        """Test that authorization URL includes audience=api.atlassian.com."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        url = get_authorization_url(team.id, redirect_uri)

        # Check for audience parameter
        self.assertIn("audience=api.atlassian.com", url)

    def test_authorization_url_includes_correct_scopes(self):
        """Test that authorization URL includes required scopes."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        url = get_authorization_url(team.id, redirect_uri)

        # Scopes can be URL encoded, so check for both forms
        self.assertIn("scope=", url)
        # Check that the URL contains the scopes (may be URL encoded)
        self.assertTrue(
            "read:jira-work" in url or "read%3Ajira-work" in url,
            "Authorization URL should contain 'read:jira-work' scope",
        )
        self.assertTrue(
            "read:jira-user" in url or "read%3Ajira-user" in url,
            "Authorization URL should contain 'read:jira-user' scope",
        )

    def test_authorization_url_includes_response_type_code(self):
        """Test that authorization URL includes response_type=code."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("response_type=code", url)

    def test_authorization_url_includes_prompt_consent(self):
        """Test that authorization URL includes prompt=consent."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("prompt=consent", url)

    def test_authorization_url_includes_state_parameter(self):
        """Test that authorization URL includes a state parameter."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("state=", url)

    def test_authorization_url_state_is_valid(self):
        """Test that the state parameter in URL can be verified."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        url = get_authorization_url(team.id, redirect_uri)

        # Extract state parameter from URL
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        state = params.get("state", [None])[0]

        self.assertIsNotNone(state)

        # Verify the state
        result = verify_oauth_state(state)
        self.assertEqual(result["team_id"], team.id)


@override_settings(
    JIRA_CLIENT_ID="test_jira_client_id_123",
    JIRA_CLIENT_SECRET="test_jira_secret_456",
)
class TestTokenExchange(TestCase):
    """Tests for exchanging OAuth code for access token."""

    @patch("apps.integrations.services.jira_oauth.requests.post")
    def test_exchange_code_for_token_returns_access_token(self, mock_post):
        """Test that exchange_code_for_token returns access_token on success."""
        # Mock successful response from Atlassian
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "refresh_token": "refresh_token_xyz",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "read:jira-work read:jira-user",
        }
        mock_post.return_value = mock_response

        code = "test_auth_code"
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        result = exchange_code_for_token(code, redirect_uri)

        self.assertIsInstance(result, dict)
        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)
        self.assertEqual(result["access_token"], "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token")
        self.assertEqual(result["refresh_token"], "refresh_token_xyz")

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # Check the URL
        self.assertEqual(call_args[0][0], "https://auth.atlassian.com/oauth/token")
        # Check the payload
        call_kwargs = call_args[1]
        self.assertEqual(call_kwargs["json"]["grant_type"], "authorization_code")
        self.assertEqual(call_kwargs["json"]["code"], code)
        self.assertEqual(call_kwargs["json"]["redirect_uri"], redirect_uri)
        self.assertEqual(call_kwargs["json"]["client_id"], "test_jira_client_id_123")
        self.assertEqual(call_kwargs["json"]["client_secret"], "test_jira_secret_456")

    @patch("apps.integrations.services.jira_oauth.requests.post")
    def test_exchange_code_for_token_handles_error_response(self, mock_post):
        """Test that exchange_code_for_token raises JiraOAuthError on error response."""
        # Mock error response from Atlassian
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "The authorization code is invalid or has expired.",
        }
        mock_post.return_value = mock_response

        code = "invalid_code"
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        with self.assertRaises(JiraOAuthError) as context:
            exchange_code_for_token(code, redirect_uri)

        self.assertIn("invalid_grant", str(context.exception))

    @patch("apps.integrations.services.jira_oauth.requests.post")
    def test_exchange_code_for_token_handles_network_error(self, mock_post):
        """Test that exchange_code_for_token raises JiraOAuthError on network error."""
        # Mock network error
        mock_post.side_effect = Exception("Network timeout")

        code = "test_code"
        redirect_uri = "http://localhost:8000/integrations/jira/callback"

        with self.assertRaises(JiraOAuthError):
            exchange_code_for_token(code, redirect_uri)

    @patch("apps.integrations.services.jira_oauth.requests.post")
    def test_exchange_code_for_token_sends_correct_headers(self, mock_post):
        """Test that exchange_code_for_token sends Accept: application/json header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "token_123",
            "refresh_token": "refresh_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        code = "test_code"
        redirect_uri = "http://localhost:8000/callback"

        exchange_code_for_token(code, redirect_uri)

        # Verify headers include Accept: application/json
        call_kwargs = mock_post.call_args[1]
        self.assertIn("headers", call_kwargs)
        self.assertEqual(call_kwargs["headers"]["Accept"], "application/json")


@override_settings(
    JIRA_CLIENT_ID="test_jira_client_id_123",
    JIRA_CLIENT_SECRET="test_jira_secret_456",
)
class TestRefreshAccessToken(TestCase):
    """Tests for refreshing Jira access token."""

    @patch("apps.integrations.services.jira_oauth.requests.post")
    def test_refresh_access_token_returns_new_tokens(self, mock_post):
        """Test that refresh_access_token returns new access and refresh tokens."""
        # Mock successful response from Atlassian
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token_xyz",
            "refresh_token": "new_refresh_token_abc",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "read:jira-work read:jira-user",
        }
        mock_post.return_value = mock_response

        refresh_token = "old_refresh_token"

        result = refresh_access_token(refresh_token)

        self.assertIsInstance(result, dict)
        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)
        self.assertEqual(result["access_token"], "new_access_token_xyz")
        self.assertEqual(result["refresh_token"], "new_refresh_token_abc")

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # Check the URL
        self.assertEqual(call_args[0][0], "https://auth.atlassian.com/oauth/token")
        # Check the payload
        call_kwargs = call_args[1]
        self.assertEqual(call_kwargs["json"]["grant_type"], "refresh_token")
        self.assertEqual(call_kwargs["json"]["refresh_token"], refresh_token)
        self.assertEqual(call_kwargs["json"]["client_id"], "test_jira_client_id_123")
        self.assertEqual(call_kwargs["json"]["client_secret"], "test_jira_secret_456")

    @patch("apps.integrations.services.jira_oauth.requests.post")
    def test_refresh_access_token_handles_error_response(self, mock_post):
        """Test that refresh_access_token raises JiraOAuthError on error response."""
        # Mock error response from Atlassian
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "The refresh token is invalid or has expired.",
        }
        mock_post.return_value = mock_response

        refresh_token = "invalid_refresh_token"

        with self.assertRaises(JiraOAuthError) as context:
            refresh_access_token(refresh_token)

        self.assertIn("invalid_grant", str(context.exception))

    @patch("apps.integrations.services.jira_oauth.requests.post")
    def test_refresh_access_token_handles_network_error(self, mock_post):
        """Test that refresh_access_token raises JiraOAuthError on network error."""
        # Mock network error
        mock_post.side_effect = Exception("Connection refused")

        refresh_token = "test_refresh_token"

        with self.assertRaises(JiraOAuthError):
            refresh_access_token(refresh_token)

    @patch("apps.integrations.services.jira_oauth.requests.post")
    def test_refresh_access_token_sends_correct_headers(self, mock_post):
        """Test that refresh_access_token sends Accept: application/json header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token_123",
            "refresh_token": "new_refresh_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        refresh_token = "test_refresh_token"

        refresh_access_token(refresh_token)

        # Verify headers include Accept: application/json
        call_kwargs = mock_post.call_args[1]
        self.assertIn("headers", call_kwargs)
        self.assertEqual(call_kwargs["headers"]["Accept"], "application/json")


@override_settings(
    JIRA_CLIENT_ID="test_jira_client_id_123",
    JIRA_CLIENT_SECRET="test_jira_secret_456",
)
class TestGetAccessibleResources(TestCase):
    """Tests for fetching accessible Jira resources/sites."""

    @patch("apps.integrations.services.jira_oauth.requests.get")
    def test_get_accessible_resources_returns_list(self, mock_get):
        """Test that get_accessible_resources returns a list of accessible sites."""
        # Mock successful response from Atlassian
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "site-1-id",
                "name": "Acme Corp Jira",
                "url": "https://acme-corp.atlassian.net",
                "scopes": ["read:jira-work", "read:jira-user"],
                "avatarUrl": "https://site-avatar.png",
            },
            {
                "id": "site-2-id",
                "name": "Test Jira",
                "url": "https://test-org.atlassian.net",
                "scopes": ["read:jira-work", "read:jira-user"],
                "avatarUrl": "https://site-avatar-2.png",
            },
        ]
        mock_get.return_value = mock_response

        access_token = "test_access_token"

        result = get_accessible_resources(access_token)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "site-1-id")
        self.assertEqual(result[0]["name"], "Acme Corp Jira")
        self.assertEqual(result[0]["url"], "https://acme-corp.atlassian.net")
        self.assertEqual(result[1]["id"], "site-2-id")

        # Verify the request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        # Check the URL
        self.assertEqual(call_args[0][0], "https://api.atlassian.com/oauth/token/accessible-resources")
        # Check the headers include authorization
        call_kwargs = call_args[1]
        self.assertIn("headers", call_kwargs)
        self.assertEqual(call_kwargs["headers"]["Authorization"], f"Bearer {access_token}")
        self.assertEqual(call_kwargs["headers"]["Accept"], "application/json")

    @patch("apps.integrations.services.jira_oauth.requests.get")
    def test_get_accessible_resources_returns_empty_list_when_no_sites(self, mock_get):
        """Test that get_accessible_resources returns empty list when user has no accessible sites."""
        # Mock successful response with no sites
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "test_access_token"

        result = get_accessible_resources(access_token)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("apps.integrations.services.jira_oauth.requests.get")
    def test_get_accessible_resources_handles_401_unauthorized(self, mock_get):
        """Test that get_accessible_resources raises JiraOAuthError on 401 unauthorized."""
        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "unauthorized",
            "error_description": "The access token is invalid or has expired.",
        }
        mock_get.return_value = mock_response

        access_token = "invalid_token"

        with self.assertRaises(JiraOAuthError) as context:
            get_accessible_resources(access_token)

        self.assertIn("401", str(context.exception))

    @patch("apps.integrations.services.jira_oauth.requests.get")
    def test_get_accessible_resources_handles_network_error(self, mock_get):
        """Test that get_accessible_resources raises JiraOAuthError on network error."""
        # Mock network error
        mock_get.side_effect = Exception("DNS resolution failed")

        access_token = "test_token"

        with self.assertRaises(JiraOAuthError):
            get_accessible_resources(access_token)

    @patch("apps.integrations.services.jira_oauth.requests.get")
    def test_get_accessible_resources_sends_bearer_token(self, mock_get):
        """Test that get_accessible_resources sends Bearer token in Authorization header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "my_access_token_xyz"

        get_accessible_resources(access_token)

        # Verify Authorization header
        call_kwargs = mock_get.call_args[1]
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer my_access_token_xyz")


@override_settings(
    JIRA_CLIENT_ID="test_jira_client_id_123",
    JIRA_CLIENT_SECRET="test_jira_secret_456",
)
class TestEnsureValidJiraToken(TestCase):
    """Tests for ensuring valid Jira token with automatic refresh."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from django.utils import timezone

        from apps.integrations.factories import IntegrationCredentialFactory

        # EncryptedTextField auto-encrypts, so use plaintext values
        # Create credential with valid token (expires in 10 minutes)
        self.valid_credential = IntegrationCredentialFactory(
            provider="jira",
            access_token="valid_access_token_123",
            refresh_token="valid_refresh_token_456",
            token_expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )

        # Create credential with expiring soon token (expires in 3 minutes)
        self.expiring_credential = IntegrationCredentialFactory(
            provider="jira",
            access_token="expiring_access_token_789",
            refresh_token="expiring_refresh_token_012",
            token_expires_at=timezone.now() + timezone.timedelta(minutes=3),
        )

        # Create credential with expired token
        self.expired_credential = IntegrationCredentialFactory(
            provider="jira",
            access_token="expired_access_token_abc",
            refresh_token="expired_refresh_token_def",
            token_expires_at=timezone.now() - timezone.timedelta(minutes=5),
        )

        # Create credential with no expiration date
        self.no_expiry_credential = IntegrationCredentialFactory(
            provider="jira",
            access_token="no_expiry_access_token_xyz",
            refresh_token="no_expiry_refresh_token_uvw",
            token_expires_at=None,
        )

    def test_returns_decrypted_token_when_valid(self):
        """Test that ensure_valid_jira_token returns decrypted token if not expired."""

        # Act
        result = ensure_valid_jira_token(self.valid_credential)

        # Assert
        self.assertEqual(result, "valid_access_token_123")

    def test_refreshes_token_when_expired(self):
        """Test that ensure_valid_jira_token refreshes token when expired."""

        # Act
        with patch("apps.integrations.services.jira_oauth.refresh_access_token") as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token_123",
                "refresh_token": "new_refresh_token_456",
                "expires_in": 3600,
            }

            result = ensure_valid_jira_token(self.expired_credential)

            # Assert
            mock_refresh.assert_called_once()
            self.assertEqual(result, "new_access_token_123")

    def test_refreshes_token_when_expiring_within_5_minutes(self):
        """Test that ensure_valid_jira_token refreshes token when expiring within 5 minutes."""

        # Act
        with patch("apps.integrations.services.jira_oauth.refresh_access_token") as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token_789",
                "refresh_token": "new_refresh_token_012",
                "expires_in": 3600,
            }

            result = ensure_valid_jira_token(self.expiring_credential)

            # Assert - refresh should be called because token expires in 3 minutes
            mock_refresh.assert_called_once()
            self.assertEqual(result, "new_access_token_789")

    @patch("apps.integrations.services.jira_oauth.refresh_access_token")
    def test_updates_credential_with_new_tokens_after_refresh(self, mock_refresh):
        """Test that ensure_valid_jira_token updates credential with new tokens after refresh."""
        # Arrange
        mock_refresh.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "expires_in": 3600,
        }

        # Act
        ensure_valid_jira_token(self.expired_credential)

        # Assert - reload credential from database
        self.expired_credential.refresh_from_db()

        # Check that tokens were updated (EncryptedTextField auto-decrypts)
        self.assertEqual(self.expired_credential.access_token, "refreshed_access_token")
        self.assertEqual(self.expired_credential.refresh_token, "refreshed_refresh_token")

    @patch("apps.integrations.services.jira_oauth.refresh_access_token")
    def test_updates_token_expires_at_after_refresh(self, mock_refresh):
        """Test that ensure_valid_jira_token updates token_expires_at after refresh."""
        from django.utils import timezone

        # Arrange
        mock_refresh.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "expires_in": 3600,
        }

        old_expiry = self.expired_credential.token_expires_at

        # Act
        ensure_valid_jira_token(self.expired_credential)

        # Assert - reload credential from database
        self.expired_credential.refresh_from_db()

        # Check that expiry was updated (should be ~1 hour from now)
        self.assertIsNotNone(self.expired_credential.token_expires_at)
        self.assertGreater(self.expired_credential.token_expires_at, timezone.now())
        self.assertNotEqual(self.expired_credential.token_expires_at, old_expiry)

        # Check it's approximately 1 hour from now (within 1 minute tolerance)
        expected_expiry = timezone.now() + timezone.timedelta(seconds=3600)
        time_diff = abs((self.expired_credential.token_expires_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60, "Token expiry should be approximately 1 hour from now")

    @patch("apps.integrations.services.jira_oauth.refresh_access_token")
    def test_raises_jira_oauth_error_if_refresh_fails(self, mock_refresh):
        """Test that ensure_valid_jira_token raises JiraOAuthError if refresh fails."""

        # Arrange - mock refresh failure
        mock_refresh.side_effect = JiraOAuthError("Token refresh failed: invalid_grant")

        # Act & Assert
        with self.assertRaises(JiraOAuthError) as context:
            ensure_valid_jira_token(self.expired_credential)

        self.assertIn("invalid_grant", str(context.exception))

    @patch("apps.integrations.services.jira_oauth.refresh_access_token")
    def test_handles_credential_with_no_token_expires_at(self, mock_refresh):
        """Test that ensure_valid_jira_token assumes refresh needed when token_expires_at is None."""

        # Arrange
        mock_refresh.return_value = {
            "access_token": "new_token_from_none_expiry",
            "refresh_token": "new_refresh_from_none_expiry",
            "expires_in": 3600,
        }

        # Act
        result = ensure_valid_jira_token(self.no_expiry_credential)

        # Assert - should refresh because we don't know if it's valid
        mock_refresh.assert_called_once()
        self.assertEqual(result, "new_token_from_none_expiry")
