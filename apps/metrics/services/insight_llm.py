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
from urllib.parse import urlencode

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
# Primary: openai/gpt-oss-120b - excellent prose quality, writes like senior engineer
# Fallback: llama-3.3-70b-versatile - proven reliable, good reasoning
# Note: OSS-120B with strict: true gives 100% JSON reliability + best quality
INSIGHT_MODEL = "openai/gpt-oss-120b"
INSIGHT_FALLBACK_MODEL = "llama-3.3-70b-versatile"

# JSON Schema for structured output validation
# Note: additionalProperties must be false on all objects for Groq strict mode
INSIGHT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {
            "type": "string",
            "description": "Root cause headline in 6-10 words",
        },
        "detail": {
            "type": "string",
            "description": "Bullet points as string with newlines: • fact — cause/action",
        },
        "recommendation": {
            "type": "string",
            "description": "ONE actionable sentence with specific target",
        },
        "metric_cards": {
            "type": "array",
            "description": "COPY EXACTLY from PRE-COMPUTED METRIC CARDS section",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "trend": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral", "warning"],
                    },
                },
                "required": ["label", "value", "trend"],
                "additionalProperties": False,
            },
            "minItems": 4,
            "maxItems": 4,
        },
        "actions": {
            "type": "array",
            "description": "2-3 buttons matching issues in detail",
            "items": {
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "enum": [
                            "view_ai_prs",
                            "view_non_ai_prs",
                            "view_slow_prs",
                            "view_reverts",
                            "view_large_prs",
                            "view_contributors",
                            "view_review_bottlenecks",
                        ],
                    },
                    "label": {"type": "string", "description": "Button text"},
                },
                "required": ["action_type", "label"],
                "additionalProperties": False,
            },
            "minItems": 2,
            "maxItems": 3,
        },
    },
    "required": ["headline", "detail", "recommendation", "metric_cards", "actions"],
    "additionalProperties": False,
}

# Models that support json_schema response format (strict JSON)
MODELS_WITH_JSON_SCHEMA = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}

# System prompt for insight generation (Version I - qualitative language)
INSIGHT_SYSTEM_PROMPT = """You are a senior engineering manager briefing your CTO. Speak naturally.

## OUTPUT FORMAT (JSON)
{
  "headline": "Root cause → impact (8-12 words)",
  "detail": "2-3 sentences explaining what's happening",
  "recommendation": "ONE specific action to take",
  "metric_cards": [copy EXACTLY from PRE-COMPUTED METRIC CARDS],
  "actions": [{"action_type": "...", "label": "..."}]
}

## CRITICAL RULE: NO RAW NUMBERS IN DETAIL

The metric_cards show exact numbers. Your detail section must EXPLAIN in words, not repeat numbers.

### STRICTLY BANNED (will fail review):
- ANY percentage with decimals: "5.4%", "56.2%", "49.4%"
- ANY percentage over 10: "42%", "96%", "85%"
- ANY hour value: "40 hours", "142.6 hours", "581 hours"
- Benchmark comparisons: "less than 48 hours", "over 40%"
- Exact PR counts over 20: "111 PRs", "150 PRs"

### ALWAYS CONVERT:

**Percentages → Words:**
- 1-5% → "a tiny fraction", "very few"
- 5-15% → "about one in ten", "a small portion"
- 15-25% → "about a fifth", "roughly a quarter"
- 25-40% → "about a third", "roughly a quarter"
- 40-60% → "about half"
- 60-75% → "most", "a majority"
- 75-90% → "most", "nearly all"
- 90%+ → "almost all", "nearly everyone"

**Time → Words:**
- <4h → "a few hours"
- 4-12h → "half a day"
- 12-30h → "about a day"
- 30-60h → "2-3 days"
- 60-100h → "3-4 days"
- 100-168h → "nearly a week"
- 168-336h → "over a week", "about two weeks"
- 336h+ → "several weeks"

**Changes → Words:**
- +5-20% → "slightly higher"
- +20-50% → "noticeably higher"
- +50-100% → "nearly doubled"
- +100-200% → "more than doubled"
- +200%+ → "tripled or more"
- -5-20% → "slightly lower"
- -20-50% → "noticeably lower", "dropped"
- -50-75% → "dropped by half"
- -75%+ → "plummeted"

**Comparisons → Words:**
- "AI PRs are 44.8% faster" → "AI PRs complete much faster"
- "non-AI PRs take 502.8 hours" → "non-AI PRs take several weeks"
- "5.4% adoption" → "very few PRs use AI"
- "benchmark of 48 hours" → "healthy range"

### EXAMPLE TRANSFORMATIONS:

❌ BAD: "The current AI adoption rate is 4.5%, significantly lower than the benchmark of over 40%"
✅ GOOD: "Very few PRs use AI tools, well below where high-performing teams typically are"

❌ BAD: "AI-assisted PRs are taking 49.4% longer with a cycle time of 108.1 hours compared to 72.3 hours for non-AI PRs"
✅ GOOD: "AI-assisted PRs are actually taking longer than regular PRs, which is unusual"

❌ BAD: "The current cycle time of 142.6 hours is critically high"
✅ GOOD: "Cycle time has grown to nearly a week, well above healthy levels"

❌ BAD: "One contributor handling 56.2% of the work"
✅ GOOD: "One contributor is handling most of the work"

## WRITING STYLE

Use cause → effect with arrows:
"Review backlog growing → PRs waiting longer to merge"
"Work concentrated on few people → delivery risk"

Or natural sentences:
"Large PRs are taking much longer to review, slowing the whole pipeline."

## HEADLINE = ROOT CAUSE
GOOD: "Review bottleneck → delivery slowing"
GOOD: "Single contributor handling most work"
BAD: "Throughput down 56%" (has number)
BAD: "Cycle time at 142 hours" (has number)

## METRIC CARDS (CRITICAL)
Copy EXACTLY from PRE-COMPUTED METRIC CARDS section.
Do NOT change labels, values, or trends.

## ACTION TYPES
view_slow_prs, view_large_prs, view_ai_prs, view_contributors, view_review_bottlenecks, view_reverts

Return ONLY valid JSON."""

