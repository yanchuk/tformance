"""Tests that validate regex detection using golden test cases.

These tests bridge the golden tests (designed for LLM evaluation) with the
regex-based detection in ai_detector.py. Not all golden tests are applicable
to regex detection - only those with explicit AI patterns.

These tests serve two purposes:
1. Validate that known AI patterns trigger detection
2. Document known limitations where regex differs from LLM detection
"""

import unittest

from django.test import TestCase

from apps.metrics.prompts.golden_tests import GOLDEN_TESTS, GoldenTestCategory
from apps.metrics.services.ai_detector import detect_ai_in_text


class TestPositiveGoldenTestsDetectWithRegex(TestCase):
    """Validate that positive golden tests trigger regex detection."""

    def test_claude_code_signature_detected(self):
        """pos_claude_code_signature should be detected by regex."""
        test = next(t for t in GOLDEN_TESTS if t.id == "pos_claude_code_signature")
        result = detect_ai_in_text(test.pr_body)

        self.assertTrue(result["is_ai_assisted"])
        # Regex returns "claude_code" for this signature pattern
        self.assertIn("claude_code", result["ai_tools"])

    def test_cursor_explicit_detected(self):
        """pos_cursor_explicit should be detected by regex."""
        test = next(t for t in GOLDEN_TESTS if t.id == "pos_cursor_explicit")
        result = detect_ai_in_text(test.pr_body)

        self.assertTrue(result["is_ai_assisted"])
        # Regex returns "cursor" (not "cursor_ide")
        self.assertIn("cursor", result["ai_tools"])

    def test_copilot_mention_detected(self):
        """pos_copilot_mention should be detected by regex."""
        test = next(t for t in GOLDEN_TESTS if t.id == "pos_copilot_mention")
        result = detect_ai_in_text(test.pr_body)

        self.assertTrue(result["is_ai_assisted"])
        # Regex returns "copilot" (not "github_copilot")
        self.assertIn("copilot", result["ai_tools"])

    @unittest.skip("Aider 'aider:' prefix pattern not yet implemented in regex")
    def test_aider_commit_detected(self):
        """pos_aider_commit should be detected by regex.

        LIMITATION: The "aider:" commit message prefix pattern is not
        currently implemented in ai_patterns.py.
        """
        test = next(t for t in GOLDEN_TESTS if t.id == "pos_aider_commit")
        result = detect_ai_in_text(test.pr_body)

        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("aider", result["ai_tools"])

    @unittest.skip("Windsurf IDE pattern not yet implemented in regex")
    def test_windsurf_codeium_detected(self):
        """pos_windsurf_codeium should be detected by regex.

        LIMITATION: The "Windsurf IDE" pattern is not currently
        implemented in ai_patterns.py.
        """
        test = next(t for t in GOLDEN_TESTS if t.id == "pos_windsurf_codeium")
        result = detect_ai_in_text(test.pr_body)

        self.assertTrue(result["is_ai_assisted"])
        self.assertIn("windsurf", result["ai_tools"])

    def test_multiple_tools_detected_at_least_one(self):
        """pos_multiple_tools should detect at least one AI tool."""
        test = next(t for t in GOLDEN_TESTS if t.id == "pos_multiple_tools")
        result = detect_ai_in_text(test.pr_body)

        self.assertTrue(result["is_ai_assisted"])
        # Should detect at least one tool (Cursor is reliably detected)
        self.assertGreaterEqual(len(result["ai_tools"]), 1)
        self.assertIn("cursor", result["ai_tools"])


