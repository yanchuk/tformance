"""Tests for GitHub GraphQL client service."""

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_graphql import (
    GitHubGraphQLClient,
    GitHubGraphQLError,
    GitHubGraphQLPermissionError,
    GitHubGraphQLRateLimitError,
    GitHubGraphQLTimeoutError,
    _is_permission_error,
)


def create_mock_client_context_manager(execute_return_value=None, execute_side_effect=None):
    """Create a mock Client class that works as async context manager.

    Usage: patch('...Client', side_effect=create_mock_client_context_manager(return_value))
    """
    mock_session = MagicMock()
    if execute_side_effect:
        mock_session.execute = AsyncMock(side_effect=execute_side_effect)
    else:
        mock_session.execute = AsyncMock(return_value=execute_return_value)

    # Create context manager mock
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    return mock_client, mock_session


class TestGitHubGraphQLError(TestCase):
    """Tests for GitHubGraphQLError exception."""

    def test_github_graphql_error_can_be_raised(self):
        """Test that GitHubGraphQLError can be raised and caught."""
        with self.assertRaises(GitHubGraphQLError):
            raise GitHubGraphQLError("Test error")

    def test_github_graphql_error_message(self):
        """Test that GitHubGraphQLError preserves error message."""
        error_message = "GraphQL query failed"
        try:
            raise GitHubGraphQLError(error_message)
        except GitHubGraphQLError as e:
            self.assertEqual(str(e), error_message)


class TestGitHubGraphQLRateLimitError(TestCase):
    """Tests for GitHubGraphQLRateLimitError exception."""

    def test_github_graphql_rate_limit_error_can_be_raised(self):
        """Test that GitHubGraphQLRateLimitError can be raised and caught."""
        with self.assertRaises(GitHubGraphQLRateLimitError):
            raise GitHubGraphQLRateLimitError("Rate limit exceeded")

    def test_github_graphql_rate_limit_error_message(self):
        """Test that GitHubGraphQLRateLimitError preserves error message."""
        error_message = "Rate limit remaining: 50"
        try:
            raise GitHubGraphQLRateLimitError(error_message)
        except GitHubGraphQLRateLimitError as e:
            self.assertEqual(str(e), error_message)

    def test_github_graphql_rate_limit_error_inherits_from_base_error(self):
        """Test that GitHubGraphQLRateLimitError inherits from GitHubGraphQLError."""
        self.assertTrue(issubclass(GitHubGraphQLRateLimitError, GitHubGraphQLError))


class TestGitHubGraphQLClientInitialization(TestCase):
    """Tests for GitHubGraphQLClient initialization."""

    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_client_initialization_creates_transport_with_correct_url(self, mock_transport_class):
        """Test that client initialization creates AIOHTTPTransport with GitHub GraphQL API URL."""
        # Arrange
        access_token = "gho_test_token_123"
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Act
        _client = GitHubGraphQLClient(access_token)  # noqa: F841

        # Assert
        mock_transport_class.assert_called_once()
        call_kwargs = mock_transport_class.call_args[1]
        self.assertEqual(call_kwargs["url"], "https://api.github.com/graphql")

    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_client_initialization_sets_authorization_header(self, mock_transport_class):
        """Test that client initialization sets Authorization header with Bearer token."""
        # Arrange
        access_token = "gho_test_token_456"
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Act
        _client = GitHubGraphQLClient(access_token)  # noqa: F841

        # Assert
        call_kwargs = mock_transport_class.call_args[1]
        expected_headers = {"Authorization": f"Bearer {access_token}"}
        self.assertEqual(call_kwargs["headers"], expected_headers)

    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_client_initialization_stores_transport(self, mock_transport_class):
        """Test that client initialization stores transport for later use."""
        # Arrange
        access_token = "gho_test_token_789"
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Act
        client = GitHubGraphQLClient(access_token)

        # Assert
        self.assertEqual(client.transport, mock_transport)
        self.assertIsNotNone(client)


