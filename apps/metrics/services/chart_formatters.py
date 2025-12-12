"""Chart Formatting Utilities.

Utilities for converting Django ORM query results and Python data structures
into formats compatible with Chart.js and other visualization libraries.
"""

from typing import Any


def format_time_series(
    data: list[dict[str, Any]], date_key: str = "week", value_key: str = "value"
) -> list[dict[str, Any]]:
    """Convert time series data to Chart.js compatible format.

    Args:
        data: List of dicts with date and value keys
        date_key: Key name for the date field (default: "week")
        value_key: Key name for the value field (default: "value")

    Returns:
        List of dicts with "date" (ISO string) and "count" keys
    """
    result = []
    for item in data:
        result.append({"date": item[date_key].isoformat(), "count": item[value_key]})
    return result


def format_categorical(data: list[tuple[Any, Any]]) -> list[list[Any]]:
    """Convert categorical data from tuples to lists.

    Args:
        data: List of tuples (label, value)

    Returns:
        List of lists [[label, value], ...]
    """
    return [list(item) for item in data]


def calculate_percentage_change(current: float | None, previous: float | None) -> float:
    """Calculate percentage change between two values.

    Args:
        current: Current value
        previous: Previous value

    Returns:
        Percentage change as float, or 0.0 if calculation not possible
    """
    if current is None or previous is None or previous == 0:
        return 0.0

    return ((current - previous) / previous) * 100
