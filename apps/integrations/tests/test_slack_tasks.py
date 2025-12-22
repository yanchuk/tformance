"""Tests for Slack-related Celery tasks."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.factories import SlackIntegrationFactory
from apps.metrics.factories import (
    PRReviewFactory,
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)


class TestSendPRSurveysTask(TestCase):
    """Tests for send_pr_surveys_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, slack_user_id="U001")
        self.reviewer1 = TeamMemberFactory(team=self.team, slack_user_id="U002")
        self.reviewer2 = TeamMemberFactory(team=self.team, slack_user_id="U003")
        self.pr = PullRequestFactory(
            team=self.team,
            author=self.author,
            state="merged",
        )
        # Create reviews for the PR
        PRReviewFactory(team=self.team, pull_request=self.pr, reviewer=self.reviewer1)
        PRReviewFactory(team=self.team, pull_request=self.pr, reviewer=self.reviewer2)

    def test_gets_pull_request_by_id(self):
        """Test that send_pr_surveys_task gets the PR by ID."""
        from apps.integrations.tasks import send_pr_surveys_task

        SlackIntegrationFactory(team=self.team, surveys_enabled=True)

        with (
            patch("apps.integrations.tasks.create_pr_survey") as mock_create_survey,
            patch("apps.integrations.tasks.send_dm") as mock_send_dm,
        ):
            mock_survey = MagicMock(id=1)
            mock_create_survey.return_value = mock_survey
            mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

            result = send_pr_surveys_task(self.pr.id)

            # Should successfully call the task with PR id
            self.assertIsNotNone(result)

    def test_skips_if_pr_not_merged(self):
        """Test that the task skips if PR is not merged."""
        from apps.integrations.tasks import send_pr_surveys_task

        # Create an open PR
        open_pr = PullRequestFactory(team=self.team, author=self.author, state="open")
        SlackIntegrationFactory(team=self.team, surveys_enabled=True)

        result = send_pr_surveys_task(open_pr.id)

        # Should skip non-merged PRs
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])

    def test_skips_if_no_slack_integration(self):
        """Test that the task skips if team has no SlackIntegration."""
        from apps.integrations.tasks import send_pr_surveys_task

        # No SlackIntegration created
        result = send_pr_surveys_task(self.pr.id)

        # Should skip when no integration exists
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])

    def test_skips_if_surveys_disabled(self):
        """Test that the task skips if surveys_enabled is False."""
        from apps.integrations.tasks import send_pr_surveys_task

        SlackIntegrationFactory(team=self.team, surveys_enabled=False)

        result = send_pr_surveys_task(self.pr.id)

        # Should skip when surveys are disabled
        self.assertIsInstance(result, dict)
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"])

    @patch("apps.integrations.tasks.create_pr_survey")
    def test_creates_pr_survey(self, mock_create_survey):
        """Test that the task creates a PRSurvey."""
        from apps.integrations.tasks import send_pr_surveys_task

        SlackIntegrationFactory(team=self.team, surveys_enabled=True)

        mock_survey = MagicMock(id=1)
        mock_create_survey.return_value = mock_survey

        with patch("apps.integrations.tasks.send_dm") as mock_send_dm:
            mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

            send_pr_surveys_task(self.pr.id)

        # Verify create_pr_survey was called with the correct PR
        mock_create_survey.assert_called_once()
        called_pr = mock_create_survey.call_args[0][0]
        self.assertEqual(called_pr.id, self.pr.id)

    @patch("apps.integrations.tasks.create_pr_survey")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    @patch("apps.integrations.tasks.build_author_survey_blocks")
    def test_sends_author_dm_when_author_has_slack_user_id(
        self, mock_build_blocks, mock_get_client, mock_send_dm, mock_create_survey
    ):
        """Test that the task sends DM to author if author has slack_user_id."""
        from apps.integrations.tasks import send_pr_surveys_task

        SlackIntegrationFactory(team=self.team, surveys_enabled=True)

        mock_survey = MagicMock(id=1)
        mock_survey.has_author_responded.return_value = False  # Author hasn't responded yet
        mock_create_survey.return_value = mock_survey
        mock_build_blocks.return_value = [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

        send_pr_surveys_task(self.pr.id)

        # Verify DM was sent to author
        mock_send_dm.assert_called()
        # Check that author's slack_user_id was used
        call_args = mock_send_dm.call_args_list
        author_dm_call = [call for call in call_args if call[0][1] == self.author.slack_user_id]
        self.assertTrue(len(author_dm_call) > 0)

    @patch("apps.integrations.tasks.create_pr_survey")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    def test_skips_author_if_no_slack_user_id(self, mock_get_client, mock_send_dm, mock_create_survey):
        """Test that the task skips author DM if author has no slack_user_id."""
        from apps.integrations.tasks import send_pr_surveys_task

        # Create author without slack_user_id
        author_no_slack = TeamMemberFactory(team=self.team, slack_user_id="")
        pr_no_slack = PullRequestFactory(team=self.team, author=author_no_slack, state="merged")

        SlackIntegrationFactory(team=self.team, surveys_enabled=True)

        mock_survey = MagicMock(id=1)
        mock_create_survey.return_value = mock_survey
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

        result = send_pr_surveys_task(pr_no_slack.id)

        # Result should indicate author was not sent
        self.assertIsInstance(result, dict)
        self.assertIn("author_sent", result)
        self.assertFalse(result["author_sent"])

    @patch("apps.integrations.tasks.create_pr_survey")
    @patch("apps.integrations.tasks.create_reviewer_survey")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    @patch("apps.integrations.tasks.build_reviewer_survey_blocks")
    def test_sends_reviewer_dms(
        self, mock_build_reviewer_blocks, mock_get_client, mock_send_dm, mock_create_reviewer_survey, mock_create_survey
    ):
        """Test that the task sends DMs to reviewers."""
        from apps.integrations.tasks import send_pr_surveys_task

        SlackIntegrationFactory(team=self.team, surveys_enabled=True)

        mock_survey = MagicMock(id=1)
        mock_create_survey.return_value = mock_survey
        mock_create_reviewer_survey.return_value = MagicMock(id=2)
        mock_build_reviewer_blocks.return_value = [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

        send_pr_surveys_task(self.pr.id)

        # Verify DMs were sent to reviewers
        # Should be called at least twice for our two reviewers
        self.assertGreaterEqual(mock_send_dm.call_count, 2)

    @patch("apps.integrations.tasks.create_pr_survey")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    def test_returns_correct_counts(self, mock_get_client, mock_send_dm, mock_create_survey):
        """Test that the task returns correct counts in result dict."""
        from apps.integrations.tasks import send_pr_surveys_task

        SlackIntegrationFactory(team=self.team, surveys_enabled=True)

        mock_survey = MagicMock(id=1)
        mock_survey.has_author_responded.return_value = False  # Author hasn't responded yet
        mock_create_survey.return_value = mock_survey
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

        with patch("apps.integrations.tasks.create_reviewer_survey") as mock_create_reviewer_survey:
            mock_create_reviewer_survey.return_value = MagicMock(id=2)
            result = send_pr_surveys_task(self.pr.id)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("author_sent", result)
        self.assertIn("reviewers_sent", result)
        self.assertIn("errors", result)

        # We have 2 reviewers
        self.assertEqual(result["reviewers_sent"], 2)
        self.assertTrue(result["author_sent"])


class TestSendRevealTask(TestCase):
    """Tests for send_reveal_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.slack_integration = SlackIntegrationFactory(team=self.team, surveys_enabled=True, reveals_enabled=True)
        self.author = TeamMemberFactory(team=self.team, slack_user_id="U001")
        self.reviewer = TeamMemberFactory(team=self.team, slack_user_id="U002")
        self.pr = PullRequestFactory(team=self.team, author=self.author, state="merged")
        self.survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author, author_ai_assisted=True)
        self.survey_review = PRSurveyReviewFactory(
            team=self.team,
            survey=self.survey,
            reviewer=self.reviewer,
            quality_rating=3,
            ai_guess=True,
            guess_correct=True,
        )

    @patch("apps.integrations.tasks.get_slack_client")
    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_reviewer_accuracy_stats")
    def test_sends_reveal_when_conditions_met(self, mock_get_stats, mock_send_dm, mock_get_client):
        """Test that send_reveal_task sends reveal when all conditions are met."""
        from apps.integrations.tasks import send_reveal_task

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_get_stats.return_value = {"correct": 5, "total": 10, "percentage": 50.0}
        mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

        result = send_reveal_task(self.survey_review.id)

        # Verify reveal was sent
        self.assertIsInstance(result, dict)
        self.assertIn("sent", result)
        self.assertTrue(result["sent"])
        mock_send_dm.assert_called_once()

    def test_returns_error_when_survey_review_not_found(self):
        """Test that the task returns error when PRSurveyReview doesn't exist."""
        from apps.integrations.tasks import send_reveal_task

        non_existent_id = 99999

        result = send_reveal_task(non_existent_id)

        # Verify error is returned
        self.assertIsInstance(result, dict)
        self.assertIn("sent", result)
        self.assertFalse(result["sent"])
        self.assertIn("error", result)


class TestSyncSlackUsersTask(TestCase):
    """Tests for sync_slack_users_task Celery task."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.slack_integration = SlackIntegrationFactory(team=self.team)

    @patch("apps.integrations.tasks.sync_slack_users")
    def test_syncs_users_and_returns_report(self, mock_sync_slack_users):
        """Test that sync_slack_users_task calls sync_slack_users and returns report."""
        from apps.integrations.tasks import sync_slack_users_task

        mock_sync_slack_users.return_value = {
            "matched_count": 5,
            "unmatched_count": 2,
            "unmatched_users": [
                {"id": "U001", "email": "test1@example.com", "real_name": "Test User 1"},
                {"id": "U002", "email": "test2@example.com", "real_name": "Test User 2"},
            ],
        }

        result = sync_slack_users_task(self.team.id)

        # Verify sync_slack_users was called
        mock_sync_slack_users.assert_called_once()

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertEqual(result["matched_count"], 5)
        self.assertEqual(result["unmatched_count"], 2)
        self.assertEqual(len(result["unmatched_users"]), 2)


class TestSlackSurveyFallbackTask(TestCase):
    """Tests for Slack survey fallback task scheduling."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.factories import GitHubIntegrationFactory, IntegrationCredentialFactory

        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, slack_user_id="U001")
        self.pr = PullRequestFactory(team=self.team, author=self.author, state="merged")
        # Create GitHub integration for update_pr_description_survey_task tests
        self.credential = IntegrationCredentialFactory(team=self.team, provider="github")
        self.github_integration = GitHubIntegrationFactory(team=self.team, credential=self.credential)

    @patch("apps.integrations.tasks.send_pr_surveys_task.apply_async")
    def test_schedule_slack_survey_fallback_schedules_with_countdown(self, mock_apply_async):
        """Test that schedule_slack_survey_fallback_task schedules with 1-hour countdown."""
        from apps.integrations.tasks import schedule_slack_survey_fallback_task

        schedule_slack_survey_fallback_task(self.pr.id)

        # Verify send_pr_surveys_task is scheduled with 1-hour countdown
        mock_apply_async.assert_called_once()
        call_kwargs = mock_apply_async.call_args[1]
        self.assertEqual(call_kwargs.get("countdown"), 3600)  # 1 hour in seconds

    @patch("apps.integrations.tasks.send_pr_surveys_task.apply_async")
    def test_schedule_slack_survey_fallback_passes_pr_id(self, mock_apply_async):
        """Test that schedule_slack_survey_fallback_task passes PR ID correctly."""
        from apps.integrations.tasks import schedule_slack_survey_fallback_task

        schedule_slack_survey_fallback_task(self.pr.id)

        # Verify PR ID is passed to the scheduled task
        mock_apply_async.assert_called_once()
        call_args = mock_apply_async.call_args[0]
        self.assertEqual(call_args, ((self.pr.id,),))

    def test_schedule_slack_survey_fallback_returns_dict(self):
        """Test that schedule_slack_survey_fallback_task returns status dict."""
        from apps.integrations.tasks import schedule_slack_survey_fallback_task

        with patch("apps.integrations.tasks.send_pr_surveys_task.apply_async") as mock_apply_async:
            mock_apply_async.return_value = MagicMock(id="task-123")
            result = schedule_slack_survey_fallback_task(self.pr.id)

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("scheduled", result)
        self.assertTrue(result["scheduled"])
        self.assertIn("task_id", result)

    @patch("apps.integrations.tasks.schedule_slack_survey_fallback_task.delay")
    @patch("apps.integrations.tasks.github_pr_description.update_pr_description_with_survey")
    def test_update_pr_description_task_schedules_slack_fallback(self, mock_update_description, mock_schedule_fallback):
        """Test that update_pr_description_survey_task schedules Slack fallback on success."""
        from apps.integrations.tasks import update_pr_description_survey_task

        mock_update_description.return_value = None  # Success
        mock_schedule_fallback.return_value = MagicMock(id="fallback-task-123")

        result = update_pr_description_survey_task(self.pr.id)

        # Verify Slack fallback was scheduled
        mock_schedule_fallback.assert_called_once_with(self.pr.id)
        self.assertTrue(result.get("success"))
        self.assertIn("slack_fallback_scheduled", result)


class TestSendPRSurveysTaskSkipLogic(TestCase):
    """Tests for send_pr_surveys_task skip logic for already-responded users."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.slack_integration = SlackIntegrationFactory(team=self.team, surveys_enabled=True)
        self.author = TeamMemberFactory(team=self.team, slack_user_id="U001")
        self.reviewer = TeamMemberFactory(team=self.team, slack_user_id="U002")
        self.pr = PullRequestFactory(team=self.team, author=self.author, state="merged")
        PRReviewFactory(team=self.team, pull_request=self.pr, reviewer=self.reviewer)

    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    def test_skips_author_dm_when_already_responded_via_github(self, mock_get_client, mock_send_dm):
        """Test that author DM is skipped if author already responded via GitHub."""
        from apps.integrations.tasks import send_pr_surveys_task
        from apps.metrics.models import PRSurvey

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

        # Create survey where author has already responded (simulating GitHub one-click)
        from django.utils import timezone

        PRSurvey.objects.create(
            team=self.team,
            pull_request=self.pr,
            author=self.author,
            author_ai_assisted=True,  # Already responded
            author_response_source="github",
            author_responded_at=timezone.now(),
        )

        result = send_pr_surveys_task(self.pr.id)

        # Should indicate author was skipped, not sent
        self.assertFalse(result.get("author_sent", True))
        self.assertTrue(result.get("author_skipped", False))

    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    def test_skips_author_dm_when_auto_detected(self, mock_get_client, mock_send_dm):
        """Test that author DM is skipped if AI was auto-detected."""
        from apps.integrations.tasks import send_pr_surveys_task
        from apps.metrics.models import PRSurvey

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

        # Create survey where author response was auto-detected
        from django.utils import timezone

        PRSurvey.objects.create(
            team=self.team,
            pull_request=self.pr,
            author=self.author,
            author_ai_assisted=True,  # Auto-detected
            author_response_source="auto",
            author_responded_at=timezone.now(),
        )

        result = send_pr_surveys_task(self.pr.id)

        # Should indicate author was skipped due to auto-detection
        self.assertFalse(result.get("author_sent", True))
        self.assertTrue(result.get("author_skipped", False))

    @patch("apps.integrations.tasks.send_dm")
    @patch("apps.integrations.tasks.get_slack_client")
    @patch("apps.integrations.tasks.create_pr_survey")
    def test_skips_reviewer_dm_when_already_responded_via_github(
        self, mock_create_survey, mock_get_client, mock_send_dm
    ):
        """Test that reviewer DM is skipped if reviewer already responded via GitHub."""
        from apps.integrations.tasks import send_pr_surveys_task
        from apps.metrics.models import PRSurveyReview

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_send_dm.return_value = {"ok": True, "ts": "123.456", "channel": "D001"}

        # Create survey
        survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author)
        mock_create_survey.return_value = survey

        # Create reviewer survey with existing response (simulating GitHub one-click)
        from django.utils import timezone

        PRSurveyReview.objects.create(
            team=self.team,
            survey=survey,
            reviewer=self.reviewer,
            quality_rating=3,
            response_source="github",
            responded_at=timezone.now(),
        )

        result = send_pr_surveys_task(self.pr.id)

        # Should indicate reviewer was skipped
        self.assertEqual(result.get("reviewers_skipped", 0), 1)
