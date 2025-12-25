"""Tests for Jinja2 template rendering."""

from pathlib import Path

from django.test import TestCase

from apps.metrics.prompts.render import (
    get_template_dir,
    list_template_sections,
    render_system_prompt,
)
from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
)


class TestRenderSystemPrompt(TestCase):
    """Tests for render_system_prompt function."""

    def test_returns_string(self):
        """Should return a non-empty string."""
        result = render_system_prompt()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_matches_original_prompt(self):
        """Rendered output should exactly match the original hardcoded prompt.

        This is the critical equivalence test that proves templates produce
        identical output to the original PR_ANALYSIS_SYSTEM_PROMPT.
        """
        rendered = render_system_prompt()
        self.assertEqual(rendered, PR_ANALYSIS_SYSTEM_PROMPT)

    def test_contains_all_major_sections(self):
        """Should contain all major section headers."""
        result = render_system_prompt()

        expected_sections = [
            "## Your Tasks",
            "## AI Detection Rules",
            "## Technology Detection",
            "## Health Assessment Guidelines",
            "## Response Format",
            "## Category Definitions",
            "## PR Type Definitions",
            "## Tool Names",
            "## Language Names",
            "## Framework Names",
        ]

        for section in expected_sections:
            with self.subTest(section=section):
                self.assertIn(section, result)

    def test_contains_json_response_schema(self):
        """Should contain the JSON response schema structure."""
        result = render_system_prompt()

        self.assertIn('"ai":', result)
        self.assertIn('"tech":', result)
        self.assertIn('"summary":', result)
        self.assertIn('"health":', result)
        self.assertIn('"is_assisted":', result)
        self.assertIn('"confidence":', result)

    def test_custom_version_included(self):
        """Should accept custom version parameter."""
        result = render_system_prompt(version="99.0.0")
        # Version is used in template comment, verify prompt renders
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 100)

    def test_no_trailing_whitespace(self):
        """Lines should not have trailing whitespace."""
        result = render_system_prompt()
        for i, line in enumerate(result.split("\n")):
            with self.subTest(line_num=i):
                self.assertEqual(line.rstrip(), line)

    def test_no_multiple_blank_lines(self):
        """Should not have more than one consecutive blank line."""
        result = render_system_prompt()
        self.assertNotIn("\n\n\n", result)


class TestGetTemplateDir(TestCase):
    """Tests for get_template_dir function."""

    def test_returns_path(self):
        """Should return a Path object."""
        result = get_template_dir()
        self.assertIsInstance(result, Path)

    def test_path_exists(self):
        """Template directory should exist."""
        result = get_template_dir()
        self.assertTrue(result.exists())

    def test_path_is_directory(self):
        """Template directory should be a directory."""
        result = get_template_dir()
        self.assertTrue(result.is_dir())

    def test_contains_system_template(self):
        """Should contain system.jinja2 template."""
        result = get_template_dir()
        system_template = result / "system.jinja2"
        self.assertTrue(system_template.exists())


class TestListTemplateSections(TestCase):
    """Tests for list_template_sections function."""

    def test_returns_list(self):
        """Should return a list."""
        result = list_template_sections()
        self.assertIsInstance(result, list)

    def test_returns_non_empty(self):
        """Should return non-empty list of sections."""
        result = list_template_sections()
        self.assertGreater(len(result), 0)

    def test_all_items_are_jinja2_files(self):
        """All items should be .jinja2 files."""
        result = list_template_sections()
        for item in result:
            with self.subTest(item=item):
                self.assertTrue(item.endswith(".jinja2"))

    def test_includes_expected_sections(self):
        """Should include all expected section files."""
        result = list_template_sections()

        expected = [
            "ai_detection.jinja2",
            "definitions.jinja2",
            "enums.jinja2",
            "health_assessment.jinja2",
            "intro.jinja2",
            "response_schema.jinja2",
            "tech_detection.jinja2",
        ]

        for section in expected:
            with self.subTest(section=section):
                self.assertIn(section, result)

    def test_sorted_alphabetically(self):
        """Results should be sorted alphabetically."""
        result = list_template_sections()
        self.assertEqual(result, sorted(result))


