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
TECH_ABBREVS = {
    "frontend": "FE",
    "backend": "BE",
    "javascript": "JS",
    "test": "TS",
    "docs": "DC",
    "config": "CF",
    "other": "OT",
}

TECH_BADGE_CLASSES = {
    "frontend": "badge-info",
    "backend": "badge-success",
    "javascript": "badge-warning",
    "test": "badge-secondary",
    "docs": "badge-ghost",
    "config": "badge-accent",
    "other": "badge-ghost",
}

TECH_DISPLAY_NAMES = {
    "frontend": "Frontend",
    "backend": "Backend",
    "javascript": "JS/TypeScript",
    "test": "Test",
    "docs": "Documentation",
    "config": "Configuration",
    "other": "Other",
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