class TestFetchPRsBulk(TestCase):
    """Tests for GitHubGraphQLClient.fetch_prs_bulk method."""

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_bulk_calls_execute_with_query(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_bulk executes GraphQL query."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        result = asyncio.run(client.fetch_prs_bulk("owner", "repo"))

        # Assert
        mock_session.execute.assert_called_once()
        self.assertIn("repository", result)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_bulk_returns_pull_requests_data(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_bulk returns repository.pullRequests data."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        expected_data = {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 123,
                            "title": "Test PR",
                            "state": "MERGED",
                            "reviews": {"nodes": []},
                            "commits": {"nodes": []},
                            "files": {"nodes": []},
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 4999},
        }

        mock_client, mock_session = create_mock_client_context_manager(expected_data)
        mock_client_class.return_value = mock_client
        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        result = asyncio.run(client.fetch_prs_bulk("owner", "repo"))

        # Assert
        self.assertEqual(result, expected_data)
        self.assertIn("pullRequests", result["repository"])
        self.assertEqual(len(result["repository"]["pullRequests"]["nodes"]), 1)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_bulk_handles_pagination_cursor(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_bulk passes cursor for pagination."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        cursor = "cursor_abc123"
        asyncio.run(client.fetch_prs_bulk("owner", "repo", cursor=cursor))

        # Assert
        # Verify execute was called with cursor in variables
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        self.assertEqual(variables["cursor"], cursor)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_bulk_raises_rate_limit_error_when_remaining_low(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_bulk raises GitHubGraphQLRateLimitError when remaining < 100."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "repository": {"pullRequests": {"nodes": [], "pageInfo": {}}},
            "rateLimit": {"remaining": 50},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLRateLimitError) as context:
            asyncio.run(client.fetch_prs_bulk("owner", "repo"))

        self.assertIn("50", str(context.exception))

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_bulk_raises_error_on_graphql_errors(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_bulk raises GitHubGraphQLError on query errors."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Simulate GraphQL error response
        from gql.transport.exceptions import TransportQueryError

        mock_client, mock_session = create_mock_client_context_manager(
            execute_side_effect=TransportQueryError("GraphQL query error")
        )
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLError):
            asyncio.run(client.fetch_prs_bulk("owner", "repo"))


class TestFetchSinglePR(TestCase):
    """Tests for GitHubGraphQLClient.fetch_single_pr method."""

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_single_pr_calls_execute_with_pr_number(self, mock_transport_class, mock_client_class):
        """Test that fetch_single_pr executes GraphQL query with PR number."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "repository": {
                "pullRequest": {
                    "number": 456,
                    "title": "Single PR",
                    "state": "OPEN",
                    "reviews": {"nodes": []},
                    "commits": {"nodes": []},
                    "files": {"nodes": []},
                }
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        asyncio.run(client.fetch_single_pr("owner", "repo", 456))

        # Assert
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        self.assertEqual(variables["number"], 456)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_single_pr_returns_pull_request_data(self, mock_transport_class, mock_client_class):
        """Test that fetch_single_pr returns repository.pullRequest data."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        expected_data = {
            "repository": {
                "pullRequest": {
                    "number": 789,
                    "title": "Feature PR",
                    "state": "MERGED",
                    "reviews": {"nodes": [{"author": {"login": "reviewer1"}}]},
                    "commits": {"nodes": [{"commit": {"oid": "abc123"}}]},
                    "files": {"nodes": [{"path": "file.py"}]},
                }
            },
            "rateLimit": {"remaining": 4500},
        }

        mock_client, mock_session = create_mock_client_context_manager(expected_data)
        mock_client_class.return_value = mock_client
        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        result = asyncio.run(client.fetch_single_pr("owner", "repo", 789))

        # Assert
        self.assertEqual(result, expected_data)
        self.assertIn("pullRequest", result["repository"])
        self.assertEqual(result["repository"]["pullRequest"]["number"], 789)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_single_pr_raises_rate_limit_error_when_remaining_low(self, mock_transport_class, mock_client_class):
        """Test that fetch_single_pr raises GitHubGraphQLRateLimitError when remaining < 100."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "repository": {"pullRequest": {"number": 123}},
            "rateLimit": {"remaining": 75},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLRateLimitError):
            asyncio.run(client.fetch_single_pr("owner", "repo", 123))

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_single_pr_raises_error_on_network_failure(self, mock_transport_class, mock_client_class):
        """Test that fetch_single_pr raises GitHubGraphQLError on network errors."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=Exception("Network timeout"))
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLError):
            asyncio.run(client.fetch_single_pr("owner", "repo", 123))


