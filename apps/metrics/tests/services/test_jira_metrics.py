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


class TestLinkageTrend(TestCase):
    """Tests for get_linkage_trend function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()

    def _get_week_start(self, weeks_ago: int) -> date:
        """Helper to get the Monday of N weeks ago."""
        today = self.today
        # Get this week's Monday
        this_monday = today - timedelta(days=today.weekday())
        # Go back N weeks
        return this_monday - timedelta(weeks=weeks_ago)

    def test_get_linkage_trend_function_exists(self):
        """Test that get_linkage_trend is importable."""
        from apps.metrics.services.dashboard_service import get_linkage_trend

        self.assertTrue(callable(get_linkage_trend))

    def test_get_linkage_trend_returns_list(self):
        """Should return a list."""
        from apps.metrics.services.dashboard_service import get_linkage_trend

        result = get_linkage_trend(self.team)

        self.assertIsInstance(result, list)

    def test_get_linkage_trend_returns_weekly_data(self):
        """Each item should have week_start, linkage_rate, linked_count, total_prs."""
        from apps.metrics.services.dashboard_service import get_linkage_trend

        # Create PRs in the last week - use week_start + 1 hour to ensure it's in the past
        # (days=2 would be Wednesday which is in the future if today is Monday)
        week_start = self._get_week_start(0)
        merged_at = timezone.make_aware(
            timezone.datetime.combine(week_start, timezone.datetime.min.time())
        ) + timedelta(hours=1)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key="PROJ-123",
            state="merged",
            merged_at=merged_at,
        )

        result = get_linkage_trend(self.team, weeks=1)

        self.assertEqual(len(result), 1)
        week_data = result[0]
        self.assertIn("week_start", week_data)
        self.assertIn("linkage_rate", week_data)
        self.assertIn("linked_count", week_data)
        self.assertIn("total_prs", week_data)

    def test_get_linkage_trend_calculates_rate_per_week(self):
        """Should calculate correct linkage rate for each week."""
        from apps.metrics.services.dashboard_service import get_linkage_trend

        # Week 1 (most recent): 2 linked, 2 unlinked = 50%
        # Use hours=1 instead of days=2 to ensure it's in the past on all days
        week1_start = self._get_week_start(0)
        week1_merged = timezone.make_aware(
            timezone.datetime.combine(week1_start, timezone.datetime.min.time())
        ) + timedelta(hours=1)
        PullRequestFactory.create_batch(
            2,
            team=self.team,
            author=self.member,
            jira_key="PROJ-100",
            state="merged",
            merged_at=week1_merged,
        )
        PullRequestFactory.create_batch(
            2,
            team=self.team,
            author=self.member,
            jira_key="",
            state="merged",
            merged_at=week1_merged,
        )

        # Week 2: 3 linked, 1 unlinked = 75%
        # Past weeks can use days=2 safely since Wednesday of last week is always past
        week2_start = self._get_week_start(1)
        week2_merged = timezone.make_aware(
            timezone.datetime.combine(week2_start + timedelta(days=2), timezone.datetime.min.time())
        )
        PullRequestFactory.create_batch(
            3,
            team=self.team,
            author=self.member,
            jira_key="PROJ-200",
            state="merged",
            merged_at=week2_merged,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key="",
            state="merged",
            merged_at=week2_merged,
        )

        result = get_linkage_trend(self.team, weeks=2)

        # Result should be ordered oldest to newest
        self.assertEqual(len(result), 2)
        # Week 2 (older) first
        self.assertEqual(result[0]["linkage_rate"], 75.0)
        self.assertEqual(result[0]["linked_count"], 3)
        self.assertEqual(result[0]["total_prs"], 4)
        # Week 1 (newer) second
        self.assertEqual(result[1]["linkage_rate"], 50.0)
        self.assertEqual(result[1]["linked_count"], 2)
        self.assertEqual(result[1]["total_prs"], 4)

    def test_get_linkage_trend_handles_no_prs(self):
        """Should return empty list when no PRs exist."""
        from apps.metrics.services.dashboard_service import get_linkage_trend

        result = get_linkage_trend(self.team, weeks=4)

        self.assertEqual(result, [])

    def test_get_linkage_trend_respects_weeks_param(self):
        """Should return requested number of weeks with data."""
        from apps.metrics.services.dashboard_service import get_linkage_trend

        # Create PRs in weeks 0, 1, 2, 3 (4 weeks)
        for weeks_ago in range(4):
            week_start = self._get_week_start(weeks_ago)
            # For week 0, use hours=1; for past weeks, days=2 is safe
            if weeks_ago == 0:
                merged_at = timezone.make_aware(
                    timezone.datetime.combine(week_start, timezone.datetime.min.time())
                ) + timedelta(hours=1)
            else:
                merged_at = timezone.make_aware(
                    timezone.datetime.combine(week_start + timedelta(days=2), timezone.datetime.min.time())
                )
            PullRequestFactory(
                team=self.team,
                author=self.member,
                jira_key="PROJ-123",
                state="merged",
                merged_at=merged_at,
            )

        # Request only 2 weeks
        result = get_linkage_trend(self.team, weeks=2)

        self.assertEqual(len(result), 2)

        # Request 4 weeks
        result_4 = get_linkage_trend(self.team, weeks=4)

        self.assertEqual(len(result_4), 4)


class TestStoryPointCorrelation(TestCase):
    """Tests for get_story_point_correlation function.

    This function compares estimated story points vs actual PR delivery time.
    PRs are linked to Jira issues via the jira_key field (string match).
    Returns data suitable for a grouped bar chart showing SP buckets vs avg hours.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()
        self.start_date = self.today - timedelta(days=30)
        self.end_date = self.today

    def test_get_story_point_correlation_function_exists(self):
        """Test that get_story_point_correlation is importable and callable."""
        from apps.metrics.services.dashboard_service import get_story_point_correlation

        self.assertTrue(callable(get_story_point_correlation))

    def test_get_story_point_correlation_returns_expected_structure(self):
        """Test that function returns dict with 'buckets' key and summary fields."""
        from apps.metrics.services.dashboard_service import get_story_point_correlation

        result = get_story_point_correlation(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("buckets", result)
        self.assertIsInstance(result["buckets"], list)
        self.assertIn("total_linked_prs", result)
        self.assertIn("total_with_sp", result)

    def test_get_story_point_correlation_groups_by_bucket(self):
        """Test that PRs are grouped into SP ranges: 1-2, 3-5, 5-8, 8-13, 13+."""
        from apps.metrics.services.dashboard_service import get_story_point_correlation

        # Create Jira issues with different story points
        issue_1sp = JiraIssueFactory(team=self.team, jira_key="PROJ-101", story_points=Decimal("1"))
        issue_3sp = JiraIssueFactory(team=self.team, jira_key="PROJ-102", story_points=Decimal("3"))
        issue_5sp = JiraIssueFactory(team=self.team, jira_key="PROJ-103", story_points=Decimal("5"))
        issue_8sp = JiraIssueFactory(team=self.team, jira_key="PROJ-104", story_points=Decimal("8"))
        issue_13sp = JiraIssueFactory(team=self.team, jira_key="PROJ-105", story_points=Decimal("13"))
        issue_21sp = JiraIssueFactory(team=self.team, jira_key="PROJ-106", story_points=Decimal("21"))

        # Create merged PRs linked to these issues
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_1sp.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("4.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_3sp.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("8.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_5sp.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("12.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_8sp.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("24.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_13sp.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("48.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_21sp.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("72.0"),
        )

        result = get_story_point_correlation(self.team, self.start_date, self.end_date)

        # Verify buckets structure
        buckets = result["buckets"]
        sp_ranges = [bucket["sp_range"] for bucket in buckets]

        # Should have these SP ranges
        expected_ranges = ["1-2", "3-5", "5-8", "8-13", "13+"]
        for expected_range in expected_ranges:
            self.assertIn(expected_range, sp_ranges, f"Missing SP range: {expected_range}")

    def test_get_story_point_correlation_calculates_avg_hours(self):
        """Test that avg cycle_time_hours is calculated per bucket."""
        from apps.metrics.services.dashboard_service import get_story_point_correlation

        # Create Jira issues in the 3-5 SP bucket
        issue_3sp_a = JiraIssueFactory(team=self.team, jira_key="PROJ-201", story_points=Decimal("3"))
        issue_3sp_b = JiraIssueFactory(team=self.team, jira_key="PROJ-202", story_points=Decimal("5"))

        # Create merged PRs with known cycle times
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_3sp_a.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("10.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_3sp_b.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=3),
            cycle_time_hours=Decimal("20.0"),
        )

        result = get_story_point_correlation(self.team, self.start_date, self.end_date)

        # Find the 3-5 bucket
        bucket_3_5 = next((b for b in result["buckets"] if b["sp_range"] == "3-5"), None)
        self.assertIsNotNone(bucket_3_5, "Missing 3-5 SP bucket")

        # Average of 10 and 20 = 15
        self.assertAlmostEqual(float(bucket_3_5["avg_hours"]), 15.0, delta=0.1)
        self.assertEqual(bucket_3_5["pr_count"], 2)

        # Each bucket should also have expected_hours for comparison
        self.assertIn("expected_hours", bucket_3_5)

    def test_get_story_point_correlation_handles_no_linked_prs(self):
        """Test that empty buckets are returned when no PRs have jira_key."""
        from apps.metrics.services.dashboard_service import get_story_point_correlation

        # Create PRs without jira_key
        PullRequestFactory.create_batch(
            3,
            team=self.team,
            author=self.member,
            jira_key="",
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("10.0"),
        )

        result = get_story_point_correlation(self.team, self.start_date, self.end_date)

        # Should return empty or zero-count buckets
        self.assertEqual(result["total_linked_prs"], 0)
        self.assertEqual(result["total_with_sp"], 0)

        # Buckets should be empty or all have pr_count=0
        for bucket in result["buckets"]:
            self.assertEqual(bucket["pr_count"], 0)

    def test_get_story_point_correlation_ignores_prs_without_story_points(self):
        """Test that PRs linked to issues without story_points are excluded from buckets."""
        from apps.metrics.services.dashboard_service import get_story_point_correlation

        # Create Jira issue WITHOUT story points
        issue_no_sp = JiraIssueFactory(team=self.team, jira_key="PROJ-301", story_points=None)

        # Create Jira issue WITH story points
        issue_with_sp = JiraIssueFactory(team=self.team, jira_key="PROJ-302", story_points=Decimal("5"))

        # Create PRs linked to both issues
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_no_sp.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("10.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            jira_key=issue_with_sp.jira_key,
            state="merged",
            merged_at=timezone.now() - timedelta(days=3),
            cycle_time_hours=Decimal("20.0"),
        )

        result = get_story_point_correlation(self.team, self.start_date, self.end_date)

        # Both PRs are linked, but only 1 has story points
        self.assertEqual(result["total_linked_prs"], 2)
        self.assertEqual(result["total_with_sp"], 1)

        # Only the PR with story points should be in buckets
        total_pr_count = sum(bucket["pr_count"] for bucket in result["buckets"])
        self.assertEqual(total_pr_count, 1)


class TestVelocityTrend(TestCase):
    """Tests for get_velocity_trend function.

    This function returns velocity metrics (story points completed) over time,
    grouped by week or sprint. Used for velocity trend line charts.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()
        self.start_date = self.today - timedelta(days=30)
        self.end_date = self.today

    def _get_week_start(self, weeks_ago: int) -> date:
        """Helper to get the Monday of N weeks ago."""
        today = self.today
        # Get this week's Monday
        this_monday = today - timedelta(days=today.weekday())
        # Go back N weeks
        return this_monday - timedelta(weeks=weeks_ago)

    def test_get_velocity_trend_function_exists(self):
        """Test that get_velocity_trend is importable and callable."""
        from apps.metrics.services.dashboard_service import get_velocity_trend

        self.assertTrue(callable(get_velocity_trend))

    def test_get_velocity_trend_returns_expected_structure(self):
        """Test that function returns dict with 'periods' list and summary fields."""
        from apps.metrics.services.dashboard_service import get_velocity_trend

        result = get_velocity_trend(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("periods", result)
        self.assertIsInstance(result["periods"], list)
        self.assertIn("total_story_points", result)
        self.assertIn("total_issues", result)
        self.assertIn("grouping", result)

    def test_get_velocity_trend_groups_by_week(self):
        """Test that issues are grouped by calendar week when no sprint data."""
        from apps.metrics.services.dashboard_service import get_velocity_trend

        # Create issues resolved in week 0 (this week)
        # Use hours=1 instead of days=2 to ensure date is in the past on all days
        week0_start = self._get_week_start(0)
        week0_resolved = timezone.make_aware(
            timezone.datetime.combine(week0_start, timezone.datetime.min.time())
        ) + timedelta(hours=1)
        JiraIssueFactory.create_batch(
            2,
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=week0_resolved,
            story_points=Decimal("5"),
            sprint_id="",  # No sprint data
            sprint_name="",
        )

        # Create issues resolved in week 1 (last week) - days=3 is safe for past weeks
        week1_start = self._get_week_start(1)
        week1_resolved = timezone.make_aware(
            timezone.datetime.combine(week1_start + timedelta(days=3), timezone.datetime.min.time())
        )
        JiraIssueFactory.create_batch(
            3,
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=week1_resolved,
            story_points=Decimal("3"),
            sprint_id="",
            sprint_name="",
        )

        result = get_velocity_trend(self.team, self.start_date, self.end_date)

        # Should have 2 periods (weeks with data)
        self.assertEqual(len(result["periods"]), 2)
        self.assertEqual(result["grouping"], "weekly")

        # Each period should have expected keys
        for period in result["periods"]:
            self.assertIn("period_start", period)
            self.assertIn("period_name", period)
            self.assertIn("story_points", period)
            self.assertIn("issues_resolved", period)

    def test_get_velocity_trend_calculates_story_points_per_period(self):
        """Test that story_points are summed correctly per period."""
        from apps.metrics.services.dashboard_service import get_velocity_trend

        # Create issues in a single week with known story points
        # Use hours=1 to ensure it's in the past (days=1 would be Tuesday, which is future on Monday)
        week_start = self._get_week_start(0)
        resolved_at = timezone.make_aware(
            timezone.datetime.combine(week_start, timezone.datetime.min.time())
        ) + timedelta(hours=1)

        # Issue with 5 SP
        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=resolved_at,
            story_points=Decimal("5"),
            sprint_id="",
            sprint_name="",
        )
        # Issue with 8 SP
        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=resolved_at,
            story_points=Decimal("8"),
            sprint_id="",
            sprint_name="",
        )
        # Issue with 13 SP
        JiraIssueFactory(
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=resolved_at,
            story_points=Decimal("13"),
            sprint_id="",
            sprint_name="",
        )

        result = get_velocity_trend(self.team, self.start_date, self.end_date)

        # Should have 1 period with sum of 5 + 8 + 13 = 26 SP
        self.assertEqual(len(result["periods"]), 1)
        self.assertEqual(result["periods"][0]["story_points"], Decimal("26"))
        self.assertEqual(result["total_story_points"], Decimal("26"))

    def test_get_velocity_trend_includes_issues_resolved_count(self):
        """Test that issues_resolved count is correct per period."""
        from apps.metrics.services.dashboard_service import get_velocity_trend

        # Create 4 issues resolved in this week
        # Use hours=1 to ensure it's in the past on all days (days=2 would be Wednesday)
        week_start = self._get_week_start(0)
        resolved_at = timezone.make_aware(
            timezone.datetime.combine(week_start, timezone.datetime.min.time())
        ) + timedelta(hours=1)
        JiraIssueFactory.create_batch(
            4,
            team=self.team,
            assignee=self.member,
            status="Done",
            resolved_at=resolved_at,
            story_points=Decimal("3"),
            sprint_id="",
            sprint_name="",
        )

        result = get_velocity_trend(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result["periods"]), 1)
        self.assertEqual(result["periods"][0]["issues_resolved"], 4)
        self.assertEqual(result["total_issues"], 4)

    def test_get_velocity_trend_handles_no_resolved_issues(self):
        """Test that empty periods list is returned when no issues are resolved."""
        from apps.metrics.services.dashboard_service import get_velocity_trend

        # No issues created - team has no velocity data

        result = get_velocity_trend(self.team, self.start_date, self.end_date)

        self.assertEqual(result["periods"], [])
        self.assertEqual(result["total_story_points"], 0)
        self.assertEqual(result["total_issues"], 0)
        self.assertEqual(result["grouping"], "weekly")
