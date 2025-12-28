"""AI Tool Category Classification Service.

Categorizes AI tools into:
- CODE: Tools that write/generate code (Cursor, Copilot, Claude, etc.)
- REVIEW: Tools that review/comment on code (CodeRabbit, Cubic, etc.)
- MIXED: Tools that can do both (default to CODE for analytics)
- EXCLUDED: Not AI coding assistance (security scanners, doc tools)

Usage:
    from apps.metrics.services.ai_categories import (
        get_tool_category,
        categorize_tools,
        get_ai_category,
    )

    # Get category for a single tool
    category = get_tool_category("cursor")  # Returns "code"

    # Split tool list into categories
    result = categorize_tools(["cursor", "coderabbit"])
    # Returns {"code": ["cursor"], "review": ["coderabbit"]}

    # Get dominant category for a PR
    category = get_ai_category(["cursor", "copilot"])  # Returns "code"
"""

from __future__ import annotations

# Category constants
CATEGORY_CODE = "code"
CATEGORY_REVIEW = "review"
CATEGORY_BOTH = "both"

# =============================================================================
# TOOL CATEGORY DEFINITIONS
# =============================================================================

# Tools that WRITE/GENERATE code
CODE_TOOLS: set[str] = {
    # Market leaders
    "cursor",
    "copilot",
    "github copilot",
    "claude",
    "claude_code",
    "claude-code",
    # AI Agents
    "devin",
    # Chat-based
    "chatgpt",
    "gpt4",
    "gpt-4",
    "gpt-5",
    "gpt5",
    "gemini",
    "gemini-code-assist",
    # IDEs & Editors
    "windsurf",
    "codeium",
    "jetbrains_ai",
    "jetbrains ai",
    # Terminal/CLI
    "aider",
    "continue",
    # Code completion
    "cody",
    "tabnine",
    "supermaven",
    "amazon_q",
    "amazon q",
    "codewhisperer",
    "codex",
    # Open source agents
    "goose",
    "openhands",
    # Generic AI indicators (likely code assistance)
    "ai_generic",
    "ai assistant",
    "codegen",
}

# Tools that REVIEW/ANALYZE code (no code changes)
REVIEW_TOOLS: set[str] = {
    "coderabbit",
    "code rabbit",
    "cubic",
    "greptile",
    "sourcery",
    "codacy",
    "sonarqube",
    "deepcode",
    "kodus",
    "graphite",
    "codeant",
}

# Tools that can do BOTH - default to CODE for analytics
# Rationale: If a tool CAN write code, the impact is higher
MIXED_TOOLS: set[str] = {
    "ellipsis",  # Reviews but can commit fixes via side-PRs
    "bito",  # Review agent + IDE code generation
    "qodo",  # Review + test generation + coding
    "codium",  # Same as qodo (old name)
    "augment",  # Code completion + review
}

# EXCLUDE from AI tracking entirely
# These are not AI coding assistance tools
EXCLUDED_TOOLS: set[str] = {
    "snyk",  # Security scanning
    "mintlify",  # Documentation generation only
    "lingohub",  # Localization/translation
    "dependabot",  # Dependency update bot
    "renovate",  # Dependency update bot
    "unknown",  # Unknown/unidentified
    "ai",  # Too generic, likely noise
    # LLM hallucinations - detected in PRs with no AI content (0.01% rate)
    "playwright",  # Testing framework, not AI tool
    "rolldown-vite",  # Build tool, not AI tool
}

# =============================================================================
# DISPLAY NAMES
# =============================================================================

AI_CATEGORY_DISPLAY_NAMES: dict[str, str] = {
    CATEGORY_CODE: "Code AI",
    CATEGORY_REVIEW: "Review AI",
    CATEGORY_BOTH: "Code + Review AI",
}

AI_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    CATEGORY_CODE: "AI tools that help write or generate code",
    CATEGORY_REVIEW: "AI tools that review and comment on code",
    CATEGORY_BOTH: "AI tools for both code writing and review",
}

# Badge classes for UI styling (DaisyUI)
AI_CATEGORY_BADGE_CLASSES: dict[str, str] = {
    CATEGORY_CODE: "badge-primary",
    CATEGORY_REVIEW: "badge-secondary",
    CATEGORY_BOTH: "badge-accent",
}


# =============================================================================
# FUNCTIONS
# =============================================================================


def normalize_tool_name(tool: str) -> str:
    """Normalize tool name for consistent matching.

    Args:
        tool: Tool name to normalize

    Returns:
        Lowercase, stripped tool name
    """
    if not tool:
        return ""
    return tool.lower().strip()


