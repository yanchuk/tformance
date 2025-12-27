"""
Tests for AI tracking fields on models - TDD RED phase.

Tests that PullRequest, PRReview, and Commit models have the required
AI tracking fields.
"""

from django.test import TestCase

from apps.metrics.factories import CommitFactory, PRReviewFactory, PullRequestFactory


class TestPullRequestAIFields(TestCase):
    """Tests for AI tracking fields on PullRequest model."""

    def test_has_body_field(self):
        """PullRequest should have a body field for PR description."""
        pr = PullRequestFactory(state="merged")
        pr.body = "This is the PR description\n\n## Summary\nAdded feature"
        pr.save()
        pr.refresh_from_db()
        self.assertEqual(pr.body, "This is the PR description\n\n## Summary\nAdded feature")

    def test_body_field_can_be_empty(self):
        """PullRequest body field should allow empty strings."""
        pr = PullRequestFactory(state="merged", body="")
        self.assertEqual(pr.body, "")

    def test_has_is_ai_assisted_field(self):
        """PullRequest should have is_ai_assisted boolean field."""
        pr = PullRequestFactory(state="merged")
        pr.is_ai_assisted = True
        pr.save()
        pr.refresh_from_db()
        self.assertTrue(pr.is_ai_assisted)

    def test_is_ai_assisted_defaults_to_false(self):
        """PullRequest is_ai_assisted should default to False."""
        pr = PullRequestFactory(state="merged")
        self.assertFalse(pr.is_ai_assisted)

    def test_has_ai_tools_detected_field(self):
        """PullRequest should have ai_tools_detected JSONField."""
        pr = PullRequestFactory(state="merged")
        pr.ai_tools_detected = ["claude_code", "copilot"]
        pr.save()
        pr.refresh_from_db()
        self.assertEqual(pr.ai_tools_detected, ["claude_code", "copilot"])

    def test_ai_tools_detected_defaults_to_empty_list(self):
        """PullRequest ai_tools_detected should default to empty list."""
        pr = PullRequestFactory(state="merged")
        self.assertEqual(pr.ai_tools_detected, [])


class TestPRReviewAIFields(TestCase):
    """Tests for AI tracking fields on PRReview model."""

    def test_has_body_field(self):
        """PRReview should have a body field for review content."""
        review = PRReviewFactory()
        review.body = "LGTM! The changes look good."
        review.save()
        review.refresh_from_db()
        self.assertEqual(review.body, "LGTM! The changes look good.")

    def test_body_field_can_be_empty(self):
        """PRReview body field should allow empty strings."""
        review = PRReviewFactory(body="")
        self.assertEqual(review.body, "")

    def test_has_is_ai_review_field(self):
        """PRReview should have is_ai_review boolean field."""
        review = PRReviewFactory()
        review.is_ai_review = True
        review.save()
        review.refresh_from_db()
        self.assertTrue(review.is_ai_review)

    def test_is_ai_review_defaults_to_false(self):
        """PRReview is_ai_review should default to False."""
        review = PRReviewFactory()
        self.assertFalse(review.is_ai_review)

    def test_has_ai_reviewer_type_field(self):
        """PRReview should have ai_reviewer_type CharField."""
        review = PRReviewFactory()
        review.ai_reviewer_type = "coderabbit"
        review.save()
        review.refresh_from_db()
        self.assertEqual(review.ai_reviewer_type, "coderabbit")

    def test_ai_reviewer_type_defaults_to_empty(self):
        """PRReview ai_reviewer_type should default to empty string."""
        review = PRReviewFactory()
        self.assertEqual(review.ai_reviewer_type, "")


