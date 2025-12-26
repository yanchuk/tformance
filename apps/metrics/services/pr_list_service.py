"""PR list service - filtering and querying PRs for data explorer page."""

from datetime import date, datetime
from typing import Any

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Avg, Count, Exists, F, OuterRef, Q, QuerySet, Subquery, Sum, Value

from apps.metrics.models import PRFile, PRReview, PullRequest
from apps.teams.models import Team

# PR size buckets: (min_lines, max_lines) - max is inclusive, None means no upper limit
PR_SIZE_BUCKETS = {
    "XS": (0, 10),
    "S": (11, 50),
    "M": (51, 200),
    "L": (201, 500),
    "XL": (501, None),
}

# LLM-based filter options
PR_TYPES = [
    ("feature", "Feature"),
    ("bugfix", "Bug Fix"),
    ("refactor", "Refactor"),
    ("docs", "Documentation"),
    ("test", "Test"),
    ("chore", "Chore"),
    ("ci", "CI/CD"),
]

RISK_LEVELS = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
]

FRICTION_LEVELS = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
]


def calculate_pr_size_bucket(total_lines: int) -> str:
    """Calculate PR size bucket based on total lines changed.

    Args:
        total_lines: Total lines changed (additions + deletions), must be >= 0

    Returns:
        Size bucket string: 'XS', 'S', 'M', 'L', or 'XL'
        Returns empty string if total_lines is negative

    Examples:
        >>> calculate_pr_size_bucket(5)
        'XS'
        >>> calculate_pr_size_bucket(100)
        'M'
        >>> calculate_pr_size_bucket(1000)
        'XL'
    """
    if total_lines < 0:
        return ""

    for bucket_name, (min_lines, max_lines) in PR_SIZE_BUCKETS.items():
        if total_lines >= min_lines and (max_lines is None or total_lines <= max_lines):
            return bucket_name

    return ""


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

    # Annotate with technology categories from PR files
    # noqa: TEAM001 - Prefetch through PR which is already team-filtered
    qs = qs.annotate(
        tech_categories=ArrayAgg(
            "files__file_category",
            distinct=True,
            filter=~Q(files__file_category="") & Q(files__file_category__isnull=False),
            default=Value([]),
        )
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

    # Filter by technology category (multi-select)
    # Searches both pattern-based categories (PRFile.file_category)
    # and LLM categories (llm_summary.tech.categories)
    tech = filters.get("tech")
    if tech:
        tech_list = tech if isinstance(tech, list) else [tech]
        # Build OR query: match pattern categories OR LLM categories
        pattern_q = Q(files__file_category__in=tech_list)
        # For LLM categories, use contains lookup on JSONB array
        llm_q = Q()
        for cat in tech_list:
            llm_q |= Q(llm_summary__tech__categories__contains=[cat])
        qs = qs.filter(pattern_q | llm_q).distinct()

    # Filter by PR type (from LLM summary)
    if filters.get("pr_type"):
        qs = qs.filter(llm_summary__summary__type=filters["pr_type"])

    # Filter by risk level (from LLM summary)
    if filters.get("risk_level"):
        qs = qs.filter(llm_summary__health__risk_level=filters["risk_level"])

    # Filter by review friction (from LLM summary)
    if filters.get("review_friction"):
        qs = qs.filter(llm_summary__health__review_friction=filters["review_friction"])

    # Filter by date range (on merged_at)
    if filters.get("date_from"):
        date_from = _parse_date(filters["date_from"])
        if date_from:
            qs = qs.filter(merged_at__date__gte=date_from)

    if filters.get("date_to"):
        date_to = _parse_date(filters["date_to"])
        if date_to:
            qs = qs.filter(merged_at__date__lte=date_to)

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

    # Get technology categories - combine pattern-based and LLM categories
    # Pattern categories from PRFile.CATEGORY_CHOICES
    tech_categories = [{"value": choice[0], "label": choice[1]} for choice in PRFile.CATEGORY_CHOICES if choice[0]]
    # LLM-only categories (not in PRFile.CATEGORY_CHOICES)
    llm_only_categories = [
        {"value": "devops", "label": "DevOps"},
        {"value": "mobile", "label": "Mobile"},
        {"value": "data", "label": "Data"},
    ]
    tech_categories.extend(llm_only_categories)

    return {
        "repos": repos,
        "authors": authors,
        "reviewers": reviewers,
        "ai_tools": ai_tools,
        "size_buckets": PR_SIZE_BUCKETS,
        "states": ["open", "merged", "closed"],
        "tech_categories": tech_categories,
        "pr_types": PR_TYPES,
        "risk_levels": RISK_LEVELS,
        "friction_levels": FRICTION_LEVELS,
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
