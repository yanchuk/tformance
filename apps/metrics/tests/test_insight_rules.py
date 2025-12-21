"""
Tests for Insight Rules - trend detection rules for AI adoption and cycle time.

Tests the following rules:
- AIAdoptionTrendRule: Detects changes in AI adoption percentage
- CycleTimeTrendRule: Detects improvements/regressions in cycle time
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PRSurveyFactory, PullRequestFactory, TeamFactory, TeamMemberFactory


class TestAIAdoptionTrendRule(TestCase):
    """Tests for AIAdoptionTrendRule."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.target_date = date(2024, 2, 1)

    def test_ai_adoption_increase_above_threshold_generates_insight(self):
        """Test that AI adoption increase >= 10% generates an insight."""
        # Create PRs over 4 weeks with increasing AI adoption
        # Week 1 (4 weeks ago): 2/10 PRs AI-assisted = 20%
        week1_start = self.target_date - timedelta(weeks=4)
        for i in range(10):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member,
                author_ai_assisted=i < 2,  # First 2 are AI-assisted
            )

        # Week 4 (1 week ago): 4/10 PRs AI-assisted = 40%
        week4_start = self.target_date - timedelta(weeks=1)
        for i in range(10):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week4_start, timezone.datetime.min.time())),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member,
                author_ai_assisted=i < 4,  # First 4 are AI-assisted
            )

        # Import and run the rule
        from apps.metrics.insights.rules import AIAdoptionTrendRule

        rule = AIAdoptionTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should generate an insight for 20% increase (40% - 20% = 20% >= 10%)
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.category, "trend")
        self.assertEqual(insight.priority, "medium")
        self.assertIn("AI adoption", insight.title)
        self.assertIn("increased", insight.title.lower())
        self.assertEqual(insight.metric_type, "ai_adoption")

    def test_ai_adoption_decrease_above_threshold_generates_insight(self):
        """Test that AI adoption decrease >= 10% generates an insight."""
        # Week 1 (4 weeks ago): 5/10 PRs AI-assisted = 50%
        week1_start = self.target_date - timedelta(weeks=4)
        for i in range(10):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member,
                author_ai_assisted=i < 5,  # First 5 are AI-assisted
            )

        # Week 4 (1 week ago): 3/10 PRs AI-assisted = 30%
        week4_start = self.target_date - timedelta(weeks=1)
        for i in range(10):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week4_start, timezone.datetime.min.time())),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member,
                author_ai_assisted=i < 3,  # First 3 are AI-assisted
            )

        from apps.metrics.insights.rules import AIAdoptionTrendRule

        rule = AIAdoptionTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should generate an insight for 20% decrease (30% - 50% = -20% <= -10%)
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.category, "trend")
        self.assertEqual(insight.priority, "medium")
        self.assertIn("AI adoption", insight.title)
        self.assertIn("decreased", insight.title.lower())

    def test_ai_adoption_change_below_threshold_no_insight(self):
        """Test that AI adoption change < 10% does not generate an insight."""
        # Week 1: 4/10 PRs AI-assisted = 40%
        week1_start = self.target_date - timedelta(weeks=4)
        for i in range(10):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member,
                author_ai_assisted=i < 4,
            )

        # Week 4: 4.5/10 PRs AI-assisted = 45% (5% increase, below 10% threshold)
        week4_start = self.target_date - timedelta(weeks=1)
        for i in range(10):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week4_start, timezone.datetime.min.time())),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member,
                author_ai_assisted=i < 4 or i == 9,  # 5 out of 10
            )

        from apps.metrics.insights.rules import AIAdoptionTrendRule

        rule = AIAdoptionTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (change < 10%)
        self.assertEqual(len(insights), 0)

    def test_ai_adoption_no_data_no_insight(self):
        """Test that no data returns no insight."""
        from apps.metrics.insights.rules import AIAdoptionTrendRule

        rule = AIAdoptionTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 0)

    def test_ai_adoption_single_week_no_insight(self):
        """Test that a single week of data returns no insight (need at least 2 weeks for trend)."""
        # Only one week of data
        week1_start = self.target_date - timedelta(weeks=1)
        for i in range(10):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member,
                author_ai_assisted=i < 5,
            )

        from apps.metrics.insights.rules import AIAdoptionTrendRule

        rule = AIAdoptionTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (need at least 2 weeks for trend)
        self.assertEqual(len(insights), 0)


