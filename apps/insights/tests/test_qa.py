"""
Tests for the question answering service.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.insights.services.qa import (
    MAX_FUNCTION_CALLS,
    answer_question,
    get_suggested_questions,
)
from apps.metrics.factories import TeamFactory


class TestAnswerQuestion(TestCase):
    """Tests for the answer_question function."""

    def test_returns_error_when_api_key_not_configured(self):
        """Test returns helpful message when API key is missing."""
        team = TeamFactory()

        with override_settings(GOOGLE_AI_API_KEY=""):
            result = answer_question(team, "How is the team doing?")

        self.assertIn("not configured", result.lower())

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    @patch("google.genai.Client")
    def test_returns_text_response_when_no_function_calls(self, mock_client_class):
        """Test returns text when Gemini doesn't call functions."""
        team = TeamFactory()

        # Set up mock response with just text
        mock_part = MagicMock()
        mock_part.function_call = None
        mock_part.text = "The team is doing well."

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = answer_question(team, "How is the team doing?")

        self.assertEqual(result, "The team is doing well.")

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    @patch("google.genai.Client")
    @patch("apps.insights.services.qa.execute_function")
    def test_executes_function_calls(self, mock_execute, mock_client_class):
        """Test executes function calls when Gemini requests them."""
        team = TeamFactory()

        # First response: function call
        mock_fc = MagicMock()
        mock_fc.name = "get_team_metrics"
        mock_fc.args = {"days": 30}

        mock_part_fc = MagicMock()
        mock_part_fc.function_call = mock_fc
        mock_part_fc.text = None

        mock_content_fc = MagicMock()
        mock_content_fc.parts = [mock_part_fc]

        mock_candidate_fc = MagicMock()
        mock_candidate_fc.content = mock_content_fc

        mock_response_fc = MagicMock()
        mock_response_fc.candidates = [mock_candidate_fc]

        # Second response: text
        mock_part_text = MagicMock()
        mock_part_text.function_call = None
        mock_part_text.text = "Based on the metrics, the team is productive."

        mock_content_text = MagicMock()
        mock_content_text.parts = [mock_part_text]

        mock_candidate_text = MagicMock()
        mock_candidate_text.content = mock_content_text

        mock_response_text = MagicMock()
        mock_response_text.candidates = [mock_candidate_text]

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            mock_response_fc,
            mock_response_text,
        ]
        mock_client_class.return_value = mock_client

        mock_execute.return_value = {"total_prs": 50, "merged_prs": 45}

        result = answer_question(team, "How is the team doing?")

        mock_execute.assert_called_once()
        self.assertIn("productive", result)

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    @patch("google.genai.Client")
    def test_handles_empty_candidates(self, mock_client_class):
        """Test handles response with no candidates."""
        team = TeamFactory()

        mock_response = MagicMock()
        mock_response.candidates = []

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = answer_question(team, "How is the team doing?")

        self.assertIn("wasn't able to generate", result.lower())

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    @patch("google.genai.Client")
    def test_handles_api_error(self, mock_client_class):
        """Test handles API errors gracefully."""
        team = TeamFactory()

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        result = answer_question(team, "How is the team doing?")

        self.assertIn("error", result.lower())

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    @patch("google.genai.Client")
    @patch("apps.insights.services.qa.execute_function")
    def test_limits_function_calls(self, mock_execute, mock_client_class):
        """Test limits the number of function calls to prevent loops."""
        team = TeamFactory()

        # Always return a function call (simulating a loop)
        mock_fc = MagicMock()
        mock_fc.name = "get_team_metrics"
        mock_fc.args = {"days": 30}

        mock_part_fc = MagicMock()
        mock_part_fc.function_call = mock_fc
        mock_part_fc.text = None

        mock_content_fc = MagicMock()
        mock_content_fc.parts = [mock_part_fc]

        mock_candidate_fc = MagicMock()
        mock_candidate_fc.content = mock_content_fc

        mock_response_fc = MagicMock()
        mock_response_fc.candidates = [mock_candidate_fc]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response_fc
        mock_client_class.return_value = mock_client

        mock_execute.return_value = {"total_prs": 50}

        result = answer_question(team, "How is the team doing?")

        # Should hit the limit
        self.assertEqual(mock_execute.call_count, MAX_FUNCTION_CALLS)
        self.assertIn("simplify", result.lower())


class TestGetSuggestedQuestions(TestCase):
    """Tests for the get_suggested_questions function."""

    def test_returns_list_of_strings(self):
        """Test returns a list of strings."""
        result = get_suggested_questions()

        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(q, str) for q in result))

    def test_returns_multiple_questions(self):
        """Test returns at least 3 questions."""
        result = get_suggested_questions()

        self.assertGreaterEqual(len(result), 3)

    def test_questions_end_with_punctuation(self):
        """Test all questions end with proper punctuation."""
        result = get_suggested_questions()

        for question in result:
            self.assertTrue(
                question.endswith("?") or question.endswith("."),
                f"Question '{question}' doesn't end with ? or .",
            )
