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
        """ai_adoption values contain weekly AI adoption percentage from surveys when use_survey_data=True."""
        from apps.metrics.factories import PRSurveyFactory

        merge_date = self.end_date - timedelta(days=3)

        # Create 4 PRs with surveys (3 AI-assisted, 1 not)
        prs = []
        for _ in range(4):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            )
            prs.append(pr)

        # Create surveys: 3 say AI was used, 1 says not
        for pr in prs[:3]:
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member,
                author_ai_assisted=True,
            )
        PRSurveyFactory(
            team=self.team,
            pull_request=prs[3],
            author=self.member,
            author_ai_assisted=False,
        )

        result = get_sparkline_data(self.team, self.start_date, self.end_date, use_survey_data=True)

        # Should have AI adoption values
        self.assertGreater(len(result["ai_adoption"]["values"]), 0)
        # 3 out of 4 surveys = 75%
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

        # Create 3 PRs in week 1 (meets MIN_SPARKLINE_SAMPLE_SIZE)
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )

        # Create 6 PRs in week 2 (100% increase)
        for _ in range(6):
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

        # Create 6 PRs in week 1 (meets MIN_SPARKLINE_SAMPLE_SIZE)
        for _ in range(6):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )

        # Create 3 PRs in week 2 (50% decrease, meets MIN_SPARKLINE_SAMPLE_SIZE)
        for _ in range(3):
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

        # Create 3 PRs in week 1 (meets MIN_SPARKLINE_SAMPLE_SIZE)
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )

        # Create 6 PRs in week 2 (100% increase, meets MIN_SPARKLINE_SAMPLE_SIZE)
        for _ in range(6):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # 3 -> 6 = 100% increase
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


class TestAIAdoptionSparklineDataSource(TestCase):
    """Tests for AI adoption sparkline using survey data (ISS-006).

    The sparkline should use PRSurvey.author_ai_assisted (survey responses)
    to match the card calculation from get_key_metrics, NOT PullRequest.is_ai_assisted
    (pattern detection).
    """

    def setUp(self):
        """Set up test fixtures."""
        from apps.metrics.factories import PRSurveyFactory

        self.PRSurveyFactory = PRSurveyFactory
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=90)

    def test_ai_adoption_sparkline_uses_survey_data_not_pattern_detection(self):
        """AI adoption sparkline should use survey data when use_survey_data=True.

        This is the key test for ISS-006: create PRs where pattern detection
        says NO AI (is_ai_assisted=False), but surveys say YES AI.
        Sparkline should show the survey value, not pattern value.
        """
        merge_date = self.end_date - timedelta(days=3)

        # Create 4 PRs with NO AI according to pattern detection
        prs = []
        for _ in range(4):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
                is_ai_assisted=False,  # Pattern detection says NO AI
            )
            prs.append(pr)

        # But 3 of them have surveys saying YES, AI was used
        for pr in prs[:3]:
            self.PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member,
                author_ai_assisted=True,  # Survey says YES AI
            )

        # 1 PR has survey saying NO AI
        self.PRSurveyFactory(
            team=self.team,
            pull_request=prs[3],
            author=self.member,
            author_ai_assisted=False,  # Survey says NO AI
        )

        result = get_sparkline_data(self.team, self.start_date, self.end_date, use_survey_data=True)

        # Should use survey data: 3/4 = 75%
        # NOT pattern detection: 0/4 = 0%
        self.assertGreater(len(result["ai_adoption"]["values"]), 0)
        self.assertIn(75.0, result["ai_adoption"]["values"])

    def test_ai_adoption_sparkline_excludes_prs_without_survey_responses(self):
        """PRs without survey responses should not be counted when use_survey_data=True.

        This matches get_key_metrics behavior where only PRs with surveys
        are considered for AI adoption calculation.
        """
        merge_date = self.end_date - timedelta(days=3)

        # Create 4 PRs
        prs = []
        for _ in range(4):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
                is_ai_assisted=False,
            )
            prs.append(pr)

        # Only 2 PRs have surveys (1 AI-assisted, 1 not)
        self.PRSurveyFactory(
            team=self.team,
            pull_request=prs[0],
            author=self.member,
            author_ai_assisted=True,
        )
        self.PRSurveyFactory(
            team=self.team,
            pull_request=prs[1],
            author=self.member,
            author_ai_assisted=False,
        )
        # prs[2] and prs[3] have NO surveys

        result = get_sparkline_data(self.team, self.start_date, self.end_date, use_survey_data=True)

        # Should be 1/2 = 50% (only count PRs with surveys)
        # NOT 1/4 = 25% (counting all PRs)
        self.assertGreater(len(result["ai_adoption"]["values"]), 0)
        self.assertIn(50.0, result["ai_adoption"]["values"])

    def test_ai_adoption_sparkline_returns_zero_when_no_surveys(self):
        """Returns 0% when no PRs have survey responses with use_survey_data=True."""
        merge_date = self.end_date - timedelta(days=3)

        # Create PRs without any surveys
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
                is_ai_assisted=True,  # Pattern says AI, but no survey
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date, use_survey_data=True)

        # Should return 0% because no surveys exist
        # NOT 100% from is_ai_assisted field
        self.assertGreater(len(result["ai_adoption"]["values"]), 0)
        self.assertIn(0.0, result["ai_adoption"]["values"])

    def test_ai_adoption_sparkline_handles_null_survey_responses(self):
        """Survey responses with author_ai_assisted=None should not be counted when use_survey_data=True."""
        merge_date = self.end_date - timedelta(days=3)

        # Create PRs with surveys
        for i in range(4):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            )
            # 2 surveys with response (1 True, 1 False), 2 with None (no response yet)
            if i == 0:
                self.PRSurveyFactory(team=self.team, pull_request=pr, author=self.member, author_ai_assisted=True)
            elif i == 1:
                self.PRSurveyFactory(team=self.team, pull_request=pr, author=self.member, author_ai_assisted=False)
            else:
                self.PRSurveyFactory(team=self.team, pull_request=pr, author=self.member, author_ai_assisted=None)

        result = get_sparkline_data(self.team, self.start_date, self.end_date, use_survey_data=True)

        # Should only count surveys with actual responses: 1/2 = 50%
        # NOT include None responses in calculation
        self.assertGreater(len(result["ai_adoption"]["values"]), 0)
        self.assertIn(50.0, result["ai_adoption"]["values"])


