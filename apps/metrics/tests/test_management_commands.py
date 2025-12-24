"""
Tests for metrics management commands.

These tests verify the behavior of management commands that backfill
and calculate PR metrics.
"""

from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PRReviewFactory, PullRequestFactory, TeamFactory


class TestBackfillPRTimingMetrics(TestCase):
    """Tests for backfill_pr_timing_metrics management command."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def test_backfill_calculates_cycle_time_for_merged_prs_with_null_cycle_time(self):
        """Test that backfill calculates cycle_time_hours for merged PRs missing it."""
        # Arrange - create merged PR with null cycle_time_hours
        pr_created = timezone.now() - timedelta(hours=48)
        merged = timezone.now() - timedelta(hours=2)
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=pr_created,
            merged_at=merged,
            cycle_time_hours=None,  # Missing metric
        )

        # Act - run the backfill command
        out = StringIO()
        call_command("backfill_pr_timing_metrics", team=self.team.name, stdout=out)

        # Assert - cycle_time_hours should be calculated
        pr.refresh_from_db()
        expected_hours = Decimal(str(round((merged - pr_created).total_seconds() / 3600, 2)))
        self.assertEqual(pr.cycle_time_hours, expected_hours)

    def test_backfill_sets_first_review_at_from_earliest_review(self):
        """Test that backfill sets first_review_at and review_time_hours from earliest review."""
        # Arrange - create merged PR with reviews but null first_review_at
        pr_created = timezone.now() - timedelta(hours=72)
        merged = timezone.now() - timedelta(hours=2)
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=pr_created,
            merged_at=merged,
            first_review_at=None,  # Missing
            review_time_hours=None,  # Missing
            cycle_time_hours=None,  # Will also be backfilled
        )

        # Create reviews at different times
        earliest_review_time = pr_created + timedelta(hours=6)
        later_review_time = pr_created + timedelta(hours=24)

        PRReviewFactory(team=self.team, pull_request=pr, submitted_at=later_review_time)
        PRReviewFactory(team=self.team, pull_request=pr, submitted_at=earliest_review_time)

        # Act - run the backfill command
        out = StringIO()
        call_command("backfill_pr_timing_metrics", team=self.team.name, stdout=out)

        # Assert - first_review_at should be set to earliest review
        pr.refresh_from_db()
        self.assertEqual(pr.first_review_at, earliest_review_time)

        # Assert - review_time_hours should be calculated
        expected_review_hours = Decimal(str(round((earliest_review_time - pr_created).total_seconds() / 3600, 2)))
        self.assertEqual(pr.review_time_hours, expected_review_hours)

    def test_backfill_skips_prs_that_already_have_timing_metrics(self):
        """Test that backfill skips PRs that already have complete timing metrics."""
        # Arrange - create merged PR with all metrics already populated
        pr_created = timezone.now() - timedelta(hours=48)
        merged = timezone.now() - timedelta(hours=2)
        original_cycle_time = Decimal("45.50")
        original_review_time = Decimal("12.25")

        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=pr_created,
            merged_at=merged,
            cycle_time_hours=original_cycle_time,
            first_review_at=pr_created + timedelta(hours=12),
            review_time_hours=original_review_time,
        )

        # Act - run the backfill command
        out = StringIO()
        call_command("backfill_pr_timing_metrics", team=self.team.name, stdout=out)

        # Assert - metrics should be unchanged
        pr.refresh_from_db()
        self.assertEqual(pr.cycle_time_hours, original_cycle_time)
        self.assertEqual(pr.review_time_hours, original_review_time)

    def test_backfill_outputs_count_of_updated_prs(self):
        """Test that backfill outputs the count of PRs updated."""
        # Arrange - create multiple PRs needing backfill
        pr_created = timezone.now() - timedelta(hours=48)
        merged = timezone.now() - timedelta(hours=2)

        # PR 1: needs cycle_time
        PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=pr_created,
            merged_at=merged,
            cycle_time_hours=None,
        )

        # PR 2: needs cycle_time and review_time
        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=pr_created,
            merged_at=merged,
            cycle_time_hours=None,
            first_review_at=None,
            review_time_hours=None,
        )
        PRReviewFactory(team=self.team, pull_request=pr2, submitted_at=pr_created + timedelta(hours=10))

        # PR 3: already has metrics (should be skipped)
        PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=pr_created,
            merged_at=merged,
            cycle_time_hours=Decimal("46.00"),
        )

        # PR 4: not merged (should be skipped)
        PullRequestFactory(
            team=self.team,
            state="open",
            pr_created_at=pr_created,
            merged_at=None,
            cycle_time_hours=None,
        )

        # Act - run the backfill command
        out = StringIO()
        call_command("backfill_pr_timing_metrics", team=self.team.name, stdout=out)

        # Assert - output should mention 2 PRs updated
        output = out.getvalue()
        self.assertIn("2", output)  # 2 PRs should be updated
        self.assertIn("Updated", output)