class TestCycleTimeTrendRule(TestCase):
    """Tests for CycleTimeTrendRule."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.target_date = date(2024, 2, 1)

    def test_cycle_time_improvement_above_threshold_generates_insight(self):
        """Test that cycle time improvement >= 20% generates an insight."""
        # Week 1 (4 weeks ago): avg cycle time = 60 hours
        week1_start = self.target_date - timedelta(weeks=4)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("60.00"),
            )

        # Week 4 (1 week ago): avg cycle time = 40 hours (33% improvement)
        week4_start = self.target_date - timedelta(weeks=1)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week4_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("40.00"),
            )

        from apps.metrics.insights.rules import CycleTimeTrendRule

        rule = CycleTimeTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should generate an insight for 33% improvement
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.category, "trend")
        self.assertIn("Cycle time", insight.title)
        self.assertIn("improved", insight.title.lower())
        self.assertEqual(insight.metric_type, "cycle_time")

    def test_cycle_time_improvement_is_medium_priority(self):
        """Test that cycle time improvements are medium priority."""
        # Week 1: avg cycle time = 50 hours
        week1_start = self.target_date - timedelta(weeks=4)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("50.00"),
            )

        # Week 4: avg cycle time = 35 hours (30% improvement)
        week4_start = self.target_date - timedelta(weeks=1)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week4_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("35.00"),
            )

        from apps.metrics.insights.rules import CycleTimeTrendRule

        rule = CycleTimeTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].priority, "medium")

    def test_cycle_time_regression_above_threshold_generates_insight(self):
        """Test that cycle time regression >= 20% generates an insight."""
        # Week 1: avg cycle time = 30 hours
        week1_start = self.target_date - timedelta(weeks=4)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("30.00"),
            )

        # Week 4: avg cycle time = 45 hours (50% regression)
        week4_start = self.target_date - timedelta(weeks=1)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week4_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("45.00"),
            )

        from apps.metrics.insights.rules import CycleTimeTrendRule

        rule = CycleTimeTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should generate an insight for regression
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.category, "trend")
        self.assertIn("Cycle time", insight.title)
        self.assertIn("regressed", insight.title.lower())

    def test_cycle_time_regression_is_high_priority(self):
        """Test that cycle time regressions are high priority."""
        # Week 1: avg cycle time = 25 hours
        week1_start = self.target_date - timedelta(weeks=4)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("25.00"),
            )

        # Week 4: avg cycle time = 40 hours (60% regression)
        week4_start = self.target_date - timedelta(weeks=1)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week4_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("40.00"),
            )

        from apps.metrics.insights.rules import CycleTimeTrendRule

        rule = CycleTimeTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].priority, "high")

    def test_cycle_time_change_below_threshold_no_insight(self):
        """Test that cycle time change < 20% does not generate an insight."""
        # Week 1: avg cycle time = 40 hours
        week1_start = self.target_date - timedelta(weeks=4)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week1_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("40.00"),
            )

        # Week 4: avg cycle time = 36 hours (10% improvement, below 20% threshold)
        week4_start = self.target_date - timedelta(weeks=1)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week4_start, timezone.datetime.min.time())),
                cycle_time_hours=Decimal("36.00"),
            )

        from apps.metrics.insights.rules import CycleTimeTrendRule

        rule = CycleTimeTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (change < 20%)
        self.assertEqual(len(insights), 0)

    def test_cycle_time_no_data_no_insight(self):
        """Test that no data returns no insight."""
        from apps.metrics.insights.rules import CycleTimeTrendRule

        rule = CycleTimeTrendRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 0)


class TestHotfixSpikeRule(TestCase):
    """Tests for HotfixSpikeRule."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.target_date = date(2024, 2, 1)

    def test_hotfix_spike_above_3x_generates_insight(self):
        """Test that hotfix spike 3x+ above average generates an insight."""
        # Previous 4 weeks: avg 1.5 hotfixes per week (6 total / 4 weeks)
        # Week -4: 1 hotfix
        week_minus_4 = self.target_date - timedelta(weeks=4)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week_minus_4, timezone.datetime.min.time())),
            is_hotfix=True,
        )

        # Week -3: 2 hotfixes
        week_minus_3 = self.target_date - timedelta(weeks=3)
        for _ in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week_minus_3, timezone.datetime.min.time())),
                is_hotfix=True,
            )

        # Week -2: 2 hotfixes
        week_minus_2 = self.target_date - timedelta(weeks=2)
        for _ in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week_minus_2, timezone.datetime.min.time())),
                is_hotfix=True,
            )

        # Week -1: 1 hotfix
        week_minus_1 = self.target_date - timedelta(weeks=1)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(week_minus_1, timezone.datetime.min.time())),
            is_hotfix=True,
        )

        # Current week: 5 hotfixes (5 / 1.5 = 3.33x above average)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(
                    timezone.datetime.combine(self.target_date, timezone.datetime.min.time())
                ),
                is_hotfix=True,
            )

        from apps.metrics.insights.rules import HotfixSpikeRule

        rule = HotfixSpikeRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should generate an insight
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.category, "anomaly")
        self.assertEqual(insight.priority, "high")
        self.assertIn("Hotfix spike", insight.title)
        self.assertIn("5", insight.title)
        self.assertIn("1.5", insight.title)

    def test_hotfix_spike_below_3x_no_insight(self):
        """Test that hotfix spike below 3x does not generate an insight."""
        # Previous 4 weeks: avg 2.0 hotfixes per week (8 total / 4 weeks)
        for week_offset in range(1, 5):
            week_date = self.target_date - timedelta(weeks=week_offset)
            for _ in range(2):
                PullRequestFactory(
                    team=self.team,
                    author=self.member,
                    state="merged",
                    merged_at=timezone.make_aware(timezone.datetime.combine(week_date, timezone.datetime.min.time())),
                    is_hotfix=True,
                )

        # Current week: 5 hotfixes (5 / 2.0 = 2.5x, below 3x threshold)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(
                    timezone.datetime.combine(self.target_date, timezone.datetime.min.time())
                ),
                is_hotfix=True,
            )

        from apps.metrics.insights.rules import HotfixSpikeRule

        rule = HotfixSpikeRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (below 3x threshold)
        self.assertEqual(len(insights), 0)

    def test_hotfix_no_hotfixes_no_insight(self):
        """Test that no hotfixes returns no insight."""
        # Create some non-hotfix PRs
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(
                    timezone.datetime.combine(self.target_date, timezone.datetime.min.time())
                ),
                is_hotfix=False,
            )

        from apps.metrics.insights.rules import HotfixSpikeRule

        rule = HotfixSpikeRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 0)

    def test_hotfix_spike_is_high_priority(self):
        """Test that hotfix spikes are high priority."""
        # Previous weeks: avg 1.0 hotfix per week
        for week_offset in range(1, 5):
            week_date = self.target_date - timedelta(weeks=week_offset)
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(week_date, timezone.datetime.min.time())),
                is_hotfix=True,
            )

        # Current week: 4 hotfixes (4x above average)
        for _ in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(
                    timezone.datetime.combine(self.target_date, timezone.datetime.min.time())
                ),
                is_hotfix=True,
            )

        from apps.metrics.insights.rules import HotfixSpikeRule

        rule = HotfixSpikeRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].priority, "high")


