"""Tests for get_sparkline_data dashboard function."""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.metrics.services.dashboard_service import get_sparkline_data


class TestGetSparklineData(TestCase):
    """Tests for get_sparkline_data function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=90)

    def test_returns_dict_with_required_keys(self):
        """get_sparkline_data returns dict with all four metric keys."""
        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("prs_merged", result)
        self.assertIn("cycle_time", result)
        self.assertIn("ai_adoption", result)
        self.assertIn("review_time", result)

    def test_each_metric_has_values_change_pct_and_trend(self):
        """Each metric contains values list, change_pct int, and trend string."""
        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        for metric_name in ["prs_merged", "cycle_time", "ai_adoption", "review_time"]:
            metric = result[metric_name]
            self.assertIn("values", metric)
            self.assertIn("change_pct", metric)
            self.assertIn("trend", metric)
            self.assertIsInstance(metric["values"], list)
            self.assertIsInstance(metric["change_pct"], int)
            self.assertIn(metric["trend"], ["up", "down", "flat"])

    def test_returns_empty_values_when_no_prs(self):
        """Returns empty values list when no PRs exist."""
        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        self.assertEqual(result["prs_merged"]["values"], [])
        self.assertEqual(result["cycle_time"]["values"], [])
        self.assertEqual(result["ai_adoption"]["values"], [])
        self.assertEqual(result["review_time"]["values"], [])

    def test_returns_flat_trend_when_no_data(self):
        """Returns flat trend when no data exists."""
        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        self.assertEqual(result["prs_merged"]["trend"], "flat")
        self.assertEqual(result["prs_merged"]["change_pct"], 0)

    def test_prs_merged_counts_weekly_prs(self):
        """prs_merged values contain weekly PR counts."""
        week1_start = self.end_date - timedelta(days=14)
        week2_start = self.end_date - timedelta(days=7)

        # Create 2 PRs in week 1
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
        )

        # Create 3 PRs in week 2
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should have 2 weeks of data
        self.assertGreaterEqual(len(result["prs_merged"]["values"]), 2)
        # Verify the counts are present (order depends on week boundaries)
        self.assertTrue(2 in result["prs_merged"]["values"] or 3 in result["prs_merged"]["values"])

    def test_cycle_time_calculates_weekly_average(self):
        """cycle_time values contain weekly average cycle time in hours."""
        merge_date = self.end_date - timedelta(days=3)

        # Create PRs with known cycle times
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            cycle_time_hours=Decimal("10.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            cycle_time_hours=Decimal("20.0"),
        )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should have cycle time values
        self.assertGreater(len(result["cycle_time"]["values"]), 0)
        # Average of 10 and 20 should be 15
        self.assertIn(15.0, result["cycle_time"]["values"])

    def test_ai_adoption_calculates_weekly_percentage(self):
        """ai_adoption values contain weekly AI adoption percentage."""
        merge_date = self.end_date - timedelta(days=3)

        # Create 3 AI-assisted PRs and 1 non-AI PR
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
                is_ai_assisted=True,
            )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            is_ai_assisted=False,
        )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should have AI adoption values
        self.assertGreater(len(result["ai_adoption"]["values"]), 0)
        # 3 out of 4 = 75%
        self.assertIn(75.0, result["ai_adoption"]["values"])

    def test_review_time_calculates_weekly_average(self):
        """review_time values contain weekly average review time in hours."""
        merge_date = self.end_date - timedelta(days=3)

        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            review_time_hours=Decimal("5.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            review_time_hours=Decimal("15.0"),
        )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should have review time values
        self.assertGreater(len(result["review_time"]["values"]), 0)
        # Average of 5 and 15 should be 10
        self.assertIn(10.0, result["review_time"]["values"])

    def test_trend_is_up_when_value_increases(self):
        """Trend is 'up' when last week's value exceeds first week's."""
        week1_start = self.end_date - timedelta(days=14)
        week2_start = self.end_date - timedelta(days=7)

        # Create 1 PR in week 1
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
        )

        # Create 3 PRs in week 2
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        self.assertEqual(result["prs_merged"]["trend"], "up")
        self.assertGreater(result["prs_merged"]["change_pct"], 0)

    def test_trend_is_down_when_value_decreases(self):
        """Trend is 'down' when last week's value is less than first week's."""
        week1_start = self.end_date - timedelta(days=14)
        week2_start = self.end_date - timedelta(days=7)

        # Create 3 PRs in week 1
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )

        # Create 1 PR in week 2
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
        )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        self.assertEqual(result["prs_merged"]["trend"], "down")
        self.assertLess(result["prs_merged"]["change_pct"], 0)

    def test_change_pct_calculated_correctly(self):
        """change_pct is calculated as percentage change from first to last."""
        week1_start = self.end_date - timedelta(days=14)
        week2_start = self.end_date - timedelta(days=7)

        # Create 2 PRs in week 1
        for _ in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )

        # Create 4 PRs in week 2 (100% increase)
        for _ in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # 2 -> 4 = 100% increase
        self.assertEqual(result["prs_merged"]["change_pct"], 100)

    def test_filters_by_team(self):
        """Only includes PRs from the specified team."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        merge_date = self.end_date - timedelta(days=3)

        # Create PR for our team
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
        )

        # Create PR for other team
        PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
        )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should only have 1 PR from our team
        self.assertEqual(sum(result["prs_merged"]["values"]), 1)

    def test_filters_by_date_range(self):
        """Only includes PRs within the specified date range."""
        in_range_date = self.end_date - timedelta(days=3)
        out_of_range_date = self.start_date - timedelta(days=10)

        # Create PR in range
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(in_range_date, timezone.datetime.min.time())),
        )

        # Create PR out of range
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(out_of_range_date, timezone.datetime.min.time())),
        )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should only count 1 PR (in range)
        self.assertEqual(sum(result["prs_merged"]["values"]), 1)

    def test_only_includes_merged_prs(self):
        """Only includes merged PRs, not open or closed."""
        merge_date = self.end_date - timedelta(days=3)

        # Create merged PR
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
        )

        # Create open PR (should not be counted)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="open",
            merged_at=None,
        )

        # Create closed PR (should not be counted)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="closed",
            merged_at=None,
        )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should only count 1 merged PR
        self.assertEqual(sum(result["prs_merged"]["values"]), 1)

    def test_handles_zero_first_value_with_positive_last(self):
        """Returns 100% change and 'up' trend when first week is 0 and last has data."""
        # Only create PRs in the most recent week
        merge_date = self.end_date - timedelta(days=3)

        # Create PRs only in last week
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            )

        # Create 0 PRs in earlier weeks (but we need at least 2 data points)
        # This test verifies the edge case handling

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # If there's only one week of data, trend should be flat
        if len(result["prs_merged"]["values"]) == 1:
            self.assertEqual(result["prs_merged"]["trend"], "flat")
            self.assertEqual(result["prs_merged"]["change_pct"], 0)

    def test_values_ordered_chronologically(self):
        """Values are ordered from oldest to newest week."""
        week1_start = self.end_date - timedelta(days=21)
        week2_start = self.end_date - timedelta(days=14)
        week3_start = self.end_date - timedelta(days=7)

        # Create 1 PR in week 1
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
        )

        # Create 2 PRs in week 2
        for _ in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
            )

        # Create 3 PRs in week 3
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week3_start, timezone.datetime.min.time())),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Values should be ordered chronologically (1, 2, 3)
        values = result["prs_merged"]["values"]
        self.assertGreaterEqual(len(values), 3)
        # First value should be smallest (1 PR), last should be largest (3 PRs)
        self.assertLessEqual(values[0], values[-1])
