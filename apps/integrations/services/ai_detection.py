"""AI co-author detection service.

Centralized patterns for detecting AI coding tool signatures in commit messages.
Add new AI tools to AI_TOOL_PATTERNS to extend detection capabilities.
"""

import re

# Centralized list of AI coding tools and their detection patterns.
# Each tool has a name and list of regex patterns to match in commit messages.
# Patterns are case-insensitive.
#
# To add a new AI tool:
# 1. Add a new dict with "name" and "patterns" keys
# 2. Patterns should match common signatures in commit messages
# 3. Run tests to verify detection works
AI_TOOL_PATTERNS = [
    {
        "name": "GitHub Copilot",
        "patterns": [
            r"co-authored-by:\s*github\s*copilot",
            r"co-authored-by:.*copilot@github\.com",
            r"generated\s+by\s+github\s+copilot",
        ],
    },
    {
        "name": "Claude Code",
        "patterns": [
            r"co-authored-by:\s*claude",
            r"co-authored-by:.*@anthropic\.com",
            r"generated\s+with\s+\[?claude\s*code\]?",
            r"🤖\s*generated\s+with.*claude",
        ],
    },
    {
        "name": "Cursor",
        "patterns": [
            r"co-authored-by:\s*cursor",
            r"co-authored-by:.*@cursor\.com",
            r"generated\s+by\s+cursor",
            r"cursor\s+ai",
        ],
    },
    {
        "name": "Devin",
        "patterns": [
            r"co-authored-by:\s*devin",
            r"co-authored-by:.*@cognition-labs\.com",
            r"co-authored-by:.*@cognition\.ai",
            r"generated\s+by\s+devin",
        ],
    },
    {
        "name": "Amazon CodeWhisperer",
        "patterns": [
            r"co-authored-by:\s*amazon\s*codewhisperer",
            r"co-authored-by:\s*codewhisperer",
            r"generated\s+by\s+amazon\s*codewhisperer",
            r"amazon\s+codewhisperer",
        ],
    },
    {
        "name": "Codeium",
        "patterns": [
            r"co-authored-by:\s*codeium",
            r"co-authored-by:.*@codeium\.com",
            r"generated\s+by\s+codeium",
            r"generated\s+with\s+windsurf",
            r"windsurf",
        ],
    },
    {
        "name": "Tabnine",
        "patterns": [
            r"co-authored-by:\s*tabnine",
            r"co-authored-by:.*@tabnine\.com",
            r"generated\s+by\s+tabnine",
        ],
    },
    {
        "name": "Sourcegraph Cody",
        "patterns": [
            r"co-authored-by:\s*cody",
            r"co-authored-by:.*@sourcegraph\.com",
            r"generated\s+by\s+cody",
            r"sourcegraph\s+cody",
        ],
    },
    {
        "name": "Aider",
        "patterns": [
            r"^aider:",
            r"aider:\s+",
            r"co-authored-by:\s*aider",
            r"generated\s+by\s+aider",
        ],
    },
    {
        "name": "Gemini Code Assist",
        "patterns": [
            r"co-authored-by:\s*gemini",
            r"co-authored-by:.*@google\.com.*gemini",
            r"generated\s+by\s+gemini\s+code\s+assist",
            r"gemini\s+code\s+assist",
        ],
    },
    {
        "name": "Replit AI",
        "patterns": [
            r"co-authored-by:\s*replit",
            r"co-authored-by:.*@replit\.com",
            r"generated\s+by\s+replit\s+ai",
            r"replit\s+ghostwriter",
        ],
    },
    {
        "name": "JetBrains AI",
        "patterns": [
            r"co-authored-by:\s*jetbrains\s+ai",
            r"co-authored-by:.*@jetbrains\.com",
            r"generated\s+by\s+jetbrains\s+ai",
        ],
    },
]


def _get_message(commit: dict) -> str:
    """Safely extract message from commit dict."""
    if not commit:
        return ""
    message = commit.get("message")
    return message if message else ""


def _check_patterns(message: str, patterns: list[str]) -> bool:
    """Check if any pattern matches the message."""
    return any(re.search(pattern, message, re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def detect_ai_coauthor(commits: list[dict] | None) -> bool:
    """Detect if any commit has an AI co-author signature.

    Args:
        commits: List of commit dicts with 'message' key

    Returns:
        True if any AI co-author signature detected, False otherwise
    """
    if not commits:
        return False

    for commit in commits:
        message = _get_message(commit)
        if not message:
            continue

        for tool in AI_TOOL_PATTERNS:
            if _check_patterns(message, tool["patterns"]):
                return True

    return False


def get_detected_ai_tool(commits: list[dict] | None) -> str | None:
    """Get the first detected AI tool name from commits.

    Args:
        commits: List of commit dicts with 'message' key

    Returns:
        Name of first detected AI tool, or None if none found
    """
    if not commits:
        return None

    for commit in commits:
        message = _get_message(commit)
        if not message:
            continue

        for tool in AI_TOOL_PATTERNS:
            if _check_patterns(message, tool["patterns"]):
                return tool["name"]

    return None


def get_all_detected_ai_tools(commits: list[dict] | None) -> list[str]:
    """Get all detected AI tools from commits (no duplicates).

    Args:
        commits: List of commit dicts with 'message' key

    Returns:
        List of unique AI tool names detected
    """
    if not commits:
        return []

    detected = set()
    for commit in commits:
        message = _get_message(commit)
        if not message:
            continue

        for tool in AI_TOOL_PATTERNS:
            if _check_patterns(message, tool["patterns"]):
                detected.add(tool["name"])

    return list(detected)
