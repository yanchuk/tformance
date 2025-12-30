"""Tests for PullRequest model computed properties.

These tests cover the effective_* properties that implement the LLM Data Priority Rule:
LLM-detected data takes priority over pattern/regex detection.

Run with: pytest apps/metrics/tests/models/test_pull_request_properties.py -v
"""

from django.test import TestCase

from apps.metrics.factories import PRFileFactory, PullRequestFactory, TeamFactory


class TestEffectiveTechCategories(TestCase):
    """Tests for PullRequest.effective_tech_categories property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_llm_categories_when_available(self):
        """LLM categories should be preferred over pattern-based detection."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary={"tech": {"categories": ["frontend", "devops"]}},
        )
        # Create a PRFile with backend category (should be ignored)
        PRFileFactory(team=self.team, pull_request=pr, file_category="backend")

        result = pr.effective_tech_categories

        self.assertEqual(result, ["frontend", "devops"])
        self.assertNotIn("backend", result)

    def test_falls_back_to_prfile_categories_when_llm_empty(self):
        """Should fall back to PRFile categories when LLM returns empty list."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary={"tech": {"categories": []}},
        )
        # Create PRFiles with categories
        PRFileFactory(team=self.team, pull_request=pr, file_category="backend")
        PRFileFactory(team=self.team, pull_request=pr, file_category="database")

        result = pr.effective_tech_categories

        self.assertIn("backend", result)
        self.assertIn("database", result)

    def test_falls_back_to_prfile_categories_when_no_llm_summary(self):
        """Should fall back to PRFile categories when llm_summary is None."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary=None,
        )
        PRFileFactory(team=self.team, pull_request=pr, file_category="mobile")

        result = pr.effective_tech_categories

        self.assertEqual(result, ["mobile"])

    def test_returns_empty_list_when_no_categories(self):
        """Should return empty list when no categories from any source."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary=None,
        )
        # No PRFiles created - no categories available

        result = pr.effective_tech_categories

        self.assertEqual(result, [])


class TestEffectiveIsAiAssisted(TestCase):
    """Tests for PullRequest.effective_is_ai_assisted property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_llm_detection_when_high_confidence(self):
        """LLM detection should be used when confidence >= 0.5."""
        pr = PullRequestFactory(
            team=self.team,
            is_ai_assisted=False,  # Regex says no
            llm_summary={"ai": {"is_assisted": True, "confidence": 0.9}},  # LLM says yes
        )

        result = pr.effective_is_ai_assisted

        self.assertTrue(result)

    def test_falls_back_to_regex_when_low_llm_confidence(self):
        """Should fall back to regex detection when LLM confidence < 0.5."""
        pr = PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,  # Regex says yes
            llm_summary={"ai": {"is_assisted": False, "confidence": 0.3}},  # LLM says no, low confidence
        )

        result = pr.effective_is_ai_assisted

        self.assertTrue(result)  # Falls back to regex

    def test_falls_back_to_regex_when_no_llm_summary(self):
        """Should use regex detection when llm_summary is None."""
        pr = PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            llm_summary=None,
        )

        result = pr.effective_is_ai_assisted

        self.assertTrue(result)

    def test_llm_false_with_high_confidence_overrides_regex_true(self):
        """LLM detecting no AI (high confidence) should override regex true."""
        pr = PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,  # Regex says yes
            llm_summary={"ai": {"is_assisted": False, "confidence": 0.8}},  # LLM says no, high confidence
        )

        result = pr.effective_is_ai_assisted

        self.assertFalse(result)

    def test_confidence_exactly_0_5_uses_llm(self):
        """Confidence exactly at 0.5 threshold should use LLM result."""
        pr = PullRequestFactory(
            team=self.team,
            is_ai_assisted=False,
            llm_summary={"ai": {"is_assisted": True, "confidence": 0.5}},
        )

        result = pr.effective_is_ai_assisted

        self.assertTrue(result)


class TestEffectiveAiTools(TestCase):
    """Tests for PullRequest.effective_ai_tools property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_llm_tools_when_available(self):
        """LLM-detected tools should be preferred over regex detection."""
        pr = PullRequestFactory(
            team=self.team,
            ai_tools_detected=["copilot"],  # Regex detected
            llm_summary={"ai": {"tools": ["cursor", "claude"]}},  # LLM detected
        )

        result = pr.effective_ai_tools

        self.assertEqual(result, ["cursor", "claude"])
        self.assertNotIn("copilot", result)

    def test_falls_back_to_regex_when_llm_empty(self):
        """Should fall back to regex detection when LLM returns empty list."""
        pr = PullRequestFactory(
            team=self.team,
            ai_tools_detected=["copilot", "chatgpt"],
            llm_summary={"ai": {"tools": []}},
        )

        result = pr.effective_ai_tools

        self.assertEqual(result, ["copilot", "chatgpt"])

    def test_falls_back_to_regex_when_no_llm_summary(self):
        """Should use regex detection when llm_summary is None."""
        pr = PullRequestFactory(
            team=self.team,
            ai_tools_detected=["windsurf"],
            llm_summary=None,
        )

        result = pr.effective_ai_tools

        self.assertEqual(result, ["windsurf"])

    def test_returns_empty_list_when_no_tools_detected(self):
        """Should return empty list when no tools from any source."""
        pr = PullRequestFactory(
            team=self.team,
            ai_tools_detected=[],
            llm_summary=None,
        )

        result = pr.effective_ai_tools

        self.assertEqual(result, [])

    def test_returns_empty_list_when_ai_tools_detected_is_empty_list(self):
        """Should return empty list when ai_tools_detected is empty."""
        pr = PullRequestFactory(
            team=self.team,
            ai_tools_detected=[],
            llm_summary={"ai": {"tools": []}},
        )

        result = pr.effective_ai_tools

        self.assertEqual(result, [])


class TestAiCodeTools(TestCase):
    """Tests for PullRequest.ai_code_tools property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_only_code_category_tools(self):
        """Should filter to only code-generation tools."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary={"ai": {"tools": ["cursor", "copilot", "coderabbit"]}},
        )

        result = pr.ai_code_tools

        self.assertIn("cursor", result)
        self.assertIn("copilot", result)
        self.assertNotIn("coderabbit", result)  # Review tool

    def test_returns_empty_when_only_review_tools(self):
        """Should return empty list when only review tools detected."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary={"ai": {"tools": ["coderabbit", "cubic"]}},
        )

        result = pr.ai_code_tools

        self.assertEqual(result, [])

    def test_returns_empty_when_no_tools(self):
        """Should return empty list when no tools detected."""
        pr = PullRequestFactory(
            team=self.team,
            ai_tools_detected=[],  # Empty list, not None
            llm_summary=None,
        )

        result = pr.ai_code_tools

        self.assertEqual(result, [])


