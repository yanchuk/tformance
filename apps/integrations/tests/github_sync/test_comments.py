"""Tests for GitHub sync service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_sync import (
    sync_pr_issue_comments,
    sync_pr_review_comments,
)


class TestSyncPRIssueComments(TestCase):
    """Tests for sync_pr_issue_comments function (general PR comments)."""

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_issue_comments_creates_records(self, mock_github_class):
        """Test that sync_pr_issue_comments creates PRComment records from GitHub API."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRComment

        # Set up test data
        team = TeamFactory()
        author = TeamMemberFactory(team=team, github_id="12345")
        commenter = TeamMemberFactory(team=team, github_id="67890")
        pr = PullRequestFactory(team=team, author=author)

        # Mock GitHub API - issue comments
        mock_comment1 = MagicMock()
        mock_comment1.id = 111111
        mock_comment1.body = "Looks good to me!"
        mock_comment1.created_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_comment1.updated_at = datetime(2025, 1, 1, 12, 5, 0, tzinfo=UTC)
        mock_comment1.user.id = 67890
        mock_comment1.user.login = "commenter"

        mock_comment2 = MagicMock()
        mock_comment2.id = 222222
        mock_comment2.body = "Please address the TODO comments"
        mock_comment2.created_at = datetime(2025, 1, 2, 10, 0, 0, tzinfo=UTC)
        mock_comment2.updated_at = datetime(2025, 1, 2, 10, 0, 0, tzinfo=UTC)
        mock_comment2.user.id = 67890
        mock_comment2.user.login = "commenter"

        # Mock PyGithub chain
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = [mock_comment1, mock_comment2]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        comments_synced = sync_pr_issue_comments(
            pr=pr,
            pr_number=pr.github_pr_id,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify comments were created
        self.assertEqual(comments_synced, 2)
        self.assertEqual(PRComment.objects.filter(team=team, pull_request=pr, comment_type="issue").count(), 2)

        # Verify first comment data
        comment1 = PRComment.objects.get(team=team, github_comment_id=111111)
        self.assertEqual(comment1.body, "Looks good to me!")
        self.assertEqual(comment1.comment_type, "issue")
        self.assertEqual(comment1.author, commenter)
        self.assertEqual(comment1.pull_request, pr)
        self.assertIsNone(comment1.path)  # Issue comments don't have path
        self.assertIsNone(comment1.line)  # Issue comments don't have line

        # Verify second comment data
        comment2 = PRComment.objects.get(team=team, github_comment_id=222222)
        self.assertEqual(comment2.body, "Please address the TODO comments")
        self.assertEqual(comment2.comment_type, "issue")

        # Verify no errors
        self.assertEqual(len(errors), 0)

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_issue_comments_maps_author(self, mock_github_class):
        """Test that sync_pr_issue_comments maps comment author to TeamMember by github_id."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRComment

        # Set up test data
        team = TeamFactory()
        known_member = TeamMemberFactory(team=team, github_id="99999", display_name="Known User")
        pr = PullRequestFactory(team=team)

        # Mock GitHub API - comment from known user
        mock_comment = MagicMock()
        mock_comment.id = 333333
        mock_comment.body = "Comment from known user"
        mock_comment.created_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_comment.updated_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_comment.user.id = 99999  # Matches known_member.github_id
        mock_comment.user.login = "known_user"

        # Mock PyGithub chain
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = [mock_comment]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        comments_synced = sync_pr_issue_comments(
            pr=pr,
            pr_number=pr.github_pr_id,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify author mapping
        self.assertEqual(comments_synced, 1)
        comment = PRComment.objects.get(team=team, github_comment_id=333333)
        self.assertEqual(comment.author, known_member)
        self.assertEqual(comment.author.display_name, "Known User")

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_issue_comments_updates_existing(self, mock_github_class):
        """Test that sync_pr_issue_comments updates existing comment if already synced."""
        from apps.metrics.factories import PRCommentFactory, PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRComment

        # Set up test data
        team = TeamFactory()
        pr = PullRequestFactory(team=team)
        member = TeamMemberFactory(team=team, github_id="55555")

        # Create existing comment in DB
        PRCommentFactory(
            team=team,
            pull_request=pr,
            github_comment_id=444444,
            body="Original comment text",
            comment_type="issue",
        )

        # Mock GitHub API - same comment ID but updated body
        mock_comment = MagicMock()
        mock_comment.id = 444444  # Same ID as existing
        mock_comment.body = "Updated comment text"  # Different body
        mock_comment.created_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_comment.updated_at = datetime(2025, 1, 1, 15, 0, 0, tzinfo=UTC)  # Updated 3 hours later
        mock_comment.user.id = 55555
        mock_comment.user.login = "member"

        # Mock PyGithub chain
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = [mock_comment]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        comments_synced = sync_pr_issue_comments(
            pr=pr,
            pr_number=pr.github_pr_id,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify comment was updated, not duplicated
        self.assertEqual(comments_synced, 1)
        self.assertEqual(PRComment.objects.filter(team=team, github_comment_id=444444).count(), 1)

        # Verify updated data
        comment = PRComment.objects.get(team=team, github_comment_id=444444)
        self.assertEqual(comment.body, "Updated comment text")
        self.assertEqual(comment.author, member)

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_issue_comments_handles_api_error(self, mock_github_class):
        """Test that sync_pr_issue_comments accumulates errors on GitHub API failure."""
        from github import GithubException

        from apps.metrics.factories import PullRequestFactory, TeamFactory
        from apps.metrics.models import PRComment

        # Set up test data
        team = TeamFactory()
        pr = PullRequestFactory(team=team)

        # Mock PyGithub to raise exception
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.side_effect = GithubException(403, {"message": "Forbidden"})

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        comments_synced = sync_pr_issue_comments(
            pr=pr,
            pr_number=pr.github_pr_id,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify error was accumulated (not raised)
        self.assertEqual(comments_synced, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("issue comments", errors[0])

        # Verify no comments were created
        self.assertEqual(PRComment.objects.filter(team=team, pull_request=pr).count(), 0)


class TestSyncPRReviewComments(TestCase):
    """Tests for sync_pr_review_comments function (inline code review comments)."""

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_review_comments_creates_records(self, mock_github_class):
        """Test that sync_pr_review_comments creates PRComment records from GitHub API."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRComment

        # Set up test data
        team = TeamFactory()
        author = TeamMemberFactory(team=team, github_id="12345")
        reviewer = TeamMemberFactory(team=team, github_id="67890")
        pr = PullRequestFactory(team=team, author=author)

        # Mock GitHub API - review comments (inline code comments)
        mock_comment1 = MagicMock()
        mock_comment1.id = 555555
        mock_comment1.body = "This function could be simplified"
        mock_comment1.path = "src/utils.py"
        mock_comment1.line = 42
        mock_comment1.created_at = datetime(2025, 1, 1, 14, 0, 0, tzinfo=UTC)
        mock_comment1.updated_at = datetime(2025, 1, 1, 14, 0, 0, tzinfo=UTC)
        mock_comment1.user.id = 67890
        mock_comment1.user.login = "reviewer"
        mock_comment1.in_reply_to_id = None

        mock_comment2 = MagicMock()
        mock_comment2.id = 666666
        mock_comment2.body = "Consider using a list comprehension here"
        mock_comment2.path = "src/app.py"
        mock_comment2.line = 123
        mock_comment2.created_at = datetime(2025, 1, 1, 15, 0, 0, tzinfo=UTC)
        mock_comment2.updated_at = datetime(2025, 1, 1, 15, 0, 0, tzinfo=UTC)
        mock_comment2.user.id = 67890
        mock_comment2.user.login = "reviewer"
        mock_comment2.in_reply_to_id = None

        # Mock PyGithub chain
        mock_pr = MagicMock()
        mock_pr.get_review_comments.return_value = [mock_comment1, mock_comment2]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        comments_synced = sync_pr_review_comments(
            pr=pr,
            pr_number=pr.github_pr_id,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify comments were created
        self.assertEqual(comments_synced, 2)
        self.assertEqual(PRComment.objects.filter(team=team, pull_request=pr, comment_type="review").count(), 2)

        # Verify first comment data
        comment1 = PRComment.objects.get(team=team, github_comment_id=555555)
        self.assertEqual(comment1.body, "This function could be simplified")
        self.assertEqual(comment1.comment_type, "review")
        self.assertEqual(comment1.author, reviewer)
        self.assertEqual(comment1.path, "src/utils.py")
        self.assertEqual(comment1.line, 42)
        self.assertIsNone(comment1.in_reply_to_id)

        # Verify second comment data
        comment2 = PRComment.objects.get(team=team, github_comment_id=666666)
        self.assertEqual(comment2.path, "src/app.py")
        self.assertEqual(comment2.line, 123)

        # Verify no errors
        self.assertEqual(len(errors), 0)

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_review_comments_includes_path_and_line(self, mock_github_class):
        """Test that sync_pr_review_comments stores path and line for inline comments."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRComment

        # Set up test data
        team = TeamFactory()
        TeamMemberFactory(team=team, github_id="11111")  # Create reviewer
        pr = PullRequestFactory(team=team)

        # Mock GitHub API - review comment with path and line
        mock_comment = MagicMock()
        mock_comment.id = 777777
        mock_comment.body = "Potential null pointer here"
        mock_comment.path = "src/controllers/user_controller.py"
        mock_comment.line = 256
        mock_comment.created_at = datetime(2025, 1, 1, 16, 0, 0, tzinfo=UTC)
        mock_comment.updated_at = datetime(2025, 1, 1, 16, 0, 0, tzinfo=UTC)
        mock_comment.user.id = 11111
        mock_comment.user.login = "reviewer"
        mock_comment.in_reply_to_id = None

        # Mock PyGithub chain
        mock_pr = MagicMock()
        mock_pr.get_review_comments.return_value = [mock_comment]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        comments_synced = sync_pr_review_comments(
            pr=pr,
            pr_number=pr.github_pr_id,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify path and line are stored
        self.assertEqual(comments_synced, 1)
        comment = PRComment.objects.get(team=team, github_comment_id=777777)
        self.assertEqual(comment.path, "src/controllers/user_controller.py")
        self.assertEqual(comment.line, 256)
        self.assertEqual(comment.comment_type, "review")

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_review_comments_handles_reply_thread(self, mock_github_class):
        """Test that sync_pr_review_comments handles threaded reply comments."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
        from apps.metrics.models import PRComment

        # Set up test data
        team = TeamFactory()
        reviewer = TeamMemberFactory(team=team, github_id="22222")
        author = TeamMemberFactory(team=team, github_id="33333")
        pr = PullRequestFactory(team=team)

        # Mock GitHub API - original comment and reply
        mock_original = MagicMock()
        mock_original.id = 888888
        mock_original.body = "Why did you choose this approach?"
        mock_original.path = "src/models.py"
        mock_original.line = 99
        mock_original.created_at = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        mock_original.updated_at = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        mock_original.user.id = 22222
        mock_original.user.login = "reviewer"
        mock_original.in_reply_to_id = None

        mock_reply = MagicMock()
        mock_reply.id = 999999
        mock_reply.body = "This approach is more efficient for large datasets"
        mock_reply.path = "src/models.py"
        mock_reply.line = 99
        mock_reply.created_at = datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC)
        mock_reply.updated_at = datetime(2025, 1, 1, 11, 0, 0, tzinfo=UTC)
        mock_reply.user.id = 33333
        mock_reply.user.login = "author"
        mock_reply.in_reply_to_id = 888888  # Reply to original

        # Mock PyGithub chain
        mock_pr = MagicMock()
        mock_pr.get_review_comments.return_value = [mock_original, mock_reply]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        comments_synced = sync_pr_review_comments(
            pr=pr,
            pr_number=pr.github_pr_id,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify both comments were created
        self.assertEqual(comments_synced, 2)

        # Verify original comment
        original = PRComment.objects.get(team=team, github_comment_id=888888)
        self.assertEqual(original.author, reviewer)
        self.assertIsNone(original.in_reply_to_id)

        # Verify reply has in_reply_to_id set
        reply = PRComment.objects.get(team=team, github_comment_id=999999)
        self.assertEqual(reply.author, author)
        self.assertEqual(reply.in_reply_to_id, 888888)

    @patch("apps.integrations.services.github_sync.processors.Github")
    def test_sync_pr_review_comments_handles_api_error(self, mock_github_class):
        """Test that sync_pr_review_comments accumulates errors on GitHub API failure."""
        from github import GithubException

        from apps.metrics.factories import PullRequestFactory, TeamFactory
        from apps.metrics.models import PRComment

        # Set up test data
        team = TeamFactory()
        pr = PullRequestFactory(team=team)

        # Mock PyGithub to raise exception
        mock_pr = MagicMock()
        mock_pr.get_review_comments.side_effect = GithubException(500, {"message": "Internal Server Error"})

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr

        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Call sync function
        errors = []
        comments_synced = sync_pr_review_comments(
            pr=pr,
            pr_number=pr.github_pr_id,
            access_token="fake-token",
            repo_full_name="acme/repo",
            team=team,
            errors=errors,
        )

        # Verify error was accumulated (not raised)
        self.assertEqual(comments_synced, 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("review comments", errors[0])

        # Verify no comments were created
        self.assertEqual(PRComment.objects.filter(team=team, pull_request=pr).count(), 0)
