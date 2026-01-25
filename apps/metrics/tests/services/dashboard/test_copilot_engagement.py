"""Tests for Copilot Engagement Dashboard service function.

TDD RED Phase: These tests define the expected behavior for get_copilot_engagement_summary().
Tests should FAIL initially until the function is implemented.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    AIUsageDailyFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.models import CopilotLanguageDaily


class TestGetCopilotEngagementSummary(TestCase):
    """Tests for get_copilot_engagement_summary function."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=30)
        cls.end_date = cls.today

    def test_returns_expected_keys(self):
        """Test that the function returns all expected keys in the response dict."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        expected_keys = {
            "suggestions_accepted",
            "lines_of_code_accepted",
            "acceptance_rate",
            "active_copilot_users",
            "cycle_time_with_copilot",
            "cycle_time_without_copilot",
            "review_time_with_copilot",
            "review_time_without_copilot",
            "sample_sufficient",
            "acceptance_rate_trend",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_handles_zero_copilot_users(self):
        """Test that the function handles division by zero when no Copilot users exist."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        # Create a team member without any Copilot usage
        member = TeamMemberFactory(team=self.team)

        # Create PRs from this member (no Copilot activity)
        PullRequestFactory.create_batch(
            5,
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("8.0"),
        )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        # Should not raise division by zero error
        self.assertEqual(result["suggestions_accepted"], 0)
        self.assertEqual(result["lines_of_code_accepted"], 0)
        self.assertEqual(result["acceptance_rate"], Decimal("0.00"))
        self.assertEqual(result["active_copilot_users"], 0)
        # Cycle time with Copilot should be None since no Copilot users
        self.assertIsNone(result["cycle_time_with_copilot"])
        self.assertIsNone(result["review_time_with_copilot"])


class TestSampleSufficientLogic(TestCase):
    """Tests for sample_sufficient field logic."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=30)
        cls.end_date = cls.today

    def test_sample_sufficient_when_enough_prs(self):
        """Test that sample_sufficient is True when both groups have >= 10 PRs."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        # Create Copilot user with activity
        copilot_member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=copilot_member,
            source="copilot",
            date=self.today - timedelta(days=5),
            suggestions_shown=100,
            suggestions_accepted=30,
        )

        # Create non-Copilot user
        non_copilot_member = TeamMemberFactory(team=self.team)

        # Create 10 PRs from Copilot user
        PullRequestFactory.create_batch(
            10,
            team=self.team,
            author=copilot_member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("20.0"),
            review_time_hours=Decimal("5.0"),
        )

        # Create 10 PRs from non-Copilot user
        PullRequestFactory.create_batch(
            10,
            team=self.team,
            author=non_copilot_member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("30.0"),
            review_time_hours=Decimal("10.0"),
        )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        self.assertTrue(result["sample_sufficient"])

    def test_sample_insufficient_when_few_prs(self):
        """Test that sample_sufficient is False when either group has < 10 PRs."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        # Create Copilot user with activity
        copilot_member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=copilot_member,
            source="copilot",
            date=self.today - timedelta(days=5),
            suggestions_shown=100,
            suggestions_accepted=30,
        )

        # Create non-Copilot user
        non_copilot_member = TeamMemberFactory(team=self.team)

        # Create only 5 PRs from Copilot user (< 10)
        PullRequestFactory.create_batch(
            5,
            team=self.team,
            author=copilot_member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("20.0"),
            review_time_hours=Decimal("5.0"),
        )

        # Create 15 PRs from non-Copilot user (>= 10)
        PullRequestFactory.create_batch(
            15,
            team=self.team,
            author=non_copilot_member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("30.0"),
            review_time_hours=Decimal("10.0"),
        )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        self.assertFalse(result["sample_sufficient"])


class TestLinesOfCodeCalculation(TestCase):
    """Tests for lines_of_code_accepted calculation from CopilotLanguageDaily."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=30)
        cls.end_date = cls.today

    def test_calculates_lines_of_code_from_language_daily(self):
        """Test that lines_of_code_accepted is summed from CopilotLanguageDaily.lines_accepted."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        # Create CopilotLanguageDaily records with lines_accepted
        CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today - timedelta(days=5),
            language="Python",
            suggestions_shown=100,
            suggestions_accepted=30,
            lines_suggested=500,
            lines_accepted=150,
        )
        CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today - timedelta(days=4),
            language="TypeScript",
            suggestions_shown=80,
            suggestions_accepted=20,
            lines_suggested=400,
            lines_accepted=100,
        )
        CopilotLanguageDaily.objects.create(
            team=self.team,
            date=self.today - timedelta(days=3),
            language="Python",
            suggestions_shown=60,
            suggestions_accepted=15,
            lines_suggested=300,
            lines_accepted=75,
        )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        # Total lines_accepted = 150 + 100 + 75 = 325
        self.assertEqual(result["lines_of_code_accepted"], 325)

    def test_lines_of_code_zero_when_no_language_data(self):
        """Test that lines_of_code_accepted is 0 when no CopilotLanguageDaily data exists."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        # No CopilotLanguageDaily records created

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        self.assertEqual(result["lines_of_code_accepted"], 0)


