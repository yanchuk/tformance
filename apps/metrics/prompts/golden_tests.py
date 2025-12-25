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

        # Full PR context (matches get_user_prompt parameters)
        file_count: Number of files changed
        comment_count: Number of comments
        repo_languages: Repository languages (e.g., ["Python", "TypeScript"])
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
        commit_messages: List of commit messages
        milestone: Milestone title
        assignees: List of assignee usernames
        linked_issues: List of linked issue references
        jira_key: Jira issue key
        author_name: PR author's display name
        reviewers: List of reviewer names
        review_comments: List of review comment bodies

        # Expectations
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

    # Full PR context (matches get_user_prompt parameters)
    file_count: int = 0
    comment_count: int = 0
    repo_languages: list[str] = field(default_factory=list)
    state: str = ""
    labels: list[str] = field(default_factory=list)
    is_draft: bool = False
    is_hotfix: bool = False
    is_revert: bool = False
    cycle_time_hours: float | None = None
    review_time_hours: float | None = None
    commits_after_first_review: int | None = None
    review_rounds: int | None = None
    file_paths: list[str] = field(default_factory=list)
    commit_messages: list[str] = field(default_factory=list)
    milestone: str | None = None
    assignees: list[str] = field(default_factory=list)
    linked_issues: list[str] = field(default_factory=list)
    jira_key: str | None = None
    author_name: str | None = None
    reviewers: list[str] = field(default_factory=list)
    review_comments: list[str] = field(default_factory=list)

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
        # Full PR context for realistic testing
        file_count=5,
        additions=180,
        deletions=12,
        repo_languages=["Python", "TypeScript"],
        state="merged",
        labels=["feature", "user-experience"],
        file_paths=["apps/users/views.py", "apps/users/models.py", "frontend/src/components/Profile.tsx"],
        cycle_time_hours=24.5,
        review_time_hours=4.0,
        author_name="Alex Developer",
        reviewers=["Sarah Reviewer"],
        commit_messages=["Add profile model", "Create profile API endpoint", "Add frontend component"],
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
        # Full PR context for realistic testing
        file_count=2,
        additions=45,
        deletions=8,
        repo_languages=["Python"],
        state="merged",
        labels=["bugfix"],
        file_paths=["apps/auth/validators.py", "apps/auth/tests/test_login.py"],
        cycle_time_hours=2.5,
        review_time_hours=1.0,
        author_name="Bob Engineer",
        reviewers=["Charlie Lead"],
        commit_messages=["Fix email validation regex", "Add test cases"],
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
        # Full PR context for realistic testing
        file_count=8,
        additions=320,
        deletions=150,
        repo_languages=["Python", "JavaScript"],
        state="merged",
        labels=["refactor", "security"],
        file_paths=["apps/auth/middleware.py", "apps/auth/decorators.py", "apps/auth/utils.py"],
        cycle_time_hours=48.0,
        review_time_hours=6.0,
        review_rounds=2,
        author_name="Diana Coder",
        reviewers=["Eve Security", "Frank Backend"],
        commit_messages=["Extract auth logic", "Add session validation", "Improve token handling"],
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
        # Full PR context for realistic testing
        file_count=15,
        additions=890,
        deletions=45,
        repo_languages=["TypeScript", "Python"],
        state="merged",
        labels=["feature", "analytics", "frontend"],
        file_paths=[
            "frontend/src/pages/Dashboard.tsx",
            "frontend/src/components/charts/LineChart.tsx",
            "apps/analytics/views.py",
        ],
        cycle_time_hours=72.0,
        review_time_hours=8.0,
        review_rounds=3,
        comment_count=12,
        author_name="Grace Fullstack",
        reviewers=["Henry Architect", "Ivy Frontend"],
        commit_messages=["Initial dashboard layout", "Add chart components", "Connect to backend API"],
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
        # Full PR context for realistic testing
        file_count=3,
        additions=120,
        deletions=5,
        repo_languages=["Python"],
        state="merged",
        labels=["feature", "api"],
        file_paths=["apps/api/middleware.py", "apps/api/throttling.py", "apps/api/tests/test_rate_limit.py"],
        cycle_time_hours=16.0,
        review_time_hours=3.0,
        author_name="Jack Backend",
        reviewers=["Kate API"],
        commit_messages=["aider: Implement rate limiting middleware", "aider: Add tests for throttling"],
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
        # Full PR context for realistic testing
        file_count=6,
        additions=240,
        deletions=80,
        repo_languages=["Python", "JavaScript"],
        state="merged",
        labels=["feature", "payments"],
        file_paths=["apps/payments/checkout.py", "apps/payments/stripe.py", "frontend/src/checkout/Form.tsx"],
        cycle_time_hours=36.0,
        review_time_hours=5.0,
        author_name="Leo Payments",
        reviewers=["Mike Finance"],
        commit_messages=["Refactor checkout flow", "Add Stripe webhook handler", "Update frontend form"],
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
        # Full PR context for realistic testing
        file_count=2,
        additions=25,
        deletions=5,
        repo_languages=["Python"],
        state="merged",
        labels=["bugfix"],
        file_paths=["apps/api/client.py", "apps/api/tests/test_timeout.py"],
        cycle_time_hours=4.0,
        review_time_hours=1.5,
        author_name="Nina Dev",
        reviewers=["Oscar Lead"],
        commit_messages=["Increase timeout to 30s", "Add retry logic"],
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
        # Full PR context for realistic testing
        file_count=7,
        additions=380,
        deletions=20,
        repo_languages=["Python", "TypeScript"],
        state="merged",
        labels=["feature", "ai-integration"],
        file_paths=["apps/ai/gemini.py", "apps/ai/prompts.py", "frontend/src/search/AISearch.tsx"],
        cycle_time_hours=56.0,
        review_time_hours=12.0,
        review_rounds=2,
        author_name="Pat AI",
        reviewers=["Quinn ML", "Rosa Backend"],
        commit_messages=["Add Gemini client", "Implement prompt engineering", "Add search UI"],
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
        # Full PR context for realistic testing
        file_count=1,
        additions=3,
        deletions=1,
        repo_languages=["Python"],
        state="merged",
        file_paths=["apps/utils/helpers.py"],
        cycle_time_hours=1.0,
        review_time_hours=0.5,
        author_name="Sam Quick",
        reviewers=["Tina Fast"],
        commit_messages=["Quick typo fix"],
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
        # Full PR context for realistic testing
        file_count=3,
        additions=45,
        deletions=8,
        repo_languages=["Java"],
        state="merged",
        labels=["bugfix", "production"],
        file_paths=["src/main/java/UserService.java", "src/test/java/UserServiceTest.java"],
        cycle_time_hours=8.0,
        review_time_hours=2.0,
        author_name="Uma Senior",
        reviewers=["Victor Staff"],
        commit_messages=["Add null check for preferences", "Add unit test"],
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
        # Full PR context for realistic testing
        file_count=4,
        additions=120,
        deletions=15,
        repo_languages=["TypeScript", "Python"],
        state="merged",
        labels=["feature", "ui"],
        file_paths=["frontend/src/components/ModelSelector.tsx", "apps/ai/models.py"],
        cycle_time_hours=24.0,
        review_time_hours=4.0,
        author_name="Wendy Product",
        reviewers=["Xavier UI"],
        commit_messages=["Add model dropdown component", "Wire up API", "Add Sonnet option"],
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
        # Full PR context for realistic testing
        file_count=2,
        additions=150,
        deletions=130,
        repo_languages=["Python"],
        state="merged",
        labels=["chore", "dependencies"],
        file_paths=["requirements.txt", "pyproject.toml"],
        cycle_time_hours=2.0,
        review_time_hours=0.5,
        author_name="Yuki Maintainer",
        reviewers=["Zack DevOps"],
        commit_messages=["Bump Django to 5.0", "Update celery"],
        expected_ai_assisted=False,
        notes="'None' in disclosure section = no AI",
    ),
    GoldenTest(
        id="neg_ai_na_disclosure",
        description="AI Disclosure section with 'N/A'",
        category=GoldenTestCategory.NEGATIVE,
        pr_title="Fix typo in README",
        pr_body="## Changes\nFixed spelling error.\n\n## AI Disclosure\nN/A",
        # Full PR context for realistic testing
        file_count=1,
        additions=2,
        deletions=2,
        repo_languages=["Markdown"],
        state="merged",
        labels=["docs"],
        file_paths=["README.md"],
        cycle_time_hours=0.5,
        review_time_hours=0.2,
        author_name="Anna Docs",
        reviewers=["Ben Editor"],
        commit_messages=["Fix typos in installation section"],
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
    # -------------------------------------------------------------------------
    # HEALTH ASSESSMENT CASES: Full PR context with timing metrics
    # -------------------------------------------------------------------------
    GoldenTest(
        id="health_slow_review",
        description="Large PR with slow review time and multiple rounds",
        category=GoldenTestCategory.HEALTH,
        pr_title="Implement user notification system",
        pr_body=(
            "## Summary\n"
            "Added real-time notifications with WebSocket support.\n\n"
            "## AI Disclosure\n"
            "Used Cursor for boilerplate code generation.\n\n"
            "## Changes\n"
            "- WebSocket server\n"
            "- React notification component\n"
            "- Database models for notification queue"
        ),
        additions=450,
        deletions=32,
        file_count=12,
        comment_count=18,
        state="merged",
        author_name="John Developer",
        labels=["feature", "backend", "frontend"],
        cycle_time_hours=96.5,
        review_time_hours=48.0,
        commits_after_first_review=5,
        review_rounds=3,
        file_paths=[
            "apps/notifications/models.py",
            "apps/notifications/consumers.py",
            "apps/notifications/routing.py",
            "frontend/src/components/NotificationBell.tsx",
            "frontend/src/hooks/useWebSocket.ts",
        ],
        commit_messages=[
            "[+0.5h] Add notification models",
            "[+4.0h] Implement WebSocket consumer",
            "[+52.0h] Fix review feedback: add rate limiting",
            "[+72.0h] Address review: improve error handling",
            "[+84.0h] 🤖 Generated with Cursor",
        ],
        repo_languages=["Python", "TypeScript", "JavaScript"],
        reviewers=["Sarah Tech Lead", "Bob Backend"],
        review_comments=[
            "[+48.0h] Sarah Tech Lead: Need rate limiting for notifications",
            "[+50.0h] Bob Backend: Consider Redis for scalability",
        ],
        expected_ai_assisted=True,
        expected_tools=["cursor"],
        expected_categories=["backend", "frontend"],
        expected_pr_type="feature",
        notes="High friction PR: slow review, large scope, multiple rework rounds",
    ),
    GoldenTest(
        id="health_fast_small",
        description="Small bugfix with fast review and minimal friction",
        category=GoldenTestCategory.HEALTH,
        pr_title="Fix null check in payment validation",
        pr_body=(
            "## Problem\n"
            "Payment validation was failing for users without saved cards.\n\n"
            "## Solution\n"
            "Added null check before accessing card details.\n\n"
            "## AI Disclosure\n"
            "N/A"
        ),
        additions=5,
        deletions=2,
        file_count=1,
        comment_count=1,
        state="merged",
        author_name="Alice Engineer",
        labels=["bugfix", "payments"],
        cycle_time_hours=2.5,
        review_time_hours=0.5,
        commits_after_first_review=0,
        review_rounds=1,
        file_paths=["apps/payments/validators.py"],
        commit_messages=["[+0.2h] Fix null check in payment validation"],
        repo_languages=["Python"],
        reviewers=["Bob Backend"],
        review_comments=["[+0.5h] Bob Backend: LGTM, simple fix"],
        jira_key="PAY-1234",
        expected_ai_assisted=False,
        expected_categories=["backend"],
        expected_pr_type="bugfix",
        notes="Low friction PR: small scope, fast review, single round",
    ),
    GoldenTest(
        id="health_hotfix_revert",
        description="Hotfix after a revert - high risk indicator",
        category=GoldenTestCategory.HEALTH,
        pr_title="Hotfix: Restore payment processing after revert",
        pr_body=(
            "## Context\n"
            "Previous PR broke payment processing and was reverted.\n\n"
            "## Fix\n"
            "Properly handle edge case in currency conversion.\n\n"
            "## Testing\n"
            "Tested with all supported currencies."
        ),
        additions=15,
        deletions=3,
        file_count=2,
        comment_count=5,
        state="merged",
        author_name="DevOps Engineer",
        labels=["hotfix", "critical", "payments"],
        is_hotfix=True,
        is_revert=False,
        cycle_time_hours=1.0,
        review_time_hours=0.25,
        commits_after_first_review=1,
        review_rounds=1,
        file_paths=["apps/payments/currency.py", "apps/payments/tests/test_currency.py"],
        commit_messages=[
            "[+0.1h] Hotfix: Fix currency conversion edge case",
            "[+0.8h] Add regression test",
        ],
        repo_languages=["Python"],
        reviewers=["CTO", "Backend Lead"],
        review_comments=[
            "[+0.25h] CTO: Ship it, we need this ASAP",
        ],
        linked_issues=["#1234"],
        expected_ai_assisted=False,
        expected_categories=["backend"],
        expected_pr_type="bugfix",
        notes="High risk: hotfix after revert, critical path",
    ),
    GoldenTest(
        id="health_draft_wip",
        description="Draft PR with work in progress - incomplete state",
        category=GoldenTestCategory.HEALTH,
        pr_title="WIP: Add GraphQL API layer",
        pr_body=(
            "## Draft\n"
            "Work in progress - not ready for review.\n\n"
            "## TODO\n"
            "- [x] Setup GraphQL schema\n"
            "- [ ] Add resolvers\n"
            "- [ ] Add authentication\n\n"
            "Using Claude for schema design."
        ),
        additions=200,
        deletions=0,
        file_count=5,
        comment_count=0,
        state="open",
        author_name="Junior Dev",
        labels=["wip", "api"],
        is_draft=True,
        cycle_time_hours=None,  # Not merged
        review_time_hours=None,  # Not reviewed
        file_paths=[
            "apps/graphql/schema.py",
            "apps/graphql/types.py",
            "apps/graphql/queries.py",
        ],
        commit_messages=[
            "[+1.0h] Initial GraphQL setup",
            "[+8.0h] Add user type schema",
            "[+24.0h] aider: Implement query resolvers",
        ],
        repo_languages=["Python"],
        milestone="Q1 2025 Release",
        expected_ai_assisted=True,
        expected_tools=["claude", "aider"],
        expected_categories=["backend"],
        expected_pr_type="feature",
        notes="Draft state, multiple AI tools detected (claude mention + aider commit)",
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

    # Build vars with all PR context fields
    vars_dict = {
        "pr_title": test.pr_title,
        "pr_body": test.pr_body,
        "additions": test.additions,
        "deletions": test.deletions,
        "file_count": test.file_count,
        "comment_count": test.comment_count,
        "repo_languages": test.repo_languages,
        "state": test.state,
        "labels": test.labels,
        "is_draft": test.is_draft,
        "is_hotfix": test.is_hotfix,
        "is_revert": test.is_revert,
        "cycle_time_hours": test.cycle_time_hours,
        "review_time_hours": test.review_time_hours,
        "commits_after_first_review": test.commits_after_first_review,
        "review_rounds": test.review_rounds,
        "file_paths": test.file_paths,
        "commit_messages": test.commit_messages,
        "milestone": test.milestone,
        "assignees": test.assignees,
        "linked_issues": test.linked_issues,
        "jira_key": test.jira_key,
        "author_name": test.author_name,
        "reviewers": test.reviewers,
        "review_comments": test.review_comments,
    }

    return {
        "description": f"[{test.id}] {test.description}",
        "vars": vars_dict,
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
