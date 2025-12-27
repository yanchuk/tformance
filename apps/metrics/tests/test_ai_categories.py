"""Tests for AI tool category classification service."""

from django.test import TestCase

from apps.metrics.services.ai_categories import (
    CATEGORY_BOTH,
    CATEGORY_CODE,
    CATEGORY_REVIEW,
    categorize_tools,
    get_ai_category,
    get_category_badge_class,
    get_category_display_name,
    get_tool_category,
    is_excluded_tool,
    normalize_tool_name,
)


class TestNormalizeToolName(TestCase):
    """Tests for normalize_tool_name function."""

    def test_lowercase_conversion(self):
        """Tool names should be lowercased."""
        self.assertEqual(normalize_tool_name("Cursor"), "cursor")
        self.assertEqual(normalize_tool_name("COPILOT"), "copilot")
        self.assertEqual(normalize_tool_name("CodeRabbit"), "coderabbit")

    def test_whitespace_stripping(self):
        """Whitespace should be stripped."""
        self.assertEqual(normalize_tool_name("  cursor  "), "cursor")
        self.assertEqual(normalize_tool_name("\tcoderabbit\n"), "coderabbit")

    def test_empty_and_none(self):
        """Empty and None values should return empty string."""
        self.assertEqual(normalize_tool_name(""), "")
        self.assertEqual(normalize_tool_name(None), "")


class TestGetToolCategory(TestCase):
    """Tests for get_tool_category function."""

    def test_code_tools_return_code(self):
        """Code tools should return 'code' category."""
        code_tools = ["cursor", "copilot", "claude", "aider", "cody", "devin"]
        for tool in code_tools:
            with self.subTest(tool=tool):
                self.assertEqual(get_tool_category(tool), CATEGORY_CODE)

    def test_review_tools_return_review(self):
        """Review tools should return 'review' category."""
        review_tools = ["coderabbit", "cubic", "greptile", "sourcery"]
        for tool in review_tools:
            with self.subTest(tool=tool):
                self.assertEqual(get_tool_category(tool), CATEGORY_REVIEW)

    def test_mixed_tools_default_to_code(self):
        """Mixed tools should default to 'code' category."""
        mixed_tools = ["ellipsis", "bito", "qodo", "codium", "augment"]
        for tool in mixed_tools:
            with self.subTest(tool=tool):
                self.assertEqual(get_tool_category(tool), CATEGORY_CODE)

    def test_excluded_tools_return_none(self):
        """Excluded tools should return None."""
        excluded_tools = ["snyk", "mintlify", "dependabot", "renovate"]
        for tool in excluded_tools:
            with self.subTest(tool=tool):
                self.assertIsNone(get_tool_category(tool))

    def test_case_insensitive(self):
        """Tool matching should be case-insensitive."""
        self.assertEqual(get_tool_category("CURSOR"), CATEGORY_CODE)
        self.assertEqual(get_tool_category("CodeRabbit"), CATEGORY_REVIEW)
        self.assertEqual(get_tool_category("SNYK"), None)

    def test_unknown_tools_default_to_code(self):
        """Unknown tools should default to code category."""
        self.assertEqual(get_tool_category("some_new_ai_tool"), CATEGORY_CODE)

    def test_empty_returns_none(self):
        """Empty tool name should return None."""
        self.assertIsNone(get_tool_category(""))
        self.assertIsNone(get_tool_category(None))

    def test_tool_name_variations(self):
        """Common tool name variations should be recognized."""
        # Claude variations
        self.assertEqual(get_tool_category("claude"), CATEGORY_CODE)
        self.assertEqual(get_tool_category("claude_code"), CATEGORY_CODE)
        self.assertEqual(get_tool_category("claude-code"), CATEGORY_CODE)

        # Copilot variations
        self.assertEqual(get_tool_category("copilot"), CATEGORY_CODE)
        self.assertEqual(get_tool_category("github copilot"), CATEGORY_CODE)

        # CodeRabbit variations
        self.assertEqual(get_tool_category("coderabbit"), CATEGORY_REVIEW)
        self.assertEqual(get_tool_category("code rabbit"), CATEGORY_REVIEW)


class TestCategorizeTools(TestCase):
    """Tests for categorize_tools function."""

    def test_splits_code_and_review(self):
        """Should split tools into code and review lists."""
        result = categorize_tools(["cursor", "coderabbit", "copilot"])
        self.assertEqual(set(result["code"]), {"cursor", "copilot"})
        self.assertEqual(result["review"], ["coderabbit"])

    def test_excludes_excluded_tools(self):
        """Excluded tools should not appear in either category."""
        result = categorize_tools(["cursor", "snyk", "mintlify"])
        self.assertEqual(result["code"], ["cursor"])
        self.assertEqual(result["review"], [])

    def test_empty_list_returns_empty_dict(self):
        """Empty input should return empty lists."""
        result = categorize_tools([])
        self.assertEqual(result, {"code": [], "review": []})

    def test_none_returns_empty_dict(self):
        """None input should return empty lists."""
        result = categorize_tools(None)
        self.assertEqual(result, {"code": [], "review": []})

    def test_all_code_tools(self):
        """List with only code tools."""
        result = categorize_tools(["cursor", "copilot", "claude"])
        self.assertEqual(len(result["code"]), 3)
        self.assertEqual(result["review"], [])

    def test_all_review_tools(self):
        """List with only review tools."""
        result = categorize_tools(["coderabbit", "cubic", "greptile"])
        self.assertEqual(result["code"], [])
        self.assertEqual(len(result["review"]), 3)

    def test_preserves_original_case(self):
        """Original tool names should be preserved in output."""
        result = categorize_tools(["Cursor", "CodeRabbit"])
        self.assertEqual(result["code"], ["Cursor"])
        self.assertEqual(result["review"], ["CodeRabbit"])


