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
        # Use strftime to get just the date part (YYYY-MM-DD) for Chart.js compatibility
        date_value = item[date_key]
        date_str = date_value.strftime("%Y-%m-%d") if hasattr(date_value, "strftime") else str(date_value)[:10]
        # Convert value to float to ensure JSON serializes as number, not string (Decimal issue)
        count_value = item[value_key]
        count_float = float(count_value) if count_value is not None else 0.0
        result.append({"date": date_str, "count": count_float})
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
