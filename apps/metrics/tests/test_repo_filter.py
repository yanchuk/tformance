"""Tests for repository filtering in dashboard service.

TDD Test Suite for Repository Selector Feature.

This module tests that dashboard_service functions correctly filter
data by repository when the `repo` parameter is provided.

Test Strategy:
- RepoFilterTestCase: Base class with multi-repo test data
- Each service function gets tests for:
  1. Returns all data when repo=None (backward compatible)
  2. Filters correctly when repo is specified
  3. Returns empty/zero when repo doesn't exist
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import UserFactory
from apps.metrics.factories import (
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.models import PullRequest
from apps.metrics.services import dashboard_service
from apps.teams.roles import ROLE_ADMIN


class RepoFilterTestCase(TestCase):
    """Base test case with multi-repo test data.

    Sets up a team with PRs distributed across 3 repositories:
    - acme/frontend: 2 PRs (1 AI-assisted)
    - acme/backend: 2 PRs (1 AI-assisted)
    - acme/mobile: 1 PR (not AI-assisted)

    All PRs are merged with realistic cycle times for trend testing.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data once for all test methods."""
        cls.team = TeamFactory()
        cls.user = UserFactory()
        cls.team.members.add(cls.user, through_defaults={"role": ROLE_ADMIN})

        # Create team members
        cls.member1 = TeamMemberFactory(team=cls.team, display_name="Alice Dev")
        cls.member2 = TeamMemberFactory(team=cls.team, display_name="Bob Dev")

        # Date range for tests
        cls.end_date = date.today()
        cls.start_date = cls.end_date - timedelta(days=30)

        # Create PRs in different repositories with varied attributes
        # Frontend repo - 2 PRs
        cls.frontend_pr1 = PullRequestFactory(
            team=cls.team,
            github_repo="acme/frontend",
            author=cls.member1,
            state="merged",
            pr_created_at=timezone.now() - timedelta(days=10),
            merged_at=timezone.now() - timedelta(days=9),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
            additions=100,
            deletions=20,
        )
        cls.frontend_pr2 = PullRequestFactory(
            team=cls.team,
            github_repo="acme/frontend",
            author=cls.member2,
            state="merged",
            pr_created_at=timezone.now() - timedelta(days=5),
            merged_at=timezone.now() - timedelta(days=4),
            cycle_time_hours=Decimal("20.0"),
            review_time_hours=Decimal("3.0"),
            is_ai_assisted=False,
            additions=50,
            deletions=10,
        )

        # Backend repo - 2 PRs
        cls.backend_pr1 = PullRequestFactory(
            team=cls.team,
            github_repo="acme/backend",
            author=cls.member1,
            state="merged",
            pr_created_at=timezone.now() - timedelta(days=8),
            merged_at=timezone.now() - timedelta(days=6),
            cycle_time_hours=Decimal("48.0"),
            review_time_hours=Decimal("8.0"),
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
            additions=200,
            deletions=50,
        )
        cls.backend_pr2 = PullRequestFactory(
            team=cls.team,
            github_repo="acme/backend",
            author=cls.member2,
            state="merged",
            pr_created_at=timezone.now() - timedelta(days=3),
            merged_at=timezone.now() - timedelta(days=2),
            cycle_time_hours=Decimal("36.0"),
            review_time_hours=Decimal("6.0"),
            is_ai_assisted=False,
            additions=80,
            deletions=30,
        )

        # Mobile repo - 1 PR
        cls.mobile_pr = PullRequestFactory(
            team=cls.team,
            github_repo="acme/mobile",
            author=cls.member1,
            state="merged",
            pr_created_at=timezone.now() - timedelta(days=2),
            merged_at=timezone.now() - timedelta(days=1),
            cycle_time_hours=Decimal("12.0"),
            review_time_hours=Decimal("2.0"),
            is_ai_assisted=False,
            additions=30,
            deletions=5,
        )

        # Create reviews for some PRs
        cls.review1 = PRReviewFactory(
            team=cls.team,
            pull_request=cls.frontend_pr1,
            reviewer=cls.member2,
            state="approved",
        )
        cls.review2 = PRReviewFactory(
            team=cls.team,
            pull_request=cls.backend_pr1,
            reviewer=cls.member2,
            state="approved",
        )


class TestApplyRepoFilterHelper(RepoFilterTestCase):
    """Tests for _apply_repo_filter helper function.

    🔴 RED Phase: These tests should FAIL initially because
    _apply_repo_filter() doesn't exist yet.
    """

    def test_apply_repo_filter_returns_filtered_queryset(self):
        """Filter returns only PRs from specified repository."""
        qs = PullRequest.objects.filter(team=self.team)

        # This will fail - function doesn't exist yet
        filtered = dashboard_service._apply_repo_filter(qs, "acme/frontend")

        self.assertEqual(filtered.count(), 2)
        for pr in filtered:
            self.assertEqual(pr.github_repo, "acme/frontend")

    def test_apply_repo_filter_returns_all_when_none(self):
        """No filter (None) returns all PRs."""
        qs = PullRequest.objects.filter(team=self.team)

        filtered = dashboard_service._apply_repo_filter(qs, None)

        self.assertEqual(filtered.count(), 5)  # All 5 PRs

    def test_apply_repo_filter_returns_all_when_empty_string(self):
        """Empty string treated same as None - returns all PRs."""
        qs = PullRequest.objects.filter(team=self.team)

        filtered = dashboard_service._apply_repo_filter(qs, "")

        self.assertEqual(filtered.count(), 5)

    def test_apply_repo_filter_returns_empty_for_nonexistent_repo(self):
        """Non-existent repo returns empty queryset (not error)."""
        qs = PullRequest.objects.filter(team=self.team)

        filtered = dashboard_service._apply_repo_filter(qs, "acme/nonexistent")

        self.assertEqual(filtered.count(), 0)

    def test_apply_repo_filter_preserves_existing_filters(self):
        """Repo filter combines with existing queryset filters."""
        # Start with only merged PRs
        qs = PullRequest.objects.filter(team=self.team, state="merged")

        filtered = dashboard_service._apply_repo_filter(qs, "acme/backend")

        self.assertEqual(filtered.count(), 2)
        for pr in filtered:
            self.assertEqual(pr.state, "merged")
            self.assertEqual(pr.github_repo, "acme/backend")


class TestGetKeyMetricsRepoFilter(RepoFilterTestCase):
    """Tests for get_key_metrics with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_key_metrics_returns_all_repos_when_no_filter(self):
        """Without repo param, returns metrics for all repos."""
        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date)

        # Should include all 5 PRs
        self.assertEqual(result["prs_merged"], 5)

    def test_get_key_metrics_filters_by_repo(self):
        """With repo param, returns metrics only for that repo."""
        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date, repo="acme/frontend")

        # Should only include 2 frontend PRs
        self.assertEqual(result["prs_merged"], 2)

    def test_get_key_metrics_returns_zero_for_nonexistent_repo(self):
        """Non-existent repo returns zero counts."""
        result = dashboard_service.get_key_metrics(self.team, self.start_date, self.end_date, repo="acme/nonexistent")

        self.assertEqual(result["prs_merged"], 0)


