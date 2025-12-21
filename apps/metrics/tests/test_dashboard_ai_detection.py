"""Tests for AI Detection Dashboard Service functions.

These functions aggregate AI detection data from the new model fields
(is_ai_assisted, ai_tools_detected, is_ai_review, ai_reviewer_type)
that are populated by the ai_detector service during seeding.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetAIDetectedMetrics(TestCase):
    """Tests for get_ai_detected_metrics function - AI detection from PR content."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_dict_with_required_keys(self):
        """Test that get_ai_detected_metrics returns a dict with all required keys."""
        result = dashboard_service.get_ai_detected_metrics(self.team, self.start_date, self.end_date)

        self.assertIn("total_prs", result)
        self.assertIn("ai_assisted_prs", result)
        self.assertIn("ai_assisted_pct", result)

    def test_counts_ai_assisted_prs(self):
        """Test that get_ai_detected_metrics counts AI-assisted PRs correctly."""
        # Create AI-assisted PRs
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["claude_code"],
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
        )

        # Create non-AI PR
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            is_ai_assisted=False,
            ai_tools_detected=[],
        )

        result = dashboard_service.get_ai_detected_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 3)
        self.assertEqual(result["ai_assisted_prs"], 2)
        # 2/3 = 66.67%
        self.assertEqual(result["ai_assisted_pct"], Decimal("66.67"))

    def test_filters_by_team(self):
        """Test that get_ai_detected_metrics filters by team."""
        # PR for our team
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
        )

        # PR for other team
        other_team = TeamFactory()
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
        )

        result = dashboard_service.get_ai_detected_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 1)
        self.assertEqual(result["ai_assisted_prs"], 1)

    def test_filters_by_date_range(self):
        """Test that get_ai_detected_metrics filters by date range."""
        # PR in range
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
        )

        # PR outside range
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
            is_ai_assisted=True,
        )

        result = dashboard_service.get_ai_detected_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 1)

    def test_returns_zero_pct_when_no_prs(self):
        """Test that get_ai_detected_metrics returns 0% when no PRs."""
        result = dashboard_service.get_ai_detected_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 0)
        self.assertEqual(result["ai_assisted_prs"], 0)
        self.assertEqual(result["ai_assisted_pct"], Decimal("0.00"))


class TestGetAIToolBreakdown(TestCase):
    """Tests for get_ai_tool_breakdown function - AI tools detected in PRs."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_list_of_tool_counts(self):
        """Test that get_ai_tool_breakdown returns a list of tool counts."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["claude_code"],
        )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn("tool", result[0])
        self.assertIn("count", result[0])

    def test_counts_each_tool_correctly(self):
        """Test that get_ai_tool_breakdown counts each tool correctly."""
        # 2 PRs with claude_code
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["claude_code"],
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["claude_code", "copilot"],
        )
        # 1 PR with copilot only
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
        )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        # Convert to dict for easier assertions
        counts_by_tool = {r["tool"]: r["count"] for r in result}

        self.assertEqual(counts_by_tool.get("claude_code"), 2)
        self.assertEqual(counts_by_tool.get("copilot"), 2)

    def test_returns_empty_list_when_no_ai_prs(self):
        """Test that get_ai_tool_breakdown returns empty list when no AI PRs."""
        # Create non-AI PR
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=False,
            ai_tools_detected=[],
        )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result, [])

    def test_filters_by_team(self):
        """Test that get_ai_tool_breakdown filters by team."""
        # PR for our team
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["claude_code"],
        )

        # PR for other team
        other_team = TeamFactory()
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
        )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        counts_by_tool = {r["tool"]: r["count"] for r in result}
        self.assertEqual(counts_by_tool.get("claude_code"), 1)
        self.assertIsNone(counts_by_tool.get("copilot"))

    def test_sorts_by_count_descending(self):
        """Test that get_ai_tool_breakdown sorts by count descending."""
        # Create PRs with different tools
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
                is_ai_assisted=True,
                ai_tools_detected=["claude_code"],
            )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
        )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["tool"], "claude_code")
        self.assertEqual(result[0]["count"], 3)


class TestGetAIBotReviewStats(TestCase):
    """Tests for get_ai_bot_review_stats function - AI bot reviewer statistics."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_dict_with_required_keys(self):
        """Test that get_ai_bot_review_stats returns a dict with required keys."""
        result = dashboard_service.get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertIn("total_reviews", result)
        self.assertIn("ai_reviews", result)
        self.assertIn("ai_review_pct", result)
        self.assertIn("by_bot", result)

    def test_counts_ai_reviews(self):
        """Test that get_ai_bot_review_stats counts AI reviews correctly."""
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # Create AI reviews
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            is_ai_review=True,
            ai_reviewer_type="coderabbit",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            is_ai_review=True,
            ai_reviewer_type="copilot",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 11, 0)),
        )

        # Create human review
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            is_ai_review=False,
            ai_reviewer_type="",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_reviews"], 3)
        self.assertEqual(result["ai_reviews"], 2)
        # 2/3 = 66.67%
        self.assertEqual(result["ai_review_pct"], Decimal("66.67"))

    def test_breaks_down_by_bot_type(self):
        """Test that get_ai_bot_review_stats breaks down by bot type."""
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # 2 coderabbit reviews
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            is_ai_review=True,
            ai_reviewer_type="coderabbit",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            is_ai_review=True,
            ai_reviewer_type="coderabbit",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
        )

        # 1 copilot review
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            is_ai_review=True,
            ai_reviewer_type="copilot",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 10, 0)),
        )

        result = dashboard_service.get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        by_bot = {r["bot_type"]: r["count"] for r in result["by_bot"]}
        self.assertEqual(by_bot.get("coderabbit"), 2)
        self.assertEqual(by_bot.get("copilot"), 1)

    def test_returns_zero_pct_when_no_reviews(self):
        """Test that get_ai_bot_review_stats returns 0% when no reviews."""
        result = dashboard_service.get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_reviews"], 0)
        self.assertEqual(result["ai_reviews"], 0)
        self.assertEqual(result["ai_review_pct"], Decimal("0.00"))
        self.assertEqual(result["by_bot"], [])

    def test_filters_by_team(self):
        """Test that get_ai_bot_review_stats filters by team."""
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # Review for our team
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            is_ai_review=True,
            ai_reviewer_type="coderabbit",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
        )

        # Review for other team
        other_team = TeamFactory()
        other_pr = PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRReviewFactory(
            team=other_team,
            pull_request=other_pr,
            is_ai_review=True,
            ai_reviewer_type="copilot",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
        )

        result = dashboard_service.get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_reviews"], 1)
        self.assertEqual(result["ai_reviews"], 1)

    def test_filters_by_date_range(self):
        """Test that get_ai_bot_review_stats filters by date range."""
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        # Review in range
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            is_ai_review=True,
            ai_reviewer_type="coderabbit",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
        )

        # Review outside range
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            is_ai_review=True,
            ai_reviewer_type="copilot",
            submitted_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 10, 0)),
        )

        result = dashboard_service.get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_reviews"], 1)
        self.assertEqual(result["ai_reviews"], 1)
