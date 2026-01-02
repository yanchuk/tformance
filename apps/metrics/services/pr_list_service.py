"""PR list service - filtering and querying PRs for data explorer page."""

from datetime import date, datetime
from typing import Any

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Avg, Count, Exists, F, OuterRef, Q, QuerySet, Subquery, Sum, Value

from apps.metrics.models import PRFile, PRReview, PullRequest, TeamMember
from apps.metrics.services.ai_categories import (
    AI_CATEGORY_DISPLAY_NAMES,
    CATEGORY_BOTH,
    CATEGORY_CODE,
    CATEGORY_REVIEW,
    CODE_TOOLS,
    MIXED_TOOLS,
    REVIEW_TOOLS,
)
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

    # Filter by author (by ID)
    if filters.get("author"):
        qs = qs.filter(author_id=filters["author"])

    # Filter by author GitHub username (e.g., "@johndoe" or "johndoe")
    # Security: Only matches team members within the specified team
    github_name = filters.get("github_name")
    if github_name:
        # Strip @ prefix if present
        username = github_name.lstrip("@")
        # Look up team member by github_username within team (team-scoped = secure)
        try:
            member = TeamMember.objects.get(team=team, github_username__iexact=username)
            qs = qs.filter(author=member)
        except TeamMember.DoesNotExist:
            # No matching team member - return empty queryset
            qs = qs.none()

    # Filter by reviewer GitHub username (e.g., "@johndoe" or "johndoe")
    # Used for bottleneck @@ mentions - shows PRs where reviewer needs to take action
    # Security: Only matches team members within the specified team
    # Logic: Exclude only PRs where reviewer's LATEST review is "approved" (they're done)
    #        Include PRs with commented/changes_requested/dismissed (still in review process)
    reviewer_name = filters.get("reviewer_name")
    if reviewer_name:
        # Strip @ prefix if present
        username = reviewer_name.lstrip("@")
        # Look up team member by github_username within team (team-scoped = secure)
        try:
            member = TeamMember.objects.get(team=team, github_username__iexact=username)
            # Subquery to get the latest review state for this reviewer on each PR
            latest_review_state = (
                PRReview.objects.filter(  # noqa: TEAM001
                    pull_request=OuterRef("pk"),
                    reviewer=member,
                )
                .order_by("-submitted_at")
                .values("state")[:1]
            )
            # Annotate with the reviewer's latest review state and exclude only "approved"
            # - approved: reviewer is done (exclude)
            # - commented/changes_requested/dismissed: still in review process (include)
            qs = qs.annotate(reviewer_latest_state=Subquery(latest_review_state)).exclude(
                reviewer_latest_state="approved"
            )
        except TeamMember.DoesNotExist:
            # No matching team member - return empty queryset
            qs = qs.none()

    # Filter by reviewer
    # When filtering by reviewer, also filter by review submitted_at date range
    # to match dashboard semantics (reviews submitted in the date range)
    if filters.get("reviewer"):
        review_filters = {"team": team, "reviewer_id": filters["reviewer"]}
        date_from = _parse_date(filters.get("date_from"))
        date_to = _parse_date(filters.get("date_to"))
        if date_from:
            review_filters["submitted_at__date__gte"] = date_from
        if date_to:
            review_filters["submitted_at__date__lte"] = date_to
        reviewer_pr_ids = PRReview.objects.filter(**review_filters).values_list(  # noqa: TEAM001
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

    # Filter by AI category (code, review, or both)
    ai_category = filters.get("ai_category")
    if ai_category:
        qs = _apply_ai_category_filter(qs, ai_category)

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

    # Filter by draft status (is_draft: 'true', 'false')
    is_draft = filters.get("is_draft")
    if is_draft == "true":
        qs = qs.filter(is_draft=True)
    elif is_draft == "false":
        qs = qs.filter(is_draft=False)

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

    # Filter by date range
    # For open PRs (no merged_at), filter by pr_created_at instead
    # For merged/closed PRs, filter by merged_at for consistency with dashboard
    state_filter = filters.get("state")
    date_field = "pr_created_at" if state_filter == "open" else "merged_at"

    if filters.get("date_from"):
        date_from = _parse_date(filters["date_from"])
        if date_from:
            qs = qs.filter(**{f"{date_field}__date__gte": date_from})

    if filters.get("date_to"):
        date_to = _parse_date(filters["date_to"])
        if date_to:
            qs = qs.filter(**{f"{date_field}__date__lte": date_to})

    # Filter by issue type (for "needs attention" filters)
    # Uses priority-based exclusion to match dashboard counts:
    # Priority 1: Reverts (highest)
    # Priority 2: Hotfixes (excludes reverts)
    # Priority 3: Long cycle (excludes reverts, hotfixes) - uses 2x team avg threshold
    # Priority 4: Large PRs (excludes reverts, hotfixes, long cycle)
    # Priority 5: Missing Jira (excludes all above)
    issue_type = filters.get("issue_type")
    if issue_type:
        # Calculate dynamic "long cycle" threshold: 2x team average cycle time
        # This matches the dashboard's get_needs_attention_prs logic
        avg_result = qs.filter(cycle_time_hours__isnull=False).aggregate(avg_cycle=Avg("cycle_time_hours"))
        team_avg_cycle = avg_result["avg_cycle"] or 0
        long_cycle_threshold = float(team_avg_cycle) * 2 if team_avg_cycle else 999999  # High default if no data

    if issue_type == "revert":
        qs = qs.filter(is_revert=True)
    elif issue_type == "hotfix":
        # Hotfixes that are NOT reverts
        qs = qs.filter(is_hotfix=True, is_revert=False)
    elif issue_type == "long_cycle":
        # Long cycle time (>2x team avg) that are NOT reverts or hotfixes
        qs = qs.filter(cycle_time_hours__gt=long_cycle_threshold, is_revert=False, is_hotfix=False)
    elif issue_type == "large_pr":
        # Large PR (>500 lines) that are NOT reverts, hotfixes, or long cycle
        # Note: NULL cycle_time_hours is NOT considered "slow"
        qs = qs.annotate(total_lines_issue=F("additions") + F("deletions"))
        qs = qs.filter(
            total_lines_issue__gt=500,
            is_revert=False,
            is_hotfix=False,
        ).filter(Q(cycle_time_hours__lte=long_cycle_threshold) | Q(cycle_time_hours__isnull=True))
    elif issue_type == "missing_jira":
        # Missing Jira that doesn't have any higher priority issue
        # Note: NULL cycle_time_hours is NOT considered "slow"
        qs = qs.annotate(total_lines_missing=F("additions") + F("deletions"))
        qs = qs.filter(
            jira_key="",
            is_revert=False,
            is_hotfix=False,
            total_lines_missing__lte=500,
        ).filter(Q(cycle_time_hours__lte=long_cycle_threshold) | Q(cycle_time_hours__isnull=True))

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
            - code_ai_count: Number of PRs with code AI tools
            - review_ai_count: Number of PRs with review AI tools
            - both_ai_count: Number of PRs with both code and review AI tools
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
        stats["code_ai_count"] = 0
        stats["review_ai_count"] = 0
        stats["both_ai_count"] = 0
        return stats

    # Count PRs by AI category
    # This requires Python-level evaluation because ai_category is computed
    # from effective_ai_tools which considers LLM priority
    from apps.metrics.services.ai_categories import get_ai_category

    code_count = 0
    review_count = 0
    both_count = 0

    # Only check AI-assisted PRs to avoid iterating all PRs
    ai_prs = queryset.filter(is_ai_assisted=True).values_list("ai_tools_detected", "llm_summary", named=True)

    for pr in ai_prs:
        # Determine effective tools (LLM priority)
        tools = []
        if pr.llm_summary and pr.llm_summary.get("ai", {}).get("tools"):
            llm_ai = pr.llm_summary.get("ai", {})
            confidence = llm_ai.get("confidence", 0)
            if confidence >= 0.5 and llm_ai.get("tools"):
                tools = llm_ai["tools"]
        if not tools and pr.ai_tools_detected:
            tools = pr.ai_tools_detected

        category = get_ai_category(tools)
        if category == CATEGORY_CODE:
            code_count += 1
        elif category == CATEGORY_REVIEW:
            review_count += 1
        elif category == CATEGORY_BOTH:
            both_count += 1

    stats["code_ai_count"] = code_count
    stats["review_ai_count"] = review_count
    stats["both_ai_count"] = both_count

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

    # AI categories for filtering
    ai_categories = [
        {"value": CATEGORY_CODE, "label": AI_CATEGORY_DISPLAY_NAMES.get(CATEGORY_CODE, "Code AI")},
        {"value": CATEGORY_REVIEW, "label": AI_CATEGORY_DISPLAY_NAMES.get(CATEGORY_REVIEW, "Review AI")},
        {"value": CATEGORY_BOTH, "label": AI_CATEGORY_DISPLAY_NAMES.get(CATEGORY_BOTH, "Code + Review AI")},
    ]

    return {
        "repos": repos,
        "authors": authors,
        "reviewers": reviewers,
        "ai_tools": ai_tools,
        "ai_categories": ai_categories,
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


def _apply_ai_category_filter(qs: QuerySet[PullRequest], category: str) -> QuerySet[PullRequest]:
    """Apply AI category filter to queryset.

    This is complex because we need to check both:
    1. LLM-detected tools (in llm_summary.ai.tools) - takes priority
    2. Regex-detected tools (in ai_tools_detected) - fallback

    The filter logic:
    - code: Has code tools but NOT review-only
    - review: Has review tools but NOT code-only
    - both: Has both code AND review tools

    Args:
        qs: QuerySet to filter
        category: Category to filter by ("code", "review", "both")

    Returns:
        Filtered QuerySet
    """
    # Build Q objects for tool matching
    # We need to check both LLM tools and regex tools

    # All tools that count as "code" (including mixed)
    all_code_tools = CODE_TOOLS | MIXED_TOOLS

    # Build contains queries for each tool
    def build_tool_contains_query(tools: set[str], field: str) -> Q:
        """Build OR query for any of the tools being present."""
        q = Q()
        for tool in tools:
            q |= Q(**{f"{field}__contains": [tool]})
        return q

    # LLM tools field path
    llm_field = "llm_summary__ai__tools"
    # Regex tools field
    regex_field = "ai_tools_detected"

    # Build queries for LLM and regex sources
    llm_has_code = build_tool_contains_query(all_code_tools, llm_field)
    llm_has_review = build_tool_contains_query(REVIEW_TOOLS, llm_field)
    regex_has_code = build_tool_contains_query(all_code_tools, regex_field)
    regex_has_review = build_tool_contains_query(REVIEW_TOOLS, regex_field)

    # Combined: has code tools from either source
    has_code = llm_has_code | regex_has_code
    # Combined: has review tools from either source
    has_review = llm_has_review | regex_has_review

    if category == CATEGORY_CODE:
        # Has code tools, may or may not have review tools
        # Exclude PRs that have ONLY review tools
        qs = qs.filter(has_code)
    elif category == CATEGORY_REVIEW:
        # Has review tools, may or may not have code tools
        # Exclude PRs that have ONLY code tools
        qs = qs.filter(has_review)
    elif category == CATEGORY_BOTH:
        # Must have both code AND review tools
        qs = qs.filter(has_code & has_review)

    return qs


def _get_ai_category_for_tools(tools: list[str] | None) -> str | None:
    """Determine AI category for a list of tools.

    Args:
        tools: List of tool names

    Returns:
        "code", "review", "both", or None
    """
    if not tools:
        return None

    from apps.metrics.services.ai_categories import get_ai_category

    return get_ai_category(tools)