class TestGetCycleTimeTrendRepoFilter(RepoFilterTestCase):
    """Tests for get_cycle_time_trend with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_cycle_time_trend_returns_all_repos_when_no_filter(self):
        """Without repo param, includes data from all repos."""
        result = dashboard_service.get_cycle_time_trend(self.team, self.start_date, self.end_date)

        # Should return trend data (list of dicts with week/cycle_time)
        self.assertIsInstance(result, list)
        # Verify we have data
        self.assertTrue(len(result) > 0)

    def test_get_cycle_time_trend_filters_by_repo(self):
        """With repo param, only includes data from that repo."""
        result = dashboard_service.get_cycle_time_trend(self.team, self.start_date, self.end_date, repo="acme/frontend")

        # Result should be filtered (only frontend PRs contribute)
        # Frontend PRs have cycle times of 24h and 20h
        self.assertIsInstance(result, list)

    def test_get_cycle_time_trend_returns_empty_for_nonexistent_repo(self):
        """Non-existent repo returns empty list."""
        result = dashboard_service.get_cycle_time_trend(
            self.team, self.start_date, self.end_date, repo="acme/nonexistent"
        )

        self.assertEqual(result, [])


class TestGetAiAdoptionTrendRepoFilter(RepoFilterTestCase):
    """Tests for get_ai_adoption_trend with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_ai_adoption_trend_returns_all_repos_when_no_filter(self):
        """Without repo param, includes AI data from all repos."""
        result = dashboard_service.get_ai_adoption_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_ai_adoption_trend_filters_by_repo(self):
        """With repo param, only includes AI data from that repo."""
        result = dashboard_service.get_ai_adoption_trend(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        # Frontend has 2 PRs, 1 AI-assisted
        self.assertIsInstance(result, list)


class TestGetReviewTimeTrendRepoFilter(RepoFilterTestCase):
    """Tests for get_review_time_trend with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_review_time_trend_returns_all_repos_when_no_filter(self):
        """Without repo param, includes review data from all repos."""
        result = dashboard_service.get_review_time_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_review_time_trend_filters_by_repo(self):
        """With repo param, only includes review data from that repo."""
        result = dashboard_service.get_review_time_trend(self.team, self.start_date, self.end_date, repo="acme/backend")

        self.assertIsInstance(result, list)


class TestGetTeamBreakdownRepoFilter(RepoFilterTestCase):
    """Tests for get_team_breakdown with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_team_breakdown_returns_all_members_when_no_filter(self):
        """Without repo param, includes all team members with activity."""
        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)
        # Both members have PRs
        member_names = [r["member_name"] for r in result]
        self.assertIn("Alice Dev", member_names)
        self.assertIn("Bob Dev", member_names)

    def test_get_team_breakdown_filters_by_repo(self):
        """With repo param, only includes members with activity in that repo."""
        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date, repo="acme/mobile")

        # Only Alice has PRs in mobile repo
        self.assertIsInstance(result, list)
        # If filtering works correctly, Bob shouldn't appear (no mobile PRs)
        member_names = [r["member_name"] for r in result]
        self.assertIn("Alice Dev", member_names)


