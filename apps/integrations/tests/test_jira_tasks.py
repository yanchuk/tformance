"""Tests for Jira Celery tasks in apps.integrations.tasks."""

from unittest.mock import MagicMock, patch

from celery.exceptions import Retry
from django.test import TestCase

from apps.integrations.factories import (
    IntegrationCredentialFactory,
    JiraIntegrationFactory,
    TrackedJiraProjectFactory,
)
from apps.metrics.factories import TeamFactory


class TestSyncJiraProjectTask(TestCase):
    """Tests for sync_jira_project_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token="encrypted_token_12345",
        )
        self.integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="ACME",
            name="ACME Project",
            is_active=True,
        )

    def test_sync_jira_project_task_returns_error_when_project_not_found(self):
        """Test that sync_jira_project_task returns error dict when project does not exist."""
        from apps.integrations.tasks import sync_jira_project_task

        non_existent_id = 99999

        # Call the task with non-existent ID
        result = sync_jira_project_task(non_existent_id)

        # Verify error is returned
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    def test_sync_jira_project_task_returns_skipped_when_project_inactive(self):
        """Test that sync_jira_project_task returns skipped dict when project is_active=False."""
        from apps.integrations.tasks import sync_jira_project_task

        # Set project to inactive
        self.tracked_project.is_active = False
        self.tracked_project.save()

        # Call the task
        result = sync_jira_project_task(self.tracked_project.id)

        # Verify task was skipped
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])
        self.assertIn("reason", result)
        self.assertIn("not active", result["reason"].lower())

    @patch("apps.integrations._task_modules.jira_sync.sync_project_issues")
    def test_sync_jira_project_task_sets_status_to_syncing_before_sync(self, mock_sync):
        """Test that sync_jira_project_task sets sync_status to 'syncing' before starting sync."""
        from apps.integrations.tasks import sync_jira_project_task

        # Mock sync to check status during execution
        def check_status_during_sync(tracked_project):
            # Reload project from database to get current state
            tracked_project.refresh_from_db()
            # Assert status is 'syncing' during execution
            assert tracked_project.sync_status == "syncing", f"Expected 'syncing', got '{tracked_project.sync_status}'"
            return {"issues_synced": 10, "errors": []}

        mock_sync.side_effect = check_status_during_sync

        # Verify initial status
        self.assertEqual(self.tracked_project.sync_status, "pending")

        # Call the task
        sync_jira_project_task(self.tracked_project.id)

        # Verify status was set to 'syncing' (checked by the mock)

    @patch("apps.integrations._task_modules.jira_sync.sync_project_issues")
    def test_sync_jira_project_task_calls_sync_project_issues_with_correct_project(self, mock_sync):
        """Test that sync_jira_project_task calls sync_project_issues with the correct project."""
        from apps.integrations.tasks import sync_jira_project_task

        mock_sync.return_value = {
            "issues_synced": 15,
            "errors": [],
        }

        # Call the task
        result = sync_jira_project_task(self.tracked_project.id)

        # Verify sync_project_issues was called with correct project
        mock_sync.assert_called_once()
        called_project = mock_sync.call_args[0][0]
        self.assertEqual(called_project.id, self.tracked_project.id)
        self.assertEqual(called_project.jira_project_key, "ACME")

        # Verify result is returned from sync
        self.assertEqual(result["issues_synced"], 15)

    @patch("apps.integrations._task_modules.jira_sync.sync_project_issues")
    def test_sync_jira_project_task_returns_sync_results_on_success(self, mock_sync):
        """Test that sync_jira_project_task returns the result dict from sync_project_issues."""
        from apps.integrations.tasks import sync_jira_project_task

        expected_result = {
            "issues_synced": 42,
            "errors": ["Some warning"],
        }
        mock_sync.return_value = expected_result

        # Call the task
        result = sync_jira_project_task(self.tracked_project.id)

        # Verify result matches sync output
        self.assertEqual(result, expected_result)

    @patch("apps.integrations._task_modules.jira_sync.sync_project_issues")
    def test_sync_jira_project_task_sets_status_to_complete_on_success(self, mock_sync):
        """Test that sync_jira_project_task sets sync_status to 'complete' on successful sync."""
        from apps.integrations.models import TrackedJiraProject
        from apps.integrations.tasks import sync_jira_project_task

        mock_sync.return_value = {
            "issues_synced": 20,
            "errors": [],
        }

        # Verify initial status
        self.assertEqual(self.tracked_project.sync_status, "pending")

        # Call the task
        sync_jira_project_task(self.tracked_project.id)

        # Reload from database and verify status is 'complete'
        project = TrackedJiraProject.objects.get(id=self.tracked_project.id)
        self.assertEqual(project.sync_status, "complete")

    @patch("apps.integrations._task_modules.jira_sync.sync_project_issues")
    def test_sync_jira_project_task_retries_with_exponential_backoff_on_failure(self, mock_sync):
        """Test that sync_jira_project_task retries with exponential backoff on failure."""
        from apps.integrations.tasks import sync_jira_project_task

        # Mock sync_project_issues to raise an exception
        mock_sync.side_effect = Exception("Jira API rate limit exceeded")

        # Mock the task's retry method
        with patch.object(sync_jira_project_task, "retry") as mock_retry:
            mock_retry.side_effect = Retry()

            # Call the task and expect it to raise Retry
            with self.assertRaises(Retry):
                sync_jira_project_task(self.tracked_project.id)

            # Verify retry was called with correct parameters
            mock_retry.assert_called_once()
            # Check that exponential backoff is configured
            # (the actual retry logic is tested by checking the decorator config)

    @patch("sentry_sdk.capture_exception")
    @patch("apps.integrations._task_modules.jira_sync.sync_project_issues")
    def test_sync_jira_project_task_sets_status_to_error_after_max_retries(self, mock_sync, mock_sentry):
        """Test that sync_jira_project_task sets sync_status to 'error' after max retries exhausted."""
        from apps.integrations.models import TrackedJiraProject
        from apps.integrations.tasks import sync_jira_project_task

        # Mock sync to raise an exception
        error_message = "Jira API rate limit exceeded"
        mock_sync.side_effect = Exception(error_message)

        # Mock retry to simulate max retries exhausted
        with patch.object(sync_jira_project_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            # Call the task
            result = sync_jira_project_task(self.tracked_project.id)

            # Verify error result is returned
            self.assertIn("error", result)

            # Reload from database and verify status is 'error'
            project = TrackedJiraProject.objects.get(id=self.tracked_project.id)
            self.assertEqual(project.sync_status, "error")

            # Verify Sentry was called
            mock_sentry.assert_called_once()


class TestSyncAllJiraProjectsTask(TestCase):
    """Tests for sync_all_jira_projects_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token="encrypted_token_12345",
        )
        self.integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

    @patch("apps.integrations._task_modules.jira_sync.sync_jira_project_task")
    def test_sync_all_jira_projects_task_dispatches_task_for_each_active_project(self, mock_task):
        """Test that sync_all_jira_projects_task dispatches sync_jira_project_task for all active projects."""
        from apps.integrations.tasks import sync_all_jira_projects_task

        # Create multiple active projects
        project1 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="PROJ1",
            is_active=True,
        )
        project2 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="PROJ2",
            is_active=True,
        )
        project3 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="PROJ3",
            is_active=True,
        )

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_jira_projects_task()

        # Verify sync_jira_project_task.delay was called for each active project
        self.assertEqual(mock_delay.call_count, 3)

        # Verify the correct project IDs were passed
        called_project_ids = {call[0][0] for call in mock_delay.call_args_list}
        expected_project_ids = {project1.id, project2.id, project3.id}
        self.assertEqual(called_project_ids, expected_project_ids)

        # Verify result contains correct counts
        self.assertIsInstance(result, dict)
        self.assertEqual(result["projects_dispatched"], 3)
        self.assertEqual(result["projects_skipped"], 0)

    @patch("apps.integrations._task_modules.jira_sync.sync_jira_project_task")
    def test_sync_all_jira_projects_task_skips_inactive_projects(self, mock_task):
        """Test that sync_all_jira_projects_task only dispatches tasks for active projects (is_active=True)."""
        from apps.integrations.tasks import sync_all_jira_projects_task

        # Create mix of active and inactive projects
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="ACTIVE",
            is_active=True,
        )
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="INACTIVE1",
            is_active=False,
        )
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="INACTIVE2",
            is_active=False,
        )

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_jira_projects_task()

        # Verify sync_jira_project_task.delay was called only once (for active project)
        self.assertEqual(mock_delay.call_count, 1)

        # Verify result contains correct counts
        self.assertIsInstance(result, dict)
        self.assertEqual(result["projects_dispatched"], 1)
        self.assertEqual(result["projects_skipped"], 2)

    @patch("apps.integrations._task_modules.jira_sync.sync_jira_project_task")
    def test_sync_all_jira_projects_task_returns_correct_counts(self, mock_task):
        """Test that sync_all_jira_projects_task returns dict with projects_dispatched and projects_skipped counts."""
        from apps.integrations.tasks import sync_all_jira_projects_task

        # Create projects
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            is_active=False,
        )

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_jira_projects_task()

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("projects_dispatched", result)
        self.assertIn("projects_skipped", result)
        self.assertEqual(result["projects_dispatched"], 2)
        self.assertEqual(result["projects_skipped"], 1)

    @patch("apps.integrations._task_modules.jira_sync.sync_jira_project_task")
    def test_sync_all_jira_projects_task_continues_on_dispatch_errors(self, mock_task):
        """Test that sync_all_jira_projects_task continues dispatching even if one dispatch fails."""
        from apps.integrations.tasks import sync_all_jira_projects_task

        # Create multiple active projects
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        project2 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )

        # Mock delay to raise exception for second project only
        mock_delay = MagicMock()

        def delay_side_effect(project_id):
            if project_id == project2.id:
                raise Exception("Celery connection error")
            return MagicMock()

        mock_delay.side_effect = delay_side_effect
        mock_task.delay = mock_delay

        # Call the task - should not raise exception
        result = sync_all_jira_projects_task()

        # Verify all projects were attempted
        self.assertEqual(mock_delay.call_count, 3)

        # Verify result still counts the successful dispatches
        self.assertIsInstance(result, dict)
        self.assertIn("projects_dispatched", result)
        # Should show 2 successful dispatches (project1 and project3)
        self.assertEqual(result["projects_dispatched"], 2)


