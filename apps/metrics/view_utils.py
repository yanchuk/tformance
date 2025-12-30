"""View utilities for metrics app.

Shared utilities for view functions, including date range extraction.
"""

from datetime import date, timedelta
from typing import TypedDict

from django.http import HttpRequest
from django.utils import timezone


class ExtendedDateRange(TypedDict, total=False):
    """Extended date range with metadata."""

    start_date: date
    end_date: date
    granularity: str  # "daily", "weekly", "monthly"
    days: int
    compare_start: date | None
    compare_end: date | None


def get_date_range_from_request(request: HttpRequest) -> tuple[date, date]:
    """Extract date range from request query parameters.

    Args:
        request: The HTTP request object

    Returns:
        Tuple of (start_date, end_date) calculated from 'days' query param
        Default: 30 days ending today
    """
    days = int(request.GET.get("days", 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def get_extended_date_range(request: HttpRequest, default_preset: str | None = None) -> ExtendedDateRange:
    """Extract extended date range from request with custom dates and granularity.

    Supports:
    - days=N: Simple N days from today (default: 30)
    - start=YYYY-MM-DD, end=YYYY-MM-DD: Custom date range
    - preset=12_months|this_year|last_year|this_quarter|yoy: Quick presets
    - granularity=daily|weekly|monthly: Data grouping (auto-adjusts for long ranges)

    Args:
        request: The HTTP request object
        default_preset: Optional default preset to use when no date params provided

    Returns:
        ExtendedDateRange dict with start_date, end_date, granularity, days,
        and optionally compare_start/compare_end for YoY comparison
    """
    today = timezone.now().date()

    # Check for preset first (from URL or default)
    preset = request.GET.get("preset", "").lower() or (default_preset or "").lower()
    if preset:
        return _get_date_range_from_preset(preset, today)

    # Check for custom start/end dates
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if start_str and end_str:
        try:
            start_date = _parse_date(start_str)
            end_date = _parse_date(end_str)

            # Swap if start > end
            if start_date > end_date:
                start_date, end_date = end_date, start_date

            # Enforce max range of 730 days (2 years)
            max_days = 730
            if (end_date - start_date).days > max_days:
                start_date = end_date - timedelta(days=max_days)

            days = (end_date - start_date).days
            granularity = _get_auto_granularity(days, request.GET.get("granularity"))

            return ExtendedDateRange(
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
                days=days,
            )
        except (ValueError, TypeError):
            # Fall through to days-based calculation
            pass

    # Default to days-based calculation
    days = int(request.GET.get("days", 30))
    start_date = today - timedelta(days=days)
    end_date = today
    granularity = _get_auto_granularity(days, request.GET.get("granularity"))

    return ExtendedDateRange(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        days=days,
    )


def _parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    parts = date_str.split("-")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def _get_auto_granularity(days: int, requested: str | None) -> str:
    """Get appropriate granularity for the date range.

    Args:
        days: Number of days in range
        requested: User-requested granularity (if any)

    Returns:
        Granularity string: "daily", "weekly", or "monthly"
    """
    valid_granularities = {"daily", "weekly", "monthly"}

    if requested and requested.lower() in valid_granularities:
        return requested.lower()

    # Auto-adjust based on range length
    if days > 90:
        return "monthly"
    return "weekly"


def _get_date_range_from_preset(preset: str, today: date) -> ExtendedDateRange:
    """Get date range from a preset value.

    Args:
        preset: Preset name (12_months, this_year, last_year, this_quarter, yoy)
        today: Today's date

    Returns:
        ExtendedDateRange for the preset
    """
    year = today.year

    if preset == "12_months":
        # Rolling 12 months from today (365 days)
        from datetime import timedelta

        start = today - timedelta(days=365)
        return ExtendedDateRange(
            start_date=start,
            end_date=today,
            granularity="monthly",
            days=365,
        )

    if preset == "this_year":
        start = date(year, 1, 1)
        return ExtendedDateRange(
            start_date=start,
            end_date=today,
            granularity="monthly",
            days=(today - start).days,
        )

    if preset == "last_year":
        last_year = year - 1
        start = date(last_year, 1, 1)
        end = date(last_year, 12, 31)
        return ExtendedDateRange(
            start_date=start,
            end_date=end,
            granularity="monthly",
            days=(end - start).days,
        )

    if preset == "this_quarter":
        quarter = (today.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        start = date(year, quarter_start_month, 1)
        return ExtendedDateRange(
            start_date=start,
            end_date=today,
            granularity="weekly",
            days=(today - start).days,
        )

    if preset == "yoy":
        # Year-over-year: This year to date vs last year same period
        start = date(year, 1, 1)
        compare_start = date(year - 1, 1, 1)
        # Compare end is same day last year
        compare_end = date(year - 1, today.month, min(today.day, 28))  # Safe for Feb
        return ExtendedDateRange(
            start_date=start,
            end_date=today,
            granularity="monthly",
            days=(today - start).days,
            compare_start=compare_start,
            compare_end=compare_end,
        )

    # Default fallback
    start = today - timedelta(days=30)
    return ExtendedDateRange(
        start_date=start,
        end_date=today,
        granularity="weekly",
        days=30,
    )