class TestGetPrSizeDistributionRepoFilter(RepoFilterTestCase):
    """Tests for get_pr_size_distribution with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_pr_size_distribution_returns_all_repos_when_no_filter(self):
        """Without repo param, includes size data from all repos."""
        result = dashboard_service.get_pr_size_distribution(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_pr_size_distribution_filters_by_repo(self):
        """With repo param, only includes size data from that repo."""
        result = dashboard_service.get_pr_size_distribution(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, list)


class TestGetAiQualityComparisonRepoFilter(RepoFilterTestCase):
    """Tests for get_ai_quality_comparison with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_ai_quality_comparison_returns_all_repos_when_no_filter(self):
        """Without repo param, includes quality data from all repos."""
        result = dashboard_service.get_ai_quality_comparison(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("ai_avg", result)
        self.assertIn("non_ai_avg", result)

    def test_get_ai_quality_comparison_filters_by_repo(self):
        """With repo param, only includes quality data from that repo."""
        result = dashboard_service.get_ai_quality_comparison(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetAiDetectedMetricsRepoFilter(RepoFilterTestCase):
    """Tests for get_ai_detected_metrics with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_ai_detected_metrics_returns_all_repos_when_no_filter(self):
        """Without repo param, includes all repos in detection stats."""
        result = dashboard_service.get_ai_detected_metrics(self.team, self.start_date, self.end_date)

        # All 5 PRs, 2 AI-assisted (frontend_pr1, backend_pr1)
        self.assertEqual(result["total_prs"], 5)
        self.assertEqual(result["ai_assisted_prs"], 2)

    def test_get_ai_detected_metrics_filters_by_repo(self):
        """With repo param, only includes that repo in detection stats."""
        result = dashboard_service.get_ai_detected_metrics(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        # Frontend has 2 PRs, 1 AI-assisted (frontend_pr1)
        self.assertEqual(result["total_prs"], 2)
        self.assertEqual(result["ai_assisted_prs"], 1)

    def test_get_ai_detected_metrics_returns_zero_for_nonexistent_repo(self):
        """Non-existent repo returns zero counts."""
        result = dashboard_service.get_ai_detected_metrics(
            self.team, self.start_date, self.end_date, repo="acme/nonexistent"
        )

        self.assertEqual(result["total_prs"], 0)
        self.assertEqual(result["ai_assisted_prs"], 0)


class TestGetAiToolBreakdownRepoFilter(RepoFilterTestCase):
    """Tests for get_ai_tool_breakdown with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_ai_tool_breakdown_returns_all_repos_when_no_filter(self):
        """Without repo param, includes tools from all repos."""
        result = dashboard_service.get_ai_tool_breakdown(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)
        # Should have both copilot and cursor from our test data
        tools = [r["tool"] for r in result]
        self.assertIn("copilot", tools)
        self.assertIn("cursor", tools)

    def test_get_ai_tool_breakdown_filters_by_repo(self):
        """With repo param, only includes tools from that repo."""
        result = dashboard_service.get_ai_tool_breakdown(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        # Frontend only has copilot
        tools = [r["tool"] for r in result]
        self.assertIn("copilot", tools)
        self.assertNotIn("cursor", tools)  # cursor is in backend

    def test_get_ai_tool_breakdown_returns_empty_for_nonexistent_repo(self):
        """Non-existent repo returns empty list."""
        result = dashboard_service.get_ai_tool_breakdown(
            self.team, self.start_date, self.end_date, repo="acme/nonexistent"
        )

        self.assertEqual(result, [])


class TestGetAiCategoryBreakdownRepoFilter(RepoFilterTestCase):
    """Tests for get_ai_category_breakdown with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_ai_category_breakdown_returns_all_repos_when_no_filter(self):
        """Without repo param, includes category data from all repos."""
        result = dashboard_service.get_ai_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("total_ai_prs", result)
        # 2 AI-assisted PRs total
        self.assertEqual(result["total_ai_prs"], 2)

    def test_get_ai_category_breakdown_filters_by_repo(self):
        """With repo param, only includes category data from that repo."""
        result = dashboard_service.get_ai_category_breakdown(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        # Frontend has 1 AI-assisted PR
        self.assertEqual(result["total_ai_prs"], 1)

    def test_get_ai_category_breakdown_returns_zero_for_nonexistent_repo(self):
        """Non-existent repo returns zero counts."""
        result = dashboard_service.get_ai_category_breakdown(
            self.team, self.start_date, self.end_date, repo="acme/nonexistent"
        )

        self.assertEqual(result["total_ai_prs"], 0)


class TestGetAiBotReviewStatsRepoFilter(RepoFilterTestCase):
    """Tests for get_ai_bot_review_stats with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_ai_bot_review_stats_returns_all_repos_when_no_filter(self):
        """Without repo param, includes review stats from all repos."""
        result = dashboard_service.get_ai_bot_review_stats(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("total_reviews", result)
        self.assertIn("ai_reviews", result)

    def test_get_ai_bot_review_stats_filters_by_repo(self):
        """With repo param, only includes review stats from that repo."""
        result = dashboard_service.get_ai_bot_review_stats(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetRecentPrsRepoFilter(RepoFilterTestCase):
    """Tests for get_recent_prs with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_recent_prs_returns_all_repos_when_no_filter(self):
        """Without repo param, includes PRs from all repos."""
        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)  # All 5 PRs

    def test_get_recent_prs_filters_by_repo(self):
        """With repo param, only includes PRs from that repo."""
        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date, repo="acme/frontend")

        self.assertEqual(len(result), 2)  # Only 2 frontend PRs

    def test_get_recent_prs_returns_empty_for_nonexistent_repo(self):
        """Non-existent repo returns empty list."""
        result = dashboard_service.get_recent_prs(self.team, self.start_date, self.end_date, repo="acme/nonexistent")

        self.assertEqual(result, [])


class TestGetRevertHotfixStatsRepoFilter(RepoFilterTestCase):
    """Tests for get_revert_hotfix_stats with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_revert_hotfix_stats_returns_all_repos_when_no_filter(self):
        """Without repo param, includes stats from all repos."""
        result = dashboard_service.get_revert_hotfix_stats(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["total_prs"], 5)

    def test_get_revert_hotfix_stats_filters_by_repo(self):
        """With repo param, only includes stats from that repo."""
        result = dashboard_service.get_revert_hotfix_stats(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertEqual(result["total_prs"], 2)

    def test_get_revert_hotfix_stats_returns_zero_for_nonexistent_repo(self):
        """Non-existent repo returns zero counts."""
        result = dashboard_service.get_revert_hotfix_stats(
            self.team, self.start_date, self.end_date, repo="acme/nonexistent"
        )

        self.assertEqual(result["total_prs"], 0)


class TestGetUnlinkedPrsRepoFilter(RepoFilterTestCase):
    """Tests for get_unlinked_prs with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_unlinked_prs_returns_all_repos_when_no_filter(self):
        """Without repo param, includes unlinked PRs from all repos."""
        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_unlinked_prs_filters_by_repo(self):
        """With repo param, only includes unlinked PRs from that repo."""
        result = dashboard_service.get_unlinked_prs(self.team, self.start_date, self.end_date, repo="acme/frontend")

        self.assertIsInstance(result, list)


class TestGetReviewerWorkloadRepoFilter(RepoFilterTestCase):
    """Tests for get_reviewer_workload with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_reviewer_workload_returns_all_repos_when_no_filter(self):
        """Without repo param, includes workload from all repos."""
        result = dashboard_service.get_reviewer_workload(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_reviewer_workload_filters_by_repo(self):
        """With repo param, only includes workload from that repo."""
        result = dashboard_service.get_reviewer_workload(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, list)


class TestGetIterationMetricsRepoFilter(RepoFilterTestCase):
    """Tests for get_iteration_metrics with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_iteration_metrics_returns_all_repos_when_no_filter(self):
        """Without repo param, includes metrics from all repos."""
        result = dashboard_service.get_iteration_metrics(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("prs_with_metrics", result)

    def test_get_iteration_metrics_filters_by_repo(self):
        """With repo param, only includes metrics from that repo."""
        result = dashboard_service.get_iteration_metrics(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetTrendComparisonRepoFilter(RepoFilterTestCase):
    """Tests for get_trend_comparison with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_trend_comparison_returns_all_repos_when_no_filter(self):
        """Without repo param, includes comparison data from all repos."""
        # get_trend_comparison takes metric, current period, and comparison period
        compare_start = self.start_date - timedelta(days=30)
        compare_end = self.start_date - timedelta(days=1)
        result = dashboard_service.get_trend_comparison(
            self.team, "cycle_time", self.start_date, self.end_date, compare_start, compare_end
        )

        self.assertIsInstance(result, dict)
        self.assertIn("current", result)
        self.assertIn("comparison", result)

    def test_get_trend_comparison_filters_by_repo(self):
        """With repo param, only includes comparison data from that repo."""
        compare_start = self.start_date - timedelta(days=30)
        compare_end = self.start_date - timedelta(days=1)
        result = dashboard_service.get_trend_comparison(
            self.team,
            "cycle_time",
            self.start_date,
            self.end_date,
            compare_start,
            compare_end,
            repo="acme/frontend",
        )

        self.assertIsInstance(result, dict)


class TestGetMonthlyPrTypeTrendRepoFilter(RepoFilterTestCase):
    """Tests for get_monthly_pr_type_trend with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_monthly_pr_type_trend_returns_all_repos_when_no_filter(self):
        """Without repo param, includes type data from all repos."""
        result = dashboard_service.get_monthly_pr_type_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_monthly_pr_type_trend_filters_by_repo(self):
        """With repo param, only includes type data from that repo."""
        result = dashboard_service.get_monthly_pr_type_trend(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetWeeklyPrTypeTrendRepoFilter(RepoFilterTestCase):
    """Tests for get_weekly_pr_type_trend with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_weekly_pr_type_trend_returns_all_repos_when_no_filter(self):
        """Without repo param, includes type data from all repos."""
        result = dashboard_service.get_weekly_pr_type_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_weekly_pr_type_trend_filters_by_repo(self):
        """With repo param, only includes type data from that repo."""
        result = dashboard_service.get_weekly_pr_type_trend(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetMonthlyTechTrendRepoFilter(RepoFilterTestCase):
    """Tests for get_monthly_tech_trend with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_monthly_tech_trend_returns_all_repos_when_no_filter(self):
        """Without repo param, includes tech data from all repos."""
        result = dashboard_service.get_monthly_tech_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_monthly_tech_trend_filters_by_repo(self):
        """With repo param, only includes tech data from that repo."""
        result = dashboard_service.get_monthly_tech_trend(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetWeeklyTechTrendRepoFilter(RepoFilterTestCase):
    """Tests for get_weekly_tech_trend with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_weekly_tech_trend_returns_all_repos_when_no_filter(self):
        """Without repo param, includes tech data from all repos."""
        result = dashboard_service.get_weekly_tech_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_weekly_tech_trend_filters_by_repo(self):
        """With repo param, only includes tech data from that repo."""
        result = dashboard_service.get_weekly_tech_trend(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetSparklineDataRepoFilter(RepoFilterTestCase):
    """Tests for get_sparkline_data with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_sparkline_data_returns_all_repos_when_no_filter(self):
        """Without repo param, includes sparkline data from all repos."""
        result = dashboard_service.get_sparkline_data(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("prs_merged", result)

    def test_get_sparkline_data_filters_by_repo(self):
        """With repo param, only includes sparkline data from that repo."""
        result = dashboard_service.get_sparkline_data(self.team, self.start_date, self.end_date, repo="acme/frontend")

        self.assertIsInstance(result, dict)
        self.assertIn("prs_merged", result)


# =============================================================================
# Phase 1.7: Batch 5 - Remaining Functions
# =============================================================================


class TestGetCopilotMetricsRepoFilter(RepoFilterTestCase):
    """Tests for get_copilot_metrics with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_copilot_metrics_returns_all_repos_when_no_filter(self):
        """Without repo param, includes copilot metrics from all repos."""
        result = dashboard_service.get_copilot_metrics(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_copilot_metrics_filters_by_repo(self):
        """With repo param, only includes copilot metrics from that repo."""
        result = dashboard_service.get_copilot_metrics(self.team, self.start_date, self.end_date, repo="acme/frontend")

        self.assertIsInstance(result, dict)


class TestGetCopilotTrendRepoFilter(RepoFilterTestCase):
    """Tests for get_copilot_trend with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_copilot_trend_returns_all_repos_when_no_filter(self):
        """Without repo param, includes copilot trend from all repos."""
        result = dashboard_service.get_copilot_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_copilot_trend_filters_by_repo(self):
        """With repo param, only includes copilot trend from that repo."""
        result = dashboard_service.get_copilot_trend(self.team, self.start_date, self.end_date, repo="acme/frontend")

        self.assertIsInstance(result, list)


class TestGetCopilotByMemberRepoFilter(RepoFilterTestCase):
    """Tests for get_copilot_by_member with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_copilot_by_member_returns_all_repos_when_no_filter(self):
        """Without repo param, includes copilot by member from all repos."""
        result = dashboard_service.get_copilot_by_member(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_copilot_by_member_filters_by_repo(self):
        """With repo param, only includes copilot by member from that repo."""
        result = dashboard_service.get_copilot_by_member(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, list)


class TestGetCicdPassRateRepoFilter(RepoFilterTestCase):
    """Tests for get_cicd_pass_rate with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_cicd_pass_rate_returns_all_repos_when_no_filter(self):
        """Without repo param, includes CICD pass rate from all repos."""
        result = dashboard_service.get_cicd_pass_rate(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_cicd_pass_rate_filters_by_repo(self):
        """With repo param, only includes CICD pass rate from that repo."""
        result = dashboard_service.get_cicd_pass_rate(self.team, self.start_date, self.end_date, repo="acme/frontend")

        self.assertIsInstance(result, dict)


class TestGetDeploymentMetricsRepoFilter(RepoFilterTestCase):
    """Tests for get_deployment_metrics with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_deployment_metrics_returns_all_repos_when_no_filter(self):
        """Without repo param, includes deployment metrics from all repos."""
        result = dashboard_service.get_deployment_metrics(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_deployment_metrics_filters_by_repo(self):
        """With repo param, only includes deployment metrics from that repo."""
        result = dashboard_service.get_deployment_metrics(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetFileCategoryBreakdownRepoFilter(RepoFilterTestCase):
    """Tests for get_file_category_breakdown with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_file_category_breakdown_returns_all_repos_when_no_filter(self):
        """Without repo param, includes file category from all repos."""
        result = dashboard_service.get_file_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_file_category_breakdown_filters_by_repo(self):
        """With repo param, only includes file category from that repo."""
        result = dashboard_service.get_file_category_breakdown(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetResponseChannelDistributionRepoFilter(RepoFilterTestCase):
    """Tests for get_response_channel_distribution with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_response_channel_distribution_returns_all_repos_when_no_filter(self):
        """Without repo param, includes response channel data from all repos."""
        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_response_channel_distribution_filters_by_repo(self):
        """With repo param, only includes response channel data from that repo."""
        result = dashboard_service.get_response_channel_distribution(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetAiDetectionMetricsRepoFilter(RepoFilterTestCase):
    """Tests for get_ai_detection_metrics with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_ai_detection_metrics_returns_all_repos_when_no_filter(self):
        """Without repo param, includes AI detection metrics from all repos."""
        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_ai_detection_metrics_filters_by_repo(self):
        """With repo param, only includes AI detection metrics from that repo."""
        result = dashboard_service.get_ai_detection_metrics(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)


class TestGetResponseTimeMetricsRepoFilter(RepoFilterTestCase):
    """Tests for get_response_time_metrics with repo filter.

    🔴 RED Phase: Tests should FAIL until repo param is added.
    """

    def test_get_response_time_metrics_returns_all_repos_when_no_filter(self):
        """Without repo param, includes response time metrics from all repos."""
        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)

    def test_get_response_time_metrics_filters_by_repo(self):
        """With repo param, only includes response time metrics from that repo."""
        result = dashboard_service.get_response_time_metrics(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )

        self.assertIsInstance(result, dict)
