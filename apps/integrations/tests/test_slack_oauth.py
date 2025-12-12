"""Tests for Slack OAuth service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.integrations.services.oauth_utils import create_oauth_state
from apps.integrations.services.slack_oauth import (
    SlackOAuthError,
    exchange_code_for_token,
    get_authorization_url,
    verify_slack_oauth_state,
)
from apps.metrics.factories import TeamFactory


class TestOAuthStateGeneration(TestCase):
    """Tests for OAuth state parameter creation and verification."""

    def test_slack_oauth_error_can_be_raised(self):
        """Test that SlackOAuthError can be raised and caught."""
        with self.assertRaises(SlackOAuthError):
            raise SlackOAuthError("Test error")

    def test_create_oauth_state_returns_string(self):
        """Test that create_oauth_state returns a non-empty string."""
        team = TeamFactory()
        state = create_oauth_state(team.id)

        self.assertIsInstance(state, str)
        self.assertGreater(len(state), 0)

    def test_verify_oauth_state_returns_team_id(self):
        """Test that verify_slack_oauth_state correctly decodes team_id from state."""
        team = TeamFactory()
        state = create_oauth_state(team.id)

        result = verify_slack_oauth_state(state)

        self.assertIsInstance(result, dict)
        self.assertIn("team_id", result)
        self.assertEqual(result["team_id"], team.id)

    def test_verify_oauth_state_raises_error_for_invalid_state(self):
        """Test that verify_slack_oauth_state raises SlackOAuthError for invalid state."""
        invalid_states = [
            "not_a_valid_state",
            "random_garbage",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
        ]

        for invalid_state in invalid_states:
            with self.subTest(invalid_state=invalid_state), self.assertRaises(SlackOAuthError):
                verify_slack_oauth_state(invalid_state)

    def test_verify_oauth_state_raises_error_for_tampered_state(self):
        """Test that verify_slack_oauth_state raises error if state signature is tampered."""
        team = TeamFactory()
        state = create_oauth_state(team.id)

        # Tamper with the state by modifying a character
        tampered_state = state[:-1] + ("X" if state[-1] != "X" else "Y")

        with self.assertRaises(SlackOAuthError):
            verify_slack_oauth_state(tampered_state)


@override_settings(
    SLACK_CLIENT_ID="test_slack_client_id_123",
    SLACK_CLIENT_SECRET="test_slack_secret_456",
)
class TestAuthorizationURL(TestCase):
    """Tests for Slack authorization URL generation."""

    def test_authorization_url_includes_client_id(self):
        """Test that authorization URL includes the correct client_id."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/slack/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("client_id=test_slack_client_id_123", url)

    def test_authorization_url_includes_correct_scopes(self):
        """Test that authorization URL includes required scopes."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/slack/callback"

        url = get_authorization_url(team.id, redirect_uri)

        # Scopes can be URL encoded, so check for both forms
        self.assertIn("scope=", url)
        # Check that the URL contains the scopes (may be URL encoded)
        self.assertTrue(
            "chat:write" in url or "chat%3Awrite" in url,
            "Authorization URL should contain 'chat:write' scope",
        )
        self.assertTrue(
            "users:read" in url or "users%3Aread" in url,
            "Authorization URL should contain 'users:read' scope",
        )
        self.assertTrue(
            "users:read.email" in url or "users%3Aread.email" in url,
            "Authorization URL should contain 'users:read.email' scope",
        )

    def test_authorization_url_includes_redirect_uri(self):
        """Test that authorization URL includes the correct redirect_uri."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/slack/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("redirect_uri=", url)
        # URL encoding check
        self.assertIn("http", url)

    def test_authorization_url_includes_state_parameter(self):
        """Test that authorization URL includes a state parameter."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/slack/callback"

        url = get_authorization_url(team.id, redirect_uri)

        self.assertIn("state=", url)

    def test_authorization_url_state_is_valid(self):
        """Test that the state parameter in URL can be verified."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/slack/callback"

        url = get_authorization_url(team.id, redirect_uri)

        # Extract state parameter from URL
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        state = params.get("state", [None])[0]

        self.assertIsNotNone(state)

        # Verify the state
        result = verify_slack_oauth_state(state)
        self.assertEqual(result["team_id"], team.id)


@override_settings(
    SLACK_CLIENT_ID="test_slack_client_id_123",
    SLACK_CLIENT_SECRET="test_slack_secret_456",
)
class TestTokenExchange(TestCase):
    """Tests for exchanging OAuth code for access token."""

    @patch("apps.integrations.services.slack_oauth.requests.post")
    def test_exchange_code_for_token_returns_access_token(self, mock_post):
        """Test that exchange_code_for_token returns access_token on success."""
        # Mock successful response from Slack
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "access_token": "xoxb-test-token-123456",
            "bot_user_id": "U12345678",
            "team": {
                "id": "T12345678",
                "name": "Test Workspace",
            },
            "authed_user": {
                "id": "U87654321",
            },
        }
        mock_post.return_value = mock_response

        code = "test_auth_code"
        redirect_uri = "http://localhost:8000/integrations/slack/callback"

        result = exchange_code_for_token(code, redirect_uri)

        self.assertIsInstance(result, dict)
        self.assertIn("access_token", result)
        self.assertEqual(result["access_token"], "xoxb-test-token-123456")

    @patch("apps.integrations.services.slack_oauth.requests.post")
    def test_exchange_code_for_token_returns_bot_user_id(self, mock_post):
        """Test that exchange_code_for_token returns bot_user_id."""
        # Mock successful response from Slack
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "access_token": "xoxb-test-token-123456",
            "bot_user_id": "U12345678",
            "team": {
                "id": "T12345678",
                "name": "Test Workspace",
            },
        }
        mock_post.return_value = mock_response

        code = "test_auth_code"
        redirect_uri = "http://localhost:8000/integrations/slack/callback"

        result = exchange_code_for_token(code, redirect_uri)

        self.assertIn("bot_user_id", result)
        self.assertEqual(result["bot_user_id"], "U12345678")

    @patch("apps.integrations.services.slack_oauth.requests.post")
    def test_exchange_code_for_token_returns_workspace_info(self, mock_post):
        """Test that exchange_code_for_token returns workspace info."""
        # Mock successful response from Slack
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "access_token": "xoxb-test-token-123456",
            "bot_user_id": "U12345678",
            "team": {
                "id": "T12345678",
                "name": "Test Workspace",
            },
        }
        mock_post.return_value = mock_response

        code = "test_auth_code"
        redirect_uri = "http://localhost:8000/integrations/slack/callback"

        result = exchange_code_for_token(code, redirect_uri)

        self.assertIn("team", result)
        self.assertEqual(result["team"]["id"], "T12345678")
        self.assertEqual(result["team"]["name"], "Test Workspace")

    @patch("apps.integrations.services.slack_oauth.requests.post")
    def test_exchange_code_for_token_handles_api_error(self, mock_post):
        """Test that exchange_code_for_token raises SlackOAuthError on API error."""
        # Mock error response from Slack
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "error": "invalid_code",
        }
        mock_post.return_value = mock_response

        code = "invalid_code"
        redirect_uri = "http://localhost:8000/integrations/slack/callback"

        with self.assertRaises(SlackOAuthError) as context:
            exchange_code_for_token(code, redirect_uri)

        self.assertIn("invalid_code", str(context.exception))
