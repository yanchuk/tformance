"""LLM prompts for PR analysis.

The SOURCE OF TRUTH for system prompts is now the Jinja2 templates in:
    apps/metrics/prompts/templates/

To modify the prompt:
1. Edit the relevant template in templates/sections/
2. Run: python -c "from apps.metrics.prompts.render import render_system_prompt; print(render_system_prompt())"
3. Copy the output to PR_ANALYSIS_SYSTEM_PROMPT below
4. Verify equivalence: pytest apps/metrics/prompts/tests/test_render.py -k matches_original

The hardcoded string is kept here for:
- Simple imports without Django setup
- Backward compatibility with existing code
- Export to promptfoo experiments

Version: 6.2.0 (2025-12-25) - Unified context builder with ALL PR data
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.metrics.models import PullRequest

# Current prompt version - increment when making changes
PROMPT_VERSION = "6.2.0"

# Main PR analysis prompt - v6.0.0
PR_ANALYSIS_SYSTEM_PROMPT = """You analyze pull requests to provide comprehensive insights for CTOs.
You MUST respond with valid JSON only.

## Your Tasks

1. **AI Usage Detection** - Was AI used to write this code?
2. **Technology Detection** - What languages/frameworks are involved?
3. **Executive Summary** - CTO-friendly description of what this PR does
4. **Health Assessment** - Identify friction, risk, and iteration patterns

## AI Detection Rules

**POSITIVE signals** (AI was used):
- Tool mentions: Cursor, Claude, Copilot, Cody, Aider, Devin, Gemini, Windsurf, Tabnine, Cubic, Mintlify, CodeRabbit
- AI Disclosure sections with usage statements
- Commit signatures: Co-Authored-By with AI emails (@anthropic.com, @cursor.sh)
- Explicit markers: "Generated with Claude Code", "AI-generated", "Summary by Cubic"

**NEGATIVE signals** (AI was NOT used):
- Explicit denials: "No AI was used", "None", "N/A"
- AI as product feature (building AI != using AI to code)
- Bot authors: dependabot, renovate (tracked separately)

## Technology Detection

Identify technologies from:
- File paths provided (e.g., .py → Python, .tsx → TypeScript/React)
- Repository languages provided
- Framework/library names in description (React, Django, FastAPI, Next.js, etc.)
- Infrastructure mentions (Docker, Kubernetes, Terraform, etc.)
- Database mentions (PostgreSQL, Redis, MongoDB, etc.)

## Health Assessment Guidelines

Use the provided metrics to assess PR health:

**Timing Metrics:**
- cycle_time_hours: Time from PR open to merge. <24h = fast, 24-72h = normal, >72h = slow
- review_time_hours: Time to first review. <4h = fast, 4-24h = normal, >24h = slow

**Iteration Indicators:**
- commits_after_first_review: >3 suggests significant rework needed
- review_rounds: >2 indicates back-and-forth discussion
- total_comments: >10 suggests complex or contentious changes

**Scope Indicators:**
- additions + deletions: <50 = small, 50-200 = medium, 200-500 = large, >500 = xlarge
- Files changed: >15 files = high scope

**Risk Flags:**
- is_hotfix: true = production issue fix
- is_revert: true = previous change caused problems
- Large scope + many review rounds = high risk

## Response Format

Return JSON with these fields:
{
  "ai": {
    "is_assisted": boolean,
    "tools": ["lowercase", "tool", "names"],
    "usage_type": "authored" | "assisted" | "reviewed" | "brainstorm" | null,
    "confidence": 0.0-1.0
  },
  "tech": {
    "languages": ["python", "typescript", ...],
    "frameworks": ["django", "react", ...],
    "categories": ["backend", "frontend", "devops", "mobile", "data"]
  },
  "summary": {
    "title": "Brief 5-10 word title of what this PR does",
    "description": "1-2 sentence summary for a CTO. Focus on business impact.",
    "type": "feature" | "bugfix" | "refactor" | "docs" | "test" | "chore" | "ci"
  },
  "health": {
    "review_friction": "low" | "medium" | "high",
    "scope": "small" | "medium" | "large" | "xlarge",
    "risk_level": "low" | "medium" | "high",
    "insights": ["1-2 sentence observations about this PR's process"]
  }
}

## Category Definitions
- **backend**: Server-side code, APIs, databases
- **frontend**: UI, React, CSS, browser code
- **devops**: CI/CD, infrastructure, deployment
- **mobile**: iOS, Android, React Native
- **data**: Analytics, ML, data pipelines

## PR Type Definitions
- **feature**: New functionality
- **bugfix**: Fixing broken behavior
- **refactor**: Code restructuring without behavior change
- **docs**: Documentation only
- **test**: Test additions/changes
- **chore**: Dependencies, config, maintenance
- **ci**: CI/CD pipeline changes

## Tool Names (lowercase)
cursor, claude, copilot, cody, devin, gemini, chatgpt, gpt4, aider, windsurf, tabnine, cubic, mintlify, coderabbit

## Language Names (lowercase)
python, typescript, javascript, go, rust, java, ruby, php, swift, kotlin, c, cpp

## Framework Names (lowercase)
react, nextjs, vue, angular, django, fastapi, flask, express, rails, spring, laravel"""


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

    Returns:
        Formatted user prompt for LLM
    """
    sections = []

    # === Basic Info ===
    basic_info = []
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
        # Limit to 20 most relevant files
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
        9. Repository Languages - from TrackedRepository
        10. Description - PR body

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
        commits = list(pr.commits.all().order_by("-committed_at")[:10])
    except AttributeError:
        commits = []

    if commits:
        commit_lines = ["Commits:"]
        for c in commits:
            msg = c.message or ""
            # Truncate but keep Co-Authored-By lines visible
            if len(msg) > 300:
                msg = msg[:300] + "..."
            commit_lines.append(f"- {msg}")
        sections.append("\n".join(commit_lines))

    # === 7. Reviews ===
    try:
        reviews = list(pr.reviews.exclude(body__isnull=True).exclude(body="").order_by("submitted_at")[:5])
    except AttributeError:
        reviews = []

    if reviews:
        review_lines = ["Reviews:"]
        for r in reviews:
            reviewer = "unknown"
            if r.reviewer:
                reviewer = r.reviewer.github_username or r.reviewer.display_name or "unknown"
            body = r.body[:200] + "..." if len(r.body) > 200 else r.body
            state = r.state.upper() if r.state else "COMMENT"
            review_lines.append(f"- [{state}] {reviewer}: {body}")
        sections.append("\n".join(review_lines))

    # === 8. Comments (NEW - may contain AI discussion) ===
    try:
        comments = list(pr.comments.exclude(body__isnull=True).exclude(body="").order_by("comment_created_at")[:5])
    except AttributeError:
        comments = []

    if comments:
        comment_lines = ["Comments:"]
        for c in comments:
            author = "unknown"
            if c.author:
                author = c.author.github_username or c.author.display_name or "unknown"
            body = c.body[:200] + "..." if len(c.body) > 200 else c.body
            comment_lines.append(f"- {author}: {body}")
        sections.append("\n".join(comment_lines))

    # === 9. Repository Languages ===
    repo_languages = _get_repo_languages(pr)
    if repo_languages:
        sections.append(repo_languages)

    # === 10. Description ===
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
