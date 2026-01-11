"""LLM prompts and context building for PR analysis.

SINGLE SOURCE OF TRUTH: Jinja2 templates in apps/metrics/prompts/templates/pr_analysis/

To get the system prompt, use:
    from apps.metrics.services.llm_prompts import get_system_prompt
    prompt = get_system_prompt()

To modify the prompt:
1. Edit the relevant template in templates/pr_analysis/sections/
2. Bump PROMPT_VERSION in apps/metrics/prompts/constants.py
3. Run: make export-prompts && npx promptfoo eval

This module also provides:
- get_user_prompt(): Build user prompt with PR context
- build_llm_pr_context(): Build complete context dict from PR model
- PR_ANALYSIS_SYSTEM_PROMPT: DEPRECATED lazy loader for backward compatibility
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING

# Re-export PROMPT_VERSION for backward compatibility
# The source of truth is apps/metrics/prompts/constants.py
from apps.metrics.prompts.constants import PROMPT_VERSION  # noqa: F401
from apps.metrics.types import PRContext

if TYPE_CHECKING:
    from apps.metrics.models import PullRequest


@lru_cache(maxsize=1)
def get_system_prompt() -> str:
    """Get the PR analysis system prompt from Jinja2 templates.

    This is the SINGLE SOURCE OF TRUTH for PR analysis system prompts.
    Edit templates/pr_analysis/system.jinja2 to modify.

    Returns:
        The fully rendered system prompt string.
    """
    # Import inside function to avoid circular imports
    from apps.metrics.prompts.render import render_pr_system_prompt

    return render_pr_system_prompt()


# DEPRECATED: Use get_system_prompt() instead.
# This constant exists only for backward compatibility with existing imports.
# The Jinja2 templates in apps/metrics/prompts/templates/pr_analysis/ are the source of truth.
def _get_pr_analysis_system_prompt() -> str:
    """Lazy loader for backward compatibility. DEPRECATED."""
    return get_system_prompt()


class _LazyPrompt:
    """Lazy-loaded prompt string for backward compatibility.

    DEPRECATED: Use get_system_prompt() function instead.
    This class exists to support existing code that imports PR_ANALYSIS_SYSTEM_PROMPT.

    Implements string-like operations for backward compatibility with code that
    uses `len()`, `in`, `+`, etc. on the prompt constant.
    """

    def __str__(self) -> str:
        return get_system_prompt()

    def __repr__(self) -> str:
        return f"LazyPrompt({get_system_prompt()[:50]}...)"

    def __len__(self) -> int:
        return len(get_system_prompt())

    def __contains__(self, item: str) -> bool:
        return item in get_system_prompt()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return get_system_prompt() == other
        return NotImplemented

    def __add__(self, other: str) -> str:
        return get_system_prompt() + other

    def __radd__(self, other: str) -> str:
        return other + get_system_prompt()


# DEPRECATED: Use get_system_prompt() instead.
# Kept for backward compatibility - will be removed in future version.
PR_ANALYSIS_SYSTEM_PROMPT = _LazyPrompt()


def calculate_relative_hours(timestamp: datetime | None, baseline: datetime | None) -> float | None:
    """Calculate hours difference between timestamp and baseline.

    Args:
        timestamp: The timestamp to compare
        baseline: The baseline timestamp to compare against

    Returns:
        Hours difference rounded to 1 decimal place, or None if either argument is None
    """
    if timestamp is None or baseline is None:
        return None

    delta = timestamp - baseline
    hours = delta.total_seconds() / 3600
    return round(hours, 1)


def _format_timestamp_prefix(timestamp: datetime | None, baseline: datetime | None) -> str:
    """Format timestamp as relative hours prefix for display.

    Args:
        timestamp: The timestamp to format
        baseline: The baseline timestamp to compare against

    Returns:
        Formatted prefix like "[+2.5h] " or empty string if timestamp/baseline is None
    """
    hours = calculate_relative_hours(timestamp, baseline)
    if hours is not None:
        return f"[+{hours}h] "
    return ""


def _get_member_display_name(member) -> str:
    """Get display name for a team member.

    Args:
        member: TeamMember object or None

    Returns:
        Display name, GitHub username, or "unknown"
    """
    if not member:
        return "unknown"
    return member.display_name or member.github_username or "unknown"


def get_user_prompt(
    pr_body: str,
    pr_title: str = "",
    file_count: int = 0,
    additions: int = 0,
    deletions: int = 0,
    comment_count: int = 0,
    repo_languages: list[str] | None = None,
    # v6.0.0 - Full PR context
    state: str = "",
    labels: list[str] | None = None,
    is_draft: bool = False,
    is_hotfix: bool = False,
    is_revert: bool = False,
    cycle_time_hours: float | None = None,
    review_time_hours: float | None = None,
    commits_after_first_review: int | None = None,
    review_rounds: int | None = None,
    file_paths: list[str] | None = None,
    commit_messages: list[str] | None = None,
    # v6.1.0 - Additional PR metadata and collaboration context
    milestone: str | None = None,
    assignees: list[str] | None = None,
    linked_issues: list[str] | None = None,
    jira_key: str | None = None,
    author_name: str | None = None,
    reviewers: list[str] | None = None,
    review_comments: list[str] | None = None,
    # v6.4.0 - Repository context for AI product detection
    repo_name: str | None = None,
) -> str:
    """Generate user prompt with full PR context.

    Args:
        pr_body: The PR description text
        pr_title: The PR title
        file_count: Number of files changed
        additions: Lines added
        deletions: Lines deleted
        comment_count: Number of comments
        repo_languages: Top languages from repository (e.g., ["Python", "TypeScript"])
        state: PR state (open, merged, closed)
        labels: List of label names
        is_draft: Whether PR is a draft
        is_hotfix: Whether PR is marked as hotfix
        is_revert: Whether PR is a revert
        cycle_time_hours: Time from open to merge
        review_time_hours: Time from open to first review
        commits_after_first_review: Number of commits after first review
        review_rounds: Number of review cycles
        file_paths: List of changed file paths (for tech detection)
        commit_messages: List of commit messages (for AI co-author detection)
        milestone: Milestone title (e.g., "Q1 2025 Release")
        assignees: List of assignee usernames
        linked_issues: List of linked issue references (e.g., ["#123", "#456"])
        jira_key: Jira issue key (e.g., "PROJ-1234")
        author_name: PR author's display name
        reviewers: List of reviewer names
        review_comments: List of review comment bodies (sample)
        repo_name: Full repository path (e.g., "anthropics/cookbook")

    Returns:
        Formatted user prompt for LLM
    """
    sections = []

    # === Basic Info ===
    basic_info = []
    if repo_name:
        basic_info.append(f"Repository: {repo_name}")
    if pr_title:
        basic_info.append(f"Title: {pr_title}")
    if author_name:
        basic_info.append(f"Author: {author_name}")
    if state:
        basic_info.append(f"State: {state}")
    if labels:
        basic_info.append(f"Labels: {', '.join(labels)}")
    if is_draft:
        basic_info.append("Draft: Yes")
    if is_hotfix:
        basic_info.append("Hotfix: Yes")
    if is_revert:
        basic_info.append("Revert: Yes")
    if basic_info:
        sections.append("\n".join(basic_info))

    # === Metadata (v6.1.0) ===
    metadata = []
    if milestone:
        metadata.append(f"Milestone: {milestone}")
    if jira_key:
        metadata.append(f"Jira: {jira_key}")
    if assignees:
        # Limit to 10 assignees
        names_str = ", ".join(assignees[:10])
        if len(assignees) > 10:
            names_str += f" (+{len(assignees) - 10} more)"
        metadata.append(f"Assignees: {names_str}")
    if linked_issues:
        metadata.append(f"Linked issues: {', '.join(linked_issues)}")
    if metadata:
        sections.append("\n".join(metadata))

    # === Code Changes ===
    changes = []
    if file_count > 0:
        changes.append(f"Files changed: {file_count}")
    if additions > 0 or deletions > 0:
        changes.append(f"Lines: +{additions}/-{deletions}")
    if file_paths:
        # Show all files if <10, otherwise truncate at 20
        if len(file_paths) <= 10:
            paths_str = ", ".join(file_paths)
        else:
            paths_str = ", ".join(file_paths[:20])
            if len(file_paths) > 20:
                paths_str += f" (+{len(file_paths) - 20} more)"
        changes.append(f"Files: {paths_str}")
    if changes:
        sections.append("\n".join(changes))

    # === Timing & Review ===
    timing = []
    if cycle_time_hours is not None:
        timing.append(f"Cycle time: {cycle_time_hours:.1f} hours")
    if review_time_hours is not None:
        timing.append(f"Time to first review: {review_time_hours:.1f} hours")
    if comment_count and comment_count > 0:
        timing.append(f"Comments: {comment_count}")
    if commits_after_first_review is not None and commits_after_first_review > 0:
        timing.append(f"Commits after first review: {commits_after_first_review}")
    if review_rounds is not None and review_rounds > 0:
        timing.append(f"Review rounds: {review_rounds}")
    if timing:
        sections.append("\n".join(timing))

    # === Repository Context ===
    if repo_languages:
        sections.append(f"Repository languages: {', '.join(repo_languages)}")

    # === Commit Messages (for AI co-author detection) ===
    if commit_messages:
        # Limit to last 5 commits
        msgs = commit_messages[:5]
        if len(commit_messages) > 5:
            msgs.append(f"... and {len(commit_messages) - 5} more commits")
        sections.append("Recent commits:\n" + "\n".join(f"- {m}" for m in msgs))

    # === Reviewers (v6.1.0) ===
    if reviewers:
        # Limit to 5 reviewers
        names_str = ", ".join(reviewers[:5])
        if len(reviewers) > 5:
            names_str += f" (+{len(reviewers) - 5} more)"
        sections.append(f"Reviewers: {names_str}")

    # === Review Comments (v6.1.0) ===
    if review_comments:
        # Limit to 3 comments, truncate long ones
        truncated = []
        for comment in review_comments[:3]:
            if len(comment) > 200:
                truncated.append(comment[:200] + "...")
            else:
                truncated.append(comment)
        sections.append("Review comments:\n" + "\n".join(f"- {c}" for c in truncated))

    # === Description ===
    sections.append(f"Description:\n{pr_body}")

    return "Analyze this pull request:\n\n" + "\n\n".join(sections)


def get_user_prompt_v2(context: PRContext) -> str:
    """Generate user prompt from a PRContext dictionary.

    This is the new API replacing get_user_prompt() with 26 individual parameters.
    All fields are accessed via .get() to handle optional/missing fields gracefully.

    Args:
        context: A PRContext TypedDict containing PR data for analysis.
                 Only pr_body is effectively required for meaningful analysis.

    Returns:
        Formatted user prompt string for LLM analysis.

    Example:
        from apps.metrics.types import PRContext

        context: PRContext = {
            "pr_body": "Add new feature...",
            "pr_title": "feat: add dark mode",
            "author_name": "johndoe",
            "additions": 150,
            "deletions": 20,
        }
        prompt = get_user_prompt_v2(context)
    """
    sections = []

    # === Basic Info ===
    basic_info = []
    if context.get("repo_name"):
        basic_info.append(f"Repository: {context['repo_name']}")
    if context.get("pr_title"):
        basic_info.append(f"Title: {context['pr_title']}")
    if context.get("author_name"):
        basic_info.append(f"Author: {context['author_name']}")
    if context.get("state"):
        basic_info.append(f"State: {context['state']}")
    if context.get("labels"):
        basic_info.append(f"Labels: {', '.join(context['labels'])}")
    if context.get("is_draft"):
        basic_info.append("Draft: Yes")
    if context.get("is_hotfix"):
        basic_info.append("Hotfix: Yes")
    if context.get("is_revert"):
        basic_info.append("Revert: Yes")
    if basic_info:
        sections.append("\n".join(basic_info))

    # === Metadata ===
    metadata = []
    if context.get("milestone"):
        metadata.append(f"Milestone: {context['milestone']}")
    if context.get("jira_key"):
        metadata.append(f"Jira: {context['jira_key']}")
    if context.get("assignees"):
        assignees = context["assignees"]
        names_str = ", ".join(assignees[:10])
        if len(assignees) > 10:
            names_str += f" (+{len(assignees) - 10} more)"
        metadata.append(f"Assignees: {names_str}")
    if context.get("linked_issues"):
        metadata.append(f"Linked issues: {', '.join(context['linked_issues'])}")
    if metadata:
        sections.append("\n".join(metadata))

    # === Code Changes ===
    changes = []
    file_count = context.get("file_count", 0)
    additions = context.get("additions", 0)
    deletions = context.get("deletions", 0)
    if file_count > 0:
        changes.append(f"Files changed: {file_count}")
    if additions > 0 or deletions > 0:
        changes.append(f"Lines: +{additions}/-{deletions}")
    if context.get("file_paths"):
        file_paths = context["file_paths"]
        if len(file_paths) <= 10:
            paths_str = ", ".join(file_paths)
        else:
            paths_str = ", ".join(file_paths[:20])
            if len(file_paths) > 20:
                paths_str += f" (+{len(file_paths) - 20} more)"
        changes.append(f"Files: {paths_str}")
    if changes:
        sections.append("\n".join(changes))

    # === Timing & Review ===
    timing = []
    cycle_time = context.get("cycle_time_hours")
    review_time = context.get("review_time_hours")
    comment_count = context.get("comment_count", 0)
    commits_after = context.get("commits_after_first_review")
    review_rounds = context.get("review_rounds")

    if cycle_time is not None:
        timing.append(f"Cycle time: {cycle_time:.1f} hours")
    if review_time is not None:
        timing.append(f"Time to first review: {review_time:.1f} hours")
    if comment_count > 0:
        timing.append(f"Comments: {comment_count}")
    if commits_after is not None and commits_after > 0:
        timing.append(f"Commits after first review: {commits_after}")
    if review_rounds is not None and review_rounds > 0:
        timing.append(f"Review rounds: {review_rounds}")
    if timing:
        sections.append("\n".join(timing))

    # === Repository Context ===
    if context.get("repo_languages"):
        sections.append(f"Repository languages: {', '.join(context['repo_languages'])}")

    # === Commit Messages (for AI co-author detection) ===
    if context.get("commit_messages"):
        commit_messages = context["commit_messages"]
        msgs = commit_messages[:5]
        if len(commit_messages) > 5:
            msgs.append(f"... and {len(commit_messages) - 5} more commits")
        sections.append("Recent commits:\n" + "\n".join(f"- {m}" for m in msgs))

    # === Reviewers ===
    if context.get("reviewers"):
        reviewers = context["reviewers"]
        names_str = ", ".join(reviewers[:5])
        if len(reviewers) > 5:
            names_str += f" (+{len(reviewers) - 5} more)"
        sections.append(f"Reviewers: {names_str}")

    # === Review Comments ===
    if context.get("review_comments"):
        review_comments = context["review_comments"]
        truncated = []
        for comment in review_comments[:3]:
            if len(comment) > 200:
                truncated.append(comment[:200] + "...")
            else:
                truncated.append(comment)
        sections.append("Review comments:\n" + "\n".join(f"- {c}" for c in truncated))

    # === Description ===
    pr_body = context.get("pr_body", "")
    sections.append(f"Description:\n{pr_body}")

    return "Analyze this pull request:\n\n" + "\n\n".join(sections)


def build_pr_context(pr: PullRequest) -> PRContext:
    """Build a PRContext dictionary from a PullRequest model.

    This bridges the gap between the PullRequest model and the new PRContext type,
    enabling gradual migration from build_llm_pr_context() to get_user_prompt_v2().

    Args:
        pr: A PullRequest instance. For best performance, prefetch relations:
            pr = PullRequest.objects.select_related("author").prefetch_related(
                "files", "commits", "reviews__reviewer", "comments__author"
            ).get(id=pr_id)

    Returns:
        A PRContext dictionary with fields extracted from the PR model.
    """
    context: PRContext = {
        "pr_body": pr.body or "",
        "pr_title": pr.title or "",
        "repo_name": pr.github_repo or "",
        "author_name": _get_member_display_name(pr.author) if pr.author else "",
        "file_count": pr.files_changed or 0,
        "additions": pr.additions or 0,
        "deletions": pr.deletions or 0,
        "state": pr.state or "",
        "is_draft": pr.is_draft or False,
        "is_hotfix": pr.is_hotfix or False,
        "is_revert": pr.is_revert or False,
        "comment_count": pr.comments_count or 0,
    }

    # Optional timing metrics
    if pr.cycle_time_hours is not None:
        context["cycle_time_hours"] = pr.cycle_time_hours
    if pr.review_time_hours is not None:
        context["review_time_hours"] = pr.review_time_hours
    if pr.commits_after_first_review is not None:
        context["commits_after_first_review"] = pr.commits_after_first_review
    if pr.review_rounds is not None:
        context["review_rounds"] = pr.review_rounds

    # File paths from prefetched files relation
    if hasattr(pr, "files") and pr.files.exists():
        context["file_paths"] = list(pr.files.values_list("file_path", flat=True))

    # Commit messages from prefetched commits relation
    if hasattr(pr, "commits") and pr.commits.exists():
        context["commit_messages"] = list(pr.commits.values_list("message", flat=True))

    # Labels from JSON field
    if pr.labels:
        context["labels"] = pr.labels if isinstance(pr.labels, list) else []

    # Jira key
    if pr.jira_key:
        context["jira_key"] = pr.jira_key

    # Reviewers from prefetched reviews relation
    if hasattr(pr, "reviews") and pr.reviews.exists():
        reviewer_names = []
        for review in pr.reviews.all():
            if review.reviewer:
                name = _get_member_display_name(review.reviewer)
                if name and name not in reviewer_names:
                    reviewer_names.append(name)
        if reviewer_names:
            context["reviewers"] = reviewer_names

    return context


def build_llm_pr_context(pr: PullRequest) -> str:
    """Build complete LLM context from a PullRequest object.

    This is the UNIFIED function for formatting PR data for LLM analysis.
    Use this instead of manually extracting fields.

    Requires prefetched relations for performance:
        pr = PullRequest.objects.select_related("author").prefetch_related(
            "files", "commits", "reviews__reviewer", "comments__author"
        ).get(id=pr_id)

    Sections included:
        1. PR Metadata - number, title, repo, author, state, timestamps
        2. Flags - draft, hotfix, revert
        3. Organization - labels, milestone, assignees, jira, linked issues
        4. Code Changes - size, files with categories
        5. Timing Metrics - cycle time, review time, iterations
        6. Commits - messages with AI co-author signatures
        7. Reviews - state, reviewer, body
        8. Comments - PR discussion (may contain AI mentions)
        9. Prior AI Detection - regex pattern results for LLM to confirm/refine
        10. Repository Languages - from TrackedRepository
        11. Description - PR body

    Args:
        pr: PullRequest object with prefetched relations

    Returns:
        Formatted context string for LLM user prompt
    """
    sections = []

    # === 1. PR Metadata ===
    metadata = []
    metadata.append(f"PR #{pr.github_pr_id}")
    if pr.title:
        metadata.append(f"Title: {pr.title}")
    metadata.append(f"Repository: {pr.github_repo}")

    # Author with GitHub username
    if pr.author:
        author_str = pr.author.display_name or pr.author.github_username or "unknown"
        if pr.author.github_username and pr.author.display_name:
            author_str = f"{pr.author.display_name} (@{pr.author.github_username})"
        metadata.append(f"Author: {author_str}")

    if pr.state:
        metadata.append(f"State: {pr.state}")
    if pr.pr_created_at:
        metadata.append(f"Created: {pr.pr_created_at.strftime('%Y-%m-%d %H:%M UTC')}")
    if pr.merged_at:
        metadata.append(f"Merged: {pr.merged_at.strftime('%Y-%m-%d %H:%M UTC')}")

    sections.append("\n".join(metadata))

    # === 2. Flags ===
    flags = []
    if pr.is_draft:
        flags.append("Draft: Yes")
    if pr.is_hotfix:
        flags.append("Hotfix: Yes")
    if pr.is_revert:
        flags.append("Revert: Yes")
    if flags:
        sections.append("\n".join(flags))

    # === 3. Organization ===
    org = []
    if pr.labels:
        org.append(f"Labels: {', '.join(pr.labels)}")
    if pr.milestone_title:
        org.append(f"Milestone: {pr.milestone_title}")
    if pr.assignees:
        assignees_str = ", ".join(pr.assignees[:10])
        if len(pr.assignees) > 10:
            assignees_str += f" (+{len(pr.assignees) - 10} more)"
        org.append(f"Assignees: {assignees_str}")
    if pr.jira_key:
        org.append(f"Jira: {pr.jira_key}")
    if pr.linked_issues:
        issues_str = ", ".join(f"#{i}" for i in pr.linked_issues[:10])
        org.append(f"Linked issues: {issues_str}")
    if org:
        sections.append("\n".join(org))

    # === 4. Code Changes ===
    changes = []
    changes.append(f"Size: +{pr.additions}/-{pr.deletions} lines")

    # Get files (use prefetched if available)
    try:
        files = list(pr.files.all()[:20])
    except AttributeError:
        files = []

    if files:
        changes.append(f"Files changed: {len(files)}")
        file_lines = []
        for f in files:
            category = f.file_category or "other"
            file_lines.append(f"  - [{category}] {f.filename} (+{f.additions}/-{f.deletions})")
        changes.append("\n".join(file_lines))
    if changes:
        sections.append("\n".join(changes))

    # === 5. Timing Metrics ===
    timing = []
    if pr.cycle_time_hours is not None:
        timing.append(f"Cycle time: {float(pr.cycle_time_hours):.1f} hours")
    if pr.review_time_hours is not None:
        timing.append(f"Time to first review: {float(pr.review_time_hours):.1f} hours")
    if pr.total_comments:
        timing.append(f"Comments: {pr.total_comments}")
    if pr.commits_after_first_review:
        timing.append(f"Commits after first review: {pr.commits_after_first_review}")
    if pr.review_rounds:
        timing.append(f"Review rounds: {pr.review_rounds}")
    if pr.avg_fix_response_hours is not None:
        timing.append(f"Avg fix response: {float(pr.avg_fix_response_hours):.1f} hours")
    if timing:
        sections.append("\n".join(timing))

    # === 6. Commits ===
    try:
        commits = list(pr.commits.all().order_by("committed_at")[:10])
    except AttributeError:
        commits = []

    if commits:
        commit_lines = ["Commits:"]
        baseline = pr.pr_created_at
        for c in commits:
            msg = c.message or ""
            # Truncate but keep Co-Authored-By lines visible
            if len(msg) > 300:
                msg = msg[:300] + "..."

            timestamp_prefix = _format_timestamp_prefix(c.committed_at, baseline)
            commit_lines.append(f"- {timestamp_prefix}{msg}")
        sections.append("\n".join(commit_lines))

    # === 7. Reviews ===
    try:
        reviews = list(pr.reviews.exclude(body__isnull=True).exclude(body="").order_by("submitted_at")[:5])
    except AttributeError:
        reviews = []

    if reviews:
        review_lines = ["Reviews:"]
        baseline = pr.pr_created_at
        for r in reviews:
            reviewer = _get_member_display_name(r.reviewer)
            body = r.body[:200] + "..." if len(r.body) > 200 else r.body
            state = r.state.upper() if r.state else "COMMENT"

            timestamp_prefix = _format_timestamp_prefix(r.submitted_at, baseline)
            review_lines.append(f"- {timestamp_prefix}[{state}] {reviewer}: {body}")
        sections.append("\n".join(review_lines))

    # === 8. Comments (NEW - may contain AI discussion) ===
    try:
        comments = list(pr.comments.exclude(body__isnull=True).exclude(body="").order_by("comment_created_at")[:5])
    except AttributeError:
        comments = []

    if comments:
        comment_lines = ["Comments:"]
        baseline = pr.pr_created_at
        for c in comments:
            author = _get_member_display_name(c.author)
            body = c.body[:200] + "..." if len(c.body) > 200 else c.body

            timestamp_prefix = _format_timestamp_prefix(c.comment_created_at, baseline)
            comment_lines.append(f"- {timestamp_prefix}{author}: {body}")
        sections.append("\n".join(comment_lines))

    # === 9. Prior AI Detection ===
    # Show what regex patterns already detected so LLM can confirm/refine
    if pr.is_ai_assisted or pr.ai_tools_detected:
        prior_detection = ["Prior AI detection (regex):"]
        if pr.ai_tools_detected:
            tools_str = ", ".join(pr.ai_tools_detected)
            prior_detection.append(f"- Tools detected: {tools_str}")
        else:
            prior_detection.append("- AI assisted: Yes (no specific tools identified)")
        if pr.ai_detection_version:
            prior_detection.append(f"- Pattern version: {pr.ai_detection_version}")
        sections.append("\n".join(prior_detection))

    # === 10. Repository Languages ===
    repo_languages = _get_repo_languages(pr)
    if repo_languages:
        sections.append(repo_languages)

    # === 11. Description ===
    if pr.body:
        sections.append(f"Description:\n{pr.body}")

    return "Analyze this pull request:\n\n" + "\n\n".join(sections)


def _get_repo_languages(pr: PullRequest) -> str:
    """Get repository languages from TrackedRepository.

    Args:
        pr: PullRequest object

    Returns:
        Formatted string with primary and top languages, or empty string
    """
    from apps.integrations.models import TrackedRepository

    try:
        repo = TrackedRepository.objects.get(  # noqa: TEAM001 - Looking up by repo name
            full_name=pr.github_repo,
            team=pr.team,
            is_active=True,
        )
    except TrackedRepository.DoesNotExist:
        return ""

    if not repo.languages:
        return ""

    # Format top languages (limit to 5)
    sorted_langs = sorted(repo.languages.items(), key=lambda x: x[1], reverse=True)[:5]
    if not sorted_langs:
        return ""

    lines = ["Repository languages:"]
    lines.append(f"- Primary: {repo.primary_language or 'Unknown'}")
    lines.append(f"- All: {', '.join(lang for lang, _ in sorted_langs)}")

    return "\n".join(lines)


@dataclass
class TimelineEvent:
    """A single event in a PR timeline.

    Attributes:
        hours_after_pr_created: Hours after PR creation (can be negative if before)
        event_type: Type of event (COMMIT, REVIEW, COMMENT, MERGED)
        content: Event content (commit message, review body, comment text, etc.)
    """

    hours_after_pr_created: float
    event_type: str
    content: str


def _collect_timeline_events(
    items,
    event_type: str,
    baseline: datetime,
    get_timestamp,
    get_content,
) -> list[TimelineEvent]:
    """Generic helper to collect timeline events from a queryset.

    Args:
        items: Queryset or list of objects to process
        event_type: Type of event (COMMIT, REVIEW, COMMENT)
        baseline: Baseline timestamp for relative hours calculation
        get_timestamp: Function to extract timestamp from item
        get_content: Function to format content from item

    Returns:
        List of TimelineEvent objects
    """
    events = []
    for item in items:
        timestamp = get_timestamp(item)
        if timestamp is None:
            continue

        hours = calculate_relative_hours(timestamp, baseline)
        if hours is not None:
            events.append(
                TimelineEvent(
                    hours_after_pr_created=hours,
                    event_type=event_type,
                    content=get_content(item),
                )
            )
    return events


def build_timeline(pr: PullRequest) -> list[TimelineEvent]:
    """Build chronological timeline of events from a PullRequest.

    Collects commits, reviews, comments, and merge events into a unified timeline
    sorted by timestamp.

    Args:
        pr: PullRequest object with prefetched commits, reviews, comments

    Returns:
        List of TimelineEvent objects sorted by hours_after_pr_created
    """
    events = []
    baseline = pr.pr_created_at

    # Collect commits
    try:
        commits = pr.commits.all()
    except AttributeError:
        commits = []

    events.extend(
        _collect_timeline_events(
            commits,
            event_type="COMMIT",
            baseline=baseline,
            get_timestamp=lambda c: c.committed_at,
            get_content=lambda c: c.message or "",
        )
    )

    # Collect reviews
    try:
        reviews = pr.reviews.all()
    except AttributeError:
        reviews = []

    def format_review_content(review):
        state = review.state.upper() if review.state else "COMMENT"
        reviewer = _get_member_display_name(review.reviewer)
        body = review.body or ""
        return f"[{state}]: {reviewer}: {body}"

    events.extend(
        _collect_timeline_events(
            reviews,
            event_type="REVIEW",
            baseline=baseline,
            get_timestamp=lambda r: r.submitted_at,
            get_content=format_review_content,
        )
    )

    # Collect comments
    try:
        comments = pr.comments.all()
    except AttributeError:
        comments = []

    def format_comment_content(comment):
        author = _get_member_display_name(comment.author)
        body = comment.body or ""
        return f"{author}: {body}"

    events.extend(
        _collect_timeline_events(
            comments,
            event_type="COMMENT",
            baseline=baseline,
            get_timestamp=lambda c: c.comment_created_at,
            get_content=format_comment_content,
        )
    )

    # Add MERGED event if PR was merged
    if pr.merged_at:
        hours = calculate_relative_hours(pr.merged_at, baseline)
        if hours is not None:
            events.append(
                TimelineEvent(
                    hours_after_pr_created=hours,
                    event_type="MERGED",
                    content="",
                )
            )

    # Sort by timestamp
    events.sort(key=lambda e: e.hours_after_pr_created)

    return events


def format_timeline(events: list[TimelineEvent], max_events: int = 15) -> str:
    """Format timeline events as a human-readable string.

    Args:
        events: List of TimelineEvent objects
        max_events: Maximum number of events to include (default 15)

    Returns:
        Formatted timeline string with "Timeline:\\n" prefix, or empty string if no events
    """
    if not events:
        return ""

    lines = ["Timeline:"]

    # Limit to max_events
    for event in events[:max_events]:
        if event.content:
            lines.append(f"- [+{event.hours_after_pr_created}h] {event.event_type}: {event.content}")
        else:
            lines.append(f"- [+{event.hours_after_pr_created}h] {event.event_type}")

    return "\n".join(lines)