class TestCommitAIFields(TestCase):
    """Tests for AI tracking fields on Commit model."""

    def test_has_is_ai_assisted_field(self):
        """Commit should have is_ai_assisted boolean field."""
        commit = CommitFactory()
        commit.is_ai_assisted = True
        commit.save()
        commit.refresh_from_db()
        self.assertTrue(commit.is_ai_assisted)

    def test_is_ai_assisted_defaults_to_false(self):
        """Commit is_ai_assisted should default to False."""
        commit = CommitFactory()
        self.assertFalse(commit.is_ai_assisted)

    def test_has_ai_co_authors_field(self):
        """Commit should have ai_co_authors JSONField."""
        commit = CommitFactory()
        commit.ai_co_authors = ["claude", "copilot"]
        commit.save()
        commit.refresh_from_db()
        self.assertEqual(commit.ai_co_authors, ["claude", "copilot"])

    def test_ai_co_authors_defaults_to_empty_list(self):
        """Commit ai_co_authors should default to empty list."""
        commit = CommitFactory()
        self.assertEqual(commit.ai_co_authors, [])


class TestPullRequestAICategoryProperties(TestCase):
    """Tests for AI category computed properties on PullRequest model."""

    def test_ai_code_tools_with_code_tools(self):
        """ai_code_tools should return only code-category tools."""
        pr = PullRequestFactory(
            state="merged",
            ai_tools_detected=["cursor", "coderabbit", "copilot"],
        )
        self.assertEqual(set(pr.ai_code_tools), {"cursor", "copilot"})

    def test_ai_code_tools_empty_when_only_review_tools(self):
        """ai_code_tools should be empty when only review tools detected."""
        pr = PullRequestFactory(
            state="merged",
            ai_tools_detected=["coderabbit", "cubic"],
        )
        self.assertEqual(pr.ai_code_tools, [])

    def test_ai_code_tools_empty_when_no_tools(self):
        """ai_code_tools should be empty when no tools detected."""
        pr = PullRequestFactory(state="merged", ai_tools_detected=[])
        self.assertEqual(pr.ai_code_tools, [])

    def test_ai_review_tools_with_review_tools(self):
        """ai_review_tools should return only review-category tools."""
        pr = PullRequestFactory(
            state="merged",
            ai_tools_detected=["cursor", "coderabbit", "greptile"],
        )
        self.assertEqual(set(pr.ai_review_tools), {"coderabbit", "greptile"})

    def test_ai_review_tools_empty_when_only_code_tools(self):
        """ai_review_tools should be empty when only code tools detected."""
        pr = PullRequestFactory(
            state="merged",
            ai_tools_detected=["cursor", "copilot"],
        )
        self.assertEqual(pr.ai_review_tools, [])

    def test_ai_category_code_only(self):
        """ai_category should return 'code' when only code tools."""
        pr = PullRequestFactory(
            state="merged",
            ai_tools_detected=["cursor", "copilot"],
        )
        self.assertEqual(pr.ai_category, "code")

    def test_ai_category_review_only(self):
        """ai_category should return 'review' when only review tools."""
        pr = PullRequestFactory(
            state="merged",
            ai_tools_detected=["coderabbit", "cubic"],
        )
        self.assertEqual(pr.ai_category, "review")

    def test_ai_category_both(self):
        """ai_category should return 'both' when code and review tools."""
        pr = PullRequestFactory(
            state="merged",
            ai_tools_detected=["cursor", "coderabbit"],
        )
        self.assertEqual(pr.ai_category, "both")

    def test_ai_category_none_when_no_tools(self):
        """ai_category should return None when no tools detected."""
        pr = PullRequestFactory(state="merged", ai_tools_detected=[])
        self.assertIsNone(pr.ai_category)

    def test_ai_category_uses_effective_ai_tools(self):
        """ai_category should prioritize LLM tools over regex detection."""
        # PR with regex-detected tools but LLM summary with different tools
        pr = PullRequestFactory(
            state="merged",
            ai_tools_detected=["coderabbit"],  # review tool from regex
            llm_summary={"ai": {"tools": ["cursor"], "is_assisted": True}},  # code tool from LLM
        )
        # Should use LLM tools (cursor = code), not regex tools (coderabbit = review)
        self.assertEqual(pr.ai_category, "code")

    def test_ai_category_excludes_excluded_tools(self):
        """ai_category should return None when only excluded tools."""
        pr = PullRequestFactory(
            state="merged",
            ai_tools_detected=["snyk", "mintlify"],
        )
        self.assertIsNone(pr.ai_category)
