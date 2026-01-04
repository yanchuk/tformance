"""Team-related metrics for dashboard.

Functions for team breakdown, member velocity, and Copilot usage per member.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum

from apps.metrics.models import AIUsageDaily, PRSurvey
from apps.metrics.services.dashboard._helpers import (
    _apply_repo_filter,
    _avatar_url_from_github_id,
    _compute_initials,
    _get_merged_prs_in_range,
)
from apps.teams.models import Team


def get_team_breakdown(
    team: Team,
    start_date: date,
    end_date: date,
    sort_by: str = "prs_merged",
    order: str = "desc",
    repo: str | None = None,
) -> list[dict]:
    """Get team breakdown with metrics per member.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        sort_by: Field to sort by (prs_merged, cycle_time, ai_pct, name)
        order: Sort order (asc or desc)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - member_id (int): Team member ID
            - member_name (str): Team member display name
            - prs_merged (int): Count of merged PRs
            - avg_cycle_time (Decimal): Average cycle time in hours (0.00 if None)
            - ai_pct (float): AI adoption percentage (0.0 to 100.0)
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Map sort_by to actual field names
    SORT_FIELDS = {
        "prs_merged": "prs_merged",
        "cycle_time": "avg_cycle_time",
        "ai_pct": None,  # Sort in Python after aggregation
        "name": "author__display_name",
    }

    # Determine database sort field
    db_sort_field = SORT_FIELDS.get(sort_by, "prs_merged")

    # Build order_by clause
    order_by_clause = []
    if db_sort_field:
        prefix = "-" if order == "desc" else ""
        order_by_clause = [f"{prefix}{db_sort_field}"]

    # Single aggregated query for PR metrics per author (replaces N+1 loop)
    query = (
        prs.exclude(author__isnull=True)
        .values(
            "author__id",
            "author__display_name",
            "author__github_id",
        )
        .annotate(
            prs_merged=Count("id"),
            avg_cycle_time=Avg("cycle_time_hours"),
        )
    )

    # Apply DB sorting if applicable
    if order_by_clause:
        query = query.order_by(*order_by_clause)

    pr_aggregates = list(query)

    # Get all author IDs for batch survey lookup
    author_ids = [row["author__id"] for row in pr_aggregates]

    # Single aggregated query for AI percentages per author (replaces N+1 loop)
    survey_aggregates = (
        PRSurvey.objects.filter(
            team=team,
            pull_request__in=prs,
            pull_request__author_id__in=author_ids,
        )
        .values("pull_request__author_id")
        .annotate(
            total_surveys=Count("id"),
            ai_assisted_count=Count("id", filter=Q(author_ai_assisted=True)),
        )
    )

    # Build lookup dict for AI percentages
    ai_pct_by_author = {}
    for row in survey_aggregates:
        author_id = row["pull_request__author_id"]
        total = row["total_surveys"]
        ai_count = row["ai_assisted_count"]
        ai_pct_by_author[author_id] = round(ai_count * 100.0 / total, 2) if total > 0 else 0.0

    # Build result list from aggregated data
    result = []
    for row in pr_aggregates:
        author_id = row["author__id"]
        display_name = row["author__display_name"]
        github_id = row["author__github_id"]

        # Compute avatar_url and initials from aggregated data
        avatar_url = _avatar_url_from_github_id(github_id)
        initials = _compute_initials(display_name) if display_name else "??"

        result.append(
            {
                "member_id": author_id,
                "member_name": display_name,
                "avatar_url": avatar_url,
                "initials": initials,
                "prs_merged": row["prs_merged"],
                "avg_cycle_time": row["avg_cycle_time"] if row["avg_cycle_time"] else Decimal("0.00"),
                "ai_pct": ai_pct_by_author.get(author_id, 0.0),
            }
        )

    # Apply Python-based sorting if needed (for ai_pct which can't be sorted in DB)
    if sort_by == "ai_pct":
        result.sort(key=lambda x: x["ai_pct"], reverse=(order == "desc"))

    return result


