"""View utilities for metrics app.

Shared utilities for view functions, including date range extraction.
"""

from datetime import date, timedelta

from django.http import HttpRequest
from django.utils import timezone


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
