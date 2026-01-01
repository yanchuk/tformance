"""Tests for Jira metrics functions in dashboard service.

TDD RED Phase: These tests define the expected behavior.
Tests should FAIL initially until the functions are implemented.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    JiraIssueFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)


class TestJiraSprintMetrics(TestCase):
    """Tests for get_jira_sprint_metrics function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()
        self.start_date = self.today - timedelta(days=30)
        self.end_date = self.today

    def test_get_jira_sprint_metrics_function_exists(self):
        """Test that get_jira_sprint_metrics is importable."""
        from apps.metrics.services.dashboard_service import get_jira_sprint_metrics

        self.assertTrue(callable(get_jira_sprint_metrics))

    def test_get_jira_sprint_metrics_counts_resolved_issues(self):
        """Should count issues resolved in date range."""
        from apps.metrics.services.dashboard_service import get_jira_sprint_metrics

        # Create issues resolved in range
        JiraIssueFactory.create_batch(
            3,
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=timezone.now() - timedelta(days=5),
        )
        # Create issue outside range (should not be counted)
        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=timezone.now() - timedelta(days=60),
        )

        result = get_jira_sprint_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["issues_resolved"], 3)

    def test_get_jira_sprint_metrics_sums_story_points(self):
        """Should sum story points from resolved issues."""
        from apps.metrics.services.dashboard_service import get_jira_sprint_metrics

        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            story_points=Decimal("5"),
            resolved_at=timezone.now() - timedelta(days=5),
        )
        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            story_points=Decimal("8"),
            resolved_at=timezone.now() - timedelta(days=3),
        )

        result = get_jira_sprint_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["story_points_completed"], Decimal("13"))

    def test_get_jira_sprint_metrics_calculates_avg_cycle_time(self):
        """Should average cycle_time_hours across issues."""
        from apps.metrics.services.dashboard_service import get_jira_sprint_metrics

        # Create issues with known cycle times
        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            cycle_time_hours=Decimal("10.0"),
            resolved_at=timezone.now() - timedelta(days=5),
        )
        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            cycle_time_hours=Decimal("20.0"),
            resolved_at=timezone.now() - timedelta(days=3),
        )

        result = get_jira_sprint_metrics(self.team, self.start_date, self.end_date)

        # Average of 10 and 20 = 15
        self.assertIsNotNone(result["avg_cycle_time_hours"])
        self.assertAlmostEqual(float(result["avg_cycle_time_hours"]), 15.0, delta=0.1)

    def test_get_jira_sprint_metrics_filters_by_date_range(self):
        """Should only include issues resolved within date range."""
        from apps.metrics.services.dashboard_service import get_jira_sprint_metrics

        # Issue in range
        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=timezone.now() - timedelta(days=10),
        )
        # Issue before range
        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=timezone.now() - timedelta(days=45),
        )

        result = get_jira_sprint_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["issues_resolved"], 1)

    def test_get_jira_sprint_metrics_handles_no_issues(self):
        """Should return zeros when no issues exist."""
        from apps.metrics.services.dashboard_service import get_jira_sprint_metrics

        result = get_jira_sprint_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["issues_resolved"], 0)
        self.assertEqual(result["story_points_completed"], 0)
        self.assertIsNone(result["avg_cycle_time_hours"])


class TestPRJiraCorrelation(TestCase):
    """Tests for get_pr_jira_correlation function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()
        self.start_date = self.today - timedelta(days=30)
        self.end_date = self.today

    def test_get_pr_jira_correlation_function_exists(self):
        """Test that get_pr_jira_correlation is importable."""
        from apps.metrics.services.dashboard_service import get_pr_jira_correlation

        self.assertTrue(callable(get_pr_jira_correlation))

    def test_get_pr_jira_correlation_calculates_linkage_rate(self):
        """Should calculate % of PRs with jira_key."""
        from apps.metrics.services.dashboard_service import get_pr_jira_correlation

        # 3 PRs with jira_key, 2 without
        PullRequestFactory.create_batch(
            3,
            team=self.team,
            author=self.member,
            jira_key="PROJ-123",
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
        )
        PullRequestFactory.create_batch(
            2,
            team=self.team,
            author=self.member,
            jira_key="",
            state="merged",
            merged_at=timezone.now() - timedelta(days=3),
        )

        result = get_pr_jira_correlation(self.team, self.start_date, self.end_date)

        # 3/5 = 60%
        self.assertEqual(result["linkage_rate"], 60.0)
        self.assertEqual(result["linked_count"], 3)
        self.assertEqual(result["unlinked_count"], 2)

    def test_get_pr_jira_correlation_compares_cycle_times(self):
        """Should compare linked vs unlinked PR cycle times."""
        from apps.metrics.services.dashboard_service import get_pr_jira_correlation

        # Linked PRs with faster cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key="PROJ-100",
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("10.0"),
        )
        # Unlinked PRs with slower cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key="",
            state="merged",
            merged_at=timezone.now() - timedelta(days=3),
            cycle_time_hours=Decimal("30.0"),
        )

        result = get_pr_jira_correlation(self.team, self.start_date, self.end_date)

        self.assertIsNotNone(result["linked_avg_cycle_time"])
        self.assertIsNotNone(result["unlinked_avg_cycle_time"])
        self.assertAlmostEqual(float(result["linked_avg_cycle_time"]), 10.0, delta=0.1)
        self.assertAlmostEqual(float(result["unlinked_avg_cycle_time"]), 30.0, delta=0.1)

    def test_get_pr_jira_correlation_handles_no_prs(self):
        """Should return 0% linkage when no PRs exist."""
        from apps.metrics.services.dashboard_service import get_pr_jira_correlation

        result = get_pr_jira_correlation(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_prs"], 0)
        self.assertEqual(result["linkage_rate"], 0)
        self.assertEqual(result["linked_count"], 0)
        self.assertEqual(result["unlinked_count"], 0)

    def test_get_pr_jira_correlation_handles_all_linked(self):
        """Should return 100% linkage when all PRs have jira_key."""
        from apps.metrics.services.dashboard_service import get_pr_jira_correlation

        PullRequestFactory.create_batch(
            5,
            team=self.team,
            author=self.member,
            jira_key="PROJ-456",
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
        )

        result = get_pr_jira_correlation(self.team, self.start_date, self.end_date)

        self.assertEqual(result["linkage_rate"], 100.0)
        self.assertEqual(result["linked_count"], 5)
        self.assertEqual(result["unlinked_count"], 0)

    def test_get_pr_jira_correlation_handles_all_unlinked(self):
        """Should return 0% linkage when no PRs have jira_key."""
        from apps.metrics.services.dashboard_service import get_pr_jira_correlation

        PullRequestFactory.create_batch(
            3,
            team=self.team,
            author=self.member,
            jira_key="",
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
        )

        result = get_pr_jira_correlation(self.team, self.start_date, self.end_date)

        self.assertEqual(result["linkage_rate"], 0)
        self.assertEqual(result["linked_count"], 0)
        self.assertEqual(result["unlinked_count"], 3)
