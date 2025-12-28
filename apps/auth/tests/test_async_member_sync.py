"""Tests for async member sync during OAuth callback.

These tests verify that the OAuth callback queues member sync as a background task
instead of calling it synchronously, ensuring fast callback response times.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from apps.auth.oauth_state import FLOW_TYPE_INTEGRATION, FLOW_TYPE_ONBOARDING, create_oauth_state
from apps.integrations.factories import UserFactory
from apps.integrations.models import GitHubIntegration
from apps.metrics.factories import TeamFactory
from apps.teams.roles import ROLE_ADMIN


class TestOnboardingAsyncMemberSync(TestCase):
    """Tests that onboarding callback queues member sync asynchronously."""

    def setUp(self):
        """Set up test user without a team."""
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:github_callback")

    @patch("apps.auth.views.github_oauth")
    @patch("apps.integrations.tasks.sync_github_members_task")
    def test_onboarding_callback_queues_member_sync_task(self, mock_sync_task, mock_github_oauth):
        """Test that onboarding callback queues sync_github_members_task.delay() instead of calling sync directly."""
        # Arrange
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "test-org", "id": 12345, "description": "Test Org", "avatar_url": ""}
        ]

        state = create_oauth_state(FLOW_TYPE_ONBOARDING)

        # Act
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Assert - task was queued with .delay()
        self.assertEqual(response.status_code, 302)
        mock_sync_task.delay.assert_called_once()

        # Verify the integration ID was passed to the task
        call_args = mock_sync_task.delay.call_args
        integration_id = call_args[0][0] if call_args[0] else call_args[1].get("integration_id")
        self.assertIsNotNone(integration_id)

        # Verify integration exists with that ID
        integration = GitHubIntegration.objects.get(id=integration_id)
        self.assertEqual(integration.organization_slug, "test-org")

    @patch("apps.auth.views.github_oauth")
    @patch("apps.auth.views.member_sync.sync_github_members")
    def test_onboarding_callback_does_not_call_sync_directly(self, mock_sync_direct, mock_github_oauth):
        """Test that onboarding callback does NOT call sync_github_members directly."""
        # Arrange
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "test-org", "id": 12345, "description": "Test Org", "avatar_url": ""}
        ]

        state = create_oauth_state(FLOW_TYPE_ONBOARDING)

        # Act
        with patch("apps.integrations.tasks.sync_github_members_task"):
            response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Assert - direct sync was NOT called
        self.assertEqual(response.status_code, 302)
        mock_sync_direct.assert_not_called()

    @patch("apps.auth.views.github_oauth")
    @patch("apps.integrations.tasks.sync_github_members_task")
    def test_onboarding_team_created_even_if_task_dispatch_fails(self, mock_sync_task, mock_github_oauth):
        """Test that team creation succeeds even if task dispatch fails."""
        # Arrange
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "test-org", "id": 12345, "description": "Test Org", "avatar_url": ""}
        ]

        # Simulate task dispatch failure
        mock_sync_task.delay.side_effect = Exception("Redis connection failed")

        state = create_oauth_state(FLOW_TYPE_ONBOARDING)

        # Act
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Assert - team was still created despite task failure
        self.assertEqual(response.status_code, 302)

        from apps.teams.models import Team

        self.assertTrue(Team.objects.filter(name="test-org").exists())

        # User is still a member
        team = Team.objects.get(name="test-org")
        self.assertTrue(team.members.filter(id=self.user.id).exists())


class TestIntegrationAsyncMemberSync(TestCase):
    """Tests that integration callback queues member sync asynchronously."""

    def setUp(self):
        """Set up test user with a team."""
        self.user = UserFactory()
        self.team = TeamFactory()
        self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:github_callback")

    @patch("apps.auth.views.github_oauth")
    @patch("apps.integrations.tasks.sync_github_members_task")
    def test_integration_callback_queues_member_sync_task(self, mock_sync_task, mock_github_oauth):
        """Test that integration callback queues sync_github_members_task.delay() instead of calling sync directly."""
        # Arrange
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "my-org", "id": 999, "description": "", "avatar_url": ""}
        ]

        state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=self.team.id)

        # Act
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Assert - task was queued with .delay()
        self.assertEqual(response.status_code, 302)
        mock_sync_task.delay.assert_called_once()

        # Verify the integration ID was passed to the task
        call_args = mock_sync_task.delay.call_args
        integration_id = call_args[0][0] if call_args[0] else call_args[1].get("integration_id")
        self.assertIsNotNone(integration_id)

        # Verify integration exists with that ID
        integration = GitHubIntegration.objects.get(id=integration_id)
        self.assertEqual(integration.organization_slug, "my-org")
        self.assertEqual(integration.team_id, self.team.id)

    @patch("apps.auth.views.github_oauth")
    @patch("apps.auth.views.member_sync.sync_github_members")
    def test_integration_callback_does_not_call_sync_directly(self, mock_sync_direct, mock_github_oauth):
        """Test that integration callback does NOT call sync_github_members directly."""
        # Arrange
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "my-org", "id": 999, "description": "", "avatar_url": ""}
        ]

        state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=self.team.id)

        # Act
        with patch("apps.integrations.tasks.sync_github_members_task"):
            response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Assert - direct sync was NOT called
        self.assertEqual(response.status_code, 302)
        mock_sync_direct.assert_not_called()

    @patch("apps.auth.views.github_oauth")
    @patch("apps.integrations.tasks.sync_github_members_task")
    def test_integration_created_even_if_task_dispatch_fails(self, mock_sync_task, mock_github_oauth):
        """Test that GitHub integration is created even if task dispatch fails."""
        # Arrange
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "my-org", "id": 999, "description": "", "avatar_url": ""}
        ]

        # Simulate task dispatch failure
        mock_sync_task.delay.side_effect = Exception("Redis connection failed")

        state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=self.team.id)

        # Act
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Assert - integration was still created despite task failure
        self.assertEqual(response.status_code, 302)
        self.assertTrue(GitHubIntegration.objects.filter(team=self.team).exists())

        integration = GitHubIntegration.objects.get(team=self.team)
        self.assertEqual(integration.organization_slug, "my-org")


class TestCallbackResponseTime(TestCase):
    """Tests that callback completes quickly without waiting for member sync."""

    def setUp(self):
        """Set up test user without a team."""
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.callback_url = reverse("tformance_auth:github_callback")

    @patch("apps.auth.views.github_oauth")
    @patch("apps.integrations.tasks.sync_github_members_task")
    def test_callback_does_not_wait_for_sync(self, mock_sync_task, mock_github_oauth):
        """Test that callback returns immediately without waiting for sync to complete.

        This verifies the callback uses task.delay() which returns immediately,
        rather than calling the sync function synchronously.
        """
        # Arrange
        mock_github_oauth.exchange_code_for_token.return_value = {"access_token": "test_token"}
        mock_github_oauth.get_user_organizations.return_value = [
            {"login": "test-org", "id": 12345, "description": "Test Org", "avatar_url": ""}
        ]

        # Set up mock to track that delay() was called, not the task itself
        mock_async_result = MagicMock()
        mock_sync_task.delay.return_value = mock_async_result

        state = create_oauth_state(FLOW_TYPE_ONBOARDING)

        # Act
        response = self.client.get(self.callback_url, {"state": state, "code": "test_code"})

        # Assert
        self.assertEqual(response.status_code, 302)

        # delay() was called (async dispatch)
        mock_sync_task.delay.assert_called_once()

        # The actual task function was NOT called directly (would block)
        # We're checking that the mock was used through .delay(), not called directly
        self.assertFalse(mock_sync_task.called, "Task should not be called directly, only via .delay()")
