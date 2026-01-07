"""Tests for Copilot vs Non-Copilot PR delivery comparison.

Tests for get_copilot_delivery_comparison() service function that compares
delivery metrics (cycle time, review time) between PRs created by team members
who actively use Copilot vs those who don't.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services.dashboard.copilot_metrics import get_copilot_delivery_comparison


class TestCopilotDeliveryComparison(TestCase):
    """Tests for get_copilot_delivery_comparison function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_correct_structure(self):
        """Test that function returns comparison data with correct structure."""
        # Arrange - create a copilot user and non-copilot user
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        # Create merged PRs for both
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert - verify structure
        self.assertIn("copilot_prs", result)
        self.assertIn("non_copilot_prs", result)
        self.assertIn("improvement", result)
        self.assertIn("sample_sufficient", result)

        # Verify copilot_prs structure
        self.assertIn("count", result["copilot_prs"])
        self.assertIn("avg_cycle_time_hours", result["copilot_prs"])
        self.assertIn("avg_review_time_hours", result["copilot_prs"])

        # Verify non_copilot_prs structure
        self.assertIn("count", result["non_copilot_prs"])
        self.assertIn("avg_cycle_time_hours", result["non_copilot_prs"])
        self.assertIn("avg_review_time_hours", result["non_copilot_prs"])

        # Verify improvement structure
        self.assertIn("cycle_time_percent", result["improvement"])
        self.assertIn("review_time_percent", result["improvement"])

    def test_categorizes_prs_by_author_copilot_activity(self):
        """Test that PRs are correctly categorized by author's Copilot activity."""
        # Arrange - create copilot user (recent activity within 30 days)
        copilot_user = TeamMemberFactory(
            team=self.team,
            display_name="Copilot User",
            copilot_last_activity_at=timezone.now() - timedelta(days=10),
        )
        # Non-copilot user (no activity)
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            display_name="Non-Copilot User",
            copilot_last_activity_at=None,
        )
        # Inactive copilot user (activity over 30 days ago - should count as non-copilot)
        inactive_copilot_user = TeamMemberFactory(
            team=self.team,
            display_name="Inactive Copilot User",
            copilot_last_activity_at=timezone.now() - timedelta(days=45),
        )

        # Create merged PRs
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )

        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=inactive_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert - copilot user PRs (10), non-copilot (5) + inactive copilot (5) = 10
        self.assertEqual(result["copilot_prs"]["count"], 10)
        self.assertEqual(result["non_copilot_prs"]["count"], 10)

    def test_calculates_avg_cycle_time_correctly(self):
        """Test that avg cycle time is calculated correctly for each group."""
        # Arrange
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        # Copilot PRs: 10h, 12h, 14h -> avg = 12h
        for hours in [10, 12, 14]:
            # Calculate merged_at properly handling day overflow
            merged_day = 15 if hours < 14 else 16
            merged_hour = (10 + hours) % 24
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, merged_day, merged_hour, 0)),
                cycle_time_hours=Decimal(str(hours)),
                review_time_hours=Decimal("2.00"),
            )

        # Non-copilot PRs: 20h, 24h, 28h -> avg = 24h
        for hours in [20, 24, 28]:
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10 + (hours - 24), 0)),
                cycle_time_hours=Decimal(str(hours)),
                review_time_hours=Decimal("4.00"),
            )

        # Add more PRs to meet sample threshold (need 10 each)
        for _ in range(7):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 22, 0)),
                cycle_time_hours=Decimal("12.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert - avg cycle times
        # Copilot: (10+12+14 + 12*7) / 10 = (36 + 84) / 10 = 12.0
        self.assertEqual(result["copilot_prs"]["avg_cycle_time_hours"], Decimal("12.00"))
        # Non-copilot: (20+24+28 + 24*7) / 10 = (72 + 168) / 10 = 24.0
        self.assertEqual(result["non_copilot_prs"]["avg_cycle_time_hours"], Decimal("24.00"))

    def test_calculates_avg_review_time_correctly(self):
        """Test that avg review time is calculated correctly for each group."""
        # Arrange
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        # Copilot PRs: 1h, 2h, 3h review times -> avg = 2h
        for hours in [1, 2, 3]:
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal(str(hours)),
            )

        # Non-copilot PRs: 4h, 5h, 6h review times -> avg = 5h
        for hours in [4, 5, 6]:
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal(str(hours)),
            )

        # Add more PRs to meet sample threshold
        for _ in range(7):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("5.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert - avg review times
        # Copilot: (1+2+3 + 2*7) / 10 = (6 + 14) / 10 = 2.0
        self.assertEqual(result["copilot_prs"]["avg_review_time_hours"], Decimal("2.00"))
        # Non-copilot: (4+5+6 + 5*7) / 10 = (15 + 35) / 10 = 5.0
        self.assertEqual(result["non_copilot_prs"]["avg_review_time_hours"], Decimal("5.00"))

    def test_calculates_improvement_percentages_correctly(self):
        """Test improvement percentages are calculated correctly."""
        # Arrange
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        # Copilot: 18h cycle time, 4h review time
        # Non-copilot: 24h cycle time, 5h review time
        # Cycle time improvement: (18 - 24) / 24 * 100 = -25% (negative = faster)
        # Review time improvement: (4 - 5) / 5 * 100 = -20% (negative = faster)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 4, 0)),
                cycle_time_hours=Decimal("18.00"),
                review_time_hours=Decimal("4.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("5.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert - improvement percentages
        # Cycle time: (18 - 24) / 24 * 100 = -25%
        self.assertEqual(result["improvement"]["cycle_time_percent"], -25)
        # Review time: (4 - 5) / 5 * 100 = -20%
        self.assertEqual(result["improvement"]["review_time_percent"], -20)

    def test_sample_sufficient_false_when_below_threshold(self):
        """Test that sample_sufficient is False when either group has < 10 PRs."""
        # Arrange - only create 5 PRs for each group
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert
        self.assertFalse(result["sample_sufficient"])

    def test_sample_sufficient_true_when_above_threshold(self):
        """Test that sample_sufficient is True when both groups have >= 10 PRs."""
        # Arrange - create 10 PRs for each group
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert
        self.assertTrue(result["sample_sufficient"])

    def test_only_merged_prs_included(self):
        """Test that only merged PRs are included in calculations."""
        # Arrange
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        # Create merged PRs (should be counted)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # Create open PRs (should NOT be counted)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="open",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=None,
                cycle_time_hours=None,
                review_time_hours=Decimal("1.00"),
            )

        # Create closed (not merged) PRs (should NOT be counted)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="closed",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=None,
                cycle_time_hours=None,
                review_time_hours=Decimal("3.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert - only merged PRs counted
        self.assertEqual(result["copilot_prs"]["count"], 10)
        self.assertEqual(result["non_copilot_prs"]["count"], 10)

    def test_only_prs_within_date_range_included(self):
        """Test that only PRs within date range are included."""
        # Arrange
        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        # PRs within date range (should be counted)
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # PRs before date range (should NOT be counted)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2023, 12, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2023, 12, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )

        # PRs after date range (should NOT be counted)
        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 2, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert - only PRs within range counted
        self.assertEqual(result["copilot_prs"]["count"], 10)
        self.assertEqual(result["non_copilot_prs"]["count"], 10)

    def test_team_isolation_enforced(self):
        """Test that team isolation is enforced."""
        # Arrange - create two teams
        other_team = TeamFactory()

        copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        non_copilot_user = TeamMemberFactory(
            team=self.team,
            copilot_last_activity_at=None,
        )

        # PRs for our team
        for _ in range(10):
            PullRequestFactory(
                team=self.team,
                author=copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 18, 0)),
                cycle_time_hours=Decimal("8.00"),
                review_time_hours=Decimal("2.00"),
            )
            PullRequestFactory(
                team=self.team,
                author=non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 10, 0)),
                cycle_time_hours=Decimal("24.00"),
                review_time_hours=Decimal("4.00"),
            )

        # PRs for other team (should NOT be counted)
        other_copilot_user = TeamMemberFactory(
            team=other_team,
            copilot_last_activity_at=timezone.now() - timedelta(days=5),
        )
        other_non_copilot_user = TeamMemberFactory(
            team=other_team,
            copilot_last_activity_at=None,
        )

        for _ in range(15):
            PullRequestFactory(
                team=other_team,
                author=other_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 14, 0)),
                cycle_time_hours=Decimal("4.00"),
                review_time_hours=Decimal("1.00"),
            )
            PullRequestFactory(
                team=other_team,
                author=other_non_copilot_user,
                state="merged",
                pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 10, 0)),
                cycle_time_hours=Decimal("48.00"),
                review_time_hours=Decimal("8.00"),
            )

        # Act
        result = get_copilot_delivery_comparison(self.team, self.start_date, self.end_date)

        # Assert - only our team's PRs counted
        self.assertEqual(result["copilot_prs"]["count"], 10)
        self.assertEqual(result["non_copilot_prs"]["count"], 10)

        # Verify our team's averages (not other team's)
        self.assertEqual(result["copilot_prs"]["avg_cycle_time_hours"], Decimal("8.00"))
        self.assertEqual(result["non_copilot_prs"]["avg_cycle_time_hours"], Decimal("24.00"))
