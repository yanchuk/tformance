"""Tests for GitHub client service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.factories import (
    GitHubAppInstallationFactory,
    IntegrationCredentialFactory,
)
from apps.integrations.models import IntegrationCredential
from apps.integrations.services.github_client import (
    NoGitHubConnectionError,
    get_github_client,
    get_github_client_for_team,
)
from apps.metrics.factories import TeamFactory


class TestGetGitHubClient(TestCase):
    """Tests for creating authenticated GitHub client instances."""

    @patch("apps.integrations.services.github_client.Github")
    def test_get_github_client_returns_github_instance(self, mock_github_class):
        """Test that get_github_client returns a Github instance."""
        # Arrange
        access_token = "gho_test_token_123"
        mock_github_instance = MagicMock()
        mock_github_class.return_value = mock_github_instance

        # Act
        result = get_github_client(access_token)

        # Assert
        self.assertEqual(result, mock_github_instance)

    @patch("apps.integrations.services.github_client.Github")
    def test_get_github_client_passes_access_token_to_github(self, mock_github_class):
        """Test that get_github_client passes the access token to Github constructor."""
        # Arrange
        access_token = "gho_test_token_456"
        mock_github_instance = MagicMock()
        mock_github_class.return_value = mock_github_instance

        # Act
        get_github_client(access_token)

        # Assert
        mock_github_class.assert_called_once_with(access_token)

    @patch("apps.integrations.services.github_client.Github")
    def test_get_github_client_works_with_different_token_formats(self, mock_github_class):
        """Test that get_github_client handles different token formats."""
        # Arrange
        tokens = [
            "gho_short",
            "gho_1234567890abcdefghijklmnopqrstuvwxyz",
            "ghp_personal_access_token",
        ]
        mock_github_instance = MagicMock()
        mock_github_class.return_value = mock_github_instance

        for token in tokens:
            with self.subTest(token=token):
                # Act
                result = get_github_client(token)

                # Assert
                self.assertEqual(result, mock_github_instance)
                mock_github_class.assert_called_with(token)


class TestGetGitHubClientForTeam(TestCase):
    """Tests for get_github_client_for_team with priority-based auth selection."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    @patch("apps.integrations.services.github_client.get_installation_client")
    def test_get_github_client_prefers_app_installation(self, mock_get_installation_client):
        """Test that GitHub App installation is preferred when available."""
        # Arrange
        installation = GitHubAppInstallationFactory(
            team=self.team,
            is_active=True,
            installation_id=12345678,
        )
        mock_github_instance = MagicMock()
        mock_get_installation_client.return_value = mock_github_instance

        # Act
        result = get_github_client_for_team(self.team)

        # Assert
        self.assertEqual(result, mock_github_instance)
        mock_get_installation_client.assert_called_once_with(installation.installation_id)

    @patch("apps.integrations.services.github_client.Github")
    def test_get_github_client_falls_back_to_oauth(self, mock_github_class):
        """Test that OAuth credential is used when no app installation exists."""
        # Arrange - no app installation, only OAuth credential
        credential = IntegrationCredentialFactory(
            team=self.team,
            provider=IntegrationCredential.PROVIDER_GITHUB,
            access_token="gho_oauth_token_123",
        )
        mock_github_instance = MagicMock()
        mock_github_class.return_value = mock_github_instance

        # Act
        result = get_github_client_for_team(self.team)

        # Assert
        self.assertEqual(result, mock_github_instance)
        mock_github_class.assert_called_once_with(credential.access_token)

    def test_get_github_client_no_connection_raises(self):
        """Test that NoGitHubConnectionError is raised when no auth method exists."""
        # Arrange - team with no GitHub connection (no app installation, no OAuth)
        team_without_github = TeamFactory()

        # Act & Assert
        with self.assertRaises(NoGitHubConnectionError) as context:
            get_github_client_for_team(team_without_github)

        self.assertIn("no github connection", str(context.exception).lower())

    @patch("apps.integrations.services.github_client.get_installation_client")
    @patch("apps.integrations.services.github_client.Github")
    def test_get_github_client_prefers_app_over_oauth(self, mock_github_class, mock_get_installation_client):
        """Test that app installation is preferred over OAuth when both exist."""
        # Arrange - both app installation and OAuth credential exist
        installation = GitHubAppInstallationFactory(
            team=self.team,
            is_active=True,
            installation_id=99999999,
        )
        IntegrationCredentialFactory(
            team=self.team,
            provider=IntegrationCredential.PROVIDER_GITHUB,
            access_token="gho_should_not_be_used",
        )
        mock_app_client = MagicMock(name="app_client")
        mock_get_installation_client.return_value = mock_app_client

        # Act
        result = get_github_client_for_team(self.team)

        # Assert - app installation client should be used, not OAuth
        self.assertEqual(result, mock_app_client)
        mock_get_installation_client.assert_called_once_with(installation.installation_id)
        mock_github_class.assert_not_called()

    @patch("apps.integrations.services.github_client.Github")
    def test_get_github_client_uses_oauth_for_inactive_app(self, mock_github_class):
        """Test that OAuth is used when app installation is inactive."""
        # Arrange - inactive app installation, active OAuth credential
        GitHubAppInstallationFactory(
            team=self.team,
            is_active=False,  # Inactive app
            installation_id=11111111,
        )
        credential = IntegrationCredentialFactory(
            team=self.team,
            provider=IntegrationCredential.PROVIDER_GITHUB,
            access_token="gho_fallback_token",
        )
        mock_github_instance = MagicMock()
        mock_github_class.return_value = mock_github_instance

        # Act
        result = get_github_client_for_team(self.team)

        # Assert - should use OAuth since app is inactive
        self.assertEqual(result, mock_github_instance)
        mock_github_class.assert_called_once_with(credential.access_token)


class TestNoGitHubConnectionError(TestCase):
    """Tests for NoGitHubConnectionError exception class."""

    def test_no_github_connection_error_is_exception(self):
        """Test that NoGitHubConnectionError is a catchable exception."""
        # Act & Assert
        with self.assertRaises(NoGitHubConnectionError):
            raise NoGitHubConnectionError("Test error message")

    def test_no_github_connection_error_inherits_from_exception(self):
        """Test that NoGitHubConnectionError inherits from Exception."""
        self.assertTrue(issubclass(NoGitHubConnectionError, Exception))

    def test_no_github_connection_error_message(self):
        """Test that NoGitHubConnectionError preserves error message."""
        error_message = "Team has no GitHub connection"
        error = NoGitHubConnectionError(error_message)
        self.assertEqual(str(error), error_message)
