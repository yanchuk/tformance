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
    get_needs_attention_prs,
    get_quality_metrics,
    get_team_health_metrics,
    get_team_velocity,
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
            "description": "2-3 actionable links - MUST match issues discussed in detail/recommendation",
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
            "minItems": 2,
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
- headline: Executive summary (MAX 12 WORDS, 1 sentence only)
- detail: 2-4 SHORT bullet points explaining WHAT happened. Each bullet = one fact with number.
  Use @username when referencing contributors. Format: "• Cycle time up 54% to 39h"
- possible_causes: 1-2 bullet points for WHY - each with specific numbers from data
- recommendation: ONE actionable sentence with @username or specific target
- metric_cards: COPY EXACTLY from the PRE-COMPUTED METRIC CARDS section
- actions: 2-3 buttons matching issues discussed (MINIMUM 2 REQUIRED)

## DETAIL FORMAT (CRITICAL - USE BULLETS)
Write detail as SHORT bullet points, NOT paragraphs. Each bullet = one insight.
GOOD:
  "• Cycle time increased 54.6% to 39.3h\\n• Non-AI PRs: 40.4h avg cycle\\n• AI PRs: 0.8h (98% faster)"
BAD:
  "The cycle time has increased by 54.6% to 39.3 hours, indicating a significant slowdown..."

## @USERNAME FORMAT (IMPORTANT)
When referencing contributors in detail or recommendation, use @username format from the ACTIONABLE DATA section.
- Use EXACT usernames from the Top Contributors table: @johndoe, @janesmith
- The @username will become a clickable link to their PRs
- Example: "Review @johndoe's 3 slow PRs averaging 156h cycle time"
- Example: "Redistribute reviews from @bob who has 15 pending"

## HEADLINE RULES (CRITICAL - STRICT WORD LIMIT)
- MAXIMUM 12 WORDS - Count carefully! Headlines over 12 words will be rejected.
- Single sentence only, no filler words like "drastically", "significantly", "overall"
- Focus on ONE key finding: the ROOT CAUSE, not the symptom
- Be specific: include ONE key metric value AND the actionable issue
- Name people when there's a clear bottleneck (reviewer with 10+ pending)
- Examples:
  - GOOD: "Review bottleneck: crazywoola has 22 pending reviews." (7 words, names person)
  - GOOD: "Cycle time critical at 174h, review delays +129%." (8 words, specific)
  - GOOD: "Bus factor risk: one contributor handles 56% of PRs." (9 words)
  - GOOD: "AI PRs taking 5x longer to merge than non-AI." (10 words)
  - BAD: "AI-assisted PRs are drastically slowing cycle time, increasing overall delays." (10 words but wordy)
  - BAD: "Throughput dropped 56%." (symptom only, no root cause)
  - BAD: "Cycle time increased this period." (vague, no specifics)

## CRITICAL RULES

### Rule 1: DATA FIDELITY
- metric_cards: Copy the EXACT values from "PRE-COMPUTED METRIC CARDS" section
- Do NOT recalculate or round differently - use the provided values verbatim
- Use EXACT percentages from the data (e.g., if data says "33.2%", use "33.2%")

### Rule 2: ROOT CAUSE HYPOTHESIS
For possible_causes, hypothesize WHY based on data patterns. Include specific numbers:
- Large PR % high + slow cycle time → "Large PRs (32% over 500 lines) add review cycles"
- AI PRs slower + high AI adoption → "AI code (45% of PRs) takes 2.3x longer to review"
- Top contributor > 50% → "56% from one contributor creates bottleneck risk"
- Throughput drop + stable contributors → "40% drop despite stable team = blocked work"
- Cycle time up + review time up → "Review time 12h→28h suggests capacity constraints"

BAD: "Large PRs may cause delays" (no specific numbers)
GOOD: "Large PRs (32% over 500 lines) are adding 40h to average cycle time"

### Rule 3: RECOMMENDATION COHERENCE (MUST BE SPECIFIC)
Your recommendation MUST:
1. Address a specific issue mentioned in 'detail'
2. Be actionable (start with a verb: "Investigate...", "Review...", "Implement...")
3. Include a specific target: person name, number, or measurable goal
4. Connect logically to the actions you provide

