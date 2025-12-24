"""Tests for LLM prompts module."""

from django.test import TestCase

from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
    PROMPT_VERSION,
    get_user_prompt,
)


class TestPromptVersion(TestCase):
    """Tests for prompt versioning."""

    def test_prompt_version_format(self):
        """Version should be semver format."""
        parts = PROMPT_VERSION.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_system_prompt_not_empty(self):
        """System prompt should have content."""
        self.assertGreater(len(PR_ANALYSIS_SYSTEM_PROMPT), 100)

    def test_system_prompt_contains_key_sections(self):
        """System prompt should have required sections."""
        self.assertIn("AI Detection", PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn("Technology Detection", PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn("Response Format", PR_ANALYSIS_SYSTEM_PROMPT)


class TestGetUserPrompt(TestCase):
    """Tests for get_user_prompt function."""

    def test_basic_prompt_with_body_only(self):
        """Prompt with just body should work."""
        prompt = get_user_prompt(pr_body="Fix bug in login")
        self.assertIn("Fix bug in login", prompt)
        self.assertIn("Description:", prompt)

    def test_prompt_includes_title(self):
        """Title should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Details here",
            pr_title="Add dark mode toggle",
        )
        self.assertIn("Title: Add dark mode toggle", prompt)

    def test_prompt_includes_file_count(self):
        """File count should be included when > 0."""
        prompt = get_user_prompt(
            pr_body="Changes",
            file_count=15,
        )
        self.assertIn("Files changed: 15", prompt)

    def test_prompt_excludes_zero_file_count(self):
        """File count should not be included when 0."""
        prompt = get_user_prompt(
            pr_body="Changes",
            file_count=0,
        )
        self.assertNotIn("Files changed", prompt)

    def test_prompt_includes_additions_deletions(self):
        """Lines added/deleted should be included."""
        prompt = get_user_prompt(
            pr_body="Refactor",
            additions=150,
            deletions=50,
        )
        self.assertIn("Lines: +150/-50", prompt)

    def test_prompt_includes_only_additions(self):
        """Lines should show when only additions present."""
        prompt = get_user_prompt(
            pr_body="New feature",
            additions=200,
            deletions=0,
        )
        self.assertIn("Lines: +200/-0", prompt)

    def test_prompt_includes_only_deletions(self):
        """Lines should show when only deletions present."""
        prompt = get_user_prompt(
            pr_body="Remove dead code",
            additions=0,
            deletions=100,
        )
        self.assertIn("Lines: +0/-100", prompt)

    def test_prompt_excludes_zero_lines(self):
        """Lines should not be included when both are 0."""
        prompt = get_user_prompt(
            pr_body="Docs only",
            additions=0,
            deletions=0,
        )
        self.assertNotIn("Lines:", prompt)

    def test_prompt_includes_comment_count(self):
        """Comment count should be included when > 0."""
        prompt = get_user_prompt(
            pr_body="Changes",
            comment_count=5,
        )
        self.assertIn("Comments: 5", prompt)

    def test_prompt_excludes_zero_comments(self):
        """Comment count should not be included when 0."""
        prompt = get_user_prompt(
            pr_body="Changes",
            comment_count=0,
        )
        self.assertNotIn("Comments", prompt)

    def test_prompt_includes_repo_languages(self):
        """Repository languages should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Backend fix",
            repo_languages=["Python", "TypeScript", "Go"],
        )
        self.assertIn("Repository languages: Python, TypeScript, Go", prompt)

    def test_prompt_excludes_empty_languages(self):
        """Languages should not be included when empty."""
        prompt = get_user_prompt(
            pr_body="Changes",
            repo_languages=[],
        )
        self.assertNotIn("Repository languages", prompt)

    def test_prompt_excludes_none_languages(self):
        """Languages should not be included when None."""
        prompt = get_user_prompt(
            pr_body="Changes",
            repo_languages=None,
        )
        self.assertNotIn("Repository languages", prompt)

    def test_full_prompt_with_all_fields(self):
        """Prompt with all fields should be properly formatted."""
        prompt = get_user_prompt(
            pr_body="Implements new dark mode feature with user preference persistence.",
            pr_title="Add dark mode toggle to settings",
            file_count=12,
            additions=450,
            deletions=30,
            comment_count=8,
            repo_languages=["TypeScript", "React", "CSS"],
        )

        # Check all parts are present
        self.assertIn("Title: Add dark mode toggle to settings", prompt)
        self.assertIn("Files changed: 12", prompt)
        self.assertIn("Lines: +450/-30", prompt)
        self.assertIn("Comments: 8", prompt)
        self.assertIn("Repository languages: TypeScript, React, CSS", prompt)
        self.assertIn("Implements new dark mode feature", prompt)

        # Check structure
        self.assertIn("Analyze this pull request:", prompt)
        self.assertIn("Description:", prompt)

    def test_prompt_handles_empty_body(self):
        """Empty body should be handled gracefully."""
        prompt = get_user_prompt(pr_body="")
        self.assertIn("Description:", prompt)

    def test_prompt_handles_multiline_body(self):
        """Multiline body should be preserved."""
        body = """## Summary
This PR adds feature X.

## Changes
- Added A
- Modified B
- Removed C"""
        prompt = get_user_prompt(pr_body=body)
        self.assertIn("## Summary", prompt)
        self.assertIn("- Added A", prompt)
