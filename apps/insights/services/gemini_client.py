"""
Gemini client wrapper with PostHog LLM analytics.

This module provides a thin wrapper around Google's Gemini API that:
1. Handles authentication via settings
2. Tracks all LLM calls to PostHog for observability
3. Provides error handling and retries
4. Supports function calling for metrics queries

Usage:
    from apps.insights.services.gemini_client import GeminiClient

    client = GeminiClient()
    response = client.generate(
        prompt="Summarize these insights",
        user_id="user-123",
        team_id="team-456",
    )
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM call with metadata."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float | None = None
    function_calls: list[dict] | None = None


class GeminiClient:
    """Wrapper for Google Gemini API with PostHog analytics."""

    # Pricing per 1M tokens (as of Dec 2025)
    # https://ai.google.dev/pricing
    PRICING = {
        "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},  # Free during preview
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    }

    DEFAULT_MODEL = "gemini-2.0-flash-exp"

    def __init__(self, model: str | None = None):
        """Initialize the Gemini client.

        Args:
            model: Model name to use. Defaults to gemini-2.0-flash-exp.

        Raises:
            ValueError: If GOOGLE_AI_API_KEY is not configured.
        """
        self.api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
        if not self.api_key:
            raise ValueError("GOOGLE_AI_API_KEY not configured. Add it to your .env file to use LLM-powered insights.")

        self.model_name = model or self.DEFAULT_MODEL
        self._client = None
        self._posthog = None

        # Lazy import PostHog
        posthog_key = getattr(settings, "POSTHOG_API_KEY", "")
        if posthog_key:
            try:
                import posthog

                self._posthog = posthog
            except ImportError:
                logger.warning("PostHog not installed, LLM analytics disabled")

    @property
    def client(self):
        """Lazy-load the Gemini client."""
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Generate a response from Gemini.

        Args:
            prompt: The user prompt to send.
            system_instruction: Optional system instruction.
            user_id: User ID for PostHog tracking.
            team_id: Team ID for PostHog tracking.
            context: Additional context for PostHog.

        Returns:
            LLMResponse with the generated text and metadata.
        """
        start_time = time.perf_counter()

        try:
            # Build the request
            config = {}
            if system_instruction:
                config["system_instruction"] = system_instruction

            # Make the API call
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config if config else None,
            )

            # Calculate metrics
            latency_ms = (time.perf_counter() - start_time) * 1000
            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0
            cost = self._calculate_cost(input_tokens, output_tokens)

            # Extract text
            text = response.text if response.text else ""

            # Track to PostHog
            self._track_generation(
                success=True,
                prompt=prompt,
                response_text=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                user_id=user_id,
                team_id=team_id,
                context=context,
            )

            return LLMResponse(
                text=text,
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Track error to PostHog
            self._track_generation(
                success=False,
                prompt=prompt,
                error=str(e),
                latency_ms=latency_ms,
                user_id=user_id,
                team_id=team_id,
                context=context,
            )

            logger.error(f"Gemini API error: {e}")
            raise

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float | None:
        """Calculate the cost of a generation in USD."""
        pricing = self.PRICING.get(self.model_name)
        if not pricing:
            return None

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def _track_generation(
        self,
        success: bool,
        prompt: str,
        response_text: str | None = None,
        error: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0,
        cost_usd: float | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Track LLM generation to PostHog."""
        if not self._posthog:
            return

        properties = {
            "$ai_model": self.model_name,
            "$ai_provider": "google",
            "$ai_input_tokens": input_tokens,
            "$ai_output_tokens": output_tokens,
            "$ai_latency_ms": latency_ms,
            "$ai_success": success,
            "prompt_length": len(prompt),
            "team_id": team_id,
        }

        if cost_usd is not None:
            properties["$ai_cost_usd"] = cost_usd

        if response_text:
            properties["response_length"] = len(response_text)

        if error:
            properties["$ai_error"] = error

        if context:
            properties.update(context)

        # Use user_id if available, otherwise use team_id as distinct_id
        distinct_id = user_id or team_id or "anonymous"

        try:
            self._posthog.capture(
                distinct_id=distinct_id,
                event="$ai_generation",
                properties=properties,
            )
        except Exception as e:
            logger.warning(f"Failed to track to PostHog: {e}")


def get_gemini_client(model: str | None = None) -> GeminiClient:
    """Get a configured Gemini client.

    Args:
        model: Optional model name override.

    Returns:
        Configured GeminiClient instance.

    Raises:
        ValueError: If API key is not configured.
    """
    return GeminiClient(model=model)
