"""Tests for detect_review_bottleneck function.

Tests for the dashboard service function that detects when a reviewer
has significantly more pending reviews than the team average (> 3x).
"""

from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestDetectReviewBottleneck(TestCase):
    """Tests for detect_review_bottleneck function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_none_when_no_reviews(self):
        """Test that returns None when there are no reviews."""
        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        self.assertIsNone(result)

    def test_returns_none_when_no_open_prs(self):
        """Test that returns None when all PRs are merged/closed."""
        reviewer = TeamMemberFactory(team=self.team, display_name="Alice")
        author = TeamMemberFactory(team=self.team, display_name="Bob")

        # Create merged PR with review (should not count as pending)
        pr = PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=reviewer,
            state="commented",  # Explicit state to test pending behavior
        )

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        self.assertIsNone(result)

    def test_returns_none_when_no_bottleneck(self):
        """Test that returns None when no reviewer exceeds 3x threshold."""
        reviewer1 = TeamMemberFactory(team=self.team, display_name="Alice")
        reviewer2 = TeamMemberFactory(team=self.team, display_name="Bob")
        author = TeamMemberFactory(team=self.team, display_name="Charlie")

        # Create open PRs - both reviewers have 2 each (balanced)
        for _i in range(2):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer1, state="commented")

        for _i in range(2):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer2, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # 2 reviews each, avg = 2, threshold = 6, no bottleneck
        self.assertIsNone(result)

    def test_returns_dict_with_required_keys_when_bottleneck_exists(self):
        """Test that returns dict with reviewer_name, pending_count, team_avg when bottleneck detected."""
        author = TeamMemberFactory(team=self.team, display_name="Charlie Author")

        # Need 5 reviewers: 4 with 1 each, 1 with 20
        # Total = 24, avg = 4.8, threshold = 14.4, 20 > 14.4 ✓
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light Reviewer {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Bob Overloaded")
        for _ in range(20):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy_reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn("reviewer_name", result)
        self.assertIn("pending_count", result)
        self.assertIn("team_avg", result)

    def test_detects_bottleneck_with_extreme_imbalance(self):
        """Test that bottleneck is detected when one reviewer has >> 3x average."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # 4 light reviewers with 1 open PR each
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light Reviewer {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # 1 heavy reviewer with 20 open PRs
        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy Reviewer")
        for _ in range(20):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy_reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Total = 4 + 20 = 24, avg = 24/5 = 4.8, threshold = 14.4
        # heavy_reviewer has 20 > 14.4 ✓ BOTTLENECK
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertIn("reviewer_name", result)
        self.assertIn("pending_count", result)
        self.assertIn("team_avg", result)

    def test_returns_correct_reviewer_name(self):
        """Test that the bottleneck reviewer's display_name is returned."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Light reviewers
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # Heavy reviewer
        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Bob Bottleneck")
        for _ in range(20):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy_reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        self.assertEqual(result["reviewer_name"], "Bob Bottleneck")

    def test_returns_correct_pending_count(self):
        """Test that pending_count matches the bottleneck reviewer's count."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Light reviewers
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # Heavy reviewer with exactly 25 reviews
        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy")
        for _ in range(25):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy_reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        self.assertEqual(result["pending_count"], 25)

    def test_returns_correct_team_avg(self):
        """Test that team_avg is calculated correctly."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # 4 reviewers with 1 each, 1 with 20
        # avg = 24/5 = 4.8
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy")
        for _ in range(20):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy_reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # 4 + 20 = 24 reviews, 5 reviewers, avg = 4.8
        self.assertAlmostEqual(float(result["team_avg"]), 4.8, places=1)

    def test_returns_none_with_single_reviewer(self):
        """Test that single reviewer cannot be a bottleneck (no comparison)."""
        reviewer = TeamMemberFactory(team=self.team, display_name="Solo")
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Single reviewer with many reviews
        for _i in range(10):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Single reviewer can't be compared, so no bottleneck
        self.assertIsNone(result)

    def test_threshold_exactly_3x_is_not_bottleneck(self):
        """Test that exactly 3x the average is NOT a bottleneck (must be > 3x)."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Set up: 3 reviewers with 2, 2, 6 reviews
        # Total = 10, avg = 10/3 ≈ 3.33, threshold = 10
        # 6 < 10, not a bottleneck
        # Need: 2 reviewers with 1 each, 1 with 6
        # Total = 8, avg = 8/3 ≈ 2.67, threshold = 8
        # 6 < 8, not bottleneck

        # For exactly 3x: if reviewer has X and avg is X/3
        # Need total/n = X/3, so X = 3*total/n
        # If reviewer has X, and rest have total-X
        # avg = total/n, so X = 3*total/n
        # X/total = 3/n, n=3 -> X/total = 1, impossible

        # Actually for n reviewers, if one has X and avg = total/n
        # X > 3*avg = 3*total/n
        # If all others have 1: total = X + (n-1)
        # X > 3*(X + n - 1)/n
        # nX > 3X + 3n - 3
        # (n-3)X > 3n - 3
        # X > 3(n-1)/(n-3) for n > 3

        # For n=5: X > 3*4/2 = 6, so X >= 7 is bottleneck
        # Setup: 4 reviewers with 1 each, 1 with 6
        # avg = 10/5 = 2, threshold = 6
        # 6 is NOT > 6, so NOT bottleneck

        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy")
        for _ in range(6):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy_reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # 4 + 6 = 10, avg = 2, threshold = 6
        # 6 is NOT > 6, so no bottleneck
        self.assertIsNone(result)

    def test_threshold_just_above_3x_is_bottleneck(self):
        """Test that just above 3x the average IS a bottleneck."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # 4 reviewers with 1 each, 1 with 7
        # avg = 11/5 = 2.2, threshold = 6.6
        # 7 > 6.6 ✓ BOTTLENECK
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy")
        for _ in range(7):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy_reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # avg = 11/5 = 2.2, threshold = 6.6, 7 > 6.6 ✓
        self.assertIsNotNone(result)
        self.assertEqual(result["pending_count"], 7)

    def test_filters_by_team(self):
        """Test that only reviews from specified team are counted."""
        other_team = TeamFactory()
        author = TeamMemberFactory(team=self.team, display_name="Author")
        other_author = TeamMemberFactory(team=other_team, display_name="Other Author")

        # Light reviewers in target team
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # Heavy reviewer in OTHER team (should be excluded)
        heavy_reviewer = TeamMemberFactory(team=other_team, display_name="Heavy")
        for _ in range(20):
            pr = PullRequestFactory(
                team=other_team,
                author=other_author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=other_team, pull_request=pr, reviewer=heavy_reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Only target team reviews counted (4 reviewers with 1 each)
        # avg = 1, no one has > 3, so no bottleneck
        self.assertIsNone(result)

    def test_counts_distinct_prs_per_reviewer(self):
        """Test that multiple reviews on same PR count as 1 pending."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Light reviewers with 1 PR each
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # Heavy reviewer with 7 open PRs but multiple reviews per PR
        # First commented, then changes_requested (latest is changes_requested = pending)
        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy")
        for _i in range(7):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            # Multiple reviews on same PR - first commented, then changes_requested
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=heavy_reviewer,
                state="commented",
                submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            )
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=heavy_reviewer,
                state="changes_requested",
                submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Should count 7 distinct PRs, not 14 reviews
        # avg = 11/5 = 2.2, threshold = 6.6, 7 > 6.6 ✓
        self.assertIsNotNone(result)
        self.assertEqual(result["pending_count"], 7)

    def test_returns_worst_bottleneck_when_multiple_exist(self):
        """Test that the reviewer with highest pending count is returned."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # 10 light reviewers with 1 PR each
        for i in range(10):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # heavy1 with 15 PRs
        heavy1 = TeamMemberFactory(team=self.team, display_name="Heavy 1")
        for _ in range(15):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy1, state="commented")

        # heavy2 with 20 PRs (worst bottleneck)
        heavy2 = TeamMemberFactory(team=self.team, display_name="Heavy 2")
        for _ in range(20):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
                created_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy2, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Total = 10 + 15 + 20 = 45, avg = 45/12 = 3.75, threshold = 11.25
        # heavy1 = 15 > 11.25 ✓ (bottleneck)
        # heavy2 = 20 > 11.25 ✓ (worst bottleneck)
        # Should return Heavy 2 as worst
        self.assertIsNotNone(result)
        self.assertEqual(result["reviewer_name"], "Heavy 2")
        self.assertEqual(result["pending_count"], 20)

    def test_date_parameters_are_ignored_for_open_prs(self):
        """Test that date parameters are ignored - all open PRs are included.

        For bottleneck detection, we look at ALL currently open PRs regardless
        of when they were created, since pending work is date-independent.
        """
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Light reviewers with recently created PRs
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # Heavy reviewer with PRs (date doesn't matter, all open PRs count)
        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy")
        for _ in range(20):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="open",
            )
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=heavy_reviewer, state="commented")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # All open PRs counted: 4 + 20 = 24, avg = 4.8, threshold = 14.4
        # heavy has 20 > 14.4 = bottleneck
        self.assertIsNotNone(result)
        self.assertEqual(result["pending_count"], 20)


class TestDetectReviewBottleneckApprovedReviewExclusion(TestCase):
    """Tests for excluding PRs where reviewer's latest review is 'approved'.

    When a reviewer has already approved a PR, that PR should NOT count as
    "pending" for them. Only the LATEST review state matters.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_approved_prs_are_excluded_from_pending_count(self):
        """Test that PRs with 'approved' latest review don't count as pending."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Light reviewers with 1 pending PR each
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=reviewer,
                state="commented",  # Still pending
            )

        # Heavy reviewer with 20 PRs, but all APPROVED
        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy Reviewer")
        for _ in range(20):
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=heavy_reviewer,
                state="approved",  # Should NOT count as pending
            )

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Heavy reviewer approved all, so 0 pending
        # Light reviewers have 4 total, avg = 1, no bottleneck
        self.assertIsNone(result)

    def test_latest_review_state_wins_over_earlier_reviews(self):
        """Test that multiple review rounds - only latest state matters.

        If reviewer commented first, then approved, the PR is NOT pending.
        """
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Light reviewers with 1 pending PR each
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=reviewer,
                state="commented",
            )

        # Heavy reviewer with 20 PRs - commented first, then approved
        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy Reviewer")
        for _ in range(20):
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            # First review: commented (would count as pending if only review)
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=heavy_reviewer,
                state="commented",
                submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            )
            # Second review: approved (should clear pending status)
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=heavy_reviewer,
                state="approved",
                submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Heavy reviewer's latest review is approved → 0 pending
        # 4 light reviewers with 1 each, avg = 1, no bottleneck
        self.assertIsNone(result)

    def test_changes_requested_after_approval_counts_as_pending(self):
        """Test that changes_requested AFTER approval makes PR pending again.

        If reviewer approved, then requested changes, it's pending.
        """
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Light reviewers with 1 pending each
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # Heavy reviewer with 20 PRs - approved then changes_requested
        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy Reviewer")
        for _ in range(20):
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            # First: approved
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=heavy_reviewer,
                state="approved",
                submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            )
            # Later: changes requested (author pushed new code that reviewer didn't like)
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=heavy_reviewer,
                state="changes_requested",
                submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Heavy reviewer's latest is changes_requested → 20 pending PRs
        # 4 + 20 = 24 total, 5 reviewers, avg = 4.8, threshold = 14.4
        # 20 > 14.4 = bottleneck
        self.assertIsNotNone(result)
        self.assertEqual(result["reviewer_name"], "Heavy Reviewer")
        self.assertEqual(result["pending_count"], 20)

    def test_mixed_approved_and_pending_reviews(self):
        """Test a reviewer with some approved and some pending PRs."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Light reviewers with 1 pending each
        for i in range(4):
            reviewer = TeamMemberFactory(team=self.team, display_name=f"Light {i}")
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # Heavy reviewer: 15 approved (not pending) + 7 commented (pending) = 7 pending
        heavy_reviewer = TeamMemberFactory(team=self.team, display_name="Heavy Reviewer")

        # 15 approved PRs (not counted)
        for _ in range(15):
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=heavy_reviewer,
                state="approved",
            )

        # 7 commented PRs (counted as pending)
        for _ in range(7):
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=heavy_reviewer,
                state="commented",
            )

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Heavy reviewer: 7 pending (15 approved don't count)
        # Total pending: 4 + 7 = 11, avg = 11/5 = 2.2, threshold = 6.6
        # 7 > 6.6 = bottleneck
        self.assertIsNotNone(result)
        self.assertEqual(result["pending_count"], 7)

    def test_all_approved_excludes_reviewer_from_calculation(self):
        """Test that a reviewer with only approved reviews has 0 pending count."""
        author = TeamMemberFactory(team=self.team, display_name="Author")

        # Two light reviewers with pending reviews
        light1 = TeamMemberFactory(team=self.team, display_name="Light 1")
        light2 = TeamMemberFactory(team=self.team, display_name="Light 2")

        for reviewer in [light1, light2]:
            for _ in range(2):
                pr = PullRequestFactory(team=self.team, author=author, state="open")
                PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")

        # Approver reviewer with many approved PRs (should not be a bottleneck)
        approver = TeamMemberFactory(team=self.team, display_name="Speedy Approver")
        for _ in range(50):
            pr = PullRequestFactory(team=self.team, author=author, state="open")
            PRReviewFactory(team=self.team, pull_request=pr, reviewer=approver, state="approved")

        result = dashboard_service.detect_review_bottleneck(self.team, self.start_date, self.end_date)

        # Approver has 0 pending (all approved)
        # Light1: 2, Light2: 2 → avg = 2, threshold = 6
        # Neither > 6, so no bottleneck
        self.assertIsNone(result)
