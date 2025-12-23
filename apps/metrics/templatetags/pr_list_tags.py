"""Template tags for PR list views."""

from django import template

register = template.Library()


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
