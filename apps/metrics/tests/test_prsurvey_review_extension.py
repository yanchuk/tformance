"""Tests for PRSurveyReview extension fields (Review Experience Survey).

P1 Feature: Add feedback_clarity and review_burden fields to capture
reviewer experience metrics for extended surveys (~25% of reviewers).
"""

from django.test import TestCase

from apps.metrics.factories import PRSurveyReviewFactory, TeamFactory


class TestPRSurveyReviewFeedbackClarityField(TestCase):
    """Tests for the feedback_clarity field on PRSurveyReview."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_prsurvey_review_has_feedback_clarity_field(self):
        """Test that PRSurveyReview model has feedback_clarity field."""
        review = PRSurveyReviewFactory(team=self.team)

        # The field should exist and be accessible
        self.assertTrue(hasattr(review, "feedback_clarity"))

    def test_feedback_clarity_accepts_null(self):
        """Test that feedback_clarity field accepts null values."""
        review = PRSurveyReviewFactory(team=self.team, feedback_clarity=None)

        review.refresh_from_db()
        self.assertIsNone(review.feedback_clarity)

    def test_feedback_clarity_accepts_value_1(self):
        """Test that feedback_clarity accepts value 1 (Unclear)."""
        review = PRSurveyReviewFactory(team=self.team, feedback_clarity=1)

        review.refresh_from_db()
        self.assertEqual(review.feedback_clarity, 1)

    def test_feedback_clarity_accepts_value_2(self):
        """Test that feedback_clarity accepts value 2 (OK)."""
        review = PRSurveyReviewFactory(team=self.team, feedback_clarity=2)

        review.refresh_from_db()
        self.assertEqual(review.feedback_clarity, 2)

    def test_feedback_clarity_accepts_value_3(self):
        """Test that feedback_clarity accepts value 3 (Clear)."""
        review = PRSurveyReviewFactory(team=self.team, feedback_clarity=3)

        review.refresh_from_db()
        self.assertEqual(review.feedback_clarity, 3)

    def test_feedback_clarity_accepts_value_4(self):
        """Test that feedback_clarity accepts value 4 (Very clear)."""
        review = PRSurveyReviewFactory(team=self.team, feedback_clarity=4)

        review.refresh_from_db()
        self.assertEqual(review.feedback_clarity, 4)

    def test_feedback_clarity_accepts_value_5(self):
        """Test that feedback_clarity accepts value 5 (Excellent)."""
        review = PRSurveyReviewFactory(team=self.team, feedback_clarity=5)

        review.refresh_from_db()
        self.assertEqual(review.feedback_clarity, 5)


class TestPRSurveyReviewReviewBurdenField(TestCase):
    """Tests for the review_burden field on PRSurveyReview."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_prsurvey_review_has_review_burden_field(self):
        """Test that PRSurveyReview model has review_burden field."""
        review = PRSurveyReviewFactory(team=self.team)

        # The field should exist and be accessible
        self.assertTrue(hasattr(review, "review_burden"))

    def test_review_burden_accepts_null(self):
        """Test that review_burden field accepts null values."""
        review = PRSurveyReviewFactory(team=self.team, review_burden=None)

        review.refresh_from_db()
        self.assertIsNone(review.review_burden)

    def test_review_burden_accepts_value_1(self):
        """Test that review_burden accepts value 1 (Very taxing)."""
        review = PRSurveyReviewFactory(team=self.team, review_burden=1)

        review.refresh_from_db()
        self.assertEqual(review.review_burden, 1)

    def test_review_burden_accepts_value_2(self):
        """Test that review_burden accepts value 2 (Taxing)."""
        review = PRSurveyReviewFactory(team=self.team, review_burden=2)

        review.refresh_from_db()
        self.assertEqual(review.review_burden, 2)

    def test_review_burden_accepts_value_3(self):
        """Test that review_burden accepts value 3 (Moderate)."""
        review = PRSurveyReviewFactory(team=self.team, review_burden=3)

        review.refresh_from_db()
        self.assertEqual(review.review_burden, 3)

    def test_review_burden_accepts_value_4(self):
        """Test that review_burden accepts value 4 (Light)."""
        review = PRSurveyReviewFactory(team=self.team, review_burden=4)

        review.refresh_from_db()
        self.assertEqual(review.review_burden, 4)

    def test_review_burden_accepts_value_5(self):
        """Test that review_burden accepts value 5 (Very light)."""
        review = PRSurveyReviewFactory(team=self.team, review_burden=5)

        review.refresh_from_db()
        self.assertEqual(review.review_burden, 5)