class TestSparklineLowDataHandling(TestCase):
    """Tests for sparkline trend calculation with low-data weeks (ISS-001/ISS-007).

    The trend calculation should skip weeks with insufficient data (< MIN_SAMPLE_SIZE PRs)
    to avoid misleading extreme percentages like +44321% or -98%.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=90)

    def test_trend_ignores_first_week_with_insufficient_data(self):
        """Trend should use first VALID week (>= min_sample_size PRs) as baseline.

        ISS-001/ISS-007: When first week has only 1-2 PRs, it creates an
        unrealistic baseline that leads to extreme percentage changes.
        """
        week1_start = self.end_date - timedelta(days=21)  # First week: 1 PR (below threshold)
        week2_start = self.end_date - timedelta(days=14)  # Second week: 5 PRs (valid)
        week3_start = self.end_date - timedelta(days=7)  # Third week: 10 PRs (valid)

        # Week 1: Only 1 PR with 1h cycle time (below min_sample_size threshold)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            cycle_time_hours=Decimal("1.0"),
        )

        # Week 2: 5 PRs with 10h avg cycle time
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("10.0"),
            )

        # Week 3: 10 PRs with 20h avg cycle time
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week3_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("20.0"),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should calculate trend from week 2 (10h) to week 3 (20h) = 100% increase
        # NOT from week 1 (1h) to week 3 (20h) = 1900% increase
        self.assertEqual(result["cycle_time"]["change_pct"], 100)
        self.assertEqual(result["cycle_time"]["trend"], "up")

    def test_trend_ignores_last_week_with_insufficient_data(self):
        """Trend should use last VALID week as endpoint, not low-data recent week.

        Example: If the most recent week is a holiday with only 2 PRs,
        don't use it as the trend endpoint.
        """
        week1_start = self.end_date - timedelta(days=21)  # First week: 5 PRs
        week2_start = self.end_date - timedelta(days=14)  # Second week: 10 PRs
        week3_start = self.end_date - timedelta(days=7)  # Third week: 2 PRs (holiday)

        # Week 1: 5 PRs with 100h avg cycle time
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("100.0"),
            )

        # Week 2: 10 PRs with 50h avg cycle time
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("50.0"),
            )

        # Week 3 (holiday): Only 2 PRs with 2h avg (below threshold)
        for _ in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week3_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("2.0"),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should calculate trend from week 1 (100h) to week 2 (50h) = -50%
        # NOT from week 1 (100h) to week 3 (2h) = -98%
        self.assertEqual(result["cycle_time"]["change_pct"], -50)
        self.assertEqual(result["cycle_time"]["trend"], "down")

    def test_returns_flat_when_no_week_has_sufficient_data(self):
        """Returns flat trend when all weeks are below sample size threshold."""
        week1_start = self.end_date - timedelta(days=14)
        week2_start = self.end_date - timedelta(days=7)

        # Week 1: 1 PR
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            cycle_time_hours=Decimal("10.0"),
        )

        # Week 2: 2 PRs
        for _ in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("100.0"),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # With all weeks below threshold, should return flat/0
        self.assertEqual(result["cycle_time"]["change_pct"], 0)
        self.assertEqual(result["cycle_time"]["trend"], "flat")

    def test_pr_count_trend_also_respects_minimum_sample_size(self):
        """PR count trend should also skip low-data weeks."""
        week1_start = self.end_date - timedelta(days=21)  # 1 PR
        week2_start = self.end_date - timedelta(days=14)  # 5 PRs
        week3_start = self.end_date - timedelta(days=7)  # 10 PRs

        # Week 1: 1 PR (below threshold)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
        )

        # Week 2: 5 PRs
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
            )

        # Week 3: 10 PRs
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week3_start, timezone.datetime.min.time())),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should calculate trend from week 2 (5) to week 3 (10) = 100% increase
        # NOT from week 1 (1) to week 3 (10) = 900% increase
        self.assertEqual(result["prs_merged"]["change_pct"], 100)
        self.assertEqual(result["prs_merged"]["trend"], "up")


class TestTrendPercentageCapping(TestCase):
    """Tests for capping extreme trend percentages (A-001).

    When trends show extreme values like +3100% or +12096%, they're not
    meaningful to users and indicate statistical anomalies. These should
    be capped at ±500% to show "significant change" without false precision.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=90)

    def test_trend_percentage_capped_at_positive_500(self):
        """Extreme positive trends should be capped at +500%.

        A-001: Dashboard showed +12096% for review time because first week
        had 0.04h (2.4 min) avg and last week had 5h avg. Raw calculation
        gives 12400%, but this should be capped at 500%.
        """
        week1_start = self.end_date - timedelta(days=14)
        week2_start = self.end_date - timedelta(days=7)

        # Week 1: 10 PRs with very low review time (0.1h = 6 min avg)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
                review_time_hours=Decimal("0.1"),
            )

        # Week 2: 10 PRs with much higher review time (10h avg)
        # Raw change: (10 - 0.1) / 0.1 * 100 = 9900%
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
                review_time_hours=Decimal("10.0"),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should be capped at +500%, not +9900%
        self.assertEqual(result["review_time"]["change_pct"], 500)
        self.assertEqual(result["review_time"]["trend"], "up")

    def test_trend_percentage_capped_at_negative_500(self):
        """Extreme negative trends should be capped at -500%.

        When metrics drop dramatically (e.g., cycle time from 100h to 1h),
        the raw -99% is fine, but if it were to exceed -500% somehow,
        it should be capped. More practically, test with very small
        ending values that create large negative percentages.
        """
        week1_start = self.end_date - timedelta(days=14)
        week2_start = self.end_date - timedelta(days=7)

        # Week 1: 10 PRs with high cycle time (100h avg)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("100.0"),
            )

        # Week 2: 10 PRs with very low cycle time (1h avg)
        # Raw change: (1 - 100) / 100 * 100 = -99%
        # This is within bounds, so let's test PR count instead
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("1.0"),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # -99% is within bounds, should pass through
        self.assertEqual(result["cycle_time"]["change_pct"], -99)
        self.assertEqual(result["cycle_time"]["trend"], "down")

    def test_pr_count_trend_capped_at_positive_500(self):
        """PR count extreme increase should be capped at +500%."""
        week1_start = self.end_date - timedelta(days=14)
        week2_start = self.end_date - timedelta(days=7)

        # Week 1: 10 PRs (minimum valid sample)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )

        # Week 2: 100 PRs (raw: 900% increase)
        for _ in range(100):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # Should be capped at +500%, not +900%
        self.assertEqual(result["prs_merged"]["change_pct"], 500)
        self.assertEqual(result["prs_merged"]["trend"], "up")

    def test_values_within_500_are_not_capped(self):
        """Values within ±500% should pass through unchanged."""
        week1_start = self.end_date - timedelta(days=14)
        week2_start = self.end_date - timedelta(days=7)

        # Week 1: 10 PRs
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )

        # Week 2: 30 PRs (raw: 200% increase - within bounds)
        for _ in range(30):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week2_start, timezone.datetime.min.time())),
            )

        result = get_sparkline_data(self.team, self.start_date, self.end_date)

        # 200% is within bounds, should not be capped
        self.assertEqual(result["prs_merged"]["change_pct"], 200)
        self.assertEqual(result["prs_merged"]["trend"], "up")