class TestRevertSpikeRule(TestCase):
    """Tests for RevertSpikeRule."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.target_date = date(2024, 2, 1)

    def test_revert_any_reverts_generates_insight(self):
        """Test that any reverts in the current week generates an insight."""
        # Create 3 reverts in the current week
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(
                    timezone.datetime.combine(self.target_date, timezone.datetime.min.time())
                ),
                is_revert=True,
            )

        # Add some normal PRs
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(
                    timezone.datetime.combine(self.target_date, timezone.datetime.min.time())
                ),
                is_revert=False,
            )

        from apps.metrics.insights.rules import RevertSpikeRule

        rule = RevertSpikeRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should generate an insight
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.category, "anomaly")
        self.assertEqual(insight.priority, "high")
        self.assertIn("3 reverts", insight.title)
        self.assertIn("investigate quality issues", insight.title.lower())

    def test_revert_no_reverts_no_insight(self):
        """Test that no reverts returns no insight."""
        # Create only non-revert PRs
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(
                    timezone.datetime.combine(self.target_date, timezone.datetime.min.time())
                ),
                is_revert=False,
            )

        from apps.metrics.insights.rules import RevertSpikeRule

        rule = RevertSpikeRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (no reverts)
        self.assertEqual(len(insights), 0)

    def test_revert_multiple_reverts_shows_count(self):
        """Test that the insight shows the correct count of reverts."""
        # Create exactly 5 reverts
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(
                    timezone.datetime.combine(self.target_date, timezone.datetime.min.time())
                ),
                is_revert=True,
            )

        from apps.metrics.insights.rules import RevertSpikeRule

        rule = RevertSpikeRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertIn("5 reverts", insights[0].title)

    def test_revert_is_high_priority(self):
        """Test that revert insights are high priority."""
        # Create 1 revert
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(self.target_date, timezone.datetime.min.time())),
            is_revert=True,
        )

        from apps.metrics.insights.rules import RevertSpikeRule

        rule = RevertSpikeRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].priority, "high")


class TestCIFailureRateRule(TestCase):
    """Tests for CIFailureRateRule."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.target_date = date(2024, 2, 1)

    def test_ci_failure_rate_above_threshold_generates_insight(self):
        """Test that CI failure rate > 20% generates an insight."""
        # Create a PR in the current week
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(self.target_date, timezone.datetime.min.time())),
        )

        # Create 10 completed check runs: 3 failures, 7 successes (30% failure rate)
        from apps.metrics.factories import PRCheckRunFactory

        for _ in range(7):
            PRCheckRunFactory(
                team=self.team,
                pull_request=pr,
                status="completed",
                conclusion="success",
            )

        for _ in range(3):
            PRCheckRunFactory(
                team=self.team,
                pull_request=pr,
                status="completed",
                conclusion="failure",
            )

        from apps.metrics.insights.rules import CIFailureRateRule

        rule = CIFailureRateRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should generate an insight (30% > 20%)
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.category, "anomaly")
        self.assertEqual(insight.priority, "medium")
        self.assertIn("CI/CD failure rate", insight.title)
        self.assertIn("30", insight.title)  # 30% failure rate
        self.assertIn("20% threshold", insight.title)

    def test_ci_failure_rate_below_threshold_no_insight(self):
        """Test that CI failure rate <= 20% does not generate an insight."""
        # Create a PR in the current week
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(self.target_date, timezone.datetime.min.time())),
        )

        # Create 10 completed check runs: 2 failures, 8 successes (20% failure rate - at threshold)
        from apps.metrics.factories import PRCheckRunFactory

        for _ in range(8):
            PRCheckRunFactory(
                team=self.team,
                pull_request=pr,
                status="completed",
                conclusion="success",
            )

        for _ in range(2):
            PRCheckRunFactory(
                team=self.team,
                pull_request=pr,
                status="completed",
                conclusion="failure",
            )

        from apps.metrics.insights.rules import CIFailureRateRule

        rule = CIFailureRateRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (20% is at threshold, not above)
        self.assertEqual(len(insights), 0)

    def test_ci_no_runs_no_insight(self):
        """Test that no CI runs returns no insight."""
        # Create a PR with no check runs
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(self.target_date, timezone.datetime.min.time())),
        )

        from apps.metrics.insights.rules import CIFailureRateRule

        rule = CIFailureRateRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 0)

    def test_ci_failure_is_medium_priority(self):
        """Test that CI failure rate insights are medium priority."""
        # Create a PR in the current week
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(self.target_date, timezone.datetime.min.time())),
        )

        # Create check runs with 50% failure rate
        from apps.metrics.factories import PRCheckRunFactory

        for _ in range(5):
            PRCheckRunFactory(
                team=self.team,
                pull_request=pr,
                status="completed",
                conclusion="success",
            )

        for _ in range(5):
            PRCheckRunFactory(
                team=self.team,
                pull_request=pr,
                status="completed",
                conclusion="failure",
            )

        from apps.metrics.insights.rules import CIFailureRateRule

        rule = CIFailureRateRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].priority, "medium")


