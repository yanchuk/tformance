"""Tests for AI co-author detection service."""

from django.test import TestCase

from apps.integrations.services.ai_detection import (
    AI_TOOL_PATTERNS,
    detect_ai_coauthor,
    get_all_detected_ai_tools,
    get_detected_ai_tool,
)


class TestAIToolPatterns(TestCase):
    """Tests for the centralized AI tool pattern list."""

    def test_ai_tool_patterns_is_list(self):
        """AI_TOOL_PATTERNS should be a list."""
        self.assertIsInstance(AI_TOOL_PATTERNS, list)

    def test_ai_tool_patterns_not_empty(self):
        """AI_TOOL_PATTERNS should contain patterns."""
        self.assertGreater(len(AI_TOOL_PATTERNS), 0)

    def test_each_pattern_has_required_keys(self):
        """Each pattern should have 'name' and 'patterns' keys."""
        for tool in AI_TOOL_PATTERNS:
            self.assertIn("name", tool, f"Pattern missing 'name': {tool}")
            self.assertIn("patterns", tool, f"Pattern missing 'patterns': {tool}")
            self.assertIsInstance(tool["patterns"], list)
            self.assertGreater(len(tool["patterns"]), 0)

    def test_contains_github_copilot(self):
        """Should include GitHub Copilot patterns."""
        names = [t["name"] for t in AI_TOOL_PATTERNS]
        self.assertIn("GitHub Copilot", names)

    def test_contains_claude_code(self):
        """Should include Claude Code patterns."""
        names = [t["name"] for t in AI_TOOL_PATTERNS]
        self.assertIn("Claude Code", names)

    def test_contains_cursor(self):
        """Should include Cursor patterns."""
        names = [t["name"] for t in AI_TOOL_PATTERNS]
        self.assertIn("Cursor", names)

    def test_contains_devin(self):
        """Should include Devin patterns."""
        names = [t["name"] for t in AI_TOOL_PATTERNS]
        self.assertIn("Devin", names)

    def test_contains_amazon_codewhisperer(self):
        """Should include Amazon CodeWhisperer patterns."""
        names = [t["name"] for t in AI_TOOL_PATTERNS]
        self.assertIn("Amazon CodeWhisperer", names)

    def test_contains_codeium(self):
        """Should include Codeium patterns."""
        names = [t["name"] for t in AI_TOOL_PATTERNS]
        self.assertIn("Codeium", names)

    def test_contains_tabnine(self):
        """Should include Tabnine patterns."""
        names = [t["name"] for t in AI_TOOL_PATTERNS]
        self.assertIn("Tabnine", names)

    def test_contains_sourcegraph_cody(self):
        """Should include Sourcegraph Cody patterns."""
        names = [t["name"] for t in AI_TOOL_PATTERNS]
        self.assertIn("Sourcegraph Cody", names)

    def test_contains_aider(self):
        """Should include Aider patterns."""
        names = [t["name"] for t in AI_TOOL_PATTERNS]
        self.assertIn("Aider", names)


