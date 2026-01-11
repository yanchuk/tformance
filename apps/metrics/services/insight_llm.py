"""LLM-powered insight generation service.

SINGLE SOURCE OF TRUTH: Jinja2 templates in apps/metrics/prompts/templates/insight/

Provides functions to:
- get_insight_system_prompt(): Get system prompt from Jinja2 templates
- gather_insight_data(): Collect metrics from various domains
- generate_insight_from_groq(): Call GROQ API with gathered data
- Cache and fallback handling with model failover

To modify the system prompt:
1. Edit templates/insight/system.jinja2
2. Bump PROMPT_VERSION in apps/metrics/prompts/constants.py
3. Test: pytest apps/metrics/prompts/tests/ -v
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from groq import Groq

from apps.integrations.services.copilot_metrics_prompt import get_copilot_metrics_for_prompt
from apps.metrics.prompts.schemas import validate_insight_response
from apps.metrics.services.dashboard_service import (
    get_ai_impact_stats,
    get_jira_sprint_metrics,
    get_linkage_trend,
    get_pr_jira_correlation,
    get_quality_metrics,
    get_team_health_metrics,
    get_velocity_comparison,
    get_velocity_trend,
)
from apps.metrics.types import (
    ContributorInfo,
    InsightAction,
    InsightData,
    InsightResponse,
    MetricCard,
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
# Note: metric_cards are pre-computed in Python, not returned by LLM (saves ~150 tokens)
INSIGHT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {
            "type": "string",
            "description": "Root cause headline in 6-10 words (no numbers)",
        },
        "detail": {
            "type": "string",
            "description": "2-3 natural sentences explaining what's happening",
        },
        "recommendation": {
            "type": "string",
            "description": "ONE actionable sentence with specific target",
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
                            "view_copilot_usage",
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
    "required": ["headline", "detail", "recommendation", "actions"],
    "additionalProperties": False,
}

# Models that support json_schema response format (strict JSON)
MODELS_WITH_JSON_SCHEMA = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}


@lru_cache(maxsize=1)
def get_insight_system_prompt() -> str:
    """Get the insight generation system prompt from Jinja2 templates.

    This is the SINGLE SOURCE OF TRUTH for insight system prompts.
    Edit templates/insight/system.jinja2 to modify.

    Returns:
        The fully rendered system prompt string.
    """
    # Import inside function to avoid circular imports
    from apps.metrics.prompts.render import render_insight_system_prompt

    return render_insight_system_prompt()


class _LazyInsightPrompt:
    """Lazy-loaded prompt string for backward compatibility.

    DEPRECATED: Use get_insight_system_prompt() function instead.

    Implements string-like operations for backward compatibility with code that
    uses `len()`, `in`, `+`, etc. on the prompt constant.
    """

    def __str__(self) -> str:
        return get_insight_system_prompt()

    def __repr__(self) -> str:
        return f"LazyPrompt({get_insight_system_prompt()[:50]}...)"

    def __len__(self) -> int:
        return len(get_insight_system_prompt())

    def __contains__(self, item: str) -> bool:
        return item in get_insight_system_prompt()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return get_insight_system_prompt() == other
        return NotImplemented

    def __add__(self, other: str) -> str:
        return get_insight_system_prompt() + other

    def __radd__(self, other: str) -> str:
        return other + get_insight_system_prompt()


# DEPRECATED: Use get_insight_system_prompt() instead.
# Kept for backward compatibility - will be removed in future version.
INSIGHT_SYSTEM_PROMPT = _LazyInsightPrompt()


# Action type to URL mapping
# Maps LLM-generated action_type to URL configuration
# - "params": query parameters for PR list page
# - "base": alternative base URL (defaults to /app/pull-requests/)
ACTION_URL_MAP: dict[str, dict] = {
    "view_ai_prs": {"params": {"ai": "yes"}},
    "view_non_ai_prs": {"params": {"ai": "no"}},
    "view_slow_prs": {"params": {"issue_type": "long_cycle"}},
    "view_reverts": {"params": {"issue_type": "revert"}},
    "view_large_prs": {"params": {"issue_type": "large_pr"}},
    "view_contributors": {"base": "/app/metrics/analytics/team/"},
    "view_review_bottlenecks": {"params": {"state": "open", "sort": "review_time", "order": "desc"}},
    "view_copilot_usage": {"base": "/app/ai-adoption/"},
}


def resolve_action_url(action: InsightAction, days: int) -> str:
    """Convert action_type to URL with filters.

    Takes an action dict from LLM output and converts it to a valid
    URL. Most actions go to the PR list page with filters, but some
    (like view_contributors) go to different pages entirely.

    Args:
        action: Dict with action_type and label from LLM response
        days: Number of days for the filter period

    Returns:
        URL string like "/app/pull-requests/?days=30&ai=yes"
        or "/app/analytics/team/?days=30" for non-PR-list actions
    """
    action_type = action.get("action_type", "")
    config = ACTION_URL_MAP.get(action_type, {})

    # Use custom base URL if specified, otherwise default to PR list
    base = config.get("base", "/app/pull-requests/")
    params = {"days": days}

    # Add any additional params from config
    if "params" in config:
        params.update(config["params"])

    return f"{base}?{urlencode(params)}"


def build_metric_cards(data: InsightData) -> list[MetricCard]:
    """Pre-compute metric cards from gathered data.

    Computes the 4 standard metric cards (Throughput, Cycle Time, AI Adoption, Quality)
    with proper trend indicators. This is computed in Python instead of asking the LLM
    to return them, saving ~150 tokens per request and eliminating format errors.

    Args:
        data: Dict from gather_insight_data with velocity, quality, ai_impact

    Returns:
        List of 4 metric card dicts with label, value, trend
    """
    velocity = data.get("velocity", {})
    quality = data.get("quality", {})
    ai_impact = data.get("ai_impact", {})

    # Extract values
    throughput = velocity.get("throughput", {})
    throughput_change = throughput.get("pct_change")
    throughput_current = throughput.get("current", 0)

    cycle_time = velocity.get("cycle_time", {})
    cycle_time_change = cycle_time.get("pct_change")
    cycle_time_current = cycle_time.get("current")

    ai_adoption = ai_impact.get("ai_adoption_pct", 0)
    revert_rate = quality.get("revert_rate", 0)

    # Build cards matching the Jinja2 template logic
    cards = []

    # 1. Throughput card
    if throughput_change is not None:
        throughput_value = f"{throughput_change:+.1f}%"
        if throughput_change > 10:
            throughput_trend = "positive"
        elif throughput_change < -10:
            throughput_trend = "negative"
        else:
            throughput_trend = "neutral"
    else:
        throughput_value = f"{throughput_current} PRs"
        throughput_trend = "neutral"
    cards.append({"label": "Throughput", "value": throughput_value, "trend": throughput_trend})

    # 2. Cycle Time card
    if cycle_time_change is not None:
        cycle_value = f"{cycle_time_change:+.1f}%"
        if cycle_time_change < -10:
            cycle_trend = "positive"  # Faster is good
        elif cycle_time_change > 20:
            cycle_trend = "negative"
        elif cycle_time_change > 10:
            cycle_trend = "warning"
        else:
            cycle_trend = "neutral"
    elif cycle_time_current is not None:
        cycle_value = f"{cycle_time_current:.1f}h"
        cycle_trend = "neutral"
    else:
        cycle_value = "N/A"
        cycle_trend = "neutral"
    cards.append({"label": "Cycle Time", "value": cycle_value, "trend": cycle_trend})

    # 3. AI Adoption card
    ai_value = f"{ai_adoption:.1f}%"
    if ai_adoption >= 40:
        ai_trend = "positive"
    elif ai_adoption >= 20:
        ai_trend = "neutral"
    else:
        ai_trend = "warning"
    cards.append({"label": "AI Adoption", "value": ai_value, "trend": ai_trend})

    # 4. Quality card
    quality_value = f"{revert_rate:.1f}% reverts"
    if revert_rate <= 2:
        quality_trend = "positive"
    elif revert_rate <= 5:
        quality_trend = "warning"
    else:
        quality_trend = "negative"
    cards.append({"label": "Quality", "value": quality_value, "trend": quality_trend})

    return cards


# Known bot username patterns to exclude from contributor insights
# These create noise in insights as they're automated, not human contributors
BOT_USERNAME_PATTERNS = (
    "bot",
    "dependabot",
    "renovate",
    "github-actions",
    "codecov",
    "snyk",
    "greenkeeper",
    "semantic-release",
    "release-please",
    "auto-merge",
    "mergify",
)


def _is_bot_username(username: str | None) -> bool:
    """Check if a username appears to be a bot.

    Args:
        username: GitHub username to check

    Returns:
        True if username matches bot patterns
    """
    if not username:
        return False
    username_lower = username.lower()
    # Check if username contains any bot pattern
    return any(pattern in username_lower for pattern in BOT_USERNAME_PATTERNS)


def _get_top_contributors(team: Team, start_date: date, end_date: date, limit: int = 5) -> list[ContributorInfo]:
    """Get top PR authors with their GitHub usernames for @mentions.

    Excludes bot accounts (dependabot, renovate, etc.) from contributor analysis
    as they create noise in insights and aren't human contributors.

    Args:
        team: Team instance
        start_date: Start of period
        end_date: End of period
        limit: Max contributors to return

    Returns:
        List of dicts with github_username, display_name, pr_count, pct_share
    """
    from django.db.models import Count

    from apps.metrics.models import PullRequest

    # Get merged PRs grouped by author (fetch more than limit to account for bot filtering)
    author_stats = list(
        PullRequest.objects.filter(  # noqa: TEAM001 - team filter present
            team=team,
            state="merged",
            merged_at__date__gte=start_date,
            merged_at__date__lte=end_date,
        )
        .values("author__github_username", "author__display_name")
        .annotate(pr_count=Count("id"))
        .order_by("-pr_count")[: limit * 3]  # Fetch extra to filter bots
    )

    # Filter out bots
    human_stats = [stat for stat in author_stats if not _is_bot_username(stat["author__github_username"])][:limit]

    # Calculate total from human contributors only
    total_prs = sum(a["pr_count"] for a in human_stats) if human_stats else 0

    return [
        {
            "github_username": stat["author__github_username"] or "unknown",
            "display_name": stat["author__display_name"] or "Unknown",
            "pr_count": stat["pr_count"],
            "pct_share": round(stat["pr_count"] * 100.0 / total_prs, 1) if total_prs > 0 else 0,
        }
        for stat in human_stats
    ]


def gather_insight_data(
    team: Team,
    start_date: date,
    end_date: date,
    repo: str | None = None,
) -> InsightData:
    """Gather all metrics into a single dict for LLM prompt.

    Collects data from:
    - get_velocity_comparison: throughput, cycle_time, review_time with WoW/MoM comparison
    - get_quality_metrics: reverts, hotfixes, review rounds, large PR percentage
    - get_team_health_metrics: contributors, distribution, bottlenecks
    - get_ai_impact_stats: AI adoption rate, cycle time comparison
    - _get_top_contributors: Top PR authors with GitHub usernames for @mentions

    Args:
        team: Team instance
        start_date: Start of period (inclusive)
        end_date: End of period (inclusive)
        repo: Optional repository filter (owner/repo format)

    Returns:
        dict with keys:
            - velocity: throughput, cycle_time, review_time comparisons
            - quality: revert/hotfix counts and rates, review rounds, large PR pct
            - team_health: contributors, distributions, bottleneck info, top_contributors
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

    # Add top contributors with GitHub usernames for @mentions
    team_health["top_contributors"] = _get_top_contributors(team, start_date, end_date)

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

    # Add Jira metrics if connected
    from apps.integrations.models import JiraIntegration

    jira_data = None
    if JiraIntegration.objects.filter(team=team).exists():
        jira_data = {
            "sprint_metrics": get_jira_sprint_metrics(team, start_date, end_date),
            "pr_correlation": get_pr_jira_correlation(team, start_date, end_date),
            "linkage_trend": get_linkage_trend(team, weeks=4),
            "velocity_trend": get_velocity_trend(team, start_date, end_date),
        }

    # Add Copilot metrics for teams with real Copilot integration
    # GitHub requires 5+ Copilot licenses to access metrics API
    # Check CopilotSeatSnapshot for minimum seat count before including
    from apps.metrics.models import CopilotSeatSnapshot

    copilot_metrics = None
    latest_snapshot = CopilotSeatSnapshot.objects.filter(team=team).order_by("-date").first()
    if latest_snapshot and latest_snapshot.total_seats >= 5:
        copilot_metrics = get_copilot_metrics_for_prompt(
            team=team,
            start_date=start_date,
            end_date=end_date,
            include_copilot=True,
        )
        # Add relative waste metric (scaled by team size)
        if copilot_metrics and copilot_metrics.get("seat_data"):
            active_contributors = team_health.get("active_contributors", 1)
            wasted_spend = float(copilot_metrics["seat_data"].get("wasted_spend", 0))
            copilot_metrics["waste_per_contributor"] = round(wasted_spend / max(active_contributors, 1), 2)
            copilot_metrics["active_contributors"] = active_contributors

    # Type ignore: dashboard_service functions return untyped dicts
    # TODO: Add types to dashboard_service.py for full type safety
    return {  # type: ignore[reportReturnType]
        "velocity": velocity,
        "quality": quality,
        "team_health": team_health,
        "ai_impact": ai_impact,
        "jira": jira_data,
        "copilot_metrics": copilot_metrics if copilot_metrics else None,
        "metadata": metadata,
    }


