"""Template tags for PR list views."""

from django import template

from apps.metrics.services.ai_patterns import get_ai_tool_display_name

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
