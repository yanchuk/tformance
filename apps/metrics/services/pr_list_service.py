"""PR list service - filtering and querying PRs for data explorer page."""

from datetime import date, datetime
from typing import Any

from django.db.models import Avg, Count, Exists, F, OuterRef, Q, QuerySet, Subquery, Sum

from apps.metrics.models import PRReview, PullRequest
from apps.teams.models import Team

# PR size buckets: (min_lines, max_lines) - max is inclusive, None means no upper limit
PR_SIZE_BUCKETS = {
    "XS": (0, 10),
    "S": (11, 50),
    "M": (51, 200),
    "L": (201, 500),
    "XL": (501, None),
}


def get_prs_queryset(team: Team, filters: dict[str, Any]) -> QuerySet[PullRequest]:
    """Get filtered queryset of PRs for a team.

    Args:
        team: The team to filter PRs for
        filters: Dictionary of filter parameters:
            - repo: Repository name (e.g., 'org/repo')
            - author: Team member ID (as string)
            - reviewer: Team member ID (as string)
            - ai: 'yes', 'no', or 'all'
            - ai_tool: Specific AI tool name (e.g., 'claude_code')
            - size: PR size bucket ('XS', 'S', 'M', 'L', 'XL')
            - state: PR state ('open', 'merged', 'closed')
            - has_jira: 'yes' or 'no'
            - self_reviewed: 'yes' or 'no'
            - date_from: Start date (ISO format string)
            - date_to: End date (ISO format string)

    Returns:
        Filtered QuerySet of PullRequest objects
    """
    # noqa: TEAM001 - Explicit team filter provided
    qs = PullRequest.objects.filter(team=team).select_related("author", "team")

    # Always annotate with is_self_reviewed for display in table
    # A PR is self-reviewed if it has only one unique reviewer and that reviewer is the author
    # noqa: TEAM001 - Subquery scoped by pull_request which is already team-filtered
    unique_reviewer_count = (
        PRReview.objects.filter(pull_request=OuterRef("pk"))  # noqa: TEAM001
        .values("pull_request")
        .annotate(cnt=Count("reviewer", distinct=True))
        .values("cnt")
    )
    has_only_author_review = Exists(
        PRReview.objects.filter(pull_request=OuterRef("pk"), reviewer=OuterRef("author"))  # noqa: TEAM001
    )
    qs = qs.annotate(
        reviewer_count=Subquery(unique_reviewer_count),
        has_author_review=has_only_author_review,
    )

    # Filter by repository
    if filters.get("repo"):
        qs = qs.filter(github_repo=filters["repo"])

    # Filter by author
    if filters.get("author"):
        qs = qs.filter(author_id=filters["author"])

    # Filter by reviewer
    if filters.get("reviewer"):
        reviewer_pr_ids = PRReview.objects.filter(team=team, reviewer_id=filters["reviewer"]).values_list(
            "pull_request_id", flat=True
        )
        qs = qs.filter(id__in=reviewer_pr_ids)

    # Filter by AI assistance
    ai_filter = filters.get("ai")
    if ai_filter == "yes":
        qs = qs.filter(is_ai_assisted=True)
    elif ai_filter == "no":
        qs = qs.filter(is_ai_assisted=False)
    # 'all' or not specified - no filter

    # Filter by specific AI tool
    if filters.get("ai_tool"):
        qs = qs.filter(ai_tools_detected__contains=[filters["ai_tool"]])

    # Filter by PR size using annotate with F expressions (modern Django ORM)
    size = filters.get("size")
    if size and size in PR_SIZE_BUCKETS:
        min_lines, max_lines = PR_SIZE_BUCKETS[size]
        # Total lines = additions + deletions
        qs = qs.annotate(total_lines=F("additions") + F("deletions"))
        qs = qs.filter(total_lines__gte=min_lines)
        if max_lines is not None:
            qs = qs.filter(total_lines__lte=max_lines)

    # Filter by state
    if filters.get("state"):
        qs = qs.filter(state=filters["state"])

    # Filter by Jira link presence
    has_jira = filters.get("has_jira")
    if has_jira == "yes":
        qs = qs.exclude(jira_key="")
    elif has_jira == "no":
        qs = qs.filter(jira_key="")

    # Filter by date range (on merged_at)
    if filters.get("date_from"):
        date_from = _parse_date(filters["date_from"])
        if date_from:
            qs = qs.filter(merged_at__date__gte=date_from)

    if filters.get("date_to"):
        date_to = _parse_date(filters["date_to"])
        if date_to:
            qs = qs.filter(merged_at__date__lte=date_to)

    # Filter by self-reviewed status
    # (annotations are already added at the start of the function)
    self_reviewed = filters.get("self_reviewed")
    if self_reviewed == "yes":
        # Only one unique reviewer AND that reviewer is the author
        qs = qs.filter(reviewer_count=1, has_author_review=True)
    elif self_reviewed == "no":
        # Either no reviews, more than one reviewer, or the single reviewer isn't the author
        qs = qs.exclude(reviewer_count=1, has_author_review=True)

    return qs


