"""LLM-powered insight generation service.

Provides functions to:
- Gather metrics data from various domains (velocity, quality, team health, AI impact)
- Build prompts using Jinja2 templates
- Call GROQ API with deepseek model for insight generation
- Cache and fallback handling
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from typing import TYPE_CHECKING

from groq import Groq

from apps.metrics.services.dashboard_service import (
    get_ai_impact_stats,
    get_quality_metrics,
    get_team_health_metrics,
    get_velocity_comparison,
)

if TYPE_CHECKING:
    from apps.metrics.models import DailyInsight
    from apps.teams.models import Team

logger = logging.getLogger(__name__)

# Model configuration for insight generation
# Using reasoning model for synthesis tasks
INSIGHT_MODEL = "deepseek-r1-distill-qwen-32b"
INSIGHT_FALLBACK_MODEL = "llama-3.3-70b-versatile"

# System prompt for insight generation
INSIGHT_SYSTEM_PROMPT = """You are an engineering metrics analyst helping CTOs understand their team's performance.

Analyze the provided metrics data and generate insights in JSON format.

Your response MUST be valid JSON with this exact structure:
{
  "headline": "1-2 sentence headline insight (most important finding)",
  "detail": "2-3 sentences of context and supporting details",
  "recommendation": "One specific, actionable recommendation",
  "metric_cards": [
    {"label": "Metric Name", "value": "+X%", "trend": "positive|negative|neutral|warning"},
    {"label": "Metric Name", "value": "-X%", "trend": "positive|negative|neutral|warning"},
    {"label": "Metric Name", "value": "XX%", "trend": "positive|negative|neutral|warning"},
    {"label": "Metric Name", "value": "description", "trend": "positive|negative|neutral|warning"}
  ]
}

Guidelines:
- headline: Focus on the most significant finding (velocity change, AI impact, quality issue)
- detail: Explain the key numbers and what they mean for the team
- recommendation: Be specific and actionable (not generic advice)
- metric_cards: Exactly 4 cards showing: throughput, cycle time, AI adoption, and quality indicator
- trend values: "positive" = good (green), "negative" = bad (red), "neutral" = stable, "warning" = needs attention

