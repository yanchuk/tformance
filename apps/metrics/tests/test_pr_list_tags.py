"""Tests for PR list template tags."""

from django.test import TestCase

from apps.metrics.templatetags.pr_list_tags import (
    tech_abbrev,
    tech_badge_class,
    tech_display_name,
)


class TestTechAbbrevFilter(TestCase):
    """Tests for tech_abbrev template filter."""

    def test_frontend_abbreviation(self):
        """Test frontend category abbreviation."""
        self.assertEqual(tech_abbrev("frontend"), "FE")

    def test_backend_abbreviation(self):
        """Test backend category abbreviation."""
        self.assertEqual(tech_abbrev("backend"), "BE")

    def test_javascript_abbreviation(self):
        """Test javascript category abbreviation."""
        self.assertEqual(tech_abbrev("javascript"), "JS")

    def test_test_abbreviation(self):
        """Test test category abbreviation."""
        self.assertEqual(tech_abbrev("test"), "TS")

    def test_docs_abbreviation(self):
        """Test docs category abbreviation."""
        self.assertEqual(tech_abbrev("docs"), "DC")

    def test_config_abbreviation(self):
        """Test config category abbreviation."""
        self.assertEqual(tech_abbrev("config"), "CF")

    def test_other_abbreviation(self):
        """Test other category abbreviation."""
        self.assertEqual(tech_abbrev("other"), "OT")

    def test_unknown_category_uses_first_two_chars(self):
        """Test unknown category falls back to first two uppercase chars."""
        self.assertEqual(tech_abbrev("unknown"), "UN")

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty."""
        self.assertEqual(tech_abbrev(""), "")

    def test_none_returns_empty(self):
        """Test None value returns empty."""
        self.assertEqual(tech_abbrev(None), "")


class TestTechBadgeClassFilter(TestCase):
    """Tests for tech_badge_class template filter."""

    def test_frontend_badge_class(self):
        """Test frontend badge class."""
        self.assertEqual(tech_badge_class("frontend"), "badge-info")

    def test_backend_badge_class(self):
        """Test backend badge class."""
        self.assertEqual(tech_badge_class("backend"), "badge-success")

    def test_javascript_badge_class(self):
        """Test javascript badge class."""
        self.assertEqual(tech_badge_class("javascript"), "badge-warning")

    def test_test_badge_class(self):
        """Test test badge class."""
        self.assertEqual(tech_badge_class("test"), "badge-secondary")

    def test_unknown_category_uses_ghost(self):
        """Test unknown category falls back to badge-ghost."""
        self.assertEqual(tech_badge_class("unknown"), "badge-ghost")

    def test_empty_string_returns_ghost(self):
        """Test empty string returns badge-ghost."""
        self.assertEqual(tech_badge_class(""), "badge-ghost")

    def test_none_returns_ghost(self):
        """Test None value returns badge-ghost."""
        self.assertEqual(tech_badge_class(None), "badge-ghost")


class TestTechDisplayNameFilter(TestCase):
    """Tests for tech_display_name template filter."""

    def test_frontend_display_name(self):
        """Test frontend display name."""
        self.assertEqual(tech_display_name("frontend"), "Frontend")

    def test_backend_display_name(self):
        """Test backend display name."""
        self.assertEqual(tech_display_name("backend"), "Backend")

    def test_javascript_display_name(self):
        """Test javascript display name."""
        self.assertEqual(tech_display_name("javascript"), "JS/TypeScript")

    def test_test_display_name(self):
        """Test test display name."""
        self.assertEqual(tech_display_name("test"), "Test")

    def test_docs_display_name(self):
        """Test docs display name."""
        self.assertEqual(tech_display_name("docs"), "Documentation")

    def test_config_display_name(self):
        """Test config display name."""
        self.assertEqual(tech_display_name("config"), "Configuration")

    def test_unknown_category_uses_title_case(self):
        """Test unknown category falls back to title case."""
        self.assertEqual(tech_display_name("unknown"), "Unknown")

    def test_empty_string_returns_empty(self):
        """Test empty string returns empty."""
        self.assertEqual(tech_display_name(""), "")

    def test_none_returns_empty(self):
        """Test None value returns empty."""
        self.assertEqual(tech_display_name(None), "")
