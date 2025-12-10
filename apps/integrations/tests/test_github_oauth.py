"""Tests for GitHub OAuth service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.integrations.services.github_oauth import (
    GitHubOAuthError,
    create_oauth_state,
    exchange_code_for_token,
    get_authenticated_user,
    get_authorization_url,
    get_organization_members,
    get_user_details,
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


@override_settings(
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestGetOrganizationMembers(TestCase):
    """Tests for fetching GitHub organization members."""

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_returns_list(self, mock_get):
        """Test that get_organization_members returns a list of members."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "login": "user1",
                "id": 1001,
                "avatar_url": "https://avatars.githubusercontent.com/u/1001",
                "type": "User",
            },
            {
                "login": "user2",
                "id": 1002,
                "avatar_url": "https://avatars.githubusercontent.com/u/1002",
                "type": "User",
            },
            {
                "login": "bot1",
                "id": 1003,
                "avatar_url": "https://avatars.githubusercontent.com/u/1003",
                "type": "Bot",
            },
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        org_slug = "acme-corp"

        result = get_organization_members(access_token, org_slug)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["login"], "user1")
        self.assertEqual(result[1]["id"], 1002)
        self.assertEqual(result[2]["type"], "Bot")

        # Verify the request
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "https://api.github.com/orgs/acme-corp/members")
        self.assertEqual(call_args[1]["headers"]["Authorization"], "token gho_test_token")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_each_member_has_required_fields(self, mock_get):
        """Test that each member has required fields: id, login, avatar_url, type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "login": "testuser",
                "id": 12345,
                "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                "type": "User",
                "site_admin": False,
            }
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        org_slug = "test-org"

        result = get_organization_members(access_token, org_slug)

        self.assertEqual(len(result), 1)
        member = result[0]
        self.assertIn("id", member)
        self.assertIn("login", member)
        self.assertIn("avatar_url", member)
        self.assertIn("type", member)

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_returns_empty_list_when_no_members(self, mock_get):
        """Test that get_organization_members returns empty list for org with no members."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        org_slug = "empty-org"

        result = get_organization_members(access_token, org_slug)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_raises_error_on_api_failure(self, mock_get):
        """Test that get_organization_members raises GitHubOAuthError on API error."""
        # Mock error response (e.g., 404 org not found, 403 no permission)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Not Found",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        org_slug = "nonexistent-org"

        with self.assertRaises(GitHubOAuthError) as context:
            get_organization_members(access_token, org_slug)

        self.assertIn("404", str(context.exception))

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_raises_error_on_403_forbidden(self, mock_get):
        """Test that get_organization_members raises GitHubOAuthError when access is forbidden."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "Forbidden",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        org_slug = "private-org"

        with self.assertRaises(GitHubOAuthError) as context:
            get_organization_members(access_token, org_slug)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_sends_correct_headers(self, mock_get):
        """Test that get_organization_members sends correct headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "test_token_xyz"
        org_slug = "my-org"

        get_organization_members(access_token, org_slug)

        # Verify headers
        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs["headers"]
        self.assertEqual(headers["Authorization"], "token test_token_xyz")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_uses_correct_endpoint(self, mock_get):
        """Test that get_organization_members uses correct API endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        org_slug = "my-test-org"

        get_organization_members(access_token, org_slug)

        # Verify the correct endpoint is called
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "https://api.github.com/orgs/my-test-org/members")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_handles_pagination_with_next_link(self, mock_get):
        """Test that get_organization_members fetches all pages when Link header has next relation."""
        # Mock first page response with Link header pointing to page 2
        mock_response_page1 = MagicMock()
        mock_response_page1.status_code = 200
        mock_response_page1.headers = {
            "Link": '<https://api.github.com/orgs/acme-corp/members?page=2>; rel="next", '
            '<https://api.github.com/orgs/acme-corp/members?page=3>; rel="last"'
        }
        mock_response_page1.json.return_value = [
            {
                "login": "user1",
                "id": 1001,
                "avatar_url": "https://avatars.githubusercontent.com/u/1001",
                "type": "User",
            },
            {
                "login": "user2",
                "id": 1002,
                "avatar_url": "https://avatars.githubusercontent.com/u/1002",
                "type": "User",
            },
        ]

        # Mock second page response with Link header pointing to page 3
        mock_response_page2 = MagicMock()
        mock_response_page2.status_code = 200
        mock_response_page2.headers = {
            "Link": '<https://api.github.com/orgs/acme-corp/members?page=3>; rel="next", '
            '<https://api.github.com/orgs/acme-corp/members?page=3>; rel="last"'
        }
        mock_response_page2.json.return_value = [
            {
                "login": "user3",
                "id": 1003,
                "avatar_url": "https://avatars.githubusercontent.com/u/1003",
                "type": "User",
            },
        ]

        # Mock third page response with no next link (last page)
        mock_response_page3 = MagicMock()
        mock_response_page3.status_code = 200
        mock_response_page3.headers = {
            "Link": '<https://api.github.com/orgs/acme-corp/members?page=1>; rel="first", '
            '<https://api.github.com/orgs/acme-corp/members?page=2>; rel="prev"'
        }
        mock_response_page3.json.return_value = [
            {
                "login": "user4",
                "id": 1004,
                "avatar_url": "https://avatars.githubusercontent.com/u/1004",
                "type": "User",
            },
        ]

        # Set up mock to return different responses for each call
        mock_get.side_effect = [mock_response_page1, mock_response_page2, mock_response_page3]

        access_token = "gho_test_token"
        org_slug = "acme-corp"

        result = get_organization_members(access_token, org_slug)

        # Verify all pages were fetched and combined
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4, "Should return all members from all pages combined")
        self.assertEqual(result[0]["login"], "user1")
        self.assertEqual(result[1]["login"], "user2")
        self.assertEqual(result[2]["login"], "user3")
        self.assertEqual(result[3]["login"], "user4")

        # Verify requests.get was called 3 times (for 3 pages)
        self.assertEqual(mock_get.call_count, 3, "Should make 3 API requests for 3 pages")

        # Verify first call was to the base endpoint
        first_call_args = mock_get.call_args_list[0]
        self.assertEqual(first_call_args[0][0], "https://api.github.com/orgs/acme-corp/members")

        # Verify subsequent calls used the URLs from Link headers
        second_call_args = mock_get.call_args_list[1]
        self.assertEqual(second_call_args[0][0], "https://api.github.com/orgs/acme-corp/members?page=2")

        third_call_args = mock_get.call_args_list[2]
        self.assertEqual(third_call_args[0][0], "https://api.github.com/orgs/acme-corp/members?page=3")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_stops_pagination_when_no_next_link(self, mock_get):
        """Test that get_organization_members stops fetching when there's no next link (last page)."""
        # Mock single page response with no next link
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Link": '<https://api.github.com/orgs/small-org/members?page=1>; rel="first"'}
        mock_response.json.return_value = [
            {
                "login": "user1",
                "id": 1001,
                "avatar_url": "https://avatars.githubusercontent.com/u/1001",
                "type": "User",
            },
            {
                "login": "user2",
                "id": 1002,
                "avatar_url": "https://avatars.githubusercontent.com/u/1002",
                "type": "User",
            },
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        org_slug = "small-org"

        result = get_organization_members(access_token, org_slug)

        # Verify only one request was made
        self.assertEqual(mock_get.call_count, 1, "Should only make 1 API request when no next link")

        # Verify results are correct
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["login"], "user1")
        self.assertEqual(result[1]["login"], "user2")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_handles_response_without_link_header(self, mock_get):
        """Test that get_organization_members handles responses without Link header (single page)."""
        # Mock response with no Link header at all
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}  # No Link header
        mock_response.json.return_value = [
            {
                "login": "user1",
                "id": 1001,
                "avatar_url": "https://avatars.githubusercontent.com/u/1001",
                "type": "User",
            },
        ]
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        org_slug = "tiny-org"

        result = get_organization_members(access_token, org_slug)

        # Verify only one request was made
        self.assertEqual(mock_get.call_count, 1, "Should only make 1 API request when no Link header")

        # Verify results are correct
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["login"], "user1")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_organization_members_fetches_all_pages_for_large_org(self, mock_get):
        """Test that get_organization_members fetches all pages for large organizations (30+ members)."""
        # Simulate a large org with 5 pages (30 members each except last page)
        responses = []
        all_members = []

        for page in range(1, 6):
            mock_response = MagicMock()
            mock_response.status_code = 200

            # Create members for this page
            page_members = []
            members_on_page = 30 if page < 5 else 15  # Last page has 15 members
            for i in range(members_on_page):
                member_num = (page - 1) * 30 + i + 1
                member = {
                    "login": f"user{member_num}",
                    "id": 1000 + member_num,
                    "avatar_url": f"https://avatars.githubusercontent.com/u/{1000 + member_num}",
                    "type": "User",
                }
                page_members.append(member)
                all_members.append(member)

            mock_response.json.return_value = page_members

            # Add Link header (no next for last page)
            if page < 5:
                mock_response.headers = {
                    "Link": f'<https://api.github.com/orgs/big-org/members?page={page + 1}>; rel="next", '
                    '<https://api.github.com/orgs/big-org/members?page=5>; rel="last"'
                }
            else:
                mock_response.headers = {
                    "Link": '<https://api.github.com/orgs/big-org/members?page=1>; rel="first", '
                    '<https://api.github.com/orgs/big-org/members?page=4>; rel="prev"'
                }

            responses.append(mock_response)

        mock_get.side_effect = responses

        access_token = "gho_test_token"
        org_slug = "big-org"

        result = get_organization_members(access_token, org_slug)

        # Verify all 135 members were fetched (4 pages of 30 + 1 page of 15)
        self.assertEqual(len(result), 135, "Should return all 135 members from 5 pages")

        # Verify 5 API requests were made
        self.assertEqual(mock_get.call_count, 5, "Should make 5 API requests for 5 pages")

        # Verify first and last members are correct
        self.assertEqual(result[0]["login"], "user1")
        self.assertEqual(result[0]["id"], 1001)
        self.assertEqual(result[134]["login"], "user135")
        self.assertEqual(result[134]["id"], 1135)


