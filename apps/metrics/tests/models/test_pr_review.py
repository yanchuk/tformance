from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    PRReview,
    PullRequest,
    TeamMember,
)
from apps.teams.context import current_team, get_current_team, set_current_team, unset_current_team
from apps.teams.models import Team


class TestPRReviewModel(TestCase):
    """Tests for PRReview model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(team=self.team, display_name="Author", github_username="author")
        self.reviewer = TeamMember.objects.create(team=self.team, display_name="Reviewer", github_username="reviewer")
        self.pull_request = PullRequest.objects.create(
            team=self.team, github_pr_id=1, github_repo="org/repo", state="open", author=self.author
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_review_creation_linked_to_pull_request(self):
        """Test that PRReview can be created linked to a PullRequest."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertEqual(review.pull_request, self.pull_request)
        self.assertEqual(review.reviewer, self.reviewer)
        self.assertEqual(review.state, "approved")
        self.assertIsNotNone(review.pk)

    def test_pr_review_state_choice_approved(self):
        """Test that PRReview state 'approved' works correctly."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertEqual(review.state, "approved")

    def test_pr_review_state_choice_changes_requested(self):
        """Test that PRReview state 'changes_requested' works correctly."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="changes_requested"
        )
        self.assertEqual(review.state, "changes_requested")

    def test_pr_review_state_choice_commented(self):
        """Test that PRReview state 'commented' works correctly."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="commented"
        )
        self.assertEqual(review.state, "commented")

    def test_pr_review_cascade_delete_when_pull_request_deleted(self):
        """Test that PRReview is cascade deleted when PullRequest is deleted."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        review_id = review.pk

        # Delete the pull request
        self.pull_request.delete()

        # Verify review is also deleted
        with self.assertRaises(PRReview.DoesNotExist):
            PRReview.objects.get(pk=review_id)

    def test_pr_review_reviewer_fk_with_set_null(self):
        """Test that PRReview.reviewer FK uses SET_NULL when TeamMember is deleted."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertEqual(review.reviewer, self.reviewer)

        # Delete the reviewer
        self.reviewer.delete()

        # Refresh review from database
        review.refresh_from_db()
        self.assertIsNone(review.reviewer)

    def test_pr_review_submitted_at_can_be_set(self):
        """Test that PRReview.submitted_at can be set."""
        submitted = django_timezone.now()
        review = PRReview.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            reviewer=self.reviewer,
            state="approved",
            submitted_at=submitted,
        )
        self.assertEqual(review.submitted_at, submitted)

    def test_pr_review_str_returns_useful_representation(self):
        """Test that PRReview.__str__ returns a useful representation."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        str_repr = str(review)
        # Should contain key identifying information
        self.assertIsNotNone(str_repr)
        self.assertIsInstance(str_repr, str)

    def test_pr_review_has_created_at_from_base_model(self):
        """Test that PRReview inherits created_at from BaseModel."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertIsNotNone(review.created_at)

    def test_pr_review_has_updated_at_from_base_model(self):
        """Test that PRReview inherits updated_at from BaseModel."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertIsNotNone(review.updated_at)

    def test_pr_review_for_team_manager_filters_by_current_team(self):
        """Test that PRReview.for_team manager filters by current team context."""
        # Create another team and related objects
        team2 = Team.objects.create(name="Team Two", slug="team-two")
        author2 = TeamMember.objects.create(team=team2, display_name="Author 2", github_username="author2")
        reviewer2 = TeamMember.objects.create(team=team2, display_name="Reviewer 2", github_username="reviewer2")
        pr2 = PullRequest.objects.create(
            team=team2, github_pr_id=2, github_repo="org/repo", state="open", author=author2
        )

        # Create reviews for both teams
        review1 = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        review2 = PRReview.objects.create(team=team2, pull_request=pr2, reviewer=reviewer2, state="approved")

        # Set team1 as current and verify filtering
        set_current_team(self.team)
        team1_reviews = list(PRReview.for_team.all())
        self.assertEqual(len(team1_reviews), 1)
        self.assertEqual(team1_reviews[0].pk, review1.pk)

        # Set team2 as current and verify filtering
        set_current_team(team2)
        team2_reviews = list(PRReview.for_team.all())
        self.assertEqual(len(team2_reviews), 1)
        self.assertEqual(team2_reviews[0].pk, review2.pk)

    def test_pr_review_for_team_manager_with_context_manager(self):
        """Test that PRReview.for_team works with context manager."""
        # Create another team and related objects
        team2 = Team.objects.create(name="Team Two", slug="team-two")
        author2 = TeamMember.objects.create(team=team2, display_name="Author 2", github_username="author2")
        reviewer2 = TeamMember.objects.create(team=team2, display_name="Reviewer 2", github_username="reviewer2")
        pr2 = PullRequest.objects.create(
            team=team2, github_pr_id=3, github_repo="org/repo", state="open", author=author2
        )

        # Create reviews for both teams
        PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        PRReview.objects.create(team=team2, pull_request=pr2, reviewer=reviewer2, state="approved")

        with current_team(self.team):
            self.assertEqual(PRReview.for_team.count(), 1)

        with current_team(team2):
            self.assertEqual(PRReview.for_team.count(), 1)

    def test_pr_review_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that PRReview.for_team returns empty queryset when no team is set."""
        PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(PRReview.for_team.count(), 0)

    def test_pr_review_multiple_reviews_on_same_pr(self):
        """Test that multiple reviews can be created for the same pull request."""
        reviewer2 = TeamMember.objects.create(team=self.team, display_name="Reviewer 2", github_username="reviewer2")

        review1 = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        review2 = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=reviewer2, state="changes_requested"
        )

        # Both reviews should exist for the same PR
        self.assertEqual(review1.pull_request, review2.pull_request)
        self.assertNotEqual(review1.reviewer, review2.reviewer)
        self.assertEqual(self.pull_request.reviews.count(), 2)