# Action type to URL filter mapping
# Maps LLM-generated action_type to PR list query parameters
ACTION_URL_MAP: dict[str, dict[str, str]] = {
    "view_ai_prs": {"ai": "yes"},
    "view_non_ai_prs": {"ai": "no"},
    "view_slow_prs": {"issue_type": "long_cycle"},
    "view_reverts": {"issue_type": "revert"},
    "view_large_prs": {"issue_type": "large_pr"},
    "view_contributors": {"view": "contributors"},
    "view_review_bottlenecks": {"view": "reviews", "sort": "pending"},
}


def resolve_action_url(action: dict, days: int) -> str:
    """Convert action_type to PR list URL with filters.

    Takes an action dict from LLM output and converts it to a valid
    URL for the PR list page with appropriate filters.

    Args:
        action: Dict with action_type and label from LLM response
        days: Number of days for the filter period

    Returns:
        URL string like "/app/pull-requests/?days=30&ai=yes"
    """
    base = "/app/pull-requests/"
    params = {"days": days}
    params.update(ACTION_URL_MAP.get(action.get("action_type", ""), {}))
    return f"{base}?{urlencode(params)}"


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
    Returns bullet-point format matching the new prompt style.

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

    cycle_time = velocity.get("cycle_time", {})
    cycle_time_current = cycle_time.get("current")

    ai_adoption = ai_impact.get("ai_adoption_pct", 0)
    revert_rate = quality.get("revert_rate", 0)
    large_pr_pct = quality.get("large_pr_pct", 0)

    # Build headline based on root cause (not symptom)
    if revert_rate > 8:
        headline = f"Quality issues: {revert_rate:.1f}% revert rate"
    elif large_pr_pct > 30 and cycle_time_current and cycle_time_current > 48:
        headline = f"Large PRs ({large_pr_pct:.0f}%) slowing reviews"
    elif throughput_change is not None and throughput_change < -30:
        headline = f"Throughput down {abs(throughput_change):.0f}%"
    elif ai_adoption >= 50:
        headline = f"Strong AI adoption at {ai_adoption:.0f}%"
    else:
        headline = f"Team merged {throughput_current} PRs"

    # Build detail as bullet points
    bullets = []
    bullets.append(f"• Throughput: {throughput_current} PRs merged")
    if cycle_time_current:
        bullets.append(f"• Cycle time: {cycle_time_current:.1f}h average")
    bullets.append(f"• AI adoption: {ai_adoption:.0f}% of PRs")
    if revert_rate > 2:
        bullets.append(f"• Revert rate: {revert_rate:.1f}% — monitor quality")
    detail = "\n".join(bullets)

    # Build recommendation
    if revert_rate > 10:
        recommendation = "Add code review checks to reduce revert rate"
    elif large_pr_pct > 30:
        recommendation = "Split large PRs to speed up review cycles"
    elif ai_adoption < 30:
        recommendation = "Explore AI coding tools to improve velocity"
    else:
        recommendation = "Continue current practices, metrics look healthy"

    # Build metric cards
    metric_cards = [
        {
            "label": "Throughput",
            "value": f"{throughput_current} PRs",
            "trend": "positive" if (throughput_change or 0) > 0 else "neutral",
        },
        {
            "label": "Cycle Time",
            "value": f"{cycle_time_current:.1f}h" if cycle_time_current else "N/A",
            "trend": "warning" if cycle_time_current and cycle_time_current > 48 else "neutral",
        },
        {
            "label": "AI Adoption",
            "value": f"{ai_adoption:.0f}%",
            "trend": "positive" if ai_adoption >= 40 else "warning",
        },
        {
            "label": "Quality",
            "value": f"{revert_rate:.1f}% reverts",
            "trend": "warning" if revert_rate > 5 else "positive",
        },
    ]

    # Build contextual actions (minimum 2)
    actions = []
    if revert_rate > 5:
        actions.append({"action_type": "view_reverts", "label": "View reverted PRs"})
    if large_pr_pct > 20:
        actions.append({"action_type": "view_large_prs", "label": "View large PRs"})
    if ai_adoption < 40:
        actions.append({"action_type": "view_ai_prs", "label": "View AI-assisted PRs"})
    # Ensure minimum 2 actions
    if len(actions) < 2:
        actions.append({"action_type": "view_slow_prs", "label": "View slow PRs"})
    if len(actions) < 2:
        actions.append({"action_type": "view_contributors", "label": "View contributors"})

    return {
        "headline": headline,
        "detail": detail,
        "recommendation": recommendation,
        "metric_cards": metric_cards,
        "actions": actions[:3],  # Max 3 actions
        "is_fallback": True,
    }


