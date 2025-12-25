"""Tests for AI signal aggregation service.

TDD tests for aggregating AI signals from commits, reviews, and files to PR level.
"""

from django.test import TestCase

from apps.metrics.factories import (
    CommitFactory,
    PRFileFactory,
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services.ai_signals import (
    aggregate_commit_ai_signals,
    aggregate_review_ai_signals,
    calculate_ai_confidence,
    detect_ai_config_files,
)


class TestAggregateCommitAISignals(TestCase):
    """Tests for commit AI signal aggregation."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_no_commits_returns_false(self):
        """PR with no commits should return False."""
        pr = PullRequestFactory(team=self.team, author=self.member)

        result = aggregate_commit_ai_signals(pr)

        self.assertFalse(result)

    def test_no_ai_commits_returns_false(self):
        """PR with commits but none AI-assisted should return False."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        CommitFactory(
            team=self.team,
            pull_request=pr,
            is_ai_assisted=False,
            ai_co_authors=[],
        )
        CommitFactory(
            team=self.team,
            pull_request=pr,
            is_ai_assisted=False,
            ai_co_authors=[],
        )

        result = aggregate_commit_ai_signals(pr)

        self.assertFalse(result)

    def test_with_ai_assisted_commit_returns_true(self):
        """PR with is_ai_assisted commit should return True."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        CommitFactory(
            team=self.team,
            pull_request=pr,
            is_ai_assisted=True,
            ai_co_authors=[],
        )

        result = aggregate_commit_ai_signals(pr)

        self.assertTrue(result)

    def test_with_ai_coauthors_returns_true(self):
        """PR with commit having AI co-authors should return True."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        CommitFactory(
            team=self.team,
            pull_request=pr,
            is_ai_assisted=False,
            ai_co_authors=["Claude <noreply@anthropic.com>"],
        )

        result = aggregate_commit_ai_signals(pr)

        self.assertTrue(result)

    def test_with_mixed_commits(self):
        """PR with mix of AI and non-AI commits should return True."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        # Regular commit
        CommitFactory(
            team=self.team,
            pull_request=pr,
            is_ai_assisted=False,
            ai_co_authors=[],
        )
        # AI-assisted commit
        CommitFactory(
            team=self.team,
            pull_request=pr,
            is_ai_assisted=True,
            ai_co_authors=[],
        )

        result = aggregate_commit_ai_signals(pr)

        self.assertTrue(result)


class TestAggregateReviewAISignals(TestCase):
    """Tests for review AI signal aggregation."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.reviewer = TeamMemberFactory(team=self.team)

    def test_no_reviews_returns_false(self):
        """PR with no reviews should return False."""
        pr = PullRequestFactory(team=self.team, author=self.member)

        result = aggregate_review_ai_signals(pr)

        self.assertFalse(result)

    def test_no_ai_reviews_returns_false(self):
        """PR with reviews but none from AI should return False."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=self.reviewer,
            is_ai_review=False,
        )

        result = aggregate_review_ai_signals(pr)

        self.assertFalse(result)

    def test_with_ai_review_returns_true(self):
        """PR with AI review should return True."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=self.reviewer,
            is_ai_review=True,
            ai_reviewer_type="coderabbit",
        )

        result = aggregate_review_ai_signals(pr)

        self.assertTrue(result)

    def test_with_mixed_reviews(self):
        """PR with mix of AI and human reviews should return True."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        # Human review
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=self.reviewer,
            is_ai_review=False,
        )
        # AI review
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=self.reviewer,
            is_ai_review=True,
        )

        result = aggregate_review_ai_signals(pr)

        self.assertTrue(result)


class TestDetectAIConfigFiles(TestCase):
    """Tests for AI config file pattern detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_no_files_returns_false(self):
        """PR with no files should return False."""
        pr = PullRequestFactory(team=self.team, author=self.member)

        result = detect_ai_config_files(pr)

        self.assertFalse(result["has_ai_files"])
        self.assertEqual(result["tools"], [])
        self.assertEqual(result["files"], [])

    def test_no_ai_config_files_returns_false(self):
        """PR with files but no AI config files should return False."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(team=self.team, pull_request=pr, filename="src/components/Button.tsx")
        PRFileFactory(team=self.team, pull_request=pr, filename="apps/metrics/views.py")

        result = detect_ai_config_files(pr)

        self.assertFalse(result["has_ai_files"])

    def test_detect_cursorrules(self):
        """PR modifying .cursorrules should be detected as Cursor."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(team=self.team, pull_request=pr, filename=".cursorrules")

        result = detect_ai_config_files(pr)

        self.assertTrue(result["has_ai_files"])
        self.assertIn("cursor", result["tools"])
        self.assertIn(".cursorrules", result["files"])

    def test_detect_claude_md(self):
        """PR modifying CLAUDE.md should be detected as Claude Code."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(team=self.team, pull_request=pr, filename="CLAUDE.md")

        result = detect_ai_config_files(pr)

        self.assertTrue(result["has_ai_files"])
        self.assertIn("claude", result["tools"])

    def test_detect_copilot_instructions(self):
        """PR modifying copilot-instructions.md should be detected as Copilot."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(
            team=self.team,
            pull_request=pr,
            filename=".github/copilot-instructions.md",
        )

        result = detect_ai_config_files(pr)

        self.assertTrue(result["has_ai_files"])
        self.assertIn("copilot", result["tools"])

    def test_detect_cursor_mdc_rules(self):
        """PR modifying .cursor/rules/*.mdc should be detected as Cursor."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(
            team=self.team,
            pull_request=pr,
            filename=".cursor/rules/python-rules.mdc",
        )

        result = detect_ai_config_files(pr)

        self.assertTrue(result["has_ai_files"])
        self.assertIn("cursor", result["tools"])

    def test_exclude_cursor_pagination(self):
        """Files with 'cursor-pagination' should NOT be detected as AI config."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(
            team=self.team,
            pull_request=pr,
            filename="src/utils/cursor-pagination-query.dto.ts",
        )

        result = detect_ai_config_files(pr)

        self.assertFalse(result["has_ai_files"])

    def test_exclude_gemini_product_code(self):
        """Files in /ai/gemini/ paths should NOT be detected (product code)."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(
            team=self.team,
            pull_request=pr,
            filename="packages/ai/gemini/client.ts",
        )

        result = detect_ai_config_files(pr)

        self.assertFalse(result["has_ai_files"])

    def test_detect_multiple_tools(self):
        """PR with multiple AI config files should detect all tools."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(team=self.team, pull_request=pr, filename=".cursorrules")
        PRFileFactory(team=self.team, pull_request=pr, filename="CLAUDE.md")
        PRFileFactory(
            team=self.team,
            pull_request=pr,
            filename=".github/copilot-instructions.md",
        )

        result = detect_ai_config_files(pr)

        self.assertTrue(result["has_ai_files"])
        self.assertEqual(len(result["tools"]), 3)
        self.assertIn("cursor", result["tools"])
        self.assertIn("claude", result["tools"])
        self.assertIn("copilot", result["tools"])

    def test_detect_aider_config(self):
        """PR modifying .aider.conf.yml should be detected as Aider."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(team=self.team, pull_request=pr, filename=".aider.conf.yml")

        result = detect_ai_config_files(pr)

        self.assertTrue(result["has_ai_files"])
        self.assertIn("aider", result["tools"])

    def test_detect_coderabbit_config(self):
        """PR modifying .coderabbit.yaml should be detected as CodeRabbit."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(team=self.team, pull_request=pr, filename=".coderabbit.yaml")

        result = detect_ai_config_files(pr)

        self.assertTrue(result["has_ai_files"])
        self.assertIn("coderabbit", result["tools"])

    def test_exclude_proguard_rules(self):
        """Android ProGuard rules should NOT be detected as AI config."""
        pr = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(team=self.team, pull_request=pr, filename="app/proguard-rules.pro")
        PRFileFactory(team=self.team, pull_request=pr, filename="lib/consumer-rules.pro")

        result = detect_ai_config_files(pr)

        self.assertFalse(result["has_ai_files"])