class TestDetectAICoauthor(TestCase):
    """Tests for detect_ai_coauthor function."""

    def test_empty_commits_returns_false(self):
        """Empty commit list should return False."""
        self.assertFalse(detect_ai_coauthor([]))

    def test_none_commits_returns_false(self):
        """None commits should return False."""
        self.assertFalse(detect_ai_coauthor(None))

    def test_no_ai_signature_returns_false(self):
        """Commits without AI signatures should return False."""
        commits = [
            {"message": "Fix bug in login form"},
            {"message": "Add new feature\n\nCo-Authored-By: John Doe <john@example.com>"},
        ]
        self.assertFalse(detect_ai_coauthor(commits))

    def test_detects_github_copilot_coauthor(self):
        """Should detect GitHub Copilot co-author signature."""
        commits = [
            {"message": "Add feature\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_copilot_case_insensitive(self):
        """Should detect Copilot regardless of case."""
        commits = [
            {"message": "Add feature\n\nco-authored-by: github copilot <copilot@github.com>"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_claude_coauthor(self):
        """Should detect Claude co-author signature."""
        commits = [
            {"message": "Fix bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_claude_code_signature(self):
        """Should detect Claude Code generated signature."""
        commits = [
            {"message": "Update config\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_cursor_coauthor(self):
        """Should detect Cursor AI co-author signature."""
        commits = [
            {"message": "Add tests\n\nCo-Authored-By: Cursor <cursor@cursor.com>"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_devin_coauthor(self):
        """Should detect Devin AI co-author signature."""
        commits = [
            {"message": "Refactor code\n\nCo-Authored-By: Devin <devin@cognition-labs.com>"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_codewhisperer(self):
        """Should detect Amazon CodeWhisperer signature."""
        commits = [
            {"message": "Add function\n\nGenerated by Amazon CodeWhisperer"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_codeium(self):
        """Should detect Codeium signature."""
        commits = [
            {"message": "Update module\n\nCo-Authored-By: Codeium <support@codeium.com>"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_windsurf(self):
        """Should detect Windsurf (Codeium IDE) signature."""
        commits = [
            {"message": "Fix issue\n\nGenerated with Windsurf"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_tabnine(self):
        """Should detect Tabnine signature."""
        commits = [
            {"message": "Add helper\n\nCo-Authored-By: Tabnine <support@tabnine.com>"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_sourcegraph_cody(self):
        """Should detect Sourcegraph Cody signature."""
        commits = [
            {"message": "Update docs\n\nCo-Authored-By: Cody <cody@sourcegraph.com>"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_aider(self):
        """Should detect Aider signature."""
        commits = [
            {"message": "Refactor\n\naider: refactored function"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_detects_ai_in_any_commit(self):
        """Should detect AI if any commit has signature."""
        commits = [
            {"message": "Manual commit 1"},
            {"message": "Manual commit 2"},
            {"message": "AI commit\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>"},
            {"message": "Manual commit 3"},
        ]
        self.assertTrue(detect_ai_coauthor(commits))

    def test_handles_commits_without_message_key(self):
        """Should handle commits that don't have message key."""
        commits = [
            {"sha": "abc123"},
            {"message": "Valid commit"},
        ]
        self.assertFalse(detect_ai_coauthor(commits))

    def test_handles_none_message(self):
        """Should handle commits with None message."""
        commits = [
            {"message": None},
            {"message": "Valid commit"},
        ]
        self.assertFalse(detect_ai_coauthor(commits))


class TestGetDetectedAITool(TestCase):
    """Tests for get_detected_ai_tool function."""

    def test_empty_commits_returns_none(self):
        """Empty commit list should return None."""
        self.assertIsNone(get_detected_ai_tool([]))

    def test_none_commits_returns_none(self):
        """None commits should return None."""
        self.assertIsNone(get_detected_ai_tool(None))

    def test_no_ai_signature_returns_none(self):
        """Commits without AI signatures should return None."""
        commits = [
            {"message": "Fix bug in login form"},
        ]
        self.assertIsNone(get_detected_ai_tool(commits))

    def test_returns_github_copilot(self):
        """Should return 'GitHub Copilot' for Copilot signatures."""
        commits = [
            {"message": "Add feature\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>"},
        ]
        self.assertEqual(get_detected_ai_tool(commits), "GitHub Copilot")

    def test_returns_claude_code(self):
        """Should return 'Claude Code' for Claude signatures."""
        commits = [
            {"message": "Fix bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>"},
        ]
        self.assertEqual(get_detected_ai_tool(commits), "Claude Code")

    def test_returns_cursor(self):
        """Should return 'Cursor' for Cursor signatures."""
        commits = [
            {"message": "Add tests\n\nCo-Authored-By: Cursor <cursor@cursor.com>"},
        ]
        self.assertEqual(get_detected_ai_tool(commits), "Cursor")

    def test_returns_devin(self):
        """Should return 'Devin' for Devin signatures."""
        commits = [
            {"message": "Refactor\n\nCo-Authored-By: Devin <devin@cognition-labs.com>"},
        ]
        self.assertEqual(get_detected_ai_tool(commits), "Devin")

    def test_returns_first_detected_tool(self):
        """Should return first detected tool when multiple present."""
        commits = [
            {"message": "First\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>"},
            {"message": "Second\n\nCo-Authored-By: Claude <noreply@anthropic.com>"},
        ]
        # Should return the first one found
        result = get_detected_ai_tool(commits)
        self.assertIn(result, ["GitHub Copilot", "Claude Code"])


class TestGetAllDetectedAITools(TestCase):
    """Tests for get_all_detected_ai_tools function."""

    def test_empty_commits_returns_empty_list(self):
        """Empty commit list should return empty list."""
        self.assertEqual(get_all_detected_ai_tools([]), [])

    def test_none_commits_returns_empty_list(self):
        """None commits should return empty list."""
        self.assertEqual(get_all_detected_ai_tools(None), [])

    def test_no_ai_signature_returns_empty_list(self):
        """Commits without AI signatures should return empty list."""
        commits = [
            {"message": "Fix bug in login form"},
        ]
        self.assertEqual(get_all_detected_ai_tools(commits), [])

    def test_returns_single_tool(self):
        """Should return list with single tool."""
        commits = [
            {"message": "Add feature\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>"},
        ]
        self.assertEqual(get_all_detected_ai_tools(commits), ["GitHub Copilot"])

    def test_returns_multiple_tools(self):
        """Should return all detected tools."""
        commits = [
            {"message": "First\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>"},
            {"message": "Second\n\nCo-Authored-By: Claude <noreply@anthropic.com>"},
        ]
        result = get_all_detected_ai_tools(commits)
        self.assertIn("GitHub Copilot", result)
        self.assertIn("Claude Code", result)

    def test_no_duplicates(self):
        """Should not return duplicate tool names."""
        commits = [
            {"message": "First\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>"},
            {"message": "Second\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>"},
        ]
        result = get_all_detected_ai_tools(commits)
        self.assertEqual(result, ["GitHub Copilot"])
