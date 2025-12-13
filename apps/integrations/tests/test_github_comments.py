"""Tests for GitHub comment service that posts survey invitations to PRs."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_comments import build_survey_comment_body, post_survey_comment
from apps.metrics.factories import (
    PRReviewFactory,
    PRSurveyFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)


class TestBuildSurveyCommentBody(TestCase):
    """Tests for building survey comment markdown with @mentions and URLs."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, github_username="author_user")
        self.reviewer1 = TeamMemberFactory(team=self.team, github_username="reviewer_one")
        self.reviewer2 = TeamMemberFactory(team=self.team, github_username="reviewer_two")
        self.pr = PullRequestFactory(team=self.team, author=self.author, state="merged")

    def test_build_survey_comment_body_generates_correct_markdown(self):
        """Test that build_survey_comment_body generates markdown with correct structure."""
        # Arrange
        survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author, token="test_token_123")
        PRReviewFactory(team=self.team, pull_request=self.pr, reviewer=self.reviewer1)

        # Act
        result = build_survey_comment_body(self.pr, survey)

        # Assert
        self.assertIsInstance(result, str)
        self.assertIn("@", result)  # Should contain @mentions
        self.assertIn("survey", result.lower())  # Should mention survey
        self.assertIn("http", result)  # Should contain URLs

    def test_comment_includes_author_mention(self):
        """Test that comment includes @mention for the PR author."""
        # Arrange
        survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author, token="test_token_456")

        # Act
        result = build_survey_comment_body(self.pr, survey)

        # Assert
        self.assertIn(f"@{self.author.github_username}", result)

    def test_comment_includes_all_reviewer_mentions(self):
        """Test that comment includes @mentions for all reviewers."""
        # Arrange
        survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author, token="test_token_789")
        PRReviewFactory(team=self.team, pull_request=self.pr, reviewer=self.reviewer1)
        PRReviewFactory(team=self.team, pull_request=self.pr, reviewer=self.reviewer2)

        # Act
        result = build_survey_comment_body(self.pr, survey)

        # Assert
        self.assertIn(f"@{self.reviewer1.github_username}", result)
        self.assertIn(f"@{self.reviewer2.github_username}", result)

    def test_comment_includes_absolute_survey_urls(self):
        """Test that comment includes absolute URLs for surveys (not relative paths)."""
        # Arrange
        survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author, token="test_token_abc")
        PRReviewFactory(team=self.team, pull_request=self.pr, reviewer=self.reviewer1)

        # Act
        result = build_survey_comment_body(self.pr, survey)

        # Assert
        # Should contain absolute URLs starting with http:// or https://
        self.assertRegex(result, r"https?://[^\s]+/survey/test_token_abc")

    def test_comment_includes_author_survey_link(self):
        """Test that comment includes link to author survey endpoint."""
        # Arrange
        survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author, token="test_token_def")

        # Act
        result = build_survey_comment_body(self.pr, survey)

        # Assert
        # Author should get link to /author/ endpoint
        self.assertIn("/survey/test_token_def/author/", result)

    def test_comment_includes_reviewer_survey_link(self):
        """Test that comment includes link to reviewer survey endpoint."""
        # Arrange
        survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author, token="test_token_ghi")
        PRReviewFactory(team=self.team, pull_request=self.pr, reviewer=self.reviewer1)

        # Act
        result = build_survey_comment_body(self.pr, survey)

        # Assert
        # Reviewers should get link to /reviewer/ endpoint
        self.assertIn("/survey/test_token_ghi/reviewer/", result)

    def test_comment_handles_pr_with_no_reviewers(self):
        """Test that comment works correctly when PR has only author, no reviewers."""
        # Arrange
        survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author, token="test_token_jkl")
        # No reviewers created

        # Act
        result = build_survey_comment_body(self.pr, survey)

        # Assert
        # Should still contain author mention
        self.assertIn(f"@{self.author.github_username}", result)
        # Should contain author survey link
        self.assertIn("/survey/test_token_jkl/author/", result)
        # Should not crash
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestPostSurveyComment(TestCase):
    """Tests for posting survey comments to GitHub PRs."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, github_username="pr_author")
        self.pr = PullRequestFactory(
            team=self.team, author=self.author, state="merged", github_repo="org/test-repo", github_pr_id=42
        )
        self.survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author, token="test_token_post")

    @patch("apps.integrations.services.github_client.get_github_client")
    def test_post_survey_comment_calls_github_api(self, mock_get_client):
        """Test that post_survey_comment calls GitHub API with correct parameters."""
        # Arrange
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = 98765

        mock_get_client.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue
        mock_issue.create_comment.return_value = mock_comment

        access_token = "gho_test_token"

        # Act
        post_survey_comment(self.pr, self.survey, access_token)

        # Assert
        mock_get_client.assert_called_once_with(access_token)
        mock_github.get_repo.assert_called_once_with("org/test-repo")
        mock_repo.get_issue.assert_called_once_with(42)
        mock_issue.create_comment.assert_called_once()

    @patch("apps.integrations.services.github_client.get_github_client")
    def test_post_survey_comment_passes_comment_body_to_github(self, mock_get_client):
        """Test that post_survey_comment passes the comment body to GitHub."""
        # Arrange
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = 12345

        mock_get_client.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue
        mock_issue.create_comment.return_value = mock_comment

        access_token = "gho_test_token"

        # Act
        post_survey_comment(self.pr, self.survey, access_token)

        # Assert
        # Should call create_comment with a string body
        call_args = mock_issue.create_comment.call_args
        self.assertEqual(len(call_args[0]), 1)  # One positional argument
        comment_body = call_args[0][0]
        self.assertIsInstance(comment_body, str)
        self.assertGreater(len(comment_body), 0)

    @patch("apps.integrations.services.github_client.get_github_client")
    def test_post_survey_comment_returns_comment_id(self, mock_get_client):
        """Test that post_survey_comment returns the GitHub comment ID."""
        # Arrange
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = 555666

        mock_get_client.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue
        mock_issue.create_comment.return_value = mock_comment

        access_token = "gho_test_token"

        # Act
        result = post_survey_comment(self.pr, self.survey, access_token)

        # Assert
        self.assertEqual(result, 555666)

    @patch("apps.integrations.services.github_client.get_github_client")
    def test_post_survey_comment_stores_comment_id_on_survey(self, mock_get_client):
        """Test that post_survey_comment stores the comment ID on the survey object."""
        # Arrange
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_issue = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = 777888

        mock_get_client.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_issue.return_value = mock_issue
        mock_issue.create_comment.return_value = mock_comment

        access_token = "gho_test_token"

        # Ensure survey starts without comment ID
        self.assertIsNone(self.survey.github_comment_id)

        # Act
        post_survey_comment(self.pr, self.survey, access_token)

        # Assert
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.github_comment_id, 777888)
