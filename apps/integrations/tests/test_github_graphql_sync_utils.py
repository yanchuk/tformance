"""Tests for GitHub GraphQL sync utility functions.

Tests for _get_access_token to prefer App installation over OAuth.
"""

import asyncio
from datetime import timedelta
from unittest.mock import patch

from django.test import TransactionTestCase
from django.utils import timezone

from apps.integrations.exceptions import GitHubAuthError
from apps.integrations.factories import (
    GitHubAppInstallationFactory,
    GitHubIntegrationFactory,
    TrackedRepositoryFactory,
)
from apps.integrations.services.github_graphql_sync._utils import _get_access_token
from apps.metrics.factories import TeamFactory
from apps.teams.context import unset_current_team


class TestGetAccessTokenPrefersAppInstallation(TransactionTestCase):
    """Tests for _get_access_token preferring App installation over OAuth."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.app_installation = GitHubAppInstallationFactory(
            team=self.team,
            cached_token="ghs_app_token_123",
            token_expires_at=timezone.now() + timedelta(hours=1),
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_get_access_token_returns_app_installation_token_when_available(self):
        """Test that _get_access_token returns app_installation token when available."""
        # Create repo with both OAuth integration and App installation
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            app_installation=self.app_installation,
        )

        # Act
        result = asyncio.run(_get_access_token(repo.id))

        # Assert - should use app_installation token, not OAuth
        self.assertEqual(result, "ghs_app_token_123")

    def test_get_access_token_falls_back_to_oauth_when_no_app_installation(self):
        """Test that _get_access_token falls back to OAuth when no app_installation."""
        # Create repo with only OAuth integration (no app_installation)
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            app_installation=None,
        )

        # Act
        result = asyncio.run(_get_access_token(repo.id))

        # Assert - should fall back to OAuth credential
        self.assertIsNotNone(result)
        # OAuth credential access_token comes from IntegrationCredential
        self.assertEqual(result, self.integration.credential.access_token)

    def test_get_access_token_raises_when_no_auth(self):
        """Test that _get_access_token raises GitHubAuthError when neither App nor OAuth available."""
        # Create repo with no app_installation and no integration
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=None,
            app_installation=None,
            full_name="owner/test-repo",
        )

        # Act & Assert
        with self.assertRaises(GitHubAuthError) as context:
            asyncio.run(_get_access_token(repo.id))

        # Verify error message includes repo name
        self.assertIn("owner/test-repo", str(context.exception))

    def test_get_access_token_error_includes_guidance(self):
        """Test that GitHubAuthError includes guidance to re-add repository."""
        # Create repo with no authentication
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=None,
            app_installation=None,
            full_name="myorg/my-project",
        )

        # Act & Assert
        with self.assertRaises(GitHubAuthError) as context:
            asyncio.run(_get_access_token(repo.id))

        # Verify error message includes guidance
        error_msg = str(context.exception)
        self.assertIn("myorg/my-project", error_msg)
        self.assertIn("re-add", error_msg.lower())

    def test_get_access_token_returns_none_for_nonexistent_repo(self):
        """Test that _get_access_token returns None for non-existent repo."""
        # Act
        result = asyncio.run(_get_access_token(999999))

        # Assert
        self.assertIsNone(result)

    def test_get_access_token_refreshes_expired_app_installation_token(self):
        """Test that _get_access_token triggers refresh when App token is expired."""
        # Set up expired app installation
        self.app_installation.cached_token = "ghs_old_expired"
        self.app_installation.token_expires_at = timezone.now() - timedelta(hours=1)
        self.app_installation.save()

        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            app_installation=self.app_installation,
        )

        new_token = "ghs_new_refreshed_token"
        new_expiry = timezone.now() + timedelta(hours=1)

        with patch("apps.integrations.services.github_app.get_installation_token_with_expiry") as mock_get_token:
            mock_get_token.return_value = (new_token, new_expiry)

            # Act
            result = asyncio.run(_get_access_token(repo.id))

            # Assert - should return refreshed token
            self.assertEqual(result, new_token)
            mock_get_token.assert_called_once()
