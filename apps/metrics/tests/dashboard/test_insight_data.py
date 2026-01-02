"""Tests for dashboard insight data functions.

Tests for dashboard service functions including:
- get_velocity_comparison: Compares velocity metrics between periods
- get_quality_metrics: Calculates quality indicators
- get_team_health_metrics: Team health and contributor distribution
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetVelocityComparison(TestCase):
    """Tests for get_velocity_comparison function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        # Current period: Jan 15-31, 2024 (17 days)
        self.start_date = date(2024, 1, 15)
        self.end_date = date(2024, 1, 31)
        # Previous period would be: Dec 29, 2023 - Jan 14, 2024 (17 days)

    def test_returns_correct_structure(self):
        """Test that get_velocity_comparison returns dict with throughput, cycle_time, review_time keys."""
        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Verify top-level keys
        self.assertIn("throughput", result)
        self.assertIn("cycle_time", result)
        self.assertIn("review_time", result)

        # Verify nested structure for throughput
        self.assertIn("current", result["throughput"])
        self.assertIn("previous", result["throughput"])
        self.assertIn("pct_change", result["throughput"])

        # Verify nested structure for cycle_time
        self.assertIn("current", result["cycle_time"])
        self.assertIn("previous", result["cycle_time"])
        self.assertIn("pct_change", result["cycle_time"])

        # Verify nested structure for review_time
        self.assertIn("current", result["review_time"])
        self.assertIn("previous", result["review_time"])
        self.assertIn("pct_change", result["review_time"])

    def test_calculates_current_period_metrics(self):
        """Test that current period metrics are calculated from PRs merged in date range."""
        # Create 3 PRs in current period (Jan 15-31)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 25, 12, 0)),
            cycle_time_hours=Decimal("48.0"),
            review_time_hours=Decimal("8.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 30, 12, 0)),
            cycle_time_hours=Decimal("36.0"),
            review_time_hours=Decimal("6.0"),
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Throughput: 3 PRs merged
        self.assertEqual(result["throughput"]["current"], 3)

        # Cycle time: avg of (24 + 48 + 36) / 3 = 36.0
        self.assertEqual(result["cycle_time"]["current"], Decimal("36.0"))

        # Review time: avg of (4 + 8 + 6) / 3 = 6.0
        self.assertEqual(result["review_time"]["current"], Decimal("6.0"))

    def test_calculates_previous_period_metrics(self):
        """Test that previous period is calculated automatically and metrics computed."""
        # Current period: Jan 15-31 (17 days)
        # Previous period should be: Dec 29 - Jan 14 (17 days)

        # Create PRs in previous period
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            cycle_time_hours=Decimal("20.0"),
            review_time_hours=Decimal("5.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("40.0"),
            review_time_hours=Decimal("10.0"),
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Throughput: 2 PRs merged in previous period
        self.assertEqual(result["throughput"]["previous"], 2)

        # Cycle time: avg of (20 + 40) / 2 = 30.0
        self.assertEqual(result["cycle_time"]["previous"], Decimal("30.0"))

        # Review time: avg of (5 + 10) / 2 = 7.5
        self.assertEqual(result["review_time"]["previous"], Decimal("7.5"))

    def test_calculates_percentage_changes(self):
        """Test that pct_change is calculated correctly (negative = improvement)."""
        # Current period: 3 PRs, avg cycle 30h, avg review 6h
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            cycle_time_hours=Decimal("30.0"),
            review_time_hours=Decimal("6.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 25, 12, 0)),
            cycle_time_hours=Decimal("30.0"),
            review_time_hours=Decimal("6.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 28, 12, 0)),
            cycle_time_hours=Decimal("30.0"),
            review_time_hours=Decimal("6.0"),
        )

        # Previous period: 2 PRs, avg cycle 40h, avg review 8h
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            cycle_time_hours=Decimal("40.0"),
            review_time_hours=Decimal("8.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("40.0"),
            review_time_hours=Decimal("8.0"),
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Throughput: (3 - 2) / 2 * 100 = 50% increase
        self.assertAlmostEqual(result["throughput"]["pct_change"], 50.0, places=1)

        # Cycle time: (30 - 40) / 40 * 100 = -25% (improvement!)
        self.assertAlmostEqual(result["cycle_time"]["pct_change"], -25.0, places=1)

        # Review time: (6 - 8) / 8 * 100 = -25% (improvement!)
        self.assertAlmostEqual(result["review_time"]["pct_change"], -25.0, places=1)

    def test_handles_no_prs_in_current_period(self):
        """Test that returns zeros/None when no PRs in current period."""
        # Only create PRs in previous period
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Current period has no PRs
        self.assertEqual(result["throughput"]["current"], 0)
        self.assertIsNone(result["cycle_time"]["current"])
        self.assertIsNone(result["review_time"]["current"])

        # pct_change should be -100% for throughput (went from some to zero)
        self.assertEqual(result["throughput"]["pct_change"], -100.0)

        # pct_change for times should be None when current is None
        self.assertIsNone(result["cycle_time"]["pct_change"])
        self.assertIsNone(result["review_time"]["pct_change"])

    def test_handles_no_prs_in_previous_period(self):
        """Test that handles case when previous period has no PRs."""
        # Only create PRs in current period
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Previous period has no PRs
        self.assertEqual(result["throughput"]["previous"], 0)
        self.assertIsNone(result["cycle_time"]["previous"])
        self.assertIsNone(result["review_time"]["previous"])

        # pct_change should be None when previous is 0 (avoid division by zero)
        self.assertIsNone(result["throughput"]["pct_change"])
        self.assertIsNone(result["cycle_time"]["pct_change"])
        self.assertIsNone(result["review_time"]["pct_change"])

    def test_handles_no_prs_in_either_period(self):
        """Test that returns zeros/None when no PRs in any period."""
        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Both periods have no PRs
        self.assertEqual(result["throughput"]["current"], 0)
        self.assertEqual(result["throughput"]["previous"], 0)
        self.assertIsNone(result["throughput"]["pct_change"])

        self.assertIsNone(result["cycle_time"]["current"])
        self.assertIsNone(result["cycle_time"]["previous"])
        self.assertIsNone(result["cycle_time"]["pct_change"])

        self.assertIsNone(result["review_time"]["current"])
        self.assertIsNone(result["review_time"]["previous"])
        self.assertIsNone(result["review_time"]["pct_change"])

    def test_filters_by_team(self):
        """Test that only PRs from specified team are included."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)

        # Create PR for target team in current period
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )

        # Create PR for other team in current period (should be excluded)
        PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            cycle_time_hours=Decimal("48.0"),
            review_time_hours=Decimal("8.0"),
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Only the target team's PR should be counted
        self.assertEqual(result["throughput"]["current"], 1)
        self.assertEqual(result["cycle_time"]["current"], Decimal("24.0"))

    def test_filters_by_repo(self):
        """Test that optional repo filter works correctly."""
        # Create PRs in different repos in current period
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            github_repo="org/frontend",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            github_repo="org/backend",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 22, 12, 0)),
            cycle_time_hours=Decimal("48.0"),
            review_time_hours=Decimal("8.0"),
        )

        # Filter by frontend repo
        result = dashboard_service.get_velocity_comparison(
            self.team, self.start_date, self.end_date, repo="org/frontend"
        )

        # Only frontend PR should be counted
        self.assertEqual(result["throughput"]["current"], 1)
        self.assertEqual(result["cycle_time"]["current"], Decimal("24.0"))

    def test_only_counts_merged_prs(self):
        """Test that only merged PRs are counted, not open or closed."""
        # Create merged PR
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )

        # Create open PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="open",
            merged_at=None,
        )

        # Create closed PR (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="closed",
            merged_at=None,
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Only merged PR should be counted
        self.assertEqual(result["throughput"]["current"], 1)

    def test_handles_prs_without_cycle_time(self):
        """Test that PRs without cycle_time_hours are handled gracefully."""
        # Create PRs with and without cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            cycle_time_hours=Decimal("24.0"),
            review_time_hours=Decimal("4.0"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 22, 12, 0)),
            cycle_time_hours=None,
            review_time_hours=None,
        )

        result = dashboard_service.get_velocity_comparison(self.team, self.start_date, self.end_date)

        # Both PRs counted for throughput
        self.assertEqual(result["throughput"]["current"], 2)

        # Average should only include PR with cycle time
        self.assertEqual(result["cycle_time"]["current"], Decimal("24.0"))
        self.assertEqual(result["review_time"]["current"], Decimal("4.0"))


class TestGetQualityMetrics(TestCase):
    """Tests for get_quality_metrics function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_correct_structure(self):
        """Test that get_quality_metrics returns dict with all expected keys."""
        result = dashboard_service.get_quality_metrics(self.team, self.start_date, self.end_date)

        # Verify all required keys are present
        self.assertIn("revert_count", result)
        self.assertIn("revert_rate", result)
        self.assertIn("hotfix_count", result)
        self.assertIn("hotfix_rate", result)
        self.assertIn("avg_review_rounds", result)
        self.assertIn("large_pr_pct", result)

    def test_returns_revert_count_and_rate(self):
        """Test that revert_count and revert_rate are calculated correctly."""
        # Create 5 PRs total, 2 are reverts
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_revert=True,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            is_revert=False,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 18, 12, 0)),
            is_revert=False,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 19, 12, 0)),
            is_revert=False,
        )

        result = dashboard_service.get_quality_metrics(self.team, self.start_date, self.end_date)

        # 2 reverts out of 5 = 40%
        self.assertEqual(result["revert_count"], 2)
        self.assertEqual(result["revert_rate"], 40.0)

    def test_returns_hotfix_count_and_rate(self):
        """Test that hotfix_count and hotfix_rate are calculated correctly."""
        # Create 4 PRs total, 1 is a hotfix
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_hotfix=True,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_hotfix=False,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            is_hotfix=False,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 18, 12, 0)),
            is_hotfix=False,
        )

        result = dashboard_service.get_quality_metrics(self.team, self.start_date, self.end_date)

        # 1 hotfix out of 4 = 25%
        self.assertEqual(result["hotfix_count"], 1)
        self.assertEqual(result["hotfix_rate"], 25.0)

    def test_returns_avg_review_rounds(self):
        """Test that avg_review_rounds is calculated correctly."""
        # Create 3 PRs with review_rounds: 1, 2, 3 => avg = 2.0
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            review_rounds=1,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            review_rounds=2,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            review_rounds=3,
        )

        result = dashboard_service.get_quality_metrics(self.team, self.start_date, self.end_date)

        # Average of (1 + 2 + 3) / 3 = 2.0
        self.assertEqual(result["avg_review_rounds"], 2.0)

    def test_returns_large_pr_percentage(self):
        """Test that large_pr_pct counts PRs with > 500 lines changed."""
        # Create 4 PRs: 2 large (>500 lines), 2 small
        # Large PR 1: 400 additions + 200 deletions = 600 lines
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            additions=400,
            deletions=200,
        )
        # Large PR 2: 501 additions + 0 deletions = 501 lines
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            additions=501,
            deletions=0,
        )
        # Small PR 1: 250 additions + 250 deletions = 500 lines (not > 500)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            additions=250,
            deletions=250,
        )
        # Small PR 2: 100 additions + 50 deletions = 150 lines
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 18, 12, 0)),
            additions=100,
            deletions=50,
        )

        result = dashboard_service.get_quality_metrics(self.team, self.start_date, self.end_date)

        # 2 large PRs out of 4 = 50%
        self.assertEqual(result["large_pr_pct"], 50.0)

    def test_handles_empty_period(self):
        """Test that returns zeros/None when no PRs in period."""
        result = dashboard_service.get_quality_metrics(self.team, self.start_date, self.end_date)

        # No PRs means zero counts and rates
        self.assertEqual(result["revert_count"], 0)
        self.assertEqual(result["revert_rate"], 0.0)
        self.assertEqual(result["hotfix_count"], 0)
        self.assertEqual(result["hotfix_rate"], 0.0)
        self.assertIsNone(result["avg_review_rounds"])
        self.assertEqual(result["large_pr_pct"], 0.0)

    def test_filters_by_repo(self):
        """Test that optional repo filter works correctly."""
        # Create PRs in different repos
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            github_repo="org/frontend",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            review_rounds=1,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            github_repo="org/frontend",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_revert=False,
            review_rounds=3,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            github_repo="org/backend",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            is_revert=True,
            review_rounds=5,
        )

        # Filter by frontend repo only
        result = dashboard_service.get_quality_metrics(self.team, self.start_date, self.end_date, repo="org/frontend")

        # Only frontend PRs: 1 revert out of 2 = 50%
        self.assertEqual(result["revert_count"], 1)
        self.assertEqual(result["revert_rate"], 50.0)
        # Average review rounds for frontend: (1 + 3) / 2 = 2.0
        self.assertEqual(result["avg_review_rounds"], 2.0)


