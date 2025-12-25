"""AI signal aggregation service.

Aggregates AI signals from commits, reviews, and files to the PullRequest level.
This enables multi-signal AI detection beyond just PR description text.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.metrics.models import PullRequest


# AI config file patterns - files MODIFIED in PR = strong signal of AI tool usage
# Key insight: Directory exists = tool setup (weak), File modified = active usage (strong)
AI_CONFIG_PATTERNS = {
    # Copilot
    r"\.github/copilot-instructions\.md$": "copilot",
    # Claude Code
    r"CLAUDE\.md$": "claude",
    r"^\.claude/": "claude",
    r"\.github/workflows/claude.*\.yml$": "claude",
    # Cursor IDE
    r"\.cursorrules$": "cursor",
    r"^\.cursor/rules/.*\.mdc$": "cursor",
    r"^\.cursor/environment\.json$": "cursor",
    r"^\.cursor/mcp\.json$": "cursor",
    # Aider
    r"\.aider\.conf\.yml$": "aider",
    r"^\.aider/": "aider",
    # CodeRabbit
    r"\.coderabbit\.ya?ml$": "coderabbit",
    # Greptile
    r"\.greptile\.ya?ml$": "greptile",
}

# Exclusion patterns - these file paths contain keywords but are NOT AI config
AI_FILE_EXCLUSIONS = [
    r"cursor-pagination",  # Database cursor pagination
    r"cursor_pagination",  # Database cursor pagination
    r"/ai/gemini/",  # AI product code (building AI features, not using AI)
    r"/langchain.*/gemini",  # AI SDK code
    r"contract-rules",  # Business rules
    r"consumer-rules\.pro$",  # Android ProGuard
    r"proguard-rules\.pro$",  # Android ProGuard
    r"-rules\.pro$",  # Generic Android rules
]


def aggregate_commit_ai_signals(pr: "PullRequest") -> bool:
    """Aggregate AI signals from commits to PR level.

    Returns True if ANY commit in the PR has:
    - is_ai_assisted = True, OR
    - ai_co_authors is non-empty

    This catches AI signatures like:
        Co-authored-by: Claude <noreply@anthropic.com>
        Co-authored-by: GitHub Copilot <copilot@github.com>

    Args:
        pr: PullRequest model instance

    Returns:
        bool: True if any commit has AI signals
    """
    commits = pr.commits.all()

    # Check for any commit with is_ai_assisted flag
    if commits.filter(is_ai_assisted=True).exists():
        return True

    # Check for any commit with non-empty ai_co_authors
    return any(commit.ai_co_authors for commit in commits)


def aggregate_review_ai_signals(pr: "PullRequest") -> bool:
    """Aggregate AI signals from reviews to PR level.

    Returns True if ANY review on the PR has:
    - is_ai_review = True

    This catches AI code reviewers like:
        coderabbitai[bot]
        greptile[bot]
        sourcery-ai[bot]

    Args:
        pr: PullRequest model instance

    Returns:
        bool: True if any review is from an AI reviewer
    """
    return pr.reviews.filter(is_ai_review=True).exists()


def detect_ai_config_files(pr: "PullRequest") -> dict:
    """Detect AI config files modified in a PR.

    Returns details about which AI tools were configured in this PR based on
    files that were MODIFIED (not just existing in repo).

    Key insight: Directory exists = tool is set up (weak signal)
                 File MODIFIED = tool is actively configured (strong signal)

    Args:
        pr: PullRequest model instance

    Returns:
        dict with keys:
            - has_ai_files: bool - True if any AI config files were modified
            - tools: list[str] - AI tools detected (e.g., ["cursor", "claude"])
            - files: list[str] - Specific files that matched
    """
    files = pr.files.values_list("filename", flat=True)
    detected_tools = set()
    detected_files = []

    for filename in files:
        # First check exclusions
        if _is_excluded_file(filename):
            continue

        # Then check for AI config patterns
        tool = _detect_tool_from_file(filename)
        if tool:
            detected_tools.add(tool)
            detected_files.append(filename)

    return {
        "has_ai_files": len(detected_tools) > 0,
        "tools": sorted(detected_tools),
        "files": detected_files,
    }


def _is_excluded_file(filename: str) -> bool:
    """Check if filename matches any exclusion pattern."""
    return any(re.search(pattern, filename, re.IGNORECASE) for pattern in AI_FILE_EXCLUSIONS)


def _detect_tool_from_file(filename: str) -> str | None:
    """Detect which AI tool the file belongs to, if any."""
    for pattern, tool in AI_CONFIG_PATTERNS.items():
        if re.search(pattern, filename, re.IGNORECASE):
            return tool
    return None


def aggregate_all_ai_signals(pr: "PullRequest") -> dict:
    """Aggregate all AI signals for a PR.

    Combines commit, review, and file signals into a single result.

    Args:
        pr: PullRequest model instance

    Returns:
        dict with aggregated signals:
            - has_ai_commits: bool
            - has_ai_review: bool
            - has_ai_files: bool
            - file_details: dict with tools and files detected
    """
    file_detection = detect_ai_config_files(pr)

    return {
        "has_ai_commits": aggregate_commit_ai_signals(pr),
        "has_ai_review": aggregate_review_ai_signals(pr),
        "has_ai_files": file_detection["has_ai_files"],
        "file_details": {
            "tools": file_detection["tools"],
            "files": file_detection["files"],
        },
    }


# AI confidence scoring weights
# Based on signal reliability and evidence strength
AI_SIGNAL_WEIGHTS = {
    "llm": 0.40,  # LLM detection is most accurate (context-aware)
    "commits": 0.25,  # Commit signatures are hard evidence
    "regex": 0.20,  # Regex patterns are reliable for explicit mentions
    "reviews": 0.10,  # AI review ≠ AI-authored (supplementary)
    "files": 0.05,  # File patterns are weak signal (config only)
}


def calculate_ai_confidence(pr: "PullRequest") -> tuple[float, dict]:
    """Calculate weighted AI confidence score from all detection signals.

    Combines LLM detection, regex patterns, commit signals, review signals,
    and file patterns into a single confidence score (0.0 - 1.0).

    Weights:
        - LLM Detection: 0.40 (most accurate, context-aware)
        - Commit Signals: 0.25 (hard evidence from Co-authored-by)
        - Regex Patterns: 0.20 (reliable for explicit mentions)
        - Review Signals: 0.10 (supplementary, AI review ≠ AI-authored)
        - File Patterns: 0.05 (weak signal, config files only)

    Args:
        pr: PullRequest model instance

    Returns:
        tuple of (score, signals_breakdown):
            - score: float between 0.0 and 1.0
            - signals_breakdown: dict with detailed signal info
    """
    signals = {
        "llm": _extract_llm_signal(pr),
        "regex": _extract_regex_signal(pr),
        "commits": _extract_commit_signal(pr),
        "reviews": _extract_review_signal(pr),
        "files": _extract_file_signal(pr),
    }

    # Calculate weighted score
    total_score = 0.0
    for _key, signal in signals.items():
        total_score += signal["score"]

    return total_score, signals


def _extract_llm_signal(pr: "PullRequest") -> dict:
    """Extract LLM detection signal from PR."""
    weight = AI_SIGNAL_WEIGHTS["llm"]

    if not pr.llm_summary:
        return {"score": 0.0, "is_assisted": False, "tools": [], "confidence": None}

    ai_data = pr.llm_summary.get("ai", {})
    is_assisted = ai_data.get("is_assisted", False)

    if not is_assisted:
        return {"score": 0.0, "is_assisted": False, "tools": [], "confidence": None}

    # LLM confidence affects the score proportionally
    llm_confidence = ai_data.get("confidence", 1.0)
    if llm_confidence is None:
        llm_confidence = 1.0

    score = weight * llm_confidence
    tools = ai_data.get("tools", [])

    return {
        "score": score,
        "is_assisted": True,
        "tools": tools,
        "confidence": llm_confidence,
    }


def _extract_regex_signal(pr: "PullRequest") -> dict:
    """Extract regex pattern detection signal from PR."""
    weight = AI_SIGNAL_WEIGHTS["regex"]

    is_assisted = pr.is_ai_assisted
    tools = pr.ai_tools_detected or []

    if not is_assisted:
        return {"score": 0.0, "is_assisted": False, "tools": []}

    return {
        "score": weight,
        "is_assisted": True,
        "tools": tools,
    }


def _extract_commit_signal(pr: "PullRequest") -> dict:
    """Extract commit AI signal from PR."""
    weight = AI_SIGNAL_WEIGHTS["commits"]

    has_ai = pr.has_ai_commits

    if not has_ai:
        return {"score": 0.0, "has_ai": False}

    return {
        "score": weight,
        "has_ai": True,
    }


def _extract_review_signal(pr: "PullRequest") -> dict:
    """Extract review AI signal from PR."""
    weight = AI_SIGNAL_WEIGHTS["reviews"]

    has_ai = pr.has_ai_review

    if not has_ai:
        return {"score": 0.0, "has_ai": False}

    return {
        "score": weight,
        "has_ai": True,
    }


def _extract_file_signal(pr: "PullRequest") -> dict:
    """Extract file pattern AI signal from PR."""
    weight = AI_SIGNAL_WEIGHTS["files"]

    has_ai = pr.has_ai_files

    if not has_ai:
        return {"score": 0.0, "has_ai": False}

    return {
        "score": weight,
        "has_ai": True,
    }


def update_pr_ai_confidence(pr: "PullRequest", save: bool = True) -> tuple[float, dict]:
    """Update PR's AI confidence score and signal breakdown.

    Args:
        pr: PullRequest model instance
        save: Whether to save the PR after updating (default True)

    Returns:
        tuple of (score, signals_breakdown)
    """
    from decimal import Decimal

    score, signals = calculate_ai_confidence(pr)

    pr.ai_confidence_score = Decimal(str(round(score, 3)))
    pr.ai_signals = signals

    if save:
        pr.save(update_fields=["ai_confidence_score", "ai_signals"])

    return score, signals


def update_pr_ai_signals(pr: "PullRequest", save: bool = True) -> dict:
    """Update a PR's AI signal fields based on related data.

    This is the main entry point for updating AI signals on a PR.
    Call this after syncing commits, reviews, or files.

    Args:
        pr: PullRequest model instance
        save: Whether to save the PR after updating (default True)

    Returns:
        dict with the updated signal values
    """
    signals = aggregate_all_ai_signals(pr)

    pr.has_ai_commits = signals["has_ai_commits"]
    pr.has_ai_review = signals["has_ai_review"]
    pr.has_ai_files = signals["has_ai_files"]

    if save:
        pr.save(update_fields=["has_ai_commits", "has_ai_review", "has_ai_files"])

    return signals
