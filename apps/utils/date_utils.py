"""Date and timezone utilities for consistent handling across the application.

Provides helpers for converting between date and datetime objects with proper
timezone awareness, solving common Django ORM warning issues when filtering
DateTimeFields with date objects.

Usage:
    from apps.utils.date_utils import start_of_day, end_of_day, days_ago

    # For ORM filtering on DateTimeFields
    prs = PullRequest.objects.filter(
        merged_at__gte=start_of_day(start_date),
        merged_at__lte=end_of_day(end_date),
    )

    # For test fixtures
    pr_date = days_ago(7)
"""

from datetime import date, datetime, time, timedelta

from django.utils import timezone


def start_of_day(d: date) -> datetime:
    """Convert a date to timezone-aware datetime at start of day (00:00:00).

    Args:
        d: A date object

    Returns:
        Timezone-aware datetime at midnight (00:00:00) of the given date.

    Example:
        >>> start_of_day(date(2024, 1, 15))
        datetime(2024, 1, 15, 0, 0, 0, tzinfo=<UTC>)
    """
    return timezone.make_aware(datetime.combine(d, time.min))


def end_of_day(d: date) -> datetime:
    """Convert a date to timezone-aware datetime at end of day (23:59:59.999999).

    Args:
        d: A date object

    Returns:
        Timezone-aware datetime at end of day (23:59:59.999999) of the given date.

    Example:
        >>> end_of_day(date(2024, 1, 15))
        datetime(2024, 1, 15, 23, 59, 59, 999999, tzinfo=<UTC>)
    """
    return timezone.make_aware(datetime.combine(d, time.max))


def days_ago(n: int) -> datetime:
    """Return timezone-aware datetime for n days ago at current time.

    Useful for creating test fixtures or calculating date ranges.

    Args:
        n: Number of days ago (0 = today)

    Returns:
        Timezone-aware datetime for n days ago.

    Example:
        >>> days_ago(7)  # One week ago
        datetime(2024, 1, 8, 12, 30, 0, tzinfo=<UTC>)  # If today is Jan 15 at 12:30
    """
    return timezone.now() - timedelta(days=n)


def make_aware_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> datetime:
    """Create a timezone-aware datetime from components.

    Convenience function for tests to avoid verbose timezone.make_aware() calls.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
        day: Day (1-31)
        hour: Hour (0-23), default 0
        minute: Minute (0-59), default 0
        second: Second (0-59), default 0

    Returns:
        Timezone-aware datetime.

    Example:
        >>> make_aware_datetime(2024, 1, 15, 12, 30)
        datetime(2024, 1, 15, 12, 30, 0, tzinfo=<UTC>)
    """
    return timezone.make_aware(datetime(year, month, day, hour, minute, second))