class TestFetchOrgMembers(TestCase):
    """Tests for GitHubGraphQLClient.fetch_org_members method."""

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_org_members_calls_execute_with_org_name(self, mock_transport_class, mock_client_class):
        """Test that fetch_org_members executes GraphQL query with organization name."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "organization": {
                "membersWithRole": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        asyncio.run(client.fetch_org_members("test-org"))

        # Assert
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        self.assertEqual(variables["org"], "test-org")

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_org_members_returns_members_data(self, mock_transport_class, mock_client_class):
        """Test that fetch_org_members returns organization.membersWithRole data."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        expected_data = {
            "organization": {
                "membersWithRole": {
                    "nodes": [
                        {"login": "user1", "name": "User One"},
                        {"login": "user2", "name": "User Two"},
                    ],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor_xyz"},
                }
            },
            "rateLimit": {"remaining": 4800},
        }

        mock_client, mock_session = create_mock_client_context_manager(expected_data)
        mock_client_class.return_value = mock_client
        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        result = asyncio.run(client.fetch_org_members("test-org"))

        # Assert
        self.assertEqual(result, expected_data)
        self.assertIn("membersWithRole", result["organization"])
        self.assertEqual(len(result["organization"]["membersWithRole"]["nodes"]), 2)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_org_members_handles_pagination_cursor(self, mock_transport_class, mock_client_class):
        """Test that fetch_org_members passes cursor for pagination."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "organization": {
                "membersWithRole": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        cursor = "cursor_page2"
        asyncio.run(client.fetch_org_members("test-org", cursor=cursor))

        # Assert
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        self.assertEqual(variables["cursor"], cursor)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_org_members_raises_rate_limit_error_when_remaining_low(
        self, mock_transport_class, mock_client_class
    ):
        """Test that fetch_org_members raises GitHubGraphQLRateLimitError when remaining < 100."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "organization": {"membersWithRole": {"nodes": [], "pageInfo": {}}},
            "rateLimit": {"remaining": 25},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLRateLimitError):
            asyncio.run(client.fetch_org_members("test-org"))

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_org_members_raises_error_on_query_failure(self, mock_transport_class, mock_client_class):
        """Test that fetch_org_members raises GitHubGraphQLError on query errors."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        mock_client, mock_session = create_mock_client_context_manager(
            execute_side_effect=Exception("Organization not found")
        )
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLError):
            asyncio.run(client.fetch_org_members("nonexistent-org"))


class TestGitHubGraphQLTimeoutError(TestCase):
    """Tests for GitHubGraphQLTimeoutError exception."""

    def test_timeout_error_can_be_raised(self):
        """Test that GitHubGraphQLTimeoutError can be raised and caught."""
        with self.assertRaises(GitHubGraphQLTimeoutError):
            raise GitHubGraphQLTimeoutError("Request timed out")

    def test_timeout_error_inherits_from_base_error(self):
        """Test that GitHubGraphQLTimeoutError inherits from GitHubGraphQLError."""
        self.assertTrue(issubclass(GitHubGraphQLTimeoutError, GitHubGraphQLError))

    def test_timeout_error_message(self):
        """Test that GitHubGraphQLTimeoutError preserves error message."""
        error_message = "Request timed out after 30 seconds"
        try:
            raise GitHubGraphQLTimeoutError(error_message)
        except GitHubGraphQLTimeoutError as e:
            self.assertEqual(str(e), error_message)


class TestGitHubGraphQLPermissionError(TestCase):
    """Tests for GitHubGraphQLPermissionError exception."""

    def test_permission_error_can_be_raised(self):
        """Test that GitHubGraphQLPermissionError can be raised and caught."""
        with self.assertRaises(GitHubGraphQLPermissionError):
            raise GitHubGraphQLPermissionError("Resource not accessible by integration")

    def test_permission_error_inherits_from_base_error(self):
        """Test that GitHubGraphQLPermissionError inherits from GitHubGraphQLError."""
        self.assertTrue(issubclass(GitHubGraphQLPermissionError, GitHubGraphQLError))

    def test_permission_error_message(self):
        """Test that GitHubGraphQLPermissionError preserves error message."""
        error_message = "Resource not accessible by integration"
        try:
            raise GitHubGraphQLPermissionError(error_message)
        except GitHubGraphQLPermissionError as e:
            self.assertEqual(str(e), error_message)


class TestIsPermissionError(TestCase):
    """Tests for _is_permission_error helper function."""

    def test_detects_resource_not_accessible(self):
        """Test detection of 'resource not accessible by integration' error."""
        error = Exception("Resource not accessible by integration")
        self.assertTrue(_is_permission_error(error))

    def test_detects_forbidden_error(self):
        """Test detection of FORBIDDEN error."""
        error = Exception("FORBIDDEN: Access denied")
        self.assertTrue(_is_permission_error(error))

    def test_detects_push_access_error(self):
        """Test detection of 'must have push access' error."""
        error = Exception("You must have push access to this repository")
        self.assertTrue(_is_permission_error(error))

    def test_detects_saml_failure(self):
        """Test detection of SAML authentication failure."""
        error = Exception("saml_failure: SSO required")
        self.assertTrue(_is_permission_error(error))

    def test_does_not_match_unrelated_errors(self):
        """Test that unrelated errors are not detected as permission errors."""
        error = Exception("Network timeout")
        self.assertFalse(_is_permission_error(error))

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        error = Exception("RESOURCE NOT ACCESSIBLE BY INTEGRATION")
        self.assertTrue(_is_permission_error(error))


@patch("asyncio.sleep", new_callable=AsyncMock)
class TestTimeoutHandling(TestCase):
    """Tests for timeout handling in GraphQL client.

    Note: asyncio.sleep is mocked at class level to avoid real delays during retry tests.
    These tests verify that timeout errors are properly raised after retries are exhausted.
    """

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_bulk_raises_timeout_error_on_timeout(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that fetch_prs_bulk raises GitHubGraphQLTimeoutError on timeout."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Simulate TimeoutError
        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=TimeoutError())
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLTimeoutError):
            asyncio.run(client.fetch_prs_bulk("owner", "repo"))

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_single_pr_raises_timeout_error_on_timeout(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that fetch_single_pr raises GitHubGraphQLTimeoutError on timeout."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=TimeoutError())
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLTimeoutError):
            asyncio.run(client.fetch_single_pr("owner", "repo", 123))

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_org_members_raises_timeout_error_on_timeout(
        self, mock_transport_class, mock_client_class, mock_sleep
    ):
        """Test that fetch_org_members raises GitHubGraphQLTimeoutError on timeout."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=TimeoutError())
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLTimeoutError):
            asyncio.run(client.fetch_org_members("test-org"))