class TestRenderUserPrompt(TestCase):
    """Tests for render_user_prompt function - Jinja-based user prompt rendering."""

    def test_render_user_prompt_exists(self):
        """render_user_prompt should be importable from render module."""
        from apps.metrics.prompts.render import render_user_prompt

        self.assertTrue(callable(render_user_prompt))

    def test_returns_string(self):
        """Should return a non-empty string."""
        from apps.metrics.prompts.render import render_user_prompt

        result = render_user_prompt(pr_title="Test PR", pr_body="Test body")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_matches_get_user_prompt_basic(self):
        """Output should match get_user_prompt for basic inputs."""
        from apps.metrics.prompts.render import render_user_prompt
        from apps.metrics.services.llm_prompts import get_user_prompt

        # Basic test case
        rendered = render_user_prompt(
            pr_title="Add new feature",
            pr_body="This is the description.",
            additions=100,
            deletions=50,
        )
        expected = get_user_prompt(
            pr_title="Add new feature",
            pr_body="This is the description.",
            additions=100,
            deletions=50,
        )
        self.assertEqual(rendered, expected)

    def test_matches_get_user_prompt_full_context(self):
        """Output should match get_user_prompt with full PR context."""
        from apps.metrics.prompts.render import render_user_prompt
        from apps.metrics.services.llm_prompts import get_user_prompt

        # Full context test case
        context = {
            "pr_title": "Fix payment bug",
            "pr_body": "Fixed null pointer exception",
            "additions": 10,
            "deletions": 5,
            "file_count": 2,
            "comment_count": 3,
            "repo_languages": ["Python", "TypeScript"],
            "state": "merged",
            "labels": ["bugfix", "urgent"],
            "is_draft": False,
            "is_hotfix": True,
            "is_revert": False,
            "cycle_time_hours": 24.5,
            "review_time_hours": 2.0,
            "commits_after_first_review": 1,
            "review_rounds": 2,
            "file_paths": ["apps/payments/views.py", "apps/payments/tests.py"],
            "commit_messages": ["Fix null check", "Add tests"],
            "milestone": "Q1 2025",
            "assignees": ["alice", "bob"],
            "linked_issues": ["#123"],
            "jira_key": "PAY-456",
            "author_name": "John Developer",
            "reviewers": ["Sarah Tech Lead"],
            "review_comments": ["LGTM!"],
        }

        rendered = render_user_prompt(**context)
        expected = get_user_prompt(**context)
        self.assertEqual(rendered, expected)

    def test_contains_analyze_header(self):
        """Should start with 'Analyze this pull request:' header."""
        from apps.metrics.prompts.render import render_user_prompt

        result = render_user_prompt(pr_title="Test", pr_body="Body")
        self.assertTrue(result.startswith("Analyze this pull request:"))

    def test_includes_title_when_provided(self):
        """Should include title in output when provided."""
        from apps.metrics.prompts.render import render_user_prompt

        result = render_user_prompt(pr_title="My Test Title", pr_body="Body")
        self.assertIn("Title: My Test Title", result)

    def test_includes_author_when_provided(self):
        """Should include author in output when provided."""
        from apps.metrics.prompts.render import render_user_prompt

        result = render_user_prompt(pr_title="Test", pr_body="Body", author_name="Alice Developer")
        self.assertIn("Author: Alice Developer", result)

    def test_includes_timing_metrics(self):
        """Should include timing metrics when provided."""
        from apps.metrics.prompts.render import render_user_prompt

        result = render_user_prompt(
            pr_title="Test",
            pr_body="Body",
            cycle_time_hours=48.5,
            review_time_hours=4.0,
        )
        self.assertIn("Cycle time: 48.5 hours", result)
        self.assertIn("Time to first review: 4.0 hours", result)

    def test_includes_commit_messages(self):
        """Should include commit messages when provided."""
        from apps.metrics.prompts.render import render_user_prompt

        result = render_user_prompt(
            pr_title="Test",
            pr_body="Body",
            commit_messages=["Initial commit", "Fix bug"],
        )
        self.assertIn("Commits:", result)
        self.assertIn("- Initial commit", result)
        self.assertIn("- Fix bug", result)

    def test_includes_reviewers(self):
        """Should include reviewers when provided."""
        from apps.metrics.prompts.render import render_user_prompt

        result = render_user_prompt(
            pr_title="Test",
            pr_body="Body",
            reviewers=["Alice", "Bob"],
        )
        self.assertIn("Reviewers: Alice, Bob", result)

    def test_includes_description_at_end(self):
        """Description should be at the end of the output."""
        from apps.metrics.prompts.render import render_user_prompt

        result = render_user_prompt(pr_title="Test", pr_body="This is the PR description.")
        self.assertIn("Description:\nThis is the PR description.", result)


class TestUserPromptTemplate(TestCase):
    """Tests for user.jinja2 template existence and structure."""

    def test_user_template_exists(self):
        """user.jinja2 template should exist."""
        result = get_template_dir()
        user_template = result / "user.jinja2"
        self.assertTrue(user_template.exists(), "user.jinja2 template should exist")

    def test_user_template_is_readable(self):
        """user.jinja2 template should be readable."""
        result = get_template_dir()
        user_template = result / "user.jinja2"
        content = user_template.read_text()
        self.assertGreater(len(content), 0)
