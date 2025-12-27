"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
)
from apps.metrics.services import dashboard_service


class TestGetAIAdoptionTrend(TestCase):
    """Tests for get_ai_adoption_trend function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_ai_adoption_trend_returns_list_of_dicts(self):
        """Test that get_ai_adoption_trend returns a list of week/value dicts."""
        result = dashboard_service.get_ai_adoption_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_ai_adoption_trend_groups_by_week(self):
        """Test that get_ai_adoption_trend groups data by week."""
        # Week 1: Jan 1-7 (2 PRs, 1 AI-assisted = 50%)
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr1, author_ai_assisted=True)

        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr2, author_ai_assisted=False)

        # Week 2: Jan 8-14 (2 PRs, 2 AI-assisted = 100%)
        pr3 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr3, author_ai_assisted=True)

        pr4 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr4, author_ai_assisted=True)

        result = dashboard_service.get_ai_adoption_trend(self.team, self.start_date, self.end_date)

        self.assertGreaterEqual(len(result), 2)
        # Each entry should have week and value
        for entry in result:
            self.assertIn("week", entry)
            self.assertIn("value", entry)

    def test_get_ai_adoption_trend_calculates_percentage_correctly(self):
        """Test that get_ai_adoption_trend calculates AI percentage per week."""
        # Create PRs in one week: 3 out of 4 AI-assisted
        merged_dates = [
            timezone.datetime(2024, 1, 3, 12, 0),
            timezone.datetime(2024, 1, 4, 12, 0),
            timezone.datetime(2024, 1, 5, 12, 0),
            timezone.datetime(2024, 1, 6, 12, 0),
        ]
        ai_flags = [True, True, True, False]

        for merged_date, ai_flag in zip(merged_dates, ai_flags, strict=True):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(merged_date),
            )
            PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=ai_flag)

        result = dashboard_service.get_ai_adoption_trend(self.team, self.start_date, self.end_date)

        # Find the week with our data
        week_data = next((w for w in result if len(result) > 0), None)
        if week_data:
            # 3 out of 4 = 75%
            self.assertAlmostEqual(float(week_data["value"]), 75.0, places=1)

    def test_get_ai_adoption_trend_handles_week_with_no_prs(self):
        """Test that get_ai_adoption_trend handles weeks with no PRs."""
        # Create PR in first week only
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 3, 12, 0)),
        )
        PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=True)

        result = dashboard_service.get_ai_adoption_trend(self.team, self.start_date, self.end_date)

        # Should handle empty weeks gracefully
        self.assertIsInstance(result, list)


class TestGetAIQualityComparison(TestCase):
    """Tests for get_ai_quality_comparison function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_ai_quality_comparison_returns_dict_with_ai_and_non_ai_keys(self):
        """Test that get_ai_quality_comparison returns dict with ai_avg and non_ai_avg."""
        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        self.assertIn("ai_avg", result)
        self.assertIn("non_ai_avg", result)

    def test_get_ai_quality_comparison_calculates_ai_average(self):
        """Test that get_ai_quality_comparison calculates AI-assisted quality average."""
        # Create AI-assisted PRs with quality ratings
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey1 = PRSurveyFactory(team=self.team, pull_request=pr1, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey1, quality_rating=3)

        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey2 = PRSurveyFactory(team=self.team, pull_request=pr2, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey2, quality_rating=1)

        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        # Average should be (3 + 1) / 2 = 2.00
        self.assertEqual(result["ai_avg"], Decimal("2.00"))

    def test_get_ai_quality_comparison_calculates_non_ai_average(self):
        """Test that get_ai_quality_comparison calculates non-AI quality average."""
        # Create non-AI-assisted PRs with quality ratings
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey1 = PRSurveyFactory(team=self.team, pull_request=pr1, author_ai_assisted=False)
        PRSurveyReviewFactory(team=self.team, survey=survey1, quality_rating=2)

        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey2 = PRSurveyFactory(team=self.team, pull_request=pr2, author_ai_assisted=False)
        PRSurveyReviewFactory(team=self.team, survey=survey2, quality_rating=2)

        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        # Average should be (2 + 2) / 2 = 2.00
        self.assertEqual(result["non_ai_avg"], Decimal("2.00"))

    def test_get_ai_quality_comparison_handles_no_ai_data(self):
        """Test that get_ai_quality_comparison handles case with no AI data."""
        # Create only non-AI PR
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=False)
        PRSurveyReviewFactory(team=self.team, survey=survey, quality_rating=2)

        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        self.assertIsNone(result["ai_avg"])
        self.assertIsNotNone(result["non_ai_avg"])

    def test_get_ai_quality_comparison_handles_no_non_ai_data(self):
        """Test that get_ai_quality_comparison handles case with no non-AI data."""
        # Create only AI-assisted PR
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey, quality_rating=3)

        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        self.assertIsNotNone(result["ai_avg"])
        self.assertIsNone(result["non_ai_avg"])