@patch("asyncio.sleep", new_callable=AsyncMock)
class TestRetryOnTimeout(TestCase):
    """Tests for retry logic on timeout.

    Note: asyncio.sleep is mocked at class level to avoid real delays during retry tests.
    """

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_bulk_retries_on_timeout(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that fetch_prs_bulk retries on timeout before failing."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        success_response = {
            "repository": {"pullRequests": {"nodes": [], "pageInfo": {}}},
            "rateLimit": {"remaining": 5000},
        }

        # Fail twice, then succeed
        mock_client, mock_session = create_mock_client_context_manager()
        mock_session.execute = AsyncMock(side_effect=[TimeoutError(), TimeoutError(), success_response])
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        result = asyncio.run(client.fetch_prs_bulk("owner", "repo", max_retries=3))

        # Assert
        self.assertEqual(mock_session.execute.call_count, 3)
        self.assertIn("repository", result)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_bulk_fails_after_max_retries(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that fetch_prs_bulk fails after max retries exceeded."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Always timeout
        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=TimeoutError())
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLTimeoutError) as context:
            asyncio.run(client.fetch_prs_bulk("owner", "repo", max_retries=3))

        self.assertIn("3", str(context.exception))  # Should mention retry count

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_single_pr_retries_on_timeout(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that fetch_single_pr retries on timeout before failing."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        success_response = {
            "repository": {"pullRequest": {"number": 123}},
            "rateLimit": {"remaining": 5000},
        }

        # Fail twice, then succeed
        mock_client, mock_session = create_mock_client_context_manager()
        mock_session.execute = AsyncMock(side_effect=[TimeoutError(), TimeoutError(), success_response])
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        result = asyncio.run(client.fetch_single_pr("owner", "repo", 123, max_retries=3))

        # Assert
        self.assertEqual(mock_session.execute.call_count, 3)
        self.assertIn("repository", result)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_single_pr_fails_after_max_retries(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that fetch_single_pr fails after max retries exceeded."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=TimeoutError())
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLTimeoutError) as context:
            asyncio.run(client.fetch_single_pr("owner", "repo", 123, max_retries=3))

        self.assertIn("3", str(context.exception))

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_org_members_retries_on_timeout(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that fetch_org_members retries on timeout before failing."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        success_response = {
            "organization": {"membersWithRole": {"nodes": [], "pageInfo": {}}},
            "rateLimit": {"remaining": 5000},
        }

        # Fail once, then succeed
        mock_client, mock_session = create_mock_client_context_manager()
        mock_session.execute = AsyncMock(side_effect=[TimeoutError(), success_response])
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio

        result = asyncio.run(client.fetch_org_members("test-org", max_retries=3))

        # Assert
        self.assertEqual(mock_session.execute.call_count, 2)
        self.assertIn("organization", result)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_org_members_fails_after_max_retries(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that fetch_org_members fails after max retries exceeded."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=TimeoutError())
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio

        with self.assertRaises(GitHubGraphQLTimeoutError) as context:
            asyncio.run(client.fetch_org_members("test-org", max_retries=3))

        self.assertIn("3", str(context.exception))


class TestFetchPRsUpdatedSince(TestCase):
    """Tests for GitHubGraphQLClient.fetch_prs_updated_since method."""

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_updated_since_calls_execute(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_updated_since executes GraphQL query."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio
        from datetime import datetime

        since = datetime(2024, 1, 1, tzinfo=UTC)
        result = asyncio.run(client.fetch_prs_updated_since("owner", "repo", since))

        # Assert
        mock_session.execute.assert_called_once()
        self.assertIn("repository", result)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_updated_since_passes_since_datetime(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_updated_since passes since datetime in query variables."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio
        from datetime import datetime

        since = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
        asyncio.run(client.fetch_prs_updated_since("owner", "repo", since))

        # Assert
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        self.assertEqual(variables["owner"], "owner")
        self.assertEqual(variables["repo"], "repo")

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_updated_since_returns_prs_data(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_updated_since returns pull requests data."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        expected_data = {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {"number": 123, "title": "Updated PR", "state": "MERGED", "updatedAt": "2024-06-15T12:00:00Z"}
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 4999},
        }
        mock_client, mock_session = create_mock_client_context_manager(expected_data)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio
        from datetime import datetime

        since = datetime(2024, 6, 1, tzinfo=UTC)
        result = asyncio.run(client.fetch_prs_updated_since("owner", "repo", since))

        # Assert
        self.assertEqual(result, expected_data)
        self.assertEqual(len(result["repository"]["pullRequests"]["nodes"]), 1)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_updated_since_handles_pagination(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_updated_since supports pagination cursor."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "repository": {
                "pullRequests": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio
        from datetime import datetime

        since = datetime(2024, 6, 1, tzinfo=UTC)
        cursor = "cursor_page2"
        asyncio.run(client.fetch_prs_updated_since("owner", "repo", since, cursor=cursor))

        # Assert
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        self.assertEqual(variables["cursor"], cursor)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_updated_since_raises_rate_limit_error(self, mock_transport_class, mock_client_class):
        """Test that fetch_prs_updated_since raises GitHubGraphQLRateLimitError when remaining low."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "repository": {"pullRequests": {"nodes": [], "pageInfo": {}}},
            "rateLimit": {"remaining": 50},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act & Assert
        import asyncio
        from datetime import datetime

        since = datetime(2024, 6, 1, tzinfo=UTC)
        with self.assertRaises(GitHubGraphQLRateLimitError):
            asyncio.run(client.fetch_prs_updated_since("owner", "repo", since))

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_fetch_prs_updated_since_retries_on_timeout(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that fetch_prs_updated_since retries on timeout."""
        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        success_response = {
            "repository": {"pullRequests": {"nodes": [], "pageInfo": {}}},
            "rateLimit": {"remaining": 5000},
        }

        mock_client, mock_session = create_mock_client_context_manager()
        mock_session.execute = AsyncMock(side_effect=[TimeoutError(), success_response])
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        import asyncio
        from datetime import datetime

        since = datetime(2024, 6, 1, tzinfo=UTC)
        result = asyncio.run(client.fetch_prs_updated_since("owner", "repo", since, max_retries=3))

        # Assert
        self.assertEqual(mock_session.execute.call_count, 2)
        self.assertIn("repository", result)


class TestRateLimitWaitBehavior(TestCase):
    """Tests for rate limit wait behavior in GitHubGraphQLClient."""

    def test_client_has_wait_for_reset_parameter(self):
        """Test that client accepts wait_for_reset parameter."""
        # Act
        client = GitHubGraphQLClient("token", wait_for_reset=True)

        # Assert
        self.assertTrue(client.wait_for_reset)

    def test_client_has_max_wait_seconds_parameter(self):
        """Test that client accepts max_wait_seconds parameter."""
        # Act
        client = GitHubGraphQLClient("token", max_wait_seconds=1800)

        # Assert
        self.assertEqual(client.max_wait_seconds, 1800)

    def test_client_defaults_to_wait_for_reset_true(self):
        """Test that client defaults to waiting for rate limit reset."""
        # Act
        client = GitHubGraphQLClient("token")

        # Assert
        self.assertTrue(client.wait_for_reset)

    def test_client_defaults_to_one_hour_max_wait(self):
        """Test that client defaults to 1 hour max wait time."""
        # Act
        client = GitHubGraphQLClient("token")

        # Assert
        self.assertEqual(client.max_wait_seconds, 3600)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_rate_limit.asyncio.sleep", new_callable=AsyncMock)
    def test_waits_when_rate_limit_low_and_wait_enabled(self, mock_sleep, mock_client_class):
        """Test that client waits when rate limit is low and wait_for_reset=True."""
        import asyncio
        from datetime import datetime, timedelta

        # Arrange - use proper ISO format without double timezone suffix
        reset_time = (datetime.now(UTC) + timedelta(seconds=10)).isoformat()
        mock_client, mock_session = create_mock_client_context_manager(
            execute_return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False}}},
                "rateLimit": {"remaining": 50, "resetAt": reset_time},  # Low remaining
            }
        )
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("token", wait_for_reset=True, max_wait_seconds=60)

        # Act
        asyncio.run(client.fetch_prs_bulk("owner", "repo"))

        # Assert - should have waited
        mock_sleep.assert_called_once()

    @patch("apps.integrations.services.github_graphql.Client")
    def test_raises_error_when_wait_disabled(self, mock_client_class):
        """Test that client raises error when rate limit low and wait_for_reset=False."""
        import asyncio
        from datetime import datetime, timedelta

        # Arrange - use proper ISO format without double timezone suffix
        reset_time = (datetime.now(UTC) + timedelta(seconds=10)).isoformat()
        mock_client, mock_session = create_mock_client_context_manager(
            execute_return_value={
                "repository": {"pullRequests": {"nodes": [], "pageInfo": {"hasNextPage": False}}},
                "rateLimit": {"remaining": 50, "resetAt": reset_time},  # Low remaining
            }
        )
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("token", wait_for_reset=False)

        # Act & Assert
        with self.assertRaises(GitHubGraphQLRateLimitError):
            asyncio.run(client.fetch_prs_bulk("owner", "repo"))


