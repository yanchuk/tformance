"""Tests for get_ai_impact_stats function.

Tests for the dashboard service function that calculates AI impact statistics
comparing AI-assisted vs non-AI-assisted PRs.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetAiImpactStats(TestCase):
    """Tests for get_ai_impact_stats function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team, display_name="Alice Developer")
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_dict_with_required_keys(self):
        """Test that get_ai_impact_stats returns dict with all required keys."""
        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("ai_adoption_pct", result)
        self.assertIn("avg_cycle_with_ai", result)
        self.assertIn("avg_cycle_without_ai", result)
        self.assertIn("cycle_time_difference_pct", result)
        self.assertIn("total_prs", result)
        self.assertIn("ai_prs", result)

    def test_ai_adoption_pct_calculated_correctly(self):
        """Test that AI adoption percentage is correctly calculated (3 AI PRs out of 10 = 30%)."""
        # Create 7 non-AI PRs
        for _ in range(7):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
                is_ai_assisted=False,
                cycle_time_hours=Decimal("24.0"),
            )

        # Create 3 AI-assisted PRs
        for _ in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
                is_ai_assisted=True,
                cycle_time_hours=Decimal("20.0"),
            )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_adoption_pct"], Decimal("30.00"))
        self.assertEqual(result["total_prs"], 10)
        self.assertEqual(result["ai_prs"], 3)

    def test_avg_cycle_with_ai_calculated_correctly(self):
        """Test that average cycle time for AI-assisted PRs is correctly calculated."""
        # Create AI-assisted PRs with different cycle times
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("10.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("20.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("30.0"),
        )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        # Average of 10, 20, 30 = 20
        self.assertEqual(result["avg_cycle_with_ai"], Decimal("20.00"))

    def test_avg_cycle_without_ai_calculated_correctly(self):
        """Test that average cycle time for non-AI PRs is correctly calculated."""
        # Create non-AI PRs with different cycle times
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=False,
            cycle_time_hours=Decimal("24.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_ai_assisted=False,
            cycle_time_hours=Decimal("36.0"),
        )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        # Average of 24, 36 = 30
        self.assertEqual(result["avg_cycle_without_ai"], Decimal("30.00"))

    def test_cycle_time_difference_pct_negative_when_ai_faster(self):
        """Test that cycle_time_difference_pct is negative when AI PRs are faster.

        AI at 10h, non-AI at 20h = ((10 - 20) / 20) * 100 = -50%
        """
        # Create AI PR with 10 hours cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("10.0"),
        )

        # Create non-AI PR with 20 hours cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_ai_assisted=False,
            cycle_time_hours=Decimal("20.0"),
        )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        # ((10 - 20) / 20) * 100 = -50%
        self.assertEqual(result["cycle_time_difference_pct"], Decimal("-50.00"))

    def test_cycle_time_difference_pct_positive_when_ai_slower(self):
        """Test that cycle_time_difference_pct is positive when AI PRs are slower.

        AI at 30h, non-AI at 20h = ((30 - 20) / 20) * 100 = +50%
        """
        # Create AI PR with 30 hours cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("30.0"),
        )

        # Create non-AI PR with 20 hours cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_ai_assisted=False,
            cycle_time_hours=Decimal("20.0"),
        )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        # ((30 - 20) / 20) * 100 = +50%
        self.assertEqual(result["cycle_time_difference_pct"], Decimal("50.00"))

    def test_handles_no_prs_in_range(self):
        """Test that function returns sensible defaults when no PRs in range."""
        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_adoption_pct"], Decimal("0.00"))
        self.assertIsNone(result["avg_cycle_with_ai"])
        self.assertIsNone(result["avg_cycle_without_ai"])
        self.assertIsNone(result["cycle_time_difference_pct"])
        self.assertEqual(result["total_prs"], 0)
        self.assertEqual(result["ai_prs"], 0)

    def test_handles_all_ai_prs(self):
        """Test that function handles 100% AI adoption (no comparison possible)."""
        # Create only AI-assisted PRs
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
                is_ai_assisted=True,
                cycle_time_hours=Decimal("20.0"),
            )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_adoption_pct"], Decimal("100.00"))
        self.assertEqual(result["avg_cycle_with_ai"], Decimal("20.00"))
        self.assertIsNone(result["avg_cycle_without_ai"])
        # Cannot calculate difference without non-AI PRs
        self.assertIsNone(result["cycle_time_difference_pct"])
        self.assertEqual(result["total_prs"], 5)
        self.assertEqual(result["ai_prs"], 5)

    def test_handles_no_ai_prs(self):
        """Test that function handles 0% AI adoption."""
        # Create only non-AI PRs
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
                is_ai_assisted=False,
                cycle_time_hours=Decimal("24.0"),
            )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        self.assertEqual(result["ai_adoption_pct"], Decimal("0.00"))
        self.assertIsNone(result["avg_cycle_with_ai"])
        self.assertEqual(result["avg_cycle_without_ai"], Decimal("24.00"))
        # Cannot calculate difference without AI PRs
        self.assertIsNone(result["cycle_time_difference_pct"])
        self.assertEqual(result["total_prs"], 5)
        self.assertEqual(result["ai_prs"], 0)

    def test_handles_prs_without_cycle_time(self):
        """Test that PRs without cycle_time_hours are excluded from cycle time calculations."""
        # Create AI PR with cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("10.0"),
        )
        # Create AI PR without cycle time (should be excluded from avg)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=None,
        )

        # Create non-AI PR with cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            is_ai_assisted=False,
            cycle_time_hours=Decimal("20.0"),
        )
        # Create non-AI PR without cycle time (should be excluded from avg)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 18, 12, 0)),
            is_ai_assisted=False,
            cycle_time_hours=None,
        )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        # Both PRs should be counted for adoption (4 total, 2 AI = 50%)
        self.assertEqual(result["total_prs"], 4)
        self.assertEqual(result["ai_prs"], 2)
        self.assertEqual(result["ai_adoption_pct"], Decimal("50.00"))

        # Averages should only include PRs with cycle time
        self.assertEqual(result["avg_cycle_with_ai"], Decimal("10.00"))
        self.assertEqual(result["avg_cycle_without_ai"], Decimal("20.00"))

    def test_uses_effective_is_ai_assisted(self):
        """Test that function uses effective_is_ai_assisted property.

        The effective_is_ai_assisted property prioritizes LLM detection over
        the is_ai_assisted field. This test verifies that behavior.
        """
        # Create PR with is_ai_assisted=False but LLM summary indicates AI
        pr_with_llm = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=False,  # Base field says no
            llm_summary={"ai": {"is_assisted": True, "confidence": 0.9, "tools": ["cursor"]}},  # LLM says yes
            cycle_time_hours=Decimal("10.0"),
        )

        # Verify the effective property returns True (LLM priority)
        self.assertTrue(pr_with_llm.effective_is_ai_assisted)

        # Create regular non-AI PR
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_ai_assisted=False,
            cycle_time_hours=Decimal("20.0"),
        )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        # Should count the LLM-detected PR as AI-assisted (1 out of 2 = 50%)
        self.assertEqual(result["ai_prs"], 1)
        self.assertEqual(result["ai_adoption_pct"], Decimal("50.00"))

    def test_filters_by_date_range(self):
        """Test that only PRs merged within date range are included."""
        # PR in range
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("10.0"),
        )

        # PR before start date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("10.0"),
        )

        # PR after end date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("10.0"),
        )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        # Only one PR should be counted
        self.assertEqual(result["total_prs"], 1)

    def test_filters_by_team(self):
        """Test that only PRs from specified team are included."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)

        # Target team PR
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("10.0"),
        )

        # Other team PR (should be excluded)
        PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_ai_assisted=True,
            cycle_time_hours=Decimal("10.0"),
        )

        result = dashboard_service.get_ai_impact_stats(self.team, self.start_date, self.end_date)

        # Only target team PR should be counted
        self.assertEqual(result["total_prs"], 1)
