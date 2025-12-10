"""Tests for GitHub OAuth service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.integrations.services.github_oauth import (
    GitHubOAuthError,
    create_oauth_state,
    exchange_code_for_token,
    get_authenticated_user,
    get_authorization_url,
    get_user_organizations,
    verify_oauth_state,
)
from apps.metrics.factories import TeamFactory


class TestOAuthStateGeneration(TestCase):
    """Tests for OAuth state parameter creation and verification."""

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
        """Test that verify_oauth_state raises GitHubOAuthError for invalid state."""
        invalid_states = [
            "not_a_valid_state",
            "random_garbage",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
        ]

        for invalid_state in invalid_states:
            with self.subTest(invalid_state=invalid_state), self.assertRaises(GitHubOAuthError):
                verify_oauth_state(invalid_state)

    def test_verify_oauth_state_raises_error_for_tampered_state(self):
        """Test that verify_oauth_state raises error if state signature is tampered."""
        team = TeamFactory()
        state = create_oauth_state(team.id)

        # Tamper with the state by modifying a character
        tampered_state = state[:-1] + ("X" if state[-1] != "X" else "Y")

        with self.assertRaises(GitHubOAuthError):
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
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestAuthorizationURL(TestCase):
    """Tests for GitHub authorization URL generation."""

    def test_get_authorization_url_returns_string(self):
        """Test that get_authorization_url returns a URL string."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/github/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith("https://github.com/login/oauth/authorize"))

    def test_authorization_url_includes_client_id(self):
        """Test that authorization URL includes the correct client_id."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/github/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("client_id=test_client_id_123", url)

    def test_authorization_url_includes_redirect_uri(self):
        """Test that authorization URL includes the correct redirect_uri."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/github/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("redirect_uri=", url)
        # URL encoding check
        self.assertIn("http", url)

    def test_authorization_url_includes_correct_scopes(self):
        """Test that authorization URL includes required scopes: read:org, repo, read:user."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/github/callback"

        url = get_authorization_url(team.id, redirect_uri)

        # Scopes can be URL encoded, so check for both forms
        self.assertIn("scope=", url)
        # Check that the URL contains the scopes (may be URL encoded)
        self.assertTrue(
            "read:org" in url or "read%3Aorg" in url,
            "Authorization URL should contain 'read:org' scope",
        )
        self.assertIn("repo", url)
        self.assertTrue(
            "read:user" in url or "read%3Auser" in url,
            "Authorization URL should contain 'read:user' scope",
        )

    def test_authorization_url_includes_state_parameter(self):
        """Test that authorization URL includes a state parameter."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/github/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("state=", url)

    def test_authorization_url_state_is_valid(self):
        """Test that the state parameter in URL can be verified."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/github/callback"

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
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestTokenExchange(TestCase):
    """Tests for exchanging OAuth code for access token."""

    @patch("apps.integrations.services.github_oauth.requests.post")
    def test_exchange_code_for_token_returns_access_token(self, mock_post):
        """Test that exchange_code_for_token returns access_token on success."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "gho_test_token_123456",
            "token_type": "bearer",
            "scope": "read:org,repo,read:user",
        }
        mock_post.return_value = mock_response

        code = "test_auth_code"
        redirect_uri = "http://localhost:8000/integrations/github/callback"

        result = exchange_code_for_token(code, redirect_uri)

        self.assertIsInstance(result, dict)
        self.assertIn("access_token", result)
        self.assertEqual(result["access_token"], "gho_test_token_123456")

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["json"]["code"], code)
        self.assertEqual(call_kwargs["json"]["redirect_uri"], redirect_uri)
        self.assertEqual(call_kwargs["json"]["client_id"], "test_client_id_123")
        self.assertEqual(call_kwargs["json"]["client_secret"], "test_client_secret_456")

    @patch("apps.integrations.services.github_oauth.requests.post")
    def test_exchange_code_for_token_handles_error_response(self, mock_post):
        """Test that exchange_code_for_token raises GitHubOAuthError on error response."""
        # Mock error response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }
        mock_post.return_value = mock_response

        code = "invalid_code"
        redirect_uri = "http://localhost:8000/integrations/github/callback"

        with self.assertRaises(GitHubOAuthError) as context:
            exchange_code_for_token(code, redirect_uri)

        self.assertIn("bad_verification_code", str(context.exception))

    @patch("apps.integrations.services.github_oauth.requests.post")
    def test_exchange_code_for_token_handles_network_error(self, mock_post):
        """Test that exchange_code_for_token raises GitHubOAuthError on network error."""
        # Mock network error
        mock_post.side_effect = Exception("Network timeout")

        code = "test_code"
        redirect_uri = "http://localhost:8000/integrations/github/callback"

        with self.assertRaises(GitHubOAuthError):
            exchange_code_for_token(code, redirect_uri)

    @patch("apps.integrations.services.github_oauth.requests.post")
    def test_exchange_code_for_token_sends_correct_headers(self, mock_post):
        """Test that exchange_code_for_token sends Accept: application/json header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "token_123"}
        mock_post.return_value = mock_response

        code = "test_code"
        redirect_uri = "http://localhost:8000/callback"

        exchange_code_for_token(code, redirect_uri)

        # Verify headers include Accept: application/json
        call_kwargs = mock_post.call_args[1]
        self.assertIn("headers", call_kwargs)
        self.assertEqual(call_kwargs["headers"]["Accept"], "application/json")


@override_settings(
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestGetAuthenticatedUser(TestCase):
    """Tests for fetching authenticated GitHub user data."""

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_authenticated_user_returns_user_data(self, mock_get):
        """Test that get_authenticated_user returns user data from GitHub API."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "testuser",
            "id": 12345,
            "email": "testuser@example.com",
            "name": "Test User",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"

        result = get_authenticated_user(access_token)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["login"], "testuser")
        self.assertEqual(result["id"], 12345)
        self.assertEqual(result["email"], "testuser@example.com")

        # Verify the request was made with correct Authorization header
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "https://api.github.com/user")
        self.assertEqual(call_args[1]["headers"]["Authorization"], "token gho_test_token")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_authenticated_user_handles_api_error(self, mock_get):
        """Test that get_authenticated_user raises GitHubOAuthError on API error."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "message": "Bad credentials",
        }
        mock_get.return_value = mock_response

        access_token = "invalid_token"

        with self.assertRaises(GitHubOAuthError) as context:
            get_authenticated_user(access_token)

        self.assertIn("401", str(context.exception))

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_authenticated_user_sends_correct_headers(self, mock_get):
        """Test that get_authenticated_user sends correct headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "user", "id": 123}
        mock_get.return_value = mock_response

        access_token = "test_token"

        get_authenticated_user(access_token)

        # Verify headers
        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs["headers"]
        self.assertEqual(headers["Authorization"], "token test_token")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")