class TestCalculateAIConfidence(TestCase):
    """Tests for AI confidence score calculation.

    Weights (from context.md):
        - LLM Detection: 0.40
        - Commit Signals: 0.25
        - Regex Patterns: 0.20
        - Review Signals: 0.10
        - File Patterns: 0.05
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_no_signals_returns_zero(self):
        """PR with no AI signals should return 0.0 confidence."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,
            ai_tools_detected=[],
        )

        score, signals = calculate_ai_confidence(pr)

        self.assertEqual(score, 0.0)
        self.assertEqual(signals["llm"]["score"], 0.0)
        self.assertEqual(signals["regex"]["score"], 0.0)
        self.assertEqual(signals["commits"]["score"], 0.0)
        self.assertEqual(signals["reviews"]["score"], 0.0)
        self.assertEqual(signals["files"]["score"], 0.0)

    def test_llm_only_returns_weight(self):
        """PR with only LLM detection should return weighted score."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,
            ai_tools_detected=[],
            llm_summary={"ai": {"is_assisted": True, "tools": ["claude"], "confidence": 0.95}},
        )

        score, signals = calculate_ai_confidence(pr)

        # 0.40 * 0.95 = 0.38
        self.assertAlmostEqual(score, 0.38, places=2)
        self.assertAlmostEqual(signals["llm"]["score"], 0.38, places=2)
        self.assertTrue(signals["llm"]["is_assisted"])
        self.assertEqual(signals["llm"]["tools"], ["claude"])

    def test_regex_only_returns_weight(self):
        """PR with only regex detection should return 0.20 (regex weight)."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
        )

        score, signals = calculate_ai_confidence(pr)

        self.assertAlmostEqual(score, 0.20, places=2)
        self.assertAlmostEqual(signals["regex"]["score"], 0.20, places=2)
        self.assertTrue(signals["regex"]["is_assisted"])
        self.assertEqual(signals["regex"]["tools"], ["cursor"])

    def test_commits_only_returns_weight(self):
        """PR with only commit signals should return 0.25 (commit weight)."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,
            ai_tools_detected=[],
            has_ai_commits=True,
        )

        score, signals = calculate_ai_confidence(pr)

        self.assertAlmostEqual(score, 0.25, places=2)
        self.assertAlmostEqual(signals["commits"]["score"], 0.25, places=2)
        self.assertTrue(signals["commits"]["has_ai"])

    def test_reviews_only_returns_weight(self):
        """PR with only review signals should return 0.10 (review weight)."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,
            ai_tools_detected=[],
            has_ai_review=True,
        )

        score, signals = calculate_ai_confidence(pr)

        self.assertAlmostEqual(score, 0.10, places=2)
        self.assertAlmostEqual(signals["reviews"]["score"], 0.10, places=2)
        self.assertTrue(signals["reviews"]["has_ai"])

    def test_files_only_returns_weight(self):
        """PR with only file signals should return 0.05 (file weight)."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,
            ai_tools_detected=[],
            has_ai_files=True,
        )

        score, signals = calculate_ai_confidence(pr)

        self.assertAlmostEqual(score, 0.05, places=2)
        self.assertAlmostEqual(signals["files"]["score"], 0.05, places=2)
        self.assertTrue(signals["files"]["has_ai"])

    def test_all_signals_returns_full_score(self):
        """PR with all AI signals should return 1.0 (sum of all weights)."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,  # Regex detection
            ai_tools_detected=["cursor"],
            llm_summary={"ai": {"is_assisted": True, "tools": ["claude"]}},  # LLM
            has_ai_commits=True,  # Commit signals
            has_ai_review=True,  # Review signals
            has_ai_files=True,  # File signals
        )

        score, signals = calculate_ai_confidence(pr)

        self.assertAlmostEqual(score, 1.0, places=2)
        self.assertAlmostEqual(signals["llm"]["score"], 0.40, places=2)
        self.assertAlmostEqual(signals["regex"]["score"], 0.20, places=2)
        self.assertAlmostEqual(signals["commits"]["score"], 0.25, places=2)
        self.assertAlmostEqual(signals["reviews"]["score"], 0.10, places=2)
        self.assertAlmostEqual(signals["files"]["score"], 0.05, places=2)

    def test_breakdown_structure(self):
        """Verify the signal breakdown has expected structure."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
        )

        _, signals = calculate_ai_confidence(pr)

        # Check all keys exist
        self.assertIn("llm", signals)
        self.assertIn("regex", signals)
        self.assertIn("commits", signals)
        self.assertIn("reviews", signals)
        self.assertIn("files", signals)

        # Check each signal has score key
        for key in ["llm", "regex", "commits", "reviews", "files"]:
            self.assertIn("score", signals[key])

    def test_llm_confidence_affects_score(self):
        """LLM confidence value should affect the score proportionally."""
        pr_high = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,
            ai_tools_detected=[],
            llm_summary={"ai": {"is_assisted": True, "confidence": 0.95}},
        )
        pr_low = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,
            ai_tools_detected=[],
            llm_summary={"ai": {"is_assisted": True, "confidence": 0.50}},
        )

        score_high, _ = calculate_ai_confidence(pr_high)
        score_low, _ = calculate_ai_confidence(pr_low)

        # High confidence should score higher than low confidence
        self.assertGreater(score_high, score_low)

    def test_llm_not_assisted_returns_zero(self):
        """LLM saying not AI-assisted should contribute 0 to score."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,
            ai_tools_detected=[],
            llm_summary={"ai": {"is_assisted": False, "tools": [], "confidence": 0.90}},
        )

        score, signals = calculate_ai_confidence(pr)

        self.assertEqual(score, 0.0)
        self.assertEqual(signals["llm"]["score"], 0.0)
        self.assertFalse(signals["llm"]["is_assisted"])