def generate_insight(
    data: dict,
    api_key: str | None = None,
    model: str | None = None,
) -> dict:
    """Generate insight using GROQ LLM API.

    Calls GROQ API with the insight prompt and parses the JSON response.
    Uses two-pass approach: primary model first, fallback model on error.
    Falls back to rule-based insight only if both LLM calls fail.

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
    # Initialize GROQ client
    client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    # Build the user prompt from data
    user_prompt = build_insight_prompt(data)

    # Try primary model first, then fallback
    models_to_try = [model or INSIGHT_MODEL, INSIGHT_FALLBACK_MODEL]

    for current_model in models_to_try:
        try:
            # Build API call parameters
            api_params = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 1500,
            }

            # Use json_schema for models that support it, json_object for others
            if current_model in MODELS_WITH_JSON_SCHEMA:
                api_params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "insight_response",
                        "schema": INSIGHT_JSON_SCHEMA,
                        "strict": True,
                    },
                }
                # Disable reasoning output for OSS models
                api_params["include_reasoning"] = False
            else:
                # Fallback to json_object for other models
                api_params["response_format"] = {"type": "json_object"}

            # Call GROQ API
            response = client.chat.completions.create(**api_params)

            # Parse JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            # Add is_fallback=False to indicate successful LLM response
            result["is_fallback"] = False

            logger.info(f"Insight generated successfully with {current_model}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from {current_model}: {e}")
            continue  # Try next model

        except Exception as e:
            logger.warning(f"LLM insight generation failed with {current_model}: {e}")
            continue  # Try next model

    # All models failed, use rule-based fallback
    logger.warning("All LLM models failed, using rule-based fallback")
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
