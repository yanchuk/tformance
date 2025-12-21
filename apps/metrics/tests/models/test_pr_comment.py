from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    PRComment,
    PullRequest,
    TeamMember,
)
from apps.teams.context import unset_current_team
from apps.teams.models import Team


class TestPRCommentModel(TestCase):
    """Tests for PRComment model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(
            team=self.team,
            display_name="John Doe",
            github_username="johndoe",
            github_id="123",
        )
        self.reviewer = TeamMember.objects.create(
            team=self.team,
            display_name="Jane Smith",
            github_username="janesmith",
            github_id="456",
        )
        self.pull_request = PullRequest.objects.create(
            team=self.team,
            github_pr_id=1,
            github_repo="org/repo",
            title="Test PR",
            author=self.author,
            state="open",
            pr_created_at=django_timezone.now(),
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_comment_creation(self):
        """Test that PRComment can be created with all required fields."""
        comment_created = django_timezone.now()
        comment_updated = comment_created + django_timezone.timedelta(hours=1)

        comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=12345,
            pull_request=self.pull_request,
            author=self.author,
            body="This is a test comment",
            comment_type="issue",
            comment_created_at=comment_created,
            comment_updated_at=comment_updated,
        )
        self.assertEqual(comment.github_comment_id, 12345)
        self.assertEqual(comment.pull_request, self.pull_request)
        self.assertEqual(comment.author, self.author)
        self.assertEqual(comment.body, "This is a test comment")
        self.assertEqual(comment.comment_type, "issue")
        self.assertIsNone(comment.path)
        self.assertIsNone(comment.line)
        self.assertIsNone(comment.in_reply_to_id)
        self.assertEqual(comment.comment_created_at, comment_created)
        self.assertEqual(comment.comment_updated_at, comment_updated)
        self.assertIsNotNone(comment.pk)

    def test_pr_comment_team_relationship(self):
        """Test that PRComment belongs to the correct team."""
        comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=12345,
            pull_request=self.pull_request,
            author=self.author,
            body="Team test comment",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(comment.team, self.team)

    def test_pr_comment_unique_constraint(self):
        """Test that unique constraint on (team, github_comment_id) is enforced."""
        PRComment.objects.create(
            team=self.team,
            github_comment_id=99999,
            pull_request=self.pull_request,
            author=self.author,
            body="First comment",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        # Attempt to create another comment with same team and github_comment_id
        with self.assertRaises(IntegrityError):
            PRComment.objects.create(
                team=self.team,
                github_comment_id=99999,
                pull_request=self.pull_request,
                author=self.reviewer,
                body="Duplicate comment",
                comment_type="issue",
                comment_created_at=django_timezone.now(),
            )

    def test_pr_comment_str_representation(self):
        """Test that PRComment __str__ returns meaningful string."""
        comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=12345,
            pull_request=self.pull_request,
            author=self.author,
            body="This is a very long comment body that should be truncated in the string representation",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        str_repr = str(comment)
        self.assertIsNotNone(str_repr)
        self.assertNotEqual(str_repr, "")
        # Should contain some identifying information
        self.assertTrue(
            "comment" in str_repr.lower() or "12345" in str_repr or str(self.pull_request.github_pr_id) in str_repr
        )

    def test_pr_comment_author_relationship(self):
        """Test that PRComment has correct optional FK relationship with TeamMember."""
        # Test with author
        comment_with_author = PRComment.objects.create(
            team=self.team,
            github_comment_id=11111,
            pull_request=self.pull_request,
            author=self.author,
            body="Comment with author",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(comment_with_author.author, self.author)

        # Test without author (null=True)
        comment_no_author = PRComment.objects.create(
            team=self.team,
            github_comment_id=22222,
            pull_request=self.pull_request,
            author=None,
            body="Comment without author",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertIsNone(comment_no_author.author)

    def test_pr_comment_pull_request_relationship(self):
        """Test that PRComment has correct required FK relationship with PullRequest."""
        comment1 = PRComment.objects.create(
            team=self.team,
            github_comment_id=33333,
            pull_request=self.pull_request,
            author=self.author,
            body="First comment on PR",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        comment2 = PRComment.objects.create(
            team=self.team,
            github_comment_id=44444,
            pull_request=self.pull_request,
            author=self.reviewer,
            body="Second comment on PR",
            comment_type="review",
            path="src/app.py",
            line=42,
            comment_created_at=django_timezone.now(),
        )

        # Test forward relationship
        self.assertEqual(comment1.pull_request, self.pull_request)
        self.assertEqual(comment2.pull_request, self.pull_request)

        # Test reverse relationship via related_name='comments'
        comments = self.pull_request.comments.all()
        self.assertEqual(comments.count(), 2)
        self.assertIn(comment1, comments)
        self.assertIn(comment2, comments)

    def test_pr_comment_type_choices(self):
        """Test that PRComment validates comment_type choices (issue vs review)."""
        # Test "issue" type
        issue_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=55555,
            pull_request=self.pull_request,
            author=self.author,
            body="Issue comment",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(issue_comment.comment_type, "issue")

        # Test "review" type
        review_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=66666,
            pull_request=self.pull_request,
            author=self.reviewer,
            body="Review comment",
            comment_type="review",
            path="src/utils.py",
            line=10,
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(review_comment.comment_type, "review")

    def test_pr_comment_review_fields(self):
        """Test that path and line fields work correctly for review comments."""
        # Review comment with path and line
        review_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=77777,
            pull_request=self.pull_request,
            author=self.reviewer,
            body="Please fix this line",
            comment_type="review",
            path="src/components/Button.tsx",
            line=25,
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(review_comment.path, "src/components/Button.tsx")
        self.assertEqual(review_comment.line, 25)

        # Issue comment without path and line
        issue_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=88888,
            pull_request=self.pull_request,
            author=self.author,
            body="General comment",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertIsNone(issue_comment.path)
        self.assertIsNone(issue_comment.line)

        # Review comment with in_reply_to_id for threaded comments
        reply_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=99998,
            pull_request=self.pull_request,
            author=self.author,
            body="Thanks for the feedback",
            comment_type="review",
            path="src/components/Button.tsx",
            line=25,
            in_reply_to_id=77777,
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(reply_comment.in_reply_to_id, 77777)
