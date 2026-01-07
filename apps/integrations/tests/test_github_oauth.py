"""Tests for GitHub OAuth service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.integrations.services.github_oauth import (
    GITHUB_OAUTH_SCOPES,
    GitHubOAuthError,
    create_oauth_state,
    exchange_code_for_token,
    get_authenticated_user,
    get_authorization_url,
    get_organization_members,
    get_organization_repositories,
    get_user_details,
    get_user_organizations,
    verify_oauth_state,
)

# Import get_user_primary_email - will fail until implemented (TDD RED phase)
try:
    from apps.integrations.services.github_oauth import get_user_primary_email
except ImportError:
    get_user_primary_email = None  # Will cause test failures with clear error
from apps.metrics.factories import TeamFactory


class TestGitHubOAuthScopes(TestCase):
    """Tests for GitHub OAuth scopes configuration."""

    def test_github_oauth_scopes_includes_copilot_billing(self):
        """Test that GITHUB_OAUTH_SCOPES constant includes manage_billing:copilot scope."""
        # This scope is required to access Copilot usage metrics via GitHub API
        self.assertIn("manage_billing:copilot", GITHUB_OAUTH_SCOPES)

    def test_github_oauth_scopes_includes_all_required_scopes(self):
        """Test that GITHUB_OAUTH_SCOPES includes all required scopes for the application.

        Note: 'repo' scope is intentionally NOT included - GitHub App handles repo access.
        OAuth is now only for social login + Copilot metrics.
        """
        # Minimal scopes - no 'repo' access (supports "no code access" claim)
        required_scopes = ["read:org", "read:user", "manage_billing:copilot"]

        for scope in required_scopes:
            with self.subTest(scope=scope):
                self.assertIn(scope, GITHUB_OAUTH_SCOPES, f"Missing required scope: {scope}")

    def test_github_oauth_scopes_does_not_include_repo(self):
        """Test that GITHUB_OAUTH_SCOPES does NOT include repo scope.

        This is intentional - GitHub App handles repo/PR access with installation tokens.
        Not having 'repo' scope supports the "we don't have access to your code" claim.
        """
        self.assertNotIn("repo", GITHUB_OAUTH_SCOPES)

    def test_github_oauth_scopes_includes_user_email(self):
        """Test that GITHUB_OAUTH_SCOPES constant includes user:email scope.

        This scope is required to access the user's email addresses via the
        /user/emails endpoint, which provides verified email addresses even
        when the user has set their email to private.
        """
        self.assertIn("user:email", GITHUB_OAUTH_SCOPES)


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
        """Test that authorization URL includes required scopes: read:org, read:user (NO repo!)."""
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
        # NO repo scope - supports "we don't have access to your code" claim
        self.assertNotIn("repo", url)
        self.assertTrue(
            "read:user" in url or "read%3Auser" in url,
            "Authorization URL should contain 'read:user' scope",
        )

    def test_authorization_url_includes_copilot_billing_scope(self):
        """Test that authorization URL includes manage_billing:copilot scope for Copilot metrics."""
        team = TeamFactory()
        redirect_uri = "http://localhost:8000/integrations/github/callback"

        url = get_authorization_url(team.id, redirect_uri)

        # Scope may be URL encoded, so check for both forms
        self.assertTrue(
            "manage_billing:copilot" in url or "manage_billing%3Acopilot" in url,
            "Authorization URL should contain 'manage_billing:copilot' scope for Copilot API access",
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

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_authenticated_user_returns_user_data(self, mock_github_class):
        """Test that get_authenticated_user returns user data from GitHub API."""
        # Mock Github instance and user object
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Create mock user with attributes (not dict)
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_user.id = 12345
        mock_user.email = "testuser@example.com"
        mock_user.name = "Test User"
        mock_user.avatar_url = "https://avatars.githubusercontent.com/u/12345"

        mock_github.get_user.return_value = mock_user

        access_token = "gho_test_token"

        result = get_authenticated_user(access_token)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["login"], "testuser")
        self.assertEqual(result["id"], 12345)
        self.assertEqual(result["email"], "testuser@example.com")
        self.assertEqual(result["name"], "Test User")
        self.assertEqual(result["avatar_url"], "https://avatars.githubusercontent.com/u/12345")

        # Verify Github was initialized with the access token
        mock_github_class.assert_called_once_with(access_token)
        # Verify get_user() was called with no arguments (gets authenticated user)
        mock_github.get_user.assert_called_once_with()

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_authenticated_user_handles_api_error(self, mock_github_class):
        """Test that get_authenticated_user raises GitHubOAuthError on API error."""
        # Mock Github instance that raises exception
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Simulate PyGithub exception (e.g., BadCredentialsException)
        from github import GithubException

        mock_github.get_user.side_effect = GithubException(401, {"message": "Bad credentials"})

        access_token = "invalid_token"

        with self.assertRaises(GitHubOAuthError) as context:
            get_authenticated_user(access_token)

        self.assertIn("401", str(context.exception))

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_authenticated_user_sends_correct_token(self, mock_github_class):
        """Test that get_authenticated_user initializes Github with correct token."""
        # Mock Github instance and user
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "user"
        mock_user.id = 123
        mock_user.email = "user@example.com"
        mock_user.name = "User"
        mock_user.avatar_url = "https://avatars.githubusercontent.com/u/123"

        mock_github.get_user.return_value = mock_user

        access_token = "test_token"

        get_authenticated_user(access_token)

        # Verify Github was initialized with the correct token
        mock_github_class.assert_called_once_with("test_token")


@override_settings(
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestGetUserOrganizations(TestCase):
    """Tests for fetching user's GitHub organizations."""

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_organizations_returns_list(self, mock_github_class):
        """Test that get_user_organizations returns a list of organizations."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Create mock user
        mock_user = MagicMock()

        # Create mock organization objects with attributes
        mock_org1 = MagicMock()
        mock_org1.login = "acme-corp"
        mock_org1.id = 1001
        mock_org1.description = "Acme Corporation"
        mock_org1.avatar_url = "https://avatars.githubusercontent.com/u/1001"

        mock_org2 = MagicMock()
        mock_org2.login = "test-org"
        mock_org2.id = 1002
        mock_org2.description = "Test Organization"
        mock_org2.avatar_url = "https://avatars.githubusercontent.com/u/1002"

        # Mock get_user().get_orgs() to return list of mock orgs
        mock_user.get_orgs.return_value = [mock_org1, mock_org2]
        mock_github.get_user.return_value = mock_user

        access_token = "gho_test_token"

        result = get_user_organizations(access_token)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["login"], "acme-corp")
        self.assertEqual(result[0]["id"], 1001)
        self.assertEqual(result[0]["description"], "Acme Corporation")
        self.assertEqual(result[0]["avatar_url"], "https://avatars.githubusercontent.com/u/1001")
        self.assertEqual(result[1]["login"], "test-org")
        self.assertEqual(result[1]["id"], 1002)

        # Verify Github was initialized with the access token
        mock_github_class.assert_called_once_with(access_token)
        # Verify get_user() was called with no arguments (gets authenticated user)
        mock_github.get_user.assert_called_once_with()
        # Verify get_orgs() was called
        mock_user.get_orgs.assert_called_once()

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_organizations_returns_empty_list_when_no_orgs(self, mock_github_class):
        """Test that get_user_organizations returns empty list when user has no orgs."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Create mock user
        mock_user = MagicMock()
        mock_user.get_orgs.return_value = []  # Empty list of orgs
        mock_github.get_user.return_value = mock_user

        access_token = "gho_test_token"

        result = get_user_organizations(access_token)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_organizations_handles_api_error(self, mock_github_class):
        """Test that get_user_organizations raises GitHubOAuthError on API error."""
        # Mock Github instance that raises exception
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Simulate PyGithub exception
        from github import GithubException

        mock_github.get_user.side_effect = GithubException(403, {"message": "Forbidden"})

        access_token = "invalid_token"

        with self.assertRaises(GitHubOAuthError) as context:
            get_user_organizations(access_token)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_organizations_passes_correct_token(self, mock_github_class):
        """Test that get_user_organizations initializes Github with correct token."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Create mock user with empty orgs
        mock_user = MagicMock()
        mock_user.get_orgs.return_value = []
        mock_github.get_user.return_value = mock_user

        access_token = "test_token_xyz_123"

        get_user_organizations(access_token)

        # Verify Github was initialized with the correct token
        mock_github_class.assert_called_once_with("test_token_xyz_123")


@override_settings(
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestGetOrganizationMembers(TestCase):
    """Tests for fetching GitHub organization members."""

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_members_returns_list(self, mock_github_class):
        """Test that get_organization_members returns a list of members."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        # Create mock member objects with attributes
        mock_member1 = MagicMock()
        mock_member1.login = "user1"
        mock_member1.id = 1001
        mock_member1.avatar_url = "https://avatars.githubusercontent.com/u/1001"
        mock_member1.type = "User"

        mock_member2 = MagicMock()
        mock_member2.login = "user2"
        mock_member2.id = 1002
        mock_member2.avatar_url = "https://avatars.githubusercontent.com/u/1002"
        mock_member2.type = "User"

        mock_member3 = MagicMock()
        mock_member3.login = "bot1"
        mock_member3.id = 1003
        mock_member3.avatar_url = "https://avatars.githubusercontent.com/u/1003"
        mock_member3.type = "Bot"

        # Mock get_members() to return list of mock members
        mock_org.get_members.return_value = [mock_member1, mock_member2, mock_member3]

        access_token = "gho_test_token"
        org_slug = "acme-corp"

        result = get_organization_members(access_token, org_slug)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["login"], "user1")
        self.assertEqual(result[1]["id"], 1002)
        self.assertEqual(result[2]["type"], "Bot")

        # Verify Github was initialized with the access token
        mock_github_class.assert_called_once_with(access_token)
        # Verify get_organization was called with org_slug
        mock_github.get_organization.assert_called_once_with(org_slug)
        # Verify get_members was called
        mock_org.get_members.assert_called_once()

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_members_each_member_has_required_fields(self, mock_github_class):
        """Test that each member has required fields: id, login, avatar_url, type."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        # Create mock member with all fields
        mock_member = MagicMock()
        mock_member.login = "testuser"
        mock_member.id = 12345
        mock_member.avatar_url = "https://avatars.githubusercontent.com/u/12345"
        mock_member.type = "User"

        mock_org.get_members.return_value = [mock_member]

        access_token = "gho_test_token"
        org_slug = "test-org"

        result = get_organization_members(access_token, org_slug)

        self.assertEqual(len(result), 1)
        member = result[0]
        self.assertIn("id", member)
        self.assertIn("login", member)
        self.assertIn("avatar_url", member)
        self.assertIn("type", member)

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_members_returns_empty_list_when_no_members(self, mock_github_class):
        """Test that get_organization_members returns empty list for org with no members."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization with no members
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org
        mock_org.get_members.return_value = []

        access_token = "gho_test_token"
        org_slug = "empty-org"

        result = get_organization_members(access_token, org_slug)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_members_raises_error_on_404_not_found(self, mock_github_class):
        """Test that get_organization_members raises GitHubOAuthError when org not found (404)."""
        # Mock Github instance that raises exception
        from github import UnknownObjectException

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Simulate 404 - organization not found
        mock_github.get_organization.side_effect = UnknownObjectException(status=404, data={"message": "Not Found"})

        access_token = "gho_test_token"
        org_slug = "nonexistent-org"

        with self.assertRaises(GitHubOAuthError) as context:
            get_organization_members(access_token, org_slug)

        self.assertIn("404", str(context.exception))

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_members_raises_error_on_403_forbidden(self, mock_github_class):
        """Test that get_organization_members raises GitHubOAuthError when access is forbidden."""
        # Mock Github instance that raises exception
        from github import GithubException

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Simulate 403 - forbidden access
        mock_github.get_organization.side_effect = GithubException(status=403, data={"message": "Forbidden"})

        access_token = "gho_test_token"
        org_slug = "private-org"

        with self.assertRaises(GitHubOAuthError) as context:
            get_organization_members(access_token, org_slug)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_members_passes_correct_token(self, mock_github_class):
        """Test that get_organization_members initializes Github with correct token."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization with no members
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org
        mock_org.get_members.return_value = []

        access_token = "test_token_xyz"
        org_slug = "my-org"

        get_organization_members(access_token, org_slug)

        # Verify Github was initialized with the correct token
        mock_github_class.assert_called_once_with("test_token_xyz")

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_members_handles_pagination_automatically(self, mock_github_class):
        """Test that get_organization_members iterates over PaginatedList correctly."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        # Create mock members across multiple pages
        mock_members = []
        for i in range(1, 136):  # 135 members (5 pages: 4x30 + 1x15)
            mock_member = MagicMock()
            mock_member.login = f"user{i}"
            mock_member.id = 1000 + i
            mock_member.avatar_url = f"https://avatars.githubusercontent.com/u/{1000 + i}"
            mock_member.type = "User"
            mock_members.append(mock_member)

        # PyGithub's PaginatedList is iterable, so we just return the list
        # The library handles pagination internally
        mock_org.get_members.return_value = mock_members

        access_token = "gho_test_token"
        org_slug = "big-org"

        result = get_organization_members(access_token, org_slug)

        # Verify all members were returned
        self.assertEqual(len(result), 135, "Should return all 135 members")
        self.assertEqual(result[0]["login"], "user1")
        self.assertEqual(result[0]["id"], 1001)
        self.assertEqual(result[134]["login"], "user135")
        self.assertEqual(result[134]["id"], 1135)

        # Verify Github was called once with correct token
        mock_github_class.assert_called_once_with(access_token)
        # Verify get_organization was called once
        mock_github.get_organization.assert_called_once_with(org_slug)
        # Verify get_members was called once (pagination handled by PyGithub)
        mock_org.get_members.assert_called_once()