Respond with ONLY the JSON object, no additional text."""


def gather_insight_data(
    team: Team,
    start_date: date,
    end_date: date,
    repo: str | None = None,
) -> dict:
    """Gather all metrics into a single dict for LLM prompt.

    Collects data from:
    - get_velocity_comparison: throughput, cycle_time, review_time with WoW/MoM comparison
    - get_quality_metrics: reverts, hotfixes, review rounds, large PR percentage
    - get_team_health_metrics: contributors, distribution, bottlenecks
    - get_ai_impact_stats: AI adoption rate, cycle time comparison

    Args:
        team: Team instance
        start_date: Start of period (inclusive)
        end_date: End of period (inclusive)
        repo: Optional repository filter (owner/repo format)

    Returns:
        dict with keys:
            - velocity: throughput, cycle_time, review_time comparisons
            - quality: revert/hotfix counts and rates, review rounds, large PR pct
            - team_health: contributors, distributions, bottleneck info
            - ai_impact: AI adoption rate and cycle time comparison
            - metadata: period info, team name
    """
    # Calculate period duration
    days = (end_date - start_date).days

    # Gather all domain data
    velocity = get_velocity_comparison(team, start_date, end_date, repo)
    quality = get_quality_metrics(team, start_date, end_date, repo)
    team_health = get_team_health_metrics(team, start_date, end_date, repo)
    ai_impact_raw = get_ai_impact_stats(team, start_date, end_date)

    # Transform ai_impact to expected format
    ai_impact = {
        "ai_pr_count": ai_impact_raw.get("ai_prs", 0),
        "non_ai_pr_count": ai_impact_raw.get("total_prs", 0) - ai_impact_raw.get("ai_prs", 0),
        "ai_adoption_pct": float(ai_impact_raw.get("ai_adoption_pct", 0)),
        "ai_avg_cycle_time": ai_impact_raw.get("avg_cycle_with_ai"),
        "non_ai_avg_cycle_time": ai_impact_raw.get("avg_cycle_without_ai"),
        "cycle_time_difference_pct": ai_impact_raw.get("cycle_time_difference_pct"),
    }

    # Build metadata
    metadata = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days": days,
        "team_name": team.name,
    }

    return {
        "velocity": velocity,
        "quality": quality,
        "team_health": team_health,
        "ai_impact": ai_impact,
        "metadata": metadata,
    }


def build_insight_prompt(data: dict) -> str:
    """Build LLM prompt from gathered insight data.

    Renders Jinja2 templates with the data to create a structured
    prompt for insight generation.

    Args:
        data: Dict from gather_insight_data with velocity, quality,
              team_health, ai_impact, and metadata

    Returns:
        Rendered prompt string ready for LLM API call
    """
    from jinja2 import Environment, PackageLoader

    # Load templates from apps/metrics/prompts/templates/insight/
    env = Environment(
        loader=PackageLoader("apps.metrics.prompts", "templates/insight"),
        autoescape=False,
    )

    template = env.get_template("user.jinja2")
    return template.render(**data)


def _create_fallback_insight(data: dict) -> dict:
    """Create a rule-based fallback insight when LLM fails.

    Uses simple rules to generate insights from the data without LLM.

    Args:
        data: Dict from gather_insight_data

    Returns:
        Insight dict with is_fallback=True
    """
    velocity = data.get("velocity", {})
    quality = data.get("quality", {})
    ai_impact = data.get("ai_impact", {})

    # Extract key metrics
    throughput = velocity.get("throughput", {})
    throughput_change = throughput.get("pct_change")
    throughput_current = throughput.get("current", 0)

    ai_adoption = ai_impact.get("ai_adoption_pct", 0)
    revert_rate = quality.get("revert_rate", 0)

    # Build headline based on most significant finding
    if throughput_change is not None and abs(throughput_change) >= 20:
        direction = "up" if throughput_change > 0 else "down"
        headline = f"Team velocity {direction} {abs(throughput_change):.0f}% with {throughput_current} PRs merged"
    elif ai_adoption >= 50:
        headline = f"Strong AI adoption at {ai_adoption:.0f}% of PRs"
    else:
        headline = f"Team merged {throughput_current} PRs this period"

    # Build detail
    detail = f"The team merged {throughput_current} PRs. "
    if ai_adoption > 0:
        detail += f"AI-assisted PRs represent {ai_adoption:.0f}% of total output. "
    if revert_rate > 5:
        detail += f"Revert rate of {revert_rate:.1f}% warrants attention."
    else:
        detail += "Code quality metrics are within healthy ranges."

    # Build recommendation
    if revert_rate > 10:
        recommendation = "Consider implementing additional code review checks to reduce revert rate."
    elif ai_adoption < 30:
        recommendation = "Explore AI coding tools to potentially improve team velocity."
    else:
        recommendation = "Continue current practices while monitoring quality metrics."

    # Build metric cards
    metric_cards = [
        {
            "label": "Throughput",
            "value": f"{throughput_current} PRs",
            "trend": "positive" if (throughput_change or 0) > 0 else "neutral",
        },
        {
            "label": "Cycle Time",
            "value": "N/A",
            "trend": "neutral",
        },
        {
            "label": "AI Adoption",
            "value": f"{ai_adoption:.0f}%",
            "trend": "positive" if ai_adoption >= 40 else "neutral",
        },
        {
            "label": "Quality",
            "value": f"{revert_rate:.1f}% reverts",
            "trend": "warning" if revert_rate > 5 else "positive",
        },
    ]

    return {
        "headline": headline,
        "detail": detail,
        "recommendation": recommendation,
        "metric_cards": metric_cards,
        "is_fallback": True,
    }


def generate_insight(
    data: dict,
    api_key: str | None = None,
    model: str | None = None,
) -> dict:
    """Generate insight using GROQ LLM API.

    Calls GROQ API with the insight prompt and parses the JSON response.
    Falls back to rule-based insight on any error.

    Args:
        data: Dict from gather_insight_data with all metrics
        api_key: Optional GROQ API key (defaults to GROQ_API_KEY env var)
        model: Optional model override (defaults to INSIGHT_MODEL)

    Returns:
        Dict with:
            - headline: 1-2 sentence headline
            - detail: 2-3 sentences of context
            - recommendation: Actionable advice
            - metric_cards: List of 4 metric card dicts
            - is_fallback: True if fallback was used
    """
    try:
        # Initialize GROQ client
        client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

        # Build the user prompt from data
        user_prompt = build_insight_prompt(data)

        # Call GROQ API
        response = client.chat.completions.create(
            model=model or INSIGHT_MODEL,
            messages=[
                {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000,
        )

        # Parse JSON response
        content = response.choices[0].message.content
        result = json.loads(content)

        # Add is_fallback=False to indicate successful LLM response
        result["is_fallback"] = False

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM JSON response: {e}")
        return _create_fallback_insight(data)

    except Exception as e:
        logger.warning(f"LLM insight generation failed: {e}")
        return _create_fallback_insight(data)


def cache_insight(
    team: Team,
    insight: dict,
    target_date: date,
    cadence: str = "weekly",
) -> DailyInsight:
    """Cache an LLM-generated insight to the database.

    Uses upsert logic to update existing insights for the same
    team/date/cadence combination.

    Args:
        team: Team instance
        insight: Dict from generate_insight with headline, detail, etc.
        target_date: Date this insight is for
        cadence: "weekly" or "monthly"

    Returns:
        DailyInsight instance (created or updated)
    """
    from apps.metrics.models import DailyInsight

    # Upsert based on team + date + cadence
    defaults = {
        "title": insight.get("headline", "")[:255],  # Truncate to field max
        "description": insight.get("detail", ""),
        "metric_value": insight,  # Store full response
        "priority": "medium",
        "metric_type": "llm_dashboard_insight",
    }

    obj, _created = DailyInsight.objects.update_or_create(
        team=team,
        date=target_date,
        category="llm_insight",
        comparison_period=cadence,
        defaults=defaults,
    )

    return obj
