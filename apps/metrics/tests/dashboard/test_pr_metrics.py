"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetRecentPrs(TestCase):
    """Tests for get_recent_prs function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_recent_prs_returns_list_of_dicts(self):
        """Test that get_recent_prs returns a list of PR dicts."""
        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_recent_prs_includes_required_fields(self):
        """Test that get_recent_prs includes all required fields."""
        author = TeamMemberFactory(team=self.team, display_name="Alice")
        pr = PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Add feature X",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey, quality_rating=3)

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        pr_data = result[0]

        self.assertIn("title", pr_data)
        self.assertIn("author", pr_data)
        self.assertIn("merged_at", pr_data)
        self.assertIn("ai_assisted", pr_data)
        self.assertIn("avg_quality", pr_data)
        self.assertIn("url", pr_data)

    def test_get_recent_prs_returns_correct_data(self):
        """Test that get_recent_prs returns correct PR data."""
        author = TeamMemberFactory(team=self.team, display_name="Bob")
        reviewer1 = TeamMemberFactory(team=self.team, display_name="Reviewer1")
        reviewer2 = TeamMemberFactory(team=self.team, display_name="Reviewer2")
        merged_time = timezone.make_aware(timezone.datetime(2024, 1, 15, 14, 30))
        pr = PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Fix bug Y",
            merged_at=merged_time,
            github_repo="org/repo",
            github_pr_id=123,
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=True)
        PRSurveyReviewFactory(team=self.team, survey=survey, reviewer=reviewer1, quality_rating=2)
        PRSurveyReviewFactory(team=self.team, survey=survey, reviewer=reviewer2, quality_rating=3)

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        pr_data = result[0]
        self.assertEqual(pr_data["title"], "Fix bug Y")
        self.assertEqual(pr_data["author"], "Bob")
        self.assertEqual(pr_data["merged_at"], merged_time)
        self.assertTrue(pr_data["ai_assisted"])
        self.assertEqual(pr_data["avg_quality"], 2.5)  # (2 + 3) / 2
        self.assertEqual(pr_data["url"], "https://github.com/org/repo/pull/123")

    def test_get_recent_prs_orders_by_merged_at_descending(self):
        """Test that get_recent_prs orders by merged_at descending (most recent first)."""
        author = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="First PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Second PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Third PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["title"], "Second PR")  # Most recent
        self.assertEqual(result[1]["title"], "Third PR")
        self.assertEqual(result[2]["title"], "First PR")

    def test_get_recent_prs_limits_results(self):
        """Test that get_recent_prs limits results to specified count."""
        author = TeamMemberFactory(team=self.team)
        for i in range(15):
            PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                title=f"PR {i}",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, i + 1, 12, 0)),
            )

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date, limit=10)

        self.assertEqual(len(result), 10)

    def test_get_recent_prs_handles_pr_without_survey(self):
        """Test that get_recent_prs handles PRs without surveys."""
        author = TeamMemberFactory(team=self.team, display_name="Charlie")
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="No Survey PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        pr_data = result[0]
        self.assertIsNone(pr_data["ai_assisted"])
        self.assertIsNone(pr_data["avg_quality"])

    def test_get_recent_prs_handles_no_data(self):
        """Test that get_recent_prs handles empty dataset."""
        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result, [])


class TestGetRevertHotfixStats(TestCase):
    """Tests for get_revert_hotfix_stats function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_revert_hotfix_stats_returns_dict_with_required_keys(self):
        """Test that get_revert_hotfix_stats returns dict with all required keys."""
        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertIn("total_prs", result)
        self.assertIn("revert_count", result)
        self.assertIn("hotfix_count", result)
        self.assertIn("revert_pct", result)
        self.assertIn("hotfix_pct", result)

    def test_get_revert_hotfix_stats_counts_total_merged_prs(self):
        """Test that get_revert_hotfix_stats counts total merged PRs in date range."""
        # Create 5 merged PRs
        for i in range(5):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        # Create non-merged PRs (should be excluded)
        PullRequestFactory(team=self.team, state="open", merged_at=None)
        PullRequestFactory(team=self.team, state="closed", merged_at=None)

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 5)

    def test_get_revert_hotfix_stats_counts_reverts(self):
        """Test that get_revert_hotfix_stats counts PRs where is_revert=True."""
        # Create 3 revert PRs
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=True,
                is_hotfix=False,
            )

        # Create 2 non-revert PRs
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["revert_count"], 3)

    def test_get_revert_hotfix_stats_counts_hotfixes(self):
        """Test that get_revert_hotfix_stats counts PRs where is_hotfix=True."""
        # Create 4 hotfix PRs
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=True,
            )

        # Create 1 non-hotfix PR
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=False,
            is_hotfix=False,
        )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["hotfix_count"], 4)

    def test_get_revert_hotfix_stats_calculates_revert_percentage(self):
        """Test that get_revert_hotfix_stats calculates revert percentage correctly."""
        # Create 2 reverts out of 10 total PRs = 20%
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5 + i, 12, 0)),
                is_revert=True,
                is_hotfix=False,
            )

        for i in range(8):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 10)
        self.assertEqual(result["revert_count"], 2)
        self.assertAlmostEqual(float(result["revert_pct"]), 20.0, places=2)

    def test_get_revert_hotfix_stats_calculates_hotfix_percentage(self):
        """Test that get_revert_hotfix_stats calculates hotfix percentage correctly."""
        # Create 3 hotfixes out of 12 total PRs = 25%
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5 + i, 12, 0)),
                is_revert=False,
                is_hotfix=True,
            )

        for i in range(9):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 12)
        self.assertEqual(result["hotfix_count"], 3)
        self.assertAlmostEqual(float(result["hotfix_pct"]), 25.0, places=2)

    def test_get_revert_hotfix_stats_handles_pr_with_both_flags(self):
        """Test that get_revert_hotfix_stats counts a PR with both is_revert and is_hotfix."""
        # Create 1 PR with both flags
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_revert=True,
            is_hotfix=True,
        )

        # Create 4 normal PRs
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 5)
        self.assertEqual(result["revert_count"], 1)
        self.assertEqual(result["hotfix_count"], 1)
        self.assertAlmostEqual(float(result["revert_pct"]), 20.0, places=2)
        self.assertAlmostEqual(float(result["hotfix_pct"]), 20.0, places=2)

    def test_get_revert_hotfix_stats_handles_no_prs(self):
        """Test that get_revert_hotfix_stats handles case with no PRs."""
        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 0)
        self.assertEqual(result["revert_count"], 0)
        self.assertEqual(result["hotfix_count"], 0)
        self.assertEqual(result["revert_pct"], 0.0)
        self.assertEqual(result["hotfix_pct"], 0.0)

    def test_get_revert_hotfix_stats_handles_zero_percentage(self):
        """Test that get_revert_hotfix_stats returns 0% when no reverts or hotfixes exist."""
        # Create 5 normal PRs with no reverts or hotfixes
        for i in range(5):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 5)
        self.assertEqual(result["revert_count"], 0)
        self.assertEqual(result["hotfix_count"], 0)
        self.assertEqual(result["revert_pct"], 0.0)
        self.assertEqual(result["hotfix_pct"], 0.0)

    def test_get_revert_hotfix_stats_filters_by_date_range(self):
        """Test that get_revert_hotfix_stats only includes PRs within date range."""
        # In range revert
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        # Before start date (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        # After end date (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 1)
        self.assertEqual(result["revert_count"], 1)

    def test_get_revert_hotfix_stats_filters_by_team(self):
        """Test that get_revert_hotfix_stats only includes PRs from specified team."""
        other_team = TeamFactory()

        # Target team PRs
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        # Other team PRs (should be excluded)
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=True,
        )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 1)
        self.assertEqual(result["revert_count"], 1)
        self.assertEqual(result["hotfix_count"], 0)

    def test_get_revert_hotfix_stats_percentage_has_correct_precision(self):
        """Test that get_revert_hotfix_stats calculates percentages with correct precision."""
        # Create 1 revert out of 3 total PRs = 33.33%
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        for i in range(2):
            PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
            )

        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        # Check percentage is a float
        self.assertIsInstance(result["revert_pct"], float)
        # Check it's in range 0.0 to 100.0
        self.assertGreaterEqual(result["revert_pct"], 0.0)
        self.assertLessEqual(result["revert_pct"], 100.0)
        # Check it's approximately 33.33%
        self.assertAlmostEqual(result["revert_pct"], 33.33, places=2)


