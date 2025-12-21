"""
Tests for the insight summarizer service.

Tests the LLM-powered summarization of DailyInsight records.
"""

from datetime import date
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.insights.services.summarizer import (
    format_insights_for_prompt,
    get_summary_cache_key,
    summarize_daily_insights,
)
from apps.metrics.factories import DailyInsightFactory, TeamFactory


class TestFormatInsightsForPrompt(TestCase):
    """Tests for formatting insights into a prompt."""

    def test_formats_empty_insights(self):
        """Test formatting when there are no insights."""
        result = format_insights_for_prompt([])
        self.assertEqual(result, "No insights available for this period.")

    def test_formats_single_insight(self):
        """Test formatting a single insight."""
        team = TeamFactory()
        insight = DailyInsightFactory(
            team=team,
            category="trend",
            priority="high",
            title="Cycle time increased 35%",
            description="Average PR cycle time jumped from 18 hours to 24 hours.",
        )

        result = format_insights_for_prompt([insight])

        self.assertIn("Cycle time increased 35%", result)
        self.assertIn("Average PR cycle time jumped", result)
        self.assertIn("TREND", result)
        self.assertIn("HIGH", result)

    def test_formats_multiple_insights_by_priority(self):
        """Test that multiple insights are formatted with priority ordering."""
        team = TeamFactory()
        low = DailyInsightFactory(team=team, priority="low", title="Low priority item")
        high = DailyInsightFactory(team=team, priority="high", title="High priority item")
        medium = DailyInsightFactory(team=team, priority="medium", title="Medium priority item")

        result = format_insights_for_prompt([low, high, medium])

        # All insights should be present
        self.assertIn("Low priority item", result)
        self.assertIn("High priority item", result)
        self.assertIn("Medium priority item", result)


class TestGetSummaryCacheKey(TestCase):
    """Tests for cache key generation."""

    def test_generates_cache_key_with_team_and_date(self):
        """Test cache key includes team and date."""
        team = TeamFactory()
        target_date = date(2025, 12, 21)

        key = get_summary_cache_key(team, target_date)

        self.assertIn(str(team.id), key)
        self.assertIn("2025-12-21", key)
        self.assertTrue(key.startswith("insight_summary:"))

    def test_different_dates_have_different_keys(self):
        """Test that different dates produce different cache keys."""
        team = TeamFactory()
        key1 = get_summary_cache_key(team, date(2025, 12, 21))
        key2 = get_summary_cache_key(team, date(2025, 12, 20))

        self.assertNotEqual(key1, key2)

    def test_different_teams_have_different_keys(self):
        """Test that different teams produce different cache keys."""
        team1 = TeamFactory()
        team2 = TeamFactory()
        target_date = date(2025, 12, 21)

        key1 = get_summary_cache_key(team1, target_date)
        key2 = get_summary_cache_key(team2, target_date)

        self.assertNotEqual(key1, key2)


class TestSummarizeDailyInsights(TestCase):
    """Tests for the main summarization function."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    def test_returns_no_insights_message_when_empty(self):
        """Test returns appropriate message when no insights exist."""
        team = TeamFactory()

        result = summarize_daily_insights(team)

        self.assertIn("no insights", result.lower())

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    @patch("apps.insights.services.gemini_client.GeminiClient")
    def test_calls_gemini_with_formatted_insights(self, mock_client_class):
        """Test that Gemini is called with properly formatted insights."""
        from datetime import date as date_module

        team = TeamFactory()
        DailyInsightFactory(
            team=team,
            date=date_module.today(),
            category="trend",
            priority="high",
            title="Test insight",
            description="Test description",
        )

        # Set up mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is the AI summary."
        mock_client.generate.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = summarize_daily_insights(team)

        # Verify Gemini was called
        mock_client.generate.assert_called_once()
        call_args = mock_client.generate.call_args

        # Verify prompt contains insight data
        self.assertIn("Test insight", call_args.kwargs["prompt"])
        self.assertEqual(result, "This is the AI summary.")

    @override_settings(
        GOOGLE_AI_API_KEY="test-api-key",
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    )
    @patch("apps.insights.services.gemini_client.GeminiClient")
    def test_caches_result(self, mock_client_class):
        """Test that summarization result is cached."""
        from datetime import date as date_module

        team = TeamFactory()
        DailyInsightFactory(team=team, date=date_module.today(), title="Test insight")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Cached summary"
        mock_client.generate.return_value = mock_response
        mock_client_class.return_value = mock_client

        # First call
        result1 = summarize_daily_insights(team)
        # Second call
        result2 = summarize_daily_insights(team)

        # Gemini should only be called once
        self.assertEqual(mock_client.generate.call_count, 1)
        self.assertEqual(result1, result2)

    @override_settings(
        GOOGLE_AI_API_KEY="test-api-key",
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    )
    @patch("apps.insights.services.gemini_client.GeminiClient")
    def test_skip_cache_parameter(self, mock_client_class):
        """Test that skip_cache bypasses the cache."""
        from datetime import date as date_module

        team = TeamFactory()
        DailyInsightFactory(team=team, date=date_module.today(), title="Test insight")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Fresh summary"
        mock_client.generate.return_value = mock_response
        mock_client_class.return_value = mock_client

        # First call with caching
        summarize_daily_insights(team)
        # Second call with skip_cache
        summarize_daily_insights(team, skip_cache=True)

        # Gemini should be called twice
        self.assertEqual(mock_client.generate.call_count, 2)

    def test_handles_missing_api_key_gracefully(self):
        """Test returns fallback when API key is not configured."""
        from datetime import date as date_module

        team = TeamFactory()
        DailyInsightFactory(team=team, date=date_module.today(), title="Test insight")

        with override_settings(GOOGLE_AI_API_KEY=""):
            result = summarize_daily_insights(team)

        # Should return a fallback message
        self.assertIn("1 insight", result.lower())

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    @patch("apps.insights.services.gemini_client.GeminiClient")
    def test_handles_api_error_gracefully(self, mock_client_class):
        """Test returns fallback when API call fails."""
        from datetime import date as date_module

        team = TeamFactory()
        DailyInsightFactory(team=team, date=date_module.today(), title="Test insight")

        mock_client = MagicMock()
        mock_client.generate.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        result = summarize_daily_insights(team)

        # Should return a fallback message
        self.assertIn("1 insight", result.lower())

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    @patch("apps.insights.services.gemini_client.GeminiClient")
    def test_includes_team_id_in_tracking(self, mock_client_class):
        """Test that team_id is passed for PostHog tracking."""
        from datetime import date as date_module

        team = TeamFactory()
        DailyInsightFactory(team=team, date=date_module.today(), title="Test insight")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Summary"
        mock_client.generate.return_value = mock_response
        mock_client_class.return_value = mock_client

        summarize_daily_insights(team)

        call_args = mock_client.generate.call_args
        self.assertEqual(call_args.kwargs["team_id"], str(team.id))
