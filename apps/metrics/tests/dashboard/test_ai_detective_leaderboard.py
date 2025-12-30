"""Tests for get_ai_detective_leaderboard dashboard function."""

from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRSurveyFactory,
    PRSurveyReviewFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services.dashboard_service import get_ai_detective_leaderboard


class TestGetAIDetectiveLeaderboard(TestCase):
    """Tests for get_ai_detective_leaderboard function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.reviewer = TeamMemberFactory(team=self.team, display_name="Alice Reviewer")
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=30)

    def _create_survey_with_review(self, team, reviewer, ai_guess, guess_correct, responded_at=None):
        """Helper to create a survey with a review that has a guess."""
        if responded_at is None:
            responded_at = timezone.now() - timedelta(days=5)

        survey = PRSurveyFactory(team=team)
        return PRSurveyReviewFactory(
            team=team,
            survey=survey,
            reviewer=reviewer,
            ai_guess=ai_guess,
            guess_correct=guess_correct,
            responded_at=responded_at,
        )

    def test_returns_list_of_dicts(self):
        """get_ai_detective_leaderboard returns a list of dicts."""
        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)
        self.assertIsInstance(result, list)

    def test_returns_empty_list_when_no_reviews(self):
        """Returns empty list when no survey reviews exist."""
        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)
        self.assertEqual(result, [])

    def test_includes_required_fields(self):
        """Each entry includes member_name, correct, total, and percentage."""
        self._create_survey_with_review(
            team=self.team,
            reviewer=self.reviewer,
            ai_guess=True,
            guess_correct=True,
        )

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        entry = result[0]
        self.assertIn("member_name", entry)
        self.assertIn("correct", entry)
        self.assertIn("total", entry)
        self.assertIn("percentage", entry)
        self.assertIn("avatar_url", entry)
        self.assertIn("initials", entry)

    def test_counts_correct_guesses(self):
        """Correctly counts the number of correct guesses per reviewer."""
        # Create 2 correct guesses
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["correct"], 2)

    def test_counts_total_guesses(self):
        """Correctly counts total guesses (correct + incorrect) per reviewer."""
        # 2 correct, 1 incorrect
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=False)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["correct"], 2)
        self.assertEqual(result[0]["total"], 3)

    def test_calculates_percentage_correctly(self):
        """Calculates accuracy percentage as (correct / total) * 100."""
        # 2 correct out of 4 = 50%
        for _ in range(2):
            self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)
        for _ in range(2):
            self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=False)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["percentage"], 50.0)

    def test_percentage_has_one_decimal_place(self):
        """Percentage is rounded to one decimal place."""
        # 1 correct out of 3 = 33.33...%
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)
        for _ in range(2):
            self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=False)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        # Should be 33.3 (rounded)
        self.assertEqual(result[0]["percentage"], 33.3)

    def test_shows_member_display_name(self):
        """Shows the reviewer's display name."""
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["member_name"], "Alice Reviewer")

    def test_includes_multiple_reviewers(self):
        """Returns entries for multiple reviewers."""
        reviewer2 = TeamMemberFactory(team=self.team, display_name="Bob Reviewer")

        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)
        self._create_survey_with_review(team=self.team, reviewer=reviewer2, ai_guess=True, guess_correct=True)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 2)
        names = [r["member_name"] for r in result]
        self.assertIn("Alice Reviewer", names)
        self.assertIn("Bob Reviewer", names)

    def test_orders_by_correct_count_descending(self):
        """Results are ordered by correct count (most correct first)."""
        reviewer2 = TeamMemberFactory(team=self.team, display_name="Bob Top Scorer")

        # Alice: 1 correct
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)

        # Bob: 3 correct
        for _ in range(3):
            self._create_survey_with_review(team=self.team, reviewer=reviewer2, ai_guess=True, guess_correct=True)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["member_name"], "Bob Top Scorer")
        self.assertEqual(result[0]["correct"], 3)
        self.assertEqual(result[1]["member_name"], "Alice Reviewer")
        self.assertEqual(result[1]["correct"], 1)

    def test_filters_by_team(self):
        """Only includes reviews from the specified team."""
        other_team = TeamFactory()
        other_reviewer = TeamMemberFactory(team=other_team, display_name="Other Team")

        # Our team review
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)

        # Other team review
        other_survey = PRSurveyFactory(team=other_team)
        PRSurveyReviewFactory(
            team=other_team,
            survey=other_survey,
            reviewer=other_reviewer,
            guess_correct=True,
            responded_at=timezone.now() - timedelta(days=5),
        )

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["member_name"], "Alice Reviewer")

    def test_filters_by_date_range(self):
        """Only includes reviews within the specified date range."""
        in_range_date = timezone.now() - timedelta(days=5)
        out_of_range_date = timezone.now() - timedelta(days=60)

        # In range
        self._create_survey_with_review(
            team=self.team,
            reviewer=self.reviewer,
            ai_guess=True,
            guess_correct=True,
            responded_at=in_range_date,
        )

        # Out of range
        self._create_survey_with_review(
            team=self.team,
            reviewer=self.reviewer,
            ai_guess=True,
            guess_correct=True,
            responded_at=out_of_range_date,
        )

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        # Should only count the in-range review
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["total"], 1)

    def test_excludes_reviews_with_null_guess_correct(self):
        """Excludes reviews where guess_correct is null (no guess made)."""
        # Review with guess
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)

        # Review without guess (guess_correct=None)
        survey = PRSurveyFactory(team=self.team)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            reviewer=self.reviewer,
            guess_correct=None,
            responded_at=timezone.now() - timedelta(days=5),
        )

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["total"], 1)

    def test_includes_avatar_url(self):
        """Each entry includes avatar_url from github_id."""
        reviewer_with_github = TeamMemberFactory(
            team=self.team,
            display_name="Dev With Avatar",
            github_id="12345",
        )

        self._create_survey_with_review(
            team=self.team,
            reviewer=reviewer_with_github,
            ai_guess=True,
            guess_correct=True,
        )

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertIn("avatar_url", result[0])
        self.assertIn("12345", result[0]["avatar_url"])

    def test_includes_initials(self):
        """Each entry includes initials computed from display name."""
        self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertIn("initials", result[0])
        # "Alice Reviewer" should have initials "AR"
        self.assertEqual(result[0]["initials"], "AR")

    def test_handles_100_percent_accuracy(self):
        """Handles reviewer with 100% accuracy."""
        for _ in range(5):
            self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=True)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["percentage"], 100.0)
        self.assertEqual(result[0]["correct"], 5)
        self.assertEqual(result[0]["total"], 5)

    def test_handles_0_percent_accuracy(self):
        """Handles reviewer with 0% accuracy (all wrong guesses)."""
        for _ in range(3):
            self._create_survey_with_review(team=self.team, reviewer=self.reviewer, ai_guess=True, guess_correct=False)

        result = get_ai_detective_leaderboard(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["percentage"], 0.0)
        self.assertEqual(result[0]["correct"], 0)
        self.assertEqual(result[0]["total"], 3)