class TestNegativeGoldenTestsNotDetectedWithRegex(TestCase):
    """Validate that negative golden tests do NOT trigger regex detection."""

    def test_explicit_no_ai_not_detected(self):
        """neg_explicit_no_ai should NOT be detected as AI-assisted."""
        test = next(t for t in GOLDEN_TESTS if t.id == "neg_explicit_no_ai")
        result = detect_ai_in_text(test.pr_body)

        self.assertFalse(result["is_ai_assisted"])
        self.assertEqual(result["ai_tools"], [])

    def test_empty_body_not_detected(self):
        """neg_empty_body should NOT be detected as AI-assisted."""
        test = next(t for t in GOLDEN_TESTS if t.id == "neg_empty_body")
        result = detect_ai_in_text(test.pr_body)

        self.assertFalse(result["is_ai_assisted"])
        self.assertEqual(result["ai_tools"], [])

    def test_human_only_not_detected(self):
        """neg_human_only should NOT be detected as AI-assisted."""
        test = next(t for t in GOLDEN_TESTS if t.id == "neg_human_only")
        result = detect_ai_in_text(test.pr_body)

        self.assertFalse(result["is_ai_assisted"])
        self.assertEqual(result["ai_tools"], [])

    def test_ai_na_disclosure_not_detected(self):
        """neg_ai_na_disclosure should NOT be detected as AI-assisted."""
        test = next(t for t in GOLDEN_TESTS if t.id == "neg_ai_na_disclosure")
        result = detect_ai_in_text(test.pr_body)

        self.assertFalse(result["is_ai_assisted"])
        self.assertEqual(result["ai_tools"], [])

    def test_ai_none_disclosure_not_detected(self):
        """neg_ai_none_disclosure should NOT be detected as AI-assisted."""
        test = next(t for t in GOLDEN_TESTS if t.id == "neg_ai_none_disclosure")
        result = detect_ai_in_text(test.pr_body)

        self.assertFalse(result["is_ai_assisted"])
        self.assertEqual(result["ai_tools"], [])


class TestProductMentionsNotDetected(TestCase):
    """Validate that AI product mentions (building AI features) are not detected.

    When developers are building AI features, they mention AI products
    but aren't using AI to write the code. These should ideally not be detected.

    Note: Some of these tests document known limitations where regex patterns
    are too broad and cause false positives.
    """

    def test_ai_as_product_not_detected(self):
        """neg_ai_as_product should NOT detect Gemini as an authoring tool."""
        test = next(t for t in GOLDEN_TESTS if t.id == "neg_ai_as_product")
        result = detect_ai_in_text(test.pr_body)

        # Should not falsely detect Gemini as an authoring tool
        self.assertFalse(
            result["is_ai_assisted"],
            "Mentioning Gemini API as a product feature should not trigger detection",
        )

    @unittest.expectedFailure
    def test_claude_product_discussion_not_detected(self):
        """neg_claude_product_discussion should NOT detect Claude as authoring tool.

        KNOWN LIMITATION: The regex pattern for "Claude" is too broad and
        triggers on discussions about Claude as a product feature.
        This is a known false positive case that LLM detection handles better.
        """
        test = next(t for t in GOLDEN_TESTS if t.id == "neg_claude_product_discussion")
        result = detect_ai_in_text(test.pr_body)

        # This currently fails because regex falsely detects "Claude" mentions
        self.assertFalse(
            result["is_ai_assisted"],
            "Discussing Claude as a product feature should not trigger detection",
        )


class TestMostNegativeTestsNotDetected(TestCase):
    """Parametrized test: Most negative golden tests should NOT trigger detection.

    Excludes known false positive cases that are tracked separately.
    """

    # Known false positive cases (regex patterns too broad)
    KNOWN_FALSE_POSITIVES = {
        "neg_claude_product_discussion",  # "Claude" as product triggers detection
        # Tests about building AI features - regex can't distinguish from using AI
        "neg_sdk_version_bump",  # Mentions "@anthropic-ai/sdk" - detected as "claude"
        "neg_llm_test_suite",  # Mentions "ChatGPT" in test names - detected as "chatgpt"
        "neg_ai_competitor_analysis",  # Mentions AI tools in comparison - detected as "chatgpt"
        "neg_openai_client_library",  # Building OpenAI client - detected as "chatgpt"
    }

    def test_most_negative_tests_not_detected(self):
        """Most negative test cases should not trigger regex detection."""
        negative_tests = [
            t
            for t in GOLDEN_TESTS
            if t.category == GoldenTestCategory.NEGATIVE and t.id not in self.KNOWN_FALSE_POSITIVES
        ]

        for test in negative_tests:
            with self.subTest(test_id=test.id, description=test.description):
                result = detect_ai_in_text(test.pr_body)
                self.assertFalse(
                    result["is_ai_assisted"],
                    f"Negative test {test.id} should NOT trigger AI detection. Detected tools: {result['ai_tools']}",
                )