@override_settings(
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestGetUserDetails(TestCase):
    """Tests for fetching detailed information about a specific GitHub user."""

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_details_returns_user_data(self, mock_get):
        """Test that get_user_details returns detailed user data from GitHub API."""
        # Mock successful response from GitHub
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "johndoe",
            "id": 98765,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/98765",
            "bio": "Software Engineer",
            "company": "Acme Corp",
            "location": "San Francisco",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        username = "johndoe"

        result = get_user_details(access_token, username)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["login"], "johndoe")
        self.assertEqual(result["id"], 98765)
        self.assertEqual(result["name"], "John Doe")
        self.assertEqual(result["email"], "john.doe@example.com")
        self.assertEqual(result["avatar_url"], "https://avatars.githubusercontent.com/u/98765")

        # Verify the request was made with correct endpoint
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "https://api.github.com/users/johndoe")
        self.assertEqual(call_args[1]["headers"]["Authorization"], "token gho_test_token")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_details_handles_null_name_and_email(self, mock_get):
        """Test that get_user_details handles users with null name and email (private)."""
        # Mock response with null name and email
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "privateuser",
            "id": 54321,
            "name": None,
            "email": None,
            "avatar_url": "https://avatars.githubusercontent.com/u/54321",
            "bio": None,
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        username = "privateuser"

        result = get_user_details(access_token, username)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["login"], "privateuser")
        self.assertEqual(result["id"], 54321)
        self.assertIsNone(result["name"])
        self.assertIsNone(result["email"])
        self.assertEqual(result["avatar_url"], "https://avatars.githubusercontent.com/u/54321")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_details_raises_error_on_user_not_found(self, mock_get):
        """Test that get_user_details raises GitHubOAuthError when user is not found (404)."""
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Not Found",
            "documentation_url": "https://docs.github.com/rest/reference/users#get-a-user",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        username = "nonexistentuser"

        with self.assertRaises(GitHubOAuthError) as context:
            get_user_details(access_token, username)

        self.assertIn("404", str(context.exception))

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_details_raises_error_on_api_failure(self, mock_get):
        """Test that get_user_details raises GitHubOAuthError on API failures."""
        # Mock 403 response
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "API rate limit exceeded",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        username = "someuser"

        with self.assertRaises(GitHubOAuthError) as context:
            get_user_details(access_token, username)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_details_uses_correct_endpoint(self, mock_get):
        """Test that get_user_details uses correct API endpoint: /users/{username}."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "testuser",
            "id": 123,
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/123",
        }
        mock_get.return_value = mock_response

        access_token = "gho_test_token"
        username = "testuser"

        get_user_details(access_token, username)

        # Verify the correct endpoint is called
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "https://api.github.com/users/testuser")

    @patch("apps.integrations.services.github_oauth.requests.get")
    def test_get_user_details_sends_correct_headers(self, mock_get):
        """Test that get_user_details sends correct Authorization and Accept headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "user",
            "id": 999,
            "name": "User",
            "email": "user@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/999",
        }
        mock_get.return_value = mock_response

        access_token = "test_token_xyz"
        username = "user"

        get_user_details(access_token, username)

        # Verify headers
        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs["headers"]
        self.assertEqual(headers["Authorization"], "token test_token_xyz")
        self.assertEqual(headers["Accept"], "application/vnd.github.v3+json")
