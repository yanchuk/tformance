"""Tests for get_ai_bot_review_stats dashboard function."""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services.dashboard_service import get_ai_bot_review_stats


class TestGetAIBotReviewStats(TestCase):
    """Tests for get_ai_bot_review_stats function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.reviewer = TeamMemberFactory(team=self.team)
        self.pr = PullRequestFactory(team=self.team, author=self.member, state="merged")
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=30)

    def _create_review(self, is_ai_review=False, ai_reviewer_type="", submitted_at=None):
        """Helper to create a review."""
        if submitted_at is None:
            submitted_at = timezone.now() - timedelta(days=5)

        return PRReviewFactory(
            team=self.team,
            pull_request=self.pr,
            reviewer=self.reviewer,
            is_ai_review=is_ai_review,
            ai_reviewer_type=ai_reviewer_type,
            submitted_at=submitted_at,
        )

    def test_returns_dict_with_required_keys(self):
        """get_ai_bot_review_stats returns dict with required keys."""
        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("total_reviews", result)
        self.assertIn("ai_reviews", result)
        self.assertIn("ai_review_pct", result)
        self.assertIn("by_bot", result)

    def test_counts_total_reviews(self):
        """Correctly counts total reviews in date range."""
        # Create 3 reviews
        for _ in range(3):
            self._create_review()

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_reviews"], 3)

    def test_counts_ai_reviews(self):
        """Correctly counts AI reviews."""
        # 2 AI reviews, 1 human review
        self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit")
        self._create_review(is_ai_review=True, ai_reviewer_type="copilot")
        self._create_review(is_ai_review=False)

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_reviews"], 2)

    def test_calculates_ai_review_percentage(self):
        """Calculates AI review percentage correctly."""
        # 1 AI review, 3 human reviews = 25% AI
        self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit")
        for _ in range(3):
            self._create_review(is_ai_review=False)

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_review_pct"], Decimal("25.00"))

    def test_ai_review_pct_is_decimal(self):
        """ai_review_pct is a Decimal type."""
        self._create_review()

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result["ai_review_pct"], Decimal)

    def test_by_bot_is_list(self):
        """by_bot is a list of bot breakdown entries."""
        self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit")

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result["by_bot"], list)

    def test_by_bot_entry_has_bot_type_and_count(self):
        """Each by_bot entry has bot_type and count keys."""
        self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit")

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result["by_bot"]), 1)
        self.assertIn("bot_type", result["by_bot"][0])
        self.assertIn("count", result["by_bot"][0])

    def test_groups_by_bot_type(self):
        """Groups AI reviews by bot type."""
        # 2 coderabbit, 3 copilot
        for _ in range(2):
            self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit")
        for _ in range(3):
            self._create_review(is_ai_review=True, ai_reviewer_type="copilot")

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result["by_bot"]), 2)
        bot_types = {b["bot_type"]: b["count"] for b in result["by_bot"]}
        self.assertEqual(bot_types["coderabbit"], 2)
        self.assertEqual(bot_types["copilot"], 3)

    def test_by_bot_ordered_by_count_descending(self):
        """by_bot is ordered by count descending."""
        # 1 coderabbit, 3 copilot, 2 dependabot
        self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit")
        for _ in range(3):
            self._create_review(is_ai_review=True, ai_reviewer_type="copilot")
        for _ in range(2):
            self._create_review(is_ai_review=True, ai_reviewer_type="dependabot")

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        # Should be ordered: copilot (3), dependabot (2), coderabbit (1)
        self.assertEqual(result["by_bot"][0]["bot_type"], "copilot")
        self.assertEqual(result["by_bot"][0]["count"], 3)
        self.assertEqual(result["by_bot"][1]["bot_type"], "dependabot")
        self.assertEqual(result["by_bot"][1]["count"], 2)
        self.assertEqual(result["by_bot"][2]["bot_type"], "coderabbit")
        self.assertEqual(result["by_bot"][2]["count"], 1)

    def test_filters_by_date_range(self):
        """Only includes reviews within the specified date range."""
        in_range_date = timezone.now() - timedelta(days=5)
        out_of_range_date = timezone.now() - timedelta(days=60)

        # In range review
        self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit", submitted_at=in_range_date)

        # Out of range review
        self._create_review(is_ai_review=True, ai_reviewer_type="copilot", submitted_at=out_of_range_date)

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_reviews"], 1)
        self.assertEqual(result["ai_reviews"], 1)

    def test_filters_by_team(self):
        """Only includes reviews from the specified team."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        other_pr = PullRequestFactory(team=other_team, author=other_member)

        # Our team review
        self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit")

        # Other team review
        PRReviewFactory(
            team=other_team,
            pull_request=other_pr,
            reviewer=other_member,
            is_ai_review=True,
            ai_reviewer_type="copilot",
            submitted_at=timezone.now() - timedelta(days=5),
        )

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_reviews"], 1)
        self.assertEqual(result["ai_reviews"], 1)
        self.assertEqual(result["by_bot"][0]["bot_type"], "coderabbit")

    def test_returns_zero_when_no_reviews(self):
        """Returns zero values when no reviews exist."""
        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_reviews"], 0)
        self.assertEqual(result["ai_reviews"], 0)
        self.assertEqual(result["ai_review_pct"], Decimal("0.00"))
        self.assertEqual(result["by_bot"], [])

    def test_handles_all_ai_reviews(self):
        """Handles case where all reviews are from AI bots."""
        for _ in range(5):
            self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit")

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_review_pct"], Decimal("100.00"))

    def test_handles_no_ai_reviews(self):
        """Handles case where no reviews are from AI bots."""
        for _ in range(3):
            self._create_review(is_ai_review=False)

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_reviews"], 0)
        self.assertEqual(result["ai_review_pct"], Decimal("0.00"))
        self.assertEqual(result["by_bot"], [])

    def test_percentage_precision_is_two_decimal_places(self):
        """ai_review_pct has two decimal places precision."""
        # 1 AI review out of 3 = 33.33%
        self._create_review(is_ai_review=True, ai_reviewer_type="coderabbit")
        self._create_review(is_ai_review=False)
        self._create_review(is_ai_review=False)

        result = get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        # Should be 33.33 rounded to 2 decimal places
        self.assertEqual(result["ai_review_pct"], Decimal("33.33"))
