"""Tests for GitHub client service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_client import get_github_client


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
