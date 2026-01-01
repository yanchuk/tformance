"""Tests for Jira onboarding pipeline tasks.

TDD RED Phase: These tests define the expected behavior of the Jira pipeline.
Tests should FAIL initially (import error expected since functions don't exist yet).
"""

from unittest.mock import patch

from django.test import TestCase

from apps.integrations.factories import (
    IntegrationCredentialFactory,
    JiraIntegrationFactory,
    TrackedJiraProjectFactory,
)
from apps.metrics.factories import TeamFactory


class TestSyncJiraUsersOnboarding(TestCase):
    """Tests for sync_jira_users_onboarding Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
        )
        self.integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

    def test_sync_jira_users_onboarding_task_exists(self):
        """Test that sync_jira_users_onboarding task is importable."""
        from apps.integrations.onboarding_pipeline import sync_jira_users_onboarding

        self.assertTrue(callable(sync_jira_users_onboarding))

    @patch("apps.integrations.tasks.sync_jira_users_task")
    def test_sync_jira_users_onboarding_calls_sync_service(self, mock_sync_task):
        """Test that task delegates to sync_jira_users_task."""
        from apps.integrations.onboarding_pipeline import sync_jira_users_onboarding

        expected_result = {"matched": 5, "unmatched": 2}
        mock_sync_task.return_value = expected_result

        # Call the task
        result = sync_jira_users_onboarding(self.team.id)

        # Verify sync_jira_users_task was called with team_id
        mock_sync_task.assert_called_once_with(self.team.id)

        # Verify result is passed through
        self.assertEqual(result, expected_result)

    @patch("apps.integrations.tasks.sync_jira_users_task")
    def test_sync_jira_users_onboarding_returns_result_dict(self, mock_sync_task):
        """Test that task returns a dict with sync results."""
        from apps.integrations.onboarding_pipeline import sync_jira_users_onboarding

        mock_sync_task.return_value = {
            "matched": 10,
            "unmatched": 3,
            "created": 2,
        }

        result = sync_jira_users_onboarding(self.team.id)

        self.assertIsInstance(result, dict)
        self.assertIn("matched", result)

    @patch("apps.integrations.tasks.sync_jira_users_task")
    def test_sync_jira_users_onboarding_handles_missing_integration(self, mock_sync_task):
        """Test that task handles team without Jira integration."""
        from apps.integrations.onboarding_pipeline import sync_jira_users_onboarding

        # Mock returns error for team without Jira
        mock_sync_task.return_value = {"error": "No Jira integration found"}

        team_without_jira = TeamFactory()
        result = sync_jira_users_onboarding(team_without_jira.id)

        self.assertIsInstance(result, dict)
        # Should pass through the error from underlying task
        mock_sync_task.assert_called_once_with(team_without_jira.id)


class TestSyncJiraProjectsOnboarding(TestCase):
    """Tests for sync_jira_projects_onboarding Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
        )
        self.integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.project1 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="PROJ1",
            is_active=True,
        )
        self.project2 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="PROJ2",
            is_active=True,
        )

    def test_sync_jira_projects_onboarding_task_exists(self):
        """Test that sync_jira_projects_onboarding task is importable."""
        from apps.integrations.onboarding_pipeline import sync_jira_projects_onboarding

        self.assertTrue(callable(sync_jira_projects_onboarding))

    @patch("apps.integrations.services.jira_sync.sync_project_issues")
    def test_sync_jira_projects_onboarding_syncs_all_projects(self, mock_sync):
        """Test that task syncs each project in the list."""
        from apps.integrations.onboarding_pipeline import sync_jira_projects_onboarding

        mock_sync.return_value = {"issues_created": 5, "issues_updated": 2, "errors": 0}

        project_ids = [self.project1.id, self.project2.id]
        sync_jira_projects_onboarding(self.team.id, project_ids)

        # Verify sync_project_issues was called for each project
        self.assertEqual(mock_sync.call_count, 2)

    @patch("apps.integrations.services.jira_sync.sync_project_issues")
    def test_sync_jira_projects_onboarding_returns_aggregate_results(self, mock_sync):
        """Test that task returns aggregated results from all projects."""
        from apps.integrations.onboarding_pipeline import sync_jira_projects_onboarding

        mock_sync.return_value = {"issues_created": 5, "issues_updated": 2, "errors": 0}

        project_ids = [self.project1.id, self.project2.id]
        result = sync_jira_projects_onboarding(self.team.id, project_ids)

        self.assertIsInstance(result, dict)
        self.assertIn("synced", result)
        self.assertIn("failed", result)
        self.assertIn("issues_created", result)
        self.assertEqual(result["synced"], 2)
        self.assertEqual(result["issues_created"], 10)  # 5 + 5

    @patch("apps.integrations.services.jira_sync.sync_project_issues")
    def test_sync_jira_projects_onboarding_continues_on_failure(self, mock_sync):
        """Test that task continues syncing if one project fails."""
        from apps.integrations.onboarding_pipeline import sync_jira_projects_onboarding

        # First call succeeds, second fails, third succeeds
        project3 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="PROJ3",
            is_active=True,
        )

        mock_sync.side_effect = [
            {"issues_created": 5, "issues_updated": 0, "errors": 0},
            Exception("Jira API error"),
            {"issues_created": 3, "issues_updated": 1, "errors": 0},
        ]

        project_ids = [self.project1.id, self.project2.id, project3.id]
        result = sync_jira_projects_onboarding(self.team.id, project_ids)

        # All projects should be attempted
        self.assertEqual(mock_sync.call_count, 3)

        # Result should show 2 synced, 1 failed
        self.assertEqual(result["synced"], 2)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["issues_created"], 8)  # 5 + 3

    @patch("apps.integrations.services.jira_sync.sync_project_issues")
    def test_sync_jira_projects_onboarding_handles_empty_list(self, mock_sync):
        """Test that task handles empty project list gracefully."""
        from apps.integrations.onboarding_pipeline import sync_jira_projects_onboarding

        result = sync_jira_projects_onboarding(self.team.id, [])

        mock_sync.assert_not_called()
        self.assertEqual(result["synced"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["issues_created"], 0)


class TestStartJiraOnboardingPipeline(TestCase):
    """Tests for start_jira_onboarding_pipeline function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
        )
        self.integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )

    def test_start_jira_onboarding_pipeline_function_exists(self):
        """Test that start_jira_onboarding_pipeline is importable."""
        from apps.integrations.onboarding_pipeline import start_jira_onboarding_pipeline

        self.assertTrue(callable(start_jira_onboarding_pipeline))

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_start_jira_onboarding_pipeline_creates_celery_chain(self, mock_chain):
        """Test that function creates a Celery chain with user sync then project sync."""
        from apps.integrations.onboarding_pipeline import start_jira_onboarding_pipeline

        mock_chain_instance = mock_chain.return_value
        mock_chain_instance.apply_async.return_value.id = "test-task-id"

        start_jira_onboarding_pipeline(self.team.id, [self.project.id])

        # Verify chain was called
        mock_chain.assert_called_once()

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_start_jira_onboarding_pipeline_syncs_users_first(self, mock_chain):
        """Test that pipeline syncs users before syncing projects."""
        from apps.integrations.onboarding_pipeline import start_jira_onboarding_pipeline

        mock_chain_instance = mock_chain.return_value
        mock_chain_instance.apply_async.return_value.id = "test-task-id"

        start_jira_onboarding_pipeline(self.team.id, [self.project.id])

        # Get the tasks passed to chain()
        chain_args = mock_chain.call_args[0]

        # Should have at least 2 tasks (users then projects)
        self.assertGreaterEqual(len(chain_args), 2)

    @patch("apps.integrations.onboarding_pipeline.chain")
    def test_start_jira_onboarding_pipeline_returns_async_result(self, mock_chain):
        """Test that function returns AsyncResult from chain execution."""
        from apps.integrations.onboarding_pipeline import start_jira_onboarding_pipeline

        mock_async_result = mock_chain.return_value.apply_async.return_value
        mock_async_result.id = "test-task-id"

        result = start_jira_onboarding_pipeline(self.team.id, [self.project.id])

        self.assertEqual(result.id, "test-task-id")
