"""Template tags for PR list views."""

import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from apps.metrics.services.ai_categories import (
    CATEGORY_BOTH,
    CATEGORY_CODE,
    CATEGORY_REVIEW,
    get_ai_category,
)
from apps.metrics.services.ai_patterns import get_ai_tool_display_name
from apps.metrics.services.pr_list_service import calculate_pr_size_bucket

register = template.Library()


@register.filter
def ai_tools_display(ai_tools_detected: list[str]) -> str:
    """Convert AI tool type identifiers to human-friendly display names.

    Args:
        ai_tools_detected: List of AI tool type identifiers (e.g., ['devin', 'copilot'])

    Returns:
        Comma-separated friendly display names (e.g., 'Devin AI, Copilot')

    Usage:
        {{ pr.ai_tools_detected|ai_tools_display }}
    """
    if not ai_tools_detected:
        return ""
    return ", ".join(get_ai_tool_display_name(tool) for tool in ai_tools_detected)


@register.simple_tag(takes_context=True)
def pagination_url(context, page_number):
    """Build pagination URL preserving current filters.

    Args:
        context: Template context with request
        page_number: Page number to link to

    Returns:
        URL query string with all filters and new page number
    """
    request = context["request"]
    query_dict = request.GET.copy()
    query_dict["page"] = page_number
    return f"?{query_dict.urlencode()}"


@register.simple_tag(takes_context=True)
def sort_url(context, field):
    """Build sort URL, toggling order if same field clicked again.

    Args:
        context: Template context with request, sort, and order
        field: Field name to sort by

    Returns:
        URL query string with sort params, preserving filters, resetting page
    """
    request = context["request"]
    current_sort = context.get("sort", "merged")
    current_order = context.get("order", "desc")

    query_dict = request.GET.copy()
    query_dict["sort"] = field

    # Toggle order if clicking same field, otherwise default to desc
    if field == current_sort:
        query_dict["order"] = "asc" if current_order == "desc" else "desc"
    else:
        query_dict["order"] = "desc"

    # Reset to first page on sort change
    query_dict["page"] = "1"

    return f"?{query_dict.urlencode()}"


# Technology category display mappings
# Includes both pattern-based categories (from PRFile.file_category)
# and LLM categories (from llm_summary.tech.categories)
TECH_ABBREVS = {
    # Pattern-based categories
    "frontend": "FE",
    "backend": "BE",
    "javascript": "JS",
    "test": "TS",
    "docs": "DC",
    "config": "CF",
    "other": "OT",
    # LLM categories
    "devops": "DO",
    "mobile": "MB",
    "data": "DA",
}

TECH_BADGE_CLASSES = {
    # Pattern-based categories
    "frontend": "badge-info",
    "backend": "badge-success",
    "javascript": "badge-warning",
    "test": "badge-secondary",
    "docs": "badge-ghost",
    "config": "badge-accent",
    "other": "badge-ghost",
    # LLM categories
    "devops": "badge-warning",
    "mobile": "badge-secondary",
    "data": "badge-primary",
}

TECH_DISPLAY_NAMES = {
    # Pattern-based categories
    "frontend": "Frontend",
    "backend": "Backend",
    "javascript": "JS/TypeScript",
    "test": "Test",
    "docs": "Documentation",
    "config": "Configuration",
    "other": "Other",
    # LLM categories
    "devops": "DevOps",
    "mobile": "Mobile",
    "data": "Data",
}


@register.filter
def tech_abbrev(category: str) -> str:
    """Convert category to 2-letter abbreviation.

    Args:
        category: File category identifier (e.g., 'frontend', 'backend')

    Returns:
        Two-letter abbreviation (e.g., 'FE', 'BE')

    Usage:
        {{ category|tech_abbrev }}
    """
    if not category:
        return ""
    return TECH_ABBREVS.get(category, category[:2].upper())


@register.filter
def tech_badge_class(category: str) -> str:
    """Get DaisyUI badge class for category.

    Args:
        category: File category identifier

    Returns:
        DaisyUI badge class (e.g., 'badge-info', 'badge-success')

    Usage:
        <span class="badge {{ category|tech_badge_class }}">...</span>
    """
    if not category:
        return "badge-ghost"
    return TECH_BADGE_CLASSES.get(category, "badge-ghost")


@register.filter
def tech_display_name(category: str) -> str:
    """Get full display name for category.

    Args:
        category: File category identifier

    Returns:
        Human-readable display name (e.g., 'Frontend', 'Backend')

    Usage:
        {{ category|tech_display_name }}
    """
    if not category:
        return ""
    return TECH_DISPLAY_NAMES.get(category, category.title())