def build_insight_prompt(data: InsightData) -> str:
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

    # Load templates from apps/metrics/prompts/templates/
    # Using parent directory so includes like '../sections/...' work correctly
    env = Environment(
        loader=PackageLoader("apps.metrics.prompts", "templates"),
        autoescape=False,
    )

    template = env.get_template("insight/user.jinja2")
    return template.render(**data)


def _create_fallback_insight(data: InsightData) -> InsightResponse:
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

    # Type cast: dict literals satisfy TypedDict at runtime
    result: InsightResponse = {  # type: ignore[reportAssignmentType]
        "headline": headline,
        "detail": detail,
        "recommendation": recommendation,
        "metric_cards": metric_cards,  # type: ignore[reportAssignmentType]
        "actions": actions[:3],  # type: ignore[reportAssignmentType]
        "is_fallback": True,
    }
    return result


def generate_insight(
    data: InsightData,
    api_key: str | None = None,
    model: str | None = None,
) -> InsightResponse:
    """Generate insight using GROQ LLM API.

    Calls GROQ API with the insight prompt and parses the JSON response.
    Uses two-pass approach: primary model first, fallback model on error.
    Falls back to rule-based insight only if both LLM calls fail.

    Metric cards are pre-computed in Python (not by LLM) for reliability.

    Args:
        data: Dict from gather_insight_data with all metrics
        api_key: Optional GROQ API key (defaults to GROQ_API_KEY env var)
        model: Optional model override (defaults to INSIGHT_MODEL)

    Returns:
        Dict with:
            - headline: 1-2 sentence headline
            - detail: 2-3 sentences of context
            - recommendation: Actionable advice
            - metric_cards: List of 4 metric card dicts (pre-computed)
            - actions: List of action buttons
            - is_fallback: True if fallback was used
    """
    # Pre-compute metric cards (not from LLM - saves ~150 tokens)
    metric_cards = build_metric_cards(data)

    # Initialize GROQ client
    client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    # Build the user prompt from data
    user_prompt = build_insight_prompt(data)

    # Try primary model first, then fallback
    models_to_try = [model or INSIGHT_MODEL, INSIGHT_FALLBACK_MODEL]

    for current_model in models_to_try:
        try:
            # Build API call parameters
            # - temperature 0.2: Low variance for consistent structured output
            # - max_tokens 1500: Increased for Copilot metrics section in prompts
            api_params = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": get_insight_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
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

            # Validate response against schema
            is_valid, errors = validate_insight_response(result)
            if not is_valid:
                logger.warning(f"Invalid insight schema from {current_model}: {errors}")
                continue  # Try next model

            # Merge pre-computed metric_cards into result
            result["metric_cards"] = metric_cards
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
    insight: InsightResponse,
    target_date: date,
    days: int = 30,
) -> DailyInsight:
    """Cache an LLM-generated insight to the database.

    Uses upsert logic to update existing insights for the same
    team/date/days combination.

    Args:
        team: Team instance
        insight: Dict from generate_insight with headline, detail, etc.
        target_date: Date this insight is for
        days: Number of days for the insight period (7, 30, or 90)

    Returns:
        DailyInsight instance (created or updated)
    """
    from apps.metrics.models import DailyInsight

    # Upsert based on team + date + days
    # comparison_period must be string of days ("7", "30", "90") to match dashboard query
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
        comparison_period=str(days),  # Must be "7", "30", or "90"
        defaults=defaults,
    )

    return obj
