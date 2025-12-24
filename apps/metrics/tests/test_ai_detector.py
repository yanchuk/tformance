"""
Tests for AI detector service - TDD RED phase.

These tests define the expected behavior for:
- detect_ai_author(username) - identify AI bot PR authors
- detect_ai_reviewer(username) - identify AI reviewer bots
- detect_ai_in_text(text) - find AI signatures in PR/commit text
- parse_co_authors(message) - extract AI co-authors from commit messages
"""

from django.test import TestCase

from apps.metrics.services.ai_detector import (
    detect_ai_author,
    detect_ai_in_text,
    detect_ai_reviewer,
    parse_co_authors,
)


class TestDetectAIAuthor(TestCase):
    """Tests for detect_ai_author() function - identifies bot PR authors."""

    def test_detects_devin_ai_integration_bot(self):
        """Devin AI integration bot should be detected as AI author."""
        result = detect_ai_author("devin-ai-integration[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "devin")

    def test_detects_devin_bot(self):
        """Devin bot should be detected as AI author."""
        result = detect_ai_author("devin[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "devin")

    def test_detects_devin_ai_bot(self):
        """Devin AI bot should be detected as AI author."""
        result = detect_ai_author("devin-ai[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "devin")

    def test_detects_dependabot_author(self):
        """Dependabot should be detected as AI author."""
        result = detect_ai_author("dependabot[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "dependabot")

    def test_detects_renovate_bot_author(self):
        """Renovate bot should be detected as AI author."""
        result = detect_ai_author("renovate[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "renovate")

    def test_detects_github_actions_bot(self):
        """GitHub Actions bot should be detected as AI author."""
        result = detect_ai_author("github-actions[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "github_actions")

    def test_human_author_not_detected(self):
        """Regular human authors should not be detected as AI."""
        result = detect_ai_author("john-doe")
        self.assertFalse(result["is_ai"])
        self.assertEqual(result["ai_type"], "")

    def test_case_insensitive_detection(self):
        """Detection should be case-insensitive."""
        result = detect_ai_author("Devin-AI-Integration[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "devin")

    def test_empty_username(self):
        """Empty username should return not AI."""
        result = detect_ai_author("")
        self.assertFalse(result["is_ai"])
        self.assertEqual(result["ai_type"], "")

    def test_none_username(self):
        """None username should return not AI."""
        result = detect_ai_author(None)
        self.assertFalse(result["is_ai"])
        self.assertEqual(result["ai_type"], "")


class TestDetectAIReviewer(TestCase):
    """Tests for detect_ai_reviewer() function."""

    def test_detects_coderabbit_bot(self):
        """CodeRabbit AI reviewer should be detected."""
        result = detect_ai_reviewer("coderabbitai")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "coderabbit")

    def test_detects_coderabbit_bot_with_suffix(self):
        """CodeRabbit with [bot] suffix should be detected."""
        result = detect_ai_reviewer("coderabbit[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "coderabbit")

    def test_detects_github_copilot_bot(self):
        """GitHub Copilot bot reviewer should be detected."""
        result = detect_ai_reviewer("github-copilot[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "copilot")

    def test_detects_copilot_bot(self):
        """Copilot bot reviewer should be detected."""
        result = detect_ai_reviewer("copilot[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "copilot")

    def test_detects_dependabot(self):
        """Dependabot should be detected as AI reviewer."""
        result = detect_ai_reviewer("dependabot[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "dependabot")

    def test_detects_renovate_bot(self):
        """Renovate bot should be detected."""
        result = detect_ai_reviewer("renovate[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "renovate")

    def test_detects_renovate_bot_alt(self):
        """Renovate-bot alternate username should be detected."""
        result = detect_ai_reviewer("renovate-bot")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "renovate")

    def test_detects_snyk_bot(self):
        """Snyk bot should be detected."""
        result = detect_ai_reviewer("snyk-bot")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "snyk")

    def test_detects_sonarcloud_bot(self):
        """SonarCloud bot should be detected."""
        result = detect_ai_reviewer("sonarcloud[bot]")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "sonarcloud")

    def test_human_reviewer_not_detected(self):
        """Regular human reviewers should not be detected as AI."""
        result = detect_ai_reviewer("john-doe")
        self.assertFalse(result["is_ai"])
        self.assertEqual(result["ai_type"], "")

    def test_username_with_copilot_in_name(self):
        """Username containing 'copilot' should not be falsely detected."""
        # A human with "copilot" in their username shouldn't trigger
        result = detect_ai_reviewer("copilot-fan-2023")
        self.assertFalse(result["is_ai"])

    def test_case_insensitive_detection(self):
        """Detection should be case-insensitive."""
        result = detect_ai_reviewer("CodeRabbitAI")
        self.assertTrue(result["is_ai"])
        self.assertEqual(result["ai_type"], "coderabbit")

    def test_empty_username(self):
        """Empty username should return not AI."""
        result = detect_ai_reviewer("")
        self.assertFalse(result["is_ai"])
        self.assertEqual(result["ai_type"], "")

    def test_none_username(self):
        """None username should return not AI."""
        result = detect_ai_reviewer(None)
        self.assertFalse(result["is_ai"])
        self.assertEqual(result["ai_type"], "")


class TestDetectAIInText(TestCase):
    """Tests for detect_ai_in_text() function."""

    def test_detects_claude_code_signature(self):
        """Claude Code signature in text should be detected."""
        text = """
        ## Summary
        Added new feature

        🤖 Generated with [Claude Code](https://claude.com/claude-code)
        """
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude_code", result["ai_tools"])

    def test_detects_claude_code_without_emoji(self):
        """Claude Code signature without emoji should be detected."""
        text = "Generated with Claude Code"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude_code", result["ai_tools"])

    def test_detects_copilot_signature(self):
        """GitHub Copilot signature should be detected."""
        text = "This code was generated by GitHub Copilot"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("copilot", result["ai_tools"])

    def test_detects_cursor_signature(self):
        """Cursor AI signature should be detected."""
        text = "Generated by Cursor AI"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_detects_generic_ai_generated(self):
        """Generic 'AI-generated' should be detected."""
        text = "This PR is AI-generated"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("ai_generic", result["ai_tools"])

    def test_detects_generic_ai_assisted(self):
        """Generic 'AI-assisted' should be detected."""
        text = "This change was AI assisted"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("ai_generic", result["ai_tools"])

    def test_detects_multiple_tools(self):
        """Multiple AI tool signatures should all be detected."""
        text = """
        Generated with Claude Code
        Also used GitHub Copilot for suggestions
        """
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude_code", result["ai_tools"])
        self.assertIn("copilot", result["ai_tools"])

    def test_no_ai_in_normal_text(self):
        """Normal text without AI signatures should not be detected."""
        text = """
        ## Summary
        Fixed a bug in the login flow.

        ## Changes
        - Updated validation logic
        - Added error handling
        """
        result = detect_ai_in_text(text)
        self.assertFalse(result["is_ai_assisted"])
        self.assertEqual(result["ai_tools"], [])

    def test_empty_text(self):
        """Empty text should return not AI-assisted."""
        result = detect_ai_in_text("")
        self.assertFalse(result["is_ai_assisted"])
        self.assertEqual(result["ai_tools"], [])

    def test_none_text(self):
        """None text should return not AI-assisted."""
        result = detect_ai_in_text(None)
        self.assertFalse(result["is_ai_assisted"])
        self.assertEqual(result["ai_tools"], [])

    def test_case_insensitive(self):
        """Detection should be case-insensitive."""
        text = "GENERATED WITH CLAUDE CODE"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude_code", result["ai_tools"])


class TestParseCoAuthors(TestCase):
    """Tests for parse_co_authors() function."""

    def test_parses_claude_co_author(self):
        """Claude co-author in commit message should be parsed."""
        message = """
        Add new feature

        Co-Authored-By: Claude <noreply@anthropic.com>
        """
        result = parse_co_authors(message)
        self.assertTrue(result["has_ai_co_authors"])
        self.assertIn("claude", result["ai_co_authors"])

    def test_parses_claude_opus_co_author(self):
        """Claude Opus co-author should be parsed."""
        message = """
        Fix bug

        🤖 Generated with [Claude Code](https://claude.com/claude-code)

        Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
        """
        result = parse_co_authors(message)
        self.assertTrue(result["has_ai_co_authors"])
        self.assertIn("claude", result["ai_co_authors"])

    def test_parses_claude_sonnet_co_author(self):
        """Claude Sonnet co-author should be parsed."""
        message = "Fix tests\n\nCo-Authored-By: Claude Sonnet <noreply@anthropic.com>"
        result = parse_co_authors(message)
        self.assertTrue(result["has_ai_co_authors"])
        self.assertIn("claude", result["ai_co_authors"])

    def test_parses_copilot_co_author(self):
        """GitHub Copilot co-author should be parsed."""
        message = "Update code\n\nCo-Authored-By: GitHub Copilot <copilot@github.com>"
        result = parse_co_authors(message)
        self.assertTrue(result["has_ai_co_authors"])
        self.assertIn("copilot", result["ai_co_authors"])

    def test_parses_cursor_co_author(self):
        """Cursor co-author should be parsed."""
        message = "Refactor\n\nCo-Authored-By: Cursor <noreply@cursor.sh>"
        result = parse_co_authors(message)
        self.assertTrue(result["has_ai_co_authors"])
        self.assertIn("cursor", result["ai_co_authors"])

    def test_parses_cody_co_author(self):
        """Cody co-author should be parsed."""
        message = "Add feature\n\nCo-Authored-By: Cody <cody@sourcegraph.com>"
        result = parse_co_authors(message)
        self.assertTrue(result["has_ai_co_authors"])
        self.assertIn("cody", result["ai_co_authors"])

    def test_parses_multiple_co_authors(self):
        """Multiple AI co-authors should all be parsed."""
        message = """
        Big refactor

        Co-Authored-By: Claude <noreply@anthropic.com>
        Co-Authored-By: GitHub Copilot <copilot@github.com>
        """
        result = parse_co_authors(message)
        self.assertTrue(result["has_ai_co_authors"])
        self.assertIn("claude", result["ai_co_authors"])
        self.assertIn("copilot", result["ai_co_authors"])

    def test_human_co_author_not_detected(self):
        """Human co-authors should not be detected as AI."""
        message = """
        Pair programming session

        Co-Authored-By: John Doe <john@example.com>
        Co-Authored-By: Jane Smith <jane@example.com>
        """
        result = parse_co_authors(message)
        self.assertFalse(result["has_ai_co_authors"])
        self.assertEqual(result["ai_co_authors"], [])

    def test_mixed_co_authors(self):
        """Mixed human and AI co-authors should only detect AI ones."""
        message = """
        Collaborative work

        Co-Authored-By: John Doe <john@example.com>
        Co-Authored-By: Claude <noreply@anthropic.com>
        """
        result = parse_co_authors(message)
        self.assertTrue(result["has_ai_co_authors"])
        self.assertIn("claude", result["ai_co_authors"])
        self.assertEqual(len(result["ai_co_authors"]), 1)

    def test_no_co_authors(self):
        """Message without co-authors should return empty."""
        message = "Simple commit without co-authors"
        result = parse_co_authors(message)
        self.assertFalse(result["has_ai_co_authors"])
        self.assertEqual(result["ai_co_authors"], [])

    def test_empty_message(self):
        """Empty message should return empty result."""
        result = parse_co_authors("")
        self.assertFalse(result["has_ai_co_authors"])
        self.assertEqual(result["ai_co_authors"], [])

    def test_none_message(self):
        """None message should return empty result."""
        result = parse_co_authors(None)
        self.assertFalse(result["has_ai_co_authors"])
        self.assertEqual(result["ai_co_authors"], [])

    def test_case_insensitive_co_authored_by(self):
        """Co-Authored-By parsing should be case-insensitive."""
        message = "Fix\n\nco-authored-by: Claude <noreply@anthropic.com>"
        result = parse_co_authors(message)
        self.assertTrue(result["has_ai_co_authors"])
        self.assertIn("claude", result["ai_co_authors"])


class TestCursorPatterns(TestCase):
    """Tests for Cursor IDE detection patterns."""

    def test_cursor_with_parenthesis(self):
        """'Cursor (' pattern should detect Cursor."""
        text = "Cursor (Claude 4.5 Sonnet) used for questions"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_cursor_parenthesis_no_space(self):
        """'Cursor(' without space should detect Cursor."""
        text = "Use Cursor(auto-mode) for the initial setup"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_cursor_ide_explicit(self):
        """'Cursor IDE' should detect Cursor."""
        text = "Model: Claude(Sonnet 4.5) via Cursor IDE"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_cursor_auto_mode(self):
        """'Cursor auto mode' should detect Cursor."""
        text = "Used cursor auto mode for doing similar pattern changes"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_cursor_auto_mode_hyphen(self):
        """'Cursor auto-mode' with hyphen should detect Cursor."""
        text = "Cursor auto-mode was helpful"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_used_cursor(self):
        """'Used Cursor' should detect Cursor."""
        text = "Used Cursor for codebase queries"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_using_cursor(self):
        """'Using Cursor' should detect Cursor."""
        text = "Using Cursor to refactor this code"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_cursor_used_for(self):
        """'Cursor used for' should detect Cursor."""
        text = "Cursor used for: Hints and advice"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_ide_cursor_structured(self):
        """Structured 'IDE: Cursor' format should detect Cursor."""
        text = "IDE: Cursor\nModel: Auto"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    # False positive prevention tests
    def test_mouse_cursor_not_detected(self):
        """'move cursor' (mouse) should NOT detect Cursor IDE."""
        text = "Move cursor to the submit button and click"
        result = detect_ai_in_text(text)
        self.assertNotIn("cursor", result.get("ai_tools", []))

    def test_database_cursor_not_detected(self):
        """'database cursor' should NOT detect Cursor IDE."""
        text = "Use a database cursor to iterate over results"
        result = detect_ai_in_text(text)
        self.assertNotIn("cursor", result.get("ai_tools", []))

    def test_cursor_position_not_detected(self):
        """'cursor position' should NOT detect Cursor IDE."""
        text = "Get the cursor position in the text field"
        result = detect_ai_in_text(text)
        self.assertNotIn("cursor", result.get("ai_tools", []))


class TestClaudeModelPatterns(TestCase):
    """Tests for Claude model name detection patterns."""

    def test_claude_sonnet(self):
        """'Claude Sonnet' should detect Claude."""
        text = "AI prompt was generated with Claude Sonnet"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_claude_opus(self):
        """'Claude Opus' should detect Claude."""
        text = "Generated using Claude Opus"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_claude_haiku(self):
        """'Claude Haiku' should detect Claude."""
        text = "Quick check with Claude Haiku"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_claude_version_sonnet(self):
        """'Claude 4.5 Sonnet' with version should detect Claude."""
        text = "Cursor (Claude 4.5 Sonnet) used for questions"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_claude_version_opus(self):
        """'Claude 4 Opus' with version should detect Claude."""
        text = "Model: Claude 4 Opus"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_sonnet_with_version(self):
        """'Sonnet 4.5' should detect Claude."""
        text = "Used Sonnet 4.5 for this task"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_claude_parenthesis_format(self):
        """'Claude(Sonnet 4.5)' should detect Claude."""
        text = "Model: Claude(Sonnet 4.5) via Cursor IDE"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    # False positive prevention
    def test_claude_api_not_ai_authoring(self):
        """'Integrate Claude API' is product integration, not AI authoring."""
        text = "This PR integrates Claude API for customer chat"
        result = detect_ai_in_text(text)
        # Should NOT detect as AI-authored (it's about using Claude as a product)
        self.assertNotIn("claude", result.get("ai_tools", []))

    def test_sonnet_music_not_detected(self):
        """Generic 'sonnet' (poetry) should NOT detect Claude."""
        text = "Like a sonnet in the wind"
        result = detect_ai_in_text(text)
        self.assertNotIn("claude", result.get("ai_tools", []))

    def test_claude_code_hyphenated(self):
        """'claude-code' (hyphenated) should detect Claude Code."""
        text = "claude-code used with Sonnet-4.5 to implement test"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude_code", result["ai_tools"])

    def test_with_claude(self):
        """'with Claude' should detect Claude."""
        text = "Assisted coding with Cursor and Claude"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_and_claude(self):
        """'and Claude' should detect Claude."""
        text = "Used Cursor and Claude for this PR"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])


class TestAdditionalCursorPatterns(TestCase):
    """Tests for additional Cursor patterns found in validation."""

    def test_with_cursor(self):
        """'with Cursor' should detect Cursor."""
        text = "Assisted coding with Cursor and Claude"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_cursor_in_auto_mode(self):
        """'cursor in auto mode' should detect Cursor."""
        text = "Gemini, cursor in auto mode, and claude-4.5 sonnet used"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])


class TestCopilotPatterns(TestCase):
    """Tests for Copilot detection patterns."""

    def test_copilot_used(self):
        """'Copilot used to...' should detect Copilot."""
        text = "Copilot used to format PR"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("copilot", result["ai_tools"])


class TestGeminiPatterns(TestCase):
    """Tests for Google Gemini detection patterns."""

    def test_gemini_with_usage_context(self):
        """'with Gemini' should detect Gemini (requires usage context to avoid false positives)."""
        text = "with Gemini, cursor in auto mode, and claude-4.5 sonnet used"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("gemini", result["ai_tools"])

    def test_used_gemini(self):
        """'used Gemini' should detect Gemini."""
        text = "used Gemini to research about ISBN format"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("gemini", result["ai_tools"])


class TestClaudeVersionPatterns(TestCase):
    """Tests for Claude with version number patterns."""

    def test_claude_4_used(self):
        """'claude 4 used' should detect Claude."""
        text = "- claude 4 used"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_claude_hyphen_4(self):
        """'claude-4' hyphenated should detect Claude."""
        text = "- claude-4 used"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_used_claude_4(self):
        """'used claude-4' should detect Claude."""
        text = "- used claude-4 to understand test suite"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude", result["ai_tools"])

    def test_claude_code_without_hyphen(self):
        """'claude code' (without hyphen) should detect Claude Code."""
        text = "cursor & claude code used to find relevant files"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("claude_code", result["ai_tools"])


class TestCursorContextPatterns(TestCase):
    """Tests for Cursor with context patterns."""

    def test_cursor_for(self):
        """'cursor for' should detect Cursor."""
        text = "- cursor for understanding the code"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_cursor_autocompletions(self):
        """'cursor autocompletions' should detect Cursor."""
        text = "- cursor autocompletions"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_cursor_autocomplete(self):
        """'cursor autocomplete' should detect Cursor."""
        text = "Used cursor autocomplete for boilerplate"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])

    def test_written_by_cursor(self):
        """'written by Cursor' should detect Cursor."""
        text = "Parts of the code are written by Cursor, which are reviewed"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("cursor", result["ai_tools"])


class TestIndirectAIUsagePatterns(TestCase):
    """Tests for indirect AI usage patterns."""

    def test_ai_was_used(self):
        """'AI was used' should detect AI usage."""
        text = "AI was used to extract related code from the PR"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("ai_generic", result["ai_tools"])

    def test_used_ai_for(self):
        """'used AI for' should detect AI usage."""
        text = "I used AI for refactoring this module"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("ai_generic", result["ai_tools"])

    def test_used_ai_to(self):
        """'used AI to' should detect AI usage."""
        text = "We used AI to generate test cases"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("ai_generic", result["ai_tools"])

    def test_with_ai_assistance(self):
        """'with AI assistance' should detect AI usage."""
        text = "This code was written with AI assistance"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("ai_generic", result["ai_tools"])

    def test_ai_helped_with(self):
        """'AI helped with' should detect AI usage."""
        text = "AI helped with writing the tests"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("ai_generic", result["ai_tools"])

    def test_ai_helped_to(self):
        """'AI helped to' should detect AI usage."""
        text = "AI helped to identify the bug"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("ai_generic", result["ai_tools"])

    def test_no_ai_was_used_not_detected(self):
        """'No AI was used' should NOT detect AI usage (negative disclosure)."""
        text = "No AI was used for any part of this contribution."
        result = detect_ai_in_text(text)
        self.assertFalse(result["is_ai_assisted"])

    def test_no_ai_used_not_detected(self):
        """'No AI used' should NOT detect AI usage."""
        text = "AI Disclosure: No AI used"
        result = detect_ai_in_text(text)
        self.assertFalse(result["is_ai_assisted"])


class TestFalsePositivePrevention(TestCase):
    """Tests to ensure we don't have false positives."""

    def test_devin_reference_not_authoring(self):
        """Referencing Devin's past work should NOT detect as AI-authored."""
        text = "Devin added unnecessary tags in this PR, we need to fix them"
        result = detect_ai_in_text(text)
        # This is fixing Devin's mistake, not AI-authored by Devin
        self.assertFalse(result["is_ai_assisted"])

    def test_ai_product_not_authoring(self):
        """Building AI features is not the same as AI-authored code."""
        text = "Add AI-powered search to the dashboard"
        result = detect_ai_in_text(text)
        # This is about AI as a product feature, not AI authoring
        self.assertFalse(result["is_ai_assisted"])

    def test_ai_in_url_not_detected(self):
        """AI in URLs should not trigger detection."""
        text = "See https://example.com/ai-docs for more info"
        result = detect_ai_in_text(text)
        self.assertFalse(result["is_ai_assisted"])


class TestGPTPatterns(TestCase):
    """Tests for GPT/ChatGPT pattern detection."""

    def test_chatgpt_basic(self):
        """'ChatGPT' should detect as GPT tool."""
        text = "Used ChatGPT to help with this implementation"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("chatgpt", result["ai_tools"])

    def test_gpt4(self):
        """'GPT-4' should detect as GPT tool."""
        text = "Generated with GPT-4"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("chatgpt", result["ai_tools"])

    def test_gpt4o(self):
        """'GPT-4o' should detect as GPT tool."""
        text = "AI Disclosure: GPT-4o used for code review"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("chatgpt", result["ai_tools"])

    def test_openai(self):
        """'OpenAI' in usage context should detect."""
        text = "Used OpenAI to generate test cases"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("chatgpt", result["ai_tools"])

    def test_openai_api_not_detected(self):
        """Integrating OpenAI API should NOT detect (product feature)."""
        text = "Add OpenAI API integration for chat feature"
        result = detect_ai_in_text(text)
        # This is building an AI feature, not using AI to write code
        self.assertFalse(result["is_ai_assisted"])


class TestWarpAIPatterns(TestCase):
    """Tests for Warp terminal AI pattern detection."""

    def test_warp_ai_explicit(self):
        """'Warp AI' should detect as Warp tool."""
        text = "Used Warp AI to help debug this issue"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("warp", result["ai_tools"])

    def test_warp_terminal_ai(self):
        """'Warp terminal' with AI context should detect."""
        text = "Warp terminal's AI helped with the bash script"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("warp", result["ai_tools"])


class TestImprovedGeminiPatterns(TestCase):
    """Tests for improved Gemini pattern detection to avoid false positives."""

    def test_gemini_used_for(self):
        """'Gemini used for' should detect."""
        text = "Gemini used for code review"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("gemini", result["ai_tools"])

    def test_used_gemini(self):
        """'used Gemini' should detect."""
        text = "I used Gemini to refactor this module"
        result = detect_ai_in_text(text)
        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("gemini", result["ai_tools"])

    def test_gemini_api_product_not_detected(self):
        """Integrating Gemini API should NOT detect (product feature)."""
        text = "Add Gemini API support for content generation"
        result = detect_ai_in_text(text)
        # This is about building with Gemini, not using it to write code
        self.assertFalse(result["is_ai_assisted"])

    def test_gemini_sdk_not_detected(self):
        """'Gemini SDK' feature work should NOT detect."""
        text = "Implement Gemini SDK integration for the app"
        result = detect_ai_in_text(text)
        self.assertFalse(result["is_ai_assisted"])