def get_tool_category(tool: str) -> str | None:
    """Get the category for a single AI tool.

    Args:
        tool: Tool name (e.g., "cursor", "coderabbit")

    Returns:
        "code" | "review" | None (for excluded/unknown tools)

    Examples:
        >>> get_tool_category("cursor")
        "code"
        >>> get_tool_category("coderabbit")
        "review"
        >>> get_tool_category("snyk")
        None
    """
    normalized = normalize_tool_name(tool)
    if not normalized:
        return None

    # Check excluded first
    if normalized in EXCLUDED_TOOLS:
        return None

    # Check code tools (includes mixed tools)
    if normalized in CODE_TOOLS or normalized in MIXED_TOOLS:
        return CATEGORY_CODE

    # Check review tools
    if normalized in REVIEW_TOOLS:
        return CATEGORY_REVIEW

    # Unknown tool - default to code if it looks like an AI tool
    # This catches new tools we haven't categorized yet
    return CATEGORY_CODE


def categorize_tools(tools: list[str] | None) -> dict[str, list[str]]:
    """Split a list of tools into code and review categories.

    Args:
        tools: List of tool names

    Returns:
        Dictionary with "code" and "review" lists

    Examples:
        >>> categorize_tools(["cursor", "coderabbit", "copilot"])
        {"code": ["cursor", "copilot"], "review": ["coderabbit"]}
    """
    result: dict[str, list[str]] = {
        CATEGORY_CODE: [],
        CATEGORY_REVIEW: [],
    }

    if not tools:
        return result

    for tool in tools:
        normalized = normalize_tool_name(tool)
        if not normalized:
            continue

        # Skip excluded tools
        if normalized in EXCLUDED_TOOLS:
            continue

        # Categorize
        if normalized in CODE_TOOLS or normalized in MIXED_TOOLS:
            result[CATEGORY_CODE].append(tool)
        elif normalized in REVIEW_TOOLS:
            result[CATEGORY_REVIEW].append(tool)
        else:
            # Unknown tools default to code
            result[CATEGORY_CODE].append(tool)

    return result


def get_ai_category(tools: list[str] | None) -> str | None:
    """Determine the dominant AI category for a list of tools.

    Args:
        tools: List of tool names detected in a PR

    Returns:
        "code" | "review" | "both" | None

    Logic:
        - If has code tools only → "code"
        - If has review tools only → "review"
        - If has both → "both"
        - If empty or all excluded → None

    Examples:
        >>> get_ai_category(["cursor", "copilot"])
        "code"
        >>> get_ai_category(["coderabbit"])
        "review"
        >>> get_ai_category(["cursor", "coderabbit"])
        "both"
        >>> get_ai_category([])
        None
    """
    if not tools:
        return None

    categorized = categorize_tools(tools)
    has_code = bool(categorized[CATEGORY_CODE])
    has_review = bool(categorized[CATEGORY_REVIEW])

    if has_code and has_review:
        return CATEGORY_BOTH
    if has_code:
        return CATEGORY_CODE
    if has_review:
        return CATEGORY_REVIEW

    return None


def get_category_display_name(category: str | None) -> str:
    """Get the display name for a category.

    Args:
        category: Category constant ("code", "review", "both")

    Returns:
        Human-readable name (e.g., "Code AI")
    """
    if not category:
        return ""
    return AI_CATEGORY_DISPLAY_NAMES.get(category, category.title())


def get_category_badge_class(category: str | None) -> str:
    """Get the CSS badge class for a category.

    Args:
        category: Category constant

    Returns:
        DaisyUI badge class (e.g., "badge-primary")
    """
    if not category:
        return "badge-ghost"
    return AI_CATEGORY_BADGE_CLASSES.get(category, "badge-ghost")


def is_excluded_tool(tool: str) -> bool:
    """Check if a tool should be excluded from AI tracking.

    Args:
        tool: Tool name

    Returns:
        True if tool should be excluded
    """
    return normalize_tool_name(tool) in EXCLUDED_TOOLS


def get_all_known_tools() -> dict[str, set[str]]:
    """Get all known tools organized by category.

    Returns:
        Dictionary with all tool sets
    """
    return {
        "code": CODE_TOOLS.copy(),
        "review": REVIEW_TOOLS.copy(),
        "mixed": MIXED_TOOLS.copy(),
        "excluded": EXCLUDED_TOOLS.copy(),
    }