class TestFeedbackClarityChoices(TestCase):
    """Tests for FEEDBACK_CLARITY_CHOICES constant."""

    def test_feedback_clarity_choices_exists(self):
        """Test that FEEDBACK_CLARITY_CHOICES constant exists in surveys module."""
        from apps.metrics.models.surveys import FEEDBACK_CLARITY_CHOICES

        self.assertIsNotNone(FEEDBACK_CLARITY_CHOICES)

    def test_feedback_clarity_choices_has_five_options(self):
        """Test that FEEDBACK_CLARITY_CHOICES has exactly 5 options."""
        from apps.metrics.models.surveys import FEEDBACK_CLARITY_CHOICES

        self.assertEqual(len(FEEDBACK_CLARITY_CHOICES), 5)

    def test_feedback_clarity_choices_value_1_is_unclear(self):
        """Test that value 1 is 'Unclear'."""
        from apps.metrics.models.surveys import FEEDBACK_CLARITY_CHOICES

        choices_dict = dict(FEEDBACK_CLARITY_CHOICES)
        self.assertEqual(choices_dict[1], "Unclear")

    def test_feedback_clarity_choices_value_2_is_ok(self):
        """Test that value 2 is 'OK'."""
        from apps.metrics.models.surveys import FEEDBACK_CLARITY_CHOICES

        choices_dict = dict(FEEDBACK_CLARITY_CHOICES)
        self.assertEqual(choices_dict[2], "OK")

    def test_feedback_clarity_choices_value_3_is_clear(self):
        """Test that value 3 is 'Clear'."""
        from apps.metrics.models.surveys import FEEDBACK_CLARITY_CHOICES

        choices_dict = dict(FEEDBACK_CLARITY_CHOICES)
        self.assertEqual(choices_dict[3], "Clear")

    def test_feedback_clarity_choices_value_4_is_very_clear(self):
        """Test that value 4 is 'Very clear'."""
        from apps.metrics.models.surveys import FEEDBACK_CLARITY_CHOICES

        choices_dict = dict(FEEDBACK_CLARITY_CHOICES)
        self.assertEqual(choices_dict[4], "Very clear")

    def test_feedback_clarity_choices_value_5_is_excellent(self):
        """Test that value 5 is 'Excellent'."""
        from apps.metrics.models.surveys import FEEDBACK_CLARITY_CHOICES

        choices_dict = dict(FEEDBACK_CLARITY_CHOICES)
        self.assertEqual(choices_dict[5], "Excellent")


class TestReviewBurdenChoices(TestCase):
    """Tests for REVIEW_BURDEN_CHOICES constant."""

    def test_review_burden_choices_exists(self):
        """Test that REVIEW_BURDEN_CHOICES constant exists in surveys module."""
        from apps.metrics.models.surveys import REVIEW_BURDEN_CHOICES

        self.assertIsNotNone(REVIEW_BURDEN_CHOICES)

    def test_review_burden_choices_has_five_options(self):
        """Test that REVIEW_BURDEN_CHOICES has exactly 5 options."""
        from apps.metrics.models.surveys import REVIEW_BURDEN_CHOICES

        self.assertEqual(len(REVIEW_BURDEN_CHOICES), 5)

    def test_review_burden_choices_value_1_is_very_taxing(self):
        """Test that value 1 is 'Very taxing'."""
        from apps.metrics.models.surveys import REVIEW_BURDEN_CHOICES

        choices_dict = dict(REVIEW_BURDEN_CHOICES)
        self.assertEqual(choices_dict[1], "Very taxing")

    def test_review_burden_choices_value_2_is_taxing(self):
        """Test that value 2 is 'Taxing'."""
        from apps.metrics.models.surveys import REVIEW_BURDEN_CHOICES

        choices_dict = dict(REVIEW_BURDEN_CHOICES)
        self.assertEqual(choices_dict[2], "Taxing")

    def test_review_burden_choices_value_3_is_moderate(self):
        """Test that value 3 is 'Moderate'."""
        from apps.metrics.models.surveys import REVIEW_BURDEN_CHOICES

        choices_dict = dict(REVIEW_BURDEN_CHOICES)
        self.assertEqual(choices_dict[3], "Moderate")

    def test_review_burden_choices_value_4_is_light(self):
        """Test that value 4 is 'Light'."""
        from apps.metrics.models.surveys import REVIEW_BURDEN_CHOICES

        choices_dict = dict(REVIEW_BURDEN_CHOICES)
        self.assertEqual(choices_dict[4], "Light")

    def test_review_burden_choices_value_5_is_very_light(self):
        """Test that value 5 is 'Very light'."""
        from apps.metrics.models.surveys import REVIEW_BURDEN_CHOICES

        choices_dict = dict(REVIEW_BURDEN_CHOICES)
        self.assertEqual(choices_dict[5], "Very light")


class TestShouldShowExtendedSurvey(TestCase):
    """Tests for should_show_extended_survey() utility function."""

    def test_should_show_extended_survey_returns_bool(self):
        """Test that should_show_extended_survey returns a boolean."""
        from apps.metrics.models.surveys import should_show_extended_survey

        result = should_show_extended_survey()

        self.assertIsInstance(result, bool)

    def test_should_show_extended_survey_sampling_distribution(self):
        """Test that should_show_extended_survey returns True approximately 25% of the time.

        Run 1000 iterations and expect 20-30% True (allowing for statistical variance).
        """
        from apps.metrics.models.surveys import should_show_extended_survey

        true_count = sum(1 for _ in range(1000) if should_show_extended_survey())
        percentage = true_count / 1000

        # Expect ~25% True, allow 20-30% range for statistical variance
        self.assertGreaterEqual(percentage, 0.20, f"Expected at least 20% True, got {percentage * 100:.1f}%")
        self.assertLessEqual(percentage, 0.30, f"Expected at most 30% True, got {percentage * 100:.1f}%")