class TestGetPRCountInDateRange(TestCase):
    """Tests for GitHubGraphQLClient.get_pr_count_in_date_range method.

    This method uses GitHub Search API to get accurate PR count within a date range.
    Unlike totalCount from pullRequests connection (which returns ALL PRs), this
    returns the exact count matching the date filter.
    """

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_returns_count_from_search_api(self, mock_transport_class, mock_client_class):
        """Test that get_pr_count_in_date_range returns issueCount from search response."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Search API response with issueCount
        return_value = {
            "search": {"issueCount": 14},
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        since = datetime(2024, 12, 1, tzinfo=UTC)
        until = datetime(2025, 1, 1, tzinfo=UTC)
        result = asyncio.run(client.get_pr_count_in_date_range("owner", "repo", since=since, until=until))

        # Assert
        self.assertEqual(result, 14)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_builds_correct_search_query_with_both_dates(self, mock_transport_class, mock_client_class):
        """Test that query includes both since and until dates in search query."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {"issueCount": 10},
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        since = datetime(2024, 12, 1, tzinfo=UTC)
        until = datetime(2025, 1, 1, tzinfo=UTC)
        asyncio.run(client.get_pr_count_in_date_range("owner", "repo", since=since, until=until))

        # Assert
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        search_query = variables["searchQuery"]

        # Verify search query format: repo:owner/repo is:pr created:>=DATE created:<=DATE
        self.assertIn("repo:owner/repo", search_query)
        self.assertIn("is:pr", search_query)
        self.assertIn("created:>=2024-12-01", search_query)
        self.assertIn("created:<=2025-01-01", search_query)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_handles_only_since_date(self, mock_transport_class, mock_client_class):
        """Test that query works with just since date (no until)."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {"issueCount": 25},
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act - only since, no until
        since = datetime(2024, 12, 1, tzinfo=UTC)
        asyncio.run(client.get_pr_count_in_date_range("owner", "repo", since=since, until=None))

        # Assert
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        search_query = variables["searchQuery"]

        self.assertIn("repo:owner/repo", search_query)
        self.assertIn("is:pr", search_query)
        self.assertIn("created:>=2024-12-01", search_query)
        self.assertNotIn("created:<=", search_query)  # No until date

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_handles_only_until_date(self, mock_transport_class, mock_client_class):
        """Test that query works with just until date (no since)."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {"issueCount": 50},
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act - only until, no since
        until = datetime(2025, 1, 1, tzinfo=UTC)
        asyncio.run(client.get_pr_count_in_date_range("owner", "repo", since=None, until=until))

        # Assert
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        search_query = variables["searchQuery"]

        self.assertIn("repo:owner/repo", search_query)
        self.assertIn("is:pr", search_query)
        self.assertNotIn("created:>=", search_query)  # No since date
        self.assertIn("created:<=2025-01-01", search_query)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_returns_zero_when_no_results(self, mock_transport_class, mock_client_class):
        """Test that returns 0 when issueCount is 0."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {"issueCount": 0},
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        since = datetime(2024, 12, 1, tzinfo=UTC)
        until = datetime(2024, 12, 2, tzinfo=UTC)
        result = asyncio.run(client.get_pr_count_in_date_range("owner", "repo", since=since, until=until))

        # Assert
        self.assertEqual(result, 0)


class TestSearchPRsByDateRange(TestCase):
    """Tests for GitHubGraphQLClient.search_prs_by_date_range method.

    This method uses GitHub Search API to fetch PRs with full data within a date range.
    Unlike fetch_prs_bulk (which has no date filtering), this returns only PRs matching
    the date filter along with issueCount for accurate progress tracking.
    """

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_returns_issue_count_and_prs(self, mock_transport_class, mock_client_class):
        """Test that search_prs_by_date_range returns issueCount and PR nodes."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {
                "issueCount": 13,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "number": 123,
                        "title": "Test PR",
                        "state": "MERGED",
                        "createdAt": "2024-12-15T10:00:00Z",
                        "author": {"login": "testuser"},
                        "reviews": {"nodes": []},
                        "commits": {"nodes": []},
                        "files": {"nodes": []},
                    }
                ],
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        since = datetime(2024, 12, 1, tzinfo=UTC)
        result = asyncio.run(client.search_prs_by_date_range("owner", "repo", since=since))

        # Assert
        self.assertEqual(result["issue_count"], 13)
        self.assertEqual(len(result["prs"]), 1)
        self.assertEqual(result["prs"][0]["number"], 123)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_builds_correct_query_for_since_only(self, mock_transport_class, mock_client_class):
        """Test that query includes created:>=DATE when only since is provided."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {
                "issueCount": 5,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [],
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        since = datetime(2024, 12, 5, tzinfo=UTC)
        asyncio.run(client.search_prs_by_date_range("owner", "repo", since=since))

        # Assert
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        search_query = variables["searchQuery"]

        self.assertIn("repo:owner/repo", search_query)
        self.assertIn("is:pr", search_query)
        self.assertIn("created:>=2024-12-05", search_query)
        self.assertIn("sort:created-desc", search_query)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_builds_correct_query_for_date_range(self, mock_transport_class, mock_client_class):
        """Test that query uses created:DATE1..DATE2 format for date range."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {
                "issueCount": 15,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [],
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act - Phase 2 style: days 31-90 (since=90d ago, until=31d ago)
        since = datetime(2024, 10, 5, tzinfo=UTC)  # 90 days ago
        until = datetime(2024, 12, 4, tzinfo=UTC)  # 31 days ago
        asyncio.run(client.search_prs_by_date_range("owner", "repo", since=since, until=until))

        # Assert
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        search_query = variables["searchQuery"]

        self.assertIn("repo:owner/repo", search_query)
        self.assertIn("is:pr", search_query)
        # Date range format: created:2024-10-05..2024-12-04
        self.assertIn("created:2024-10-05..2024-12-04", search_query)
        self.assertIn("sort:created-desc", search_query)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_returns_has_next_page_info(self, mock_transport_class, mock_client_class):
        """Test that search_prs_by_date_range returns pagination info."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {
                "issueCount": 25,
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor_abc123"},
                "nodes": [{"number": 1}] * 10,  # 10 PRs
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        since = datetime(2024, 12, 1, tzinfo=UTC)
        result = asyncio.run(client.search_prs_by_date_range("owner", "repo", since=since))

        # Assert
        self.assertTrue(result["has_next_page"])
        self.assertEqual(result["end_cursor"], "cursor_abc123")
        self.assertEqual(result["issue_count"], 25)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_passes_cursor_for_pagination(self, mock_transport_class, mock_client_class):
        """Test that search_prs_by_date_range passes cursor for subsequent pages."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {
                "issueCount": 25,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [{"number": 11}] * 10,
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act - pass cursor for page 2
        since = datetime(2024, 12, 1, tzinfo=UTC)
        asyncio.run(client.search_prs_by_date_range("owner", "repo", since=since, cursor="cursor_abc123"))

        # Assert
        call_args = mock_session.execute.call_args
        variables = call_args[1]["variable_values"]
        self.assertEqual(variables["cursor"], "cursor_abc123")

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_includes_full_pr_fields(self, mock_transport_class, mock_client_class):
        """Test that search_prs_by_date_range returns full PR data including reviews, commits, files."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {
                "issueCount": 1,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "number": 456,
                        "title": "Feature: Add new API",
                        "body": "This PR adds...",
                        "state": "MERGED",
                        "createdAt": "2024-12-10T09:00:00Z",
                        "mergedAt": "2024-12-12T14:30:00Z",
                        "additions": 150,
                        "deletions": 20,
                        "isDraft": False,
                        "author": {"login": "developer1"},
                        "labels": {"nodes": [{"name": "feature", "color": "0e8a16"}]},
                        "milestone": {"title": "v1.0", "number": 1, "dueOn": "2025-01-01"},
                        "assignees": {"nodes": [{"login": "developer1"}]},
                        "closingIssuesReferences": {"nodes": [{"number": 100, "title": "Issue"}]},
                        "reviews": {
                            "nodes": [
                                {
                                    "databaseId": 1001,
                                    "state": "APPROVED",
                                    "body": "LGTM!",
                                    "submittedAt": "2024-12-11T10:00:00Z",
                                    "author": {"login": "reviewer1"},
                                }
                            ]
                        },
                        "commits": {
                            "nodes": [
                                {
                                    "commit": {
                                        "oid": "abc123def456",
                                        "message": "Add new endpoint",
                                        "additions": 50,
                                        "deletions": 5,
                                        "author": {"date": "2024-12-10T09:00:00Z", "user": {"login": "developer1"}},
                                    }
                                }
                            ]
                        },
                        "files": {
                            "nodes": [
                                {"path": "src/api/endpoint.py", "additions": 50, "deletions": 5, "changeType": "ADDED"}
                            ]
                        },
                    }
                ],
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        since = datetime(2024, 12, 1, tzinfo=UTC)
        result = asyncio.run(client.search_prs_by_date_range("owner", "repo", since=since))

        # Assert
        pr = result["prs"][0]
        self.assertEqual(pr["number"], 456)
        self.assertEqual(pr["title"], "Feature: Add new API")
        self.assertEqual(pr["additions"], 150)
        self.assertEqual(pr["deletions"], 20)
        self.assertEqual(len(pr["reviews"]["nodes"]), 1)
        self.assertEqual(len(pr["commits"]["nodes"]), 1)
        self.assertEqual(len(pr["files"]["nodes"]), 1)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_handles_empty_results(self, mock_transport_class, mock_client_class):
        """Test that search_prs_by_date_range handles empty results correctly."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {
                "issueCount": 0,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [],
            },
            "rateLimit": {"remaining": 5000},
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        since = datetime(2024, 12, 1, tzinfo=UTC)
        result = asyncio.run(client.search_prs_by_date_range("owner", "repo", since=since))

        # Assert
        self.assertEqual(result["issue_count"], 0)
        self.assertEqual(len(result["prs"]), 0)
        self.assertFalse(result["has_next_page"])

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_raises_rate_limit_error(self, mock_transport_class, mock_client_class):
        """Test that search_prs_by_date_range raises error when rate limit low."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        return_value = {
            "search": {"issueCount": 10, "pageInfo": {}, "nodes": []},
            "rateLimit": {"remaining": 50},  # Low rate limit
        }
        mock_client, mock_session = create_mock_client_context_manager(return_value)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token", wait_for_reset=False)

        # Act & Assert
        since = datetime(2024, 12, 1, tzinfo=UTC)
        with self.assertRaises(GitHubGraphQLRateLimitError):
            asyncio.run(client.search_prs_by_date_range("owner", "repo", since=since))

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_retries_on_timeout(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that search_prs_by_date_range retries on timeout."""
        import asyncio
        from datetime import datetime

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        success_response = {
            "search": {
                "issueCount": 5,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [],
            },
            "rateLimit": {"remaining": 5000},
        }

        # Fail once, then succeed
        mock_client, mock_session = create_mock_client_context_manager()
        mock_session.execute = AsyncMock(side_effect=[TimeoutError(), success_response])
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")

        # Act
        since = datetime(2024, 12, 1, tzinfo=UTC)
        result = asyncio.run(client.search_prs_by_date_range("owner", "repo", since=since, max_retries=3))

        # Assert
        self.assertEqual(mock_session.execute.call_count, 2)
        self.assertEqual(result["issue_count"], 5)


