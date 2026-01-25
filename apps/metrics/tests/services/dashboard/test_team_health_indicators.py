"""Tests for Team Health Indicators service function.

TDD RED Phase: These tests define the expected behavior for get_team_health_indicators().
Tests should FAIL initially until the function is implemented.
"""

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


class TestHealthIndicatorsStructure(TestCase):
    """Tests for the structure of get_team_health_indicators response."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=7)
        cls.end_date = cls.today

    def test_returns_all_five_indicators(self):
        """Test that the function returns all five expected indicator keys."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        expected_keys = {
            "throughput",
            "cycle_time",
            "quality",
            "review_bottleneck",
            "ai_adoption",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_each_indicator_has_value_trend_status(self):
        """Test that throughput, cycle_time, quality, ai_adoption have value/trend/status."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        # Standard indicators should have value, trend, status
        for key in ["throughput", "cycle_time", "quality", "ai_adoption"]:
            indicator = result[key]
            self.assertIn("value", indicator, f"{key} should have 'value'")
            self.assertIn("trend", indicator, f"{key} should have 'trend'")
            self.assertIn("status", indicator, f"{key} should have 'status'")

        # review_bottleneck has different structure
        bottleneck = result["review_bottleneck"]
        self.assertIn("detected", bottleneck)
        self.assertIn("reviewer", bottleneck)
        self.assertIn("status", bottleneck)


class TestThroughputIndicator(TestCase):
    """Tests for throughput indicator (PRs merged per week)."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=7)
        cls.end_date = cls.today

    def test_throughput_green_when_high_pr_count(self):
        """Test throughput status is green when >= 5 PRs merged per week."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create 6 merged PRs in the date range (> 5 threshold)
        for i in range(6):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i % 7),
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["throughput"]["status"], "green")
        self.assertGreaterEqual(result["throughput"]["value"], 5.0)

    def test_throughput_yellow_when_moderate_pr_count(self):
        """Test throughput status is yellow when 3-4 PRs merged per week."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create 4 merged PRs in the date range (between 3-5 threshold)
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["throughput"]["status"], "yellow")
        self.assertGreaterEqual(result["throughput"]["value"], 3.0)
        self.assertLess(result["throughput"]["value"], 5.0)

    def test_throughput_red_when_low_pr_count(self):
        """Test throughput status is red when < 3 PRs merged per week."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create only 2 merged PRs in the date range (< 3 threshold)
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["throughput"]["status"], "red")
        self.assertLess(result["throughput"]["value"], 3.0)


class TestCycleTimeIndicator(TestCase):
    """Tests for cycle time indicator (hours from PR open to merge)."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=7)
        cls.end_date = cls.today

    def test_cycle_time_green_when_fast(self):
        """Test cycle time status is green when <= 24 hours."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create PRs with fast cycle time (20 hours)
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
                cycle_time_hours=Decimal("20.0"),
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["cycle_time"]["status"], "green")
        self.assertLessEqual(result["cycle_time"]["value"], 24.0)

    def test_cycle_time_yellow_when_moderate(self):
        """Test cycle time status is yellow when 24-72 hours."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create PRs with moderate cycle time (48 hours)
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
                cycle_time_hours=Decimal("48.0"),
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["cycle_time"]["status"], "yellow")
        self.assertGreater(result["cycle_time"]["value"], 24.0)
        self.assertLessEqual(result["cycle_time"]["value"], 72.0)

    def test_cycle_time_red_when_slow(self):
        """Test cycle time status is red when > 72 hours."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create PRs with slow cycle time (96 hours)
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
                cycle_time_hours=Decimal("96.0"),
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["cycle_time"]["status"], "red")
        self.assertGreater(result["cycle_time"]["value"], 72.0)


class TestQualityIndicator(TestCase):
    """Tests for quality indicator (revert rate percentage)."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=7)
        cls.end_date = cls.today

    def test_quality_green_when_low_revert_rate(self):
        """Test quality status is green when revert rate <= 2%."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create 100 PRs with only 1 revert (1% revert rate)
        for i in range(99):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i % 7),
                is_revert=False,
            )
        # 1 revert PR
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=1),
            is_revert=True,
        )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["quality"]["status"], "green")
        self.assertLessEqual(result["quality"]["value"], 2.0)

    def test_quality_yellow_when_moderate_revert_rate(self):
        """Test quality status is yellow when revert rate is 2-5%."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create 100 PRs with 4 reverts (4% revert rate)
        for i in range(96):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i % 7),
                is_revert=False,
            )
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
                is_revert=True,
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["quality"]["status"], "yellow")
        self.assertGreater(result["quality"]["value"], 2.0)
        self.assertLessEqual(result["quality"]["value"], 5.0)

    def test_quality_red_when_high_revert_rate(self):
        """Test quality status is red when revert rate > 5%."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create 10 PRs with 1 revert (10% revert rate)
        for i in range(9):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i % 7),
                is_revert=False,
            )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=1),
            is_revert=True,
        )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["quality"]["status"], "red")
        self.assertGreater(result["quality"]["value"], 5.0)


class TestReviewBottleneckIndicator(TestCase):
    """Tests for review bottleneck detection."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=7)
        cls.end_date = cls.today

    def test_bottleneck_detected_when_reviewer_overloaded(self):
        """Test bottleneck is detected when one reviewer has > 50% of reviews."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create reviewers
        overloaded_reviewer = TeamMemberFactory(team=self.team, display_name="Overloaded Dev")
        other_reviewer = TeamMemberFactory(team=self.team, display_name="Other Dev")
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Create 10 PRs - overloaded reviewer has 8 reviews, other has 2
        for i in range(8):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i % 7),
            )
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=overloaded_reviewer,
                state="approved",
            )

        for i in range(2):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
            )
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=other_reviewer,
                state="approved",
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertTrue(result["review_bottleneck"]["detected"])
        self.assertEqual(result["review_bottleneck"]["reviewer"], "Overloaded Dev")
        self.assertEqual(result["review_bottleneck"]["status"], "red")

    def test_bottleneck_not_detected_when_balanced(self):
        """Test no bottleneck when reviews are evenly distributed."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create reviewers
        reviewer1 = TeamMemberFactory(team=self.team, display_name="Dev 1")
        reviewer2 = TeamMemberFactory(team=self.team, display_name="Dev 2")
        reviewer3 = TeamMemberFactory(team=self.team, display_name="Dev 3")
        author = TeamMemberFactory(team=self.team, display_name="Author")

        reviewers = [reviewer1, reviewer2, reviewer3]

        # Create 9 PRs - evenly distributed reviews (3 each)
        for i in range(9):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i % 7),
            )
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=reviewers[i % 3],
                state="approved",
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertFalse(result["review_bottleneck"]["detected"])
        self.assertIsNone(result["review_bottleneck"]["reviewer"])
        self.assertEqual(result["review_bottleneck"]["status"], "green")


