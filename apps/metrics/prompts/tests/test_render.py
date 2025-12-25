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
