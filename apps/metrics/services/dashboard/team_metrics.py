"""Team-related metrics for dashboard.

Functions for team breakdown, member velocity, and Copilot usage per member.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, F, Min, Q, Sum
from django.db.models.functions import Coalesce

from apps.metrics.models import AIUsageDaily, PRReview
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
        sort_by: Field to sort by (prs_merged, cycle_time, ai_pct, name, pr_size, reviews, response_time, copilot_pct)
        order: Sort order (asc or desc)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        list of dicts with keys:
            - member_id (int): Team member ID
            - member_name (str): Team member display name
            - prs_merged (int): Count of merged PRs
            - avg_cycle_time (Decimal): Average cycle time in hours (0.00 if None)
            - avg_pr_size (int): Average PR size in lines (additions + deletions)
            - reviews_given (int): Count of reviews given as reviewer
            - avg_review_response_hours (Decimal): Avg time to first review (as reviewer)
            - ai_pct (float): AI adoption percentage (0.0 to 100.0) from effective_is_ai_assisted
            - copilot_pct (float | None): Copilot suggestion acceptance rate (0.0 to 100.0), None if no data
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    prs = _apply_repo_filter(prs, repo)

    # Map sort_by to actual field names
    SORT_FIELDS = {
        "prs_merged": "prs_merged",
        "cycle_time": "avg_cycle_time",
        "ai_pct": None,  # Sort in Python after aggregation
        "name": "author__display_name",
        "pr_size": "avg_pr_size",
        "reviews": None,  # Sort in Python (requires separate query)
        "response_time": None,  # Sort in Python (requires separate query)
        "copilot_pct": None,  # Sort in Python (requires separate AIUsageDaily query)
    }

    # Determine database sort field
    db_sort_field = SORT_FIELDS.get(sort_by, "prs_merged")

    # Build order_by clause
    order_by_clause = []
    if db_sort_field:
        prefix = "-" if order == "desc" else ""
        order_by_clause = [f"{prefix}{db_sort_field}"]

    # Single aggregated query for PR metrics per author (replaces N+1 loop)
    # Added avg_pr_size (additions + deletions) and ai_pct from is_ai_assisted
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
            avg_pr_size=Avg(Coalesce(F("additions"), 0) + Coalesce(F("deletions"), 0)),
            total_prs=Count("id"),
            ai_assisted_count=Count("id", filter=Q(is_ai_assisted=True)),
        )
    )

    # Apply DB sorting if applicable
    if order_by_clause:
        query = query.order_by(*order_by_clause)

    pr_aggregates = list(query)

    # Get all author IDs for batch lookups
    author_ids = [row["author__id"] for row in pr_aggregates]

    # Get reviews given per member (as reviewer, excluding AI reviews)
    reviews_aggregates = (
        PRReview.objects.filter(
            team=team,
            reviewer_id__in=author_ids,
            submitted_at__gte=start_date,
            submitted_at__lte=end_date,
            is_ai_review=False,
        )
        .values("reviewer_id")
        .annotate(reviews_given=Count("id"))
    )
    reviews_by_member = {row["reviewer_id"]: row["reviews_given"] for row in reviews_aggregates}

    # Get average review response time per reviewer
    # This is the time from PR creation to the reviewer's first review on that PR
    # We need to get the minimum submitted_at for each PR per reviewer
    first_reviews = (
        PRReview.objects.filter(
            team=team,
            reviewer_id__in=author_ids,
            submitted_at__gte=start_date,
            submitted_at__lte=end_date,
            is_ai_review=False,
            pull_request__pr_created_at__isnull=False,
        )
        .values("reviewer_id", "pull_request_id")
        .annotate(
            first_review_at=Min("submitted_at"),
        )
        .values("reviewer_id", "first_review_at", "pull_request__pr_created_at")
    )

    # Calculate average response time per reviewer
    response_times_by_member: dict[int, list[float]] = {}
    for row in first_reviews:
        reviewer_id = row["reviewer_id"]
        pr_created = row["pull_request__pr_created_at"]
        first_review = row["first_review_at"]
        if pr_created and first_review:
            response_hours = (first_review - pr_created).total_seconds() / 3600
            if response_hours >= 0:  # Only positive response times
                if reviewer_id not in response_times_by_member:
                    response_times_by_member[reviewer_id] = []
                response_times_by_member[reviewer_id].append(response_hours)

    avg_response_by_member = {}
    for reviewer_id, times in response_times_by_member.items():
        if times:
            avg_response_by_member[reviewer_id] = Decimal(str(round(sum(times) / len(times), 2)))

    # Get Copilot acceptance rate per member from AIUsageDaily
    # Only includes source="copilot" data, excludes cursor/other AI tools
    copilot_aggregates = (
        AIUsageDaily.objects.filter(
            team=team,
            member_id__in=author_ids,
            date__gte=start_date,
            date__lte=end_date,
            source="copilot",
        )
        .values("member_id")
        .annotate(avg_acceptance_rate=Avg("acceptance_rate"))
    )
    copilot_by_member = {row["member_id"]: row["avg_acceptance_rate"] for row in copilot_aggregates}

    # Build result list from aggregated data
    result = []
    for row in pr_aggregates:
        author_id = row["author__id"]
        display_name = row["author__display_name"]
        github_id = row["author__github_id"]

        # Compute avatar_url and initials from aggregated data
        avatar_url = _avatar_url_from_github_id(github_id)
        initials = _compute_initials(display_name) if display_name else "??"

        # Calculate AI percentage from is_ai_assisted field (not surveys)
        total_prs = row["total_prs"]
        ai_count = row["ai_assisted_count"]
        ai_pct = round(ai_count * 100.0 / total_prs, 2) if total_prs > 0 else 0.0

        # Get Copilot acceptance rate (None if no data, preserving 0% for actual 0 acceptance)
        copilot_rate = copilot_by_member.get(author_id)
        copilot_pct = float(copilot_rate) if copilot_rate is not None else None

        result.append(
            {
                "member_id": author_id,
                "member_name": display_name,
                "avatar_url": avatar_url,
                "initials": initials,
                "prs_merged": row["prs_merged"],
                "avg_cycle_time": row["avg_cycle_time"] if row["avg_cycle_time"] else Decimal("0.00"),
                "avg_pr_size": int(row["avg_pr_size"]) if row["avg_pr_size"] else 0,
                "reviews_given": reviews_by_member.get(author_id, 0),
                "avg_review_response_hours": avg_response_by_member.get(author_id, Decimal("0.00")),
                "ai_pct": ai_pct,
                "copilot_pct": copilot_pct,
            }
        )

    # Apply Python-based sorting if needed
    if sort_by == "ai_pct":
        result.sort(key=lambda x: x["ai_pct"], reverse=(order == "desc"))
    elif sort_by == "reviews":
        result.sort(key=lambda x: x["reviews_given"], reverse=(order == "desc"))
    elif sort_by == "response_time":
        result.sort(key=lambda x: x["avg_review_response_hours"], reverse=(order == "desc"))
    elif sort_by == "copilot_pct":
        # Sort by copilot_pct, treating None as -1 (lowest) for consistent ordering
        result.sort(key=lambda x: x["copilot_pct"] if x["copilot_pct"] is not None else -1, reverse=(order == "desc"))

    return result


def get_team_averages(
    team: Team,
    start_date: date,
    end_date: date,
    repo: str | None = None,
) -> dict:
    """Get team-wide averages for comparison.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - avg_prs (float): Average PRs per member
            - avg_cycle_time (float): Average cycle time in hours
            - avg_pr_size (float): Average PR size in lines
            - avg_reviews (float): Average reviews given per member
            - avg_response_time (float): Average review response time in hours
            - avg_ai_pct (float): Average AI adoption percentage
            - avg_copilot_pct (float | None): Average Copilot acceptance rate (None if no data)
    """
    # Get breakdown data for all members
    breakdown = get_team_breakdown(team, start_date, end_date, repo=repo)

    if not breakdown:
        return {
            "avg_prs": 0,
            "avg_cycle_time": 0.0,
            "avg_pr_size": 0.0,
            "avg_reviews": 0.0,
            "avg_response_time": 0.0,
            "avg_ai_pct": 0.0,
            "avg_copilot_pct": None,
        }

    num_members = len(breakdown)

    # Calculate averages across all members
    total_prs = sum(m["prs_merged"] for m in breakdown)
    total_cycle_time = sum(float(m["avg_cycle_time"]) for m in breakdown)
    total_pr_size = sum(m["avg_pr_size"] for m in breakdown)
    total_reviews = sum(m["reviews_given"] for m in breakdown)
    total_response_time = sum(float(m["avg_review_response_hours"]) for m in breakdown)
    total_ai_pct = sum(m["ai_pct"] for m in breakdown)

    # Calculate Copilot average only for members with Copilot data
    copilot_values = [m["copilot_pct"] for m in breakdown if m["copilot_pct"] is not None]
    avg_copilot_pct = round(sum(copilot_values) / len(copilot_values), 2) if copilot_values else None

    return {
        "avg_prs": round(total_prs / num_members, 1),
        "avg_cycle_time": round(total_cycle_time / num_members, 2),
        "avg_pr_size": round(total_pr_size / num_members, 1),
        "avg_reviews": round(total_reviews / num_members, 1),
        "avg_response_time": round(total_response_time / num_members, 2),
        "avg_ai_pct": round(total_ai_pct / num_members, 2),
        "avg_copilot_pct": avg_copilot_pct,
    }


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

        # Skip bot authors (e.g., dependabot, github-bot)
        if pr.author.github_username and "bot" in pr.author.github_username.lower():
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