class TestGetTeamHealthMetrics(TestCase):
    """Tests for get_team_health_metrics function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")
        self.member3 = TeamMemberFactory(team=self.team, display_name="Charlie")
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_correct_structure(self):
        """Test that get_team_health_metrics returns dict with all expected keys."""
        result = dashboard_service.get_team_health_metrics(self.team, self.start_date, self.end_date)

        # Verify all required keys are present
        self.assertIn("active_contributors", result)
        self.assertIn("pr_distribution", result)
        self.assertIn("review_distribution", result)
        self.assertIn("bottleneck", result)

        # Verify nested structure for pr_distribution
        self.assertIn("top_contributor_pct", result["pr_distribution"])
        self.assertIn("is_concentrated", result["pr_distribution"])

        # Verify nested structure for review_distribution
        self.assertIn("avg_reviews_per_reviewer", result["review_distribution"])
        self.assertIn("max_reviews", result["review_distribution"])

    def test_returns_active_contributors(self):
        """Test that active_contributors counts unique PR authors in period."""
        # Create PRs from 2 different authors in the period
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
        )

        result = dashboard_service.get_team_health_metrics(self.team, self.start_date, self.end_date)

        # 2 unique authors (member1 and member2)
        self.assertEqual(result["active_contributors"], 2)

    def test_returns_pr_distribution(self):
        """Test that pr_distribution shows top contributor percentage and concentration flag."""
        # Create 5 PRs: 4 from member1 (80%), 1 from member2 (20%)
        for _ in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
        PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )

        result = dashboard_service.get_team_health_metrics(self.team, self.start_date, self.end_date)

        # Top contributor has 80% of PRs
        self.assertEqual(result["pr_distribution"]["top_contributor_pct"], 80.0)
        # is_concentrated should be True when > 50%
        self.assertTrue(result["pr_distribution"]["is_concentrated"])

    def test_returns_review_distribution(self):
        """Test that review_distribution shows avg and max reviews per reviewer."""
        # Create PRs and reviews
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        pr2 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )
        pr3 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
        )

        # member2 reviews 3 PRs, member3 reviews 1 PR
        PRReviewFactory(team=self.team, pull_request=pr1, reviewer=self.member2)
        PRReviewFactory(team=self.team, pull_request=pr2, reviewer=self.member2)
        PRReviewFactory(team=self.team, pull_request=pr3, reviewer=self.member2)
        PRReviewFactory(team=self.team, pull_request=pr1, reviewer=self.member3)

        result = dashboard_service.get_team_health_metrics(self.team, self.start_date, self.end_date)

        # Average: (3 + 1) / 2 = 2.0 reviews per reviewer
        self.assertEqual(result["review_distribution"]["avg_reviews_per_reviewer"], 2.0)
        # Max: member2 with 3 reviews
        self.assertEqual(result["review_distribution"]["max_reviews"], 3)

    def test_includes_bottleneck_when_detected(self):
        """Test that bottleneck integrates detect_review_bottleneck() result."""
        # For bottleneck to trigger, we need:
        # - At least 2 reviewers
        # - One reviewer with pending_count > 3x team_avg
        #
        # Math: With n reviewers, total T, avg = T/n, threshold = 3*avg = 3T/n
        # For max to exceed: max > 3T/n, so max*n > 3T
        # Since max <= T, need max*n > 3*max, so n > 3
        # Therefore we need 4+ reviewers for bottleneck to be mathematically possible
        #
        # Example: 10, 1, 1, 1 → avg=3.25, threshold=9.75, 10>9.75 ✓
        member4 = TeamMemberFactory(team=self.team, display_name="Diana")

        # Create 10 open PRs
        prs = [
            PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="open",
                merged_at=None,
            )
            for _ in range(10)
        ]

        # member2 reviews all 10 open PRs (bottleneck candidate)
        # Use explicit state="commented" to ensure these count as pending reviews
        for pr in prs:
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=self.member2, state="commented")

        # member3, member4 and member1 each review only 1 PR
        PRReviewFactory(team=self.team, pull_request=prs[0], reviewer=self.member3, state="commented")
        PRReviewFactory(team=self.team, pull_request=prs[1], reviewer=member4, state="commented")
        PRReviewFactory(team=self.team, pull_request=prs[2], reviewer=self.member1, state="commented")

        # Now: member2=10, member3=1, member4=1, member1=1
        # avg = 13/4 = 3.25, threshold = 9.75
        # member2 has 10 > 9.75 → bottleneck!

        result = dashboard_service.get_team_health_metrics(self.team, self.start_date, self.end_date)

        self.assertIsNotNone(result["bottleneck"])
        self.assertIn("reviewer_name", result["bottleneck"])
        self.assertIn("pending_count", result["bottleneck"])
        self.assertIn("team_avg", result["bottleneck"])
        self.assertEqual(result["bottleneck"]["reviewer_name"], "Bob")
        self.assertEqual(result["bottleneck"]["pending_count"], 10)

    def test_handles_single_contributor(self):
        """Test edge case with only 1 author - they have 100% of PRs."""
        # Create PRs from only one author
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )

        result = dashboard_service.get_team_health_metrics(self.team, self.start_date, self.end_date)

        # 1 unique author
        self.assertEqual(result["active_contributors"], 1)
        # Top contributor has 100% of PRs
        self.assertEqual(result["pr_distribution"]["top_contributor_pct"], 100.0)
        # is_concentrated should be True when > 50%
        self.assertTrue(result["pr_distribution"]["is_concentrated"])

    def test_handles_empty_period(self):
        """Test that returns zeros/None when no PRs in period."""
        result = dashboard_service.get_team_health_metrics(self.team, self.start_date, self.end_date)

        # No PRs means zero active contributors
        self.assertEqual(result["active_contributors"], 0)
        # pr_distribution should have 0 and False for empty period
        self.assertEqual(result["pr_distribution"]["top_contributor_pct"], 0.0)
        self.assertFalse(result["pr_distribution"]["is_concentrated"])
        # review_distribution should have None/0 for empty period
        self.assertIsNone(result["review_distribution"]["avg_reviews_per_reviewer"])
        self.assertEqual(result["review_distribution"]["max_reviews"], 0)
        # No bottleneck when no data
        self.assertIsNone(result["bottleneck"])
