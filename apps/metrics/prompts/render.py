"""Jinja2 template rendering for LLM prompts.

This module provides functions to render prompts from Jinja2 templates,
enabling composable and maintainable prompt definitions.

Usage:
    from apps.metrics.prompts.render import render_system_prompt

    prompt = render_system_prompt()  # Full prompt with all sections
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from apps.metrics.services.llm_prompts import PROMPT_VERSION

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


def render_system_prompt(version: str | None = None) -> str:
    """Render the system prompt from Jinja2 templates.

    Args:
        version: Optional version string to include in template.
                 Defaults to PROMPT_VERSION from llm_prompts.py.

    Returns:
        The fully rendered system prompt string.

    Example:
        >>> prompt = render_system_prompt()
        >>> "AI Detection Rules" in prompt
        True
    """
    template = _env.get_template("system.jinja2")
    rendered = template.render(version=version or PROMPT_VERSION)

    # Normalize whitespace: collapse multiple blank lines to single
    lines = rendered.split("\n")
    normalized = []
    prev_blank = False

    for line in lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        normalized.append(line)
        prev_blank = is_blank

    # Remove trailing whitespace from each line and trailing newlines
    result = "\n".join(line.rstrip() for line in normalized).rstrip()
    return result


def get_template_dir() -> Path:
    """Get the path to the templates directory.

    Returns:
        Path to the templates directory.
    """
    return _TEMPLATE_DIR


def list_template_sections() -> list[str]:
    """List all available template section files.

    Returns:
        List of section template filenames (without path).
    """
    sections_dir = _TEMPLATE_DIR / "sections"
    if not sections_dir.exists():
        return []

    return sorted(f.name for f in sections_dir.glob("*.jinja2"))


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
    reviews: list[str] | None = None,
    comments: list[str] | None = None,
) -> str:
    """Render user prompt from Jinja2 template with full PR context.

    This is the Jinja-based equivalent of build_llm_pr_context() in llm_prompts.py.
    Use this for systematic template-based prompt generation.

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
        commit_messages: List of commit messages with [+X.Xh] timestamps
        milestone: Milestone title
        assignees: List of assignee usernames
        linked_issues: List of linked issue references
        jira_key: Jira issue key
        author_name: PR author's display name
        reviewers: Fallback list of reviewer names (used if reviews not provided)
        review_comments: Fallback list of comment bodies (used if comments not provided)
        reviews: List of "[+X.Xh] [STATE] reviewer: body" strings
        comments: List of "[+X.Xh] author: body" strings

    Returns:
        Formatted user prompt for LLM

    Example:
        >>> prompt = render_user_prompt(pr_title="Fix bug", pr_body="Fixed it")
        >>> "Analyze this pull request:" in prompt
        True
    """
    template = _env.get_template("user.jinja2")
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
        reviews=reviews,
        comments=comments,
    )

    # Normalize: strip trailing whitespace from lines
    lines = rendered.split("\n")
    return "\n".join(line.rstrip() for line in lines).rstrip()
