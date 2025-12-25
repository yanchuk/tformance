"""Template tags for PR list views."""

from django import template

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
