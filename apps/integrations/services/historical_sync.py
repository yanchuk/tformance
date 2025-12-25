"""Historical sync utilities for onboarding.

Provides utilities for calculating sync date ranges and prioritizing
repositories for historical data import during user onboarding.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Count, OuterRef, QuerySet, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

# Get config with defaults
SYNC_CONFIG = getattr(settings, "HISTORICAL_SYNC_CONFIG", {})
DEFAULT_HISTORY_MONTHS = SYNC_CONFIG.get("HISTORY_MONTHS", 12)

if TYPE_CHECKING:
    from apps.integrations.models import TrackedRepository


def calculate_sync_date_range(months: int | None = None) -> tuple[date, date]:
    """
    Calculate sync date range: N months back + beginning of earliest month.

    The start date is extended to the beginning of the month to ensure
    complete month coverage for analytics aggregations.

    Args:
        months: Number of months of history to sync (default: 12)

    Returns:
        Tuple of (start_date, end_date) as date objects.

    Example:
        If today is Dec 25, 2025 and months=12:
        - End date: Dec 25, 2025
        - 12 months back: Dec 25, 2024
        - Extended to month start: Dec 1, 2024
        - Returns: (date(2024, 12, 1), date(2025, 12, 25))
    """
    if months is None:
        months = DEFAULT_HISTORY_MONTHS

    end_date = date.today()

    # Go back N months using dateutil for accurate month handling
    start_date = end_date - relativedelta(months=months)

    # Extend to beginning of that month
    start_date = start_date.replace(day=1)

    return start_date, end_date


def prioritize_repositories(
    repos: QuerySet[TrackedRepository],
) -> list[TrackedRepository]:
    """
    Order repositories by recent PR activity for optimal sync priority.

    Repositories with more PRs in the last 6 months are synced first,
    providing faster time-to-value for users during onboarding.

    Args:
        repos: QuerySet of TrackedRepository objects to prioritize

    Returns:
        List of repositories ordered by recent PR count (descending).
    """
    if not repos.exists():
        return []

    from apps.metrics.models import PullRequest

    six_months_ago = timezone.now() - timedelta(days=180)

    # Count PRs per repo using Subquery since PullRequest uses github_repo CharField
    # matching TrackedRepository.full_name
    pr_count_subquery = Subquery(
        PullRequest.objects.filter(
            github_repo=OuterRef("full_name"),
            team=OuterRef("team"),
            pr_created_at__gte=six_months_ago,
        )
        .values("github_repo")
        .annotate(count=Count("id"))
        .values("count")[:1]
    )

    repos_with_counts = repos.annotate(recent_pr_count=Coalesce(pr_count_subquery, 0)).order_by("-recent_pr_count")

    return list(repos_with_counts)
