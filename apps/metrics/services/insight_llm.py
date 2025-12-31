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
# Primary: openai/gpt-oss-20b - fast, cheap ($0.0375/1M input), good for structured JSON
# Fallback: llama-3.3-70b-versatile - proven reliable, better reasoning
INSIGHT_MODEL = "openai/gpt-oss-20b"
INSIGHT_FALLBACK_MODEL = "llama-3.3-70b-versatile"

# JSON Schema for structured output validation
# Note: additionalProperties must be false on all objects for Groq strict mode
INSIGHT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "1-2 sentence headline insight"},
        "detail": {"type": "string", "description": "2-3 sentences explaining what happened and why it matters"},
        "possible_causes": {
            "type": "array",
            "description": "1-2 hypotheses for WHY this is happening based on data patterns",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 2,
        },
        "recommendation": {
            "type": "string",
            "description": "Actionable recommendation that addresses an issue mentioned in detail",
        },
        "metric_cards": {
            "type": "array",
            "description": "MUST use exact values from PRE-COMPUTED METRIC CARDS section",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "trend": {"type": "string", "enum": ["positive", "negative", "neutral", "warning"]},
                },
                "required": ["label", "value", "trend"],
                "additionalProperties": False,
            },
            "minItems": 4,
            "maxItems": 4,
        },
        "actions": {
            "type": "array",
            "description": "1-3 actionable links - MUST match issues discussed in detail/recommendation",
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
                    "label": {"type": "string", "description": "Button text for the action"},
                },
                "required": ["action_type", "label"],
                "additionalProperties": False,
            },
            "minItems": 1,
            "maxItems": 3,
        },
    },
    "required": ["headline", "detail", "possible_causes", "recommendation", "metric_cards", "actions"],
    "additionalProperties": False,
}

# Models that support json_schema response format (strict JSON)
MODELS_WITH_JSON_SCHEMA = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}

# System prompt for insight generation
INSIGHT_SYSTEM_PROMPT = """You are an engineering metrics analyst providing actionable insights to CTOs.

## OUTPUT FORMAT
Return a JSON object with these fields:
- headline: Executive summary of the MOST SIGNIFICANT finding (MAX 15 WORDS, 1 sentence only)
- detail: 2-3 sentences explaining WHAT happened, with specific numbers
- possible_causes: 1-2 hypotheses for WHY this is happening (must be an array of strings)
- recommendation: One specific action that addresses an issue from 'detail'
- metric_cards: COPY EXACTLY from the PRE-COMPUTED METRIC CARDS section in the data
- actions: 1-3 buttons matching issues discussed in detail/recommendation

## HEADLINE RULES (CRITICAL)
- Maximum 12 words
- Single sentence only
- Focus on ONE key finding, not multiple metrics
- Be specific: include the metric value and direction
- Examples:
  - GOOD: "Review bottleneck: one reviewer has 22 pending reviews."
  - GOOD: "Cycle time doubled to 48h despite improved AI adoption."
  - GOOD: "Throughput dropped 31% as work concentrated on one contributor."
  - BAD: "AI adoption 95% but cycle time +205% as AI PRs 43% faster." (too many metrics)
  - BAD: "Various metrics changed this period." (too vague)

## CRITICAL RULES

### Rule 1: DATA FIDELITY
- metric_cards: Copy the EXACT values from "PRE-COMPUTED METRIC CARDS" section
- Do NOT recalculate or round differently - use the provided values verbatim
- Use EXACT percentages from the data (e.g., if data says "33.2%", use "33.2%")

### Rule 2: ROOT CAUSE HYPOTHESIS
For possible_causes, hypothesize WHY based on data patterns:
- Large PR % high + slow cycle time → "Large PRs (>500 lines) require more review cycles"
- AI PRs slower + high AI adoption → "AI-generated code may need more thorough review"
- Top contributor > 50% → "Work concentration creates bottleneck when key person is unavailable"
- Throughput drop + stable contributors → "May indicate sprint planning, holidays, or blocked work"
- Cycle time up + review time up → "Review delays suggest reviewer capacity constraints"

### Rule 3: RECOMMENDATION COHERENCE
Your recommendation MUST:
1. Address a specific issue mentioned in 'detail'
2. Be actionable (start with a verb: "Investigate...", "Review...", "Implement...")
3. Connect logically to the actions you provide

BAD: detail mentions AI slowness, recommendation talks about code reviews (unrelated)
GOOD: detail mentions AI slowness, recommendation says "Review AI-assisted PR workflows"

### Rule 4: ACTION ALIGNMENT
Actions MUST correspond to issues discussed:
- If detail mentions AI impact → include view_ai_prs
- If detail mentions slow PRs → include view_slow_prs
- If detail mentions contributor concentration → include view_contributors
- If detail mentions review bottleneck → include view_review_bottlenecks

## PRIORITY ORDER FOR HEADLINE
Pick the FIRST that applies:
1. Quality crisis: revert_rate > 8% → Lead with quality/reverts
2. AI impact significant: adoption > 40% AND |cycle_time_diff| > 25% → Lead with AI impact
3. Severe slowdown: cycle_time change > 50% → Lead with cycle time
4. Major throughput change: |throughput change| > 30% → Lead with throughput
5. Review bottleneck detected → Lead with bottleneck
6. Bus factor: top_contributor > 50% → Lead with work concentration
7. Otherwise: Most notable change

## AI IMPACT INTERPRETATION
- cycle_time_difference_pct = (AI_cycle - NonAI_cycle) / NonAI_cycle * 100
- NEGATIVE = AI PRs are FASTER (good)
- POSITIVE = AI PRs are SLOWER (needs investigation)

## BENCHMARKS (for context)
| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Cycle Time | <48h | 48-120h | >120h |
| Revert Rate | <2% | 2-5% | >5% |
| AI Adoption | >40% | 20-40% | <20% |
| Top Contributor | <30% | 30-50% | >50% |

## ACTION TYPES
- view_ai_prs: AI adoption or AI vs non-AI comparison
- view_non_ai_prs: Comparing AI vs non-AI performance
- view_slow_prs: Cycle time concerns
- view_reverts: Quality/revert issues
- view_large_prs: PR size mentioned
- view_contributors: Work distribution/bus factor
- view_review_bottlenecks: Review delays

## TREND VALUES
- positive: Good for the team (faster, more PRs, better quality)
- negative: Bad for the team (slower, fewer PRs, worse quality)
- neutral: Stable, no significant change
- warning: Needs attention but not critical

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

    # Build contextual actions based on the insight
    actions = []
    if revert_rate > 5:
        actions.append({"action_type": "view_reverts", "label": "View reverted PRs"})
    if ai_adoption >= 30:
        actions.append({"action_type": "view_ai_prs", "label": "View AI-assisted PRs"})
    # Ensure we always have at least one action
    if not actions:
        actions.append({"action_type": "view_slow_prs", "label": "View slow PRs"})

    # Build possible causes based on data patterns
    possible_causes = []
    if throughput_change is not None and throughput_change < -20:
        possible_causes.append("Throughput drop may indicate sprint planning, holidays, or blocked work")
    if revert_rate > 5:
        possible_causes.append("High revert rate suggests rushed reviews or insufficient testing")
    if ai_adoption < 30:
        possible_causes.append("Low AI adoption may limit potential velocity improvements")
    # Ensure we always have at least one cause
    if not possible_causes:
        possible_causes.append("Metrics are within normal ranges for the team")

    return {
        "headline": headline,
        "detail": detail,
        "possible_causes": possible_causes,
        "recommendation": recommendation,
        "metric_cards": metric_cards,
        "actions": actions,
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
