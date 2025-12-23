"""Custom template filters for number formatting."""

from django import template

register = template.Library()


@register.filter
def format_compact(value):
    """
    Format large numbers with K/M suffix for compact display.

    Examples:
        1234 -> "1.2K"
        15810 -> "15.8K"
        1500000 -> "1.5M"
        999 -> "999"
    """
    try:
        num = float(value)
    except (TypeError, ValueError):
        return value

    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(int(num))