def get_copilot_by_member(
    team: Team, start_date: date, end_date: date, limit: int = 5, repo: str | None = None
) -> list[dict]:
    """Get Copilot metrics breakdown by member.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum number of members to return (default 5)
        repo: Optional repository filter (not applicable - Copilot data is not repo-specific)

    Returns:
        list of dicts with keys:
            - member_name (str): Team member display name
            - suggestions (int): Total suggestions shown
            - accepted (int): Total suggestions accepted
            - acceptance_rate (Decimal): Acceptance rate percentage

    Note:
        repo parameter is accepted for API consistency but has no effect since
        Copilot usage is tracked at the member level, not per-repository.
    """
    # Note: AIUsageDaily doesn't have repo field - Copilot data is not repo-specific
    copilot_usage = AIUsageDaily.objects.filter(
        team=team,
        source="copilot",
        date__gte=start_date,
        date__lte=end_date,
    )

    # Group by member and calculate totals
    member_data = (
        copilot_usage.values("member__display_name", "member__github_id")
        .annotate(
            suggestions=Sum("suggestions_shown"),
            accepted=Sum("suggestions_accepted"),
        )
        .order_by("-suggestions")
    )

    result = []
    for entry in member_data:
        suggestions = entry["suggestions"] or 0
        accepted = entry["accepted"] or 0

        acceptance_rate = Decimal(str(round(accepted / suggestions * 100, 2))) if suggestions > 0 else Decimal("0.00")

        result.append(
            {
                "member_name": entry["member__display_name"],
                "avatar_url": _avatar_url_from_github_id(entry["member__github_id"]),
                "initials": _compute_initials(entry["member__display_name"]),
                "suggestions": suggestions,
                "accepted": accepted,
                "acceptance_rate": acceptance_rate,
            }
        )

    return result[:limit] if limit else result


def get_team_velocity(team: Team, start_date: date, end_date: date, limit: int = 5) -> list[dict]:
    """Get top contributors by PR count with average cycle time.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        limit: Maximum number of contributors to return (default 5)

    Returns:
        list of dicts ordered by PR count descending, then display_name alphabetically:
            - member_id: int TeamMember ID
            - display_name: str member's display name
            - avatar_url: str member's avatar URL
            - pr_count: int number of PRs merged
            - avg_cycle_time: Decimal average cycle time in hours (or None)
    """
    # Get all merged PRs in range with author info
    prs = _get_merged_prs_in_range(team, start_date, end_date).select_related("author")

    # Group PRs by author
    author_prs: dict[int, list] = {}
    author_info: dict[int, dict] = {}

    for pr in prs:
        if not pr.author:
            continue

        author_id = pr.author.id
        if author_id not in author_prs:
            author_prs[author_id] = []
            author_info[author_id] = {
                "member_id": pr.author.id,
                "display_name": pr.author.display_name or "Unknown",
                "avatar_url": _avatar_url_from_github_id(pr.author.github_id),
            }
        author_prs[author_id].append(pr)

    # Calculate stats for each author
    results = []
    for author_id, prs_list in author_prs.items():
        pr_count = len(prs_list)

        # Calculate avg cycle time (only PRs with cycle_time_hours)
        cycle_times = [pr.cycle_time_hours for pr in prs_list if pr.cycle_time_hours is not None]
        avg_cycle_time = None
        if cycle_times:
            avg = sum(cycle_times) / len(cycle_times)
            avg_cycle_time = Decimal(str(round(float(avg), 1)))

        results.append(
            {
                **author_info[author_id],
                "pr_count": pr_count,
                "avg_cycle_time": avg_cycle_time,
            }
        )

    # Sort by pr_count descending, then display_name ascending
    results.sort(key=lambda x: (-x["pr_count"], x["display_name"]))

    return results[:limit]