class TestAiReviewTools(TestCase):
    """Tests for PullRequest.ai_review_tools property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_only_review_category_tools(self):
        """Should filter to only code-review tools."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary={"ai": {"tools": ["cursor", "coderabbit", "greptile"]}},
        )

        result = pr.ai_review_tools

        self.assertIn("coderabbit", result)
        self.assertIn("greptile", result)
        self.assertNotIn("cursor", result)  # Code tool

    def test_returns_empty_when_only_code_tools(self):
        """Should return empty list when only code tools detected."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary={"ai": {"tools": ["cursor", "copilot"]}},
        )

        result = pr.ai_review_tools

        self.assertEqual(result, [])


class TestAiCategory(TestCase):
    """Tests for PullRequest.ai_category property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_code_when_only_code_tools(self):
        """Should return 'code' when only code-generation tools detected."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary={"ai": {"tools": ["cursor", "copilot"]}},
        )

        result = pr.ai_category

        self.assertEqual(result, "code")

    def test_returns_review_when_only_review_tools(self):
        """Should return 'review' when only review tools detected."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary={"ai": {"tools": ["coderabbit"]}},
        )

        result = pr.ai_category

        self.assertEqual(result, "review")

    def test_returns_both_when_mixed_tools(self):
        """Should return 'both' when both code and review tools detected."""
        pr = PullRequestFactory(
            team=self.team,
            llm_summary={"ai": {"tools": ["cursor", "coderabbit"]}},
        )

        result = pr.ai_category

        self.assertEqual(result, "both")

    def test_returns_none_when_no_tools(self):
        """Should return None when no AI tools detected."""
        pr = PullRequestFactory(
            team=self.team,
            ai_tools_detected=[],  # Empty list, not None
            llm_summary=None,
        )

        result = pr.ai_category

        self.assertIsNone(result)


class TestEffectivePrType(TestCase):
    """Tests for PullRequest.effective_pr_type property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_returns_llm_type_when_valid(self):
        """LLM-detected type should be preferred when valid."""
        pr = PullRequestFactory(
            team=self.team,
            labels=["enhancement"],  # Would infer feature
            llm_summary={"summary": {"type": "bugfix"}},  # LLM says bugfix
        )

        result = pr.effective_pr_type

        self.assertEqual(result, "bugfix")

    def test_infers_from_labels_when_no_llm_type(self):
        """Should infer from labels when LLM has no type."""
        pr = PullRequestFactory(
            team=self.team,
            labels=["feature"],
            llm_summary={"summary": {}},
        )

        result = pr.effective_pr_type

        self.assertEqual(result, "feature")

    def test_infers_bugfix_from_bug_label(self):
        """Should infer bugfix from 'bug' label."""
        pr = PullRequestFactory(
            team=self.team,
            labels=["bug"],
            llm_summary=None,
        )

        result = pr.effective_pr_type

        self.assertEqual(result, "bugfix")

    def test_infers_feature_from_enhancement_label(self):
        """Should infer feature from 'enhancement' label."""
        pr = PullRequestFactory(
            team=self.team,
            labels=["enhancement"],
            llm_summary=None,
        )

        result = pr.effective_pr_type

        self.assertEqual(result, "feature")

    def test_returns_unknown_when_no_type_info(self):
        """Should return 'unknown' when no type information available."""
        pr = PullRequestFactory(
            team=self.team,
            labels=[],
            llm_summary=None,
        )

        result = pr.effective_pr_type

        self.assertEqual(result, "unknown")

    def test_ignores_invalid_llm_type(self):
        """Should fall back to labels if LLM type is invalid."""
        pr = PullRequestFactory(
            team=self.team,
            labels=["refactor"],
            llm_summary={"summary": {"type": "invalid_type"}},
        )

        result = pr.effective_pr_type

        self.assertEqual(result, "refactor")


class TestGithubUrl(TestCase):
    """Tests for PullRequest.github_url property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_constructs_correct_github_url(self):
        """Should construct correct GitHub URL from repo and PR ID."""
        pr = PullRequestFactory(
            team=self.team,
            github_repo="org/repo-name",
            github_pr_id=123,
        )

        result = pr.github_url

        self.assertEqual(result, "https://github.com/org/repo-name/pull/123")

    def test_handles_complex_repo_names(self):
        """Should handle repos with dashes and underscores."""
        pr = PullRequestFactory(
            team=self.team,
            github_repo="my-org/my-cool_repo",
            github_pr_id=456,
        )

        result = pr.github_url

        self.assertEqual(result, "https://github.com/my-org/my-cool_repo/pull/456")
