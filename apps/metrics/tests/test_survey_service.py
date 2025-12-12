"""Tests for Survey Service (Section 7).

Business logic for managing PR surveys - creating them, recording responses,
and triggering reveals.
"""

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import SlackIntegrationFactory
from apps.metrics.factories import (
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
