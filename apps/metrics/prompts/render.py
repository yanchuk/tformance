"""Jinja2 template rendering for LLM prompts.

This module provides functions to render prompts from Jinja2 templates,
enabling composable and maintainable prompt definitions.

Template Structure:
    templates/
    ├── pr_analysis/          # PR Analysis prompts
    │   ├── system.jinja2
    │   ├── user.jinja2
    │   └── sections/
    └── insight/              # Insight generation prompts
        ├── system.jinja2
        └── user.jinja2

Usage:
    # PR Analysis
    from apps.metrics.prompts.render import render_pr_system_prompt, render_pr_user_prompt

    # Insights
    from apps.metrics.prompts.render import render_insight_system_prompt, render_insight_user_prompt
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from apps.metrics.prompts.constants import PROMPT_VERSION

# Template directory path
_TEMPLATE_DIR = Path(__file__).parent / "templates"

# Create Jinja2 environment with template loader
# trim_blocks=False to preserve blank lines between sections
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    trim_blocks=False,
    lstrip_blocks=False,
    keep_trailing_newline=False,
)


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace in rendered template output.

    - Collapses multiple consecutive blank lines to single blank line
    - Strips trailing whitespace from each line
    - Removes trailing newlines
    """
    lines = text.split("\n")
    normalized = []
    prev_blank = False

    for line in lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        normalized.append(line.rstrip())
        prev_blank = is_blank

    return "\n".join(normalized).rstrip()


# =============================================================================
# PR Analysis Prompts
# =============================================================================


@lru_cache(maxsize=1)
def render_pr_system_prompt(version: str | None = None) -> str:
    """Render the PR analysis system prompt from Jinja2 templates.

    This is the SINGLE SOURCE OF TRUTH for PR analysis system prompts.
    Edit templates/pr_analysis/system.jinja2 to modify.

    Args:
        version: Optional version string. Defaults to PROMPT_VERSION.

    Returns:
        The fully rendered system prompt string.
    """
    template = _env.get_template("pr_analysis/system.jinja2")
    rendered = template.render(version=version or PROMPT_VERSION)
    return _normalize_whitespace(rendered)


def render_pr_user_prompt(
    pr_body: str,
    pr_title: str = "",
    file_count: int = 0,
    additions: int = 0,
    deletions: int = 0,
    comment_count: int = 0,
    repo_languages: list[str] | None = None,
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
    milestone: str | None = None,
    assignees: list[str] | None = None,
    linked_issues: list[str] | None = None,
    jira_key: str | None = None,
    author_name: str | None = None,
    reviewers: list[str] | None = None,
    review_comments: list[str] | None = None,
    timeline: str | None = None,
    repo_name: str | None = None,
    commit_co_authors: list[str] | None = None,
    ai_config_files: list[str] | None = None,
) -> str:
    """Render PR analysis user prompt from Jinja2 template.

    This is the SINGLE SOURCE OF TRUTH for PR analysis user prompts.
    Edit templates/pr_analysis/user.jinja2 to modify.

    Args:
        pr_body: The PR description text
        pr_title: The PR title
        file_count: Number of files changed
        additions: Lines added
        deletions: Lines deleted
        comment_count: Number of comments
        repo_languages: Top languages from repository
        state: PR state (open, merged, closed)
        labels: List of label names
        is_draft: Whether PR is a draft
        is_hotfix: Whether PR is marked as hotfix
        is_revert: Whether PR is a revert
        cycle_time_hours: Time from open to merge
        review_time_hours: Time from open to first review
        commits_after_first_review: Number of commits after first review
        review_rounds: Number of review cycles
        file_paths: List of changed file paths
        commit_messages: List of commit messages
        milestone: Milestone title
        assignees: List of assignee usernames
        linked_issues: List of linked issue references
        jira_key: Jira issue key
        author_name: PR author's display name
        reviewers: List of reviewer names
        review_comments: List of review comment bodies
        timeline: Pre-formatted timeline string
        repo_name: Full repository path
        commit_co_authors: List of AI co-authors from commits
        ai_config_files: List of AI tool config files

    Returns:
        Formatted user prompt for LLM
    """
    template = _env.get_template("pr_analysis/user.jinja2")
    rendered = template.render(
        pr_body=pr_body,
        pr_title=pr_title,
        file_count=file_count,
        additions=additions,
        deletions=deletions,
        comment_count=comment_count,
        repo_languages=repo_languages,
        state=state,
        labels=labels,
        is_draft=is_draft,
        is_hotfix=is_hotfix,
        is_revert=is_revert,
        cycle_time_hours=cycle_time_hours,
        review_time_hours=review_time_hours,
        commits_after_first_review=commits_after_first_review,
        review_rounds=review_rounds,
        file_paths=file_paths,
        commit_messages=commit_messages,
        milestone=milestone,
        assignees=assignees,
        linked_issues=linked_issues,
        jira_key=jira_key,
        author_name=author_name,
        reviewers=reviewers,
        review_comments=review_comments,
        timeline=timeline,
        repo_name=repo_name,
        commit_co_authors=commit_co_authors,
        ai_config_files=ai_config_files,
    )
    return _normalize_whitespace(rendered)


