"""Tests for GitHub sync auth helper.

Tests the get_access_token function that handles authentication
for both GitHub App installations and OAuth credentials.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.integrations.exceptions import GitHubAuthError
from apps.integrations.factories import (
    GitHubAppInstallationFactory,
    GitHubIntegrationFactory,
    TrackedRepositoryFactory,
)
from apps.integrations.services.github_sync.auth import get_access_token
from apps.metrics.factories import TeamFactory


class TestGetAccessToken(TestCase):
    """Tests for get_access_token() function."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all test methods."""
        cls.team = TeamFactory()

    def test_with_only_app_installation(self):
        """Test get_access_token returns App installation token when only App is configured."""
        # Create App installation
        app_installation = GitHubAppInstallationFactory(team=self.team)

        # Create repo with app_installation only (no OAuth integration)
        tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=None,  # No OAuth
            app_installation=app_installation,
        )

        # Mock the get_access_token method on the installation
        with patch.object(app_installation, "get_access_token", return_value="app_token_123"):
            # Need to re-fetch to get fresh reference
            tracked_repo.app_installation = app_installation
            token = get_access_token(tracked_repo)

        self.assertEqual(token, "app_token_123")

    def test_with_only_oauth_credential(self):
        """Test get_access_token returns OAuth token when only OAuth is configured."""
        # Create OAuth integration with credential
        integration = GitHubIntegrationFactory(team=self.team)

        # Create repo with OAuth only (no App installation)
        tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            app_installation=None,  # No App installation
        )

        token = get_access_token(tracked_repo)

        # Should return the OAuth access token
        self.assertEqual(token, integration.credential.access_token)

    def test_prefers_app_installation_over_oauth(self):
        """Test get_access_token prefers App installation when both are configured."""
        # Create both OAuth and App installation
        integration = GitHubIntegrationFactory(team=self.team)
        app_installation = GitHubAppInstallationFactory(team=self.team)

        # Create repo with both
        tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=integration,
            app_installation=app_installation,
        )

        # Mock the get_access_token method on the installation
        with patch.object(app_installation, "get_access_token", return_value="preferred_app_token"):
            tracked_repo.app_installation = app_installation
            token = get_access_token(tracked_repo)

        # Should prefer App installation token
        self.assertEqual(token, "preferred_app_token")

    def test_raises_error_with_neither_auth(self):
        """Test get_access_token raises GitHubAuthError when neither auth is configured."""
        # Create repo with neither auth method
        tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=None,
            app_installation=None,
            full_name="org/repo-without-auth",
        )

        with self.assertRaises(GitHubAuthError) as context:
            get_access_token(tracked_repo)

        self.assertIn("no valid authentication", str(context.exception))
        self.assertIn("org/repo-without-auth", str(context.exception))

    def test_error_message_includes_repo_name(self):
        """Test GitHubAuthError includes repository name for debugging.

        Note: GitHubIntegration has a NOT NULL constraint on credential_id,
        so testing "integration without credential" isn't possible in practice.
        Instead, we verify the error message is informative for the case where
        neither auth method is configured.
        """
        # Create repo with neither auth method
        tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=None,
            app_installation=None,
            full_name="my-org/my-special-repo",
        )

        with self.assertRaises(GitHubAuthError) as context:
            get_access_token(tracked_repo)

        # Verify error message helps with debugging
        error_msg = str(context.exception)
        self.assertIn("my-org/my-special-repo", error_msg)
        self.assertIn("re-add the repository", error_msg)


class TestGetAccessTokenEdgeCases(TestCase):
    """Edge case tests for get_access_token()."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all test methods."""
        cls.team = TeamFactory()

    def test_app_installation_token_refresh(self):
        """Test that App installation can handle token refresh scenarios."""
        app_installation = GitHubAppInstallationFactory(team=self.team)
        tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=None,
            app_installation=app_installation,
        )

        # Mock get_access_token to return fresh token (simulating refresh)
        with patch.object(
            app_installation,
            "get_access_token",
            return_value="refreshed_token_xyz",
        ):
            tracked_repo.app_installation = app_installation
            token = get_access_token(tracked_repo)

        self.assertEqual(token, "refreshed_token_xyz")

    def test_handles_app_installation_error_gracefully(self):
        """Test that errors from App installation token fetch bubble up correctly."""
        from apps.integrations.services.github_app import GitHubAppError

        app_installation = GitHubAppInstallationFactory(team=self.team)
        tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=None,
            app_installation=app_installation,
        )

        # Mock get_access_token to raise an error
        with patch.object(
            app_installation,
            "get_access_token",
            side_effect=GitHubAppError("Token fetch failed"),
        ):
            tracked_repo.app_installation = app_installation

            # The error should bubble up
            with self.assertRaises(GitHubAppError):
                get_access_token(tracked_repo)
