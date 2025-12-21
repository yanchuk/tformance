"""
AI Detector Service

Provides functions to detect AI involvement in PRs, reviews, and commits:
- detect_ai_reviewer(username) - Identify AI reviewer bots by username
- detect_ai_in_text(text) - Find AI tool signatures in PR/commit text
- parse_co_authors(message) - Extract AI co-authors from commit messages

All detection is case-insensitive.

Patterns are defined in ai_patterns.py for easy extension. When patterns are
updated, increment PATTERNS_VERSION in that file to enable reprocessing.
"""

import re
from typing import TypedDict

from .ai_patterns import (
    AI_CO_AUTHOR_PATTERNS,
    AI_REVIEWER_BOTS,
    AI_SIGNATURE_PATTERNS,
    PATTERNS_VERSION,
)

# =============================================================================
# Compile Patterns for Efficiency
# =============================================================================
_COMPILED_SIGNATURE_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), ai_type) for pattern, ai_type in AI_SIGNATURE_PATTERNS
]

_COMPILED_CO_AUTHOR_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), ai_type) for pattern, ai_type in AI_CO_AUTHOR_PATTERNS
]


# =============================================================================
# Type Definitions
# =============================================================================
class AIReviewerResult(TypedDict):
    """Result of AI reviewer detection."""

    is_ai: bool
    ai_type: str


class AITextResult(TypedDict):
    """Result of AI text signature detection."""

    is_ai_assisted: bool
    ai_tools: list[str]


class CoAuthorResult(TypedDict):
    """Result of AI co-author parsing."""

    has_ai_co_authors: bool
    ai_co_authors: list[str]


# =============================================================================
# Public Functions
# =============================================================================
def get_patterns_version() -> str:
    """Get the current patterns version for tracking reprocessing needs."""
    return PATTERNS_VERSION


def detect_ai_reviewer(username: str | None) -> AIReviewerResult:
    """
    Detect if a reviewer username is an AI bot.

    Args:
        username: GitHub username to check

    Returns:
        AIReviewerResult with is_ai and ai_type fields

    Examples:
        >>> detect_ai_reviewer("coderabbitai")
        {'is_ai': True, 'ai_type': 'coderabbit'}
        >>> detect_ai_reviewer("john-doe")
        {'is_ai': False, 'ai_type': ''}
    """
    if not username:
        return {"is_ai": False, "ai_type": ""}

    # Normalize username to lowercase for comparison
    username_lower = username.lower()

    # Check exact match in known bots
    if username_lower in AI_REVIEWER_BOTS:
        return {"is_ai": True, "ai_type": AI_REVIEWER_BOTS[username_lower]}

    return {"is_ai": False, "ai_type": ""}


def detect_ai_in_text(text: str | None) -> AITextResult:
    """
    Detect AI tool signatures in text (PR body, title, etc.).

    Args:
        text: Text content to analyze

    Returns:
        AITextResult with is_ai_assisted and ai_tools list

    Examples:
        >>> detect_ai_in_text("Generated with Claude Code")
        {'is_ai_assisted': True, 'ai_tools': ['claude_code']}
        >>> detect_ai_in_text("Fixed a bug")
        {'is_ai_assisted': False, 'ai_tools': []}
    """
    if not text:
        return {"is_ai_assisted": False, "ai_tools": []}

    detected_tools: list[str] = []

    for pattern, ai_type in _COMPILED_SIGNATURE_PATTERNS:
        if pattern.search(text) and ai_type not in detected_tools:
            detected_tools.append(ai_type)

    return {
        "is_ai_assisted": len(detected_tools) > 0,
        "ai_tools": detected_tools,
    }


def parse_co_authors(message: str | None) -> CoAuthorResult:
    """
    Parse AI co-authors from a commit message.

    Args:
        message: Git commit message to parse

    Returns:
        CoAuthorResult with has_ai_co_authors and ai_co_authors list

    Examples:
        >>> parse_co_authors("Fix bug\\n\\nCo-Authored-By: Claude <noreply@anthropic.com>")
        {'has_ai_co_authors': True, 'ai_co_authors': ['claude']}
        >>> parse_co_authors("Fix bug")
        {'has_ai_co_authors': False, 'ai_co_authors': []}
    """
    if not message:
        return {"has_ai_co_authors": False, "ai_co_authors": []}

    detected_co_authors: list[str] = []

    for pattern, ai_type in _COMPILED_CO_AUTHOR_PATTERNS:
        if pattern.search(message) and ai_type not in detected_co_authors:
            detected_co_authors.append(ai_type)

    return {
        "has_ai_co_authors": len(detected_co_authors) > 0,
        "ai_co_authors": detected_co_authors,
    }
