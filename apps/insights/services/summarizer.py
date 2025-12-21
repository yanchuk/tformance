"""
Insight summarizer service.

Provides LLM-powered summarization of DailyInsight records for teams.
Uses Gemini API with caching to avoid redundant API calls.
"""

import logging
from datetime import date

from django.conf import settings
from django.core.cache import cache

from apps.metrics.models import DailyInsight

logger = logging.getLogger(__name__)

# Cache TTL: 1 hour
CACHE_TTL_SECONDS = 60 * 60

SUMMARY_SYSTEM_INSTRUCTION = """You are an analytics assistant for engineering managers.
Summarize the provided insights in 2-3 concise sentences.
Focus on the most important trends and any concerning patterns.
Be direct and actionable. Avoid generic statements.
Do not use bullet points or lists - write in flowing prose."""


def get_summary_cache_key(team, target_date: date) -> str:
    """Generate a cache key for insight summaries.

    Args:
        team: The team to generate the key for.
        target_date: The date to include in the key.

    Returns:
        A unique cache key string.
    """
    return f"insight_summary:{team.id}:{target_date.isoformat()}"


def format_insights_for_prompt(insights: list) -> str:
    """Format a list of DailyInsight records into a prompt string.

    Args:
        insights: List of DailyInsight model instances.

    Returns:
        Formatted string suitable for LLM prompt.
    """
    if not insights:
        return "No insights available for this period."

    lines = ["Here are today's insights for the engineering team:\n"]

    for insight in insights:
        lines.append(f"[{insight.category.upper()}] [{insight.priority.upper()}]")
        lines.append(f"Title: {insight.title}")
        lines.append(f"Details: {insight.description}")
        lines.append("")

    return "\n".join(lines)


def _generate_fallback_summary(insights: list) -> str:
    """Generate a simple fallback summary without LLM.

    Used when API key is not configured or API call fails.

    Args:
        insights: List of DailyInsight model instances.

    Returns:
        A simple summary string.
    """
    if not insights:
        return "No insights available for today."

    count = len(insights)
    high_priority = sum(1 for i in insights if i.priority == "high")

    parts = [f"You have {count} insight{'s' if count != 1 else ''} today"]

    if high_priority > 0:
        parts.append(f", including {high_priority} high priority item{'s' if high_priority != 1 else ''}")

    parts.append(".")
    return "".join(parts)


def summarize_daily_insights(
    team,
    target_date: date | None = None,
    skip_cache: bool = False,
) -> str:
    """Summarize daily insights for a team using Gemini LLM.

    Fetches DailyInsight records for the team and date, then uses Gemini
    to generate a concise 2-3 sentence summary. Results are cached for
    1 hour to reduce API costs.

    Args:
        team: The team to summarize insights for.
        target_date: The date to summarize. Defaults to today.
        skip_cache: If True, bypass the cache and generate a fresh summary.

    Returns:
        A summary string (2-3 sentences).
    """
    if target_date is None:
        target_date = date.today()

    # Check cache first
    cache_key = get_summary_cache_key(team, target_date)
    if not skip_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    # Fetch insights for the team and date (explicit team filter, not for_team manager)
    insights = list(
        DailyInsight.objects.filter(
            team=team,
            date=target_date,
            is_dismissed=False,
        ).order_by("priority", "category")
    )

    # If no insights, return simple message
    if not insights:
        return "There are no insights for today."

    # Check if API key is configured
    api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
    if not api_key:
        logger.warning("GOOGLE_AI_API_KEY not configured, using fallback summary")
        return _generate_fallback_summary(insights)

    # Format insights for the prompt
    prompt = format_insights_for_prompt(insights)

    try:
        from apps.insights.services.gemini_client import GeminiClient

        client = GeminiClient()
        response = client.generate(
            prompt=prompt,
            system_instruction=SUMMARY_SYSTEM_INSTRUCTION,
            team_id=str(team.id),
            context={"feature": "insight_summary", "insight_count": len(insights)},
        )

        summary = response.text

        # Cache the result
        cache.set(cache_key, summary, CACHE_TTL_SECONDS)

        return summary

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return _generate_fallback_summary(insights)