class TestGetPrSizeDistribution(TestCase):
    """Tests for get_pr_size_distribution function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_pr_size_distribution_returns_list_of_dicts(self):
        """Test that get_pr_size_distribution returns a list of category dicts."""
        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_pr_size_distribution_returns_all_five_categories(self):
        """Test that get_pr_size_distribution always returns all 5 categories."""
        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 5)
        categories = [item["category"] for item in result]
        self.assertEqual(categories, ["XS", "S", "M", "L", "XL"])

    def test_get_pr_size_distribution_categorizes_xs_size(self):
        """Test that PRs with 1-10 lines are categorized as XS."""
        # XS: 1-10 lines (additions + deletions)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=10,
            deletions=0,  # Total: 10 lines (boundary)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xs_data = next((item for item in result if item["category"] == "XS"), None)
        self.assertIsNotNone(xs_data)
        self.assertEqual(xs_data["count"], 2)

    def test_get_pr_size_distribution_categorizes_s_size(self):
        """Test that PRs with 11-50 lines are categorized as S."""
        # S: 11-50 lines
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=11,
            deletions=0,  # Total: 11 lines (lower boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=30,
            deletions=20,  # Total: 50 lines (upper boundary)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        s_data = next((item for item in result if item["category"] == "S"), None)
        self.assertIsNotNone(s_data)
        self.assertEqual(s_data["count"], 2)

    def test_get_pr_size_distribution_categorizes_m_size(self):
        """Test that PRs with 51-200 lines are categorized as M."""
        # M: 51-200 lines
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=51,
            deletions=0,  # Total: 51 lines (lower boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=100,
            deletions=100,  # Total: 200 lines (upper boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=75,
            deletions=50,  # Total: 125 lines
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        m_data = next((item for item in result if item["category"] == "M"), None)
        self.assertIsNotNone(m_data)
        self.assertEqual(m_data["count"], 3)

    def test_get_pr_size_distribution_categorizes_l_size(self):
        """Test that PRs with 201-500 lines are categorized as L."""
        # L: 201-500 lines
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=201,
            deletions=0,  # Total: 201 lines (lower boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=250,
            deletions=250,  # Total: 500 lines (upper boundary)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        l_data = next((item for item in result if item["category"] == "L"), None)
        self.assertIsNotNone(l_data)
        self.assertEqual(l_data["count"], 2)

    def test_get_pr_size_distribution_categorizes_xl_size(self):
        """Test that PRs with 500+ lines are categorized as XL."""
        # XL: 500+ lines
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=501,
            deletions=0,  # Total: 501 lines (just above boundary)
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=1000,
            deletions=500,  # Total: 1500 lines
        )
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=10000,
            deletions=5000,  # Total: 15000 lines
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xl_data = next((item for item in result if item["category"] == "XL"), None)
        self.assertIsNotNone(xl_data)
        self.assertEqual(xl_data["count"], 3)

    def test_get_pr_size_distribution_returns_zero_counts_for_empty_categories(self):
        """Test that categories with no PRs return count of 0."""
        # Create only one XL PR
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=600,
            deletions=0,  # Total: 600 lines (XL)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        # All categories should be present
        self.assertEqual(len(result), 5)

        # XL should have count of 1
        xl_data = next((item for item in result if item["category"] == "XL"), None)
        self.assertEqual(xl_data["count"], 1)

        # All others should have count of 0
        for category in ["XS", "S", "M", "L"]:
            category_data = next((item for item in result if item["category"] == category), None)
            self.assertIsNotNone(category_data)
            self.assertEqual(category_data["count"], 0)

    def test_get_pr_size_distribution_only_includes_merged_prs(self):
        """Test that only merged PRs are included in distribution."""
        # Merged PR (should be counted)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # Open PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="open",
            merged_at=None,
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # Closed PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="closed",
            merged_at=None,
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xs_data = next((item for item in result if item["category"] == "XS"), None)
        self.assertEqual(xs_data["count"], 1)

    def test_get_pr_size_distribution_filters_by_date_range(self):
        """Test that only PRs merged within date range are included."""
        # In range
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # Before start date (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # After end date (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xs_data = next((item for item in result if item["category"] == "XS"), None)
        self.assertEqual(xs_data["count"], 1)

    def test_get_pr_size_distribution_filters_by_team(self):
        """Test that only PRs from the specified team are included."""
        other_team = TeamFactory()

        # Target team PR
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        # Other team PR (should be excluded)
        PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=5,
            deletions=3,  # Total: 8 lines (XS)
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        xs_data = next((item for item in result if item["category"] == "XS"), None)
        self.assertEqual(xs_data["count"], 1)

    def test_get_pr_size_distribution_handles_no_prs(self):
        """Test that all categories return 0 count when there are no PRs."""
        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 5)
        for item in result:
            self.assertEqual(item["count"], 0)

    def test_get_pr_size_distribution_has_correct_dict_structure(self):
        """Test that each item in result has correct keys: category and count."""
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=5,
            deletions=3,
        )

        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        for item in result:
            self.assertIn("category", item)
            self.assertIn("count", item)
            self.assertEqual(len(item), 2)  # No extra keys


class TestGetUnlinkedPrs(TestCase):
    """Tests for get_unlinked_prs function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_unlinked_prs_returns_list_of_dicts(self):
        """Test that get_unlinked_prs returns a list of PR dicts."""
        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_unlinked_prs_includes_required_fields(self):
        """Test that get_unlinked_prs includes all required fields."""
        author = TeamMemberFactory(team=self.team, display_name="Alice")
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Add feature X",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
            github_repo="org/repo",
            github_pr_id=123,
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        pr_data = result[0]

        self.assertIn("title", pr_data)
        self.assertIn("author", pr_data)
        self.assertIn("merged_at", pr_data)
        self.assertIn("url", pr_data)
        self.assertEqual(len(pr_data), 4)  # Only these 4 fields

    def test_get_unlinked_prs_returns_correct_data(self):
        """Test that get_unlinked_prs returns correct PR data."""
        author = TeamMemberFactory(team=self.team, display_name="Bob")
        merged_time = timezone.make_aware(timezone.datetime(2024, 1, 15, 14, 30))
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Fix bug Y",
            merged_at=merged_time,
            jira_key="",
            github_repo="org/repo",
            github_pr_id=456,
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        pr_data = result[0]
        self.assertEqual(pr_data["title"], "Fix bug Y")
        self.assertEqual(pr_data["author"], "Bob")
        self.assertEqual(pr_data["merged_at"], merged_time)
        self.assertEqual(pr_data["url"], "https://github.com/org/repo/pull/456")

    def test_get_unlinked_prs_only_includes_prs_with_empty_jira_key(self):
        """Test that get_unlinked_prs only includes PRs where jira_key is empty or None."""
        author = TeamMemberFactory(team=self.team)

        # Unlinked PR with empty string
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Unlinked PR 1",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
        )

        # Linked PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Linked PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            jira_key="PROJ-123",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Unlinked PR 1")

    def test_get_unlinked_prs_only_includes_merged_prs(self):
        """Test that get_unlinked_prs only includes merged PRs."""
        author = TeamMemberFactory(team=self.team)

        # Merged PR (should be included)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Merged PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
        )

        # Open PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="open",
            title="Open PR",
            merged_at=None,
            jira_key="",
        )

        # Closed PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="closed",
            title="Closed PR",
            merged_at=None,
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Merged PR")

    def test_get_unlinked_prs_orders_by_merged_at_descending(self):
        """Test that get_unlinked_prs orders by merged_at descending (most recent first)."""
        author = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="First PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            jira_key="",
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Second PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="",
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Third PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["title"], "Second PR")  # Most recent
        self.assertEqual(result[1]["title"], "Third PR")
        self.assertEqual(result[2]["title"], "First PR")

    def test_get_unlinked_prs_respects_limit_parameter(self):
        """Test that get_unlinked_prs limits results to specified count."""
        author = TeamMemberFactory(team=self.team)
        for i in range(15):
            PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                title=f"PR {i}",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, i + 1, 12, 0)),
                jira_key="",
            )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date, limit=5)

        self.assertEqual(len(result), 5)

    def test_get_unlinked_prs_defaults_to_limit_10(self):
        """Test that get_unlinked_prs defaults to limit=10 when not specified."""
        author = TeamMemberFactory(team=self.team)
        for i in range(20):
            PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                title=f"PR {i}",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, i + 1, 12, 0)),
                jira_key="",
            )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 10)

    def test_get_unlinked_prs_filters_by_date_range(self):
        """Test that get_unlinked_prs only includes PRs within date range."""
        author = TeamMemberFactory(team=self.team)

        # In range
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="In Range PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="",
        )

        # Before start date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Before Start PR",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
            jira_key="",
        )

        # After end date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="After End PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "In Range PR")

    def test_get_unlinked_prs_filters_by_team(self):
        """Test that get_unlinked_prs only includes PRs from specified team."""
        other_team = TeamFactory()

        # Target team PR
        author1 = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=author1,
            state="merged",
            title="Target Team PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="",
        )

        # Other team PR (should be excluded)
        author2 = TeamMemberFactory(team=other_team)
        PullRequestFactory(
            team=other_team,
            author=author2,
            state="merged",
            title="Other Team PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Target Team PR")

    def test_get_unlinked_prs_handles_no_unlinked_prs(self):
        """Test that get_unlinked_prs handles case with no unlinked PRs."""
        author = TeamMemberFactory(team=self.team)

        # All PRs have Jira keys
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Linked PR 1",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="PROJ-123",
        )
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Linked PR 2",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            jira_key="PROJ-456",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result, [])

    def test_get_unlinked_prs_constructs_github_url_correctly(self):
        """Test that get_unlinked_prs constructs GitHub URL from repo and PR ID."""
        author = TeamMemberFactory(team=self.team)
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Test PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
            github_repo="my-org/my-repo",
            github_pr_id=789,
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["url"], "https://github.com/my-org/my-repo/pull/789")

    def test_get_unlinked_prs_handles_author_with_no_display_name(self):
        """Test that get_unlinked_prs handles PRs with authors who have display names."""
        author = TeamMemberFactory(team=self.team, display_name="Charlie Brown")
        PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            title="Test PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            jira_key="",
        )

        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result[0]["author"], "Charlie Brown")
