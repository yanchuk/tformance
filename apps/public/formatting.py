"""Shared formatting utilities for public pages."""


def format_duration(value) -> str:
    """Format hours for display: minutes if <1h, hours otherwise.

    Examples:
        0.22  → "13m"
        0.5   → "30m"
        1.0   → "1.0h"
        12.4  → "12.4h"
        0     → "N/A"
        None  → "N/A"
    """
    hours = float(value or 0)
    if hours <= 0:
        return "N/A"
    if hours < 1:
        minutes = round(hours * 60)
        return f"{minutes}m"
    return f"{hours:.1f}h"
