"""Tests for GitHub App service module.

RED phase: These tests are written BEFORE the service module exists.
They should all FAIL until the service is implemented.
"""

import time
from unittest.mock import MagicMock, patch

import jwt
from django.test import TestCase, override_settings


class TestGitHubAppError(TestCase):
    """Tests for GitHubAppError exception class."""

    def test_github_app_error_is_exception(self):
        """Test that GitHubAppError can be raised and caught as an exception."""
        from apps.integrations.services.github_app import GitHubAppError

        with self.assertRaises(GitHubAppError):
            raise GitHubAppError("Test error message")

    def test_github_app_error_contains_message(self):
        """Test that GitHubAppError preserves error message."""
        from apps.integrations.services.github_app import GitHubAppError

        try:
            raise GitHubAppError("Installation not found")
        except GitHubAppError as e:
            self.assertIn("Installation not found", str(e))

    def test_github_app_error_is_subclass_of_exception(self):
        """Test that GitHubAppError is a subclass of Exception."""
        from apps.integrations.services.github_app import GitHubAppError

        self.assertTrue(issubclass(GitHubAppError, Exception))


# RSA private key for testing JWT generation (DO NOT USE IN PRODUCTION)
# Generated with: openssl genrsa -out test.pem 2048
TEST_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAwCfpHUgkZZ6v8xFbDn89ZQzzFnss570i2Y/ma+nNhZ87bCtH
uUVACCdTPPAzadlCKGWRF5mQMZC7uf1LTXKbdUwF/7LmvCdRAMh/LqdrxSGa16KF
wZNR/xtn7KLzC6hMck8UZyzv3Enixn9hi98MGisP/RON5wVBy5ZJ3T+zuObsuJhF
Yd3qTYGz2z4cDR+gxm6QlGhXeJgvyDQFOWMh0GtgBSbmXxca3XxFL110Zy/UaJrv
gGKZ8Vuhtr6/dQkFUo2dA0GNK0A7kTDtxLZXn58PhSBmyxCPCsh31mOEVyEFHPPS
G//sXm83CKAOfsJr1AAhIYeL15KLyiYFVwjPpQIDAQABAoIBABw/QbN+QWt20mKm
8H3HEp1iM/HgFY/Ta+YTk0nVytKTv8Z87kQ7+9e3ADN7E/PBbkpF8/hGKL5Aingi
1gkCifvKOy+Fewm5tdypnJidH+iQshR03bjBEVKxEqvkoFncWbCME3G/V1tIuT94
xjwrg7ntDqKjVz7YtP1akG0nyiGp/wtx/Y/N7Cfr1LVWWuZqhitUWJwbFcq2xE+G
Zz4smGZMs/hyM1LotsUepTmilkvjBADfE5pO/+4VyHxeS2sbl4eDTf5EEoo83O3l
pHx1wywmZ0mQ3U73Is40QmCU2FefSsy04RQbelDyoZjjFcZSLzuKt+Z/Q9WPKu5O
O8CqJtkCgYEA+LeOZ9c0axID9AhqkD3ZvU57fLQ+dxKUoTpTi7nXdcQXmhdw4le2
/LBg6E02m8cq3MLVLPkwFnLWx0PMLer1L5g+Q8+JcJ/5IPXQN8kTXZ0Fs7nO9v4o
SW00QKWaVyKFmkny1D1aIicVeqlcZ66obHept6uXkDz0AeHkQBnih/MCgYEAxchb
vDmhJ350U237WHN0G/c35vS9JPYFtWVBSNroBeSLnxoiwbo1L2ZOerC7VeAhdMEP
daS64K6R29OmoTupXkgGmx0GRDw2tEhL+V5EcPOEYZZ84t02B4GmRPxnyko/MwWb
RxPUwklJ1Lmy+RjpVBTON0JoqqRfEgaf/sVqiAcCgYEAydFQaaxz6Wnd8Vge+Fpn
47fadi9f/IkEN+u3PUsYrYPnzu60d8XLQzHwALAe3rr3adli17KANccLxveZp6zf
Nbao16eBE/WLVxZ/1bSA1VaD+PmOGlfT4vkNDGQUYB4wISleNKBwEgR65mSlCbDt
E87p1ZMUUkNTkG93Ihie+8cCgYBy+mYyB0KjZgUUF0TeB8hBFbf+4NowaYGqEWIh
i3kFK/brGFOKUcjndE89Tg6p/rEUYcOt/YTSZ0nOBL3Cz59HexG0DOx+sI6QwdLA
9kdNbpPP859Id5cYSAuz4RQpan5RF/pMGMA/7kEolIfx/cRvJ+U2BLo6MXI/VXCf
uH6U8wKBgB/3sZVezvADYizEnOO52PTEBA7FNd1myyLxv+1lYNmucOqRQC37Ln8S
AXd3AoiQGn6/rt2nfv7ccyI07Rbgjku3nVwnpQ8yYPq7R/8v7lExmmk+IIZj9Rz5
ohCiNFkGpn9lBYHRAMNZE4vJAfv6oaJG0TmEE35EYHrplh5rr3Nx
-----END RSA PRIVATE KEY-----"""

TEST_APP_ID = "123456"


@override_settings(
    GITHUB_APP_ID=TEST_APP_ID,
    GITHUB_APP_PRIVATE_KEY=TEST_PRIVATE_KEY,
)
class TestGetJwt(TestCase):
    """Tests for get_jwt() function."""

    def test_get_jwt_returns_valid_jwt(self):
        """Test that get_jwt returns a valid JWT string signed with RS256."""
        from apps.integrations.services.github_app import get_jwt

        token = get_jwt()

        # Should be a string
        self.assertIsInstance(token, str)

        # Should be decodable as JWT (skip signature verification for unit test)
        decoded = jwt.decode(token, options={"verify_signature": False})
        self.assertIsInstance(decoded, dict)

    def test_get_jwt_expires_in_10_minutes(self):
        """Test that JWT expiry is approximately 600 seconds (10 minutes) from now."""
        from apps.integrations.services.github_app import get_jwt

        before_time = int(time.time())
        token = get_jwt()
        after_time = int(time.time())

        decoded = jwt.decode(token, options={"verify_signature": False})

        # exp should be ~600 seconds from iat
        exp = decoded["exp"]
        iat = decoded["iat"]

        # Expiry should be 600 seconds from issued at
        self.assertEqual(exp - iat, 600)

        # iat should be approximately now (within a few seconds)
        self.assertGreaterEqual(iat, before_time)
        self.assertLessEqual(iat, after_time + 1)

    def test_get_jwt_includes_app_id_as_issuer(self):
        """Test that JWT includes GITHUB_APP_ID as the 'iss' (issuer) claim."""
        from apps.integrations.services.github_app import get_jwt

        token = get_jwt()
        decoded = jwt.decode(token, options={"verify_signature": False})

        # iss claim should match GITHUB_APP_ID
        self.assertIn("iss", decoded)
        self.assertEqual(decoded["iss"], TEST_APP_ID)

    def test_get_jwt_uses_rs256_algorithm(self):
        """Test that JWT is signed with RS256 algorithm."""
        from apps.integrations.services.github_app import get_jwt

        token = get_jwt()

        # Get the header to check algorithm
        header = jwt.get_unverified_header(token)
        self.assertEqual(header["alg"], "RS256")


@override_settings(
    GITHUB_APP_ID=TEST_APP_ID,
    GITHUB_APP_PRIVATE_KEY=TEST_PRIVATE_KEY,
)
class TestGetInstallationToken(TestCase):
    """Tests for get_installation_token() function."""

    @patch("apps.integrations.services.github_app.GithubIntegration")
    def test_get_installation_token_success(self, mock_github_integration_class):
        """Test that get_installation_token returns token string on success."""
        from apps.integrations.services.github_app import get_installation_token

        # Mock GithubIntegration
        mock_integration = MagicMock()
        mock_github_integration_class.return_value = mock_integration

        # Mock the get_access_token method
        mock_token = MagicMock()
        mock_token.token = "ghs_test_installation_token_12345"
        mock_integration.get_access_token.return_value = mock_token

        installation_id = 12345678

        result = get_installation_token(installation_id)

        # Should return the token string
        self.assertEqual(result, "ghs_test_installation_token_12345")

        # Verify GithubIntegration was initialized correctly
        mock_github_integration_class.assert_called_once()
        call_args = mock_github_integration_class.call_args

        # Check that app_id is passed (as int)
        self.assertEqual(call_args[1]["integration_id"], int(TEST_APP_ID))

        # Verify get_access_token was called with installation_id
        mock_integration.get_access_token.assert_called_once_with(installation_id)

    @patch("apps.integrations.services.github_app.GithubIntegration")
    def test_get_installation_token_not_found_raises_error(self, mock_github_integration_class):
        """Test that get_installation_token raises GitHubAppError when installation not found."""
        from github import GithubException

        from apps.integrations.services.github_app import GitHubAppError, get_installation_token

        # Mock GithubIntegration
        mock_integration = MagicMock()
        mock_github_integration_class.return_value = mock_integration

        # Mock get_access_token to raise exception (installation not found)
        mock_integration.get_access_token.side_effect = GithubException(
            status=404, data={"message": "Integration not found"}
        )

        installation_id = 99999999

        with self.assertRaises(GitHubAppError) as context:
            get_installation_token(installation_id)

        self.assertIn("404", str(context.exception))

    @patch("apps.integrations.services.github_app.GithubIntegration")
    def test_get_installation_token_handles_unauthorized_error(self, mock_github_integration_class):
        """Test that get_installation_token raises GitHubAppError on 401 unauthorized."""
        from github import GithubException

        from apps.integrations.services.github_app import GitHubAppError, get_installation_token

        # Mock GithubIntegration
        mock_integration = MagicMock()
        mock_github_integration_class.return_value = mock_integration

        # Mock get_access_token to raise 401 error
        mock_integration.get_access_token.side_effect = GithubException(status=401, data={"message": "Bad credentials"})

        installation_id = 12345678

        with self.assertRaises(GitHubAppError) as context:
            get_installation_token(installation_id)

        self.assertIn("401", str(context.exception))


@override_settings(
    GITHUB_APP_ID=TEST_APP_ID,
    GITHUB_APP_PRIVATE_KEY=TEST_PRIVATE_KEY,
)
class TestGetInstallationClient(TestCase):
    """Tests for get_installation_client() function."""

    @patch("apps.integrations.services.github_app.get_installation_token")
    @patch("apps.integrations.services.github_app.Github")
    def test_get_installation_client_returns_github_instance(self, mock_github_class, mock_get_token):
        """Test that get_installation_client returns a Github client instance."""
        from github import Github

        from apps.integrations.services.github_app import get_installation_client

        # Mock get_installation_token
        mock_get_token.return_value = "ghs_test_token_12345"

        # Mock Github class
        mock_github_instance = MagicMock(spec=Github)
        mock_github_class.return_value = mock_github_instance

        installation_id = 12345678

        result = get_installation_client(installation_id)

        # Should return a Github instance
        self.assertEqual(result, mock_github_instance)

        # Verify get_installation_token was called
        mock_get_token.assert_called_once_with(installation_id)

        # Verify Github was initialized with the token
        mock_github_class.assert_called_once_with("ghs_test_token_12345")

    @patch("apps.integrations.services.github_app.get_installation_token")
    def test_get_installation_client_propagates_error(self, mock_get_token):
        """Test that get_installation_client propagates GitHubAppError from get_installation_token."""
        from apps.integrations.services.github_app import GitHubAppError, get_installation_client

        # Mock get_installation_token to raise error
        mock_get_token.side_effect = GitHubAppError("Installation not found")

        installation_id = 99999999

        with self.assertRaises(GitHubAppError):
            get_installation_client(installation_id)


@override_settings(
    GITHUB_APP_ID=TEST_APP_ID,
    GITHUB_APP_PRIVATE_KEY=TEST_PRIVATE_KEY,
)
class TestGetInstallation(TestCase):
    """Tests for get_installation() function."""

    @patch("apps.integrations.services.github_app.GithubIntegration")
    def test_get_installation_returns_dict(self, mock_github_integration_class):
        """Test that get_installation returns a dictionary with installation details."""
        from apps.integrations.services.github_app import get_installation

        # Mock GithubIntegration
        mock_integration = MagicMock()
        mock_github_integration_class.return_value = mock_integration

        # Mock installation object
        mock_installation = MagicMock()
        mock_installation.id = 12345678
        mock_installation.account.login = "acme-corp"
        mock_installation.account.id = 87654321
        mock_installation.account.type = "Organization"
        mock_installation.permissions = {"contents": "read", "pull_requests": "write"}
        mock_installation.events = ["push", "pull_request"]
        mock_installation.repository_selection = "selected"

        mock_integration.get_installation.return_value = mock_installation

        installation_id = 12345678

        result = get_installation(installation_id)

        # Should return a dict
        self.assertIsInstance(result, dict)

        # Should contain expected keys
        self.assertIn("account", result)
        self.assertIn("permissions", result)
        self.assertIn("events", result)

        # Verify GithubIntegration was called
        mock_integration.get_installation.assert_called_once_with(installation_id)

    @patch("apps.integrations.services.github_app.GithubIntegration")
    def test_get_installation_not_found_raises_error(self, mock_github_integration_class):
        """Test that get_installation raises GitHubAppError when installation not found."""
        from github import GithubException

        from apps.integrations.services.github_app import GitHubAppError, get_installation

        # Mock GithubIntegration
        mock_integration = MagicMock()
        mock_github_integration_class.return_value = mock_integration

        # Mock get_installation to raise exception
        mock_integration.get_installation.side_effect = GithubException(status=404, data={"message": "Not Found"})

        installation_id = 99999999

        with self.assertRaises(GitHubAppError):
            get_installation(installation_id)


@override_settings(
    GITHUB_APP_ID=TEST_APP_ID,
    GITHUB_APP_PRIVATE_KEY=TEST_PRIVATE_KEY,
)
class TestGetInstallationRepositories(TestCase):
    """Tests for get_installation_repositories() function."""

    @patch("apps.integrations.services.github_app.get_installation_client")
    def test_get_installation_repositories_returns_list(self, mock_get_client):
        """Test that get_installation_repositories returns a list of repository dicts."""
        from apps.integrations.services.github_app import get_installation_repositories

        # Mock Github client
        mock_github = MagicMock()
        mock_get_client.return_value = mock_github

        # Mock installation object with repositories
        mock_installation = MagicMock()

        # Create mock repo objects
        mock_repo1 = MagicMock()
        mock_repo1.id = 123456
        mock_repo1.full_name = "acme-corp/backend"
        mock_repo1.name = "backend"
        mock_repo1.private = False

        mock_repo2 = MagicMock()
        mock_repo2.id = 123457
        mock_repo2.full_name = "acme-corp/frontend"
        mock_repo2.name = "frontend"
        mock_repo2.private = True

        mock_installation.get_repos.return_value = [mock_repo1, mock_repo2]
        mock_github.get_installation.return_value = mock_installation

        installation_id = 12345678

        result = get_installation_repositories(installation_id)

        # Should return a list
        self.assertIsInstance(result, list)

        # Should have 2 repos
        self.assertEqual(len(result), 2)

        # Each item should be a dict
        self.assertIsInstance(result[0], dict)
        self.assertIsInstance(result[1], dict)

        # Verify get_installation_client was called
        mock_get_client.assert_called_once_with(installation_id)

    @patch("apps.integrations.services.github_app.get_installation_client")
    def test_get_installation_repositories_returns_empty_list_when_no_repos(self, mock_get_client):
        """Test that get_installation_repositories returns empty list when no repos accessible."""
        from apps.integrations.services.github_app import get_installation_repositories

        # Mock Github client
        mock_github = MagicMock()
        mock_get_client.return_value = mock_github

        # Mock installation object with no repositories
        mock_installation = MagicMock()
        mock_installation.get_repos.return_value = []
        mock_github.get_installation.return_value = mock_installation

        installation_id = 12345678

        result = get_installation_repositories(installation_id)

        # Should return empty list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("apps.integrations.services.github_app.get_installation_client")
    def test_get_installation_repositories_propagates_error(self, mock_get_client):
        """Test that get_installation_repositories propagates GitHubAppError."""
        from apps.integrations.services.github_app import GitHubAppError, get_installation_repositories

        # Mock get_installation_client to raise error
        mock_get_client.side_effect = GitHubAppError("Installation not found")

        installation_id = 99999999

        with self.assertRaises(GitHubAppError):
            get_installation_repositories(installation_id)
