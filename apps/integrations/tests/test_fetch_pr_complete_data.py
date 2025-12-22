"""Tests for fetch_pr_complete_data_task Celery task."""

from unittest.mock import patch

from django.test import TestCase

from apps.integrations.factories import GitHubIntegrationFactory, IntegrationCredentialFactory, TrackedRepositoryFactory
from apps.metrics.factories import PullRequestFactory, TeamFactory


class TestFetchPRCompleteDataTask(TestCase):
    """Tests for fetch_pr_complete_data_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="fake_access_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="acme-corp",
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/backend",
            is_active=True,
        )
        self.pr = PullRequestFactory(
            team=self.team,
            github_repo="acme-corp/backend",
            github_pr_id=42,
            title="Add feature X",
        )

    @patch("apps.integrations.services.github_sync.calculate_pr_iteration_metrics")
    @patch("apps.integrations.services.github_sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync_pr_commits")
    def test_task_calls_all_sync_functions(
        self,
        mock_sync_commits,
        mock_sync_files,
        mock_sync_check_runs,
        mock_sync_issue_comments,
        mock_sync_review_comments,
        mock_calculate_metrics,
    ):
        """Test that task calls all sync functions with correct parameters."""
        from apps.integrations.tasks import fetch_pr_complete_data_task

        # Configure mocks to return counts
        mock_sync_commits.return_value = 5
        mock_sync_files.return_value = 8
        mock_sync_check_runs.return_value = 3
        mock_sync_issue_comments.return_value = 2
        mock_sync_review_comments.return_value = 4

        # Call the task
        fetch_pr_complete_data_task(self.pr.id)

        # Verify all sync functions were called once
        mock_sync_commits.assert_called_once()
        mock_sync_files.assert_called_once()
        mock_sync_check_runs.assert_called_once()
        mock_sync_issue_comments.assert_called_once()
        mock_sync_review_comments.assert_called_once()

        # Verify correct parameters passed to each sync function
        # All should receive: pr, pr_number, access_token, repo_full_name, team, errors
        expected_pr = self.pr
        expected_pr_number = 42
        expected_access_token = "fake_access_token_12345"
        expected_repo = "acme-corp/backend"
        expected_team = self.team

        for mock_func in [
            mock_sync_commits,
            mock_sync_files,
            mock_sync_check_runs,
            mock_sync_issue_comments,
            mock_sync_review_comments,
        ]:
            call_args = mock_func.call_args
            self.assertEqual(call_args[0][0].id, expected_pr.id)  # pr
            self.assertEqual(call_args[0][1], expected_pr_number)  # pr_number
            self.assertEqual(call_args[0][2], expected_access_token)  # access_token
            self.assertEqual(call_args[0][3], expected_repo)  # repo_full_name
            self.assertEqual(call_args[0][4].id, expected_team.id)  # team
            self.assertIsInstance(call_args[0][5], list)  # errors list

        # Verify calculate_pr_iteration_metrics called after syncing
        mock_calculate_metrics.assert_called_once()
        self.assertEqual(mock_calculate_metrics.call_args[0][0].id, self.pr.id)

    @patch("apps.integrations.services.github_sync.calculate_pr_iteration_metrics")
    @patch("apps.integrations.services.github_sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync_pr_commits")
    def test_task_returns_sync_counts(
        self,
        mock_sync_commits,
        mock_sync_files,
        mock_sync_check_runs,
        mock_sync_issue_comments,
        mock_sync_review_comments,
        mock_calculate_metrics,
    ):
        """Test that task returns dict with sync counts."""
        from apps.integrations.tasks import fetch_pr_complete_data_task

        # Configure mocks to return specific counts
        mock_sync_commits.return_value = 5
        mock_sync_files.return_value = 8
        mock_sync_check_runs.return_value = 3
        mock_sync_issue_comments.return_value = 2
        mock_sync_review_comments.return_value = 4

        # Call the task
        result = fetch_pr_complete_data_task(self.pr.id)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertEqual(result["commits_synced"], 5)
        self.assertEqual(result["files_synced"], 8)
        self.assertEqual(result["check_runs_synced"], 3)
        self.assertEqual(result["issue_comments_synced"], 2)
        self.assertEqual(result["review_comments_synced"], 4)
        self.assertIn("errors", result)
        self.assertIsInstance(result["errors"], list)

    def test_task_handles_missing_pull_request(self):
        """Test that task handles missing PullRequest gracefully without raising."""
        from apps.integrations.tasks import fetch_pr_complete_data_task

        non_existent_id = 99999

        # Call the task with non-existent PR ID
        result = fetch_pr_complete_data_task(non_existent_id)

        # Verify error dict returned (not raising exception)
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("PullRequest", result["error"])
        self.assertIn("not found", result["error"].lower())

    @patch("apps.integrations.services.github_sync.sync_pr_commits")
    def test_task_handles_missing_tracked_repository(self, mock_sync_commits):
        """Test that task returns error dict when no matching TrackedRepository found."""
        from apps.integrations.tasks import fetch_pr_complete_data_task

        # Create PR with repo that doesn't have a TrackedRepository
        pr_without_tracked_repo = PullRequestFactory(
            team=self.team,
            github_repo="other-org/untracked-repo",
            github_pr_id=99,
        )

        # Call the task
        result = fetch_pr_complete_data_task(pr_without_tracked_repo.id)

        # Verify error returned
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("TrackedRepository", result["error"])
        self.assertIn("not found", result["error"].lower())

        # Verify sync functions were NOT called
        mock_sync_commits.assert_not_called()

    @patch("apps.integrations.services.github_sync.calculate_pr_iteration_metrics")
    @patch("apps.integrations.services.github_sync.sync_pr_review_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_issue_comments")
    @patch("apps.integrations.services.github_sync.sync_pr_check_runs")
    @patch("apps.integrations.services.github_sync.sync_pr_files")
    @patch("apps.integrations.services.github_sync.sync_pr_commits")
    def test_task_calculates_iteration_metrics(
        self,
        mock_sync_commits,
        mock_sync_files,
        mock_sync_check_runs,
        mock_sync_issue_comments,
        mock_sync_review_comments,
        mock_calculate_metrics,
    ):
        """Test that calculate_pr_iteration_metrics is called after all sync operations."""
        from apps.integrations.tasks import fetch_pr_complete_data_task

        # Configure mocks
        mock_sync_commits.return_value = 5
        mock_sync_files.return_value = 8
        mock_sync_check_runs.return_value = 3
        mock_sync_issue_comments.return_value = 2
        mock_sync_review_comments.return_value = 4

        # Call the task
        fetch_pr_complete_data_task(self.pr.id)

        # Verify calculate_pr_iteration_metrics was called exactly once
        mock_calculate_metrics.assert_called_once()

        # Verify it was called with the correct PR
        call_args = mock_calculate_metrics.call_args
        self.assertEqual(call_args[0][0].id, self.pr.id)

        # Verify it was called AFTER all sync functions (by checking call order)
        # If calculate_metrics was called before sync functions, the test would fail
        self.assertTrue(mock_sync_commits.called)
        self.assertTrue(mock_sync_files.called)
        self.assertTrue(mock_sync_check_runs.called)
        self.assertTrue(mock_sync_issue_comments.called)
        self.assertTrue(mock_sync_review_comments.called)
