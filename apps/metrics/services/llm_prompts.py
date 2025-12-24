"""LLM prompts for PR analysis.

This is the SOURCE OF TRUTH for all LLM prompts used in PR analysis.
Update prompts here, then copy to promptfoo experiments for testing.

Version: 6.0.0 (2024-12-24) - Enhanced with full PR context and health assessment
"""

# Current prompt version - increment when making changes
PROMPT_VERSION = "6.1.0"

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
