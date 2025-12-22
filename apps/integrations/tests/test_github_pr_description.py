"""Tests for GitHub PR description survey service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.integrations.services.github_pr_description import (
    SURVEY_END_MARKER,
    SURVEY_START_MARKER,
    build_ai_detected_survey_section,
    build_author_survey_section,
    build_survey_section,
    extract_existing_survey_section,
    update_pr_description_with_survey,
)
from apps.metrics.factories import PRSurveyFactory, PullRequestFactory, TeamFactory


class TestSurveyMarkers(TestCase):
    """Tests for survey section markers."""

    def test_survey_start_marker_is_html_comment(self):
        """Test that start marker is an HTML comment."""
        self.assertTrue(SURVEY_START_MARKER.startswith("<!--"))
        self.assertTrue(SURVEY_START_MARKER.endswith("-->"))

    def test_survey_end_marker_is_html_comment(self):
        """Test that end marker is an HTML comment."""
        self.assertTrue(SURVEY_END_MARKER.startswith("<!--"))
        self.assertTrue(SURVEY_END_MARKER.endswith("-->"))

    def test_markers_contain_tformance_identifier(self):
        """Test that markers contain tformance identifier for uniqueness."""
        self.assertIn("tformance", SURVEY_START_MARKER)
        self.assertIn("tformance", SURVEY_END_MARKER)


class TestBuildAuthorSurveySection(TestCase):
    """Tests for build_author_survey_section function."""

    def test_contains_yes_vote_link(self):
        """Test that section contains Yes vote link."""
        survey = PRSurveyFactory.build(token="abc123")
        section = build_author_survey_section(survey, base_url="https://app.example.com")
        self.assertIn("vote=yes", section)
        self.assertIn("abc123", section)

    def test_contains_no_vote_link(self):
        """Test that section contains No vote link."""
        survey = PRSurveyFactory.build(token="abc123")
        section = build_author_survey_section(survey, base_url="https://app.example.com")
        self.assertIn("vote=no", section)

    def test_contains_author_mention(self):
        """Test that section mentions the author."""
        survey = PRSurveyFactory.build(token="abc123")
        survey.pull_request.author.github_username = "alice"
        section = build_author_survey_section(survey, base_url="https://app.example.com")
        self.assertIn("@alice", section)


class TestBuildAIDetectedSurveySection(TestCase):
    """Tests for build_ai_detected_survey_section function."""

    def test_indicates_ai_detected(self):
        """Test that section indicates AI was detected."""
        survey = PRSurveyFactory.build(token="abc123", author_ai_assisted=True)
        section = build_ai_detected_survey_section(survey, base_url="https://app.example.com")
        self.assertIn("AI", section)

    def test_contains_reviewer_vote_links(self):
        """Test that section contains reviewer vote links."""
        survey = PRSurveyFactory.build(token="abc123", author_ai_assisted=True)
        section = build_ai_detected_survey_section(survey, base_url="https://app.example.com")
        self.assertIn("vote=1", section)
        self.assertIn("vote=2", section)
        self.assertIn("vote=3", section)

    def test_no_author_question(self):
        """Test that AI-detected section doesn't ask author question."""
        survey = PRSurveyFactory.build(token="abc123", author_ai_assisted=True)
        section = build_ai_detected_survey_section(survey, base_url="https://app.example.com")
        # Should not contain "Was this PR AI-assisted?" type question
        self.assertNotIn("AI-assisted?", section)


class TestBuildSurveySection(TestCase):
    """Tests for build_survey_section main function."""

    def test_uses_ai_detected_template_when_ai_detected(self):
        """Test that AI-detected template is used when author_ai_assisted is True."""
        survey = PRSurveyFactory.build(token="abc123", author_ai_assisted=True, author_response_source="auto")
        section = build_survey_section(survey, base_url="https://app.example.com")
        # Should indicate AI detected
        self.assertIn("AI", section)
        # Should NOT have author vote links
        self.assertNotIn("vote=yes", section)

    def test_uses_author_template_when_not_ai_detected(self):
        """Test that author template is used when author_ai_assisted is None."""
        survey = PRSurveyFactory.build(token="abc123", author_ai_assisted=None)
        section = build_survey_section(survey, base_url="https://app.example.com")
        # Should have author vote links
        self.assertIn("vote=yes", section)
        self.assertIn("vote=no", section)

    def test_includes_markers(self):
        """Test that section includes start and end markers."""
        survey = PRSurveyFactory.build(token="abc123")
        section = build_survey_section(survey, base_url="https://app.example.com")
        self.assertIn(SURVEY_START_MARKER, section)
        self.assertIn(SURVEY_END_MARKER, section)

    def test_includes_reviewer_links_always(self):
        """Test that reviewer links are always included."""
        survey = PRSurveyFactory.build(token="abc123", author_ai_assisted=None)
        section = build_survey_section(survey, base_url="https://app.example.com")
        self.assertIn("vote=1", section)
        self.assertIn("vote=2", section)
        self.assertIn("vote=3", section)


