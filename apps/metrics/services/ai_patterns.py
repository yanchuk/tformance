"""
AI Detection Patterns Registry

This file defines all patterns used to detect AI involvement in PRs, reviews, and commits.
Patterns are easily extensible - just add new entries to the appropriate dictionary or list.

To add a new AI reviewer bot:
    AI_REVIEWER_BOTS["bot-username"] = "tool_name"

To add a new text signature pattern:
    AI_SIGNATURE_PATTERNS.append((r"pattern regex", "tool_name"))

To add a new co-author pattern:
    AI_CO_AUTHOR_PATTERNS.append((r"pattern regex", "tool_name"))

All patterns are case-insensitive.

VERSIONING:
When adding new patterns, increment PATTERNS_VERSION to trigger reprocessing
of historical data. The version is stored with each detection to allow
selective reprocessing.
"""

# =============================================================================
# Pattern Version - Increment when adding/changing patterns
# =============================================================================
# This version is stored with AI detections to support selective reprocessing.
# Increment major version for breaking changes, minor for additions.
PATTERNS_VERSION = "1.5.0"

# =============================================================================
# AI Reviewer Bots (username-based detection)
# =============================================================================
# Maps lowercase usernames to AI tool type identifier
# Add new bot usernames here as they become common
AI_REVIEWER_BOTS: dict[str, str] = {
    # ----- CodeRabbit - AI code reviewer -----
    "coderabbitai": "coderabbit",
    "coderabbit[bot]": "coderabbit",
    # ----- GitHub Copilot -----
    "github-copilot[bot]": "copilot",
    "copilot[bot]": "copilot",
    # ----- Dependabot - dependency updates -----
    "dependabot[bot]": "dependabot",
    "dependabot-preview[bot]": "dependabot",
    # ----- Renovate - dependency updates -----
    "renovate[bot]": "renovate",
    "renovate-bot": "renovate",
    # ----- Snyk - security scanning -----
    "snyk-bot": "snyk",
    "snyk[bot]": "snyk",
    # ----- SonarCloud/SonarQube - code quality -----
    "sonarcloud[bot]": "sonarcloud",
    "sonarqube[bot]": "sonarcloud",
    # ----- Codecov - code coverage -----
    "codecov[bot]": "codecov",
    "codecov-io": "codecov",
    # ----- Linear - issue tracking bot -----
    "linear[bot]": "linear",
    # ----- Vercel - deployment bot -----
    "vercel[bot]": "vercel",
    # ----- GitHub Apps/Actions -----
    "github-actions[bot]": "github_actions",
    # ----- Devin AI - autonomous coding agent -----
    "devin-ai-integration[bot]": "devin",
    "devin[bot]": "devin",
    "devin-ai[bot]": "devin",
    # ----- Autofix CI -----
    "autofix-ci[bot]": "autofix",
}