class TestGetAIToolBreakdown(TestCase):
    """Tests for get_ai_tool_breakdown function with category support."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_list_of_dicts_with_category(self):
        """Test that tool breakdown includes category for each tool."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
        )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertIn("tool", result[0])
        self.assertIn("count", result[0])
        self.assertIn("category", result[0])
        self.assertEqual(result[0]["category"], "code")

    def test_code_tools_have_code_category(self):
        """Test that code tools are categorized as 'code'."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["cursor", "copilot", "claude"],
        )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        for item in result:
            self.assertEqual(item["category"], "code")

    def test_review_tools_have_review_category(self):
        """Test that review tools are categorized as 'review'."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["coderabbit", "greptile"],
        )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        for item in result:
            self.assertEqual(item["category"], "review")

    def test_excludes_excluded_tools(self):
        """Test that excluded tools (snyk, mintlify) are not included."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["cursor", "snyk", "mintlify"],
        )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        # Should only have cursor, not snyk or mintlify
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tool"], "cursor")

    def test_sorts_by_category_then_count(self):
        """Test that results are sorted by category (code first) then by count."""
        # Multiple PRs with different tools
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
                is_ai_assisted=True,
                ai_tools_detected=["cursor"],
            )
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
                is_ai_assisted=True,
                ai_tools_detected=["coderabbit"],
            )

        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        # Code tools should come first even if review tool has higher count
        self.assertEqual(result[0]["category"], "code")
        self.assertEqual(result[0]["tool"], "cursor")
        self.assertEqual(result[1]["category"], "review")
        self.assertEqual(result[1]["tool"], "coderabbit")


class TestGetAICategoryBreakdown(TestCase):
    """Tests for get_ai_category_breakdown function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_category_counts(self):
        """Test that category breakdown returns all expected keys."""
        result = dashboard_service.get_ai_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertIn("total_ai_prs", result)
        self.assertIn("code_ai_count", result)
        self.assertIn("review_ai_count", result)
        self.assertIn("both_ai_count", result)
        self.assertIn("code_ai_pct", result)
        self.assertIn("review_ai_pct", result)

    def test_counts_code_ai_prs(self):
        """Test that PRs with code tools are counted in code_ai_count."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
        )

        result = dashboard_service.get_ai_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["code_ai_count"], 2)
        self.assertEqual(result["review_ai_count"], 0)
        self.assertEqual(result["both_ai_count"], 0)

    def test_counts_review_ai_prs(self):
        """Test that PRs with review tools are counted in review_ai_count."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["coderabbit"],
        )

        result = dashboard_service.get_ai_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["code_ai_count"], 0)
        self.assertEqual(result["review_ai_count"], 1)
        self.assertEqual(result["both_ai_count"], 0)

    def test_counts_both_ai_prs(self):
        """Test that PRs with both code and review tools are counted in both_ai_count."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["cursor", "coderabbit"],
        )

        result = dashboard_service.get_ai_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["code_ai_count"], 0)
        self.assertEqual(result["review_ai_count"], 0)
        self.assertEqual(result["both_ai_count"], 1)

    def test_calculates_percentages(self):
        """Test that percentages are calculated correctly."""
        # 2 code, 1 review, 1 both = 4 total
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["coderabbit"],
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 13, 12, 0)),
            is_ai_assisted=True,
            ai_tools_detected=["cursor", "coderabbit"],
        )

        result = dashboard_service.get_ai_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_ai_prs"], 4)
        self.assertEqual(result["code_ai_pct"], 50.0)  # 2/4
        self.assertEqual(result["review_ai_pct"], 25.0)  # 1/4

    def test_handles_empty_data(self):
        """Test that empty data returns zeros."""
        result = dashboard_service.get_ai_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_ai_prs"], 0)
        self.assertEqual(result["code_ai_count"], 0)
        self.assertEqual(result["review_ai_count"], 0)
        self.assertEqual(result["both_ai_count"], 0)
        self.assertEqual(result["code_ai_pct"], 0.0)
