"""Tests for the Gemini client wrapper."""

from unittest.mock import MagicMock

from django.test import TestCase, override_settings


class TestGeminiClientInit(TestCase):
    """Tests for GeminiClient initialization."""

    def test_init_without_api_key_raises_error(self):
        """Test that init raises ValueError without API key."""
        with override_settings(GOOGLE_AI_API_KEY=""):
            from apps.insights.services.gemini_client import GeminiClient

            with self.assertRaises(ValueError) as context:
                GeminiClient()

            self.assertIn("GOOGLE_AI_API_KEY not configured", str(context.exception))

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    def test_init_with_api_key_succeeds(self):
        """Test that init succeeds with API key."""
        from apps.insights.services.gemini_client import GeminiClient

        client = GeminiClient()
        self.assertEqual(client.api_key, "test-api-key")
        self.assertEqual(client.model_name, "gemini-2.0-flash-exp")

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    def test_init_with_custom_model(self):
        """Test that init accepts custom model."""
        from apps.insights.services.gemini_client import GeminiClient

        client = GeminiClient(model="gemini-1.5-pro")
        self.assertEqual(client.model_name, "gemini-1.5-pro")


class TestGeminiClientCostCalculation(TestCase):
    """Tests for cost calculation."""

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    def test_calculate_cost_for_flash_model(self):
        """Test cost calculation for gemini-1.5-flash."""
        from apps.insights.services.gemini_client import GeminiClient

        client = GeminiClient(model="gemini-1.5-flash")

        # 1000 input tokens, 500 output tokens
        cost = client._calculate_cost(1000, 500)

        # Expected: (1000/1M * 0.075) + (500/1M * 0.30) = 0.000075 + 0.00015 = 0.000225
        self.assertAlmostEqual(cost, 0.000225, places=6)

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    def test_calculate_cost_for_free_model(self):
        """Test cost calculation for free preview model."""
        from apps.insights.services.gemini_client import GeminiClient

        client = GeminiClient(model="gemini-2.0-flash-exp")
        cost = client._calculate_cost(10000, 5000)
        self.assertEqual(cost, 0.0)

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    def test_calculate_cost_unknown_model_returns_none(self):
        """Test cost calculation returns None for unknown model."""
        from apps.insights.services.gemini_client import GeminiClient

        client = GeminiClient(model="unknown-model")
        cost = client._calculate_cost(1000, 500)
        self.assertIsNone(cost)


class TestGeminiClientGenerate(TestCase):
    """Tests for generate method with mocked API."""

    @override_settings(GOOGLE_AI_API_KEY="test-api-key", POSTHOG_API_KEY="")
    def test_generate_returns_response(self):
        """Test that generate returns LLMResponse with text."""
        from apps.insights.services.gemini_client import GeminiClient

        # Create mock response
        mock_response = MagicMock()
        mock_response.text = "Generated response text"
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        # Create client and inject mock
        client = GeminiClient()
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.return_value = mock_response
        client._client = mock_genai_client

        # Call generate
        result = client.generate(prompt="Test prompt")

        # Verify response
        self.assertEqual(result.text, "Generated response text")
        self.assertEqual(result.input_tokens, 100)
        self.assertEqual(result.output_tokens, 50)
        self.assertEqual(result.model, "gemini-2.0-flash-exp")
        self.assertGreater(result.latency_ms, 0)

    @override_settings(GOOGLE_AI_API_KEY="test-api-key", POSTHOG_API_KEY="")
    def test_generate_handles_api_error(self):
        """Test that generate raises exception on API error."""
        from apps.insights.services.gemini_client import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = Exception("API Error")
        client._client = mock_genai_client

        with self.assertRaises(Exception) as context:
            client.generate(prompt="Test prompt")

        self.assertIn("API Error", str(context.exception))


class TestGetGeminiClient(TestCase):
    """Tests for get_gemini_client helper function."""

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    def test_get_gemini_client_returns_client(self):
        """Test that get_gemini_client returns configured client."""
        from apps.insights.services.gemini_client import get_gemini_client

        client = get_gemini_client()
        self.assertIsNotNone(client)
        self.assertEqual(client.model_name, "gemini-2.0-flash-exp")

    @override_settings(GOOGLE_AI_API_KEY="test-api-key")
    def test_get_gemini_client_with_model_override(self):
        """Test that get_gemini_client accepts model override."""
        from apps.insights.services.gemini_client import get_gemini_client

        client = get_gemini_client(model="gemini-1.5-pro")
        self.assertEqual(client.model_name, "gemini-1.5-pro")
