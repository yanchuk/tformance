"""Tests for GitHub sync service."""

from django.test import TestCase

from apps.integrations.services.github_sync import (
    calculate_pr_iteration_metrics,
)


class TestCalculatePRIterationMetrics(TestCase):
    """Tests for calculating PR iteration metrics from synced data."""

    def test_calculates_total_comments(self):
        """Test that total_comments counts all PR comments."""
        from apps.metrics.factories import (
            PRCommentFactory,
            PullRequestFactory,
            TeamFactory,
        )

        # Set up test data
        team = TeamFactory()
        pr = PullRequestFactory(team=team, total_comments=None)

        # Create 5 comments
        for i in range(5):
            PRCommentFactory(team=team, pull_request=pr, github_comment_id=1000 + i)

        # Calculate metrics
        calculate_pr_iteration_metrics(pr)

        # Refresh and verify
        pr.refresh_from_db()
        self.assertEqual(pr.total_comments, 5)

    def test_calculates_commits_after_first_review(self):
        """Test that commits_after_first_review counts commits made after the first review."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.metrics.factories import (
            CommitFactory,
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )

        # Set up test data
        team = TeamFactory()
        reviewer = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, commits_after_first_review=None)

        # Create first review at time T
        first_review_time = timezone.now() - timedelta(hours=5)
        PRReviewFactory(
            team=team,
            pull_request=pr,
            reviewer=reviewer,
            submitted_at=first_review_time,
            state="commented",
        )

        # Create commits: 2 before review, 3 after review
        # Commits before first review (should not count)
        CommitFactory(team=team, pull_request=pr, committed_at=first_review_time - timedelta(hours=1))
        CommitFactory(team=team, pull_request=pr, committed_at=first_review_time - timedelta(hours=2))
        # Commits after first review (should count)
        CommitFactory(team=team, pull_request=pr, committed_at=first_review_time + timedelta(hours=1))
        CommitFactory(team=team, pull_request=pr, committed_at=first_review_time + timedelta(hours=2))
        CommitFactory(team=team, pull_request=pr, committed_at=first_review_time + timedelta(hours=3))

        # Calculate metrics
        calculate_pr_iteration_metrics(pr)

        # Refresh and verify
        pr.refresh_from_db()
        self.assertEqual(pr.commits_after_first_review, 3)

    def test_calculates_review_rounds(self):
        """Test that review_rounds counts cycles of changes_requested → commits → re-review."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.metrics.factories import (
            CommitFactory,
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )

        # Set up test data - simulate 2 review rounds
        team = TeamFactory()
        reviewer = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, review_rounds=None)

        base_time = timezone.now() - timedelta(hours=10)

        # Round 1: changes_requested → commit → approval
        PRReviewFactory(
            team=team,
            pull_request=pr,
            reviewer=reviewer,
            submitted_at=base_time,
            state="changes_requested",
        )
        CommitFactory(team=team, pull_request=pr, committed_at=base_time + timedelta(hours=1))
        PRReviewFactory(
            team=team,
            pull_request=pr,
            reviewer=reviewer,
            submitted_at=base_time + timedelta(hours=2),
            state="changes_requested",  # Another round of changes
        )

        # Round 2: changes_requested → commit → approval
        CommitFactory(team=team, pull_request=pr, committed_at=base_time + timedelta(hours=3))
        PRReviewFactory(
            team=team,
            pull_request=pr,
            reviewer=reviewer,
            submitted_at=base_time + timedelta(hours=4),
            state="approved",
        )

        # Calculate metrics
        calculate_pr_iteration_metrics(pr)

        # Refresh and verify - 2 rounds of changes_requested followed by commits
        pr.refresh_from_db()
        self.assertEqual(pr.review_rounds, 2)

    def test_calculates_avg_fix_response_hours(self):
        """Test that avg_fix_response_hours calculates average time from changes_requested to next commit."""
        from datetime import timedelta
        from decimal import Decimal

        from django.utils import timezone

        from apps.metrics.factories import (
            CommitFactory,
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )

        # Set up test data
        team = TeamFactory()
        reviewer = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, avg_fix_response_hours=None)

        base_time = timezone.now() - timedelta(hours=10)

        # First changes_requested → commit after 2 hours
        PRReviewFactory(
            team=team,
            pull_request=pr,
            reviewer=reviewer,
            submitted_at=base_time,
            state="changes_requested",
        )
        CommitFactory(team=team, pull_request=pr, committed_at=base_time + timedelta(hours=2))

        # Second changes_requested → commit after 4 hours
        PRReviewFactory(
            team=team,
            pull_request=pr,
            reviewer=reviewer,
            submitted_at=base_time + timedelta(hours=3),
            state="changes_requested",
        )
        CommitFactory(team=team, pull_request=pr, committed_at=base_time + timedelta(hours=7))

        # Calculate metrics
        calculate_pr_iteration_metrics(pr)

        # Refresh and verify - average of 2 and 4 hours = 3 hours
        pr.refresh_from_db()
        self.assertEqual(pr.avg_fix_response_hours, Decimal("3.00"))

    def test_handles_pr_with_no_reviews(self):
        """Test that metrics are 0 or None for PR with no reviews."""
        from apps.metrics.factories import (
            CommitFactory,
            PullRequestFactory,
            TeamFactory,
        )

        # Set up test data - PR with commits but no reviews
        team = TeamFactory()
        pr = PullRequestFactory(team=team)
        CommitFactory(team=team, pull_request=pr)
        CommitFactory(team=team, pull_request=pr)

        # Calculate metrics
        calculate_pr_iteration_metrics(pr)

        # Refresh and verify
        pr.refresh_from_db()
        self.assertEqual(pr.total_comments, 0)
        self.assertEqual(pr.commits_after_first_review, 0)
        self.assertEqual(pr.review_rounds, 0)
        self.assertIsNone(pr.avg_fix_response_hours)

    def test_handles_only_approved_reviews(self):
        """Test that review_rounds is 0 when only approved reviews exist."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.metrics.factories import (
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )

        # Set up test data - only approved reviews
        team = TeamFactory()
        reviewer = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team)

        base_time = timezone.now() - timedelta(hours=5)
        PRReviewFactory(
            team=team,
            pull_request=pr,
            reviewer=reviewer,
            submitted_at=base_time,
            state="approved",
        )

        # Calculate metrics
        calculate_pr_iteration_metrics(pr)

        # Refresh and verify - no review rounds since no changes_requested
        pr.refresh_from_db()
        self.assertEqual(pr.review_rounds, 0)
        self.assertIsNone(pr.avg_fix_response_hours)
