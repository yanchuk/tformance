"""Tests for GitHub sync service."""

from django.test import TestCase

from apps.integrations.services.github_sync import (
    calculate_reviewer_correlations,
)


class TestCalculateReviewerCorrelations(TestCase):
    """Tests for calculating reviewer agreement correlations."""

    def test_calculates_agreement_for_both_approved(self):
        """Test that both reviewers approving counts as an agreement."""
        from apps.metrics.factories import (
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )
        from apps.metrics.models import ReviewerCorrelation

        # Set up test data
        team = TeamFactory()
        reviewer1 = TeamMemberFactory(team=team, display_name="Alice")
        reviewer2 = TeamMemberFactory(team=team, display_name="Bob")
        pr = PullRequestFactory(team=team)

        # Both reviewers approve the same PR
        PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer1, state="approved")
        PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer2, state="approved")

        # Calculate correlations
        calculate_reviewer_correlations(team)

        # Verify correlation was created
        correlation = ReviewerCorrelation.objects.get(team=team, reviewer_1=reviewer1, reviewer_2=reviewer2)
        self.assertEqual(correlation.prs_reviewed_together, 1)
        self.assertEqual(correlation.agreements, 1)
        self.assertEqual(correlation.disagreements, 0)

    def test_calculates_disagreement_for_mixed_reviews(self):
        """Test that one approve and one changes_requested counts as disagreement."""
        from apps.metrics.factories import (
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )
        from apps.metrics.models import ReviewerCorrelation

        # Set up test data
        team = TeamFactory()
        reviewer1 = TeamMemberFactory(team=team, display_name="Alice")
        reviewer2 = TeamMemberFactory(team=team, display_name="Bob")
        pr = PullRequestFactory(team=team)

        # One approves, one requests changes
        PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer1, state="approved")
        PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer2, state="changes_requested")

        # Calculate correlations
        calculate_reviewer_correlations(team)

        # Verify correlation
        correlation = ReviewerCorrelation.objects.get(team=team, reviewer_1=reviewer1, reviewer_2=reviewer2)
        self.assertEqual(correlation.prs_reviewed_together, 1)
        self.assertEqual(correlation.agreements, 0)
        self.assertEqual(correlation.disagreements, 1)

    def test_aggregates_multiple_prs(self):
        """Test that correlations are aggregated across multiple PRs."""
        from apps.metrics.factories import (
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )
        from apps.metrics.models import ReviewerCorrelation

        # Set up test data
        team = TeamFactory()
        reviewer1 = TeamMemberFactory(team=team, display_name="Alice")
        reviewer2 = TeamMemberFactory(team=team, display_name="Bob")

        # PR 1: Both approve (agreement)
        pr1 = PullRequestFactory(team=team)
        PRReviewFactory(team=team, pull_request=pr1, reviewer=reviewer1, state="approved")
        PRReviewFactory(team=team, pull_request=pr1, reviewer=reviewer2, state="approved")

        # PR 2: One approve, one changes_requested (disagreement)
        pr2 = PullRequestFactory(team=team)
        PRReviewFactory(team=team, pull_request=pr2, reviewer=reviewer1, state="approved")
        PRReviewFactory(team=team, pull_request=pr2, reviewer=reviewer2, state="changes_requested")

        # PR 3: Both changes_requested (agreement)
        pr3 = PullRequestFactory(team=team)
        PRReviewFactory(team=team, pull_request=pr3, reviewer=reviewer1, state="changes_requested")
        PRReviewFactory(team=team, pull_request=pr3, reviewer=reviewer2, state="changes_requested")

        # Calculate correlations
        calculate_reviewer_correlations(team)

        # Verify aggregated correlation
        correlation = ReviewerCorrelation.objects.get(team=team, reviewer_1=reviewer1, reviewer_2=reviewer2)
        self.assertEqual(correlation.prs_reviewed_together, 3)
        self.assertEqual(correlation.agreements, 2)  # PR 1 and PR 3
        self.assertEqual(correlation.disagreements, 1)  # PR 2

    def test_ignores_commented_reviews(self):
        """Test that 'commented' reviews are ignored for agreement calculation."""
        from apps.metrics.factories import (
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )
        from apps.metrics.models import ReviewerCorrelation

        # Set up test data
        team = TeamFactory()
        reviewer1 = TeamMemberFactory(team=team, display_name="Alice")
        reviewer2 = TeamMemberFactory(team=team, display_name="Bob")
        pr = PullRequestFactory(team=team)

        # One approves, one only comments (should not count)
        PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer1, state="approved")
        PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer2, state="commented")

        # Calculate correlations
        calculate_reviewer_correlations(team)

        # No correlation should exist (commented doesn't count)
        self.assertFalse(ReviewerCorrelation.objects.filter(team=team).exists())

    def test_updates_existing_correlations(self):
        """Test that existing correlations are updated, not duplicated."""
        from apps.metrics.factories import (
            PRReviewFactory,
            PullRequestFactory,
            ReviewerCorrelationFactory,
            TeamFactory,
            TeamMemberFactory,
        )
        from apps.metrics.models import ReviewerCorrelation

        # Set up test data
        team = TeamFactory()
        reviewer1 = TeamMemberFactory(team=team, display_name="Alice")
        reviewer2 = TeamMemberFactory(team=team, display_name="Bob")

        # Pre-existing correlation
        ReviewerCorrelationFactory(
            team=team,
            reviewer_1=reviewer1,
            reviewer_2=reviewer2,
            prs_reviewed_together=5,
            agreements=4,
            disagreements=1,
        )

        # New PR with reviews
        pr = PullRequestFactory(team=team)
        PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer1, state="approved")
        PRReviewFactory(team=team, pull_request=pr, reviewer=reviewer2, state="approved")

        # Calculate correlations (should add to existing)
        calculate_reviewer_correlations(team)

        # Should still be only one correlation
        self.assertEqual(ReviewerCorrelation.objects.filter(team=team).count(), 1)
        correlation = ReviewerCorrelation.objects.get(team=team)
        # Old values replaced with fresh calculation from current reviews
        self.assertEqual(correlation.prs_reviewed_together, 1)
        self.assertEqual(correlation.agreements, 1)