@override_settings(
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestGetUserOrganizations(TestCase):
    """Tests for fetching user's GitHub organizations."""

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_organizations_returns_list(self, mock_get):
        """Test that get_user_organizations returns a list of organizations."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "login": "acme-corp",
                "id": 1001,
                "description": "Acme Corporation",
                "avatar_url": "https://avatars.githubusercontent.com/u/1001",
            },
            {
                "login": "test-org",
                "id": 1002,
                "description": "Test Organization",
                "avatar_url": "https://avatars.githubusercontent.com/u/1002",
            },
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token"

        result = get_user_organizations(access_token)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["login"], "acme-corp")
        self.assertEqual(result[1]["login"], "test-org")

        # Verify the request
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "https://api.github.com/user/orgs")
        self.assertEqual(call_args[1]["headers"]["Authorization"], "token gho_test_token")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_organizations_returns_empty_list_when_no_orgs(self, mock_get):
        """Test that get_user_organizations returns empty list when user has no orgs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "gho_test_token"

        result = get_user_organizations(access_token)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_organizations_handles_api_error(self, mock_get):
        """Test that get_user_organizations raises GitHubOAuthError on API error."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "Forbidden",
        }
        mock_get.return_value = mock_response

        access_token = "invalid_token"

        with self.assertRaises(GitHubOAuthError) as context:
            get_user_organizations(access_token)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_organizations_sends_correct_headers(self, mock_get):
        """Test that get_user_organizations sends correct headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "test_token"

        get_user_organizations(access_token)

        # Verify headers
        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs["headers"]
        self.assertEqual(headers["Authorization"], "token test_token")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")
