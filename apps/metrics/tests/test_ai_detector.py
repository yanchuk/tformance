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
