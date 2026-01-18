"""Tests for GitHub sync Celery tasks routing logic."""

from unittest.mock import patch

from django.test import TestCase

from apps.integrations._task_modules.github_sync import sync_github_app_members_task
from apps.integrations.factories import GitHubAppInstallationFactory
from apps.metrics.factories import TeamFactory


class TestSyncGitHubAppMembersTaskRouting(TestCase):
    """Tests for sync_github_app_members_task routing based on account_type."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    @patch("apps.integrations.services.member_sync.sync_single_user_as_member")
    @patch("apps.integrations.services.github_app.get_installation_token")
    def test_sync_github_app_members_task_routes_to_single_user_for_user_account(
        self, mock_get_token, mock_sync_single_user
    ):
        """Test that task calls sync_single_user_as_member when account_type is User."""
        # Arrange - create installation with account_type="User"
        installation = GitHubAppInstallationFactory(
            team=self.team,
            account_type="User",
            account_login="johndoe",
            installation_id=12345678,
        )
        mock_get_token.return_value = "ghs_fake_installation_token"
        mock_sync_single_user.return_value = {
            "created": 1,
            "updated": 0,
            "unchanged": 0,
            "failed": 0,
        }

        # Act - call the task directly (not via .delay())
        result = sync_github_app_members_task(installation.id)

        # Assert - sync_single_user_as_member was called
        mock_sync_single_user.assert_called_once_with(
            team=installation.team,
            access_token="ghs_fake_installation_token",
            username="johndoe",
        )
        self.assertEqual(result["created"], 1)

    @patch("apps.integrations.services.member_sync.sync_github_members")
    @patch("apps.integrations.services.github_app.get_installation_token")
    def test_sync_github_app_members_task_routes_to_org_sync_for_organization_account(
        self, mock_get_token, mock_sync_github_members
    ):
        """Test that task calls sync_github_members when account_type is Organization."""
        # Arrange - create installation with account_type="Organization"
        installation = GitHubAppInstallationFactory(
            team=self.team,
            account_type="Organization",
            account_login="acme-corp",
            installation_id=87654321,
        )
        mock_get_token.return_value = "ghs_fake_installation_token"
        mock_sync_github_members.return_value = {
            "created": 5,
            "updated": 2,
            "unchanged": 3,
            "failed": 0,
        }

        # Act - call the task directly (not via .delay())
        result = sync_github_app_members_task(installation.id)

        # Assert - sync_github_members was called with org_slug
        mock_sync_github_members.assert_called_once_with(
            team=installation.team,
            access_token="ghs_fake_installation_token",
            org_slug="acme-corp",
        )
        self.assertEqual(result["created"], 5)
        self.assertEqual(result["updated"], 2)

    @patch("apps.integrations.services.member_sync.sync_github_members")
    @patch("apps.integrations.services.member_sync.sync_single_user_as_member")
    @patch("apps.integrations.services.github_app.get_installation_token")
    def test_sync_github_app_members_task_does_not_call_org_sync_for_user_account(
        self, mock_get_token, mock_sync_single_user, mock_sync_github_members
    ):
        """Test that task does NOT call sync_github_members when account_type is User."""
        # Arrange - create installation with account_type="User"
        installation = GitHubAppInstallationFactory(
            team=self.team,
            account_type="User",
            account_login="personal-user",
            installation_id=11111111,
        )
        mock_get_token.return_value = "ghs_fake_token"
        mock_sync_single_user.return_value = {
            "created": 1,
            "updated": 0,
            "unchanged": 0,
            "failed": 0,
        }

        # Act
        sync_github_app_members_task(installation.id)

        # Assert - sync_github_members was NOT called
        mock_sync_github_members.assert_not_called()
        # sync_single_user_as_member WAS called
        mock_sync_single_user.assert_called_once()

    @patch("apps.integrations.services.member_sync.sync_github_members")
    @patch("apps.integrations.services.member_sync.sync_single_user_as_member")
    @patch("apps.integrations.services.github_app.get_installation_token")
    def test_sync_github_app_members_task_does_not_call_single_user_for_org_account(
        self, mock_get_token, mock_sync_single_user, mock_sync_github_members
    ):
        """Test that task does NOT call sync_single_user_as_member when account_type is Organization."""
        # Arrange - create installation with account_type="Organization"
        installation = GitHubAppInstallationFactory(
            team=self.team,
            account_type="Organization",
            account_login="enterprise-org",
            installation_id=22222222,
        )
        mock_get_token.return_value = "ghs_fake_token"
        mock_sync_github_members.return_value = {
            "created": 10,
            "updated": 0,
            "unchanged": 0,
            "failed": 0,
        }

        # Act
        sync_github_app_members_task(installation.id)

        # Assert - sync_single_user_as_member was NOT called
        mock_sync_single_user.assert_not_called()
        # sync_github_members WAS called
        mock_sync_github_members.assert_called_once()