# =============================================================================
# Insight Prompts
# =============================================================================


@lru_cache(maxsize=2)  # Cache both True and False variants
def render_insight_system_prompt(include_copilot: bool = True) -> str:
    """Render the insight generation system prompt from Jinja2 templates.

    This is the SINGLE SOURCE OF TRUTH for insight system prompts.
    Edit templates/insight/system.jinja2 to modify.

    Args:
        include_copilot: If True, include Copilot metrics guidance section.
            Set to False for teams without Copilot to save ~800 chars.

    Returns:
        The fully rendered system prompt string.
    """
    template = _env.get_template("insight/system.jinja2")
    rendered = template.render(include_copilot=include_copilot)
    return _normalize_whitespace(rendered)


def render_insight_user_prompt(data: dict) -> str:
    """Render insight user prompt from Jinja2 template.

    This is the SINGLE SOURCE OF TRUTH for insight user prompts.
    Edit templates/insight/user.jinja2 to modify.

    Args:
        data: InsightData dict with metrics for the team

    Returns:
        Formatted user prompt for LLM
    """
    template = _env.get_template("insight/user.jinja2")
    rendered = template.render(**data)
    return _normalize_whitespace(rendered)


# =============================================================================
# Backward Compatibility Aliases (Deprecated)
# =============================================================================
# These are kept for backward compatibility during transition.
# Use the new explicit names: render_pr_system_prompt, render_pr_user_prompt


def render_system_prompt(version: str | None = None) -> str:
    """Render PR analysis system prompt. DEPRECATED: Use render_pr_system_prompt()."""
    return render_pr_system_prompt(version)


def render_user_prompt(
    pr_body: str,
    pr_title: str = "",
    file_count: int = 0,
    additions: int = 0,
    deletions: int = 0,
    comment_count: int = 0,
    repo_languages: list[str] | None = None,
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
    milestone: str | None = None,
    assignees: list[str] | None = None,
    linked_issues: list[str] | None = None,
    jira_key: str | None = None,
    author_name: str | None = None,
    reviewers: list[str] | None = None,
    review_comments: list[str] | None = None,
    timeline: str | None = None,
    repo_name: str | None = None,
    commit_co_authors: list[str] | None = None,
    ai_config_files: list[str] | None = None,
) -> str:
    """Render PR analysis user prompt. DEPRECATED: Use render_pr_user_prompt()."""
    return render_pr_user_prompt(
        pr_body=pr_body,
        pr_title=pr_title,
        file_count=file_count,
        additions=additions,
        deletions=deletions,
        comment_count=comment_count,
        repo_languages=repo_languages,
        state=state,
        labels=labels,
        is_draft=is_draft,
        is_hotfix=is_hotfix,
        is_revert=is_revert,
        cycle_time_hours=cycle_time_hours,
        review_time_hours=review_time_hours,
        commits_after_first_review=commits_after_first_review,
        review_rounds=review_rounds,
        file_paths=file_paths,
        commit_messages=commit_messages,
        milestone=milestone,
        assignees=assignees,
        linked_issues=linked_issues,
        jira_key=jira_key,
        author_name=author_name,
        reviewers=reviewers,
        review_comments=review_comments,
        timeline=timeline,
        repo_name=repo_name,
        commit_co_authors=commit_co_authors,
        ai_config_files=ai_config_files,
    )


# =============================================================================
# Utility Functions
# =============================================================================


def get_template_dir() -> Path:
    """Get the path to the templates directory."""
    return _TEMPLATE_DIR


def list_template_sections(template_type: str = "pr_analysis") -> list[str]:
    """List all available template section files for a given template type.

    Args:
        template_type: Either "pr_analysis" or "insight". Defaults to "pr_analysis".

    Returns:
        Sorted list of section file names (e.g., ["intro.jinja2", "ai_detection.jinja2"])
    """
    sections_dir = _TEMPLATE_DIR / template_type / "sections"
    if not sections_dir.exists():
        return []
    return sorted(f.name for f in sections_dir.glob("*.jinja2"))