class TestGetAiCategory(TestCase):
    """Tests for get_ai_category function."""

    def test_code_only_returns_code(self):
        """PR with only code tools should return 'code'."""
        self.assertEqual(get_ai_category(["cursor", "copilot"]), CATEGORY_CODE)

    def test_review_only_returns_review(self):
        """PR with only review tools should return 'review'."""
        self.assertEqual(get_ai_category(["coderabbit", "cubic"]), CATEGORY_REVIEW)

    def test_both_returns_both(self):
        """PR with both code and review tools should return 'both'."""
        self.assertEqual(get_ai_category(["cursor", "coderabbit"]), CATEGORY_BOTH)

    def test_empty_returns_none(self):
        """Empty list should return None."""
        self.assertIsNone(get_ai_category([]))

    def test_none_returns_none(self):
        """None input should return None."""
        self.assertIsNone(get_ai_category(None))

    def test_only_excluded_returns_none(self):
        """List with only excluded tools should return None."""
        self.assertIsNone(get_ai_category(["snyk", "mintlify"]))

    def test_mixed_with_excluded(self):
        """Excluded tools should be ignored in category determination."""
        self.assertEqual(get_ai_category(["cursor", "snyk"]), CATEGORY_CODE)
        self.assertEqual(get_ai_category(["coderabbit", "mintlify"]), CATEGORY_REVIEW)


class TestDisplayFunctions(TestCase):
    """Tests for display helper functions."""

    def test_category_display_name(self):
        """Display names should be human-readable."""
        self.assertEqual(get_category_display_name(CATEGORY_CODE), "Code AI")
        self.assertEqual(get_category_display_name(CATEGORY_REVIEW), "Review AI")
        self.assertEqual(get_category_display_name(CATEGORY_BOTH), "Code + Review AI")

    def test_category_display_name_empty(self):
        """Empty/None category should return empty string."""
        self.assertEqual(get_category_display_name(None), "")
        self.assertEqual(get_category_display_name(""), "")

    def test_category_badge_class(self):
        """Badge classes should be valid DaisyUI classes."""
        self.assertEqual(get_category_badge_class(CATEGORY_CODE), "badge-primary")
        self.assertEqual(get_category_badge_class(CATEGORY_REVIEW), "badge-secondary")
        self.assertEqual(get_category_badge_class(CATEGORY_BOTH), "badge-accent")

    def test_category_badge_class_empty(self):
        """Empty/None category should return ghost badge."""
        self.assertEqual(get_category_badge_class(None), "badge-ghost")
        self.assertEqual(get_category_badge_class(""), "badge-ghost")


class TestIsExcludedTool(TestCase):
    """Tests for is_excluded_tool function."""

    def test_excluded_tools(self):
        """Excluded tools should return True."""
        self.assertTrue(is_excluded_tool("snyk"))
        self.assertTrue(is_excluded_tool("mintlify"))
        self.assertTrue(is_excluded_tool("dependabot"))

    def test_non_excluded_tools(self):
        """Non-excluded tools should return False."""
        self.assertFalse(is_excluded_tool("cursor"))
        self.assertFalse(is_excluded_tool("coderabbit"))

    def test_case_insensitive(self):
        """Should be case-insensitive."""
        self.assertTrue(is_excluded_tool("SNYK"))
        self.assertTrue(is_excluded_tool("Mintlify"))


class TestRealWorldScenarios(TestCase):
    """Tests based on real PR data patterns."""

    def test_cursor_pr_summary(self):
        """PR with Cursor Bugbot summary should be code category."""
        tools = ["cursor"]
        self.assertEqual(get_ai_category(tools), CATEGORY_CODE)

    def test_coderabbit_summary(self):
        """PR with CodeRabbit summary should be review category."""
        tools = ["coderabbit"]
        self.assertEqual(get_ai_category(tools), CATEGORY_REVIEW)

    def test_claude_code_signature(self):
        """PR with Claude Code signature should be code category."""
        tools = ["claude"]
        self.assertEqual(get_ai_category(tools), CATEGORY_CODE)

    def test_devin_pr(self):
        """PR from Devin AI agent should be code category."""
        tools = ["devin"]
        self.assertEqual(get_ai_category(tools), CATEGORY_CODE)

    def test_multiple_code_tools(self):
        """PR with multiple code tools still returns code."""
        tools = ["cursor", "claude", "copilot"]
        self.assertEqual(get_ai_category(tools), CATEGORY_CODE)

    def test_cubic_with_claude(self):
        """PR with both Cubic (review) and Claude (code)."""
        tools = ["cubic", "claude"]
        self.assertEqual(get_ai_category(tools), CATEGORY_BOTH)