BAD: "Consider improving code review practices" (vague, no specific target)
BAD: "Review team workflows" (generic, doesn't mention the issue)
GOOD: "Investigate the 15 PRs taking >120h to identify common blockers"
GOOD: "Redistribute reviews from crazywoola (22 pending) to balance workload"
GOOD: "Focus AI tooling guidance on the 8 PRs where AI slowed delivery by 50%+"

### Rule 4: ACTION ALIGNMENT (MINIMUM 2 REQUIRED)
You MUST provide 2-3 actions that correspond to issues discussed:
- If detail mentions AI impact → include view_ai_prs
- If detail mentions slow PRs → include view_slow_prs
- If detail mentions contributor concentration → include view_contributors
- If detail mentions review bottleneck → include view_review_bottlenecks
- If detail mentions quality/reverts → include view_reverts
- If detail mentions large PRs → include view_large_prs

Example: If headline is about cycle time and AI PRs are involved:
  actions: [
    {"action_type": "view_slow_prs", "label": "View slow PRs"},
    {"action_type": "view_ai_prs", "label": "Analyze AI-assisted PRs"}
  ]

Example: If headline is about bus factor risk:
  actions: [
    {"action_type": "view_contributors", "label": "View contributor stats"},
    {"action_type": "view_large_prs", "label": "Review large PRs"}
  ]

## PRIORITY ORDER FOR HEADLINE (ROOT CAUSE FIRST)
Pick the FIRST that applies - always identify root cause, not just symptom:
1. Named bottleneck: reviewer with pending_count > 10 → Name the person in headline
2. Quality crisis: revert_rate > 8% → Lead with quality/reverts
3. AI slowing things down: AI PRs >25% slower than non-AI → Lead with AI slowdown
4. Bus factor risk: top_contributor > 50% → Lead with work concentration (root cause of throughput issues)
5. Review bottleneck: review_time > 2x previous → Lead with review delays
6. Critical cycle time: cycle_time > 120h → Lead with critical zone warning (even without AI data)
7. Severe slowdown: cycle_time change > 50% → Lead with cycle time (but mention cause if known)
8. Major throughput change: |throughput change| > 30% → BUT look for root cause first
9. Otherwise: Most notable change with actionable insight

IMPORTANT: Lead with ROOT CAUSE, not symptom:
- Throughput dropped + top_contributor > 50% → lead with bus factor
- Cycle time up + AI PRs slower → lead with AI impact
- Cycle time >120h + no AI data → lead with critical cycle time + contributing factor

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


def _build_issue_by_person(attention_items: list[dict]) -> dict[str, list[str]]:
    """Build a summary of issues grouped by person.

    Groups the attention PRs by author and issue type to identify
    who has the most issues of each type.

    Args:
        attention_items: List of PR dicts from get_needs_attention_prs

    Returns:
        Dict mapping issue_type to list of "@username (count)" strings.
        Example: {"revert": ["@johndoe (2)", "@janesmith (1)"], "long_cycle": ["@bob (3)"]}
    """
    from collections import defaultdict

    # Count issues by person and type
    person_issues: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for item in attention_items:
        author_github = item.get("author_github", "") or item.get("author", "Unknown")
        issue_type = item.get("issue_type", "")
        if author_github and issue_type:
            person_issues[issue_type][author_github] += 1

    # Format as sorted list per issue type
    result = {}
    for issue_type, authors in person_issues.items():
        sorted_authors = sorted(authors.items(), key=lambda x: -x[1])  # Sort by count desc
        result[issue_type] = [f"@{author} ({count})" for author, count in sorted_authors[:3]]

    return result


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

    # Get top contributors (actionable: names with PR counts and cycle times)
    top_contributors_raw = get_team_velocity(team, start_date, end_date, limit=5)
    top_contributors = [
        {
            "github_username": c.get("github_username", ""),
            "display_name": c.get("display_name", "Unknown"),
            "pr_count": c.get("pr_count", 0),
            "avg_cycle_time": float(c["avg_cycle_time"]) if c.get("avg_cycle_time") else None,
        }
        for c in top_contributors_raw
    ]

    # Get PRs needing attention (actionable: specific PRs with titles and authors)
    attention_prs_raw = get_needs_attention_prs(team, start_date, end_date, page=1, per_page=5)
    attention_prs = [
        {
            "title": pr.get("title", "")[:60],  # Truncate for prompt efficiency
            "author": pr.get("author", "Unknown"),
            "author_github": pr.get("author_github", ""),  # GitHub username for linking
            "issue_type": pr.get("issue_type", ""),
            "github_url": pr.get("url", ""),
            "cycle_time": pr.get("cycle_time_hours"),
        }
        for pr in attention_prs_raw.get("items", [])
    ]

    # Build issue summary by person (actionable: who has most issues)
    issue_by_person = _build_issue_by_person(attention_prs_raw.get("items", []))

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
        "top_contributors": top_contributors,
        "attention_prs": attention_prs,
        "issue_by_person": issue_by_person,
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

    # Build contextual actions based on the insight (minimum 2 required)
    actions = []
    if revert_rate > 5:
        actions.append({"action_type": "view_reverts", "label": "View reverted PRs"})
    if ai_adoption >= 30:
        actions.append({"action_type": "view_ai_prs", "label": "View AI-assisted PRs"})
    # Always add view_slow_prs as a relevant action
    actions.append({"action_type": "view_slow_prs", "label": "View slow PRs"})
    # Ensure we always have at least 2 actions
    if len(actions) < 2:
        actions.append({"action_type": "view_contributors", "label": "View contributors"})

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