@override_settings(
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestGetUserDetails(TestCase):
    """Tests for fetching detailed information about a specific GitHub user."""

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_details_returns_user_data(self, mock_github_class):
        """Test that get_user_details returns detailed user data from GitHub API."""
        # Mock GitHub client and user object
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "johndoe"
        mock_user.id = 98765
        mock_user.name = "John Doe"
        mock_user.email = "john.doe@example.com"
        mock_user.avatar_url = "https://avatars.githubusercontent.com/u/98765"
        mock_user.bio = "Software Engineer"
        mock_user.company = "Acme Corp"
        mock_user.location = "San Francisco"

        mock_github.get_user.return_value = mock_user

        access_token = "gho_test_token"
        username = "johndoe"

        result = get_user_details(access_token, username)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["login"], "johndoe")
        self.assertEqual(result["id"], 98765)
        self.assertEqual(result["name"], "John Doe")
        self.assertEqual(result["email"], "john.doe@example.com")
        self.assertEqual(result["avatar_url"], "https://avatars.githubusercontent.com/u/98765")

        # Verify Github was initialized with correct token
        mock_github_class.assert_called_once_with("gho_test_token")
        # Verify get_user was called with correct username
        mock_github.get_user.assert_called_once_with("johndoe")

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_details_handles_null_name_and_email(self, mock_github_class):
        """Test that get_user_details handles users with null name and email (private)."""
        # Mock GitHub client and user object with null fields
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "privateuser"
        mock_user.id = 54321
        mock_user.name = None
        mock_user.email = None
        mock_user.avatar_url = "https://avatars.githubusercontent.com/u/54321"
        mock_user.bio = None
        mock_user.company = None
        mock_user.location = None

        mock_github.get_user.return_value = mock_user

        access_token = "gho_test_token"
        username = "privateuser"

        result = get_user_details(access_token, username)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["login"], "privateuser")
        self.assertEqual(result["id"], 54321)
        self.assertIsNone(result["name"])
        self.assertIsNone(result["email"])
        self.assertEqual(result["avatar_url"], "https://avatars.githubusercontent.com/u/54321")

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_details_raises_error_on_user_not_found(self, mock_github_class):
        """Test that get_user_details raises GitHubOAuthError when user is not found (404)."""
        # Mock GitHub client that raises UnknownObjectException
        from github import UnknownObjectException

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_github.get_user.side_effect = UnknownObjectException(status=404, data={"message": "Not Found"})

        access_token = "gho_test_token"
        username = "nonexistentuser"

        with self.assertRaises(GitHubOAuthError) as context:
            get_user_details(access_token, username)

        self.assertIn("404", str(context.exception))

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_details_raises_error_on_api_failure(self, mock_github_class):
        """Test that get_user_details raises GitHubOAuthError on API failures."""
        # Mock GitHub client that raises GithubException
        from github import GithubException

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_github.get_user.side_effect = GithubException(status=403, data={"message": "API rate limit exceeded"})

        access_token = "gho_test_token"
        username = "someuser"

        with self.assertRaises(GitHubOAuthError) as context:
            get_user_details(access_token, username)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_details_calls_get_user_with_username(self, mock_github_class):
        """Test that get_user_details calls github.get_user() with the correct username."""
        # Mock GitHub client and user object
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_user.id = 123
        mock_user.name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.avatar_url = "https://avatars.githubusercontent.com/u/123"
        mock_user.bio = None
        mock_user.company = None
        mock_user.location = None

        mock_github.get_user.return_value = mock_user

        access_token = "gho_test_token"
        username = "testuser"

        get_user_details(access_token, username)

        # Verify get_user is called with correct username
        mock_github.get_user.assert_called_once_with("testuser")

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_details_passes_correct_token(self, mock_github_class):
        """Test that get_user_details initializes Github client with correct access token."""
        # Mock GitHub client and user object
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        mock_user = MagicMock()
        mock_user.login = "user"
        mock_user.id = 999
        mock_user.name = "User"
        mock_user.email = "user@example.com"
        mock_user.avatar_url = "https://avatars.githubusercontent.com/u/999"
        mock_user.bio = None
        mock_user.company = None
        mock_user.location = None

        mock_github.get_user.return_value = mock_user

        access_token = "test_token_xyz"
        username = "user"

        get_user_details(access_token, username)

        # Verify Github is initialized with correct token
        mock_github_class.assert_called_once_with("test_token_xyz")