# =============================================================================
# AI Signature Patterns (regex detection in PR body/title)
# =============================================================================
# List of (regex_pattern, ai_tool_type) tuples
# Patterns are matched case-insensitively
AI_SIGNATURE_PATTERNS: list[tuple[str, str]] = [
    # ----- Claude Code (Anthropic CLI) -----
    (r"generated\s+with\s+\[?claude\s*code\]?", "claude_code"),
    (r"🤖\s*generated\s+with\s+.*claude", "claude_code"),
    (r"claude\.com/claude-code", "claude_code"),
    # Hyphenated "claude-code" variation
    (r"\bclaude-code\b", "claude_code"),
    # "claude code" without hyphen
    (r"\bclaude\s+code\b", "claude_code"),
    # ----- Claude Model Names (Opus, Sonnet, Haiku) -----
    # "Claude Sonnet", "Claude Opus", "Claude Haiku"
    (r"\bclaude\s+(?:opus|sonnet|haiku)\b", "claude"),
    # "Claude 4.5 Sonnet", "Claude 4 Opus" with version numbers
    (r"\bclaude\s*\(?\s*\d+(?:\.\d+)?\s*\)?\s*(?:opus|sonnet|haiku)", "claude"),
    (r"\bclaude\s+\d+(?:\.\d+)?\s+(?:opus|sonnet|haiku)", "claude"),
    # "Claude(Sonnet 4.5)" parenthesis format
    (r"\bclaude\s*\(\s*(?:opus|sonnet|haiku)", "claude"),
    # "Sonnet 4.5", "Opus 4" with version (requires digit to avoid poetry false positive)
    (r"\b(?:sonnet|opus)\s+\d+(?:\.\d+)?", "claude"),
    # "with Claude", "and Claude" in context of AI assistance
    (r"\b(?:with|and)\s+claude\b", "claude"),
    # "Claude 4", "claude-4", "Claude-4.5" with version number (without model name)
    (r"\bclaude[- ]?\d+(?:\.\d+)?\b", "claude"),
    # ----- GitHub Copilot -----
    (r"generated\s+by\s+.*copilot", "copilot"),
    (r"github\s+copilot", "copilot"),
    (r"copilot\s+generated", "copilot"),
    # "Copilot used to...", "Copilot used for..."
    (r"\bcopilot\s+used\b", "copilot"),
    # ----- Cursor AI -----
    (r"generated\s+by\s+cursor", "cursor"),
    (r"cursor\s+ai", "cursor"),
    (r"cursor\.sh", "cursor"),
    # Cursor with parenthesis - "Cursor (Claude 4.5)", "Cursor(auto-mode)"
    (r"\bcursor\s*\(", "cursor"),
    # Cursor IDE explicit mention
    (r"\bcursor\s+ide\b", "cursor"),
    # Cursor auto mode variations
    (r"\bcursor\s+auto[- ]?mode", "cursor"),
    # "used Cursor", "using Cursor", "with Cursor" for something
    (r"\bused\s+cursor\b", "cursor"),
    (r"\busing\s+cursor\b", "cursor"),
    (r"\bwith\s+cursor\b", "cursor"),
    # "cursor in auto mode" - matches "cursor in" followed by mode context
    (r"\bcursor\s+in\s+auto", "cursor"),
    # "Cursor used for", "Cursor was used"
    (r"\bcursor\s+(?:was\s+)?used\s+(?:for|to)", "cursor"),
    # Structured format: "IDE: Cursor"
    (r"\bide:\s*cursor\b", "cursor"),
    # "cursor for understanding", "cursor for ..."
    (r"\bcursor\s+for\b", "cursor"),
    # "cursor autocompletions", "cursor autocomplete"
    (r"\bcursor\s+autocompletions?\b", "cursor"),
    # "written by Cursor"
    (r"\bwritten\s+by\s+cursor\b", "cursor"),
    # ----- Cody (Sourcegraph) -----
    (r"generated\s+by\s+cody", "cody"),
    (r"sourcegraph\s+cody", "cody"),
    # ----- Windsurf -----
    (r"generated\s+by\s+windsurf", "windsurf"),
    (r"windsurf\s+ai", "windsurf"),
    # ----- Tabnine -----
    (r"generated\s+by\s+tabnine", "tabnine"),
    (r"tabnine\s+ai", "tabnine"),
    # ----- Amazon CodeWhisperer / Amazon Q -----
    (r"codewhisperer", "codewhisperer"),
    (r"amazon\s+q", "amazon_q"),
    # ----- Google Gemini -----
    # Specific patterns to avoid false positives on "Gemini API", "Gemini SDK"
    (r"\bused\s+gemini\b", "gemini"),
    (r"\bgemini\s+used\b", "gemini"),
    (r"\bgemini\s+(?:helped|assisted)\b", "gemini"),
    (r"\bwith\s+gemini\b", "gemini"),
    (r"\busing\s+gemini\b", "gemini"),
    # ----- ChatGPT / OpenAI GPT -----
    (r"\bchatgpt\b", "chatgpt"),
    (r"\bgpt-?4o?\b", "chatgpt"),
    (r"\bgpt-?5\b", "chatgpt"),
    (r"\bused\s+openai\b", "chatgpt"),
    (r"\busing\s+openai\b", "chatgpt"),
    (r"\bwith\s+openai\b", "chatgpt"),
    # ----- Warp Terminal AI -----
    (r"\bwarp\s+ai\b", "warp"),
    (r"\bwarp\b.*\bai\b", "warp"),
    (r"\bwarp\s+terminal\b.*\bai\b", "warp"),
    # ----- Aider -----
    (r"generated\s+by\s+aider", "aider"),
    (r"aider\.chat", "aider"),
    # ----- Devin AI -----
    (r"generated\s+by\s+devin", "devin"),
    (r"created\s+by\s+devin", "devin"),
    (r"devin\.ai", "devin"),
    (r"devin\s+ai", "devin"),
    # ----- Generic AI indicators -----
    (r"ai[- ]?generated", "ai_generic"),
    (r"ai[- ]?assisted", "ai_generic"),
    (r"llm[- ]?generated", "ai_generic"),
    (r"written\s+by\s+ai", "ai_generic"),
    # ----- Indirect AI Usage Patterns -----
    # "AI was used to...", "AI was used for..." - require continuation to avoid "No AI was used"
    (r"\bai\s+was\s+used\s+(?:to|for)\b", "ai_generic"),
    # "used AI for...", "used AI to..."
    (r"\bused\s+ai\s+(?:for|to)\b", "ai_generic"),
    # "with AI assistance"
    (r"\bwith\s+ai\s+assistance\b", "ai_generic"),
    # "AI helped with...", "AI helped to..."
    (r"\bai\s+helped?\s+(?:with|to)\b", "ai_generic"),
]

