"""Tests for Survey Service (Section 7).

Business logic for managing PR surveys - creating them, recording responses,
and triggering reveals.
"""

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import SlackIntegrationFactory
from apps.metrics.factories import (
    CommitFactory,
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import survey_service


class TestCreatePRSurvey(TestCase):
    """Tests for create_pr_survey function."""

    def test_create_pr_survey_creates_survey_record(self):
        """Test that create_pr_survey creates a PRSurvey record."""
        pr = PullRequestFactory()

        survey = survey_service.create_pr_survey(pr)

        self.assertIsNotNone(survey)
        self.assertIsNotNone(survey.id)

    def test_create_pr_survey_links_to_pull_request(self):
        """Test that create_pr_survey links survey to the pull request."""
        pr = PullRequestFactory()

        survey = survey_service.create_pr_survey(pr)

        self.assertEqual(survey.pull_request, pr)

    def test_create_pr_survey_sets_author_from_pr(self):
        """Test that create_pr_survey sets author from the PR."""
        team = TeamFactory()
        author = TeamMemberFactory(team=team, display_name="Alice")
        pr = PullRequestFactory(team=team, author=author)

        survey = survey_service.create_pr_survey(pr)

        self.assertEqual(survey.author, author)


class TestCreatePRSurveyAIAutoDetection(TestCase):
    """Tests for AI auto-detection in create_pr_survey (Phase 0.3)."""

    def test_create_pr_survey_detects_ai_from_commit_flag(self):
        """Test that create_pr_survey auto-detects AI from commit is_ai_assisted flag."""
        team = TeamFactory()
        pr = PullRequestFactory(team=team)
        # Create commit with is_ai_assisted=True (already flagged during sync)
        CommitFactory(team=team, pull_request=pr, is_ai_assisted=True)

        survey = survey_service.create_pr_survey(pr)

        self.assertTrue(survey.author_ai_assisted)
        self.assertEqual(survey.author_response_source, "auto")

    def test_create_pr_survey_detects_ai_from_commit_message_copilot(self):
        """Test that create_pr_survey detects AI from Copilot co-author in commit message."""
        team = TeamFactory()
        pr = PullRequestFactory(team=team)
        CommitFactory(
            team=team,
            pull_request=pr,
            is_ai_assisted=False,  # Not flagged yet
            message="Add feature\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>",
        )

        survey = survey_service.create_pr_survey(pr)

        self.assertTrue(survey.author_ai_assisted)
        self.assertEqual(survey.author_response_source, "auto")

    def test_create_pr_survey_detects_ai_from_commit_message_claude(self):
        """Test that create_pr_survey detects AI from Claude co-author in commit message."""
        team = TeamFactory()
        pr = PullRequestFactory(team=team)
        CommitFactory(
            team=team,
            pull_request=pr,
            is_ai_assisted=False,
            message="Fix bug\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)",
        )

        survey = survey_service.create_pr_survey(pr)

        self.assertTrue(survey.author_ai_assisted)
        self.assertEqual(survey.author_response_source, "auto")

    def test_create_pr_survey_no_auto_detection_for_normal_commits(self):
        """Test that create_pr_survey does NOT auto-detect for normal commits."""
        team = TeamFactory()
        pr = PullRequestFactory(team=team)
        CommitFactory(
            team=team,
            pull_request=pr,
            is_ai_assisted=False,
            message="Normal commit message without AI signatures",
        )

        survey = survey_service.create_pr_survey(pr)

        self.assertIsNone(survey.author_ai_assisted)
        self.assertIsNone(survey.author_response_source)

    def test_create_pr_survey_no_auto_detection_for_pr_without_commits(self):
        """Test that create_pr_survey works for PRs without commits."""
        team = TeamFactory()
        pr = PullRequestFactory(team=team)
        # No commits created

        survey = survey_service.create_pr_survey(pr)

        self.assertIsNone(survey.author_ai_assisted)
        self.assertIsNone(survey.author_response_source)

    def test_create_pr_survey_detects_ai_from_any_commit(self):
        """Test that create_pr_survey detects AI if ANY commit has AI signature."""
        team = TeamFactory()
        pr = PullRequestFactory(team=team)
        # First commit: normal
        CommitFactory(team=team, pull_request=pr, is_ai_assisted=False, message="Normal commit 1")
        # Second commit: AI-assisted
        CommitFactory(team=team, pull_request=pr, is_ai_assisted=True, message="AI commit")
        # Third commit: normal
        CommitFactory(team=team, pull_request=pr, is_ai_assisted=False, message="Normal commit 2")

        survey = survey_service.create_pr_survey(pr)

        self.assertTrue(survey.author_ai_assisted)
        self.assertEqual(survey.author_response_source, "auto")

    def test_create_pr_survey_sets_author_responded_at_for_auto_detection(self):
        """Test that auto-detected surveys set author_responded_at timestamp."""
        team = TeamFactory()
        pr = PullRequestFactory(team=team)
        CommitFactory(team=team, pull_request=pr, is_ai_assisted=True)

        before = timezone.now()
        survey = survey_service.create_pr_survey(pr)
        after = timezone.now()

        self.assertIsNotNone(survey.author_responded_at)
        self.assertGreaterEqual(survey.author_responded_at, before)
        self.assertLessEqual(survey.author_responded_at, after)


class TestRecordAuthorResponse(TestCase):
    """Tests for record_author_response function."""

    def test_record_author_response_sets_ai_assisted_field(self):
        """Test that record_author_response sets the ai_assisted field."""
        survey = PRSurveyFactory(author_ai_assisted=None)

        survey_service.record_author_response(survey, ai_assisted=True)

        survey.refresh_from_db()
        self.assertTrue(survey.author_ai_assisted)

    def test_record_author_response_sets_responded_at_timestamp(self):
        """Test that record_author_response sets responded_at timestamp."""
        survey = PRSurveyFactory(author_ai_assisted=None, author_responded_at=None)

        before = timezone.now()
        survey_service.record_author_response(survey, ai_assisted=False)
        after = timezone.now()

        survey.refresh_from_db()
        self.assertIsNotNone(survey.author_responded_at)
        self.assertGreaterEqual(survey.author_responded_at, before)
        self.assertLessEqual(survey.author_responded_at, after)

    def test_record_author_response_sets_response_source_github(self):
        """Test that record_author_response sets response_source when provided."""
        survey = PRSurveyFactory(author_ai_assisted=None, author_response_source=None)

        survey_service.record_author_response(survey, ai_assisted=True, response_source="github")

        survey.refresh_from_db()
        self.assertEqual(survey.author_response_source, "github")

    def test_record_author_response_sets_response_source_slack(self):
        """Test that record_author_response sets response_source to slack."""
        survey = PRSurveyFactory(author_ai_assisted=None, author_response_source=None)

        survey_service.record_author_response(survey, ai_assisted=False, response_source="slack")

        survey.refresh_from_db()
        self.assertEqual(survey.author_response_source, "slack")

    def test_record_author_response_defaults_to_web_source(self):
        """Test that record_author_response defaults to 'web' when no source provided."""
        survey = PRSurveyFactory(author_ai_assisted=None, author_response_source=None)

        survey_service.record_author_response(survey, ai_assisted=True)

        survey.refresh_from_db()
        self.assertEqual(survey.author_response_source, "web")


class TestCreateReviewerSurvey(TestCase):
    """Tests for create_reviewer_survey function."""

    def test_create_reviewer_survey_creates_pr_survey_review(self):
        """Test that create_reviewer_survey creates a PRSurveyReview record."""
        survey = PRSurveyFactory()
        reviewer = TeamMemberFactory(team=survey.team)

        survey_review = survey_service.create_reviewer_survey(survey, reviewer)

        self.assertIsNotNone(survey_review)
        self.assertIsNotNone(survey_review.id)
        self.assertEqual(survey_review.survey, survey)
        self.assertEqual(survey_review.reviewer, reviewer)


class TestRecordReviewerResponse(TestCase):
    """Tests for record_reviewer_response function."""

    def test_record_reviewer_response_sets_quality_rating(self):
        """Test that record_reviewer_response sets quality_rating."""
        survey_review = PRSurveyReviewFactory(quality_rating=None)

        survey_service.record_reviewer_response(survey_review, quality=3, ai_guess=True)

        survey_review.refresh_from_db()
        self.assertEqual(survey_review.quality_rating, 3)

    def test_record_reviewer_response_sets_ai_guess(self):
        """Test that record_reviewer_response sets ai_guess."""
        survey_review = PRSurveyReviewFactory(ai_guess=None)

        survey_service.record_reviewer_response(survey_review, quality=2, ai_guess=True)

        survey_review.refresh_from_db()
        self.assertTrue(survey_review.ai_guess)

    def test_record_reviewer_response_calculates_guess_correct_when_author_responded(self):
        """Test that guess_correct is calculated when author has responded."""
        survey = PRSurveyFactory(author_ai_assisted=True, author_responded_at=timezone.now())
        survey_review = PRSurveyReviewFactory(survey=survey, guess_correct=None)

        # Reviewer guesses True, author said True -> correct
        survey_service.record_reviewer_response(survey_review, quality=3, ai_guess=True)

        survey_review.refresh_from_db()
        self.assertTrue(survey_review.guess_correct)

    def test_record_reviewer_response_leaves_guess_correct_null_when_author_not_responded(self):
        """Test that guess_correct is null when author hasn't responded."""
        survey = PRSurveyFactory(author_ai_assisted=None, author_responded_at=None)
        survey_review = PRSurveyReviewFactory(survey=survey, guess_correct=None)

        survey_service.record_reviewer_response(survey_review, quality=2, ai_guess=False)

        survey_review.refresh_from_db()
        self.assertIsNone(survey_review.guess_correct)

    def test_record_reviewer_response_sets_response_source_github(self):
        """Test that record_reviewer_response sets response_source when provided."""
        survey_review = PRSurveyReviewFactory(quality_rating=None, response_source=None)

        survey_service.record_reviewer_response(survey_review, quality=3, ai_guess=True, response_source="github")

        survey_review.refresh_from_db()
        self.assertEqual(survey_review.response_source, "github")

    def test_record_reviewer_response_defaults_to_web_source(self):
        """Test that record_reviewer_response defaults to 'web' when no source provided."""
        survey_review = PRSurveyReviewFactory(quality_rating=None, response_source=None)

        survey_service.record_reviewer_response(survey_review, quality=2, ai_guess=False)

        survey_review.refresh_from_db()
        self.assertEqual(survey_review.response_source, "web")


class TestRecordReviewerQualityVote(TestCase):
    """Tests for record_reviewer_quality_vote function (one-click voting).

    One-click voting from PR description only captures quality rating,
    not the AI guess. This function handles that case.
    """

    def test_record_reviewer_quality_vote_sets_quality_rating(self):
        """Test that record_reviewer_quality_vote sets quality_rating."""
        survey_review = PRSurveyReviewFactory(quality_rating=None)

        survey_service.record_reviewer_quality_vote(survey_review, quality=3, response_source="github")

        survey_review.refresh_from_db()
        self.assertEqual(survey_review.quality_rating, 3)

    def test_record_reviewer_quality_vote_sets_responded_at(self):
        """Test that record_reviewer_quality_vote sets responded_at timestamp."""
        survey_review = PRSurveyReviewFactory(quality_rating=None, responded_at=None)

        before = timezone.now()
        survey_service.record_reviewer_quality_vote(survey_review, quality=2, response_source="github")
        after = timezone.now()

        survey_review.refresh_from_db()
        self.assertIsNotNone(survey_review.responded_at)
        self.assertGreaterEqual(survey_review.responded_at, before)
        self.assertLessEqual(survey_review.responded_at, after)

    def test_record_reviewer_quality_vote_sets_response_source(self):
        """Test that record_reviewer_quality_vote sets response_source."""
        survey_review = PRSurveyReviewFactory(quality_rating=None, response_source=None)

        survey_service.record_reviewer_quality_vote(survey_review, quality=1, response_source="github")

        survey_review.refresh_from_db()
        self.assertEqual(survey_review.response_source, "github")

    def test_record_reviewer_quality_vote_does_not_set_ai_guess(self):
        """Test that record_reviewer_quality_vote leaves ai_guess as None."""
        survey_review = PRSurveyReviewFactory(quality_rating=None, ai_guess=None)

        survey_service.record_reviewer_quality_vote(survey_review, quality=3, response_source="github")

        survey_review.refresh_from_db()
        self.assertIsNone(survey_review.ai_guess)


class TestCheckAndSendReveal(TestCase):
    """Tests for check_and_send_reveal function."""

    def test_check_and_send_reveal_returns_false_if_author_not_responded(self):
        """Test that check_and_send_reveal returns False if author hasn't responded."""
        survey = PRSurveyFactory(author_ai_assisted=None, author_responded_at=None)
        survey_review = PRSurveyReviewFactory(
            survey=survey, quality_rating=3, ai_guess=True, responded_at=timezone.now()
        )
        SlackIntegrationFactory(team=survey.team, reveals_enabled=True)

        result = survey_service.check_and_send_reveal(survey, survey_review)

        self.assertFalse(result)

    def test_check_and_send_reveal_returns_false_if_reveals_disabled(self):
        """Test that check_and_send_reveal returns False if reveals_enabled is False."""
        survey = PRSurveyFactory(author_ai_assisted=True, author_responded_at=timezone.now())
        survey_review = PRSurveyReviewFactory(
            survey=survey, quality_rating=2, ai_guess=False, responded_at=timezone.now()
        )
        SlackIntegrationFactory(team=survey.team, reveals_enabled=False)

        result = survey_service.check_and_send_reveal(survey, survey_review)

        self.assertFalse(result)


class TestGetReviewerAccuracyStats(TestCase):
    """Tests for get_reviewer_accuracy_stats function."""

    def test_get_reviewer_accuracy_stats_returns_correct_counts(self):
        """Test that get_reviewer_accuracy_stats returns correct counts."""
        team = TeamFactory()
        reviewer = TeamMemberFactory(team=team)

        # Create 5 reviews: 3 correct, 2 incorrect
        for correct in [True, True, True, False, False]:
            survey = PRSurveyFactory(team=team)
            PRSurveyReviewFactory(team=team, survey=survey, reviewer=reviewer, guess_correct=correct)

        stats = survey_service.get_reviewer_accuracy_stats(reviewer)

        self.assertEqual(stats["correct"], 3)
        self.assertEqual(stats["total"], 5)
        self.assertEqual(stats["percentage"], 60.0)

    def test_get_reviewer_accuracy_stats_handles_zero_total(self):
        """Test that get_reviewer_accuracy_stats handles zero total without division error."""
        reviewer = TeamMemberFactory()

        stats = survey_service.get_reviewer_accuracy_stats(reviewer)

        self.assertEqual(stats["correct"], 0)
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["percentage"], 0.0)