class TestAIAdoptionIndicator(TestCase):
    """Tests for AI adoption indicator (percentage of AI-assisted PRs)."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=7)
        cls.end_date = cls.today

    def test_ai_adoption_green_when_high(self):
        """Test AI adoption status is green when >= 30%."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create 10 PRs with 4 AI-assisted (40% adoption)
        for i in range(6):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i % 7),
                is_ai_assisted=False,
            )
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
                is_ai_assisted=True,
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_adoption"]["status"], "green")
        self.assertGreaterEqual(result["ai_adoption"]["value"], 30.0)

    def test_ai_adoption_yellow_when_moderate(self):
        """Test AI adoption status is yellow when 10-30%."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create 10 PRs with 2 AI-assisted (20% adoption)
        for i in range(8):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i % 7),
                is_ai_assisted=False,
            )
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
                is_ai_assisted=True,
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_adoption"]["status"], "yellow")
        self.assertGreaterEqual(result["ai_adoption"]["value"], 10.0)
        self.assertLess(result["ai_adoption"]["value"], 30.0)

    def test_ai_adoption_red_when_low(self):
        """Test AI adoption status is red when < 10%."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Create 20 PRs with only 1 AI-assisted (5% adoption)
        for i in range(19):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i % 7),
                is_ai_assisted=False,
            )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=1),
            is_ai_assisted=True,
        )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_adoption"]["status"], "red")
        self.assertLess(result["ai_adoption"]["value"], 10.0)


class TestTrendCalculation(TestCase):
    """Tests for trend calculation (up/down/stable compared to previous period)."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)
        cls.today = date.today()
        # Current period: last 7 days
        cls.start_date = cls.today - timedelta(days=7)
        cls.end_date = cls.today

    def test_throughput_trend_up_when_increased(self):
        """Test throughput trend is 'up' when current period has more PRs than previous."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Previous period (days 8-14): 2 PRs
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=10 + i),
            )

        # Current period (days 0-7): 6 PRs
        for i in range(6):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["throughput"]["trend"], "up")

    def test_throughput_trend_down_when_decreased(self):
        """Test throughput trend is 'down' when current period has fewer PRs than previous."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Previous period (days 8-14): 8 PRs
        for i in range(8):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=10 + i % 7),
            )

        # Current period (days 0-7): 2 PRs
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["throughput"]["trend"], "down")

    def test_throughput_trend_stable_when_similar(self):
        """Test throughput trend is 'stable' when current and previous periods are similar."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # Previous period (days 8-14): 5 PRs
        for i in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=10 + i % 7),
            )

        # Current period (days 0-7): 5 PRs
        for i in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.now() - timedelta(days=i),
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        self.assertEqual(result["throughput"]["trend"], "stable")


class TestEdgeCases(TestCase):
    """Tests for edge cases and empty data scenarios."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=7)
        cls.end_date = cls.today

    def test_handles_no_data_gracefully(self):
        """Test that function handles empty data without errors."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        # No PRs, no reviews, no AI usage

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        # Should return valid structure with zero/default values
        self.assertIn("throughput", result)
        self.assertIn("cycle_time", result)
        self.assertIn("quality", result)
        self.assertIn("review_bottleneck", result)
        self.assertIn("ai_adoption", result)

        # Throughput should be 0 with red status
        self.assertEqual(result["throughput"]["value"], 0.0)
        self.assertEqual(result["throughput"]["status"], "red")

    def test_handles_only_open_prs(self):
        """Test that function only counts merged PRs for throughput."""
        from apps.metrics.services.dashboard.velocity_metrics import (
            get_team_health_indicators,
        )

        member = TeamMemberFactory(team=self.team)

        # Create only open PRs (not merged)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=member,
                state="open",
                merged_at=None,
            )

        result = get_team_health_indicators(self.team, self.start_date, self.end_date)

        # Throughput should be 0 since no PRs were merged
        self.assertEqual(result["throughput"]["value"], 0.0)
        self.assertEqual(result["throughput"]["status"], "red")