@override_settings(
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestGetOrganizationRepositories(TestCase):
    """Tests for fetching GitHub organization repositories."""

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_repositories_returns_list(self, mock_github_class):
        """Test that get_organization_repositories returns a list of repositories."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        # Create mock repository objects with attributes
        mock_repo1 = MagicMock()
        mock_repo1.id = 123456
        mock_repo1.full_name = "acme-corp/backend-api"
        mock_repo1.name = "backend-api"
        mock_repo1.description = "Main backend API service"
        mock_repo1.language = "Python"
        mock_repo1.private = False
        mock_repo1.updated_at = "2025-01-15T10:30:00Z"
        mock_repo1.archived = False
        mock_repo1.default_branch = "main"

        mock_repo2 = MagicMock()
        mock_repo2.id = 123457
        mock_repo2.full_name = "acme-corp/frontend-app"
        mock_repo2.name = "frontend-app"
        mock_repo2.description = "React frontend application"
        mock_repo2.language = "TypeScript"
        mock_repo2.private = True
        mock_repo2.updated_at = "2025-01-14T09:20:00Z"
        mock_repo2.archived = False
        mock_repo2.default_branch = "main"

        # Mock get_repos() to return list of mock repos
        mock_org.get_repos.return_value = [mock_repo1, mock_repo2]

        access_token = "gho_test_token"
        org_slug = "acme-corp"

        result = get_organization_repositories(access_token, org_slug)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "backend-api")
        self.assertEqual(result[0]["full_name"], "acme-corp/backend-api")
        self.assertEqual(result[0]["language"], "Python")
        self.assertEqual(result[1]["name"], "frontend-app")
        self.assertEqual(result[1]["private"], True)

        # Verify Github was initialized with the access token
        mock_github_class.assert_called_once_with(access_token)
        # Verify get_organization was called with org_slug
        mock_github.get_organization.assert_called_once_with(org_slug)
        # Verify get_repos was called
        mock_org.get_repos.assert_called_once()

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_repositories_each_repo_has_required_fields(self, mock_github_class):
        """Test that each repository has required metadata fields."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        # Create mock repository with all required fields
        mock_repo = MagicMock()
        mock_repo.id = 789012
        mock_repo.full_name = "test-org/test-repo"
        mock_repo.name = "test-repo"
        mock_repo.description = "Test repository"
        mock_repo.language = "JavaScript"
        mock_repo.private = False
        mock_repo.updated_at = "2025-01-10T12:00:00Z"
        mock_repo.archived = False
        mock_repo.default_branch = "main"

        mock_org.get_repos.return_value = [mock_repo]

        access_token = "gho_test_token"
        org_slug = "test-org"

        result = get_organization_repositories(access_token, org_slug)

        self.assertEqual(len(result), 1)
        repo = result[0]
        # Verify all required fields are present
        self.assertIn("id", repo)
        self.assertIn("full_name", repo)
        self.assertIn("name", repo)
        self.assertIn("description", repo)
        self.assertIn("language", repo)
        self.assertIn("private", repo)
        self.assertIn("updated_at", repo)
        self.assertIn("archived", repo)
        self.assertIn("default_branch", repo)

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_repositories_returns_empty_list_when_no_repos(self, mock_github_class):
        """Test that get_organization_repositories returns empty list for org with no repos."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization with no repos
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org
        mock_org.get_repos.return_value = []

        access_token = "gho_test_token"
        org_slug = "empty-org"

        result = get_organization_repositories(access_token, org_slug)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_repositories_raises_error_on_401_unauthorized(self, mock_github_class):
        """Test that get_organization_repositories raises GitHubOAuthError on 401 unauthorized."""
        # Mock Github instance that raises exception
        from github import GithubException

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Simulate 401 - bad credentials
        mock_github.get_organization.side_effect = GithubException(status=401, data={"message": "Bad credentials"})

        access_token = "invalid_token"
        org_slug = "acme-corp"

        with self.assertRaises(GitHubOAuthError) as context:
            get_organization_repositories(access_token, org_slug)

        self.assertIn("401", str(context.exception))

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_repositories_raises_error_on_404_not_found(self, mock_github_class):
        """Test that get_organization_repositories raises GitHubOAuthError on 404 org not found."""
        # Mock Github instance that raises exception
        from github import UnknownObjectException

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Simulate 404 - organization not found
        mock_github.get_organization.side_effect = UnknownObjectException(status=404, data={"message": "Not Found"})

        access_token = "gho_test_token"
        org_slug = "nonexistent-org"

        with self.assertRaises(GitHubOAuthError) as context:
            get_organization_repositories(access_token, org_slug)

        self.assertIn("404", str(context.exception))

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_repositories_raises_error_on_403_rate_limit(self, mock_github_class):
        """Test that get_organization_repositories raises GitHubOAuthError when rate limited."""
        # Mock Github instance that raises exception
        from github import GithubException

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Simulate 403 - rate limit exceeded
        mock_github.get_organization.side_effect = GithubException(
            status=403, data={"message": "API rate limit exceeded"}
        )

        access_token = "gho_test_token"
        org_slug = "acme-corp"

        with self.assertRaises(GitHubOAuthError) as context:
            get_organization_repositories(access_token, org_slug)

        self.assertIn("403", str(context.exception))

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_repositories_passes_correct_token(self, mock_github_class):
        """Test that get_organization_repositories initializes Github with correct token."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization with no repos
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org
        mock_org.get_repos.return_value = []

        access_token = "test_token_xyz"
        org_slug = "my-org"

        get_organization_repositories(access_token, org_slug)

        # Verify Github was initialized with the correct token
        mock_github_class.assert_called_once_with("test_token_xyz")

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_repositories_can_filter_archived_repos(self, mock_github_class):
        """Test that get_organization_repositories can filter out archived repositories."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        # Create mock repos with both active and archived
        mock_repo1 = MagicMock()
        mock_repo1.id = 4001
        mock_repo1.full_name = "org/active-repo"
        mock_repo1.name = "active-repo"
        mock_repo1.description = "Active repository"
        mock_repo1.language = "Python"
        mock_repo1.private = False
        mock_repo1.updated_at = "2025-01-15T10:00:00Z"
        mock_repo1.archived = False
        mock_repo1.default_branch = "main"

        mock_repo2 = MagicMock()
        mock_repo2.id = 4002
        mock_repo2.full_name = "org/archived-repo"
        mock_repo2.name = "archived-repo"
        mock_repo2.description = "Archived repository"
        mock_repo2.language = "Python"
        mock_repo2.private = False
        mock_repo2.updated_at = "2023-06-10T10:00:00Z"
        mock_repo2.archived = True
        mock_repo2.default_branch = "main"

        mock_repo3 = MagicMock()
        mock_repo3.id = 4003
        mock_repo3.full_name = "org/another-active-repo"
        mock_repo3.name = "another-active-repo"
        mock_repo3.description = "Another active repository"
        mock_repo3.language = "JavaScript"
        mock_repo3.private = True
        mock_repo3.updated_at = "2025-01-14T10:00:00Z"
        mock_repo3.archived = False
        mock_repo3.default_branch = "main"

        mock_org.get_repos.return_value = [mock_repo1, mock_repo2, mock_repo3]

        access_token = "gho_test_token"
        org_slug = "org"

        # Call with exclude_archived=True
        result = get_organization_repositories(access_token, org_slug, exclude_archived=True)

        # Verify only non-archived repos are returned
        self.assertEqual(len(result), 2, "Should only return non-archived repos")
        self.assertEqual(result[0]["name"], "active-repo")
        self.assertFalse(result[0]["archived"])
        self.assertEqual(result[1]["name"], "another-active-repo")
        self.assertFalse(result[1]["archived"])

        # Verify archived repo is not in results
        archived_names = [repo["name"] for repo in result]
        self.assertNotIn("archived-repo", archived_names)

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_organization_repositories_includes_archived_by_default(self, mock_github_class):
        """Test that get_organization_repositories includes archived repos by default."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Mock organization
        mock_org = MagicMock()
        mock_github.get_organization.return_value = mock_org

        # Create mock repos with both active and archived
        mock_repo1 = MagicMock()
        mock_repo1.id = 5001
        mock_repo1.full_name = "org/active-repo"
        mock_repo1.name = "active-repo"
        mock_repo1.description = "Active repository"
        mock_repo1.language = "Python"
        mock_repo1.private = False
        mock_repo1.updated_at = "2025-01-15T10:00:00Z"
        mock_repo1.archived = False
        mock_repo1.default_branch = "main"

        mock_repo2 = MagicMock()
        mock_repo2.id = 5002
        mock_repo2.full_name = "org/archived-repo"
        mock_repo2.name = "archived-repo"
        mock_repo2.description = "Archived repository"
        mock_repo2.language = "Python"
        mock_repo2.private = False
        mock_repo2.updated_at = "2023-06-10T10:00:00Z"
        mock_repo2.archived = True
        mock_repo2.default_branch = "main"

        mock_org.get_repos.return_value = [mock_repo1, mock_repo2]

        access_token = "gho_test_token"
        org_slug = "org"

        # Call without exclude_archived parameter (should default to False)
        result = get_organization_repositories(access_token, org_slug)

        # Verify all repos are returned including archived
        self.assertEqual(len(result), 2, "Should return all repos including archived by default")
        self.assertEqual(result[0]["name"], "active-repo")
        self.assertEqual(result[1]["name"], "archived-repo")
        self.assertTrue(result[1]["archived"])


@override_settings(
    GITHUB_CLIENT_ID="test_client_id_123",
    GITHUB_SECRET_ID="test_client_secret_456",
)
class TestGetUserPrimaryEmail(TestCase):
    """Tests for fetching user's primary email from GitHub API."""

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_primary_email_returns_primary_verified_email(self, mock_github_class):
        """Test that get_user_primary_email returns the primary verified email when available."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Create mock user
        mock_user = MagicMock()
        mock_github.get_user.return_value = mock_user

        # Create mock email objects with primary verified email
        mock_email1 = MagicMock()
        mock_email1.email = "primary@example.com"
        mock_email1.primary = True
        mock_email1.verified = True

        mock_email2 = MagicMock()
        mock_email2.email = "secondary@example.com"
        mock_email2.primary = False
        mock_email2.verified = True

        mock_user.get_emails.return_value = [mock_email1, mock_email2]

        access_token = "gho_test_token"

        result = get_user_primary_email(access_token)

        self.assertEqual(result, "primary@example.com")

        # Verify Github was initialized with the access token
        mock_github_class.assert_called_once_with(access_token)
        # Verify get_user() was called with no arguments (gets authenticated user)
        mock_github.get_user.assert_called_once_with()
        # Verify get_emails() was called
        mock_user.get_emails.assert_called_once()

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_primary_email_falls_back_to_first_verified_email(self, mock_github_class):
        """Test that get_user_primary_email returns first verified email when no primary exists."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Create mock user
        mock_user = MagicMock()
        mock_github.get_user.return_value = mock_user

        # Create mock email objects - no primary, but verified exists
        mock_email1 = MagicMock()
        mock_email1.email = "first@example.com"
        mock_email1.primary = False
        mock_email1.verified = True

        mock_email2 = MagicMock()
        mock_email2.email = "second@example.com"
        mock_email2.primary = False
        mock_email2.verified = False

        mock_user.get_emails.return_value = [mock_email1, mock_email2]

        access_token = "gho_test_token"

        result = get_user_primary_email(access_token)

        # Should return the first verified email
        self.assertEqual(result, "first@example.com")

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_primary_email_returns_none_when_no_verified_emails(self, mock_github_class):
        """Test that get_user_primary_email returns None when all emails are unverified."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Create mock user
        mock_user = MagicMock()
        mock_github.get_user.return_value = mock_user

        # Create mock email objects - all unverified
        mock_email1 = MagicMock()
        mock_email1.email = "unverified@example.com"
        mock_email1.primary = True
        mock_email1.verified = False

        mock_user.get_emails.return_value = [mock_email1]

        access_token = "gho_test_token"

        result = get_user_primary_email(access_token)

        # Should return None since no verified emails exist
        self.assertIsNone(result)

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_primary_email_returns_none_when_no_emails(self, mock_github_class):
        """Test that get_user_primary_email returns None when user has no emails."""
        # Mock Github instance
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Create mock user
        mock_user = MagicMock()
        mock_github.get_user.return_value = mock_user

        # Empty email list
        mock_user.get_emails.return_value = []

        access_token = "gho_test_token"

        result = get_user_primary_email(access_token)

        # Should return None since no emails exist
        self.assertIsNone(result)

    @patch("apps.integrations.services.github_oauth.Github")
    def test_get_user_primary_email_raises_error_on_api_failure(self, mock_github_class):
        """Test that get_user_primary_email raises GitHubOAuthError on API failure."""
        # Mock Github instance that raises exception
        from github import GithubException

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github

        # Create mock user that raises exception on get_emails()
        mock_user = MagicMock()
        mock_github.get_user.return_value = mock_user
        mock_user.get_emails.side_effect = GithubException(status=401, data={"message": "Bad credentials"})

        access_token = "invalid_token"

        with self.assertRaises(GitHubOAuthError) as context:
            get_user_primary_email(access_token)

        self.assertIn("401", str(context.exception))
