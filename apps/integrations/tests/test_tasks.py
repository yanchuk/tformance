"""Tests for Celery tasks in apps.integrations.tasks."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from celery.exceptions import Retry
from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    TrackedRepositoryFactory,
)
from apps.metrics.factories import TeamFactory


class TestSyncRepositoryTask(TestCase):
    """Tests for sync_repository_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="encrypted_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.tracked_repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/api-server",
            is_active=True,
        )

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_calls_sync_repository_incremental_with_correct_repo(self, mock_sync):
        """Test that sync_repository_task calls sync_repository_incremental with the correct repository."""
        from apps.integrations.tasks import sync_repository_task

        mock_sync.return_value = {
            "prs_synced": 5,
            "reviews_synced": 3,
            "errors": [],
        }

        # Call the task
        result = sync_repository_task(self.tracked_repo.id)

        # Verify sync_repository_incremental was called with correct repo
        mock_sync.assert_called_once()
        called_repo = mock_sync.call_args[0][0]
        self.assertEqual(called_repo.id, self.tracked_repo.id)
        self.assertEqual(called_repo.full_name, "acme-corp/api-server")

        # Verify result is returned from sync
        self.assertEqual(result["prs_synced"], 5)
        self.assertEqual(result["reviews_synced"], 3)

    def test_sync_repository_task_skips_inactive_repos(self):
        """Test that sync_repository_task skips repositories where is_active=False."""
        from apps.integrations.tasks import sync_repository_task

        # Set repo to inactive
        self.tracked_repo.is_active = False
        self.tracked_repo.save()

        # Call the task
        result = sync_repository_task(self.tracked_repo.id)

        # Verify task was skipped
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])
        self.assertIn("reason", result)
        self.assertIn("not active", result["reason"].lower())

    def test_sync_repository_task_handles_does_not_exist(self):
        """Test that sync_repository_task handles TrackedRepository.DoesNotExist gracefully."""
        from apps.integrations.tasks import sync_repository_task

        non_existent_id = 99999

        # Call the task with non-existent ID
        result = sync_repository_task(non_existent_id)

        # Verify error is returned
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_retries_on_failure(self, mock_sync):
        """Test that sync_repository_task retries up to 3 times on failure with exponential backoff."""
        from apps.integrations.tasks import sync_repository_task

        # Mock sync_repository_incremental to raise an exception
        mock_sync.side_effect = Exception("GitHub API rate limit exceeded")

        # Mock the task's retry method
        with patch.object(sync_repository_task, "retry") as mock_retry:
            mock_retry.side_effect = Retry()

            # Call the task and expect it to raise Retry
            with self.assertRaises(Retry):
                sync_repository_task(self.tracked_repo.id)

            # Verify retry was called with correct parameters
            mock_retry.assert_called_once()
            # Check that max_retries and exponential backoff are configured
            # (the actual retry logic is tested by checking the decorator config)

    @patch("sentry_sdk.capture_exception")
    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_logs_to_sentry_on_final_failure(self, mock_sync, mock_sentry):
        """Test that sync_repository_task logs errors to Sentry on final failure after retries exhausted."""
        from apps.integrations.tasks import sync_repository_task

        # Mock sync_repository_incremental to raise an exception
        test_exception = Exception("Permanent failure")
        mock_sync.side_effect = test_exception

        # Mock the task's retry method to raise Retry for the first attempts,
        # then let the exception through on the final attempt
        with patch.object(sync_repository_task, "retry") as mock_retry:
            # Simulate max retries exceeded by not raising Retry
            mock_retry.side_effect = Exception("Max retries exceeded")

            # Call the task - should handle the exception and log to Sentry
            result = sync_repository_task(self.tracked_repo.id)

            # Verify Sentry was called
            mock_sentry.assert_called_once()

            # Verify error result is returned
            self.assertIsInstance(result, dict)
            self.assertIn("error", result)

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_returns_result_dict_from_sync(self, mock_sync):
        """Test that sync_repository_task returns the result dict from sync_repository_incremental."""
        from apps.integrations.tasks import sync_repository_task

        expected_result = {
            "prs_synced": 10,
            "reviews_synced": 7,
            "errors": ["Some warning"],
        }
        mock_sync.return_value = expected_result

        # Call the task
        result = sync_repository_task(self.tracked_repo.id)

        # Verify result matches sync output
        self.assertEqual(result, expected_result)

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_sets_status_to_syncing_before_sync(self, mock_sync):
        """Test that sync_repository_task sets sync_status to 'syncing' before starting sync."""
        from apps.integrations.tasks import sync_repository_task

        # Mock sync to check status during execution
        def check_status_during_sync(repo):
            # Reload repo from database to get current state
            repo.refresh_from_db()
            # Assert status is 'syncing' during execution
            assert repo.sync_status == "syncing", f"Expected 'syncing', got '{repo.sync_status}'"
            return {"prs_synced": 5, "reviews_synced": 3, "errors": []}

        mock_sync.side_effect = check_status_during_sync

        # Verify initial status
        self.assertEqual(self.tracked_repo.sync_status, "pending")

        # Call the task
        sync_repository_task(self.tracked_repo.id)

        # Verify status was set to 'syncing' (checked by the mock)

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_sets_status_to_complete_on_success(self, mock_sync):
        """Test that sync_repository_task sets sync_status to 'complete' on successful sync."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_task

        mock_sync.return_value = {
            "prs_synced": 10,
            "reviews_synced": 7,
            "errors": [],
        }

        # Verify initial status
        self.assertEqual(self.tracked_repo.sync_status, "pending")

        # Call the task
        sync_repository_task(self.tracked_repo.id)

        # Reload from database and verify status is 'complete'
        repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
        self.assertEqual(repo.sync_status, "complete")

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_sets_status_to_error_on_failure(self, mock_sync):
        """Test that sync_repository_task sets sync_status to 'error' on permanent failure."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_task

        # Mock sync to raise an exception
        error_message = "GitHub API rate limit exceeded"
        mock_sync.side_effect = Exception(error_message)

        # Mock retry to simulate max retries exhausted
        with patch.object(sync_repository_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            # Mock Sentry to avoid actual calls
            with patch("sentry_sdk.capture_exception"):
                # Call the task
                result = sync_repository_task(self.tracked_repo.id)

                # Verify error result is returned
                self.assertIn("error", result)

                # Reload from database and verify status is 'error'
                repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
                self.assertEqual(repo.sync_status, "error")

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_saves_error_message_on_failure(self, mock_sync):
        """Test that sync_repository_task saves error message to last_sync_error on failure."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_task

        # Mock sync to raise an exception
        error_message = "GitHub API rate limit exceeded"
        mock_sync.side_effect = Exception(error_message)

        # Mock retry to simulate max retries exhausted
        with patch.object(sync_repository_task, "retry") as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")

            # Mock Sentry to avoid actual calls
            with patch("sentry_sdk.capture_exception"):
                # Call the task
                sync_repository_task(self.tracked_repo.id)

                # Reload from database and verify error message is saved
                repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
                self.assertIsNotNone(repo.last_sync_error)
                self.assertIn(error_message, repo.last_sync_error)

    @patch("apps.integrations.tasks.sync_repository_incremental")
    def test_sync_repository_task_clears_last_sync_error_on_successful_sync(self, mock_sync):
        """Test that sync_repository_task clears last_sync_error on successful sync after previous error."""
        from apps.integrations.models import TrackedRepository
        from apps.integrations.tasks import sync_repository_task

        # Set up repo with previous error
        self.tracked_repo.sync_status = "error"
        self.tracked_repo.last_sync_error = "Previous error message"
        self.tracked_repo.save()

        mock_sync.return_value = {
            "prs_synced": 5,
            "reviews_synced": 3,
            "errors": [],
        }

        # Call the task
        sync_repository_task(self.tracked_repo.id)

        # Reload from database and verify error is cleared
        repo = TrackedRepository.objects.get(id=self.tracked_repo.id)
        self.assertEqual(repo.sync_status, "complete")
        self.assertIsNone(repo.last_sync_error)


class TestSyncAllRepositoriesTask(TestCase):
    """Tests for sync_all_repositories_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="encrypted_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_dispatches_tasks_for_all_active_repos(self, mock_task):
        """Test that sync_all_repositories_task dispatches sync_repository_task for all active repos."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Create multiple active repos
        repo1 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/repo-1",
            is_active=True,
        )
        repo2 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/repo-2",
            is_active=True,
        )
        repo3 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/repo-3",
            is_active=True,
        )

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_repositories_task()

        # Verify sync_repository_task.delay was called for each active repo
        self.assertEqual(mock_delay.call_count, 3)

        # Verify the correct repo IDs were passed
        called_repo_ids = {call[0][0] for call in mock_delay.call_args_list}
        expected_repo_ids = {repo1.id, repo2.id, repo3.id}
        self.assertEqual(called_repo_ids, expected_repo_ids)

        # Verify result contains correct counts
        self.assertIsInstance(result, dict)
        self.assertEqual(result["repos_dispatched"], 3)
        self.assertEqual(result["repos_skipped"], 0)

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_skips_inactive_repos(self, mock_task):
        """Test that sync_all_repositories_task only dispatches tasks for active repos (is_active=True)."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Create mix of active and inactive repos
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/active-repo",
            is_active=True,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/inactive-repo-1",
            is_active=False,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="acme-corp/inactive-repo-2",
            is_active=False,
        )

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_repositories_task()

        # Verify sync_repository_task.delay was called only once (for active repo)
        self.assertEqual(mock_delay.call_count, 1)

        # Verify result contains correct counts
        self.assertIsInstance(result, dict)
        self.assertEqual(result["repos_dispatched"], 1)
        self.assertEqual(result["repos_skipped"], 2)

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_returns_correct_counts(self, mock_task):
        """Test that sync_all_repositories_task returns dict with repos_dispatched and repos_skipped counts."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Create repos
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=False,
        )

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_repositories_task()

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("repos_dispatched", result)
        self.assertIn("repos_skipped", result)
        self.assertEqual(result["repos_dispatched"], 2)
        self.assertEqual(result["repos_skipped"], 1)

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_handles_empty_repository_list(self, mock_task):
        """Test that sync_all_repositories_task handles case where no repositories exist."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Don't create any repos

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = sync_all_repositories_task()

        # Verify no tasks were dispatched
        mock_delay.assert_not_called()

        # Verify result contains zero counts
        self.assertIsInstance(result, dict)
        self.assertEqual(result["repos_dispatched"], 0)
        self.assertEqual(result["repos_skipped"], 0)

    @patch("apps.integrations.tasks.sync_repository_task")
    def test_sync_all_repositories_task_continues_on_individual_dispatch_error(self, mock_task):
        """Test that sync_all_repositories_task continues dispatching even if one dispatch fails."""
        from apps.integrations.tasks import sync_all_repositories_task

        # Create multiple active repos
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        repo2 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            is_active=True,
        )

        # Mock delay to raise exception for second repo only
        mock_delay = MagicMock()

        def delay_side_effect(repo_id):
            if repo_id == repo2.id:
                raise Exception("Celery connection error")
            return MagicMock()

        mock_delay.side_effect = delay_side_effect
        mock_task.delay = mock_delay

        # Call the task - should not raise exception
        result = sync_all_repositories_task()

        # Verify all repos were attempted
        self.assertEqual(mock_delay.call_count, 3)

        # Verify result still counts the successful dispatches
        # (Implementation detail: task should track successful vs failed dispatches)
        self.assertIsInstance(result, dict)
        self.assertIn("repos_dispatched", result)
        # Should show 2 successful dispatches (repo1 and repo3)
        self.assertEqual(result["repos_dispatched"], 2)