class TestSyncJiraUsersTask(TestCase):
    """Tests for sync_jira_users_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token="encrypted_token_12345",
        )
        self.integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

    def test_sync_jira_users_task_returns_error_when_team_not_found(self):
        """Test that sync_jira_users_task returns error when team does not exist."""
        from apps.integrations.tasks import sync_jira_users_task

        non_existent_id = 99999

        # Call the task with non-existent team ID
        result = sync_jira_users_task(non_existent_id)

        # Verify error is returned
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    def test_sync_jira_users_task_returns_error_when_no_jira_integration(self):
        """Test that sync_jira_users_task returns error when team has no Jira integration."""
        from apps.integrations.tasks import sync_jira_users_task

        # Create team without Jira integration
        team_without_jira = TeamFactory()

        # Call the task
        result = sync_jira_users_task(team_without_jira.id)

        # Verify error is returned
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("jira", result["error"].lower())

    @patch("apps.integrations._task_modules.jira_sync.sync_jira_users")
    def test_sync_jira_users_task_calls_sync_jira_users_and_returns_results(self, mock_sync):
        """Test that sync_jira_users_task calls sync_jira_users and returns matching results."""
        from apps.integrations.tasks import sync_jira_users_task

        expected_result = {
            "matched": 5,
            "unmatched": 2,
            "created": 1,
        }
        mock_sync.return_value = expected_result

        # Call the task
        result = sync_jira_users_task(self.team.id)

        # Verify sync_jira_users was called with correct parameters
        mock_sync.assert_called_once()
        called_team = mock_sync.call_args[0][0]
        called_credential = mock_sync.call_args[0][1]
        self.assertEqual(called_team.id, self.team.id)
        self.assertEqual(called_credential.id, self.credential.id)

        # Verify result is returned
        self.assertEqual(result, expected_result)