@register.filter
def repo_name(full_repo: str | None) -> str:
    """Extract repository name from 'owner/repo' format.

    Args:
        full_repo: Full repository path (e.g., 'antiwork/gumroad')

    Returns:
        Repository name only (e.g., 'gumroad')
        Returns empty string for None or empty input

    Usage:
        {{ pr.github_repo|repo_name }}
    """
    if not full_repo:
        return ""
    return full_repo.split("/")[-1] if "/" in full_repo else full_repo


@register.filter
def pr_size_bucket(additions: int | None, deletions: int | None) -> str:
    """Calculate PR size bucket based on total lines changed.

    Args:
        additions: Number of lines added
        deletions: Number of lines deleted

    Returns:
        Size bucket string: 'XS', 'S', 'M', 'L', or 'XL'
        Returns empty string for None or negative inputs

    Usage:
        {{ pr.additions|pr_size_bucket:pr.deletions }}
    """
    # Validate inputs
    if additions is None or deletions is None:
        return ""
    if additions < 0 or deletions < 0:
        return ""

    # Delegate to service layer for bucket calculation
    total_lines = additions + deletions
    return calculate_pr_size_bucket(total_lines)


# AI Confidence display mappings
AI_CONFIDENCE_LEVELS = {
    "high": (0.5, 1.0),  # Score >= 0.5
    "medium": (0.2, 0.5),  # Score >= 0.2 and < 0.5
    "low": (0.001, 0.2),  # Score > 0 and < 0.2
}

AI_CONFIDENCE_BADGE_CLASSES = {
    "high": "badge-success",
    "medium": "badge-warning",
    "low": "badge-ghost",
}


@register.filter
def ai_confidence_level(score: float | None) -> str:
    """Get confidence level label from score.

    Args:
        score: AI confidence score (0.0 - 1.0)

    Returns:
        Confidence level: 'high', 'medium', 'low', or '' for no signal

    Usage:
        {{ pr.ai_confidence_score|ai_confidence_level }}
    """
    if score is None or float(score) <= 0:
        return ""

    score_float = float(score)

    if score_float >= 0.5:
        return "high"
    elif score_float >= 0.2:
        return "medium"
    else:
        return "low"


@register.filter
def ai_confidence_badge_class(level: str | None) -> str:
    """Get DaisyUI badge class for confidence level.

    Args:
        level: Confidence level ('high', 'medium', 'low')

    Returns:
        DaisyUI badge class (e.g., 'badge-success', 'badge-warning')

    Usage:
        <span class="badge {{ level|ai_confidence_badge_class }}">...</span>
    """
    if not level:
        return "badge-ghost"
    return AI_CONFIDENCE_BADGE_CLASSES.get(level, "badge-ghost")


