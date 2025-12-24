"""LLM prompts for PR analysis.

This is the SOURCE OF TRUTH for all LLM prompts used in PR analysis.
Update prompts here, then copy to promptfoo experiments for testing.

Version: 5.0.0 (2024-12-24)
"""

# Current prompt version - increment when making changes
PROMPT_VERSION = "5.0.0"

# Main PR analysis prompt
PR_ANALYSIS_SYSTEM_PROMPT = """You analyze pull requests to provide a comprehensive summary for engineering leaders.
You MUST respond with valid JSON only.

## Your Task

Analyze the PR description and extract:
1. **AI Usage** - Was AI used to write this code?
2. **Technologies** - What languages/frameworks are involved?
3. **Summary** - A 1-2 sentence executive summary for CTOs

## AI Detection Rules

**POSITIVE signals** (AI was used):
- Tool mentions: Cursor, Claude, Copilot, Cody, Aider, Devin, Gemini, Windsurf, Tabnine
- AI Disclosure sections with usage statements
- Commit signatures: Co-Authored-By with AI emails (@anthropic.com, @cursor.sh)
- Explicit markers: "Generated with Claude Code", "AI-generated"

**NEGATIVE signals** (AI was NOT used):
- Explicit denials: "No AI was used", "None", "N/A"
- AI as product feature (building AI != using AI to code)
- Bot authors: dependabot, renovate (tracked separately)

## Technology Detection

Identify technologies from:
- File extensions mentioned (.py, .ts, .tsx, .go, etc.)
- Framework/library names (React, Django, FastAPI, Next.js, etc.)
- Infrastructure (Docker, Kubernetes, Terraform, etc.)
- Database mentions (PostgreSQL, Redis, MongoDB, etc.)

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
    "description": "1-2 sentence summary for a CTO. Focus on business impact or technical scope.",
    "type": "feature" | "bugfix" | "refactor" | "docs" | "test" | "chore" | "ci"
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

## Tool Names (use lowercase)
cursor, claude, copilot, cody, devin, gemini, chatgpt, gpt4, aider, windsurf, tabnine

## Language Names (use lowercase)
python, typescript, javascript, go, rust, java, ruby, php, swift, kotlin, c, cpp

## Framework Names (use lowercase)
react, nextjs, vue, angular, django, fastapi, flask, express, rails, spring, laravel"""


def get_user_prompt(
    pr_body: str,
    pr_title: str = "",
    file_count: int = 0,
    additions: int = 0,
    deletions: int = 0,
    comment_count: int = 0,
    repo_languages: list[str] | None = None,
) -> str:
    """Generate user prompt with PR context.

    Args:
        pr_body: The PR description text
        pr_title: The PR title
        file_count: Number of files changed
        additions: Lines added
        deletions: Lines deleted
        comment_count: Number of comments
        repo_languages: Top languages from repository (e.g., ["Python", "TypeScript"])

    Returns:
        Formatted user prompt for LLM
    """
    context_parts = []

    if pr_title:
        context_parts.append(f"Title: {pr_title}")

    if file_count > 0:
        context_parts.append(f"Files changed: {file_count}")

    if additions > 0 or deletions > 0:
        context_parts.append(f"Lines: +{additions}/-{deletions}")

    if comment_count > 0:
        context_parts.append(f"Comments: {comment_count}")

    if repo_languages:
        context_parts.append(f"Repository languages: {', '.join(repo_languages)}")

    context = "\n".join(context_parts)

    return f"""Analyze this pull request:

{context}

Description:
{pr_body}"""
