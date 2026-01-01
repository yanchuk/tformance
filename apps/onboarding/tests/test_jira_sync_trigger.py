"""Tests for Jira sync pipeline trigger in onboarding views.

TDD RED Phase: These tests define the expected behavior.
Tests should FAIL initially until the view is modified.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from apps.integrations.factories import (
    IntegrationCredentialFactory,
    JiraIntegrationFactory,
    TrackedJiraProjectFactory,
)
from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


class TestSelectJiraProjectsTriggersPipeline(TestCase):
    """Tests for select_jira_projects view triggering Jira pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="jira_test@example.com",
            email="jira_test@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)

        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
        )
        self.jira_integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        self.client.login(username="jira_test@example.com", password="testpassword123")

    @patch("apps.integrations.onboarding_pipeline.start_jira_onboarding_pipeline")
    @patch("apps.integrations.services.jira_client.get_accessible_projects")
    def test_post_triggers_jira_pipeline(self, mock_get_projects, mock_pipeline):
        """POST should start jira onboarding pipeline."""
        # Mock Jira API response
        mock_get_projects.return_value = [
            {"id": "10001", "key": "PROJ1", "name": "Project One"},
            {"id": "10002", "key": "PROJ2", "name": "Project Two"},
        ]

        # Mock pipeline return value
        mock_result = MagicMock()
        mock_result.id = "test-task-id-123"
        mock_pipeline.return_value = mock_result

        # POST to select projects
        response = self.client.post(
            reverse("onboarding:select_jira_projects"),
            {"projects": ["10001", "10002"]},
        )

        # Verify pipeline was triggered
        mock_pipeline.assert_called_once()

        # Verify redirect
        self.assertRedirects(response, reverse("onboarding:connect_slack"), fetch_redirect_response=False)

    @patch("apps.integrations.onboarding_pipeline.start_jira_onboarding_pipeline")
    @patch("apps.integrations.services.jira_client.get_accessible_projects")
    def test_post_stores_task_id_in_session(self, mock_get_projects, mock_pipeline):
        """Task ID should be stored in session for status polling."""
        mock_get_projects.return_value = [
            {"id": "10001", "key": "PROJ1", "name": "Project One"},
        ]

        mock_result = MagicMock()
        mock_result.id = "jira-task-id-456"
        mock_pipeline.return_value = mock_result

        self.client.post(
            reverse("onboarding:select_jira_projects"),
            {"projects": ["10001"]},
        )

        # Check session contains task ID
        session = self.client.session
        self.assertEqual(session.get("jira_sync_task_id"), "jira-task-id-456")

    @patch("apps.integrations.onboarding_pipeline.start_jira_onboarding_pipeline")
    @patch("apps.integrations.services.jira_client.get_accessible_projects")
    def test_post_without_projects_skips_pipeline(self, mock_get_projects, mock_pipeline):
        """POST with no projects selected should not trigger pipeline."""
        mock_get_projects.return_value = [
            {"id": "10001", "key": "PROJ1", "name": "Project One"},
        ]

        # POST with no projects selected
        response = self.client.post(
            reverse("onboarding:select_jira_projects"),
            {"projects": []},
        )

        # Pipeline should not be triggered
        mock_pipeline.assert_not_called()

        # Should still redirect
        self.assertRedirects(response, reverse("onboarding:connect_slack"), fetch_redirect_response=False)

    @patch("apps.integrations.onboarding_pipeline.start_jira_onboarding_pipeline")
    @patch("apps.integrations.services.jira_client.get_accessible_projects")
    def test_pipeline_receives_correct_project_ids(self, mock_get_projects, mock_pipeline):
        """Pipeline should receive correct TrackedJiraProject IDs."""
        mock_get_projects.return_value = [
            {"id": "10001", "key": "PROJ1", "name": "Project One"},
            {"id": "10002", "key": "PROJ2", "name": "Project Two"},
        ]

        mock_result = MagicMock()
        mock_result.id = "test-task-id"
        mock_pipeline.return_value = mock_result

        self.client.post(
            reverse("onboarding:select_jira_projects"),
            {"projects": ["10001", "10002"]},
        )

        # Verify pipeline was called with team_id and project_ids
        call_args = mock_pipeline.call_args
        self.assertEqual(call_args[0][0], self.team.id)  # First arg: team_id
        self.assertEqual(len(call_args[0][1]), 2)  # Second arg: list of 2 project IDs


class TestJiraSyncStatus(TestCase):
    """Tests for jira_sync_status endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="jira_status@example.com",
            email="jira_status@example.com",
            password="testpassword123",
        )
        self.team = TeamFactory()
        self.team.members.add(self.user)

        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
        )
        self.jira_integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        self.client.login(username="jira_status@example.com", password="testpassword123")

    def test_jira_sync_status_endpoint_exists(self):
        """Test that jira_sync_status endpoint exists."""
        url = reverse("onboarding:jira_sync_status")
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 404)

    def test_jira_sync_status_returns_project_statuses(self):
        """Status endpoint should return per-project sync status."""
        # Create tracked projects with different statuses
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.jira_integration,
            jira_project_key="PROJ1",
            sync_status="completed",
            is_active=True,
        )
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.jira_integration,
            jira_project_key="PROJ2",
            sync_status="syncing",
            is_active=True,
        )

        response = self.client.get(reverse("onboarding:jira_sync_status"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("projects", data)
        self.assertEqual(len(data["projects"]), 2)

    def test_jira_sync_status_returns_issues_count(self):
        """Status endpoint should return total issues synced."""
        from apps.metrics.factories import JiraIssueFactory

        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.jira_integration,
            is_active=True,
        )

        # Create some Jira issues for this team
        JiraIssueFactory.create_batch(5, team=self.team)

        response = self.client.get(reverse("onboarding:jira_sync_status"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("issues_synced", data)
        self.assertEqual(data["issues_synced"], 5)

    def test_jira_sync_status_calculates_overall_status(self):
        """Status endpoint should calculate overall status from project statuses."""
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.jira_integration,
            sync_status="completed",
            is_active=True,
        )
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.jira_integration,
            sync_status="syncing",
            is_active=True,
        )

        response = self.client.get(reverse("onboarding:jira_sync_status"))

        data = response.json()
        self.assertIn("overall_status", data)
        # With one syncing, overall should be syncing
        self.assertEqual(data["overall_status"], "syncing")

    def test_jira_sync_status_requires_authentication(self):
        """Status endpoint should require authentication."""
        self.client.logout()

        response = self.client.get(reverse("onboarding:jira_sync_status"))

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