@register.filter
def get_item(dictionary: dict | None, key: str):
    """Get item from dictionary by key.

    Useful for accessing nested dict values in templates where dot notation
    doesn't work (e.g., when keys are dynamic).

    Args:
        dictionary: Dictionary to access
        key: Key to look up

    Returns:
        Value at key, or empty dict if not found/invalid

    Usage:
        {{ pr_type_config|get_item:item.type|get_item:'color' }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, {})
    return {}


@register.filter
def ai_signals_tooltip(signals: dict | None) -> str:
    """Format AI signals breakdown for tooltip display.

    Args:
        signals: AI signals dict from PullRequest.ai_signals field

    Returns:
        Human-readable signal breakdown for tooltip

    Usage:
        data-tip="{{ pr.ai_signals|ai_signals_tooltip }}"
    """
    if not signals:
        return "No AI signals"

    active_signals = []

    # LLM signal
    llm = signals.get("llm", {})
    if llm.get("score", 0) > 0:
        tools = llm.get("tools", [])
        tool_str = f" ({', '.join(tools)})" if tools else ""
        active_signals.append(f"LLM{tool_str}")

    # Regex signal
    regex = signals.get("regex", {})
    if regex.get("score", 0) > 0:
        tools = regex.get("tools", [])
        tool_str = f" ({', '.join(tools)})" if tools else ""
        active_signals.append(f"Regex{tool_str}")

    # Commit signal
    commits = signals.get("commits", {})
    if commits.get("score", 0) > 0:
        active_signals.append("Commits")

    # Review signal
    reviews = signals.get("reviews", {})
    if reviews.get("score", 0) > 0:
        active_signals.append("Reviews")

    # File signal
    files = signals.get("files", {})
    if files.get("score", 0) > 0:
        active_signals.append("Files")

    if not active_signals:
        return "No AI signals"

    return ", ".join(active_signals)


# =============================================================================
# LLM Summary Display Filters
# =============================================================================

# PR Type display configuration
PR_TYPE_CONFIG = {
    "feature": {"label": "Feature", "class": "badge-success", "icon": "sparkles"},
    "bugfix": {"label": "Bug Fix", "class": "badge-error", "icon": "bug"},
    "refactor": {"label": "Refactor", "class": "badge-info", "icon": "arrows"},
    "docs": {"label": "Docs", "class": "badge-ghost", "icon": "book"},
    "test": {"label": "Test", "class": "badge-secondary", "icon": "check"},
    "chore": {"label": "Chore", "class": "badge-ghost", "icon": "wrench"},
    "ci": {"label": "CI/CD", "class": "badge-warning", "icon": "gear"},
}

# Risk/Friction level display configuration
LEVEL_CONFIG = {
    "low": {"label": "Low", "class": "badge-success"},
    "medium": {"label": "Medium", "class": "badge-warning"},
    "high": {"label": "High", "class": "badge-error"},
}

# Scope display configuration
SCOPE_CONFIG = {
    "small": {"label": "Small", "class": "badge-success"},
    "medium": {"label": "Medium", "class": "badge-warning"},
    "large": {"label": "Large", "class": "badge-error"},
    "xlarge": {"label": "X-Large", "class": "badge-error"},
}

# AI Usage Type display configuration
AI_USAGE_TYPE_CONFIG = {
    "authored": {"label": "Authored by AI", "class": "badge-primary"},
    "assisted": {"label": "AI Assisted", "class": "badge-success"},
    "reviewed": {"label": "AI Reviewed", "class": "badge-info"},
    "brainstorm": {"label": "Brainstorming", "class": "badge-ghost"},
}

# AI Category display configuration (Code AI vs Review AI)
AI_CATEGORY_CONFIG = {
    CATEGORY_CODE: {"label": "Code", "class": "badge-primary"},
    CATEGORY_REVIEW: {"label": "Review", "class": "badge-secondary"},
    CATEGORY_BOTH: {"label": "Both", "class": "badge-accent"},
}


@register.filter
def ai_category_display(tools: list | None) -> str:
    """Get display label for AI category based on tools.

    Args:
        tools: List of AI tool identifiers

    Returns:
        Category label: 'Code', 'Review', 'Both', or ''

    Usage:
        {{ pr.effective_ai_tools|ai_category_display }}
    """
    if not tools:
        return ""
    category = get_ai_category(tools)
    if not category:
        return ""
    return AI_CATEGORY_CONFIG.get(category, {}).get("label", "")


@register.filter
def ai_category_badge_class(tools: list | None) -> str:
    """Get DaisyUI badge class for AI category based on tools.

    Args:
        tools: List of AI tool identifiers

    Returns:
        DaisyUI badge class (e.g., 'badge-primary', 'badge-secondary')

    Usage:
        <span class="badge {{ pr.effective_ai_tools|ai_category_badge_class }}">...</span>
    """
    if not tools:
        return "badge-ghost"
    category = get_ai_category(tools)
    if not category:
        return "badge-ghost"
    return AI_CATEGORY_CONFIG.get(category, {}).get("class", "badge-ghost")


@register.filter
def llm_pr_type(pr) -> str | None:
    """Get PR type from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        PR type string (feature, bugfix, etc.) or None

    Usage:
        {{ pr|llm_pr_type }}
    """
    if not pr.llm_summary:
        return None
    summary = pr.llm_summary.get("summary", {})
    return summary.get("type")


@register.filter
def llm_pr_type_label(pr_type: str | None) -> str:
    """Get display label for PR type.

    Args:
        pr_type: PR type string

    Returns:
        Human-readable label

    Usage:
        {{ pr|llm_pr_type|llm_pr_type_label }}
    """
    if not pr_type:
        return ""
    return PR_TYPE_CONFIG.get(pr_type, {}).get("label", pr_type.title())


@register.filter
def llm_pr_type_class(pr_type: str | None) -> str:
    """Get badge class for PR type.

    Args:
        pr_type: PR type string

    Returns:
        DaisyUI badge class

    Usage:
        <span class="badge {{ pr|llm_pr_type|llm_pr_type_class }}">...</span>
    """
    if not pr_type:
        return "badge-ghost"
    return PR_TYPE_CONFIG.get(pr_type, {}).get("class", "badge-ghost")


@register.filter
def llm_risk_level(pr) -> str | None:
    """Get risk level from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        Risk level (low, medium, high) or None

    Usage:
        {{ pr|llm_risk_level }}
    """
    if not pr.llm_summary:
        return None
    health = pr.llm_summary.get("health", {})
    return health.get("risk_level")


@register.filter
def llm_review_friction(pr) -> str | None:
    """Get review friction from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        Friction level (low, medium, high) or None

    Usage:
        {{ pr|llm_review_friction }}
    """
    if not pr.llm_summary:
        return None
    health = pr.llm_summary.get("health", {})
    return health.get("review_friction")


@register.filter
def llm_scope(pr) -> str | None:
    """Get scope from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        Scope (small, medium, large, xlarge) or None

    Usage:
        {{ pr|llm_scope }}
    """
    if not pr.llm_summary:
        return None
    health = pr.llm_summary.get("health", {})
    return health.get("scope")


@register.filter
def level_class(level: str | None) -> str:
    """Get badge class for risk/friction level.

    Args:
        level: Level string (low, medium, high)

    Returns:
        DaisyUI badge class

    Usage:
        <span class="badge {{ pr|llm_risk_level|level_class }}">...</span>
    """
    if not level:
        return "badge-ghost"
    return LEVEL_CONFIG.get(level, {}).get("class", "badge-ghost")


@register.filter
def level_label(level: str | None) -> str:
    """Get display label for risk/friction level.

    Args:
        level: Level string (low, medium, high)

    Returns:
        Human-readable label

    Usage:
        {{ pr|llm_risk_level|level_label }}
    """
    if not level:
        return ""
    return LEVEL_CONFIG.get(level, {}).get("label", level.title())


@register.filter
def scope_class(scope: str | None) -> str:
    """Get badge class for scope.

    Args:
        scope: Scope string (small, medium, large, xlarge)

    Returns:
        DaisyUI badge class

    Usage:
        <span class="badge {{ pr|llm_scope|scope_class }}">...</span>
    """
    if not scope:
        return "badge-ghost"
    return SCOPE_CONFIG.get(scope, {}).get("class", "badge-ghost")


@register.filter
def scope_label(scope: str | None) -> str:
    """Get display label for scope.

    Args:
        scope: Scope string (small, medium, large, xlarge)

    Returns:
        Human-readable label

    Usage:
        {{ pr|llm_scope|scope_label }}
    """
    if not scope:
        return ""
    return SCOPE_CONFIG.get(scope, {}).get("label", scope.title())


@register.filter
def llm_usage_type(pr) -> str | None:
    """Get AI usage type from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        Usage type (authored, assisted, reviewed, brainstorm) or None

    Usage:
        {{ pr|llm_usage_type }}
    """
    if not pr.llm_summary:
        return None
    ai = pr.llm_summary.get("ai", {})
    return ai.get("usage_type")


@register.filter
def usage_type_class(usage_type: str | None) -> str:
    """Get badge class for AI usage type.

    Args:
        usage_type: Usage type string

    Returns:
        DaisyUI badge class

    Usage:
        <span class="badge {{ pr|llm_usage_type|usage_type_class }}">...</span>
    """
    if not usage_type:
        return "badge-ghost"
    return AI_USAGE_TYPE_CONFIG.get(usage_type, {}).get("class", "badge-ghost")


@register.filter
def usage_type_label(usage_type: str | None) -> str:
    """Get display label for AI usage type.

    Args:
        usage_type: Usage type string

    Returns:
        Human-readable label

    Usage:
        {{ pr|llm_usage_type|usage_type_label }}
    """
    if not usage_type:
        return ""
    return AI_USAGE_TYPE_CONFIG.get(usage_type, {}).get("label", usage_type.title())


@register.filter
def llm_summary_title(pr) -> str | None:
    """Get LLM-generated title from summary.

    Args:
        pr: PullRequest instance

    Returns:
        LLM summary title or None

    Usage:
        {{ pr|llm_summary_title }}
    """
    if not pr.llm_summary:
        return None
    summary = pr.llm_summary.get("summary", {})
    return summary.get("title")


@register.filter
def llm_summary_description(pr) -> str | None:
    """Get LLM-generated description from summary.

    Args:
        pr: PullRequest instance

    Returns:
        LLM summary description or None

    Usage:
        {{ pr|llm_summary_description }}
    """
    if not pr.llm_summary:
        return None
    summary = pr.llm_summary.get("summary", {})
    return summary.get("description")


@register.filter
def llm_insights(pr) -> list | None:
    """Get health insights from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        List of insight strings or None

    Usage:
        {% for insight in pr|llm_insights %}...{% endfor %}
    """
    if not pr.llm_summary:
        return None
    health = pr.llm_summary.get("health", {})
    return health.get("insights")


@register.filter
def llm_languages(pr) -> list | None:
    """Get languages from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        List of language strings or None

    Usage:
        {{ pr|llm_languages|join:", " }}
    """
    if not pr.llm_summary:
        return None
    tech = pr.llm_summary.get("tech", {})
    return tech.get("languages")


@register.filter
def llm_frameworks(pr) -> list | None:
    """Get frameworks from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        List of framework strings or None

    Usage:
        {{ pr|llm_frameworks|join:", " }}
    """
    if not pr.llm_summary:
        return None
    tech = pr.llm_summary.get("tech", {})
    return tech.get("frameworks")


@register.filter
def llm_ai_tools(pr) -> list | None:
    """Get AI tools from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        List of AI tool strings or None

    Usage:
        {{ pr|llm_ai_tools|join:", " }}
    """
    if not pr.llm_summary:
        return None
    ai = pr.llm_summary.get("ai", {})
    return ai.get("tools")


@register.filter
def llm_ai_confidence(pr) -> float | None:
    """Get AI confidence from LLM summary.

    Args:
        pr: PullRequest instance

    Returns:
        Confidence score (0.0-1.0) or None

    Usage:
        {{ pr|llm_ai_confidence|floatformat:2 }}
    """
    if not pr.llm_summary:
        return None
    ai = pr.llm_summary.get("ai", {})
    return ai.get("confidence")


@register.filter
def format_list(items: list | None, max_items: int = 5) -> str:
    """Format a list for display, with ellipsis if too long.

    Args:
        items: List of strings
        max_items: Maximum items to show before ellipsis

    Returns:
        Comma-separated string with optional "..."

    Usage:
        {{ pr|llm_languages|format_list:3 }}
    """
    if not items:
        return ""
    if len(items) <= max_items:
        return ", ".join(str(item).title() for item in items)
    shown = [str(item).title() for item in items[:max_items]]
    return f"{', '.join(shown)}, +{len(items) - max_items} more"


@register.filter
def has_llm_summary(pr) -> bool:
    """Check if PR has LLM summary data.

    Args:
        pr: PullRequest instance

    Returns:
        True if llm_summary exists and has content

    Usage:
        {% if pr|has_llm_summary %}...{% endif %}
    """
    return bool(pr.llm_summary)


# =============================================================================
# Personal Notes Tags
# =============================================================================


@register.simple_tag(takes_context=True)
def user_note_for_pr(context, pr):
    """Get the current user's note for a PR.

    Args:
        context: Template context with request
        pr: PullRequest instance

    Returns:
        PRNote instance if exists, None otherwise

    Usage:
        {% user_note_for_pr pr as note %}
        {% if note %}...{% endif %}
    """
    request = context.get("request")
    if not request or not hasattr(request, "user") or not request.user.is_authenticated:
        return None

    # Import here to avoid circular imports
    from apps.notes.models import PRNote

    try:
        return PRNote.objects.get(user=request.user, pull_request=pr)
    except PRNote.DoesNotExist:
        return None


# =============================================================================
# Insight @Mention and Link Filters
# =============================================================================

# Pattern to match @username mentions (alphanumeric and hyphens, like GitHub usernames)
# Uses negative lookbehind to avoid matching emails like user@example.com
MENTION_PATTERN = re.compile(r"(?<![a-zA-Z0-9])@([a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)")


@register.filter
def linkify_mentions(text: str | None, days: int = 30) -> str:
    """Convert @username mentions to clickable links to PR list filtered by that user.

    Args:
        text: Text that may contain @username mentions
        days: Number of days for the date filter (default: 30)

    Returns:
        HTML with @mentions converted to links (marked safe)

    Usage:
        {{ insight.detail|linkify_mentions:30 }}
    """
    if not text:
        return ""

    # Escape the text first to prevent XSS
    escaped_text = escape(text)

    def replace_mention(match):
        username = match.group(1)
        url = f"/app/pull-requests/?github_name=@{username}&days={days}"
        return (
            f'<a href="{url}" target="_blank" rel="noopener" '
            f'class="text-primary hover:underline font-medium">@{username}</a>'
        )

    result = MENTION_PATTERN.sub(replace_mention, escaped_text)
    return mark_safe(result)