def get_pr_stats(queryset: QuerySet[PullRequest]) -> dict[str, Any]:
    """Calculate aggregate statistics for a PR queryset.

    Args:
        queryset: QuerySet of PullRequest objects

    Returns:
        Dictionary with aggregate stats:
            - total_count: Number of PRs
            - avg_cycle_time: Average cycle time in hours
            - avg_review_time: Average review time in hours
            - total_additions: Total lines added
            - total_deletions: Total lines deleted
            - ai_assisted_count: Number of AI-assisted PRs
    """
    stats = queryset.aggregate(
        total_count=Count("id"),
        avg_cycle_time=Avg("cycle_time_hours"),
        avg_review_time=Avg("review_time_hours"),
        total_additions=Sum("additions"),
        total_deletions=Sum("deletions"),
        ai_assisted_count=Count("id", filter=Q(is_ai_assisted=True)),
    )

    # Handle empty queryset
    if stats["total_count"] == 0:
        stats["total_additions"] = 0
        stats["total_deletions"] = 0
        stats["ai_assisted_count"] = 0

    return stats


def get_filter_options(team: Team) -> dict[str, Any]:
    """Get available filter options for a team's PRs.

    Args:
        team: The team to get filter options for

    Returns:
        Dictionary with filter option lists:
            - repos: List of repository names
            - authors: List of dicts with 'id' and 'name'
            - reviewers: List of dicts with 'id' and 'name'
            - ai_tools: List of AI tool names detected
            - size_buckets: PR_SIZE_BUCKETS constant
            - states: List of PR state options
    """
    # noqa: TEAM001 - Explicit team filter provided
    prs = PullRequest.objects.filter(team=team)

    # Get unique repositories
    repos = list(prs.values_list("github_repo", flat=True).distinct().order_by("github_repo"))

    # Get unique authors
    authors_qs = (
        prs.exclude(author__isnull=True)
        .values("author__id", "author__display_name")
        .distinct()
        .order_by("author__display_name")
    )
    authors = [{"id": str(a["author__id"]), "name": a["author__display_name"]} for a in authors_qs]

    # Get unique reviewers
    reviews = PRReview.objects.filter(team=team).exclude(reviewer__isnull=True)
    reviewers_qs = (
        reviews.values("reviewer__id", "reviewer__display_name").distinct().order_by("reviewer__display_name")
    )
    reviewers = [{"id": str(r["reviewer__id"]), "name": r["reviewer__display_name"]} for r in reviewers_qs]

    # Get unique AI tools from ai_tools_detected JSONField
    # This requires iterating since it's a JSON array field
    ai_tools_set = set()
    ai_prs = prs.filter(is_ai_assisted=True).values_list("ai_tools_detected", flat=True)
    for tools in ai_prs:
        if tools:
            ai_tools_set.update(tools)
    ai_tools = sorted(list(ai_tools_set))

    return {
        "repos": repos,
        "authors": authors,
        "reviewers": reviewers,
        "ai_tools": ai_tools,
        "size_buckets": PR_SIZE_BUCKETS,
        "states": ["open", "merged", "closed"],
    }


def _parse_date(date_str: str) -> date | None:
    """Parse ISO format date string.

    Args:
        date_str: Date in ISO format (YYYY-MM-DD)

    Returns:
        date object or None if parsing fails
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