class TestExecuteWithRetry(TestCase):
    """TDD tests for _execute_with_retry() helper method.

    This class provides comprehensive unit tests for the centralized retry logic,
    testing all code paths including success, timeout, rate limit, and error cases.
    """

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_execute_with_retry_returns_result_on_success(self, mock_transport_class, mock_client_class):
        """Test that _execute_with_retry returns result on successful execution."""
        import asyncio

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        expected_result = {
            "data": {"test": "value"},
            "rateLimit": {"remaining": 5000, "resetAt": "2024-01-01T00:00:00Z"},
        }
        mock_client, mock_session = create_mock_client_context_manager(expected_result)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")
        mock_query = MagicMock()

        # Act
        result = asyncio.run(
            client._execute_with_retry(
                query=mock_query,
                variables={"key": "value"},
                operation_name="test_operation",
            )
        )

        # Assert
        self.assertEqual(result, expected_result)
        mock_session.execute.assert_called_once()

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_execute_with_retry_passes_rate_limit_error_through_immediately(
        self, mock_transport_class, mock_client_class
    ):
        """Test that _execute_with_retry does not retry on rate limit error - passes through immediately."""
        import asyncio

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Return low rate limit (triggers error after execution)
        low_rate_limit_result = {
            "data": {"test": "value"},
            "rateLimit": {"remaining": 50, "resetAt": "2024-01-01T00:00:00Z"},  # Below threshold
        }
        mock_client, mock_session = create_mock_client_context_manager(low_rate_limit_result)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token", wait_for_reset=False)
        mock_query = MagicMock()

        # Act & Assert
        with self.assertRaises(GitHubGraphQLRateLimitError):
            asyncio.run(
                client._execute_with_retry(
                    query=mock_query,
                    variables={},
                    operation_name="test_operation",
                )
            )

        # Should only call once - no retry on rate limit
        self.assertEqual(mock_session.execute.call_count, 1)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_execute_with_retry_retries_on_timeout_then_succeeds(
        self, mock_transport_class, mock_client_class, mock_sleep
    ):
        """Test that _execute_with_retry retries on timeout and eventually succeeds."""
        import asyncio

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        success_response = {
            "data": {"success": True},
            "rateLimit": {"remaining": 5000, "resetAt": "2024-01-01T00:00:00Z"},
        }

        # Fail twice with timeout, then succeed
        mock_client, mock_session = create_mock_client_context_manager()
        mock_session.execute = AsyncMock(side_effect=[TimeoutError(), TimeoutError(), success_response])
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")
        mock_query = MagicMock()

        # Act
        result = asyncio.run(
            client._execute_with_retry(
                query=mock_query,
                variables={},
                operation_name="test_operation",
                max_retries=3,
            )
        )

        # Assert
        self.assertEqual(result, success_response)
        self.assertEqual(mock_session.execute.call_count, 3)
        # Verify exponential backoff was used: sleep(1), sleep(2)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(1)  # 2^0
        mock_sleep.assert_any_call(2)  # 2^1

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_execute_with_retry_raises_timeout_error_after_max_retries(
        self, mock_transport_class, mock_client_class, mock_sleep
    ):
        """Test that _execute_with_retry raises GitHubGraphQLTimeoutError after max retries exhausted."""
        import asyncio

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Always timeout
        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=TimeoutError())
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")
        mock_query = MagicMock()

        # Act & Assert
        with self.assertRaises(GitHubGraphQLTimeoutError) as context:
            asyncio.run(
                client._execute_with_retry(
                    query=mock_query,
                    variables={},
                    operation_name="test_operation(context)",
                    max_retries=3,
                )
            )

        # Verify error message contains operation name and retry count
        self.assertIn("test_operation(context)", str(context.exception))
        self.assertIn("3", str(context.exception))
        self.assertEqual(mock_session.execute.call_count, 3)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_execute_with_retry_converts_generic_exception_to_graphql_error(
        self, mock_transport_class, mock_client_class
    ):
        """Test that _execute_with_retry converts generic exceptions to GitHubGraphQLError without retry."""
        import asyncio

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        # Raise a generic exception (should not retry)
        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=ValueError("Invalid query"))
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")
        mock_query = MagicMock()

        # Act & Assert
        with self.assertRaises(GitHubGraphQLError) as context:
            asyncio.run(
                client._execute_with_retry(
                    query=mock_query,
                    variables={},
                    operation_name="test_operation",
                )
            )

        # Verify error message contains operation name and original error type
        self.assertIn("test_operation", str(context.exception))
        self.assertIn("ValueError", str(context.exception))
        # Should only call once - no retry on generic exceptions
        self.assertEqual(mock_session.execute.call_count, 1)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_execute_with_retry_uses_exponential_backoff(self, mock_transport_class, mock_client_class, mock_sleep):
        """Test that _execute_with_retry uses exponential backoff timing (1s, 2s, 4s)."""
        import asyncio

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        success_response = {
            "data": {},
            "rateLimit": {"remaining": 5000},
        }

        # Fail 3 times, succeed on 4th attempt
        mock_client, mock_session = create_mock_client_context_manager()
        mock_session.execute = AsyncMock(side_effect=[TimeoutError(), TimeoutError(), TimeoutError(), success_response])
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")
        mock_query = MagicMock()

        # Act
        asyncio.run(
            client._execute_with_retry(
                query=mock_query,
                variables={},
                operation_name="test_backoff",
                max_retries=4,
            )
        )

        # Assert - verify exponential backoff: 2^0=1, 2^1=2, 2^2=4
        self.assertEqual(mock_sleep.call_count, 3)
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertEqual(calls, [1, 2, 4])

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_execute_with_retry_respects_max_retries_parameter(self, mock_transport_class, mock_client_class):
        """Test that _execute_with_retry respects the max_retries parameter."""
        import asyncio

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=TimeoutError())
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")
        mock_query = MagicMock()

        # Act & Assert - with max_retries=1, should only try once
        with self.assertRaises(GitHubGraphQLTimeoutError):
            asyncio.run(
                client._execute_with_retry(
                    query=mock_query,
                    variables={},
                    operation_name="test_max_1",
                    max_retries=1,
                )
            )

        self.assertEqual(mock_session.execute.call_count, 1)

    @patch("apps.integrations.services.github_graphql.Client")
    @patch("apps.integrations.services.github_graphql.AIOHTTPTransport")
    def test_execute_with_retry_preserves_original_exception_as_cause(self, mock_transport_class, mock_client_class):
        """Test that _execute_with_retry preserves the original exception as __cause__."""
        import asyncio

        # Arrange
        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        original_error = ValueError("Original error message")
        mock_client, mock_session = create_mock_client_context_manager(execute_side_effect=original_error)
        mock_client_class.return_value = mock_client

        client = GitHubGraphQLClient("test_token")
        mock_query = MagicMock()

        # Act & Assert
        with self.assertRaises(GitHubGraphQLError) as context:
            asyncio.run(
                client._execute_with_retry(
                    query=mock_query,
                    variables={},
                    operation_name="test_operation",
                )
            )

        # Verify original exception is preserved as cause
        self.assertIsInstance(context.exception.__cause__, ValueError)
        self.assertEqual(str(context.exception.__cause__), "Original error message")