class TestRedundantReviewerRule(TestCase):
    """Tests for RedundantReviewerRule."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")
        self.member3 = TeamMemberFactory(team=self.team, display_name="Charlie")
        self.target_date = date(2024, 2, 1)

    def test_redundant_reviewer_pair_generates_insight(self):
        """Test that redundant reviewer pairs (95%+ agreement on 10+ PRs) generate insights."""
        from apps.metrics.factories import ReviewerCorrelationFactory

        # Create a redundant pair: 96.67% agreement on 15 PRs (above 95% threshold)
        ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.member1,
            reviewer_2=self.member2,
            prs_reviewed_together=15,
            agreements=15,  # 15/15 = 100% (well above 95% threshold)
            disagreements=0,
        )

        from apps.metrics.insights.rules import RedundantReviewerRule

        rule = RedundantReviewerRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should generate an insight for redundant pair
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.category, "action")
        self.assertEqual(insight.priority, "low")
        self.assertIn("Redundant reviewers", insight.title)
        self.assertIn("Alice", insight.title)
        self.assertIn("Bob", insight.title)

    def test_non_redundant_pair_no_insight(self):
        """Test that non-redundant pairs (below 95% agreement) do not generate insights."""
        from apps.metrics.factories import ReviewerCorrelationFactory

        # Create a non-redundant pair: 60% agreement on 15 PRs
        ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.member1,
            reviewer_2=self.member2,
            prs_reviewed_together=15,
            agreements=9,  # 9/15 = 60%
            disagreements=6,
        )

        from apps.metrics.insights.rules import RedundantReviewerRule

        rule = RedundantReviewerRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (below 95% threshold)
        self.assertEqual(len(insights), 0)

    def test_no_correlations_no_insight(self):
        """Test that no reviewer correlations returns no insight."""
        from apps.metrics.insights.rules import RedundantReviewerRule

        # Don't create any correlations
        rule = RedundantReviewerRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (no correlation data)
        self.assertEqual(len(insights), 0)

    def test_max_3_redundant_pairs_reported(self):
        """Test that at most 3 redundant pairs are reported."""
        from apps.metrics.factories import ReviewerCorrelationFactory

        # Create 5 redundant pairs
        members = [self.member1, self.member2, self.member3]
        members.extend([TeamMemberFactory(team=self.team) for _ in range(2)])

        for i in range(5):
            ReviewerCorrelationFactory(
                team=self.team,
                reviewer_1=members[i],
                reviewer_2=members[(i + 1) % 5],
                prs_reviewed_together=15,
                agreements=15,  # 100% agreement
                disagreements=0,
            )

        from apps.metrics.insights.rules import RedundantReviewerRule

        rule = RedundantReviewerRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should only generate 3 insights (max 3 pairs)
        self.assertEqual(len(insights), 3)

    def test_redundant_is_action_category(self):
        """Test that redundant reviewer insights are in action category."""
        from apps.metrics.factories import ReviewerCorrelationFactory

        ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.member1,
            reviewer_2=self.member2,
            prs_reviewed_together=12,
            agreements=12,  # 100% agreement
            disagreements=0,
        )

        from apps.metrics.insights.rules import RedundantReviewerRule

        rule = RedundantReviewerRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].category, "action")

    def test_redundant_is_low_priority(self):
        """Test that redundant reviewer insights are low priority."""
        from apps.metrics.factories import ReviewerCorrelationFactory

        ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.member1,
            reviewer_2=self.member2,
            prs_reviewed_together=10,
            agreements=10,  # 100% agreement
            disagreements=0,
        )

        from apps.metrics.insights.rules import RedundantReviewerRule

        rule = RedundantReviewerRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].priority, "low")


class TestUnlinkedPRsRule(TestCase):
    """Tests for UnlinkedPRsRule."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.target_date = date(2024, 2, 1)

    def test_unlinked_prs_generates_insight(self):
        """Test that unlinked PRs in the last 2 weeks generate an insight."""
        # Create 10 unlinked PRs in the last 2 weeks
        recent_date = self.target_date - timedelta(weeks=1)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(recent_date, timezone.datetime.min.time())),
                jira_key="",  # No Jira link
            )

        from apps.metrics.insights.rules import UnlinkedPRsRule

        rule = UnlinkedPRsRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should generate an insight
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.category, "action")
        self.assertEqual(insight.priority, "low")
        self.assertIn("PRs missing Jira links", insight.title)

    def test_unlinked_prs_below_threshold_no_insight(self):
        """Test that fewer than 5 unlinked PRs does not generate an insight."""
        # Create 4 unlinked PRs (below the 5+ threshold)
        recent_date = self.target_date - timedelta(weeks=1)
        for _ in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(recent_date, timezone.datetime.min.time())),
                jira_key="",  # No Jira link
            )

        from apps.metrics.insights.rules import UnlinkedPRsRule

        rule = UnlinkedPRsRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (below 5 threshold)
        self.assertEqual(len(insights), 0)

    def test_no_unlinked_prs_no_insight(self):
        """Test that no unlinked PRs returns no insight."""
        # Create PRs with Jira keys (linked)
        recent_date = self.target_date - timedelta(weeks=1)
        for i in range(10):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(recent_date, timezone.datetime.min.time())),
                jira_key=f"PROJ-{i + 100}",  # Has Jira link
            )

        from apps.metrics.insights.rules import UnlinkedPRsRule

        rule = UnlinkedPRsRule()
        insights = rule.evaluate(self.team, self.target_date)

        # Should not generate an insight (all PRs are linked)
        self.assertEqual(len(insights), 0)

    def test_unlinked_shows_count_in_title(self):
        """Test that the insight title shows the count of unlinked PRs."""
        # Create 5 unlinked PRs
        recent_date = self.target_date - timedelta(weeks=1)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(recent_date, timezone.datetime.min.time())),
                jira_key="",
            )

        from apps.metrics.insights.rules import UnlinkedPRsRule

        rule = UnlinkedPRsRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertIn("5", insights[0].title)

    def test_unlinked_is_action_category(self):
        """Test that unlinked PRs insights are in action category."""
        recent_date = self.target_date - timedelta(weeks=1)
        # Create 6 unlinked PRs (above threshold)
        for _ in range(6):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(recent_date, timezone.datetime.min.time())),
                jira_key="",
            )

        from apps.metrics.insights.rules import UnlinkedPRsRule

        rule = UnlinkedPRsRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].category, "action")

    def test_unlinked_is_low_priority(self):
        """Test that unlinked PRs insights are low priority."""
        recent_date = self.target_date - timedelta(weeks=1)
        # Create 7 unlinked PRs (above threshold)
        for _ in range(7):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime.combine(recent_date, timezone.datetime.min.time())),
                jira_key="",
            )

        from apps.metrics.insights.rules import UnlinkedPRsRule

        rule = UnlinkedPRsRule()
        insights = rule.evaluate(self.team, self.target_date)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].priority, "low")