class TestSkipRespondedReviewers(TestCase):
    """Tests for skipping reviewers who have already responded via GitHub web survey."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.factories import SlackIntegrationFactory
        from apps.metrics.factories import (
            PRReviewFactory,
            PullRequestFactory,
            TeamMemberFactory,
        )

        self.team = TeamFactory()
        self.slack_credential = IntegrationCredentialFactory(
            team=self.team,
            provider="slack",
            access_token="encrypted_slack_token",
        )
        self.slack_integration = SlackIntegrationFactory(
            team=self.team,
            credential=self.slack_credential,
            surveys_enabled=True,
        )

        # Create author with Slack ID
        self.author = TeamMemberFactory(team=self.team, slack_user_id="U001AUTHOR")

        # Create merged PR
        self.pr = PullRequestFactory(
            team=self.team,
            state="merged",
            author=self.author,
        )

        # Create reviewers with Slack IDs
        self.reviewer1 = TeamMemberFactory(team=self.team, slack_user_id="U002REV1", display_name="Reviewer One")
        self.reviewer2 = TeamMemberFactory(team=self.team, slack_user_id="U003REV2", display_name="Reviewer Two")

        # Create PR reviews to link reviewers to PR
        PRReviewFactory(pull_request=self.pr, reviewer=self.reviewer1)
        PRReviewFactory(pull_request=self.pr, reviewer=self.reviewer2)

    @patch("apps.integrations.tasks.create_pr_survey")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    def test_skip_reviewer_already_responded_via_github(self, mock_get_client, mock_send_dm, mock_create_survey):
        """Test that reviewer who responded via GitHub web survey doesn't get Slack DM."""
        from apps.integrations.tasks import send_pr_surveys_task
        from apps.metrics.factories import PRSurveyFactory, PRSurveyReviewFactory

        # Create survey and mock create_pr_survey to return it
        survey = PRSurveyFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.author,
            author_ai_assisted=None,
        )
        mock_create_survey.return_value = survey

        # Create PRSurveyReview for reviewer1 with responded_at set (GitHub web response)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            reviewer=self.reviewer1,
            responded_at=timezone.now() - timedelta(hours=2),
            ai_guess=True,
            quality_rating=3,
        )

        # Mock Slack client
        mock_get_client.return_value = MagicMock()

        # Call task
        result = send_pr_surveys_task(self.pr.id)

        # Verify only ONE reviewer got DM (reviewer2), not reviewer1
        # mock_send_dm should be called twice: once for author, once for reviewer2 (not reviewer1)
        self.assertEqual(mock_send_dm.call_count, 2)

        # Verify result shows 1 reviewer skipped
        self.assertIn("reviewers_skipped", result)
        self.assertEqual(result["reviewers_skipped"], 1)
        self.assertEqual(result["reviewers_sent"], 1)  # Only reviewer2 got DM

    @patch("apps.integrations.tasks.create_pr_survey")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    def test_skip_author_already_responded_via_github(self, mock_get_client, mock_send_dm, mock_create_survey):
        """Test that author who responded via GitHub doesn't get Slack DM."""
        from apps.integrations.tasks import send_pr_surveys_task
        from apps.metrics.factories import PRSurveyFactory

        # Create survey with author already responded
        survey = PRSurveyFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.author,
            author_ai_assisted=True,
            author_responded_at=timezone.now() - timedelta(hours=1),
        )
        mock_create_survey.return_value = survey

        # Mock Slack client
        mock_get_client.return_value = MagicMock()

        # Call task
        result = send_pr_surveys_task(self.pr.id)

        # Verify author DM was NOT sent, but reviewer DMs were sent
        # mock_send_dm should be called twice (only for the 2 reviewers)
        self.assertEqual(mock_send_dm.call_count, 2)

        # Verify result shows author was skipped
        self.assertIn("author_skipped", result)
        self.assertTrue(result["author_skipped"])
        self.assertFalse(result["author_sent"])
        self.assertEqual(result["reviewers_sent"], 2)

    @patch("apps.integrations.tasks.create_pr_survey")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    def test_sends_dm_when_reviewer_has_not_responded(self, mock_get_client, mock_send_dm, mock_create_survey):
        """Test that reviewers without responses get Slack DMs as normal."""
        from apps.integrations.tasks import send_pr_surveys_task
        from apps.metrics.factories import PRSurveyFactory

        # Create survey without any responses
        survey = PRSurveyFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.author,
            author_ai_assisted=None,
        )
        mock_create_survey.return_value = survey

        # Mock Slack client
        mock_get_client.return_value = MagicMock()

        # Call task (no PRSurveyReview exists for any reviewer)
        result = send_pr_surveys_task(self.pr.id)

        # Verify DMs were sent to author + 2 reviewers = 3 total
        self.assertEqual(mock_send_dm.call_count, 3)

        # Verify result shows all sent, none skipped
        self.assertTrue(result["author_sent"])
        self.assertEqual(result["reviewers_sent"], 2)
        self.assertEqual(result.get("reviewers_skipped", 0), 0)
        self.assertEqual(result.get("author_skipped", False), False)

    @patch("apps.integrations.tasks.create_pr_survey")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    def test_sends_dm_when_prsurveyreview_exists_but_not_responded(
        self, mock_get_client, mock_send_dm, mock_create_survey
    ):
        """Test that reviewer with PRSurveyReview but responded_at=None still gets DM."""
        from apps.integrations.tasks import send_pr_surveys_task
        from apps.metrics.factories import PRSurveyFactory, PRSurveyReviewFactory

        # Create survey
        survey = PRSurveyFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.author,
            author_ai_assisted=None,
        )
        mock_create_survey.return_value = survey

        # Create PRSurveyReview for reviewer1 but WITHOUT responded_at (survey sent via Slack, not responded yet)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            reviewer=self.reviewer1,
            responded_at=None,  # Not responded yet
            ai_guess=None,
            quality_rating=None,
        )

        # Mock Slack client
        mock_get_client.return_value = MagicMock()

        # Call task
        result = send_pr_surveys_task(self.pr.id)

        # Verify DMs were sent to author + 2 reviewers = 3 total
        self.assertEqual(mock_send_dm.call_count, 3)

        # Verify no reviewers were skipped
        self.assertEqual(result.get("reviewers_skipped", 0), 0)
        self.assertEqual(result["reviewers_sent"], 2)

    @patch("apps.integrations.tasks.create_pr_survey")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    def test_task_returns_skipped_counts(self, mock_get_client, mock_send_dm, mock_create_survey):
        """Test that task returns reviewers_skipped and author_skipped in result."""
        from apps.integrations.tasks import send_pr_surveys_task
        from apps.metrics.factories import PRSurveyFactory, PRSurveyReviewFactory

        # Create survey with author responded
        survey = PRSurveyFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.author,
            author_ai_assisted=False,
            author_responded_at=timezone.now() - timedelta(hours=2),
        )
        mock_create_survey.return_value = survey

        # Create responded survey review for reviewer1
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            reviewer=self.reviewer1,
            responded_at=timezone.now() - timedelta(hours=3),
            ai_guess=False,
            quality_rating=2,
        )

        # Mock Slack client
        mock_get_client.return_value = MagicMock()

        # Call task
        result = send_pr_surveys_task(self.pr.id)

        # Verify result has skip counts
        self.assertIn("author_skipped", result)
        self.assertIn("reviewers_skipped", result)
        self.assertTrue(result["author_skipped"])
        self.assertEqual(result["reviewers_skipped"], 1)

        # Verify only reviewer2 got DM
        self.assertEqual(result["reviewers_sent"], 1)
        self.assertFalse(result["author_sent"])


