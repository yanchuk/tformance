"""PR filter utilities extracted from pr_list_service.py.

This module provides reusable filter functions for PullRequest querysets,
reducing complexity in the main service while enabling independent testing.

Each filter function is pure and stateless, operating on QuerySets.

Usage:
    from apps.metrics.services.pr_filters import (
        apply_date_range_filter,
        apply_issue_type_filter,
    )

    qs = PullRequest.for_team.filter(...)
    qs = apply_date_range_filter(qs, state_filter="merged", date_from=date(2025, 1, 1))
    qs = apply_issue_type_filter(qs, issue_type="long_cycle")
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.db.models import Avg, F, Q

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from apps.metrics.models import PullRequest


# =============================================================================
# Date Range Filter
# =============================================================================
def apply_date_range_filter(
    qs: QuerySet[PullRequest],
    state_filter: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[PullRequest]:
    """Apply date range filter with state-aware field selection.

    Date field logic:
    - Open PRs: Filter by pr_created_at (open PRs have no merged_at)
    - Merged/Closed PRs: Filter by merged_at for consistency with dashboard
    - All states (None): OR query combining both logics

    Args:
        qs: PullRequest QuerySet to filter
        state_filter: PR state filter ("open", "merged", "closed", or None for all)
        date_from: Start date (inclusive)
        date_to: End date (inclusive)

    Returns:
        Filtered QuerySet
    """
    if not date_from and not date_to:
        return qs

    if state_filter == "open":
        return _filter_by_date_field(qs, "pr_created_at", date_from, date_to)

    if state_filter in ("merged", "closed"):
        return _filter_by_date_field(qs, "merged_at", date_from, date_to)

    # All states: combine with OR
    return _filter_all_states_date_range(qs, date_from, date_to)


def _filter_by_date_field(
    qs: QuerySet[PullRequest],
    field: str,
    date_from: date | None,
    date_to: date | None,
) -> QuerySet[PullRequest]:
    """Apply date range filter on a specific field."""
    if date_from:
        qs = qs.filter(**{f"{field}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{field}__date__lte": date_to})
    return qs


def _filter_all_states_date_range(
    qs: QuerySet[PullRequest],
    date_from: date | None,
    date_to: date | None,
) -> QuerySet[PullRequest]:
    """Apply date range for all states using appropriate fields.

    Uses OR query: open PRs filtered by pr_created_at, merged/closed by merged_at.
    """
    open_q = Q(state="open")
    merged_q = Q(state__in=["merged", "closed"])

    if date_from:
        open_q &= Q(pr_created_at__date__gte=date_from)
        merged_q &= Q(merged_at__date__gte=date_from)
    if date_to:
        open_q &= Q(pr_created_at__date__lte=date_to)
        merged_q &= Q(merged_at__date__lte=date_to)

    return qs.filter(open_q | merged_q)


# =============================================================================
# Issue Type Filter
# =============================================================================
def apply_issue_type_filter(
    qs: QuerySet[PullRequest],
    issue_type: str | None,
) -> QuerySet[PullRequest]:
    """Apply issue type filter with priority-based exclusions.

    Priority (highest to lowest):
    1. revert - Reverted PRs
    2. hotfix - Hotfixes (excludes reverts)
    3. long_cycle - Long cycle time >2x team avg (excludes reverts, hotfixes)
    4. large_pr - Large PRs >500 lines (excludes reverts, hotfixes, long cycle)
    5. missing_jira - Missing Jira key (excludes all above)

    The threshold for "long cycle" is calculated dynamically as 2x team average.

    Args:
        qs: PullRequest QuerySet to filter
        issue_type: One of "revert", "hotfix", "long_cycle", "large_pr", "missing_jira"

    Returns:
        Filtered QuerySet
    """
    if not issue_type:
        return qs

    # Calculate threshold once for filters that need it
    threshold = _calculate_long_cycle_threshold(qs)

    handlers = {
        "revert": _filter_revert,
        "hotfix": _filter_hotfix,
        "long_cycle": lambda q: _filter_long_cycle(q, threshold),
        "large_pr": lambda q: _filter_large_pr(q, threshold),
        "missing_jira": lambda q: _filter_missing_jira(q, threshold),
    }

    handler = handlers.get(issue_type)
    if handler:
        return handler(qs)
    return qs


def _calculate_long_cycle_threshold(qs: QuerySet[PullRequest]) -> float:
    """Calculate dynamic 'long cycle' threshold: 2x team average cycle time.

    Returns:
        Threshold in hours. Returns 999999 if no data available (effectively no filter).
    """
    avg_result = qs.filter(cycle_time_hours__isnull=False).aggregate(avg_cycle=Avg("cycle_time_hours"))
    team_avg = avg_result["avg_cycle"] or 0
    return float(team_avg) * 2 if team_avg else 999999


def _filter_revert(qs: QuerySet[PullRequest]) -> QuerySet[PullRequest]:
    """Filter for reverted PRs."""
    return qs.filter(is_revert=True)


def _filter_hotfix(qs: QuerySet[PullRequest]) -> QuerySet[PullRequest]:
    """Filter for hotfix PRs (excludes reverts)."""
    return qs.filter(is_hotfix=True, is_revert=False)


def _filter_long_cycle(qs: QuerySet[PullRequest], threshold: float) -> QuerySet[PullRequest]:
    """Filter for long cycle time PRs (excludes reverts and hotfixes)."""
    return qs.filter(
        cycle_time_hours__gt=threshold,
        is_revert=False,
        is_hotfix=False,
    )


def _filter_large_pr(qs: QuerySet[PullRequest], threshold: float) -> QuerySet[PullRequest]:
    """Filter for large PRs >500 lines (excludes reverts, hotfixes, long cycle).

    Note: NULL cycle_time_hours is NOT considered "slow".
    """
    qs = qs.annotate(total_lines_issue=F("additions") + F("deletions"))
    return qs.filter(
        total_lines_issue__gt=500,
        is_revert=False,
        is_hotfix=False,
    ).filter(Q(cycle_time_hours__lte=threshold) | Q(cycle_time_hours__isnull=True))


def _filter_missing_jira(qs: QuerySet[PullRequest], threshold: float) -> QuerySet[PullRequest]:
    """Filter for PRs missing Jira key (excludes all higher priority issues).

    Note: NULL cycle_time_hours is NOT considered "slow".
    """
    qs = qs.annotate(total_lines_missing=F("additions") + F("deletions"))
    return qs.filter(
        jira_key="",
        is_revert=False,
        is_hotfix=False,
        total_lines_missing__lte=500,
    ).filter(Q(cycle_time_hours__lte=threshold) | Q(cycle_time_hours__isnull=True))
