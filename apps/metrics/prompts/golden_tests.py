"""Golden test cases for LLM prompt evaluation.

This module defines a single source of truth for test cases that can be used by:
1. Python unit tests (parametrized pytest tests)
2. Promptfoo YAML configuration (external LLM evaluation)

Usage:
    from apps.metrics.prompts.golden_tests import GOLDEN_TESTS, GoldenTest

    # Iterate over all test cases
    for test in GOLDEN_TESTS:
        print(f"{test.id}: {test.description}")

    # Generate promptfoo assertions
    from apps.metrics.prompts.golden_tests import to_promptfoo_test
    promptfoo_test = to_promptfoo_test(GOLDEN_TESTS[0])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GoldenTestCategory(Enum):
    """Categories for organizing golden test cases.

    Named GoldenTestCategory (not TestCategory) to avoid pytest collection warnings.
    """

    POSITIVE = "positive"  # Should detect AI
    NEGATIVE = "negative"  # Should NOT detect AI
    EDGE_CASE = "edge_case"  # Ambiguous or boundary cases
    TECH_DETECTION = "tech_detection"  # Technology detection focus
    SUMMARY = "summary"  # Summary generation focus
    HEALTH = "health"  # Health assessment focus


@dataclass
class GoldenTest:
    """A single golden test case for LLM prompt evaluation.

    Attributes:
        id: Unique identifier (e.g., "pos_cursor_explicit")
        description: Human-readable description of what's being tested
        category: Test category for organization
        pr_title: PR title text
        pr_body: PR description/body text
        additions: Lines added (default 0)
        deletions: Lines deleted (default 0)
        expected_ai_assisted: Expected is_assisted value (None = don't check)
        expected_tools: Expected tools in response (empty = don't check specific tools)
        expected_not_tools: Tools that should NOT be in response
        min_confidence: Minimum confidence threshold (0.0 = don't check)
        expected_categories: Expected tech categories
        expected_pr_type: Expected PR type classification
        notes: Optional notes explaining the test case
    """

    id: str
    description: str
    category: GoldenTestCategory
    pr_title: str = ""
    pr_body: str = ""
    additions: int = 0
    deletions: int = 0

    # AI detection expectations
    expected_ai_assisted: bool | None = None
    expected_tools: list[str] = field(default_factory=list)
    expected_not_tools: list[str] = field(default_factory=list)
    min_confidence: float = 0.0

    # Tech detection expectations
    expected_categories: list[str] = field(default_factory=list)

    # Summary expectations
    expected_pr_type: str | None = None

    # Documentation
    notes: str = ""


# =============================================================================
# GOLDEN TEST CASES
# =============================================================================

GOLDEN_TESTS: list[GoldenTest] = [
    # -------------------------------------------------------------------------
    # POSITIVE CASES: Should detect AI
    # -------------------------------------------------------------------------
    GoldenTest(
        id="pos_cursor_explicit",
        description="Cursor IDE mentioned explicitly in AI Disclosure section",
        category=GoldenTestCategory.POSITIVE,
        pr_title="Add user profile feature",
        pr_body="## Summary\nAdded new feature.\n\n## AI Disclosure\nUsed Cursor IDE for implementation.",
        expected_ai_assisted=True,
        expected_tools=["cursor"],
        min_confidence=0.8,
        notes="Clear AI disclosure with specific tool mention",
    ),
    GoldenTest(
        id="pos_claude_code_signature",
        description="Claude Code emoji signature with Co-Authored-By",
        category=GoldenTestCategory.POSITIVE,
        pr_title="Fix login validation bug",
        pr_body=(
            "Fix login bug.\n\n"
            "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\n"
            "Co-Authored-By: Claude <noreply@anthropic.com>"
        ),
        expected_ai_assisted=True,
        expected_tools=["claude"],
        min_confidence=0.9,
        notes="Standard Claude Code signature pattern",
    ),
    GoldenTest(
        id="pos_copilot_mention",
        description="GitHub Copilot mentioned in description",
        category=GoldenTestCategory.POSITIVE,
        pr_title="Refactor authentication module",
        pr_body="Refactored the auth module with help from GitHub Copilot.\n\nThis change improves security.",
        expected_ai_assisted=True,
        expected_tools=["copilot"],
        min_confidence=0.7,
        notes="Casual mention of Copilot assistance",
    ),
    GoldenTest(
        id="pos_multiple_tools",
        description="Multiple AI tools mentioned",
        category=GoldenTestCategory.POSITIVE,
        pr_title="Implement new dashboard",
        pr_body=(
            "## AI Tools Used\n"
            "- Cursor for code generation\n"
            "- Claude for architecture review\n\n"
            "Built the new analytics dashboard."
        ),
        expected_ai_assisted=True,
        expected_tools=["cursor", "claude"],
        min_confidence=0.85,
        notes="Multiple tools should all be detected",
    ),
    GoldenTest(
        id="pos_aider_commit",
        description="Aider commit message pattern",
        category=GoldenTestCategory.POSITIVE,
        pr_title="Add API rate limiting",
        pr_body="Added rate limiting to API endpoints.\n\nCommit message: aider: Implement rate limiting middleware",
        expected_ai_assisted=True,
        expected_tools=["aider"],
        min_confidence=0.8,
        notes="Aider prefixes commit messages with 'aider:'",
    ),
    GoldenTest(
        id="pos_windsurf_codeium",
        description="Windsurf/Codeium IDE mentioned",
        category=GoldenTestCategory.POSITIVE,
        pr_title="Update payment flow",
        pr_body="Updated payment processing.\n\n## Development\nUsed Windsurf IDE with Codeium for autocomplete.",
        expected_ai_assisted=True,
        expected_tools=["windsurf"],
        min_confidence=0.75,
        notes="Windsurf is Codeium's IDE product",
    ),
    # -------------------------------------------------------------------------
    # NEGATIVE CASES: Should NOT detect AI
    # -------------------------------------------------------------------------
    GoldenTest(
        id="neg_explicit_no_ai",
        description="Explicit 'No AI was used' denial",
        category=GoldenTestCategory.NEGATIVE,
        pr_title="Fix API timeout",
        pr_body="## Changes\nBug fix.\n\n## AI Disclosure\nNo AI was used.",
        expected_ai_assisted=False,
        notes="Explicit denial should override any false positives",
    ),
    GoldenTest(
        id="neg_ai_as_product",
        description="AI mentioned as product feature, not authoring tool",
        category=GoldenTestCategory.NEGATIVE,
        pr_title="Add Gemini API integration",
        pr_body=(
            "Added Gemini API integration for AI-powered search.\n\nThis PR adds support for Google's Gemini model."
        ),
        expected_ai_assisted=False,
        expected_not_tools=["gemini"],
        notes="Building AI features != using AI to write code",
    ),
    GoldenTest(
        id="neg_empty_body",
        description="Empty PR body - no evidence either way",
        category=GoldenTestCategory.NEGATIVE,
        pr_title="Minor fix",
        pr_body="",
        expected_ai_assisted=False,
        notes="No evidence = assume no AI",
    ),
    GoldenTest(
        id="neg_human_only",
        description="Standard PR with no AI mentions",
        category=GoldenTestCategory.NEGATIVE,
        pr_title="Fix null pointer exception in UserService",
        pr_body=(
            "## Problem\nUsers were getting 500 errors on profile page.\n\n"
            "## Solution\nAdded null check before accessing user preferences.\n\n"
            "## Testing\nAdded unit test for the edge case."
        ),
        expected_ai_assisted=False,
        notes="Standard human-written PR format",
    ),
    GoldenTest(
        id="neg_claude_product_discussion",
        description="Discussing Claude as product, not using it",
        category=GoldenTestCategory.NEGATIVE,
        pr_title="Add Claude model selector",
        pr_body=(
            "Added dropdown to select between Claude Opus and Sonnet models.\n\n"
            "Users can now choose which Claude model to use for their queries."
        ),
        expected_ai_assisted=False,
        expected_not_tools=["claude"],
        notes="Mentioning Claude as a product != using Claude to write code",
    ),
    GoldenTest(
        id="neg_ai_none_disclosure",
        description="AI Disclosure section with 'None'",
        category=GoldenTestCategory.NEGATIVE,
        pr_title="Update dependencies",
        pr_body="## Changes\nBumped package versions.\n\n## AI Disclosure\nNone",
        expected_ai_assisted=False,
        notes="'None' in disclosure section = no AI",
    ),
    GoldenTest(
        id="neg_ai_na_disclosure",
        description="AI Disclosure section with 'N/A'",
        category=GoldenTestCategory.NEGATIVE,
        pr_title="Fix typo in README",
        pr_body="## Changes\nFixed spelling error.\n\n## AI Disclosure\nN/A",
        expected_ai_assisted=False,
        notes="'N/A' in disclosure section = no AI",
    ),
    # -------------------------------------------------------------------------
    # EDGE CASES: Ambiguous or boundary conditions
    # -------------------------------------------------------------------------
    GoldenTest(
        id="edge_brainstorm_only",
        description="AI used only for brainstorming, not coding",
        category=GoldenTestCategory.EDGE_CASE,
        pr_title="New feature architecture",
        pr_body=(
            "## Overview\nNew event system design.\n\n"
            "## AI Disclosure\n"
            "Used ChatGPT for initial brainstorming of the architecture. "
            "All code was written manually."
        ),
        expected_ai_assisted=True,  # Still counts as AI-assisted
        expected_tools=["chatgpt"],
        notes="Brainstorming counts but should be usage_type='brainstorm'",
    ),
    GoldenTest(
        id="edge_review_only",
        description="AI used only for code review",
        category=GoldenTestCategory.EDGE_CASE,
        pr_title="Optimize database queries",
        pr_body="Optimized slow queries.\n\n## AI Disclosure\nCode was reviewed by Claude for potential issues.",
        expected_ai_assisted=True,  # Review assistance still counts
        expected_tools=["claude"],
        notes="Review assistance is a form of AI-assisted development",
    ),
    GoldenTest(
        id="edge_partial_ai",
        description="Some code AI-generated, some manual",
        category=GoldenTestCategory.EDGE_CASE,
        pr_title="Add data export feature",
        pr_body=(
            "## Changes\n"
            "- Export to CSV (AI-generated with Cursor)\n"
            "- Export to PDF (manual implementation)\n\n"
            "Mixed AI and manual work."
        ),
        expected_ai_assisted=True,
        expected_tools=["cursor"],
        notes="Partial AI use still counts as AI-assisted",
    ),
    # -------------------------------------------------------------------------
    # TECHNOLOGY DETECTION CASES
    # -------------------------------------------------------------------------
    GoldenTest(
        id="tech_python_django",
        description="Python/Django backend PR",
        category=GoldenTestCategory.TECH_DETECTION,
        pr_title="Add user authentication API",
        pr_body="Added Django REST Framework endpoints for user auth.\n\nFiles: views.py, serializers.py, urls.py",
        expected_ai_assisted=False,
        expected_categories=["backend"],
        expected_pr_type="feature",
    ),
    GoldenTest(
        id="tech_react_frontend",
        description="React frontend PR",
        category=GoldenTestCategory.TECH_DETECTION,
        pr_title="Add dark mode toggle",
        pr_body=(
            "Implemented dark mode using React context and Tailwind CSS.\n\n"
            "Files: ThemeContext.tsx, App.tsx, tailwind.config.js"
        ),
        expected_ai_assisted=False,
        expected_categories=["frontend"],
        expected_pr_type="feature",
    ),
    GoldenTest(
        id="tech_devops_docker",
        description="DevOps/Docker PR",
        category=GoldenTestCategory.TECH_DETECTION,
        pr_title="Add Docker Compose for local dev",
        pr_body=(
            "Added docker-compose.yml for local development environment.\n\n"
            "Includes PostgreSQL, Redis, and the app container."
        ),
        expected_ai_assisted=False,
        expected_categories=["devops"],
        expected_pr_type="chore",
    ),
    GoldenTest(
        id="tech_fullstack",
        description="Full-stack PR touching multiple areas",
        category=GoldenTestCategory.TECH_DETECTION,
        pr_title="Add real-time notifications",
        pr_body=(
            "## Backend\n"
            "- WebSocket endpoint in Django Channels\n"
            "- Redis pub/sub\n\n"
            "## Frontend\n"
            "- React notification component\n"
            "- Toast animations with Framer Motion"
        ),
        expected_ai_assisted=False,
        expected_categories=["backend", "frontend"],
        expected_pr_type="feature",
    ),
    # -------------------------------------------------------------------------
    # SUMMARY/TYPE DETECTION CASES
    # -------------------------------------------------------------------------
    GoldenTest(
        id="type_bugfix",
        description="Clear bugfix PR",
        category=GoldenTestCategory.SUMMARY,
        pr_title="Fix: Null pointer in payment processing",
        pr_body=(
            "## Problem\nPayments failing with NullPointerException.\n\n"
            "## Root Cause\nMissing null check on optional field.\n\n"
            "## Fix\nAdded null check before accessing payment method."
        ),
        expected_ai_assisted=False,
        expected_pr_type="bugfix",
    ),
    GoldenTest(
        id="type_refactor",
        description="Code refactoring PR",
        category=GoldenTestCategory.SUMMARY,
        pr_title="Refactor: Extract UserService from monolith",
        pr_body=(
            "Extracted user-related logic into dedicated service class.\n\nNo behavior changes, just code organization."
        ),
        expected_ai_assisted=False,
        expected_pr_type="refactor",
    ),
    GoldenTest(
        id="type_docs",
        description="Documentation-only PR",
        category=GoldenTestCategory.SUMMARY,
        pr_title="Update API documentation",
        pr_body="Updated README with new API endpoints.\n\nAdded examples for authentication flow.",
        expected_ai_assisted=False,
        expected_pr_type="docs",
    ),
    GoldenTest(
        id="type_test",
        description="Test-only PR",
        category=GoldenTestCategory.SUMMARY,
        pr_title="Add unit tests for PaymentService",
        pr_body=(
            "Added comprehensive test coverage for payment processing.\n\n"
            "- 15 new test cases\n"
            "- Edge cases for refunds\n"
            "- Mock Stripe API responses"
        ),
        expected_ai_assisted=False,
        expected_pr_type="test",
    ),
    GoldenTest(
        id="type_ci",
        description="CI/CD pipeline PR",
        category=GoldenTestCategory.SUMMARY,
        pr_title="Add GitHub Actions workflow",
        pr_body=(
            "Added CI pipeline for automated testing.\n\n"
            "- Run tests on PR\n"
            "- Build Docker image\n"
            "- Deploy to staging on merge"
        ),
        expected_ai_assisted=False,
        expected_pr_type="ci",
    ),
]


def to_promptfoo_test(test: GoldenTest, schema_assertion: dict[str, Any]) -> dict[str, Any]:
    """Convert a GoldenTest to promptfoo test format.

    Args:
        test: The golden test case
        schema_assertion: The schema validation assertion to include

    Returns:
        Dictionary in promptfoo test format
    """
    assertions: list[dict[str, Any]] = [
        {"type": "is-json"},
        schema_assertion,
    ]

    # AI detection assertions
    if test.expected_ai_assisted is not None:
        value = "true" if test.expected_ai_assisted else "false"
        assertions.append(
            {
                "type": "javascript",
                "value": f"JSON.parse(output).ai.is_assisted === {value}",
            }
        )

    # Expected tools assertions
    for tool in test.expected_tools:
        assertions.append(
            {
                "type": "javascript",
                "value": f'JSON.parse(output).ai.tools.includes("{tool}")',
            }
        )

    # Not-expected tools assertions
    for tool in test.expected_not_tools:
        assertions.append(
            {
                "type": "javascript",
                "value": f'!JSON.parse(output).ai.tools.includes("{tool}")',
            }
        )

    # Confidence threshold assertion
    if test.min_confidence > 0:
        assertions.append(
            {
                "type": "javascript",
                "value": f"JSON.parse(output).ai.confidence >= {test.min_confidence}",
            }
        )

    # Category assertions
    for category in test.expected_categories:
        assertions.append(
            {
                "type": "javascript",
                "value": f'JSON.parse(output).tech.categories.includes("{category}")',
            }
        )

    # PR type assertion
    if test.expected_pr_type:
        assertions.append(
            {
                "type": "javascript",
                "value": f'JSON.parse(output).summary.type === "{test.expected_pr_type}"',
            }
        )

    return {
        "description": f"[{test.id}] {test.description}",
        "vars": {
            "pr_title": test.pr_title,
            "pr_body": test.pr_body,
            "additions": test.additions,
            "deletions": test.deletions,
        },
        "assert": assertions,
    }


def get_tests_by_category(category: GoldenTestCategory) -> list[GoldenTest]:
    """Get all tests in a specific category.

    Args:
        category: The category to filter by

    Returns:
        List of tests in that category
    """
    return [t for t in GOLDEN_TESTS if t.category == category]


def get_positive_tests() -> list[GoldenTest]:
    """Get all positive test cases (should detect AI)."""
    return get_tests_by_category(GoldenTestCategory.POSITIVE)


def get_negative_tests() -> list[GoldenTest]:
    """Get all negative test cases (should NOT detect AI)."""
    return get_tests_by_category(GoldenTestCategory.NEGATIVE)