class TestExtractExistingSurveySection(TestCase):
    """Tests for extract_existing_survey_section function."""

    def test_returns_none_for_empty_body(self):
        """Test that None is returned for empty body."""
        self.assertIsNone(extract_existing_survey_section(""))
        self.assertIsNone(extract_existing_survey_section(None))

    def test_returns_none_when_no_markers(self):
        """Test that None is returned when no survey markers present."""
        body = "# PR Title\n\nSome description"
        self.assertIsNone(extract_existing_survey_section(body))

    def test_extracts_existing_section(self):
        """Test that existing survey section is extracted."""
        body = f"""# PR Title

Some description

{SURVEY_START_MARKER}
## Survey Content
{SURVEY_END_MARKER}

Footer"""
        result = extract_existing_survey_section(body)
        self.assertIn("Survey Content", result)

    def test_returns_none_for_incomplete_markers(self):
        """Test that None is returned if only start marker present."""
        body = f"# PR Title\n\n{SURVEY_START_MARKER}\nContent without end"
        self.assertIsNone(extract_existing_survey_section(body))


class TestUpdatePRDescriptionWithSurvey(TestCase):
    """Tests for update_pr_description_with_survey function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.pr = PullRequestFactory(team=self.team)
        self.survey = PRSurveyFactory(team=self.team, pull_request=self.pr, token="test123")

    @patch("apps.integrations.services.github_pr_description.Github")
    def test_appends_survey_to_empty_description(self, mock_github_class):
        """Test that survey is appended to empty PR description."""
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo
        mock_pr = MagicMock()
        mock_pr.body = ""
        mock_repo.get_pull.return_value = mock_pr

        update_pr_description_with_survey(self.survey, access_token="token123", base_url="https://app.example.com")

        mock_pr.edit.assert_called_once()
        call_kwargs = mock_pr.edit.call_args[1]
        self.assertIn(SURVEY_START_MARKER, call_kwargs["body"])
        self.assertIn(SURVEY_END_MARKER, call_kwargs["body"])

    @patch("apps.integrations.services.github_pr_description.Github")
    def test_appends_survey_to_existing_description(self, mock_github_class):
        """Test that survey is appended to existing PR description."""
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo
        mock_pr = MagicMock()
        mock_pr.body = "# Original Title\n\nOriginal description content."
        mock_repo.get_pull.return_value = mock_pr

        update_pr_description_with_survey(self.survey, access_token="token123", base_url="https://app.example.com")

        mock_pr.edit.assert_called_once()
        call_kwargs = mock_pr.edit.call_args[1]
        # Original content preserved
        self.assertIn("Original Title", call_kwargs["body"])
        self.assertIn("Original description content", call_kwargs["body"])
        # Survey added
        self.assertIn(SURVEY_START_MARKER, call_kwargs["body"])

    @patch("apps.integrations.services.github_pr_description.Github")
    def test_replaces_existing_survey_section(self, mock_github_class):
        """Test that existing survey section is replaced."""
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo
        mock_pr = MagicMock()
        mock_pr.body = f"""# Title

Description

{SURVEY_START_MARKER}
Old survey content
{SURVEY_END_MARKER}

Footer"""
        mock_repo.get_pull.return_value = mock_pr

        update_pr_description_with_survey(self.survey, access_token="token123", base_url="https://app.example.com")

        mock_pr.edit.assert_called_once()
        call_kwargs = mock_pr.edit.call_args[1]
        # Old content NOT present
        self.assertNotIn("Old survey content", call_kwargs["body"])
        # New survey present
        self.assertIn("test123", call_kwargs["body"])
        # Only one pair of markers
        self.assertEqual(call_kwargs["body"].count(SURVEY_START_MARKER), 1)
        self.assertEqual(call_kwargs["body"].count(SURVEY_END_MARKER), 1)

    @patch("apps.integrations.services.github_pr_description.Github")
    def test_uses_correct_repo_and_pr_number(self, mock_github_class):
        """Test that correct repo and PR number are used."""
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo
        mock_pr = MagicMock()
        mock_pr.body = ""
        mock_repo.get_pull.return_value = mock_pr

        self.pr.github_repo = "owner/myrepo"
        self.pr.github_pr_id = 42
        self.pr.save()

        update_pr_description_with_survey(self.survey, access_token="token123", base_url="https://app.example.com")

        mock_github.get_repo.assert_called_with("owner/myrepo")
        mock_repo.get_pull.assert_called_with(42)
