"""Tests for TrackedRepository model changes.

RED phase: Tests for app_installation FK and access_token property.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import (
    GitHubAppInstallationFactory,
    GitHubIntegrationFactory,
)
from apps.integrations.models import TrackedRepository
from apps.metrics.factories import TeamFactory
from apps.teams.context import unset_current_team


class TestTrackedRepositoryAppInstallationFK(TestCase):
    """Tests for TrackedRepository.app_installation FK field."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.app_installation = GitHubAppInstallationFactory(team=self.team)

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_tracked_repository_has_app_installation_fk(self):
        """Test that TrackedRepository can be created with app_installation FK."""
        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            app_installation=self.app_installation,
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )

        self.assertEqual(repo.app_installation, self.app_installation)

    def test_tracked_repository_app_installation_nullable(self):
        """Test that app_installation FK can be null (for backwards compatibility)."""
        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            app_installation=None,
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )

        self.assertIsNone(repo.app_installation)

    def test_tracked_repository_app_installation_cascade_delete(self):
        """Test that deleting app_installation cascades to TrackedRepository."""
        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            app_installation=self.app_installation,
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )
        repo_id = repo.id

        # Delete the app installation
        self.app_installation.delete()

        # Repository should also be deleted (CASCADE)
        self.assertFalse(TrackedRepository.objects.filter(id=repo_id).exists())


class TestTrackedRepositoryAccessTokenProperty(TestCase):
    """Tests for TrackedRepository.access_token property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = GitHubIntegrationFactory(team=self.team)
        self.app_installation = GitHubAppInstallationFactory(
            team=self.team,
            cached_token="ghs_cached_token_123",
            token_expires_at=timezone.now() + timedelta(hours=1),
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_access_token_property_delegates_to_app_installation(self):
        """Test that access_token property returns app_installation.get_access_token()."""
        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            app_installation=self.app_installation,
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )

        # access_token should return cached token
        self.assertEqual(repo.access_token, "ghs_cached_token_123")

    def test_access_token_property_falls_back_to_oauth_when_no_app_installation(self):
        """Test that access_token falls back to OAuth when app_installation is None.

        This was updated for EC-10 fallback logic.
        """
        # Set a known OAuth token
        expected_token = "gho_test_oauth_token"
        self.integration.credential.access_token = expected_token
        self.integration.credential.save()

        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            app_installation=None,
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )

        # Should fall back to OAuth credential
        self.assertEqual(repo.access_token, expected_token)

    def test_access_token_property_triggers_refresh_when_expired(self):
        """Test that access_token triggers token refresh when expired."""
        # Set expired token
        self.app_installation.cached_token = "ghs_old_expired"
        self.app_installation.token_expires_at = timezone.now() - timedelta(hours=1)
        self.app_installation.save()

        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            app_installation=self.app_installation,
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )

        new_token = "ghs_new_refreshed_token"
        new_expiry = timezone.now() + timedelta(hours=1)

        with patch("apps.integrations.services.github_app.get_installation_token_with_expiry") as mock_get_token:
            mock_get_token.return_value = (new_token, new_expiry)

            result = repo.access_token

            # Should return new token
            self.assertEqual(result, new_token)
            mock_get_token.assert_called_once()


class TestTrackedRepositoryAuthFallback(TestCase):
    """Edge case #10: TrackedRepository with Both App AND OAuth.

    Tests that access_token property:
    1. Prefers App installation when available and active
    2. Falls back to OAuth credential when App unavailable
    3. Raises GitHubAuthError when neither available
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        # Create OAuth integration with credential (factory auto-creates credential)
        self.integration = GitHubIntegrationFactory(team=self.team)
        # Update the credential's access token
        self.integration.credential.access_token = "gho_oauth_token_456"
        self.integration.credential.save()

        # Create App installation
        self.app_installation = GitHubAppInstallationFactory(
            team=self.team,
            cached_token="ghs_app_token_123",
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_active=True,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_access_token_prefers_app_installation(self):
        """access_token should use App installation when both are available."""
        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            app_installation=self.app_installation,
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )

        # Should return App token, not OAuth token
        self.assertEqual(repo.access_token, "ghs_app_token_123")

    def test_access_token_falls_back_to_oauth(self):
        """access_token should fall back to OAuth when App is unavailable."""
        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            app_installation=None,  # No App installation
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )

        # Should return OAuth token
        self.assertEqual(repo.access_token, "gho_oauth_token_456")

    def test_access_token_falls_back_when_app_inactive(self):
        """access_token should fall back to OAuth when App is inactive."""
        self.app_installation.is_active = False
        self.app_installation.save()

        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=self.integration,
            app_installation=self.app_installation,
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )

        # Should return OAuth token since App is inactive
        self.assertEqual(repo.access_token, "gho_oauth_token_456")

    def test_access_token_raises_when_neither_available(self):
        """access_token should raise GitHubAuthError when neither auth available."""
        from apps.integrations.exceptions import GitHubAuthError

        # No App, no integration (neither auth available)
        repo = TrackedRepository.objects.create(
            team=self.team,
            integration=None,  # No OAuth integration
            app_installation=None,  # No App installation
            github_repo_id=999999,
            full_name="acme-corp/my-repo",
        )

        with self.assertRaises(GitHubAuthError) as context:
            _ = repo.access_token

        # Error should include repo name and guidance
        error_msg = str(context.exception)
        self.assertIn("acme-corp/my-repo", error_msg)
        self.assertTrue(
            "reconnect" in error_msg.lower() or "integrations" in error_msg.lower(),
            f"Error should guide user to reconnect: {error_msg}",
        )