class TestPostSurveyCommentTask(TestCase):
    """Tests for post_survey_comment_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.metrics.factories import PullRequestFactory, TeamMemberFactory

        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="encrypted_token_12345",
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )
        self.author = TeamMemberFactory(team=self.team, github_username="alice")
        self.pr = PullRequestFactory(
            team=self.team,
            state="merged",
            author=self.author,
            github_repo="acme-corp/api-server",
            github_pr_id=123,
        )

    @patch("apps.integrations.services.github_comments.post_survey_comment")
    def test_task_creates_pr_survey_for_merged_pr(self, mock_post_comment):
        """Test that task creates PRSurvey for merged PR."""
        from apps.integrations.tasks import post_survey_comment_task
        from apps.metrics.models import PRSurvey

        mock_post_comment.return_value = 999888777

        # Call the task
        result = post_survey_comment_task(self.pr.id)

        # Verify PRSurvey was created
        self.assertTrue(PRSurvey.objects.filter(pull_request=self.pr).exists())
        survey = PRSurvey.objects.get(pull_request=self.pr)

        # Verify survey has token
        self.assertIsNotNone(survey.token)
        self.assertGreater(len(survey.token), 0)

        # Verify survey has token_expires_at
        self.assertIsNotNone(survey.token_expires_at)

        # Verify result contains survey_id
        self.assertIn("survey_id", result)
        self.assertEqual(result["survey_id"], survey.id)

    @patch("apps.integrations.services.github_comments.post_survey_comment")
    def test_task_posts_comment_to_github(self, mock_post_comment):
        """Test that task posts comment to GitHub using post_survey_comment."""
        from apps.integrations.tasks import post_survey_comment_task

        comment_id = 999888777
        mock_post_comment.return_value = comment_id

        # Call the task
        post_survey_comment_task(self.pr.id)

        # Verify post_survey_comment was called with correct arguments
        mock_post_comment.assert_called_once()
        call_args = mock_post_comment.call_args
        self.assertEqual(call_args[0][0].id, self.pr.id)  # PR
        self.assertIsNotNone(call_args[0][1])  # Survey
        self.assertEqual(call_args[0][2], "encrypted_token_12345")  # Access token

    @patch("apps.integrations.services.github_comments.post_survey_comment")
    def test_task_stores_github_comment_id_on_survey(self, mock_post_comment):
        """Test that task stores github_comment_id on survey."""
        from apps.integrations.tasks import post_survey_comment_task
        from apps.metrics.models import PRSurvey

        comment_id = 999888777
        mock_post_comment.return_value = comment_id

        # Call the task
        result = post_survey_comment_task(self.pr.id)

        # Verify survey has github_comment_id stored
        survey = PRSurvey.objects.get(pull_request=self.pr)
        self.assertEqual(survey.github_comment_id, comment_id)

        # Verify result contains comment_id
        self.assertIn("comment_id", result)
        self.assertEqual(result["comment_id"], comment_id)

    @patch("apps.integrations.services.github_comments.post_survey_comment")
    def test_task_skips_non_merged_prs(self, mock_post_comment):
        """Test that task skips PRs that are not merged."""
        from apps.integrations.tasks import post_survey_comment_task
        from apps.metrics.factories import PullRequestFactory
        from apps.metrics.models import PRSurvey

        # Create open PR
        open_pr = PullRequestFactory(
            team=self.team,
            state="open",
            author=self.author,
        )

        # Call the task
        result = post_survey_comment_task(open_pr.id)

        # Verify task was skipped
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])
        self.assertIn("reason", result)
        self.assertIn("not merged", result["reason"].lower())

        # Verify no survey was created
        self.assertFalse(PRSurvey.objects.filter(pull_request=open_pr).exists())

        # Verify post_survey_comment was NOT called
        mock_post_comment.assert_not_called()

    @patch("apps.integrations.services.github_comments.post_survey_comment")
    def test_task_skips_if_survey_already_exists(self, mock_post_comment):
        """Test that task is idempotent - skips if survey already exists."""
        from apps.integrations.tasks import post_survey_comment_task
        from apps.metrics.factories import PRSurveyFactory
        from apps.metrics.models import PRSurvey

        # Create existing survey
        existing_survey = PRSurveyFactory(pull_request=self.pr, team=self.team)

        # Call the task
        result = post_survey_comment_task(self.pr.id)

        # Verify task was skipped
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])
        self.assertIn("reason", result)
        self.assertIn("already exists", result["reason"].lower())

        # Verify no duplicate survey was created
        self.assertEqual(PRSurvey.objects.filter(pull_request=self.pr).count(), 1)

        # Verify existing survey was not modified
        existing_survey.refresh_from_db()
        self.assertEqual(existing_survey.id, PRSurvey.objects.get(pull_request=self.pr).id)

        # Verify post_survey_comment was NOT called
        mock_post_comment.assert_not_called()

    @patch("apps.integrations.services.github_comments.post_survey_comment")
    def test_task_skips_if_no_github_integration_exists(self, mock_post_comment):
        """Test that task skips if no GitHub integration exists for team."""
        from apps.integrations.tasks import post_survey_comment_task
        from apps.metrics.factories import PullRequestFactory, TeamFactory
        from apps.metrics.models import PRSurvey

        # Create team without GitHub integration
        team_without_integration = TeamFactory()
        pr_no_integration = PullRequestFactory(
            team=team_without_integration,
            state="merged",
        )

        # Call the task
        result = post_survey_comment_task(pr_no_integration.id)

        # Verify task was skipped
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])
        self.assertIn("reason", result)
        self.assertIn("no github integration", result["reason"].lower())

        # Verify no survey was created
        self.assertFalse(PRSurvey.objects.filter(pull_request=pr_no_integration).exists())

        # Verify post_survey_comment was NOT called
        mock_post_comment.assert_not_called()

    @patch("apps.integrations.services.github_comments.post_survey_comment")
    def test_task_handles_github_api_errors_gracefully(self, mock_post_comment):
        """Test that task handles GitHub API errors gracefully without raising."""
        from github import GithubException

        from apps.integrations.tasks import post_survey_comment_task
        from apps.metrics.models import PRSurvey

        # Mock post_survey_comment to raise GithubException
        mock_post_comment.side_effect = GithubException(403, "API rate limit exceeded")

        # Call the task - should NOT raise
        result = post_survey_comment_task(self.pr.id)

        # Verify error is returned in result, not raised
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("rate limit", result["error"].lower())

        # Verify survey was created despite comment failure
        self.assertTrue(PRSurvey.objects.filter(pull_request=self.pr).exists())

        # Verify github_comment_id is None (comment was not posted)
        survey = PRSurvey.objects.get(pull_request=self.pr)
        self.assertIsNone(survey.github_comment_id)

    @patch("apps.integrations.services.github_comments.post_survey_comment")
    def test_task_returns_success_dict_with_survey_id_and_comment_id(self, mock_post_comment):
        """Test that task returns success dict with survey_id and comment_id."""
        from apps.integrations.tasks import post_survey_comment_task

        comment_id = 123456789
        mock_post_comment.return_value = comment_id

        # Call the task
        result = post_survey_comment_task(self.pr.id)

        # Verify result is a dict with expected keys
        self.assertIsInstance(result, dict)
        self.assertIn("survey_id", result)
        self.assertIn("comment_id", result)

        # Verify values are correct
        self.assertIsNotNone(result["survey_id"])
        self.assertEqual(result["comment_id"], comment_id)

        # Verify no error keys
        self.assertNotIn("error", result)
        self.assertNotIn("skipped", result)


class TestAggregateWeeklyMetricsTasks(TestCase):
    """Tests for weekly metrics aggregation Celery tasks."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from datetime import date, timedelta

        self.team = TeamFactory()

        # Calculate previous week's Monday for test assertions
        today = date.today()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        self.expected_week_start = last_monday

    @patch("apps.integrations.tasks.aggregate_team_weekly_metrics")
    def test_aggregate_team_weekly_metrics_task_calls_service(self, mock_aggregate):
        """Test that aggregate_team_weekly_metrics_task calls aggregate_team_weekly_metrics with correct team and week_start."""
        from apps.integrations.tasks import aggregate_team_weekly_metrics_task
        from apps.metrics.factories import WeeklyMetricsFactory

        # Mock the service to return some WeeklyMetrics instances
        mock_weekly_metrics = [
            WeeklyMetricsFactory.build(),
            WeeklyMetricsFactory.build(),
        ]
        mock_aggregate.return_value = mock_weekly_metrics

        # Call the task
        result = aggregate_team_weekly_metrics_task(self.team.id)

        # Verify aggregate_team_weekly_metrics was called once
        mock_aggregate.assert_called_once()

        # Verify it was called with correct team
        call_args = mock_aggregate.call_args
        self.assertEqual(call_args[0][0].id, self.team.id)

        # Verify it was called with previous week's Monday
        actual_week_start = call_args[0][1]
        self.assertEqual(actual_week_start, self.expected_week_start)

        # Verify result contains count of records created/updated
        self.assertEqual(result, 2)

    def test_aggregate_team_weekly_metrics_task_handles_missing_team(self):
        """Test that aggregate_team_weekly_metrics_task handles Team.DoesNotExist gracefully."""
        from apps.integrations.tasks import aggregate_team_weekly_metrics_task

        non_existent_team_id = 99999

        # Call the task with non-existent team_id - should not raise exception
        result = aggregate_team_weekly_metrics_task(non_existent_team_id)

        # Verify result is None or 0 (no exception raised)
        self.assertIn(result, [None, 0])

    @patch("apps.integrations.tasks.aggregate_team_weekly_metrics_task")
    def test_aggregate_all_teams_weekly_metrics_task_dispatches_per_team(self, mock_task):
        """Test that aggregate_all_teams_weekly_metrics_task dispatches task for each team with GitHub integration."""
        from apps.integrations.tasks import aggregate_all_teams_weekly_metrics_task

        # Create multiple teams with GitHubIntegration
        team1 = TeamFactory()
        team2 = TeamFactory()
        team3 = TeamFactory()

        GitHubIntegrationFactory(team=team1)
        GitHubIntegrationFactory(team=team2)
        GitHubIntegrationFactory(team=team3)

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = aggregate_all_teams_weekly_metrics_task()

        # Verify delay was called for each team
        self.assertEqual(mock_delay.call_count, 3)

        # Verify the correct team IDs were passed
        called_team_ids = {call[0][0] for call in mock_delay.call_args_list}
        expected_team_ids = {team1.id, team2.id, team3.id}
        self.assertEqual(called_team_ids, expected_team_ids)

        # Verify result contains count of teams processed
        self.assertEqual(result, 3)

    @patch("apps.integrations.tasks.aggregate_team_weekly_metrics_task")
    def test_aggregate_all_teams_weekly_metrics_task_skips_teams_without_github(self, mock_task):
        """Test that aggregate_all_teams_weekly_metrics_task skips teams without GitHub integration."""
        from apps.integrations.tasks import aggregate_all_teams_weekly_metrics_task

        # Create teams
        team_with_github = TeamFactory()
        team_without_github = TeamFactory()

        # Only team1 has GitHub integration
        GitHubIntegrationFactory(team=team_with_github)

        # Mock the delay method
        mock_delay = MagicMock()
        mock_task.delay = mock_delay

        # Call the task
        result = aggregate_all_teams_weekly_metrics_task()

        # Verify delay was called only once (for team with GitHub integration)
        self.assertEqual(mock_delay.call_count, 1)

        # Verify only the team with GitHub integration was dispatched
        called_team_ids = {call[0][0] for call in mock_delay.call_args_list}
        self.assertEqual(called_team_ids, {team_with_github.id})

        # Verify result contains count of teams processed (only 1)
        self.assertEqual(result, 1)
