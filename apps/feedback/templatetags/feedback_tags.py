"""Template tags for the feedback app."""

import json

from django import template

register = template.Library()


@register.filter
def to_json_attr(value):
    """Convert a Python dict/list to a JSON string safe for HTML attributes.

    Properly escapes the JSON string for use in HTML data-* attributes.
    Django's default string representation of dicts is not valid JSON.

    Args:
        value: Python dict, list, or any JSON-serializable value

    Returns:
        JSON string safe for HTML attributes

    Usage:
        <div data-config="{{ config|to_json_attr }}">
        <div data-snapshot="{{ pr.llm_summary|to_json_attr }}">
    """
    if value is None:
        return "{}"
    if isinstance(value, str):
        # If already a string, try to validate it's JSON
        try:
            json.loads(value)
            return value
        except (json.JSONDecodeError, TypeError):
            # Not valid JSON, wrap it
            return json.dumps(value)
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        # If not JSON-serializable, return empty object
        return "{}"
