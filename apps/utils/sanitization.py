"""
Input sanitization utilities for preventing XSS and other injection attacks.

This module provides reusable sanitization functions using the bleach library.
Use these utilities when handling any user-provided HTML content.
"""

import bleach

# Default safe HTML tags - minimal set for basic formatting
DEFAULT_ALLOWED_TAGS = ["a", "b", "i", "em", "strong", "br", "span"]

# Default safe attributes per tag
DEFAULT_ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "span": ["class"],
}


def sanitize_html(
    value: str,
    tags: list[str] | None = None,
    attributes: dict | None = None,
    strip: bool = True,
) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Uses bleach to remove all tags except those in the whitelist.
    Safe for use with mark_safe() after sanitization.

    Args:
        value: The HTML string to sanitize
        tags: List of allowed tag names (defaults to DEFAULT_ALLOWED_TAGS)
        attributes: Dict of tag -> allowed attributes (defaults to DEFAULT_ALLOWED_ATTRIBUTES)
        strip: If True, remove disallowed tags entirely. If False, escape them.

    Returns:
        Sanitized HTML string

    Example:
        >>> from apps.utils.sanitization import sanitize_html
        >>> sanitize_html('<script>alert("xss")</script><b>Safe</b>')
        '<b>Safe</b>'
    """
    if not value:
        return ""

    return bleach.clean(
        value,
        tags=tags or DEFAULT_ALLOWED_TAGS,
        attributes=attributes or DEFAULT_ALLOWED_ATTRIBUTES,
        strip=strip,
    )


def strip_all_html(value: str) -> str:
    """
    Remove all HTML tags from a string, keeping only text content.

    Use this when you need plain text with no HTML at all.

    Args:
        value: The string to strip

    Returns:
        Plain text with all HTML tags removed

    Example:
        >>> strip_all_html('<p>Hello <b>World</b></p>')
        'Hello World'
    """
    if not value:
        return ""

    return bleach.clean(value, tags=[], strip=True)