# =============================================================================
# AI Co-Author Patterns (commit message detection)
# =============================================================================
# Regex patterns to detect AI co-authors in commit messages
# Format: Co-Authored-By: Name <email>
AI_CO_AUTHOR_PATTERNS: list[tuple[str, str]] = [
    # ----- Claude (Anthropic) -----
    (r"co-authored-by:\s*claude(?:\s+(?:opus|sonnet|haiku))?(?:\s+[\d.]+)?\s*<[^>]+>", "claude"),
    (r"co-authored-by:[^<]*<noreply@anthropic\.com>", "claude"),
    (r"co-authored-by:[^<]*<.*@anthropic\.com>", "claude"),
    # ----- GitHub Copilot -----
    (r"co-authored-by:\s*github\s*copilot\s*<[^>]+>", "copilot"),
    (r"co-authored-by:[^<]*<copilot@github\.com>", "copilot"),
    (r"co-authored-by:\s*copilot\s*<[^>]+>", "copilot"),
    # ----- Cursor -----
    (r"co-authored-by:\s*cursor\s*<[^>]+>", "cursor"),
    (r"co-authored-by:[^<]*<[^>]*@cursor\.sh>", "cursor"),
    (r"co-authored-by:[^<]*<[^>]*@cursor\.ai>", "cursor"),
    # ----- Cody (Sourcegraph) -----
    (r"co-authored-by:\s*cody\s*<[^>]+>", "cody"),
    (r"co-authored-by:[^<]*<[^>]*@sourcegraph\.com>", "cody"),
    # ----- Windsurf -----
    (r"co-authored-by:\s*windsurf\s*<[^>]+>", "windsurf"),
    # ----- Aider -----
    (r"co-authored-by:\s*aider\s*<[^>]+>", "aider"),
    (r"co-authored-by:[^<]*<aider@", "aider"),
    # ----- Devin AI -----
    (r"co-authored-by:\s*devin\s*<[^>]+>", "devin"),
    (r"co-authored-by:[^<]*<[^>]*@devin\.ai>", "devin"),
    # ----- Autofix CI bot -----
    (r"co-authored-by:\s*autofix-ci\[bot\]\s*<[^>]+>", "autofix"),
]


# =============================================================================
# Friendly Display Names for AI Tools
# =============================================================================
# Maps AI tool type identifiers to human-friendly display names
AI_TOOL_DISPLAY_NAMES: dict[str, str] = {
    "devin": "Devin AI",
    "coderabbit": "CodeRabbit",
    "copilot": "Copilot",
    "dependabot": "Dependabot",
    "renovate": "Renovate",
    "snyk": "Snyk",
    "sonarcloud": "SonarCloud",
    "codecov": "Codecov",
    "linear": "Linear",
    "vercel": "Vercel",
    "github_actions": "GitHub Actions",
    "autofix": "Autofix CI",
    "claude": "Claude",
    "claude_code": "Claude Code",
    "cursor": "Cursor",
    "cody": "Cody",
    "windsurf": "Windsurf",
    "tabnine": "Tabnine",
    "codewhisperer": "CodeWhisperer",
    "amazon_q": "Amazon Q",
    "gemini": "Gemini",
    "chatgpt": "ChatGPT",
    "warp": "Warp AI",
    "aider": "Aider",
    "ai_generic": "AI",
}


# =============================================================================
# Helper: Get all known AI tool types
# =============================================================================
def get_all_ai_tools() -> set[str]:
    """Return a set of all known AI tool type identifiers."""
    tools = set(AI_REVIEWER_BOTS.values())
    tools.update(tool for _, tool in AI_SIGNATURE_PATTERNS)
    tools.update(tool for _, tool in AI_CO_AUTHOR_PATTERNS)
    return tools


def get_ai_tool_display_name(tool_type: str) -> str:
    """Get the friendly display name for an AI tool type.

    Args:
        tool_type: The AI tool type identifier (e.g., 'devin', 'copilot')

    Returns:
        Human-friendly display name (e.g., 'Devin AI', 'Copilot')
    """
    return AI_TOOL_DISPLAY_NAMES.get(tool_type, tool_type.replace("_", " ").title())