class TestAcceptanceRateTrend(TestCase):
    """Tests for acceptance_rate_trend calculation."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=30)
        cls.end_date = cls.today

    def test_calculates_acceptance_rate_trend_up(self):
        """Test that acceptance_rate_trend is 'up' when rate increased vs previous period."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        member = TeamMemberFactory(team=self.team)

        # Previous period (days 31-60): lower acceptance rate
        for i in range(35, 45):
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                source="copilot",
                date=self.today - timedelta(days=i),
                suggestions_shown=100,
                suggestions_accepted=20,  # 20% acceptance
            )

        # Current period (days 0-30): higher acceptance rate
        for i in range(5, 15):
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                source="copilot",
                date=self.today - timedelta(days=i),
                suggestions_shown=100,
                suggestions_accepted=40,  # 40% acceptance
            )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        self.assertEqual(result["acceptance_rate_trend"], "up")

    def test_calculates_acceptance_rate_trend_down(self):
        """Test that acceptance_rate_trend is 'down' when rate decreased vs previous period."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        member = TeamMemberFactory(team=self.team)

        # Previous period (days 31-60): higher acceptance rate
        for i in range(35, 45):
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                source="copilot",
                date=self.today - timedelta(days=i),
                suggestions_shown=100,
                suggestions_accepted=50,  # 50% acceptance
            )

        # Current period (days 0-30): lower acceptance rate
        for i in range(5, 15):
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                source="copilot",
                date=self.today - timedelta(days=i),
                suggestions_shown=100,
                suggestions_accepted=25,  # 25% acceptance
            )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        self.assertEqual(result["acceptance_rate_trend"], "down")

    def test_calculates_acceptance_rate_trend_stable(self):
        """Test that acceptance_rate_trend is 'stable' when rate is similar to previous period."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        member = TeamMemberFactory(team=self.team)

        # Previous period (days 31-60): ~30% acceptance
        for i in range(35, 45):
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                source="copilot",
                date=self.today - timedelta(days=i),
                suggestions_shown=100,
                suggestions_accepted=30,  # 30% acceptance
            )

        # Current period (days 0-30): ~31% acceptance (within threshold)
        for i in range(5, 15):
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                source="copilot",
                date=self.today - timedelta(days=i),
                suggestions_shown=100,
                suggestions_accepted=31,  # 31% acceptance
            )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        self.assertEqual(result["acceptance_rate_trend"], "stable")

    def test_trend_stable_when_no_previous_data(self):
        """Test that acceptance_rate_trend is 'stable' when no previous period data exists."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        member = TeamMemberFactory(team=self.team)

        # Only current period data (no previous period)
        for i in range(5, 15):
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                source="copilot",
                date=self.today - timedelta(days=i),
                suggestions_shown=100,
                suggestions_accepted=35,
            )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        # Should be 'stable' when there's no baseline to compare
        self.assertEqual(result["acceptance_rate_trend"], "stable")


class TestCycleTimeComparison(TestCase):
    """Tests for cycle time comparison between Copilot and non-Copilot users."""

    @classmethod
    def setUpTestData(cls):
        """Set up read-only test fixtures shared across all test methods."""
        cls.team = TeamFactory()
        cls.today = date.today()
        cls.start_date = cls.today - timedelta(days=30)
        cls.end_date = cls.today

    def test_calculates_cycle_time_with_and_without_copilot(self):
        """Test that cycle times are calculated separately for Copilot and non-Copilot users."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        # Create Copilot user with activity
        copilot_member = TeamMemberFactory(team=self.team)
        AIUsageDailyFactory(
            team=self.team,
            member=copilot_member,
            source="copilot",
            date=self.today - timedelta(days=5),
            suggestions_shown=100,
            suggestions_accepted=30,
        )

        # Create non-Copilot user
        non_copilot_member = TeamMemberFactory(team=self.team)

        # Copilot user PRs: 20 hours cycle time
        PullRequestFactory.create_batch(
            5,
            team=self.team,
            author=copilot_member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("20.0"),
            review_time_hours=Decimal("5.0"),
        )

        # Non-Copilot user PRs: 30 hours cycle time
        PullRequestFactory.create_batch(
            5,
            team=self.team,
            author=non_copilot_member,
            state="merged",
            merged_at=timezone.now() - timedelta(days=5),
            cycle_time_hours=Decimal("30.0"),
            review_time_hours=Decimal("10.0"),
        )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        # Copilot users should have lower cycle time
        self.assertEqual(result["cycle_time_with_copilot"], Decimal("20.00"))
        self.assertEqual(result["cycle_time_without_copilot"], Decimal("30.00"))
        self.assertEqual(result["review_time_with_copilot"], Decimal("5.00"))
        self.assertEqual(result["review_time_without_copilot"], Decimal("10.00"))

    def test_suggestions_accepted_from_ai_usage_daily(self):
        """Test that suggestions_accepted is summed from AIUsageDaily records."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        member = TeamMemberFactory(team=self.team)

        # Create multiple AIUsageDaily records
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            source="copilot",
            date=self.today - timedelta(days=5),
            suggestions_shown=100,
            suggestions_accepted=30,
        )
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            source="copilot",
            date=self.today - timedelta(days=4),
            suggestions_shown=80,
            suggestions_accepted=25,
        )
        AIUsageDailyFactory(
            team=self.team,
            member=member,
            source="copilot",
            date=self.today - timedelta(days=3),
            suggestions_shown=60,
            suggestions_accepted=20,
        )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        # Total suggestions_accepted = 30 + 25 + 20 = 75
        self.assertEqual(result["suggestions_accepted"], 75)
        # Total suggestions_shown = 100 + 80 + 60 = 240
        # Acceptance rate = 75 / 240 * 100 = 31.25%
        self.assertEqual(result["acceptance_rate"], Decimal("31.25"))
        # Active users = 1 (distinct members)
        self.assertEqual(result["active_copilot_users"], 1)

    def test_counts_distinct_active_copilot_users(self):
        """Test that active_copilot_users counts distinct members with Copilot activity."""
        from apps.metrics.services.dashboard.copilot_metrics import (
            get_copilot_engagement_summary,
        )

        # Create 3 members with Copilot activity
        member1 = TeamMemberFactory(team=self.team)
        member2 = TeamMemberFactory(team=self.team)
        member3 = TeamMemberFactory(team=self.team)

        # Multiple records for same member should count as 1
        AIUsageDailyFactory(
            team=self.team,
            member=member1,
            source="copilot",
            date=self.today - timedelta(days=5),
        )
        AIUsageDailyFactory(
            team=self.team,
            member=member1,
            source="copilot",
            date=self.today - timedelta(days=4),
        )
        AIUsageDailyFactory(
            team=self.team,
            member=member2,
            source="copilot",
            date=self.today - timedelta(days=5),
        )
        AIUsageDailyFactory(
            team=self.team,
            member=member3,
            source="copilot",
            date=self.today - timedelta(days=5),
        )

        result = get_copilot_engagement_summary(self.team, self.start_date, self.end_date)

        self.assertEqual(result["active_copilot_users"], 3)
