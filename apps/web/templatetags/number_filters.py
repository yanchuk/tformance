"""Custom template filters for number formatting."""

from django import template
from django.contrib.humanize.templatetags.humanize import intcomma as django_intcomma

register = template.Library()

# Re-export intcomma from django.contrib.humanize
register.filter("intcomma", django_intcomma)


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key.

    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


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
